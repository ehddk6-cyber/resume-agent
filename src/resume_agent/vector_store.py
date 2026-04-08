"""
벡터 임베딩 기반 검색 - 의미적 유사도 기반 참고 자료 검색
SentenceTransformer 384차원 임베딩 + 해시 폴백
"""

from __future__ import annotations

import json
import hashlib
import importlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .config import get_config_value
from .tokenizer import tokenize_for_embedding

# SentenceTransformer 싱글톤
_ST_MODEL = None
_ST_CLASS = None


def _get_st_model() -> Any:
    """SentenceTransformer 모델 싱글톤 로더 (지연 로딩)"""
    global _ST_MODEL, _ST_CLASS
    if _ST_CLASS is None:
        try:
            module = importlib.import_module("sentence_transformers")
            _ST_CLASS = getattr(module, "SentenceTransformer", None)
        except ImportError:
            _ST_CLASS = False
    if _ST_CLASS in (None, False):
        return None
    if _ST_MODEL is None:
        model_name = get_config_value(
            "embedding.model_name", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        _ST_MODEL = _ST_CLASS(model_name)
    return _ST_MODEL


def get_embedding_dimension() -> int:
    """현재 설정된 임베딩 차원 반환"""
    return int(get_config_value("embedding.dimension", 384))


@dataclass
class VectorDocument:
    """벡터 문서"""

    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class SimpleVectorStore:
    """
    벡터 저장소

    SentenceTransformer 사용 가능 시 384차원 임베딩,
    미사용 시 해시 기반 폴백.
    """

    INDEX_VERSION = 3

    def __init__(self, persist_directory: str = "./kb/vector"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.documents: Dict[str, VectorDocument] = {}
        self._load()

    @property
    def embedding_dimension(self) -> int:
        return get_embedding_dimension()

    def _load(self) -> None:
        """저장된 문서 로드 (차원 불일치 시 재임베딩)"""
        index_file = self.persist_directory / "index.json"

        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                return

            stored_dim = data.get("embedding_dimension", 128)
            current_dim = self.embedding_dimension
            need_reindex = stored_dim != current_dim

            for doc_data in data.get("documents", []):
                stored_embedding = doc_data.get("embedding")
                if (
                    need_reindex
                    or stored_embedding is None
                    or len(stored_embedding) != current_dim
                ):
                    embedding = self._embed(doc_data["text"])
                else:
                    embedding = stored_embedding

                doc = VectorDocument(
                    id=doc_data["id"],
                    text=doc_data["text"],
                    metadata=doc_data["metadata"],
                    embedding=embedding,
                )
                self.documents[doc.id] = doc

            if need_reindex:
                self._save()

    def _save(self) -> None:
        """문서 저장"""
        index_file = self.persist_directory / "index.json"

        documents_data = []
        for doc in self.documents.values():
            embedding = doc.embedding
            if embedding is not None:
                # numpy array → list 변환
                if hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()
                embedding = list(embedding)

            documents_data.append(
                {
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "embedding": embedding,
                }
            )

        data = {
            "index_version": self.INDEX_VERSION,
            "embedding_dimension": self.embedding_dimension,
            "documents": documents_data,
        }

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_document(
        self, text: str, metadata: Dict[str, Any], doc_id: Optional[str] = None
    ) -> str:
        """
        문서 추가

        Args:
            text: 문서 텍스트
            metadata: 메타데이터
            doc_id: 문서 ID (없으면 자동 생성)

        Returns:
            문서 ID
        """
        if doc_id is None:
            doc_id = hashlib.md5(text.encode("utf-8")).hexdigest()

        doc = VectorDocument(
            id=doc_id,
            text=text,
            metadata=metadata,
            embedding=self._embed(text),
        )

        self.documents[doc_id] = doc
        self._save()

        return doc_id

    def _embed(self, text: str) -> List[float]:
        """
        임베딩 생성.
        1순위: SentenceTransformer
        2순위: 해시 기반 폴백
        """
        model = _get_st_model()
        if model is not None:
            try:
                processed = tokenize_for_embedding(text)
                if not processed.strip():
                    processed = text
                vec = model.encode(processed, normalize_embeddings=True)
                result = vec.tolist() if hasattr(vec, "tolist") else list(vec)
                if len(result) != self.embedding_dimension:
                    return self._hash_embed(text)
                return result
            except Exception:
                return self._hash_embed(text)
        return self._hash_embed(text)

    def _hash_embed(self, text: str) -> List[float]:
        """해시 기반 폴백 임베딩"""
        dim = self.embedding_dimension
        embedding = [0.0] * dim
        for feature in self._extract_features(text):
            index = self._feature_index(feature, dim)
            embedding[index] += 1.0

        norm = sum(value * value for value in embedding) ** 0.5
        if norm > 0:
            embedding = [value / norm for value in embedding]

        return embedding

    def search(
        self, query: str, n_results: int = 5, min_similarity: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        유사한 문서 검색

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            min_similarity: 최소 유사도

        Returns:
            검색 결과 리스트
        """
        query_embedding = self._embed(query)

        results = []
        for doc in self.documents.values():
            if doc.embedding is None:
                continue

            similarity = self._cosine_similarity(query_embedding, doc.embedding)

            if similarity >= min_similarity:
                results.append(
                    {
                        "id": doc.id,
                        "text": doc.text,
                        "metadata": doc.metadata,
                        "similarity": similarity,
                    }
                )

        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:n_results]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _extract_features(self, text: str) -> List[str]:
        """문서와 쿼리 모두에서 동일한 특징 공간을 사용"""
        if not text:
            return []

        # kiwipiepy 폴백으로 정규식 사용
        features: List[str] = []
        tokens = re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
        features.extend(tokens)

        compact_text = re.sub(r"\s+", "", text.lower())
        features.extend(
            char for char in compact_text if char.isalnum() or ("가" <= char <= "힣")
        )
        features.extend(
            compact_text[index : index + 2]
            for index in range(len(compact_text) - 1)
            if compact_text[index : index + 2].strip()
        )
        return features

    def _feature_index(self, feature: str, dim: Optional[int] = None) -> int:
        digest = hashlib.md5(feature.encode("utf-8")).hexdigest()
        return int(digest, 16) % (dim or self.embedding_dimension)

    def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        """문서 조회"""
        return self.documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save()
            return True
        return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """문서 목록 반환"""
        return [
            {
                "id": doc.id,
                "text_preview": doc.text[:100] + "..."
                if len(doc.text) > 100
                else doc.text,
                "metadata": doc.metadata,
            }
            for doc in self.documents.values()
        ]

    def clear(self) -> None:
        """모든 문서 삭제"""
        self.documents.clear()
        self._save()


class VectorKnowledgeBase:
    """
    벡터 기반 지식베이스

    기능:
    - 패턴 인덱싱
    - 의미적 유사도 검색
    - 다국어 지원
    """

    def __init__(self, persist_directory: str = "./kb/vector"):
        self.store = SimpleVectorStore(persist_directory)

    def index_pattern(
        self, pattern_id: str, text: str, metadata: Dict[str, Any]
    ) -> str:
        """
        패턴 인덱싱

        Args:
            pattern_id: 패턴 ID
            text: 패턴 텍스트
            metadata: 메타데이터 (회사, 직무, 질문 유형 등)

        Returns:
            문서 ID
        """
        return self.store.add_document(text, metadata, doc_id=pattern_id)

    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        유사한 패턴 검색

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수

        Returns:
            검색 결과 리스트
        """
        return self.store.search(query, n_results)

    def search_by_company(
        self, company: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """회사별 패턴 검색"""
        all_docs = self.store.list_documents()

        company_docs = [
            doc
            for doc in all_docs
            if doc["metadata"].get("company", "").lower() == company.lower()
        ]

        return company_docs[:n_results]

    def search_by_question_type(
        self, question_type: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """질문 유형별 패턴 검색"""
        all_docs = self.store.list_documents()

        type_docs = [
            doc
            for doc in all_docs
            if doc["metadata"].get("question_type", "").lower() == question_type.lower()
        ]

        return type_docs[:n_results]

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        docs = self.store.list_documents()

        companies = set()
        question_types = set()

        for doc in docs:
            if "company" in doc["metadata"]:
                companies.add(doc["metadata"]["company"])
            if "question_type" in doc["metadata"]:
                question_types.add(doc["metadata"]["question_type"])

        return {
            "total_patterns": len(docs),
            "companies": list(companies),
            "question_types": list(question_types),
        }


def create_vector_knowledge_base(
    persist_directory: str = "./kb/vector",
) -> VectorKnowledgeBase:
    """VectorKnowledgeBase 인스턴스 생성 편의 함수"""
    return VectorKnowledgeBase(persist_directory)
