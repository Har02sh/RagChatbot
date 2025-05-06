import os
import re
from typing import List, Dict, Any, Union, Optional
import json
import logging

import PyPDF2
import spacy
from spacy.language import Language

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    nlp = spacy.load("en_core_web_md")
    logger.info("Loaded spaCy model: en_core_web_md")
except OSError:
    logger.warning("spaCy model not found. Downloading model...")
    from spacy.cli import download
    download("en_core_web_md")
    nlp = spacy.load("en_core_web_md")
    logger.info("Downloaded and loaded spaCy model: en_core_web_md")


def extract_text_from_pdf(pdf_path: str) -> str:
    logger.info(f"Extracting text from PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            logger.info(f"PDF has {num_pages} pages")
            
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                text += page_text + "\n\n"
                
        logger.info(f"Successfully extracted {len(text)} characters from PDF")
        return text
    
    except PyPDF2.errors.PdfReadError as e:
        logger.error(f"Error reading PDF file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting text from PDF: {e}")
        raise


def preprocess_text(text: str) -> str:
    """
    Preprocess the extracted text to clean and normalize it.
    
    Args:
        text: Raw text extracted from PDF
        
    Returns:
        Preprocessed text
    """
    logger.info("Preprocessing extracted text")
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove page numbers (common patterns)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    
    # Remove footer/header patterns (customize based on your PDFs)
    text = re.sub(r'\n.{0,50}Page \d+ of \d+.{0,50}\n', '\n', text)
    
    # Replace unicode characters that might cause issues
    text = text.replace('\u2019', "'")  # Smart quotes
    text = text.replace('\u2018', "'")  # Smart quotes
    text = text.replace('\u201c', '"')  # Smart double quotes
    text = text.replace('\u201d', '"')  # Smart double quotes
    text = text.replace('\u2014', '-')  # Em dash
    text = text.replace('\u2013', '-')  # En dash
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    logger.info(f"Text preprocessing complete, resulting in {len(text)} characters")
    return text


def chunk_text_with_spacy(text: str, 
                         chunk_size: int = 1000, 
                         chunk_overlap: int = 200,
                         respect_sentences: bool = True) -> List[Dict[str, Any]]:
    """
    Chunk text using spaCy's NLP capabilities. This method tries to create 
    semantically meaningful chunks by respecting sentence boundaries.
    
    Args:
        text: Preprocessed text to chunk
        chunk_size: Target size for each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        respect_sentences: Whether to respect sentence boundaries
        
    Returns:
        List of dictionaries containing chunks with metadata
    """
    logger.info(f"Chunking text with spaCy (chunk_size={chunk_size}, overlap={chunk_overlap})")
    
    # Process the text with spaCy
    doc = nlp(text)
    
    chunks = []
    current_chunk = []
    current_chunk_size = 0
    
    if respect_sentences:
        # Chunk by respecting sentence boundaries
        for sent in doc.sents:
            sent_text = sent.text.strip()
            sent_size = len(sent_text)
            
            # If adding this sentence would exceed the chunk size and we already have content,
            # store the current chunk and start a new one
            if current_chunk_size + sent_size > chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "sentences": len(current_chunk)
                })
                
                # Start a new chunk with overlap
                overlap_chunk = []
                overlap_size = 0
                for s in reversed(current_chunk):
                    if overlap_size + len(s) <= chunk_overlap:
                        overlap_chunk.insert(0, s)
                        overlap_size += len(s) + 1  # +1 for the space
                    else:
                        break
                
                current_chunk = overlap_chunk
                current_chunk_size = overlap_size
            
            # Add the current sentence
            current_chunk.append(sent_text)
            current_chunk_size += sent_size + 1  # +1 for the space
    
    else:
        # Simple chunking by characters
        start_idx = 0
        while start_idx < len(text):
            end_idx = min(start_idx + chunk_size, len(text))
            
            # Try to find a natural breaking point (whitespace)
            if end_idx < len(text) and not text[end_idx].isspace():
                # Look for the last whitespace within the chunk
                last_space = text.rfind(' ', start_idx, end_idx)
                if last_space > start_idx:
                    end_idx = last_space
            
            chunk_text = text[start_idx:end_idx].strip()
            chunks.append({
                "text": chunk_text,
                "size": len(chunk_text),
                "start_char": start_idx,
                "end_char": end_idx
            })
            
            # Move to the next chunk with overlap
            start_idx = end_idx - chunk_overlap
            if start_idx < 0:
                start_idx = 0
    
    # Don't forget to add the last chunk if it's not empty
    if current_chunk and respect_sentences:
        chunk_text = " ".join(current_chunk)
        chunks.append({
            "text": chunk_text,
            "size": len(chunk_text),
            "sentences": len(current_chunk)
        })
    
    # Add metadata to each chunk
    for i, chunk in enumerate(chunks):
        chunk["id"] = i
        chunk["entities"] = extract_entities_from_text(chunk["text"])
        chunk["keywords"] = extract_keywords_from_text(chunk["text"])
    
    logger.info(f"Created {len(chunks)} chunks from text")
    return chunks


def extract_entities_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract named entities from text using spaCy.
    
    Args:
        text: Text to extract entities from
        
    Returns:
        List of entities with their types
    """
    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} 
                for ent in doc.ents]
    return entities


def extract_keywords_from_text(text: str, top_n: int = 5) -> List[str]:
    """
    Extract keywords from text using spaCy.
    
    Args:
        text: Text to extract keywords from
        top_n: Number of keywords to extract
        
    Returns:
        List of keywords
    """
    doc = nlp(text)
    
    # Filter for nouns, proper nouns, and adjectives
    keywords = [token.lemma_ for token in doc 
                if token.pos_ in ("NOUN", "PROPN", "ADJ") 
                and not token.is_stop 
                and len(token.lemma_) > 2]
    
    # Count occurrences
    keyword_counts = {}
    for keyword in keywords:
        if keyword in keyword_counts:
            keyword_counts[keyword] += 1
        else:
            keyword_counts[keyword] = 1
    
    # Sort by frequency
    sorted_keywords = sorted(keyword_counts.items(), 
                             key=lambda x: x[1], 
                             reverse=True)
    
    # Return top N keywords
    return [k for k, _ in sorted_keywords[:top_n]]


def process_pdf(pdf_path: str, 
               output_path: Optional[str] = None,
               chunk_size: int = 1000,
               chunk_overlap: int = 200,
               respect_sentences: bool = True) -> List[Dict[str, Any]]:
    """
    Process a PDF file: extract text, preprocess, and chunk.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Path to save the chunks as JSON (optional)
        chunk_size: Target size for each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        respect_sentences: Whether to respect sentence boundaries
        
    Returns:
        List of text chunks with metadata
    """
    logger.info(f"Processing PDF file: {pdf_path}")
    
    # Extract text from PDF
    raw_text = extract_text_from_pdf(pdf_path)
    
    # Preprocess text
    processed_text = preprocess_text(raw_text)
    
    # Chunk text
    chunks = chunk_text_with_spacy(
        processed_text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        respect_sentences=respect_sentences
    )
    
    # Add metadata about the source
    for chunk in chunks:
        chunk["source"] = {
            "file": os.path.basename(pdf_path),
            "path": pdf_path,
            "total_chunks": len(chunks)
        }
    
    # Save to output file if specified
    if output_path:
        logger.info(f"Saving chunks to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    logger.info(f"PDF processing complete. Generated {len(chunks)} chunks.")
    return chunks


# Example usage function for direct script execution
def process_pdf_folder(folder_path: str, 
                      output_folder: str,
                      chunk_size: int = 1000,
                      chunk_overlap: int = 200,
                      respect_sentences: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process all PDF files in a folder.
    
    Args:
        folder_path: Path to folder containing PDF files
        output_folder: Path to folder to save output JSON files
        chunk_size: Target size for each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        respect_sentences: Whether to respect sentence boundaries
        
    Returns:
        Dictionary mapping file names to their chunks
    """
    logger.info(f"Processing all PDFs in folder: {folder_path}")
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logger.info(f"Created output folder: {output_folder}")
    
    results = {}
    
    # Process each PDF file in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(folder_path, filename)
            output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}.json")
            
            try:
                chunks = process_pdf(
                    pdf_path=pdf_path,
                    output_path=output_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    respect_sentences=respect_sentences
                )
                results[filename] = chunks
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
    
    return results


if __name__ == "__main__":
    # Example usage
    pdf_path = r"/Users/harshvardhan/CollegeProject/RAG2/Biological Classification.pdf"
    output_path = "./example_chunks.json"
    
    chunks = process_pdf(
        pdf_path=pdf_path,
        output_path=output_path,
        chunk_size=1024,
        chunk_overlap=256,
        respect_sentences=True
    )
    
    print(f"Processed PDF and generated {len(chunks)} chunks.")