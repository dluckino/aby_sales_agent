import chromadb

client = chromadb.PersistentClient(path="data/chroma")
collection = client.get_or_create_collection("knowledge")

def search_knowledge_base(query, n_results=3, category=None):
    where = {"source": category} if category else None
    res = collection.query(query_texts=[query], n_results=n_results, where=where)
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]

    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(docs, metas, dists)
    ]

if __name__ == "__main__":
    while True:
        query = input("query> ")
        if not query.strip():
            break
        for hit in search_knowledge_base(query):
            print(f"\n[{hit['distance']:.3f}] {hit['metadata']['title']}")
            print(hit['text'])