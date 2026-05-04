"""Embedding and hybrid search"""
import os
import sys
import warnings
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

# Disable all Chroma telemetry and warnings
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"
warnings.filterwarnings("ignore")

import chromadb

from config.settings import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE, CHROMA_PATH, DENSE_TOP_K, SPARSE_WEIGHT, DENSE_WEIGHT, CHROMA_TELEMETRY_DISABLED

class EmbeddingService:
    def __init__(self):
        model_map = {"UAE-Large-V1": "WhereIsAI/UAE-Large-V1", "bge-large-zh-v1.5": "BAAI/bge-large-zh-v1.5"}
        model_path = model_map.get(EMBEDDING_MODEL, EMBEDDING_MODEL)
        try:
            self.model = SentenceTransformer(model_path, device="cuda")
        except:
            self.model = SentenceTransformer(model_path, device="cpu")

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, batch_size=EMBEDDING_BATCH_SIZE, convert_to_numpy=True).tolist() if texts else []

class VectorStore:
    def __init__(self):
        # Suppress telemetry
        os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"
        
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.client.get_or_create_collection(name="papers", metadata={"hnsw:space": "cosine"})

    def count(self) -> int:
        """Count papers stored in vector database"""
        return self.collection.count()

    def add_papers(self, papers: List[Dict]):
        """Add papers to vector store"""
        if papers:
            self.collection.add(
                ids=[p["id"] for p in papers],
                documents=[p["content"] for p in papers],
                metadatas=[{"title": p["title"], "source": p["source"], "link": p.get("link", "")} for p in papers],
            )

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        results = self.collection.query(query_texts=[query], n_results=top_k)
        return [{"id": results["ids"][0][i], "title": results["metadatas"][0][i]["title"], 
                 "source": results["metadatas"][0][i]["source"], "link": results["metadatas"][0][i]["link"],
                 "score": 1 - results["distances"][0][i]} for i in range(len(results["ids"][0]))]

class Retriever:
    def __init__(self, vectorstore: VectorStore):
        self.vectorstore = vectorstore
        self.bm25 = None
        self.papers = []

    def build_index(self, papers: List[Dict]):
        self.papers = papers
        # Handle papers with or without abstract
        corpus = []
        for p in papers:
            content = p["title"]
            if p.get("abstract"):  # Only add abstract if it exists
                content = content + " " + p["abstract"]
            corpus.append(content.lower().split())
        self.bm25 = BM25Okapi(corpus)

    def _sparse_search(self, query: str, top_k: int) -> List[Dict]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(query.lower().split())
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [{"id": self.papers[idx]["id"], "title": self.papers[idx]["title"], "source": self.papers[idx]["source"],
                 "link": self.papers[idx].get("link", ""), "score": float(score)} for idx, score in ranked[:top_k]]

    def search(self, query: str, top_k: int = DENSE_TOP_K) -> List[Dict]:
        sparse = self._sparse_search(query, top_k)
        dense = self.vectorstore.search(query, top_k)

        if sparse and (max_s := max(p["score"] for p in sparse)):
            for p in sparse:
                p["score"] /= max_s
        if dense and (max_d := max(p["score"] for p in dense)):
            for p in dense:
                p["score"] /= max_d

        merged = {}
        for p in sparse:
            merged[p["id"]] = {**p, "sparse_score": p["score"], "dense_score": 0}
        for p in dense:
            if p["id"] in merged:
                merged[p["id"]]["dense_score"] = p["score"]
            else:
                merged[p["id"]] = {**p, "sparse_score": 0, "dense_score": p["score"]}

        return sorted([{**p, "final_score": SPARSE_WEIGHT * p["sparse_score"] + DENSE_WEIGHT * p["dense_score"]}
                      for p in merged.values()], key=lambda x: x["final_score"], reverse=True)
