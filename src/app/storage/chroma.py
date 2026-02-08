import asyncio

import chromadb

from app.storage.vector_store import VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, host: str, port: int) -> None:
        self._client = chromadb.HttpClient(host=host, port=port)

    def _get_collection(self, name: str) -> chromadb.Collection:
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(
        self,
        collection: str,
        doc_id: str,
        text: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        coll = self._get_collection(collection)
        await asyncio.to_thread(
            coll.upsert,
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}],
        )

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        n_results: int = 10,
    ) -> list[dict]:
        coll = self._get_collection(collection)
        results = await asyncio.to_thread(
            coll.query,
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["distances", "metadatas", "documents"],
        )

        items: list[dict] = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                items.append(
                    {
                        "id": doc_id,
                        "distance": results["distances"][0][i] if results["distances"] else 0.0,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "document": results["documents"][0][i] if results["documents"] else "",
                    }
                )
        return items

    async def delete(self, collection: str, doc_id: str) -> None:
        coll = self._get_collection(collection)
        await asyncio.to_thread(coll.delete, ids=[doc_id])

    async def get(self, collection: str, doc_id: str) -> dict | None:
        coll = self._get_collection(collection)
        result = await asyncio.to_thread(coll.get, ids=[doc_id], include=["metadatas", "documents"])

        if not result or not result["ids"]:
            return None

        return {
            "id": result["ids"][0],
            "document": result["documents"][0] if result["documents"] else "",
            "metadata": result["metadatas"][0] if result["metadatas"] else {},
        }
