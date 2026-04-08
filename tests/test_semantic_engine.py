"""semantic_engine 모듈 테스트 — 의미적 검색 엔진"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from resume_agent.semantic_engine import (
    is_embedding_available,
    SemanticSearchEngine,
    SemanticSearchConfig,
    SemanticMatch,
    compute_hash_similarity,
    compute_similarity,
    compute_tfidf_similarity,
    extract_korean_nouns,
    extract_keywords_advanced,
    extract_semantic_keywords,
    match_experiences_to_questions,
    _cosine_similarity,
    _extract_features,
    _text_to_sparse_vector,
)


# ──────────────────────────────────────────────────
# 기본 기능 테스트
# ──────────────────────────────────────────────────


class TestCosineSimilarity:
    def test_identical_vectors(self):
        vec = {0: 1.0, 1: 2.0, 2: 3.0}
        result = _cosine_similarity(vec, vec)
        assert abs(result - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        vec1 = {0: 1.0}
        vec2 = {1: 1.0}
        result = _cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_empty_vectors(self):
        assert _cosine_similarity({}, {0: 1.0}) == 0.0
        assert _cosine_similarity({0: 1.0}, {}) == 0.0
        assert _cosine_similarity({}, {}) == 0.0

    def test_similar_vectors(self):
        vec1 = {0: 1.0, 1: 1.0}
        vec2 = {0: 1.0, 1: 1.0}
        result = _cosine_similarity(vec1, vec2)
        assert abs(result - 1.0) < 0.001


class TestFeatureExtraction:
    def test_extract_features_korean(self):
        features = _extract_features("안녕하세요 세계")
        assert len(features) > 0
        assert any("안녕하세요" in f for f in features)

    def test_extract_features_english(self):
        features = _extract_features("Hello World")
        assert len(features) > 0

    def test_extract_features_empty(self):
        features = _extract_features("")
        assert features == []

    def test_extract_features_mixed(self):
        features = _extract_features("Python 개발자 모집")
        assert len(features) > 0


class TestTextToSparseVector:
    def test_basic_vector(self):
        vec = _text_to_sparse_vector("테스트 텍스트")
        assert len(vec) > 0
        assert all(isinstance(k, int) for k in vec.keys())
        assert all(isinstance(v, float) for v in vec.values())

    def test_empty_text(self):
        vec = _text_to_sparse_vector("")
        assert vec == {}

    def test_vector_dimension(self):
        vec = _text_to_sparse_vector("긴 텍스트입니다 " * 100, dim=128)
        assert all(k < 128 for k in vec.keys())


# ──────────────────────────────────────────────────
# 해시 기반 유사도 테스트
# ──────────────────────────────────────────────────


class TestHashSimilarity:
    def test_identical_texts(self):
        text = "웹 서비스 개발 프로젝트"
        result = compute_hash_similarity(text, text)
        assert result > 0.9

    def test_similar_texts(self):
        text1 = "Python 개발자 모집 Django 경험 필수"
        text2 = "Python 개발자 Django 사용 경험 우대"
        result = compute_hash_similarity(text1, text2)
        assert result > 0.3

    def test_different_texts(self):
        text1 = "웹 개발 프로젝트"
        text2 = "요리 레시피 책 출판"
        result = compute_hash_similarity(text1, text2)
        assert result < 0.5

    def test_empty_texts(self):
        assert compute_hash_similarity("", "테스트") == 0.0
        assert compute_hash_similarity("테스트", "") == 0.0
        assert compute_hash_similarity("", "") == 0.0

    def test_korean_meaning_similarity(self):
        """의미적으로 유사한 한국어 텍스트"""
        text1 = "고객 응대 서비스 품질 개선"
        text2 = "민원 처리 고객 만족도 향상"
        result = compute_hash_similarity(text1, text2)
        # 일부 키워드가 겹칠 수 있음
        assert result >= 0.0


# ──────────────────────────────────────────────────
# TF-IDF 유사도 테스트
# ──────────────────────────────────────────────────


class TestTfidfSimilarity:
    def test_identical_texts(self):
        text = "테스트 텍스트입니다"
        result = compute_tfidf_similarity(text, text)
        assert result > 0.9

    def test_different_texts(self):
        text1 = "Python 프로그래밍"
        text2 = "요리 레시피"
        result = compute_tfidf_similarity(text1, text2)
        assert result < 0.5

    def test_empty_texts(self):
        result = compute_tfidf_similarity("", "")
        assert result >= 0.0


# ──────────────────────────────────────────────────
# 통합 유사도 테스트
# ──────────────────────────────────────────────────


class TestComputeSimilarity:
    def test_returns_valid_method(self):
        score, method = compute_similarity("테스트1", "테스트2")
        assert method in ("embedding", "tfidf", "hash")
        assert 0.0 <= score <= 1.0

    def test_embedding_disabled(self):
        config = SemanticSearchConfig(use_embedding=False)
        score, method = compute_similarity("테스트1", "테스트2", config)
        assert method in ("tfidf", "hash")

    def test_tfidf_disabled(self):
        config = SemanticSearchConfig(use_embedding=False, use_tfidf_fallback=False)
        score, method = compute_similarity("테스트1", "테스트2", config)
        assert method == "hash"


# ──────────────────────────────────────────────────
# 한국어 형태소 분석 테스트
# ──────────────────────────────────────────────────


class TestKoreanNouns:
    def test_extract_nouns_basic(self):
        nouns = extract_korean_nouns("웹 서비스 개발 프로젝트를 수행했습니다")
        assert isinstance(nouns, list)
        assert len(nouns) > 0

    def test_extract_nouns_empty(self):
        assert extract_korean_nouns("") == []
        assert extract_korean_nouns(None) == []

    def test_extract_nouns_english_only(self):
        nouns = extract_korean_nouns("Python Django FastAPI")
        # 영어만 있으면 한국어 명사 없음
        assert isinstance(nouns, list)

    def test_extract_keywords_advanced(self):
        keywords = extract_keywords_advanced("Python 개발자 30% 성과 달성")
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_extract_keywords_empty(self):
        assert extract_keywords_advanced("") == []
        assert extract_keywords_advanced(None) == []

    def test_extract_semantic_keywords(self):
        result = extract_semantic_keywords("Python 개발자 30% 성과 달성")
        assert "nouns" in result
        assert "keywords" in result
        assert "numeric" in result
        assert "30%" in result["numeric"]


# ──────────────────────────────────────────────────
# 검색 엔진 테스트
# ──────────────────────────────────────────────────


class TestSemanticSearchEngine:
    def test_init_default(self):
        engine = SemanticSearchEngine()
        assert engine.config.top_k == 5
        assert engine.config.min_score == 0.01

    def test_init_custom_config(self):
        config = SemanticSearchConfig(top_k=3, min_score=0.1)
        engine = SemanticSearchEngine(config)
        assert engine.config.top_k == 3

    def test_index_documents(self):
        engine = SemanticSearchEngine()
        docs = {
            "e1": "Python 웹 개발 경험",
            "e2": "데이터 분석 프로젝트",
            "e3": "팀 리더십 경험",
        }
        engine.index_documents(docs)
        assert len(engine._doc_cache) == 3

    def test_search_empty_query(self):
        engine = SemanticSearchEngine()
        engine.index_documents({"e1": "테스트"})
        results = engine.search("")
        assert results == []

    def test_search_empty_index(self):
        engine = SemanticSearchEngine()
        results = engine.search("테스트 쿼리")
        assert results == []

    def test_search_returns_matches(self):
        engine = SemanticSearchEngine()
        docs = {
            "e1": "Python 웹 개발 프로젝트를 수행했습니다",
            "e2": "데이터 분석 및 시각화 작업",
            "e3": "React 프론트엔드 개발 경험",
        }
        engine.index_documents(docs)
        results = engine.search("Python 개발 경험", top_k=2)

        assert len(results) <= 2
        assert all(isinstance(m, SemanticMatch) for m in results)
        assert all(0.0 <= m.score <= 1.0 for m in results)

    def test_search_relevance_order(self):
        engine = SemanticSearchEngine()
        docs = {
            "e1": "Python Django 웹 개발 프로젝트",
            "e2": "요리 레시피 블로그 운영",
            "e3": "Python FastAPI API 서버 구축",
        }
        engine.index_documents(docs)
        results = engine.search("Python 개발", top_k=3)

        # Python 관련 문서가 더 높은 순위
        if len(results) >= 2:
            assert results[0].score >= results[1].score

    def test_find_best_match(self):
        engine = SemanticSearchEngine()
        docs = {
            "e1": "웹 개발 프로젝트",
            "e2": "모바일 앱 개발",
        }
        engine.index_documents(docs)
        result = engine.find_best_match("웹 개발")
        assert result is not None
        assert isinstance(result, SemanticMatch)

    def test_find_best_match_empty(self):
        engine = SemanticSearchEngine()
        result = engine.find_best_match("테스트")
        assert result is None

    def test_get_stats(self):
        engine = SemanticSearchEngine()
        engine.index_documents({"e1": "테스트", "e2": "테스트2"})
        stats = engine.get_stats()
        assert stats["indexed_documents"] == 2
        assert "embedding_available" in stats

    def test_search_with_min_score(self):
        engine = SemanticSearchEngine()
        docs = {
            "e1": "Python 개발",
            "e2": "요리 레시피",
        }
        engine.index_documents(docs)
        results = engine.search("Python", min_score=0.5)
        # 높은 임계값으로 필터링
        assert all(m.score >= 0.5 for m in results)


# ──────────────────────────────────────────────────
# 경험-질문 매칭 테스트
# ──────────────────────────────────────────────────


class TestMatchExperiencesToQuestions:
    def test_basic_matching(self):
        questions = ["Python 개발 경험을 말씀해주세요"]
        experiences = {
            "e1": "Python Django 웹 개발 프로젝트 수행",
            "e2": "Java Spring 백엔드 개발",
        }
        result = match_experiences_to_questions(questions, experiences)
        assert len(result) == 1
        assert "Python 개발 경험을 말씀해주세요" in result

    def test_multiple_questions(self):
        questions = [
            "Python 개발 경험",
            "데이터 분석 경험",
        ]
        experiences = {
            "e1": "Python 개발 프로젝트",
            "e2": "데이터 분석 및 시각화",
        }
        result = match_experiences_to_questions(questions, experiences)
        assert len(result) == 2

    def test_empty_inputs(self):
        result = match_experiences_to_questions([], {})
        assert result == {}


# ──────────────────────────────────────────────────
# 설정 테스트
# ──────────────────────────────────────────────────


class TestSemanticSearchConfig:
    def test_default_values(self):
        config = SemanticSearchConfig()
        assert config.top_k == 5
        assert config.min_score == 0.01
        assert config.use_embedding is True
        assert config.use_tfidf_fallback is True

    def test_custom_values(self):
        config = SemanticSearchConfig(
            top_k=10,
            min_score=0.5,
            use_embedding=False,
        )
        assert config.top_k == 10
        assert config.min_score == 0.5
        assert config.use_embedding is False


class TestSemanticMatch:
    def test_creation(self):
        match = SemanticMatch(
            doc_id="e1",
            score=0.85,
            query_text="테스트",
            doc_text="테스트 문서",
            method="embedding",
        )
        assert match.doc_id == "e1"
        assert match.score == 0.85
        assert match.method == "embedding"


class TestIsEmbeddingAvailable:
    def test_returns_bool(self):
        result = is_embedding_available()
        assert isinstance(result, bool)
