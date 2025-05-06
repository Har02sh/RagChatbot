from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
from typing import List, Dict, Any, Optional


class QdrantRetriever:
    def __init__(self, persistence_path: str, collection_name: str):
        self.persistence_path = persistence_path
        self.collection_name = collection_name
        
        # Initialize embedding models
        self.dense_embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
        self.bm25_embedding_model = SparseTextEmbedding("Qdrant/bm25")
        self.late_interaction_embedding_model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")
        
        # Initialize Qdrant client
        self.client = QdrantClient(path=persistence_path)
        
        # Check if collection exists
        self._check_collection()
    
    def _check_collection(self) -> None:
        if not self.client.collection_exists(self.collection_name):
            print(f"[INFO] Collection '{self.collection_name}' does not exist. Please create it first.")
        else:
            collection_count = self.client.count(self.collection_name)
            print(f"[INFO] Collection '{self.collection_name}' exists with {collection_count}.")
    
    def retrieve(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        # Create query embeddings
        dense_query_vector = next(self.dense_embedding_model.query_embed(query))
        sparse_query_vector = next(self.bm25_embedding_model.query_embed(query))
        late_query_vector = next(self.late_interaction_embedding_model.query_embed(query))
        
        # Set up prefetching for hybrid search
        prefetch = [
            models.Prefetch(
                query=dense_query_vector,
                using="all-MiniLM-L6-v2",
                limit=20,
            ),
            models.Prefetch(
                query=models.SparseVector(**sparse_query_vector.as_object()),
                using="bm25",
                limit=20,
            ),
        ]
        
        # Perform the query
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=late_query_vector,
            using="colbertv2.0",
            prefetch=prefetch,
            limit=limit,
            with_payload=True
        )
        
        # Extract payloads from results
        contexts = [point.payload for point in results.points]
        return contexts
    
    def get_context_string(self, query: str, limit: int = 10) -> str:
        contexts = self.retrieve(query, limit)
        
        if not contexts:
            return "No relevant information found."
            
        context_string = "\n\n".join([
            f"Document {i+1}:\n{self._format_payload(doc)}" 
            for i, doc in enumerate(contexts)
        ])
        
        return context_string
    
    def _format_payload(self, payload: Dict[str, Any]) -> str:
        """Format a payload into a readable string."""
        # This can be customized based on your payload structure
        # Here's a simple implementation that works with any payload
        return "\n".join([f"{key}: {value}" for key, value in payload.items()])


# Example usage
if __name__ == "__main__":
    # Initialize the retriever
    retriever = QdrantRetriever(
        persistence_path="/Users/harshvardhan/CollegeProject/RAG2/Qdrant",
        collection_name="myRag"
    )
    
    # Interactive query loop
    while True:
        query = input("Enter your query: ")
        if query.lower() == "exit":
            break
        
        # Get contexts
        contexts = retriever.retrieve(query)
        
        print("\n[RESULTS]")
        print(len(contexts))
        for context in contexts:
            print(context)
            print("--"*20)
        
        # Example of getting a formatted context string for prompts
        # context_string = retriever.get_context_string(query)
        # print(f"\n[CONTEXT STRING FOR PROMPT]\n{context_string}")