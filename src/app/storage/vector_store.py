from abc import ABC, abstractmethod


class VectorStore(ABC):
    @abstractmethod
    async def upsert(
        self,
        collection: str,
        doc_id: str,
        text: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        """Store or update a document with its embedding."""
        ...

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> list[dict]:
        """Search for similar documents. Returns list of {id, distance, metadata}."""
        ...

    @abstractmethod
    async def delete(self, collection: str, doc_id: str) -> None:
        """Delete a document from the collection."""
        ...

    @abstractmethod
    async def get(self, collection: str, doc_id: str) -> dict | None:
        """Get a document by ID. Returns {id, document, metadata} or None."""
        ...
