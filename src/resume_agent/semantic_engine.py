"""의미적 검색 엔진 — 임베딩 기반 경험-질문 매칭"""

from __future__ import annotations

import hashlib
import importlib
import re
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .logger import get_logger
from .config import get_config_value

logger = get_logger(__name__)

_ST_MODEL = None
_ST_LOCK = threading.Lock()
_ST_CLASS = None


def is_embedding_available() -> bool:
    """SentenceTransformer 사용 가능 여부"""
    global _ST_CLASS
    if _ST_CLASS is None:
        try:
            module = importlib.import_module("sentence_transformers")
            _ST_CLASS = getattr(module, "SentenceTransformer", None)
        except ImportError:
            _ST_CLASS = False
    return _ST_CLASS not in (None, False)


def _get_embedding_model() -> Optional[Any]:
    """SentenceTransformer 싱글톤 인스턴스 반환"""
    global _ST_MODEL, _ST_CLASS
    if not is_embedding_available():
        return None
    with _ST_LOCK:
        if _ST_MODEL is None:
            model_name = get_config_value(
                "embedding.model_name", "intfloat/multilingual-e5-small"
            )
            try:
                _ST_MODEL = _ST_CLASS(model_name)
                logger.info(f"임베딩 모델 로드 완료: {model_name}")
            except Exception as e:
                logger.warning(f"임베딩 모델 로드 실패: {e}")
                return None
    return _ST_MODEL


@dataclass
class SemanticMatch:
    """의미적 검색 결과"""

    doc_id: str
    score: float
    query_text: str
    doc_text: str
    method: str  # "embedding", "tfidf", "hash"


@dataclass
class SemanticSearchConfig:
    """검색 설정"""

    top_k: int = 5
    min_score: float = 0.01
    use_embedding: bool = True
    use_tfidf_fallback: bool = True
    embedding_weight: float = 0.6
    tfidf_weight: float = 0.3
    hash_weight: float = 0.1


_KIWI = None
_USE_KIWI = False

try:
    from kiwipiepy import Kiwi as _KiwiClass

    _USE_KIWI = True
except ImportError:
    _KiwiClass = None  # type: ignore[assignment,misc]


def _get_kiwi() -> Optional[Any]:
    """Kiwi 인스턴스 싱글톤"""
    global _KIWI
    if not _USE_KIWI:
        return None
    if _KIWI is None:
        _KIWI = _KiwiClass()
    return _KIWI


def extract_korean_nouns(text: str) -> List[str]:
    if not text or not text.strip():
        return []

    kiwi = _get_kiwi()
    if kiwi is not None:
        try:
            tokens = kiwi.tokenize(text)
            nouns = [
                token.form
                for token in tokens
                if token.tag.startswith("NN") and len(token.form) >= 2
            ]
            return list(dict.fromkeys(nouns))  # 순서 유지 중복 제거
        except Exception:
            pass

    return list(dict.fromkeys(re.findall(r"[가-힣]{2,}", text)))


def extract_keywords_advanced(text: str) -> List[str]:
    if not text:
        return []
    keywords = []
    keywords.extend(extract_korean_nouns(text))
    keywords.extend(re.findall(r"[A-Za-z]{2,}", text))
    keywords.extend(re.findall(r"\d+[가-힣%]+|\d+[a-zA-Z%]+", text))
    return list(dict.fromkeys(keywords))


def _cosine_similarity(vec1: Dict[int, float], vec2: Dict[int, float]) -> float:
    """두 희박 벡터 간 코사인 유사도"""
    if not vec1 or not vec2:
        return 0.0

    common_indices = set(vec1.keys()) & set(vec2.keys())
    dot = sum(vec1[i] * vec2[i] for i in common_indices)

    norm1 = sum(v * v for v in vec1.values()) ** 0.5
    norm2 = sum(v * v for v in vec2.values()) ** 0.5

    if not norm1 or not norm2:
        return 0.0

    return dot / (norm1 * norm2)


def compute_embedding_similarity(text1: str, text2: str) -> float:
    if not text1.strip() or not text2.strip():
        return 0.0

    model = _get_embedding_model()
    if model is None:
        return -1.0  # 모델 없음 표시

    try:
        embeddings = model.encode([text1, text2], normalize_embeddings=True)
        vec1 = (
            embeddings[0].tolist()
            if hasattr(embeddings[0], "tolist")
            else list(embeddings[0])
        )
        vec2 = (
            embeddings[1].tolist()
            if hasattr(embeddings[1], "tolist")
            else list(embeddings[1])
        )
        similarity = sum(a * b for a, b in zip(vec1, vec2))
        return max(0.0, min(1.0, similarity))
    except Exception as e:
        logger.warning(f"임베딩 유사도 계산 실패: {e}")
        return -1.0


def compute_batch_embedding_similarity(query: str, documents: List[str]) -> List[float]:
    if not query.strip() or not documents:
        return [0.0] * len(documents)

    model = _get_embedding_model()
    if model is None:
        return [-1.0] * len(documents)

    try:
        all_texts = [query] + documents
        embeddings = model.encode(all_texts, normalize_embeddings=True)
        query_vec = (
            embeddings[0].tolist()
            if hasattr(embeddings[0], "tolist")
            else list(embeddings[0])
        )

        similarities = []
        for i in range(1, len(embeddings)):
            doc_vec = (
                embeddings[i].tolist()
                if hasattr(embeddings[i], "tolist")
                else list(embeddings[i])
            )
            sim = sum(a * b for a, b in zip(query_vec, doc_vec))
            similarities.append(max(0.0, min(1.0, sim)))

        return similarities
    except Exception as e:
        logger.warning(f"배치 임베딩 유사도 계산 실패: {e}")
        return [-1.0] * len(documents)


def compute_tfidf_similarity(text1: str, text2: str) -> float:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return max(0.0, float(sim))
    except ImportError:
        return -1.0
    except Exception:
        return 0.0


def _extract_features(text: str) -> List[str]:
    """텍스트에서 특성 추출 (토큰 + 바이그램)"""
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
    compact = re.sub(r"\s+", "", text.lower())
    bigrams = [
        compact[i : i + 2]
        for i in range(len(compact) - 1)
        if compact[i : i + 2].strip()
    ]
    return tokens + bigrams


def _text_to_sparse_vector(text: str, dim: int = 256) -> Dict[int, float]:
    vec: Dict[int, float] = {}
    for feature in _extract_features(text):
        idx = int(hashlib.md5(feature.encode("utf-8")).hexdigest(), 16) % dim
        vec[idx] = vec.get(idx, 0.0) + 1.0
    return vec


def compute_hash_similarity(text1: str, text2: str) -> float:
    if not text1.strip() or not text2.strip():
        return 0.0

    vec1 = _text_to_sparse_vector(text1)
    vec2 = _text_to_sparse_vector(text2)
    return _cosine_similarity(vec1, vec2)


def compute_similarity(
    text1: str,
    text2: str,
    config: Optional[SemanticSearchConfig] = None,
) -> Tuple[float, str]:
    if config is None:
        config = SemanticSearchConfig()

    # 1. 임베딩 시도
    if config.use_embedding:
        emb_sim = compute_embedding_similarity(text1, text2)
        if emb_sim >= 0:
            return emb_sim, "embedding"

    # 2. TF-IDF 폴백
    if config.use_tfidf_fallback:
        tfidf_sim = compute_tfidf_similarity(text1, text2)
        if tfidf_sim >= 0:
            return tfidf_sim, "tfidf"

    # 3. 해시 기반 최후 폴백
    hash_sim = compute_hash_similarity(text1, text2)
    return hash_sim, "hash"


class SemanticSearchEngine:

    def __init__(self, config: Optional[SemanticSearchConfig] = None):
        self.config = config or SemanticSearchConfig()
        self._doc_cache: Dict[str, str] = {}
        self._embedding_cache: Dict[str, Any] = {}

    def index_documents(self, documents: Dict[str, str]) -> None:
        self._doc_cache.update(documents)

        # 임베딩 사전 계산 (배치)
        if is_embedding_available() and documents:
            model = _get_embedding_model()
            if model is not None:
                try:
                    ids = list(documents.keys())
                    texts = list(documents.values())
                    embeddings = model.encode(texts, normalize_embeddings=True)
                    for doc_id, emb in zip(ids, embeddings):
                        self._embedding_cache[doc_id] = (
                            emb.tolist() if hasattr(emb, "tolist") else list(emb)
                        )
                    logger.info(f"{len(documents)}개 문서 임베딩 인덱싱 완료")
                except Exception as e:
                    logger.warning(f"배치 인덱싱 실패: {e}")

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[SemanticMatch]:
        if not query.strip() or not self._doc_cache:
            return []

        k = top_k or self.config.top_k
        min_s = min_score if min_score is not None else self.config.min_score

        # 배치 유사도 계산
        if self._embedding_cache and is_embedding_available():
            results = self._search_with_cached_embeddings(query, k, min_s)
        else:
            results = self._search_without_cache(query, k, min_s)

        return results

    def _search_with_cached_embeddings(
        self, query: str, top_k: int, min_score: float
    ) -> List[SemanticMatch]:
        """캐시된 임베딩을 사용한 검색"""
        model = _get_embedding_model()
        if model is None:
            return self._search_without_cache(query, top_k, min_score)

        try:
            query_emb = model.encode(query, normalize_embeddings=True)
            query_vec = (
                query_emb.tolist() if hasattr(query_emb, "tolist") else list(query_emb)
            )

            matches = []
            for doc_id, doc_emb in self._embedding_cache.items():
                sim = sum(a * b for a, b in zip(query_vec, doc_emb))
                sim = max(0.0, min(1.0, sim))
                if sim >= min_score:
                    matches.append(
                        SemanticMatch(
                            doc_id=doc_id,
                            score=sim,
                            query_text=query,
                            doc_text=self._doc_cache.get(doc_id, ""),
                            method="embedding",
                        )
                    )

            matches.sort(key=lambda m: m.score, reverse=True)
            return matches[:top_k]
        except Exception as e:
            logger.warning(f"캐시 임베딩 검색 실패: {e}")
            return self._search_without_cache(query, top_k, min_score)

    def _search_without_cache(
        self, query: str, top_k: int, min_score: float
    ) -> List[SemanticMatch]:
        """캐시 없이 직접 계산하는 검색"""
        matches = []

        for doc_id, doc_text in self._doc_cache.items():
            score, method = compute_similarity(query, doc_text, self.config)
            if score >= min_score:
                matches.append(
                    SemanticMatch(
                        doc_id=doc_id,
                        score=score,
                        query_text=query,
                        doc_text=doc_text,
                        method=method,
                    )
                )

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:top_k]

    def find_best_match(
        self,
        query: str,
        candidates: Optional[List[str]] = None,
    ) -> Optional[SemanticMatch]:
        if candidates:
            docs = {
                cid: self._doc_cache[cid]
                for cid in candidates
                if cid in self._doc_cache
            }
            old_cache = self._doc_cache
            self._doc_cache = docs
            results = self.search(query, top_k=1)
            self._doc_cache = old_cache
        else:
            results = self.search(query, top_k=1)

        return results[0] if results else None

    def get_stats(self) -> Dict[str, Any]:
        """검색 엔진 통계"""
        return {
            "indexed_documents": len(self._doc_cache),
            "cached_embeddings": len(self._embedding_cache),
            "embedding_available": is_embedding_available(),
            "method": "embedding" if is_embedding_available() else "tfidf/hash",
        }


def match_experiences_to_questions(
    questions: List[str],
    experiences: Dict[str, str],
    config: Optional[SemanticSearchConfig] = None,
) -> Dict[str, List[SemanticMatch]]:
    engine = SemanticSearchEngine(config)
    engine.index_documents(experiences)

    results = {}
    for question in questions:
        matches = engine.search(question, top_k=3)
        results[question] = matches

    return results


def extract_semantic_keywords(text: str) -> Dict[str, List[str]]:
    return {
        "nouns": extract_korean_nouns(text),
        "keywords": extract_keywords_advanced(text),
        "numeric": re.findall(r"\d+[가-힣%]+|\d+[a-zA-Z%]+|\d{2,}", text),
    }
