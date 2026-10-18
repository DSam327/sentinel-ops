"""
Semantic Vector and Text Store for SentinelOps.
Uses TF-IDF and Cosine Similarity (via scikit-learn) for fast, zero-external-daemon retrieval.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class DocumentChunk:
    def __init__(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        self.doc_id = doc_id
        self.content = content
        self.metadata = metadata


class SemanticTextStore:
    """
    Lightweight vector store for indexing and retrieving:
    - Recent Git diffs & commit messages
    - Service runbooks & postmortems
    - Aggregated structured log lines
    """

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self._is_fitted = False

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        self.chunks.append(DocumentChunk(doc_id=doc_id, content=content, metadata=metadata))
        self._is_fitted = False

    def build_index(self) -> None:
        """Fits TF-IDF vectorizer over all indexed documents."""
        if not self.chunks:
            return
        corpus = [c.content for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self._is_fitted = True

    def search(
        self, query: str, top_k: int = 3, filter_service: Optional[str] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """Searches documents by cosine similarity against query vector."""
        if not self._is_fitted or not self.vectorizer:
            self.build_index()

        if not self.chunks or self.tfidf_matrix is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Pair with chunks and sort
        ranked_indices = np.argsort(similarities)[::-1]
        results = []

        for idx in ranked_indices:
            score = float(similarities[idx])
            chunk = self.chunks[idx]

            if filter_service and chunk.metadata.get("service_name") != filter_service:
                continue

            if score > 0.05:  # Relevance threshold
                results.append((chunk, round(score, 4)))

            if len(results) >= top_k:
                break

        return results
