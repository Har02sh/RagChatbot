import requests
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
from transformers import AutoTokenizer

class RAGChatbot:
    def __init__(self, collection_name="myRag", qdrant_host="localhost", qdrant_port=6333):
        self.collection_name = collection_name
        self.tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)

        if not self.client.collection_exists(self.collection_name):
            raise Exception(f"Collection '{self.collection_name}' does not exist. Please create it first.")

        collection_count = self.client.count(self.collection_name)
        print(f"[INFO] Collection '{self.collection_name}' exists with {collection_count.count} documents.")

        # Initialize embedding models
        self.dense_embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
        self.bm25_embedding_model = SparseTextEmbedding("Qdrant/bm25")
        self.late_interaction_embedding_model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")

    def _embed_query(self, query):
        dense_vector = next(self.dense_embedding_model.query_embed(query))
        sparse_vector = next(self.bm25_embedding_model.query_embed(query))
        late_vector = next(self.late_interaction_embedding_model.query_embed(query))
        return dense_vector, sparse_vector, late_vector

    def _retrieve_context(self, dense_vector, sparse_vector, late_vector):
        prefetch = [
            models.Prefetch(
                query=dense_vector,
                using="all-MiniLM-L6-v2",
                limit=10,
            ),
            models.Prefetch(
                query=models.SparseVector(**sparse_vector.as_object()),
                using="bm25",
                limit=10,
            ),
        ]

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=late_vector,
            using="colbertv2.0",
            prefetch=prefetch,
            limit=5,
            with_payload=True
        )

        context_docs = [
            point.payload.get("text", str(point.payload)) for point in results.points
        ]
        return "\n\n".join(context_docs)

    def _generate_answer_with_ollama(self, query, context, model="gemma3:4b"):
        prompt = f"Answer the question based on the following context:\n\n{context}\n\nQuestion: {query}\nAnswer:"
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json().get("response", "").strip()

    def answer_query(self, query):
        dense_vector, sparse_vector, late_vector = self._embed_query(query)
        context = self._retrieve_context(dense_vector, sparse_vector, late_vector)
        return self._generate_answer_with_ollama(query, context)
    
    def summarize_full_document(self, model="gemma3:4b", max_tokens=120000):
        results = self.client.scroll(
            collection_name=self.collection_name,
            limit=1000,
            with_payload=True
        )

        all_chunks = [point.payload.get("text", str(point.payload)) for point in results[0]]

        document_text = ""
        total_tokens = 0

        for chunk in all_chunks:
            tokens = len(self.tokenizer.encode(chunk))
            if total_tokens + tokens <= max_tokens:
                document_text += chunk + "\n\n"
                total_tokens += tokens
            else:
                break

        prompt = f"Summarize the following document:\n\n{document_text}\n\nSummary:"
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )

        return response.json().get("response", "").strip()


# --- Usage Example ---

if __name__ == "__main__":
    rag_bot = RAGChatbot()

    while True:
        user_query = input("\nEnter your query (or type 'exit'): ")
        if user_query.lower() == "exit":
            break

        print("\n[GENERATED ANSWER]")
        print(rag_bot.answer_query(user_query))
