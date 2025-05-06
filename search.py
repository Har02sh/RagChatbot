from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding

dense_embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
bm25_embedding_model = SparseTextEmbedding("Qdrant/bm25")
late_interaction_embedding_model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")

persistence_path = r"/Users/harshvardhan/CollegeProject/RAG2/Qdrant"
collection_name = "myRag"
client = QdrantClient(path=persistence_path)
if not client.collection_exists(collection_name):
    print(f"[INFO] Collection '{collection_name}' does not exist. Please create it first.")
else:
    collectionCount = client.count(collection_name)
    print(f"[INFO] Collection '{collection_name}' exists with {collectionCount}.")

while True:
    query = input("Enter your query: ")
    if query.lower() == "exit":
        break
    
    # Create query embeddings
    dense_query_vector = next(dense_embedding_model.query_embed(query))
    sparse_query_vector = next(bm25_embedding_model.query_embed(query))
    late_query_vector = next(late_interaction_embedding_model.query_embed(query))

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
    results = client.query_points(
        collection_name=collection_name,
        query=late_query_vector,
        using="colbertv2.0",
        prefetch=prefetch,
        limit=10,
        with_payload=True
    )

    print("\n[RESULTS]")
    print(len(results.points))
    for point in results.points:
        print(point.payload)
        print("--"*20)
