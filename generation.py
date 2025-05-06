import requests
import json
import os
from typing import List, Dict, Any, Optional

class GraniteGenerator:
    """
    A class for generating responses using the Granite model through Ollama API.
    This class handles the generation part of a RAG (Retrieval-Augmented Generation) system.
    """
    
    def __init__(self, model_name: str = "granite", api_base: str = "http://localhost:11434"):
        """
        Initialize the GraniteGenerator with the specified model and API base URL.
        
        Args:
            model_name: The name of the Granite model to use (default: "granite")
            api_base: The base URL for the Ollama API (default: "http://localhost:11434")
        """
        self.model_name = model_name
        self.api_base = api_base.rstrip("/")
        self.generate_endpoint = f"{self.api_base}/api/generate"
        
    def _build_prompt(self, query: str, context: List[str], system_prompt: Optional[str] = None) -> str:
        """
        Build a prompt for the model by combining the context and query.
        
        Args:
            query: The user query
            context: List of context snippets retrieved from the vector store
            system_prompt: Optional system prompt to guide the model's behavior
            
        Returns:
            A formatted prompt string
        """
        # Default system prompt if none provided
        if system_prompt is None:
            system_prompt = (
                "You are a helpful assistant. Answer the user's question based on the provided context. "
                "If the context doesn't contain relevant information, say that you don't know. "
                "Keep your answers concise and accurate."
            )
            
        # Format the context into a single string
        formatted_context = "\n\n".join([f"Context snippet {i+1}:\n{snippet}" for i, snippet in enumerate(context)])
        
        # Build the complete prompt
        prompt = f"""<|system|>
{system_prompt}

Here is the context information to help answer the user's question:

{formatted_context}
<|user|>
{query}
<|assistant|>"""
        
        return prompt
        
    def generate(self, 
                query: str, 
                context: List[str], 
                system_prompt: Optional[str] = None,
                temperature: float = 0.7, 
                max_tokens: int = 1024) -> Dict[str, Any]:
        """
        Generate a response using the Granite model with Ollama.
        
        Args:
            query: The user's question
            context: List of context snippets from the retrieval step
            system_prompt: Optional system prompt to guide the model's behavior
            temperature: Controls randomness in the output (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            A dictionary containing the generated response and metadata
        """
        prompt = self._build_prompt(query, context, system_prompt)
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(self.generate_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            
            return {
                "response": result.get("response", ""),
                "input_tokens": result.get("prompt_eval_count", 0),
                "output_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                "model": self.model_name
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Error calling Ollama API: {str(e)}",
                "response": "Sorry, I encountered an error while generating a response."
            }
    
    def stream_generate(self, 
                      query: str, 
                      context: List[str],
                      system_prompt: Optional[str] = None,
                      temperature: float = 0.7, 
                      max_tokens: int = 1024):
        """
        Stream a response from the Granite model through Ollama.
        
        Args:
            query: The user's question
            context: List of context snippets from the retrieval step
            system_prompt: Optional system prompt to guide model behavior
            temperature: Controls randomness in the output (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Yields:
            Text chunks as they are generated
        """
        prompt = self._build_prompt(query, context, system_prompt)
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        try:
            with requests.post(self.generate_endpoint, json=payload, stream=True) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            continue
                            
        except requests.exceptions.RequestException as e:
            yield f"\nError: {str(e)}"


# Example usage
def main():
    # Example context from retrieval step
    retrieved_context = [
        "Granite is a language model developed by Databricks. It's an open-source model available in various sizes.",
        "RAG (Retrieval-Augmented Generation) is a technique that enhances LLM responses by first retrieving relevant information from a knowledge base.",
        "Ollama is a tool for running LLMs locally. It supports various models including Granite.",
    ]
    
    # Initialize the generator
    generator = GraniteGenerator(model_name="granite")
    
    # Generate a response
    query = "How can I use Granite in a RAG system?"
    result = generator.generate(query=query, context=retrieved_context)
    
    print(f"Query: {query}")
    print(f"Response: {result['response']}")
    print(f"Token usage: {result['total_tokens']}")
    
    # Example of streaming response
    print("\nStreaming response:")
    query = "What are the benefits of RAG systems?"
    print(f"Query: {query}")
    print("Response: ", end="", flush=True)
    
    for chunk in generator.stream_generate(query=query, context=retrieved_context):
        print(chunk, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    main()