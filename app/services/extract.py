import os
import json
import pickle
from typing import List, Optional, Union
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


class PDFRAGProcessor:
    """
    A class to process PDF files for RAG (Retrieval-Augmented Generation).
    Extracts text from PDFs, chunks them, and saves for embedding.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        output_dir: str = "./my_rag_chunks"
    ):
        """
        Initialize the PDF RAG Processor.
        
        Args:
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Number of characters to overlap between chunks
            separators: Custom separators for text splitting
            output_dir: Directory to save chunk files
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or ["\n\n", "\n", " ", ""],
            length_function=len,
        )
        
        self.documents = []
        self.chunks = []
    
    def load_pdf(self, pdf_path: Union[str, Path]) -> List[Document]:
        """
        Load and extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of Document objects containing the extracted text
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"File must be a PDF: {pdf_path}")
        
        print(f"Loading PDF: {pdf_path}")
        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()
        
        # Add metadata
        for doc in documents:
            doc.metadata.update({
                'source_file': str(pdf_path),
                'file_name': pdf_path.name,
                'total_pages': len(documents)
            })
        
        self.documents.extend(documents)
        print(f"Loaded {len(documents)} pages from {pdf_path.name}")
        
        return documents
    

    
    def chunk_documents(self, documents: Optional[List[Document]] = None) -> List[Document]:
        """
        Split documents into smaller chunks for RAG processing.
        
        Args:
            documents: List of documents to chunk. If None, uses loaded documents.
            
        Returns:
            List of chunked Document objects
        """
        if documents is None:
            documents = self.documents
        
        if not documents:
            raise ValueError("No documents to chunk. Load PDFs first.")
        
        print(f"Chunking {len(documents)} documents...")
        
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'chunk_id': i,
                'chunk_size': len(chunk.page_content),
                'total_chunks': len(chunks)
            })
        
        self.chunks = chunks
        print(f"Created {len(chunks)} chunks")
        
        return chunks
    
    def save_chunks_json(self, filename: str = "chunks.json") -> str:
        """
        Save chunks to a JSON file.
        
        Args:
            filename: Name of the output JSON file
            
        Returns:
            Path to the saved file
        """
        if not self.chunks:
            raise ValueError("No chunks to save. Process documents first.")
        
        output_path = self.output_dir / filename
        
        # Convert chunks to serializable format
        chunks_data = []
        for chunk in self.chunks:
            chunks_data.append({
                'content': chunk.page_content,
                'metadata': chunk.metadata
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(chunks_data)} chunks to {output_path}")
        return str(output_path)
    
    def save_chunks_pickle(self, filename: str = "chunks.pkl") -> str:
        """
        Save chunks to a pickle file (preserves Document objects).
        
        Args:
            filename: Name of the output pickle file
            
        Returns:
            Path to the saved file
        """
        if not self.chunks:
            raise ValueError("No chunks to save. Process documents first.")
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'wb') as f:
            pickle.dump(self.chunks, f)
        
        print(f"Saved {len(self.chunks)} chunks to {output_path}")
        return str(output_path)
    
    def save_chunks_text(self, filename: str = "chunks.txt") -> str:
        """
        Save chunk contents to a text file (one chunk per line).
        
        Args:
            filename: Name of the output text file
            
        Returns:
            Path to the saved file
        """
        if not self.chunks:
            raise ValueError("No chunks to save. Process documents first.")
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, chunk in enumerate(self.chunks):
                f.write(f"--- Chunk {i+1} ---\n")
                f.write(f"Source: {chunk.metadata.get('source_file', 'Unknown')}\n")
                f.write(f"Page: {chunk.metadata.get('page', 'Unknown')}\n")
                f.write(f"Content:\n{chunk.page_content}\n\n")
        
        print(f"Saved {len(self.chunks)} chunks to {output_path}")
        return str(output_path)
    
    def get_chunk_texts(self) -> List[str]:
        """
        Get list of chunk texts for embedding.
        
        Returns:
            List of chunk text content
        """
        if not self.chunks:
            raise ValueError("No chunks available. Process documents first.")
        
        return [chunk.page_content for chunk in self.chunks]
    
    def get_chunk_metadata(self) -> List[dict]:
        """
        Get list of chunk metadata.
        
        Returns:
            List of chunk metadata dictionaries
        """
        if not self.chunks:
            raise ValueError("No chunks available. Process documents first.")
        
        return [chunk.metadata for chunk in self.chunks]
    
    def process_pdf_for_rag(
        self,
        pdf_path: Union[str, Path],
        save_format: str = "json"
    ) -> List[Document]:
        """
        Complete pipeline: load PDF, chunk, and save.
        
        Args:
            pdf_path: Path to PDF file
            save_format: Format to save chunks ('json', 'pickle', 'text', or 'all')
            
        Returns:
            List of chunked Document objects ready for embedding
        """
        # Clear any previous data
        self.documents = []
        self.chunks = []
        
        # Load PDF
        self.load_pdf(pdf_path)
        
        # Chunk documents
        chunks = self.chunk_documents()
        
        # Save chunks
        pdf_name = Path(pdf_path).stem
        
        if save_format == "json" or save_format == "all":
            self.save_chunks_json("rag_chunks.json")
        
        if save_format == "pickle" or save_format == "all":
            self.save_chunks_pickle("rag_chunks.pkl")
        
        if save_format == "text" or save_format == "all":
            self.save_chunks_text("rag_chunks.txt")
        
        return chunks

    
    def load_chunks_from_file(self, file_path: Union[str, Path]) -> List[Document]:
        """
        Load previously saved chunks from file.
        
        Args:
            file_path: Path to the saved chunks file
            
        Returns:
            List of Document objects
        """
        file_path = Path(file_path)
        
        if file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
            
            chunks = []
            for chunk_data in chunks_data:
                doc = Document(
                    page_content=chunk_data['content'],
                    metadata=chunk_data['metadata']
                )
                chunks.append(doc)
            
            self.chunks = chunks
            
        elif file_path.suffix == '.pkl':
            with open(file_path, 'rb') as f:
                self.chunks = pickle.load(f)
        
        else:
            raise ValueError("Unsupported file format. Use .json or .pkl files.")
        
        print(f"Loaded {len(self.chunks)} chunks from {file_path}")
        return self.chunks
    
    def get_summary_stats(self) -> dict:
        """
        Get summary statistics about the processed documents and chunks.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.chunks:
            return {"error": "No chunks processed yet"}
        
        chunk_sizes = [len(chunk.page_content) for chunk in self.chunks]
        
        stats = {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "total_characters": sum(chunk_sizes),
            "chunk_size_setting": self.chunk_size,
            "chunk_overlap_setting": self.chunk_overlap
        }
        
        return stats


# Example usage
# if __name__ == "__main__":
#     # Initialize processor
#     processor = PDFRAGProcessor(
#         chunk_size=1000,
#         chunk_overlap=200,
#         output_dir="my_rag_chunks"
#     )
    
#     # Process single PDF only
#     try:
#         chunks = processor.process_pdf_for_rag(
#             pdf_path=r'/Users/harshvardhan/Downloads/Chemical Coordination.pdf',
#             save_format="json"  # Save in all formats
#         )
        
#         # Get chunks for embedding
#         chunk_texts = processor.get_chunk_texts()
#         chunk_metadata = processor.get_chunk_metadata()
        
#         print(f"Ready for embedding: {len(chunk_texts)} chunks")
#         print("Summary stats:", processor.get_summary_stats())
        
#         # Example: First few chunks
#         for i, text in enumerate(chunk_texts[:3]):
#             print(f"\nChunk {i+1} preview:")
#             print(text[:200] + "..." if len(text) > 200 else text)
            
#     except Exception as e:
#         print(f"Error: {e}")