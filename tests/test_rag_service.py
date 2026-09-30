from unittest.mock import Mock

from chromadb.errors import NotFoundError

from src.services import rag_service as module


def test_missing_collection_returns_no_source_and_can_be_loaded_later(monkeypatch):
    client = Mock()
    collection = Mock()
    client.get_collection.side_effect = [NotFoundError("Not loaded"), collection]
    collection.query.return_value = {
        "documents": [["Official information"]],
        "metadatas": [[{"source_id": "SRC-TEST", "title": "Guide", "url": "https://example.invalid"}]],
        "distances": [[0.2]],
        "ids": [["chunk-1"]],
    }
    factory = Mock(return_value=client)
    monkeypatch.setattr(module.chromadb, "PersistentClient", factory)
    service = module.RAGService(chroma_dir="test-knowledge")
    factory.assert_not_called()

    missing = service.retrieve("question")
    assert missing["status"] == "NO_SOURCE"
    assert missing["citations"] == []
    collection.query.assert_not_called()

    loaded = service.retrieve("question")
    assert loaded["status"] == "SUCCESS"
    assert loaded["citations"][0]["source_id"] == "SRC-TEST"
    factory.assert_called_once_with(path="test-knowledge")


def test_unrelated_storage_errors_are_not_reported_as_missing_sources(monkeypatch):
    import pytest

    client = Mock()
    client.get_collection.side_effect = RuntimeError("Storage unavailable")
    monkeypatch.setattr(module.chromadb, "PersistentClient", Mock(return_value=client))
    with pytest.raises(RuntimeError, match="Storage unavailable"):
        module.RAGService().retrieve("question")
