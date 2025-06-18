from .extract import PDFRAGProcessor
from .index import QdrantRAGUploader
from .generation import RAGChatbot
from .intent import IntentClassifier
import os 

qdrant_path = r"/Users/harshvardhan/RagChatbot/instance/Qdrant"
os.makedirs(qdrant_path, exist_ok=True)

processor = PDFRAGProcessor(
        chunk_size=1000,
        chunk_overlap=200,
        output_dir="./my_rag_chunks"
    )



