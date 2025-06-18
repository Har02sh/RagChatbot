from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timezone
from app.extensions import db
from app.model import Chat, Message, PDF
from . import chat_blueprint
from ..services import *
import json


@chat_blueprint.route('/api/chats', methods=['GET'])
@login_required
def get_chats():
    """Get all chats for current user"""
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.updated_at.desc()).all()
    return jsonify({
        'success': True,
        'chats': [chat.to_dict() for chat in chats]
    })

@chat_blueprint.route('/api/chats', methods=['POST'])
@login_required
def create_chat():
    """Create a new chat"""
    data = request.json
    title = data.get('title', 'New Chat')
    pdf_id = data.get('pdf_id')
    if not pdf_id:
        return jsonify({'success': False, 'message': 'pdf_id is required'}), 400

    # Ensure the PDF exists and belongs to the user
    pdf = PDF.query.filter_by(id=pdf_id, user_id=current_user.id).first()
    if not pdf:
        return jsonify({'success': False, 'message': 'PDF not found'}), 404

    new_chat = Chat(
        title=title,
        user_id=current_user.id,
        pdf_id=pdf_id
    )
    db.session.add(new_chat)
    db.session.commit()
    return jsonify(new_chat.to_dict())

@chat_blueprint.route('/api/chats/<int:chat_id>', methods=['GET'])
@login_required
def get_chat(chat_id):
    """Get a specific chat"""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    return jsonify(chat.to_dict())


@chat_blueprint.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    """Delete a chat and all its messages"""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    
    db.session.delete(chat)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Chat deleted successfully'
    })


@chat_blueprint.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@login_required
def get_messages(chat_id):
    """Get all messages for a specific chat"""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
    
    return jsonify({
        'success': True,
        'messages': [message.to_dict() for message in messages]
    })

@chat_blueprint.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@login_required
def send_message(chat_id):
    """Send a new message in a chat and get bot response (JSON, not stream)"""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    data = request.json
    user_text = data.get('text', '')
    
    if not user_text.strip():
        return jsonify({
            'success': False,
            'message': 'Message cannot be empty'
        }), 400
    
    # Create user message
    user_message = Message(
        chat_id=chat_id,
        sender='user',
        text=user_text
    )
    db.session.add(user_message)
    
    chat.updated_at = datetime.now(timezone.utc) # Update chat's updated_at timestamp
    
    # Update chat title if it's the first message
    updated_title = None
    message_count = Message.query.filter_by(chat_id=chat_id).count()
    if message_count == 0:
        words = user_text.split()
        title = ' '.join(words[:4])
        if len(words) > 4:
            title += '...'
        chat.title = title
        print(f"Setting chat title to: {title}")
        updated_title = title
    
    db.session.commit()
    
    searcher = QdrantHybridSearcher(
        collection_name="pdf_hybrid_search",
        embedding_model="all-MiniLM-L6-v2",
        tfidf_vectorizer_path="pdf_hybrid_search_vectorizer.pkl"
    )
    hybrid_results = searcher.hybrid_search(user_text, limit=5)

    # Generate bot response (collect all chunks)
    bot_text = ""
    try:
        for chunk in answer_gen.generate_answer_streaming(user_text, hybrid_results):
            if chunk.get("type") == "content":
                bot_text += chunk.get("content", "")
    except Exception as e:
        print("Error generating bot response:", e, flush=True)
        return jsonify({
            'success': False,
            'message': f'Error generating bot response: {str(e)}'
        }), 500

    # Save bot response to DB
    bot_msg = Message(chat_id=chat_id, sender="bot", text=bot_text)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({
        'success': True,
        'user_message': user_message.to_dict(),
        'bot_message': bot_msg.to_dict(),
        'updated_title': updated_title
    })

@chat_blueprint.route('/api/uploadPdf', methods=['POST'])
@login_required
def upload_file():
    """Upload a file for chat context"""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No file part'
        }), 400
    
    file = request.files['file']
    
    # If user does not select file, browser may also submit an empty file without filename
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'No selected file'
        }), 400
    
    # Check file type
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf'})
    if not allowed_file(file.filename, allowed_extensions):
        return jsonify({
            'success': False,
            'message': f'File type not allowed. Supported types: {", ".join(allowed_extensions)}'
        }), 400
    
    # Save the file
    filename = secure_filename(file.filename)
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    # RAG FUNCTIONALITY
    chunks = processor.process_pdf_for_rag( pdf_path=file_path, save_format="json")

    indexer = QdrantHybridIndexer(
        path=qdrant_path,
        collection_name="pdf_hybrid_search",
        embedding_model="all-MiniLM-L6-v2"
    )
    success = indexer.index_from_pdf_processor(processor, recreate_collection=True)

    if success:
        print("Indexing completed successfully!")
        stats = indexer.get_collection_stats()
        print("Collection Stats:", json.dumps(stats, indent=2))
    else:
        print("Indexing failed!")

    os.remove(file_path)  # Clean up the uploaded file after processing

    pdf = PDF(
        file_name=filename,
        file_path=file_path,
        user_id=current_user.id
    )
    db.session.add(pdf)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'File uploaded successfully',
        "pdf_id": pdf.id, 
        "file_name": pdf.file_name
    })

# Helper functions
def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions