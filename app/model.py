from app.extensions import db
from flask_login import UserMixin
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo  # fallback for older Python

    

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')


class PDF(db.Model):
    """Model to store uploaded PDF metadata"""
    __tablename__ = "pdf"
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # local or cloud path
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='processing')

    # Relationships
    chats = db.relationship('Chat', backref='pdf', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<PDF {self.id} - {self.file_name}>"
    

class Chat(db.Model):
    """Chat model for storing conversation threads"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf.id'), nullable=False)  # 👈 link to PDF

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    messages = db.relationship('Message', backref='chat', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'pdf_id': self.pdf_id,
            'file_name': self.pdf.file_name if self.pdf else None,
            'message_count': len(self.messages)
        }

    def __repr__(self):
        return f'<Chat {self.id}: {self.title}>'

class Message(db.Model):
    """Message model for storing individual messages in a chat"""
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def to_dict(self):
        """Convert message to dictionary for JSON response"""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'sender': self.sender,
            'text': self.text,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender}>'