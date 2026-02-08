"""Unit tests for InMemoryVectorStore (and VectorStore contract)."""

import pytest

from tests.mocks.mock_vector_store import InMemoryVectorStore


@pytest.mark.unit
class TestInMemoryVectorStore:
    @pytest.mark.asyncio
    async def test_upsert_and_get(self) -> None:
        store = InMemoryVectorStore()
        await store.upsert("col", "doc1", "hello", [1.0, 0.0], {"key": "val"})

        result = await store.get("col", "doc1")
        assert result is not None
        assert result["id"] == "doc1"
        assert result["text"] == "hello"
        assert result["embedding"] == [1.0, 0.0]
        assert result["metadata"]["key"] == "val"

    @pytest.mark.asyncio
    async def test_get_not_found(self) -> None:
        store = InMemoryVectorStore()
        result = await store.get("col", "missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        store = InMemoryVectorStore()
        await store.upsert("col", "doc1", "hello", [1.0, 0.0])
        await store.delete("col", "doc1")
        result = await store.get("col", "doc1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_missing_is_noop(self) -> None:
        store = InMemoryVectorStore()
        await store.delete("col", "missing")  # should not raise

    @pytest.mark.asyncio
    async def test_search_returns_sorted_by_distance(self) -> None:
        store = InMemoryVectorStore()
        # Vectors: query is [1, 0], doc_a is close, doc_b is far
        await store.upsert("col", "close", "close doc", [0.9, 0.1])
        await store.upsert("col", "far", "far doc", [0.0, 1.0])

        results = await store.search("col", [1.0, 0.0], n_results=10)
        assert len(results) == 2
        assert results[0]["id"] == "close"
        assert results[1]["id"] == "far"
        assert results[0]["distance"] < results[1]["distance"]

    @pytest.mark.asyncio
    async def test_search_respects_n_results(self) -> None:
        store = InMemoryVectorStore()
        await store.upsert("col", "a", "a", [1.0, 0.0])
        await store.upsert("col", "b", "b", [0.9, 0.1])
        await store.upsert("col", "c", "c", [0.0, 1.0])

        results = await store.search("col", [1.0, 0.0], n_results=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_empty_collection(self) -> None:
        store = InMemoryVectorStore()
        results = await store.search("empty", [1.0, 0.0], n_results=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_upsert_overwrites(self) -> None:
        store = InMemoryVectorStore()
        await store.upsert("col", "doc1", "old", [1.0, 0.0])
        await store.upsert("col", "doc1", "new", [0.0, 1.0])

        result = await store.get("col", "doc1")
        assert result is not None
        assert result["text"] == "new"
        assert result["embedding"] == [0.0, 1.0]
