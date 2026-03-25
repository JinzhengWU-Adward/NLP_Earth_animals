from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.models.species import Species
from app.nlp.embedder import Embedder, TfidfFallbackEmbedder


@dataclass
class RetrievalHit:
    score: float
    species: Species


class SpeciesVectorIndex:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        self._species: list[Species] = []
        self._embeddings: np.ndarray | None = None
        self._faiss = None
        self._index = None

    def build(self, species: list[Species]) -> None:
        self._species = list(species)
        texts = [self._doc_text(s) for s in self._species]

        if isinstance(self.embedder, TfidfFallbackEmbedder):
            self.embedder.fit(texts)

        embs = self.embedder.embed(texts)
        if embs.ndim != 2:
            raise ValueError("Embeddings must be 2D array.")

        self._embeddings = embs.astype(np.float32, copy=False)

        import faiss  # lazy import

        self._faiss = faiss
        dim = self._embeddings.shape[1]
        # 由于我们做了 normalize_embeddings=True，这里用 inner product 即余弦相似度
        index = faiss.IndexFlatIP(dim)
        index.add(self._embeddings)
        self._index = index

    def search(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        if self._index is None or self._embeddings is None:
            raise RuntimeError("Vector index is not built.")
        q = self.embedder.embed([query]).astype(np.float32, copy=False)
        scores, ids = self._index.search(q, top_k)
        hits: list[RetrievalHit] = []
        for score, idx in zip(scores[0].tolist(), ids[0].tolist(), strict=False):
            if idx < 0 or idx >= len(self._species):
                continue
            hits.append(RetrievalHit(score=float(score), species=self._species[idx]))
        return hits

    @staticmethod
    def _doc_text(s: Species) -> str:
        # 把结构化字段拼成“可检索文档”，同时对后续 RAG 友好
        return (
            f"Species: {s.species_name}\n"
            f"Region: {s.region}\n"
            f"Habitat: {s.habitat}\n"
            f"Diet: {s.diet}\n"
            f"Description: {s.description}\n"
        )

