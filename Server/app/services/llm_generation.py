import requests
import json
from typing import List, Dict, Any, Optional
from qdrant_retriever import QdrantRetriever

class GemmaGenerator:
    
    def __init__(self, model_name: str = "gemma", api_base: str = "http://localhost:11434"):
        self.model_name = model_name
        self.api_base = api_base.rstrip("/")
        self.generate_endpoint = f"{self.api_base}/api/generate"
        
    def _build_prompt(self, query: str, contexts: List[Dict], system_prompt: Optional[str] = None) -> str:
        if system_prompt is None:
            system_prompt = (
                "You are a helpful assistant. Answer the user's question based on the provided context. "
                "If the context doesn't contain relevant information, say that you don't know. "
                "Keep your answers concise and accurate."
            )
            
        # Extract text from contexts
        context_texts = []
        for i, context in enumerate(contexts):
            # Extract text from payload, assuming 'text' or 'content' key exists
            if 'text' in context:
                context_texts.append(f"Context {i+1}:\n{context['text']}")
            elif 'content' in context:
                context_texts.append(f"Context {i+1}:\n{context['content']}")
            else:
                # If no text/content field exists, use the whole payload
                context_texts.append(f"Context {i+1}:\n{json.dumps(context)}")
        
        formatted_context = "\n\n".join(context_texts)
        
        # Build the complete prompt - Gemma format
        prompt = f"""<system>
        {system_prompt}

        Here is the context information to help answer the user's question:

        {formatted_context}
        </system>

        <user>
        {query}
        </user>

        <assistant>
        """
        
        return prompt
        
    def generate(self, 
                query: str, 
                contexts: List[Dict], 
                system_prompt: Optional[str] = None,
                temperature: float = 0.7, 
                max_tokens: int = 1024) -> Dict[str, Any]:
        prompt = self._build_prompt(query, contexts, system_prompt)
        
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
                      contexts: List[Dict],
                      system_prompt: Optional[str] = None,
                      temperature: float = 0.7, 
                      max_tokens: int = 1024):
        """
        Stream a response from the Gemma model through Ollama.
        
        Args:
            query: The user's question
            contexts: List of context dictionaries from the retrieval step
            system_prompt: Optional system prompt to guide model behavior
            temperature: Controls randomness in the output (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Yields:
            Text chunks as they are generated
        """
        prompt = self._build_prompt(query, contexts, system_prompt)
        
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


def main():

    retriever = QdrantRetriever(
        persistence_path="/Users/harshvardhan/CollegeProject/RAG2/Qdrant",
        collection_name="myRag"
    )
    generator = GemmaGenerator(model_name="gemma3:4b")
    

    while True:
        query = input("Enter your query: ")
        if query.lower() == "exit":
            break
        
        contexts = retriever.retrieve(query)
    
        print("\n[GENERATING RESPONSE...]")
    
        # Non-streaming version
        result = generator.generate(query=query, contexts=contexts)
        print(f"\n[ANSWER]\n{result['response']}")
        print(f"\n[TOKENS USED] {result['total_tokens']}")


if __name__ == "__main__":
    main()