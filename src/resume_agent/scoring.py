import importlib
import re
from typing import Any, List, Optional
from .models import (
    ApplicationProject,
    Experience,
    Question,
    QuestionType,
    EvidenceLevel,
    VerificationStatus,
)
from .classifier import (
    classify_question,
    extract_question_keywords,
    TAG_HINTS,
    QUESTION_TYPE_LABELS,
)
from .config import get_config_value


def _evidence_bonus(level: EvidenceLevel) -> int:
    bonus_map = get_config_value("scoring.evidence_bonus", {"L1": 1, "L2": 4, "L3": 8})
    return bonus_map.get(level.value, 0)


def _verified_bonus() -> int:
    return get_config_value("scoring.verified_bonus", 3)


def _unverified_penalty() -> int:
    return get_config_value("scoring.unverified_penalty", -2)


def _reuse_penalty() -> int:
    return get_config_value("scoring.reuse_penalty", 7)


def _same_org_penalty() -> int:
    return get_config_value("scoring.same_org_penalty", 4)


_SEMANTIC_EQUIVALENTS = {
    "민원": {"고객", "응대", "안내", "서비스"},
    "고객": {"민원", "응대", "안내", "서비스"},
    "협업": {"조율", "소통", "협력", "팀"},
    "소통": {"협업", "조율", "안내", "설명"},
    "문제": {"개선", "해결", "조치"},
    "직무": {"업무", "실무", "역할"},
}


def _extract_profile_snapshot(candidate_profile: dict[str, Any] | None) -> dict[str, Any]:
    if not candidate_profile:
        return {}
    nested = candidate_profile.get("personalized_profile")
    if isinstance(nested, dict):
        return nested
    return candidate_profile

# 임베딩 모듈 지연 로딩 (순환 import 방지)
_ST_MODEL_SCORING = None
_ST_CLASS_SCORING = None


def _get_st_model_scoring():
    global _ST_MODEL_SCORING, _ST_CLASS_SCORING
    if _ST_CLASS_SCORING is None:
        try:
            module = importlib.import_module("sentence_transformers")
            _ST_CLASS_SCORING = getattr(module, "SentenceTransformer", None)
        except ImportError:
            _ST_CLASS_SCORING = False
    if _ST_CLASS_SCORING in (None, False):
        return None
    if _ST_MODEL_SCORING is None:
        model_name = get_config_value(
            "embedding.model_name", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        _ST_MODEL_SCORING = _ST_CLASS_SCORING(model_name)
    return _ST_MODEL_SCORING


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    n1 = sum(a * a for a in vec1) ** 0.5
    n2 = sum(b * b for b in vec2) ** 0.5
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def _semantic_adjustment_embedding(
    question_text: str, haystack: str
) -> tuple[int, list[str]]:
    """SentenceTransformer 기반 의미적 유사도 가점 (최대 +3)"""
    model = _get_st_model_scoring()
    if model is None:
        return _semantic_adjustment_fallback(question_text, haystack)

    try:
        threshold = float(get_config_value("embedding.similarity_threshold", 0.35))
        max_bonus = int(get_config_value("embedding.max_semantic_bonus", 3))

        q_vec = model.encode(question_text, normalize_embeddings=True)
        h_vec = model.encode(haystack, normalize_embeddings=True)

        q_list = q_vec.tolist() if hasattr(q_vec, "tolist") else list(q_vec)
        h_list = h_vec.tolist() if hasattr(h_vec, "tolist") else list(h_vec)

        sim = _cosine_similarity(q_list, h_list)
        if sim < threshold:
            return 0, []

        adjustment = min(max_bonus, max(1, int(sim * max_bonus / 0.5)))
        return adjustment, ["질문과 경험의 의미 축이 임베딩 유사도로 연결되어 가점"]
    except Exception:
        return _semantic_adjustment_fallback(question_text, haystack)


def _semantic_adjustment_fallback(
    question_text: str, haystack: str
) -> tuple[int, list[str]]:
    """동의어 사전 기반 폴백"""
    question_tokens = {
        token for token in re.findall(r"[A-Za-z0-9가-힣]{2,}", question_text.lower())
    }
    hay_tokens = {
        token for token in re.findall(r"[A-Za-z0-9가-힣]{2,}", haystack.lower())
    }
    if not question_tokens or not hay_tokens:
        return 0, []

    hits = 0
    for token in question_tokens:
        related = _SEMANTIC_EQUIVALENTS.get(token, set())
        if related & hay_tokens:
            hits += 1
    if hits <= 0:
        return 0, []
    adjustment = min(3, hits)
    return adjustment, ["질문과 경험의 의미 축이 직접 연결되어 가점"]


def _semantic_adjustment(question_text: str, haystack: str) -> tuple[int, list[str]]:
    """의미적 유사도 가점 — 임베딩 우선, 폴백"""
    fallback_adjustment, fallback_notes = _semantic_adjustment_fallback(
        question_text, haystack
    )
    if fallback_adjustment > 0:
        return fallback_adjustment, fallback_notes
    embedding_adjustment, embedding_notes = _semantic_adjustment_embedding(
        question_text, haystack
    )
    if fallback_adjustment > embedding_adjustment:
        return fallback_adjustment, fallback_notes
    return embedding_adjustment, embedding_notes


def _outcome_alignment_adjustment(
    experience: Experience,
    outcome_summary: dict[str, Any] | None,
) -> tuple[int, list[str]]:
    if (
        not outcome_summary
        or int(outcome_summary.get("matched_feedback_count", 0)) <= 0
    ):
        return 0, []

    adjustment = 0
    notes: list[str] = []
    outcomes = outcome_summary.get("outcome_breakdown", {}) or {}
    pass_count = int(outcomes.get("pass", 0)) + int(outcomes.get("document_pass", 0))
    fail_count = int(outcomes.get("fail_interview", 0)) + int(
        outcomes.get("document_fail", 0)
    )

    rejection_text = " ".join(
        item.get("reason", "")
        for item in outcome_summary.get("top_rejection_reasons", [])
        if isinstance(item, dict)
    )

    if pass_count:
        if metric_present(experience):
            adjustment += 2
            notes.append("통과 사례 기준으로 수치 근거가 있는 경험을 우대")
        if experience.evidence_text.strip():
            adjustment += 1
            notes.append("통과 사례 기준으로 증빙이 있는 경험을 우대")
        if experience.personal_contribution.strip():
            adjustment += 1
            notes.append("통과 사례 기준으로 개인 기여가 분명한 경험을 우대")

    if fail_count and rejection_text:
        if (
            "근거" in rejection_text or "수치" in rejection_text
        ) and not metric_present(experience):
            adjustment -= 3
            notes.append("과거 실패 이유가 근거 부족이라 수치 없는 경험을 감점")
        if (
            "개인" in rejection_text or "기여" in rejection_text
        ) and not experience.personal_contribution.strip():
            adjustment -= 2
            notes.append(
                "과거 실패 이유가 개인 기여 불명확이라 개인 역할이 약한 경험을 감점"
            )
        if (
            "증빙" in rejection_text or "검증" in rejection_text
        ) and not experience.evidence_text.strip():
            adjustment -= 2
            notes.append("과거 실패 이유가 검증 취약이라 증빙 없는 경험을 감점")

    return adjustment, notes


def _strategy_outcome_adjustment(
    question_type: QuestionType,
    experience: Experience,
    strategy_outcome_summary: dict[str, Any] | None,
    current_pattern: str | None,
) -> tuple[int, list[str]]:
    if not strategy_outcome_summary:
        return 0, []

    type_stats = (
        strategy_outcome_summary.get("experience_stats_by_question_type", {}) or {}
    ).get(question_type.value, {})
    exp_stats = type_stats.get(experience.id)
    if not isinstance(exp_stats, dict):
        return 0, []

    bucket = exp_stats
    note_prefix = "실제 결과 통계"
    if current_pattern:
        pattern_bucket = (exp_stats.get("pattern_breakdown", {}) or {}).get(
            current_pattern
        )
        if (
            isinstance(pattern_bucket, dict)
            and int(pattern_bucket.get("total_uses", 0)) > 0
        ):
            bucket = pattern_bucket
            note_prefix = "실제 결과 통계(동일 패턴)"

    total_uses = int(bucket.get("total_uses", 0))
    pass_count = int(bucket.get("pass_count", 0))
    fail_count = int(bucket.get("fail_count", 0))
    if total_uses <= 0:
        return 0, []

    min_samples = int(get_config_value("scoring.strategy_outcome_min_samples", 3))
    strong_samples = int(get_config_value("scoring.strategy_outcome_strong_samples", 5))
    weighted_margin = int(bucket.get("weighted_net_score", 0))
    if not weighted_margin:
        weighted_margin = int(bucket.get("weighted_pass_score", 0)) - int(
            bucket.get("weighted_fail_score", 0)
        )
    margin = weighted_margin or (pass_count - fail_count)
    if total_uses < min_samples:
        cap = 1
    elif total_uses < strong_samples:
        cap = 2
    else:
        cap = 4

    if margin > 0:
        adjustment = min(cap, max(1, abs(margin)))
        notes = [
            f"{note_prefix}에서 {question_type.value} 문항에 이 경험의 통과 비중이 높아 가점",
        ]
        if total_uses < min_samples:
            notes.append("표본 수가 적어 결과 통계 가중치는 약하게 반영")
        return adjustment, notes
    if margin < 0:
        adjustment = -min(cap, max(1, abs(margin)))
        reasons = (
            bucket.get("top_rejection_reasons")
            or exp_stats.get("top_rejection_reasons")
            or []
        )
        reason_hint = ""
        if reasons and isinstance(reasons[0], dict):
            reason_hint = reasons[0].get("reason", "")
        notes = [
            f"{note_prefix}에서 {question_type.value} 문항에 이 경험의 실패 비중이 높아 감점"
        ]
        if total_uses < min_samples:
            notes.append("표본 수가 적어 결과 통계 가중치는 약하게 반영")
        if reason_hint:
            notes.append(f"주요 실패 사유: {reason_hint}")
        return adjustment, notes
    return 0, []


def _feedback_adaptation_adjustment(
    question_type: QuestionType,
    experience: Experience,
    feedback_adaptation_plan: dict[str, Any] | None,
) -> tuple[int, list[str]]:
    if not feedback_adaptation_plan:
        return 0, []

    risky_question_types = feedback_adaptation_plan.get("risky_question_types", []) or []
    for item in risky_question_types:
        if str(item.get("question_type", "")).strip() != question_type.value:
            continue
        for weak in item.get("weak_experiences", []) or []:
            if str(weak.get("experience_id", "")).strip() != experience.id:
                continue
            reasons = weak.get("top_rejection_reasons", []) or []
            reason_hint = ""
            if reasons and isinstance(reasons[0], dict):
                reason_hint = str(reasons[0].get("reason", "")).strip()
            notes = [
                f"학습 적응 계획에서 {question_type.value} 문항에 이 경험이 반복 취약 경험으로 식별되어 감점"
            ]
            if reason_hint:
                notes.append(f"반복 탈락 사유: {reason_hint}")
            return -12, notes
    return 0, []


def _personalization_adjustment(
    experience: Experience,
    candidate_profile: dict[str, Any] | None,
) -> tuple[int, list[str]]:
    profile = _extract_profile_snapshot(candidate_profile)
    if not profile:
        return 0, []

    strengths = {
        str(item).strip().lower()
        for item in profile.get("strength_keywords", []) or []
        if str(item).strip()
    }
    weakness_codes = {
        str(item).strip() for item in profile.get("weakness_codes", []) or []
    }
    style = profile.get("writing_style", {}) or {}
    haystack = " ".join(
        [experience.title, experience.action, experience.result, " ".join(experience.tags)]
    ).lower()

    adjustment = 0
    notes: list[str] = []
    if any(keyword and keyword.lower() in haystack for keyword in strengths):
        adjustment += 2
        notes.append("지원자 고유 강점과 맞닿는 경험이라 가점")
    if "low_metrics" in weakness_codes and not metric_present(experience):
        adjustment -= 2
        notes.append("지원자 약점이 수치 부족이라 정량 근거 없는 경험을 감점")
    if "low_contribution" in weakness_codes and not experience.personal_contribution.strip():
        adjustment -= 2
        notes.append("지원자 약점이 개인 기여 불명확이라 기여도 약한 경험을 감점")
    if "low_evidence" in weakness_codes and not experience.evidence_text.strip():
        adjustment -= 1
        notes.append("지원자 약점이 증빙 부족이라 근거 없는 경험을 감점")
    if style.get("dominant_tone") == "logical" and metric_present(experience):
        adjustment += 1
        notes.append("현재 지원자 문체와 잘 맞는 근거 중심 경험이라 가점")
    return adjustment, notes


def metric_present(experience: Experience) -> bool:
    metric_text = experience.metrics.strip()
    return bool(metric_text and metric_text != "정량 수치 없음")


def _build_allocation_reason(
    question: Question,
    question_type: QuestionType,
    experience: Experience,
    keywords: List[str],
    outcome_notes: List[str] | None = None,
) -> str:
    expected = QUESTION_TYPE_LABELS.get(question_type, question_type.value)
    keyword_hint = ", ".join(keywords[:3]) or "핵심 키워드 미상"

    strengths: list[str] = []
    if metric_present(experience):
        strengths.append(f"정량 근거({experience.metrics.strip()})")
    if experience.evidence_text.strip():
        strengths.append("면접에서 다시 꺼낼 증빙 문장 보유")
    if experience.personal_contribution.strip():
        strengths.append("개인 기여를 분리해 설명 가능")
    if not strengths:
        strengths.append("상황-행동-결과 흐름이 비교적 선명함")

    follow_ups: list[str] = []
    if not metric_present(experience):
        follow_ups.append("성과를 어떻게 비교·측정했는지")
    if not experience.personal_contribution.strip():
        follow_ups.append("팀 성과 중 본인 지분이 정확히 무엇인지")
    if not experience.evidence_text.strip():
        follow_ups.append("근거 자료나 현장 기록이 무엇인지")
    if not follow_ups:
        follow_ups.append("왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지")

    lines = [
        f"질문 기대: {expected} 문항이며, 질문 키워드({keyword_hint})와 가장 직접적으로 맞닿아 있습니다.",
        f"이 경험의 강점: {' / '.join(strengths[:3])}.",
        f"면접관 꼬리질문: {' / '.join(follow_ups[:3])}를 30초 안에 방어할 준비가 필요합니다.",
    ]
    if outcome_notes:
        lines.append(f"결과 학습 반영: {' / '.join(outcome_notes[:2])}.")
    return "\n".join(lines)


def score_experience(
    question: Question | Experience,
    experience: Experience | None = None,
    priority_order: List[str] | None = None,
    already_used: List[str] | None = None,
    previous_organization: Optional[str] = None,
    outcome_summary: dict[str, Any] | None = None,
    strategy_outcome_summary: dict[str, Any] | None = None,
    current_pattern: str | None = None,
    feedback_adaptation_plan: dict[str, Any] | None = None,
    candidate_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if experience is None and isinstance(question, Experience):
        experience = question
        question = Question(
            id="legacy-score",
            order_no=1,
            question_text=experience.title or "경험 적합도",
            detected_type=QuestionType.TYPE_UNKNOWN,
        )
    if experience is None:
        raise TypeError("experience is required")

    priority_order = priority_order or []
    already_used = already_used or []

    question_text = question.question_text
    question_type = getattr(question, "detected_type", None)
    if not isinstance(question_type, QuestionType) or question_type == QuestionType.TYPE_UNKNOWN:
        question_type = classify_question(question_text)
    keywords = extract_question_keywords(question_text)

    haystack = " ".join(
        [
            experience.title,
            experience.organization,
            experience.situation,
            experience.task,
            experience.action,
            experience.result,
            experience.personal_contribution,
            experience.metrics,
            experience.evidence_text,
        ]
    )
    tags = set(experience.tags)

    score = _evidence_bonus(experience.evidence_level)
    score += (
        _verified_bonus()
        if experience.verification_status == VerificationStatus.VERIFIED
        else _unverified_penalty()
    )
    score += sum(1 for keyword in keywords if keyword in haystack) * 2
    score += len(tags & TAG_HINTS.get(question_type, set())) * 3
    if metric_present(experience):
        score += 2
    semantic_adjustment, semantic_notes = _semantic_adjustment(question_text, haystack)
    score += semantic_adjustment
    if experience.title in priority_order:
        score += (len(priority_order) - priority_order.index(experience.title)) * 3
    if experience.id in already_used:
        score -= _reuse_penalty()
    if (
        previous_organization
        and previous_organization == experience.organization.strip()
    ):
        score -= _same_org_penalty()
    outcome_adjustment, outcome_notes = _outcome_alignment_adjustment(
        experience,
        outcome_summary,
    )
    score += outcome_adjustment
    strategy_adjustment, strategy_notes = _strategy_outcome_adjustment(
        question_type,
        experience,
        strategy_outcome_summary,
        current_pattern,
    )
    score += strategy_adjustment
    adaptation_adjustment, adaptation_notes = _feedback_adaptation_adjustment(
        question_type,
        experience,
        feedback_adaptation_plan,
    )
    score += adaptation_adjustment
    personalization_adjustment, personalization_notes = _personalization_adjustment(
        experience,
        candidate_profile,
    )
    score += personalization_adjustment

    return {
        "score": score,
        "question_type": question_type,
        "keywords": keywords,
        "outcome_adjustment": outcome_adjustment,
        "strategy_adjustment": strategy_adjustment,
        "adaptation_adjustment": adaptation_adjustment,
        "personalization_adjustment": personalization_adjustment,
        "semantic_adjustment": semantic_adjustment,
        "outcome_notes": [
            *outcome_notes,
            *strategy_notes,
            *adaptation_notes,
            *personalization_notes,
        ],
        "semantic_notes": semantic_notes,
    }


def find_experience(
    experiences: List[Experience], experience_id: str
) -> Optional[Experience]:
    for experience in experiences:
        if experience.id == experience_id:
            return experience
    return None


def allocate_experiences(
    questions: List[Question],
    experiences: List[Experience],
    priority_order: List[str],
    outcome_summary: dict[str, Any] | None = None,
    strategy_outcome_summary: dict[str, Any] | None = None,
    current_pattern: str | None = None,
    feedback_adaptation_plan: dict[str, Any] | None = None,
    candidate_profile: dict[str, Any] | None = None,
) -> List[dict[str, Any]]:
    allocations: List[dict[str, Any]] = []
    used_experience_ids: List[str] = []
    previous_organization: Optional[str] = None

    for question in questions:
        candidates = [
            {
                "experience": exp,
                "detail": score_experience(
                    question,
                    exp,
                    priority_order,
                    used_experience_ids,
                    previous_organization,
                    outcome_summary,
                    strategy_outcome_summary,
                    current_pattern,
                    feedback_adaptation_plan,
                    candidate_profile,
                ),
            }
            for exp in experiences
        ]
        candidates.sort(key=lambda item: item["detail"]["score"], reverse=True)
        if not candidates:
            continue
        picked = candidates[0]
        exp = picked["experience"]
        detail = picked["detail"]
        allocations.append(
            {
                "question_id": question.id,
                "order_no": question.order_no,
                "question_type": detail["question_type"],
                "experience_id": exp.id,
                "experience_title": exp.title,
                "score": detail["score"],
                "reason": (
                    _build_allocation_reason(
                        question,
                        detail["question_type"],
                        exp,
                        detail["keywords"],
                        detail.get("outcome_notes"),
                    )
                ),
                "reuse_reason": (
                    "다른 경험보다 적합도가 높아 재사용되었으며 관점을 다르게 써야 합니다."
                    if exp.id in used_experience_ids
                    else None
                ),
            }
        )
        used_experience_ids.append(exp.id)
        previous_organization = exp.organization.strip() or None

    # Force L3 if available and not used
    if allocations and not any(
        find_experience(experiences, item["experience_id"]).evidence_level
        == EvidenceLevel.L3
        for item in allocations
    ):
        l3_candidates = [
            exp for exp in experiences if exp.evidence_level == EvidenceLevel.L3
        ]
        if l3_candidates:
            strongest = l3_candidates[0]
            allocations[0]["experience_id"] = strongest.id
            allocations[0]["experience_title"] = strongest.title
            allocations[0]["reason"] += (
                " 최소 1개의 L3 경험을 상위 문항에 강제로 배치했습니다."
            )

    return allocations


def analyze_gaps(
    project: ApplicationProject, experiences: List[Experience]
) -> dict[str, Any]:
    questions = project.questions
    missing_metrics = [exp.title for exp in experiences if not metric_present(exp)]
    missing_evidence = [
        exp.title for exp in experiences if not exp.evidence_text.strip()
    ]
    needs_verification = [
        exp.title
        for exp in experiences
        if exp.verification_status != VerificationStatus.VERIFIED
    ]
    l3_count = sum(1 for exp in experiences if exp.evidence_level == EvidenceLevel.L3)

    question_risks: List[dict[str, Any]] = []
    for question in questions:
        candidates = [
            score_experience(question, exp, project.priority_experience_order, [], None)
            for exp in experiences
        ]
        best_score = max((item["score"] for item in candidates), default=0)
        risk_thresholds = get_config_value(
            "gap_analysis.risk_thresholds", {"high": 5, "medium": 10}
        )
        question_risks.append(
            {
                "question_id": question.id,
                "order_no": question.order_no,
                "question_type": classify_question(question.question_text),
                "best_score": best_score,
                "risk": "high"
                if best_score < risk_thresholds.get("high", 5)
                else "medium"
                if best_score < risk_thresholds.get("medium", 10)
                else "low",
            }
        )

    summary = [
        f"질문 수: {len(questions)}",
        f"경험 수: {len(experiences)}",
        f"L3 경험 수: {l3_count}",
        f"검증 필요 경험 수: {len(needs_verification)}",
    ]
    recommendations: List[str] = []
    if not experiences:
        recommendations.append("경험 카드가 비어 있어 coach 단계를 진행할 수 없습니다.")
    if l3_count == 0:
        recommendations.append("최소 1개의 L3 증거 경험을 추가하세요.")
    if missing_metrics:
        recommendations.append(
            "정량 근거가 비어 있는 경험에 수치 또는 비교 근거를 보강하세요."
        )
    if missing_evidence:
        recommendations.append("면접에서 방어 가능한 증빙 텍스트를 추가하세요.")
    if any(item["risk"] == "high" for item in question_risks):
        recommendations.append("일부 문항은 현재 경험 데이터와의 적합도가 낮습니다.")

    return {
        "summary": summary,
        "missing_metrics": missing_metrics,
        "missing_evidence": missing_evidence,
        "needs_verification": needs_verification,
        "question_risks": question_risks,
        "recommendations": recommendations
        or ["즉시 보강이 필요한 위험 신호가 크지 않습니다."],
    }


def calculate_readability_score(text: str) -> dict[str, Any]:
    """텍스트의 가독성 점수와 개선 피드백을 반환합니다."""
    import re

    if not text.strip():
        return {"score": 0, "feedback": ["내용이 없습니다."]}

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    avg_len = sum(len(s) for s in sentences) / len(sentences) if sentences else 0

    score = 100
    feedback = []

    if avg_len > 80:
        score -= 15
        feedback.append("문장이 너무 깁니다. (평균 80자 초과)")
    elif avg_len < 30:
        score -= 5
        feedback.append("문장이 너무 짧아 흐름이 끊길 수 있습니다.")

    star_keywords = ["상황", "과제", "문제", "행동", "해결", "결과", "성과"]
    matched_star = sum(1 for kw in star_keywords if kw in text)
    if matched_star < 2:
        score -= 20
        feedback.append(
            "STAR(상황/행동/결과) 구조를 나타내는 명확한 표현이 부족합니다."
        )

    return {"score": max(0, score), "feedback": feedback or ["가독성이 좋습니다."]}


def audit_facts(generated_text: str, source_experiences: List[Experience]) -> List[str]:
    """생성된 텍스트에 포함된 수치가 원본 경험 데이터에 존재하는지 엄격하게 검증합니다."""
    import re

    warnings = []

    # 1. 정교한 수치 패턴 추출 (숫자+단위 결합)
    metric_patterns = [
        r"\d+(?:\.\d+)?%",
        r"\d+건",
        r"\d+명",
        r"\d+배",
        r"\d+위",
        r"\d+시간",
        r"\d+일",
        r"\d+개월",
        r"\d+년",
        r"\d+월",
        r"\d+\.\d+/\d+\.\d+",
    ]

    combined_pattern = "|".join(metric_patterns)
    metrics_in_text = re.findall(combined_pattern, generated_text)

    if not metrics_in_text:
        return warnings

    # 2. 원본 데이터의 모든 수치 토큰화 (situation, task, action, result, metrics 모두 포함)
    source_text = " ".join(
        [
            f"{exp.metrics} {exp.result} {exp.situation} {exp.action} {exp.task}"
            for exp in source_experiences
        ]
    )

    # 3. 엄격한 매칭
    for metric in set(metrics_in_text):
        if metric not in source_text:
            # 보조 확인: 수치가 분수 형태(학점 등)인 경우 부분 일치 허용
            is_partial_match = False
            if "/" in metric:
                num_part = metric.split("/")[0]
                if num_part in source_text:
                    is_partial_match = True

            if not is_partial_match:
                warnings.append(
                    f"⚠️ [환각 의심] 생성된 수치 '{metric}'가 원본 데이터 어디에서도 발견되지 않았습니다."
                )

    return warnings
