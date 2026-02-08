"""In-memory VectorStore for testing — stores embeddings in a dict."""

import math

from app.storage.vector_store import VectorStore


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """Compute cosine distance between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 2.0  # max distance
    similarity = dot / (norm_a * norm_b)
    return 1.0 - similarity


class InMemoryVectorStore(VectorStore):
    """VectorStore backed by a plain dict — no external dependencies."""

    def __init__(self) -> None:
        # {collection_name: {doc_id: {text, embedding, metadata}}}
        self._data: dict[str, dict[str, dict]] = {}

    async def upsert(
        self,
        collection: str,
        doc_id: str,
        text: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        if collection not in self._data:
            self._data[collection] = {}
        self._data[collection][doc_id] = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
        }

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> list[dict]:
        coll = self._data.get(collection, {})
        if not coll:
            return []

        scored = []
        for doc_id, entry in coll.items():
            dist = _cosine_distance(query_embedding, entry["embedding"])
            scored.append(
                {
                    "id": doc_id,
                    "distance": dist,
                    "metadata": entry["metadata"],
                    "document": entry["text"],
                }
            )

        scored.sort(key=lambda x: x["distance"])
        return scored[:n_results]

    async def delete(self, collection: str, doc_id: str) -> None:
        coll = self._data.get(collection, {})
        coll.pop(doc_id, None)

    async def get(self, collection: str, doc_id: str) -> dict | None:
        coll = self._data.get(collection, {})
        entry = coll.get(doc_id)
        if entry is None:
            return None
        return {
            "id": doc_id,
            "text": entry["text"],
            "embedding": entry["embedding"],
            "metadata": entry["metadata"],
        }
