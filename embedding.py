from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
from qdrant_client import QdrantClient, models
import json
import uuid
from qdrant_client.models import PointStruct, SparseVector
import os

# Load chunks from the file
texts = None
with open(r"/Users/harshvardhan/CollegeProject/RAG2/example_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)
    texts = [chunk["text"] for chunk in chunks]
    print(len(chunks), "chunks loaded from file")

# Initialize embedding models
dense_embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
bm25_embedding_model = SparseTextEmbedding("Qdrant/bm25")
late_interaction_embedding_model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")

# Connect to Qdrant client
persistence_path = r"/Users/harshvardhan/CollegeProject/RAG2/Qdrant"
os.makedirs(persistence_path, exist_ok=True)
client = QdrantClient(path=persistence_path)
collection_name = "myRag"

# Create collection if it doesn't exist
if not client.collection_exists(collection_name):
    client.create_collection(
        "myRag",
        vectors_config={
            "all-MiniLM-L6-v2": models.VectorParams(
                size=384,
                distance=models.Distance.COSINE,
            ),
            "colbertv2.0": models.VectorParams(
                size=384,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM,
                )
            ),
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            )
        }
    )
    print(f"[INFO] Collection '{collection_name}' created successfully.")
else:
    print(f"[INFO] Collection '{collection_name}' already exists. Skipping creation.")


# Embed the text using the models
print("[INFO] Generating dense, sparse, and late interaction embeddings...")
dense_vecs = list(dense_embedding_model.passage_embed(texts))
sparse_vecs = list(bm25_embedding_model.passage_embed(texts))
colbert_vecs = list(late_interaction_embedding_model.passage_embed(texts))

# Sanity check for colbert vectors
if isinstance(colbert_vecs[0][0], list):  # list of lists = multi-vector
    print("[INFO] ColBERT embeddings are multi-vector representations.")
else:
    print("[WARNING] ColBERT output appears to be flat — check your model config.")

# Prepare points for insertion into Qdrant
points = []
for i, chunk in enumerate(chunks):
    point = PointStruct(
        id=str(uuid.uuid4()), 
        payload={
            "text": chunk["text"],
            "chunk_id": chunk["id"],
            "file": chunk["source"]["file"],
            "path": chunk["source"]["path"],
            "total_chunks": chunk["source"]["total_chunks"],
            "size": chunk["size"],
            "sentences": chunk["sentences"],
        },
        vector={
            "all-MiniLM-L6-v2": dense_vecs[i].tolist(),           # Ensure the vector is a list of floats
            "bm25": sparse_vecs[i].as_object(),           # Wrap sparse vector in SparseVector
            "colbertv2.0": colbert_vecs[i].tolist()               # Ensure the vector is a list of floats
        }
    )
    points.append(point)


print(f"[INFO] Inserting {len(points)} points into Qdrant collection '{collection_name}'...")
client.upsert(collection_name=collection_name, points=points)
print("[SUCCESS] Data inserted into Qdrant successfully.")