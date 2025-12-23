import os
import numpy as np
import faiss
import json
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)

index = None
metas = []

def get_embedding(text):
    vector = model.encode([text], normalize_embeddings=True)[0]
    return vector.astype("float32")

def init_index(dim=384):
    global index
    index = faiss.IndexFlatIP(dim)
    return index

def upsert_documents(docs):
    global index, metas

    if index is None:
        init_index()

    vectors = []
    for d in docs:
        emb = get_embedding(d["text"])
        vectors.append(emb)
        metas.append(d)

    vectors = np.array(vectors).astype("float32")
    index.add(vectors)

def semantic_search(query, top_k=5):
    global index, metas
    if index is None:
        return []

    q_emb = get_embedding(query).reshape(1, -1)
    D, I = index.search(q_emb, top_k)

    results = []
    for idx in I[0]:
        if idx < len(metas):
            results.append(metas[idx])
    return results

def load_seed(path="data/seed_docs.json"):
    if os.path.exists(path):
        docs = json.load(open(path, "r"))
        upsert_documents(docs)
