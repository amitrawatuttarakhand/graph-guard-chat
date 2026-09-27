"""Lightweight document store for RAG: chunks text and searches it with TF-IDF
+ cosine similarity. Deliberately not embeddings-based — a neural embedding
model is another heavy, slow-to-install dependency (same lesson as Presidio),
and TF-IDF is enough for keyword-heavy questions over a handful of documents.
"""
from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Split on whitespace into overlapping word-count windows."""
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks


@dataclass
class Chunk:
    source: str
    index: int
    content: str


class DocumentStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    def _reindex(self) -> None:
        if not self.chunks:
            self._vectorizer, self._matrix = None, None
            return
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform([c.content for c in self.chunks])

    def add_chunks(self, source: str, contents: list[str]) -> int:
        """Add already-chunked content as-is (used when reloading from persistence)."""
        start = len(self.chunks)
        self.chunks.extend(Chunk(source=source, index=i, content=c) for i, c in enumerate(contents))
        self._reindex()
        return len(self.chunks) - start

    def add_document(self, source: str, text: str) -> list[str]:
        """Chunk `text` and add it under `source`. Returns the chunk contents added."""
        pieces = chunk_text(text)
        self.add_chunks(source, pieces)
        return pieces

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05) -> list[Chunk]:
        if not self.chunks or self._vectorizer is None:
            return []
        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.chunks[i] for i in ranked[:top_k] if scores[i] >= min_score]

    def summary(self) -> dict[str, int]:
        """Filename -> chunk count, for display in the UI."""
        out: dict[str, int] = {}
        for c in self.chunks:
            out[c.source] = out.get(c.source, 0) + 1
        return out


docs = DocumentStore()