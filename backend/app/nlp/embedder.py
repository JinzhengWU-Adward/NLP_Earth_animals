from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Embedder:
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class SentenceTransformersEmbedder(Embedder):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        super().__init__(name=f"sentence-transformers:{model_name}")
        from sentence_transformers import SentenceTransformer  # lazy import

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vecs.astype(np.float32, copy=False)


class TfidfFallbackEmbedder(Embedder):
    """
    兜底方案：当 sentence-transformers（常见原因：torch 安装困难）不可用时，
    用 TF-IDF 向量做检索，保证 MVP 可跑通。
    """

    def __init__(self):
        super().__init__(name="tfidf-fallback")
        from sklearn.feature_extraction.text import TfidfVectorizer  # lazy import

        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._fitted = False

    def fit(self, texts: list[str]) -> None:
        self._vectorizer.fit(texts)
        self._fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("TF-IDF embedder is not fitted yet.")
        mat = self._vectorizer.transform(texts)
        dense = mat.toarray().astype(np.float32, copy=False)
        norms = np.linalg.norm(dense, axis=1, keepdims=True) + 1e-12
        return dense / norms


def build_embedder() -> Embedder:
    try:
        return SentenceTransformersEmbedder()
    except Exception:
        # 任何导入/模型加载失败都回退，优先保证系统可运行。
        return TfidfFallbackEmbedder()

