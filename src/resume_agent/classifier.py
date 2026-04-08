import importlib
import re
from typing import Dict, List, Optional, Tuple
from .models import QuestionType, Question, Experience
from .experience_analyzer import ExperienceDeepAnalyzer
from .config import get_config_value

QUESTION_TYPE_PATTERNS = {
    QuestionType.TYPE_A: [
        r"지원동기",
        r"지원.*이유",
        r"왜 .*지원",
        r"직무.*적합",
        r"관심.*계기",
    ],
    QuestionType.TYPE_B: [r"직무역량", r"역량", r"강점", r"업무 수행.*노력", r"전문성"],
    QuestionType.TYPE_C: [r"협업", r"협력", r"갈등", r"소통", r"의사소통", r"팀워크"],
    QuestionType.TYPE_D: [r"성장", r"배운 점", r"자기개발", r"학습", r"개선", r"보완"],
    QuestionType.TYPE_E: [r"입사 후", r"포부", r"기여", r"발전 방향", r"향후 계획"],
    QuestionType.TYPE_F: [r"원칙", r"기준", r"신뢰", r"책임감", r"약속"],
    QuestionType.TYPE_G: [r"실패", r"어려운 문제", r"극복", r"위기", r"재발 방지"],
    QuestionType.TYPE_H: [r"고객", r"민원", r"응대", r"만족", r"보호자", r"서비스"],
    QuestionType.TYPE_I: [
        r"우선순위",
        r"압박",
        r"판단",
        r"시간",
        r"제한된 자원",
        r"협상",
    ],
}

QUESTION_TYPE_LABELS = {
    QuestionType.TYPE_A: "지원동기와 직무 적합성",
    QuestionType.TYPE_B: "핵심 역량",
    QuestionType.TYPE_C: "협업과 조정",
    QuestionType.TYPE_D: "성장과 학습 루프",
    QuestionType.TYPE_E: "입사 후 기여",
    QuestionType.TYPE_F: "원칙과 신뢰",
    QuestionType.TYPE_G: "실패와 복기",
    QuestionType.TYPE_H: "고객응대",
    QuestionType.TYPE_I: "상황판단과 우선순위",
    QuestionType.TYPE_UNKNOWN: "분류 불가 (확인 필요)",
}

STOPWORDS = {
    "자기소개서",
    "기술",
    "주십시오",
    "무엇",
    "통해",
    "본인",
    "지원",
    "직무",
    "경험",
    "입사",
    "이후",
    "관련",
}

TAG_HINTS = {
    QuestionType.TYPE_A: {"직무역량", "성과"},
    QuestionType.TYPE_B: {"직무역량", "데이터", "문제해결"},
    QuestionType.TYPE_C: {"협업", "의사소통", "리더십"},
    QuestionType.TYPE_D: {"성장", "문제해결"},
    QuestionType.TYPE_E: {"직무역량", "성과"},
    QuestionType.TYPE_F: {"성과", "의사소통"},
    QuestionType.TYPE_G: {"실패", "문제해결"},
    QuestionType.TYPE_H: {"고객응대", "의사소통"},
    QuestionType.TYPE_I: {"상황판단", "문제해결"},
    QuestionType.TYPE_UNKNOWN: set(),
}

MARKETING_PATTERNS = [
    "링커리어 자소서 만능검색기",
    "더 많은 최신 합격 자소서",
    "더 많은 자소서가 궁금하다면",
    "문항별 예시는",
    "AI 개요",
    "합격 자소서 함께 확인",
    "자소서 함께 확인하세요",
    "스크랩 TOP 자소서 함께 확인",
    "최신 자소서 함께 확인",
]


def classify_question(text: str) -> QuestionType:
    """
    질문 텍스트를 분류하여 QuestionType을 반환합니다.
    매칭 실패 시 임베딩 기반 폴백을 시도합니다.
    둘 다 실패하면 TYPE_UNKNOWN을 반환합니다.
    """
    normalized = text.strip()
    for question_type, patterns in QUESTION_TYPE_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            return question_type

    emb_type, _ = classify_question_by_embedding(text)
    return emb_type


def classify_question_regex_only(text: str) -> QuestionType:
    """임베딩 폴백 없이 정규식 패턴만으로 질문 유형을 분류합니다."""
    normalized = text.strip()
    for question_type, patterns in QUESTION_TYPE_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            return question_type
    return QuestionType.TYPE_UNKNOWN


def classify_question_with_confidence(text: str) -> Tuple[QuestionType, float]:
    """
    질문 텍스트를 분류하고 confidence score를 함께 반환합니다.
    regex 매칭 실패 시 임베딩 폴백을 시도합니다.

    Returns:
        (QuestionType, confidence) 튜플
        confidence: 0.0 ~ 1.0
    """
    normalized = text.strip()
    best_type = QuestionType.TYPE_UNKNOWN
    best_score = 0.0

    for question_type, patterns in QUESTION_TYPE_PATTERNS.items():
        match_count = sum(1 for p in patterns if re.search(p, normalized))
        if match_count > best_score:
            best_score = match_count
            best_type = question_type

    if best_score > 0:
        total_patterns = len(QUESTION_TYPE_PATTERNS.get(best_type, []))
        confidence = min(best_score / max(total_patterns, 1), 1.0)
        return best_type, confidence

    return classify_question_by_embedding(text)


def extract_question_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z가-힣]{2,}", text)
    seen: List[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token not in seen:
            seen.append(token)
    return seen[:8]


_TYPE_REPRESENTATIVES: Dict[QuestionType, List[str]] = {
    QuestionType.TYPE_A: [
        "지원 동기", "직무 적합", "지원 이유", "왜 지원", "관심 계기",
    ],
    QuestionType.TYPE_B: [
        "직무 역량", "업무 수행", "전문성", "핵심 역량", "강점 활용",
    ],
    QuestionType.TYPE_C: [
        "협업", "팀원 갈등", "소통", "협력", "의사소통",
    ],
    QuestionType.TYPE_D: [
        "실패", "배운 점", "자기개발", "학습", "성장",
    ],
    QuestionType.TYPE_E: [
        "입사 후 기여", "포부", "성장 계획", "회사 발전", "역할",
    ],
    QuestionType.TYPE_F: [
        "원칙", "신뢰", "책임감", "약속", "윤리",
    ],
    QuestionType.TYPE_G: [
        "실패 극복", "어려운 문제", "위기 상황", "재발 방지",
    ],
    QuestionType.TYPE_H: [
        "고객 응대", "민원 해결", "고객 만족", "보호자",
    ],
    QuestionType.TYPE_I: [
        "우선순위", "압박 상황", "판단", "시간 부족", "자원 제한",
    ],
}

_TYPE_CENTROIDS: Optional[Dict[QuestionType, List[float]]] = None
_ST_MODEL_CLS = None
_ST_CLASS_CLS = None


def _get_st_model_classifier():
    global _ST_MODEL_CLS, _ST_CLASS_CLS
    if _ST_CLASS_CLS is None:
        try:
            module = importlib.import_module("sentence_transformers")
            _ST_CLASS_CLS = getattr(module, "SentenceTransformer", None)
        except ImportError:
            _ST_CLASS_CLS = False
    if _ST_CLASS_CLS in (None, False):
        return None
    if _ST_MODEL_CLS is None:
        model_name = get_config_value(
            "embedding.model_name", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        _ST_MODEL_CLS = _ST_CLASS_CLS(model_name)
    return _ST_MODEL_CLS


def _compute_type_centroids() -> Optional[Dict[QuestionType, List[float]]]:
    """질문 유형별 대표 문장의 임베딩 centroid를 계산합니다."""
    global _TYPE_CENTROIDS
    if _TYPE_CENTROIDS is not None:
        return _TYPE_CENTROIDS

    model = _get_st_model_classifier()
    if model is None:
        return None

    try:
        centroids: Dict[QuestionType, List[float]] = {}
        for qtype, sentences in _TYPE_REPRESENTATIVES.items():
            vecs = model.encode(sentences, normalize_embeddings=True)
            import numpy as np

            centroid = vecs.mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            centroids[qtype] = centroid.tolist()
        _TYPE_CENTROIDS = centroids
        return centroids
    except Exception:
        return None


def _cosine_similarity_classifier(vec1: List[float], vec2: List[float]) -> float:
    if len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    n1 = sum(a * a for a in vec1) ** 0.5
    n2 = sum(b * b for b in vec2) ** 0.5
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def classify_question_by_embedding(text: str) -> Tuple[QuestionType, float]:
    """
    임베딩 기반 질문 분류 (폴백).
    regex가 TYPE_UNKNOWN을 반환할 때 사용.

    Returns:
        (QuestionType, confidence) 튜플
    """
    centroids = _compute_type_centroids()
    if centroids is None:
        return QuestionType.TYPE_UNKNOWN, 0.0

    model = _get_st_model_classifier()
    if model is None:
        return QuestionType.TYPE_UNKNOWN, 0.0

    try:
        q_vec = model.encode(text, normalize_embeddings=True)
        q_list = q_vec.tolist() if hasattr(q_vec, "tolist") else list(q_vec)

        best_type = QuestionType.TYPE_UNKNOWN
        best_sim = 0.0
        for qtype, centroid in centroids.items():
            sim = _cosine_similarity_classifier(q_list, centroid)
            if sim > best_sim:
                best_sim = sim
                best_type = qtype

        if best_sim < 0.3:
            return QuestionType.TYPE_UNKNOWN, best_sim

        confidence = min(1.0, best_sim)
        return best_type, confidence
    except Exception:
        return QuestionType.TYPE_UNKNOWN, 0.0


def classify_question_type(text: str, config: dict) -> QuestionType:
    """질문 텍스트를 기반으로 유형을 분류합니다.
    
    기존 classify_question 함수를 래핑하여 config 기반 동작을 제공합니다.
    """
    return classify_question(text)


def classify_with_experience_hints(
    questions: List["Question"],
    experiences: List["Experience"],
    config: dict,
    use_deep_analysis: bool = True,
) -> dict:
    """경험 힌트를 활용한 질문 분류
    
    ExperienceDeepAnalyzer를 사용하여 질문의 숨겨진 의도를 분석하고,
    관련 경험과 매칭합니다.
    
    Args:
        questions: 분류할 질문 목록
        experiences: 사용자 경험 목록
        config: 설정 딕셔너리
        use_deep_analysis: ExperienceDeepAnalyzer 사용 여부
        
    Returns:
        {
            question_id: {
                "type": QuestionType,
                "intent_analysis": {...},
                "recommended_experiences": [...],
                "confidence_boost": bool
            }
        }
    """
    results = {}
    analyzer = ExperienceDeepAnalyzer()
    
    # 경험 핵심 역량 매핑
    exp_competencies = {}
    for exp in experiences:
        analysis = analyzer.analyze_core_competency(exp)
        exp_competencies[exp.id] = [c.competency for c in analysis]
    
    for question in questions:
        # 기존 분류
        base_type = classify_question_type(question.question_text, config)
        
        # 경험 기반 보완
        if use_deep_analysis:
            intent = analyzer.analyze_question_intent(question)
            
            # 경험 역량과 질문 의도 매칭
            matching_exp = []
            for exp_id, comps in exp_competencies.items():
                common = set(comps) & set(intent.core_competencies_sought)
                if common:
                    matching_exp.append({
                        "exp_id": exp_id,
                        "matched": list(common)
                    })
            
            # 가장 관련 깊은 경험 3개
            top_matching = sorted(
                matching_exp,
                key=lambda x: len(x["matched"]),
                reverse=True
            )[:3]
            
            results[question.id] = {
                "type": base_type,
                "intent_analysis": {
                    "hidden_intent": intent.hidden_intent,
                    "wanted_competencies": intent.core_competencies_sought,
                    "risk_topics": intent.risk_topics
                },
                "recommended_experiences": top_matching,
                "confidence_boost": len(top_matching) > 0
            }
        else:
            results[question.id] = {
                "type": base_type,
                "confidence_boost": False
            }
    
    return results
