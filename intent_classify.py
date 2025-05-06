import json
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import time
import backoff

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("intent_classifier")

class DocumentIntent(str, Enum):
    """Enumeration of possible document-related intents."""
    QUESTION_ANSWERING = "Question Answering"
    SUMMARIZE_FULL = "Summarize Full Document"
    SUMMARIZE_SECTION = "Summarize Section"
    FIND_SECTION = "Find Section"
    COMPARE_SECTIONS = "Compare Sections"
    OTHER = "Other"

class IntentClassifier:
    """A production-ready intent classifier using Ollama LLM."""
    
    def __init__(
        self,
        ollama_api_url: str = "http://localhost:11434/api/generate",
        model_name: str = "gemma3:4b",
        max_retries: int = 3,
        timeout: int = 30,
        temperature: float = 0.1,
    ):
        """
        Initialize the intent classifier.
        
        Args:
            ollama_api_url: URL for the Ollama API
            model_name: Name of the model to use
            max_retries: Maximum number of retries for API calls
            timeout: Timeout in seconds for API calls
            temperature: Temperature parameter for the model (lower = more deterministic)
        """
        self.ollama_api_url = ollama_api_url
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout = timeout
        self.temperature = temperature
        
        # Test connection to Ollama
        self._test_connection()
        
    def _test_connection(self) -> None:
        """Test the connection to Ollama API."""
        try:
            requests.post(
                self.ollama_api_url,
                json={"model": self.model_name, "prompt": "test", "stream": False},
                timeout=self.timeout
            )
            logger.info(f"Successfully connected to Ollama API using model {self.model_name}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama API: {e}")
            raise ConnectionError(f"Could not connect to Ollama API at {self.ollama_api_url}")
    
    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, json.JSONDecodeError),
        max_tries=3,
        giveup=lambda e: isinstance(e, requests.exceptions.HTTPError) and e.response.status_code < 500
    )
    def _call_ollama(self, prompt: str) -> str:
        """
        Call the Ollama API with backoff retry logic.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            The model's response as a string
        """
        try:
            response = requests.post(
                self.ollama_api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": self.temperature,
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise
    
    def _build_classification_prompt(self, user_input: str) -> str:
        """
        Build a prompt for intent classification.
        
        Args:
            user_input: The user's input to classify
            
        Returns:
            A formatted prompt for the model
        """
        return f"""
        Your task is to classify the user's intent when interacting with a document.
        Analyze the following user input and classify it into EXACTLY ONE of these categories:
        - Question Answering: User wants to ask a specific question about the content
        - Summarize Full Document: User wants a summary of the entire document
        - Summarize Section: User wants a summary of a specific section
        - Find Section: User wants to locate or navigate to a specific section
        - Compare Sections: User wants to compare multiple sections
        - Other: User's intent doesn't fit any of the above categories
        
        User input: "{user_input}"
        
        Return ONLY the category name without any explanation or additional text.
        """
    
    def classify(self, user_input: str) -> Tuple[DocumentIntent, float]:
        """
        Classify the user's intent.
        
        Args:
            user_input: The user's input to classify
            
        Returns:
            A tuple of (detected intent, confidence score)
        """
        if not user_input or not user_input.strip():
            logger.warning("Received empty user input")
            return DocumentIntent.OTHER, 0.0
            
        start_time = time.time()
        
        try:
            prompt = self._build_classification_prompt(user_input)
            response = self._call_ollama(prompt)
            
            # Clean up response (remove whitespace, quotes, etc.)
            cleaned_response = response.strip().strip('"').strip("'")
            
            # Map to enum or default to OTHER
            try:
                intent = DocumentIntent(cleaned_response)
                confidence = 0.9  # High confidence for exact match
            except ValueError:
                # Try to find closest match
                for intent_type in DocumentIntent:
                    if intent_type.value.lower() in cleaned_response.lower():
                        intent = intent_type
                        confidence = 0.7  # Medium confidence for partial match
                        break
                else:
                    logger.warning(f"Could not map response to intent: '{cleaned_response}'")
                    intent = DocumentIntent.OTHER
                    confidence = 0.5  # Low confidence
            
            elapsed_time = time.time() - start_time
            logger.info(f"Intent classification completed in {elapsed_time:.2f}s: {intent.value} ({confidence:.2f})")
            
            return intent, confidence
            
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            # Fallback to OTHER with low confidence in case of errors
            return DocumentIntent.OTHER, 0.0
    
    def classify_with_details(self, user_input: str) -> Dict[str, Any]:
        """
        Classify the user's intent with detailed response.
        
        Args:
            user_input: The user's input to classify
            
        Returns:
            A dictionary containing the classification details
        """
        intent, confidence = self.classify(user_input)
        
        return {
            "intent": intent.value,
            "confidence": confidence,
            "input": user_input,
            "timestamp": time.time(),
            "model": self.model_name,
        }

# Example usage
def get_intent_for_rag(user_query: str, ollama_url: str = "http://localhost:11434/api/generate") -> Dict[str, Any]:
    """
    Helper function to classify intent for RAG pipeline routing.
    
    Args:
        user_query: The user's query to classify
        ollama_url: URL for the Ollama API
        
    Returns:
        Classification results
    """
    classifier = IntentClassifier(ollama_api_url=ollama_url)
    result = classifier.classify_with_details(user_query)
    
    # Additional RAG-specific processing could be added here
    
    return result

# Example of how to use this in a RAG pipeline
def process_user_query(user_query: str) -> Dict[str, Any]:
    """
    Process a user query by first classifying intent, then routing to appropriate RAG handler.
    
    Args:
        user_query: The user's query
        
    Returns:
        Response from the appropriate RAG handler
    """
    # Classify intent
    intent_result = get_intent_for_rag(user_query)
    intent = intent_result["intent"]
    
    # Route based on intent
    if intent == DocumentIntent.QUESTION_ANSWERING:
        # Call QA RAG pipeline
        return {"type": "qa_response", "data": {"query": user_query, "intent": intent}}
    
    elif intent == DocumentIntent.SUMMARIZE_FULL:
        # Call document summarization pipeline
        return {"type": "summary_response", "data": {"full_document": True, "intent": intent}}
    
    elif intent == DocumentIntent.SUMMARIZE_SECTION:
        # Call section summarization pipeline
        return {"type": "summary_response", "data": {"section": True, "intent": intent}}
    
    elif intent == DocumentIntent.FIND_SECTION:
        # Call section retrieval pipeline
        return {"type": "section_response", "data": {"find": True, "intent": intent}}
    
    elif intent == DocumentIntent.COMPARE_SECTIONS:
        # Call section comparison pipeline
        return {"type": "comparison_response", "data": {"intent": intent}}
    
    else:
        # Handle other intents or fallback
        return {"type": "general_response", "data": {"intent": intent}}

if __name__ == "__main__":
    # Example usage
    test_query = "summarise"
    result = process_user_query(test_query)
    print(json.dumps(result, indent=2))