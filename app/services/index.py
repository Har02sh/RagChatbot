import json
import uuid
import os
from tqdm import tqdm
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding


class QdrantRAGUploader:
    def __init__(self, file_path, collection_name="myRag", host="localhost", port=6333, timeout=60.0):
        self.file_path = file_path
        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port, timeout=timeout)
        self.texts = []
        self.chunks = []

        # Initialize embedding models
        self.dense_embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
        self.bm25_embedding_model = SparseTextEmbedding("Qdrant/bm25")
        self.late_interaction_embedding_model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")

    def load_chunks(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
            self.texts = [chunk["content"] for chunk in self.chunks]
            print(f"[INFO] {len(self.chunks)} chunks loaded from file")

    def setup_collection(self):
        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"[INFO] Collection '{self.collection_name}' deleted successfully.")

        self.client.create_collection(
            self.collection_name,
            vectors_config={
                "all-MiniLM-L6-v2": models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE,
                ),
                "colbertv2.0": models.VectorParams(
                    size=128,
                    distance=models.Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM,
                    ),
                    hnsw_config=models.HnswConfigDiff(m=0)
                ),
            },
            sparse_vectors_config={
                "bm25": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                )
            }
        )
        print(f"[INFO] Collection '{self.collection_name}' created successfully.")

    def embed_texts(self):
        print("[INFO] Generating embeddings...")
        self.dense_vecs = list(self.dense_embedding_model.embed(doc for doc in self.texts))
        self.sparse_vecs = list(self.bm25_embedding_model.embed(doc for doc in self.texts))
        self.colbert_vecs = list(self.late_interaction_embedding_model.embed(doc for doc in self.texts))

    def insert_into_qdrant(self, batch_size=10):
        print(f"[INFO] Inserting {len(self.chunks)} points into Qdrant in batches of {batch_size}...")
        for i in tqdm(range(0, len(self.chunks), batch_size), desc="Uploading batches"):
            batch_points = []
            for j in range(i, min(i + batch_size, len(self.chunks))):
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    payload={"text": self.chunks[j]["content"]},
                    vector={
                        "all-MiniLM-L6-v2": self.dense_vecs[j].tolist(),
                        "bm25": self.sparse_vecs[j].as_object(),
                        "colbertv2.0": self.colbert_vecs[j].tolist(),
                    }
                )
                batch_points.append(point)
            self.client.upsert(collection_name=self.collection_name, points=batch_points)
        print("[SUCCESS] All data inserted into Qdrant successfully.")

    def run(self):
        try:
            self.load_chunks()
            self.setup_collection()
            self.embed_texts()
            self.insert_into_qdrant()
        except Exception as e:
            print(f"[ERROR] {e}")
            return False
        return True


# Usage
if __name__ == "__main__":
    uploader = QdrantRAGUploader(
        file_path="/Users/harshvardhan/CollegeProject/RAG2/my_rag_chunks/Chemical Coordination_chunks.json"
    )
    uploader.run()
