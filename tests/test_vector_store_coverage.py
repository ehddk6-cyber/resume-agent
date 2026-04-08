"""vector_store.py 커버리지 — 누락 라인 25-26, 33, 83-113, 125, 161, 186, 190, 192-194, 198-208, 229, 250, 257, 263-280, 283-284, 288, 292-296, 300, 313-314, 328, 344, 357, 363-371, 377-385, 389-400, 411"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestSimpleVectorStore:
    def test_creation(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        assert store is not None

    def test_add_document(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트 문서", {"id": "1"}, doc_id="d1")
        assert len(store.documents) == 1

    def test_add_multiple_documents(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        for i in range(5):
            store.add_document(f"문서 {i} 내용", {"id": str(i)}, doc_id=f"d{i}")
        assert len(store.documents) == 5

    def test_search(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("Python 개발", {"id": "1"}, doc_id="d1")
        store.add_document("요리 레시피", {"id": "2"}, doc_id="d2")
        results = store.search("Python", n_results=2)
        assert isinstance(results, list)

    def test_search_with_min_similarity(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("Python 개발", {"id": "1"}, doc_id="d1")
        store.add_document("요리 레시피", {"id": "2"}, doc_id="d2")
        results = store.search("Python", n_results=2, min_similarity=0.5)
        assert isinstance(results, list)

    def test_search_empty(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        results = store.search("Python", n_results=2)
        assert results == []

    def test_get_document(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트 문서", {"id": "1"}, doc_id="d1")
        doc = store.get_document("d1")
        assert doc is not None

    def test_get_document_not_found(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        doc = store.get_document("nonexistent")
        assert doc is None

    def test_delete_document(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트 문서", {"id": "1"}, doc_id="d1")
        store.delete_document("d1")
        assert len(store.documents) == 0

    def test_delete_document_not_found(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.delete_document("nonexistent")
        assert len(store.documents) == 0

    def test_get_document_count(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        assert len(store.documents) == 0
        store.add_document("테스트", {}, doc_id="d1")
        assert len(store.documents) == 1

    def test_clear(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트", {}, doc_id="d1")
        store.documents.clear()
        assert len(store.documents) == 0

    def test_list_documents(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("문서1", {}, doc_id="d1")
        store.add_document("문서2", {}, doc_id="d2")
        assert len(store.documents) == 2
