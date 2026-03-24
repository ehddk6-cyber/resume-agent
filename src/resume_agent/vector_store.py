"""
벡터 임베딩 기반 검색 - 의미적 유사도 기반 참고 자료 검색
"""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VectorDocument:
    """벡터 문서"""
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class SimpleVectorStore:
    """
    간단한 벡터 저장소 (별도 라이브러리 없이 구현)
    
    실제 프로덕션에서는 chromadb, faiss, pinecone 등을 사용 권장
    이 구현은 학습 및 데모 목적
    """
    
    EMBEDDING_DIMENSION = 128
    INDEX_VERSION = 2

    def __init__(self, persist_directory: str = "./kb/vector"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.documents: Dict[str, VectorDocument] = {}
        self._load()
    
    def _load(self) -> None:
        """저장된 문서 로드"""
        index_file = self.persist_directory / "index.json"
        
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                return
                
            for doc_data in data.get("documents", []):
                doc = VectorDocument(
                    id=doc_data["id"],
                    text=doc_data["text"],
                    metadata=doc_data["metadata"],
                    embedding=self._simple_embed(doc_data["text"])
                )
                self.documents[doc.id] = doc
    
    def _save(self) -> None:
        """문서 저장"""
        index_file = self.persist_directory / "index.json"
        
        data = {
            "index_version": self.INDEX_VERSION,
            "documents": [
                {
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "embedding": doc.embedding
                }
                for doc in self.documents.values()
            ]
        }
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_document(self, text: str, metadata: Dict[str, Any], doc_id: Optional[str] = None) -> str:
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
            embedding=self._simple_embed(text)
        )
        
        self.documents[doc_id] = doc
        self._save()
        
        return doc_id
    
    def _simple_embed(self, text: str) -> List[float]:
        """
        간단한 임베딩 생성 (실제로는 sentence-transformers 사용 권장)
        
        이 구현은 단어 빈도 기반으로 간단하게 구현
        """
        embedding = [0.0] * self.EMBEDDING_DIMENSION
        for feature in self._extract_features(text):
            index = self._feature_index(feature)
            embedding[index] += 1.0

        norm = sum(value * value for value in embedding) ** 0.5
        if norm > 0:
            embedding = [value / norm for value in embedding]

        return embedding
    
    def search(self, query: str, n_results: int = 5, min_similarity: float = 0.1) -> List[Dict[str, Any]]:
        """
        유사한 문서 검색
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            min_similarity: 최소 유사도
        
        Returns:
            검색 결과 리스트
        """
        query_embedding = self._simple_embed(query)
        
        results = []
        for doc in self.documents.values():
            if doc.embedding is None:
                continue
            
            similarity = self._cosine_similarity(query_embedding, doc.embedding)
            
            if similarity >= min_similarity:
                results.append({
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "similarity": similarity
                })
        
        # 유사도 기준 정렬
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

        features: List[str] = []
        tokens = re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
        features.extend(tokens)

        compact_text = re.sub(r"\s+", "", text.lower())
        features.extend(
            char
            for char in compact_text
            if char.isalnum() or ('가' <= char <= '힣')
        )
        features.extend(
            compact_text[index:index + 2]
            for index in range(len(compact_text) - 1)
            if compact_text[index:index + 2].strip()
        )
        return features

    def _feature_index(self, feature: str) -> int:
        digest = hashlib.md5(feature.encode("utf-8")).hexdigest()
        return int(digest, 16) % self.EMBEDDING_DIMENSION
    
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
                "text_preview": doc.text[:100] + "..." if len(doc.text) > 100 else doc.text,
                "metadata": doc.metadata
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
    - 다국어 지원 (간단한 구현)
    """
    
    def __init__(self, persist_directory: str = "./kb/vector"):
        self.store = SimpleVectorStore(persist_directory)
    
    def index_pattern(self, pattern_id: str, text: str, metadata: Dict[str, Any]) -> str:
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
    
    def search_by_company(self, company: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """회사별 패턴 검색"""
        all_docs = self.store.list_documents()
        
        company_docs = [
            doc for doc in all_docs
            if doc["metadata"].get("company", "").lower() == company.lower()
        ]
        
        return company_docs[:n_results]
    
    def search_by_question_type(self, question_type: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """질문 유형별 패턴 검색"""
        all_docs = self.store.list_documents()
        
        type_docs = [
            doc for doc in all_docs
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
            "question_types": list(question_types)
        }


def create_vector_knowledge_base(persist_directory: str = "./kb/vector") -> VectorKnowledgeBase:
    """VectorKnowledgeBase 인스턴스 생성 편의 함수"""
    return VectorKnowledgeBase(persist_directory)
