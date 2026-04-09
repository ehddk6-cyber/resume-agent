from __future__ import annotations

import hashlib
import importlib
import re
import threading
import tempfile
from collections import Counter
from typing import Any, List, Optional
from .models import (
    ApplicationProject,
    Experience,
    KnowledgeSource,
    QuestionType,
    EvidenceLevel,
    SuccessPattern,
    Question,
)
from .config import get_config_value
from .experience_analyzer import ExperienceDeepAnalyzer

from .classifier import (
    classify_question,
    extract_question_keywords,
    QUESTION_TYPE_LABELS,
)
from .scoring import (
    score_experience,
    analyze_gaps,
    allocate_experiences,
    metric_present,
    find_experience,
    calculate_readability_score,
    audit_facts,
)
from .parsing import (
    ingest_source_file,
    summarize_knowledge_sources,
    stable_id,
    calculate_sources_hash,
    detect_patterns,
)
from .vector_store import SimpleVectorStore

_KNOWLEDGE_CACHE = {
    "hash": "",
    "vectorizer": None,
    "tfidf_matrix": None,
    "valid_sources": [],
    "doc_texts": [],
}
_KNOWLEDGE_CACHE_LOCK = threading.Lock()

# SentenceTransformer 싱글톤 (domain 전용)
_ST_MODEL_DOMAIN = None
_ST_DOMAIN_CLASS = None


def _get_st_model_domain():
    global _ST_MODEL_DOMAIN, _ST_DOMAIN_CLASS
    if _ST_DOMAIN_CLASS is None:
        try:
            module = importlib.import_module("sentence_transformers")
            _ST_DOMAIN_CLASS = getattr(module, "SentenceTransformer", None)
        except ImportError:
            _ST_DOMAIN_CLASS = False
    if _ST_DOMAIN_CLASS in (None, False):
        return None
    if _ST_MODEL_DOMAIN is None:
        model_name = get_config_value(
            "embedding.model_name", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        _ST_MODEL_DOMAIN = _ST_DOMAIN_CLASS(model_name)
    return _ST_MODEL_DOMAIN


def _semantic_similarity(query_text: str, doc_text: str) -> float:
    if not query_text.strip() or not doc_text.strip():
        return 0.0

    # SentenceTransformer 우선 시도
    model = _get_st_model_domain()
    if model is not None:
        try:
            q_vec = model.encode(query_text, normalize_embeddings=True)
            d_vec = model.encode(doc_text, normalize_embeddings=True)
            q_list = q_vec.tolist() if hasattr(q_vec, "tolist") else list(q_vec)
            d_list = d_vec.tolist() if hasattr(d_vec, "tolist") else list(d_vec)
            dot = sum(a * b for a, b in zip(q_list, d_list))
            return max(0.0, min(1.0, dot))
        except Exception:
            pass

    # 해시 기반 폴백 (기존 로직)
    def _features(text: str) -> List[str]:
        tokens = re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
        compact_text = re.sub(r"\s+", "", text.lower())
        bigrams = [
            compact_text[index : index + 2]
            for index in range(len(compact_text) - 1)
            if compact_text[index : index + 2].strip()
        ]
        return tokens + bigrams

    def _embed(text: str) -> dict[int, float]:
        vec: dict[int, float] = {}
        for feature in _features(text):
            idx = int(hashlib.md5(feature.encode("utf-8")).hexdigest(), 16) % 128
            vec[idx] = vec.get(idx, 0.0) + 1.0
        return vec

    query_vec = _embed(query_text)
    doc_vec = _embed(doc_text)
    if not query_vec or not doc_vec:
        return 0.0

    dot = sum(value * doc_vec.get(idx, 0.0) for idx, value in query_vec.items())
    query_norm = sum(value * value for value in query_vec.values()) ** 0.5
    doc_norm = sum(value * value for value in doc_vec.values()) ** 0.5
    if not query_norm or not doc_norm:
        return 0.0
    return dot / (query_norm * doc_norm)


def auto_classify_project_questions(project: ApplicationProject) -> None:
    for question in project.questions:
        question.detected_type = classify_question(question.question_text)


def _compress_hint_sources(
    sources: List[KnowledgeSource],
    *,
    max_sources: int,
) -> List[KnowledgeSource]:
    if len(sources) <= max_sources:
        return sources

    compressed: List[KnowledgeSource] = []
    seen_keys: set[tuple[str, str]] = set()
    for source in sources:
        key = (
            (source.title or "").strip(),
            source.source_type.value,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        compressed.append(source)
        if len(compressed) >= max_sources:
            break
    return compressed


def _normalize_match_text(text: str) -> str:
    return re.sub(r"[\s\(\)\[\]·,./_-]+", "", (text or "").lower())


def _company_aliases(company_name: str, company_type: str = "") -> set[str]:
    normalized = _normalize_match_text(company_name)
    aliases = {normalized} if normalized else set()
    normalized_type = _normalize_match_text(company_type)

    if any(token in normalized for token in ["새마을금고", "mg"]):
        aliases.update({"새마을금고", "mg", "상호금융", "지역금융"})
    if any(token in normalized for token in ["농축협", "농협", "축협"]):
        aliases.update(
            {"농축협", "농협", "축협", "협동조합", "상호금융", "지역금융"}
        )
    if "신협" in normalized:
        aliases.update({"신협", "협동조합", "상호금융", "지역금융"})
    if any(token in normalized_type for token in ["상호금융", "협동조합"]):
        aliases.update({"상호금융", "협동조합", "지역금융"})
    return {item for item in aliases if item}


def _match_reason_summary(
    *,
    project: ApplicationProject,
    pattern: Any,
    question: Question | None = None,
) -> tuple[float, list[str]]:
    bonus = 0.0
    reasons: list[str] = []
    project_company_aliases = _company_aliases(
        project.company_name, project.company_type
    )
    source_company = _normalize_match_text(getattr(pattern, "company_name", ""))
    project_job = _normalize_match_text(project.job_title)
    source_job = _normalize_match_text(getattr(pattern, "job_title", ""))

    if (
        project_company_aliases
        and source_company
        and any(alias == source_company for alias in project_company_aliases)
    ):
        bonus += 0.45
        reasons.append("회사명 exact match")
    elif (
        project_company_aliases
        and source_company
        and any(alias in source_company or source_company in alias for alias in project_company_aliases)
    ):
        bonus += 0.25
        reasons.append("회사군 partial match")

    if project_job and source_job and project_job == source_job:
        bonus += 0.2
        reasons.append("직무명 exact match")
    elif project_job and source_job and (project_job in source_job or source_job in project_job):
        bonus += 0.12
        reasons.append("직무명 overlap")

    if question is not None:
        qtype = getattr(question, "detected_type", None)
        if qtype and qtype in getattr(pattern, "question_types", []):
            bonus += 0.12
            reasons.append(f"문항유형 match ({qtype.value})")

    return bonus, reasons


def _build_source_doc_text(source: KnowledgeSource) -> str:
    pattern = source.pattern
    return " ".join(
        [
            pattern.company_name,
            pattern.job_title,
            pattern.structure_summary,
            " ".join(pattern.retrieval_terms),
            source.cleaned_text[:500],
        ]
    ).strip()


def _derive_evidence_focus(source: KnowledgeSource) -> list[str]:
    patterns = detect_patterns(source.cleaned_text[:1600])
    focus: list[str] = []
    mapping = {
        SuccessPattern.QUANTIFIED_RESULT: "정량 결과",
        SuccessPattern.STAR_STRUCTURE: "STAR 구조",
        SuccessPattern.PROBLEM_SOLVING: "문제 해결",
        SuccessPattern.COLLABORATION: "협업",
        SuccessPattern.CUSTOMER_FOCUS: "고객 관점",
        SuccessPattern.ETHICS: "윤리/원칙",
        SuccessPattern.GROWTH_STORY: "성장 서사",
        SuccessPattern.INNOVATION: "개선/혁신",
    }
    for pattern in patterns:
        label = mapping.get(pattern)
        if label and label not in focus:
            focus.append(label)
    if source.pattern and source.pattern.structure_signals.has_metrics and "정량 결과" not in focus:
        focus.append("정량 결과")
    return focus[:4]


def _build_hint_entry(
    *,
    source: KnowledgeSource,
    tfidf_score: float,
    semantic_score: float,
    vector_score: float,
    combined_score: float,
    match_reasons: list[str],
    question: Question | None = None,
) -> dict[str, Any]:
    pattern = source.pattern
    applicable_question_types = [qt.value for qt in pattern.question_types]
    entry = {
        "title": source.title,
        "company_name": pattern.company_name,
        "job_title": pattern.job_title,
        "signal": f"{pattern.company_name or '일반'} / {pattern.job_title or '직무 미상'} / TF-IDF score {tfidf_score:.3f}",
        "structure_summary": pattern.structure_summary,
        "caution": pattern.caution,
        "question_types": applicable_question_types,
        "applicable_question_types": applicable_question_types,
        "evidence_focus": _derive_evidence_focus(source),
        "structure_signals": pattern.structure_signals.model_dump(),
        "match_reasons": match_reasons,
        "semantic_score": round(semantic_score, 3),
        "vector_score": round(vector_score, 3),
        "combined_score": round(combined_score, 3),
    }
    if question is not None:
        entry["question_id"] = question.id
        entry["question_order"] = question.order_no
        entry["question_text"] = question.question_text
        entry["question_type"] = getattr(question.detected_type, "value", "")
    return entry


def _rank_knowledge_hints(
    valid_sources: list[KnowledgeSource],
    *,
    vectorizer: Any,
    tfidf_matrix: Any,
    project: ApplicationProject,
    doc_texts: list[str],
    question: Question | None = None,
    use_semantic_hinting: bool = True,
    limit: int = 5,
) -> list[dict[str, Any]]:
    company = project.company_name.strip()
    job = project.job_title.strip()
    query_parts = [company, job]

    if question is None:
        for item in project.questions:
            query_parts.extend(extract_question_keywords(item.question_text))
            qtype = getattr(item.detected_type, "value", "")
            if qtype:
                query_parts.append(qtype)
    else:
        query_parts.extend(extract_question_keywords(question.question_text))
        qtype = getattr(question.detected_type, "value", "")
        if qtype:
            query_parts.append(qtype)

    query_text = " ".join(part for part in query_parts if part)
    if not query_text.strip():
        return []

    query_vector = vectorizer.transform([query_text])
    from sklearn.metrics.pairwise import cosine_similarity

    cosine_similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    vector_scores: dict[str, float] = {}
    if use_semantic_hinting:
        with tempfile.TemporaryDirectory(prefix="resume-agent-vector-") as vector_dir:
            vector_store = SimpleVectorStore(vector_dir)
            for source, doc_text in zip(valid_sources, doc_texts):
                vector_store.add_document(
                    doc_text,
                    {"source_id": source.id},
                    doc_id=source.id,
                )
            vector_scores = {
                item["id"]: float(item.get("similarity", 0.0))
                for item in vector_store.search(
                    query_text,
                    n_results=max(limit, len(valid_sources)),
                    min_similarity=0.0,
                )
            }

    ranked_indices = cosine_similarities.argsort()[::-1]
    hints: list[dict[str, Any]] = []
    for idx in ranked_indices:
        tfidf_score = float(cosine_similarities[idx])
        source = valid_sources[idx]
        pattern = source.pattern
        bonus, reasons = _match_reason_summary(
            project=project,
            pattern=pattern,
            question=question,
        )
        semantic_score = (
            _semantic_similarity(query_text, doc_texts[idx]) if use_semantic_hinting else 0.0
        )
        vector_score = vector_scores.get(source.id, 0.0) if use_semantic_hinting else 0.0

        if pattern.structure_signals.has_metrics:
            tfidf_score += 0.05
            reasons = [*reasons, "정량 결과 포함"]

        combined_score = tfidf_score + bonus + (semantic_score * 0.15) + (vector_score * 0.2)
        if combined_score <= 0.05:
            continue
        hints.append(
            _build_hint_entry(
                source=source,
                tfidf_score=tfidf_score,
                semantic_score=semantic_score,
                vector_score=vector_score,
                combined_score=combined_score,
                match_reasons=reasons,
                question=question,
            )
        )
        if len(hints) >= limit:
            break

    hints.sort(
        key=lambda item: (
            float(item.get("combined_score", 0.0)),
            len(item.get("match_reasons", [])),
            float(item.get("vector_score", 0.0)),
            float(item.get("semantic_score", 0.0)),
        ),
        reverse=True,
    )
    return hints


def build_question_specific_knowledge_hints(
    sources: List[KnowledgeSource], project: ApplicationProject
) -> List[dict[str, Any]]:
    if not sources or not project.questions:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        return []

    global _KNOWLEDGE_CACHE
    current_hash = calculate_sources_hash(sources)
    cache_hit = False
    with _KNOWLEDGE_CACHE_LOCK:
        cache_hit = (
            _KNOWLEDGE_CACHE["hash"] == current_hash
            and _KNOWLEDGE_CACHE["vectorizer"] is not None
        )
        if cache_hit:
            vectorizer = _KNOWLEDGE_CACHE["vectorizer"]
            tfidf_matrix = _KNOWLEDGE_CACHE["tfidf_matrix"]
            valid_sources = list(_KNOWLEDGE_CACHE["valid_sources"])
            doc_texts = list(_KNOWLEDGE_CACHE.get("doc_texts", []))

    hint_source_cap = int(get_config_value("writer.hint_source_cap", 120))
    if not cache_hit:
        corpus = []
        valid_sources = []
        for source in sources:
            if not source.pattern:
                continue
            valid_sources.append(source)
        valid_sources = _compress_hint_sources(valid_sources, max_sources=hint_source_cap)
        doc_texts = []
        for source in valid_sources:
            doc_text = _build_source_doc_text(source)
            doc_texts.append(doc_text)
            corpus.append(
                " ".join(
                    [
                        source.pattern.company_name,
                        source.pattern.job_title,
                        " ".join(source.pattern.retrieval_terms),
                        " ".join([qt.value for qt in source.pattern.question_types]),
                    ]
                )
            )
        if not corpus:
            return []
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(corpus)
        with _KNOWLEDGE_CACHE_LOCK:
            _KNOWLEDGE_CACHE["hash"] = current_hash
            _KNOWLEDGE_CACHE["vectorizer"] = vectorizer
            _KNOWLEDGE_CACHE["tfidf_matrix"] = tfidf_matrix
            _KNOWLEDGE_CACHE["valid_sources"] = list(valid_sources)
            _KNOWLEDGE_CACHE["doc_texts"] = list(doc_texts)

    semantic_hint_cap = int(get_config_value("writer.semantic_hint_cap", 32))
    use_semantic_hinting = len(valid_sources) <= semantic_hint_cap
    question_hints: list[dict[str, Any]] = []
    for question in project.questions:
        hints = _rank_knowledge_hints(
            valid_sources,
            vectorizer=vectorizer,
            tfidf_matrix=tfidf_matrix,
            project=project,
            doc_texts=doc_texts,
            question=question,
            use_semantic_hinting=use_semantic_hinting,
            limit=3,
        )
        question_hints.append(
            {
                "question_id": question.id,
                "question_order": question.order_no,
                "question_text": question.question_text,
                "question_type": getattr(question.detected_type, "value", ""),
                "hints": hints,
            }
        )
    return question_hints


def build_experience_knowledge_hints(
    experiences: List[Experience],
    questions: List[Question],
    kb_path: str = "./kb",
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """경험-질문 의미적 매칭 기반 힌트 생성
    
    ExperienceDeepAnalyzer를 활용하여 질문과 경험의 의미적 연결을 개선합니다.
    
    Returns:
        {
            "experience_hints": [...],  # 각 경험의 역량 분석
            "question_hints": [...],    # 각 질문의 의도 분석
            "matching_pairs": [...]     # 경험-질문 매칭 쌍
        }
    """
    analyzer = ExperienceDeepAnalyzer()
    
    # 1. 경험 힌트 생성
    experience_hints = []
    exp_competencies_map = {}  # exp_id -> [competency names]
    
    for exp in experiences:
        core_comps = analyzer.analyze_core_competency(exp)
        top_comp = core_comps[0].competency if core_comps else None
        comps_list = [c.competency for c in core_comps]
        exp_competencies_map[exp.id] = comps_list
        
        experience_hints.append({
            "experience_id": exp.id,
            "experience_title": exp.title,
            "top_competency": top_comp,
            "competencies": comps_list,
            "confidence": core_comps[0].confidence if core_comps else 0.0,
            "evidence_keywords": core_comps[0].evidence_keywords if core_comps else [],
            "interview_relevance": core_comps[0].interview_relevance if core_comps else "",
        })
    
    # 2. 질문 힌트 생성
    question_hints = []
    question_intents_map = {}  # question_id -> QuestionIntentAnalysis
    
    for q in questions:
        intent = analyzer.analyze_question_intent(q)
        question_intents_map[q.id] = intent
        
        question_hints.append({
            "question_id": q.id,
            "question_text": q.question_text[:50],
            "hidden_intent": intent.hidden_intent,
            "wanted_competencies": intent.core_competencies_sought,
            "risk_topics": intent.risk_topics,
            "surface_topic": intent.surface_topic,
            "recommended_approach": intent.recommended_approach,
        })
    
    # 3. 경험-질문 매칭
    matching_pairs = []
    
    for exp_id, exp_comps in exp_competencies_map.items():
        for q_id, intent in question_intents_map.items():
            wanted = set(intent.core_competencies_sought)
            matched = set(exp_comps) & wanted
            
            if matched:
                # 매칭 점수 계산
                match_score = len(matched) / max(len(wanted), 1)
                
                matching_pairs.append({
                    "experience_id": exp_id,
                    "question_id": q_id,
                    "matched_competencies": list(matched),
                    "match_score": round(match_score, 2),
                    "reason": f"역량 '{', '.join(matched)}' 매칭",
                })
    
    # 점수순 정렬
    matching_pairs.sort(key=lambda x: x["match_score"], reverse=True)
    
    return {
        "experience_hints": experience_hints,
        "question_hints": question_hints,
        "matching_pairs": matching_pairs,
    }


# ============================================================================
# 기존 함수들 (하위 호환성 유지)
# ============================================================================


def build_knowledge_hints(
    sources: List[KnowledgeSource],
    project: ApplicationProject,
    applicant_profile: dict[str, Any] | None = None,
) -> List[dict[str, Any]]:
    if not sources:
        if applicant_profile:
            return [_build_personalized_profile_hint(applicant_profile, project)]
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return _fallback_build_knowledge_hints(sources, project)

    global _KNOWLEDGE_CACHE
    current_hash = calculate_sources_hash(sources)

    # 1. 캐시 히트 체크 (지식 베이스 데이터가 변경되지 않았다면 재사용)
    cache_hit = False
    with _KNOWLEDGE_CACHE_LOCK:
        cache_hit = (
            _KNOWLEDGE_CACHE["hash"] == current_hash
            and _KNOWLEDGE_CACHE["vectorizer"] is not None
        )
        if cache_hit:
            vectorizer = _KNOWLEDGE_CACHE["vectorizer"]
            tfidf_matrix = _KNOWLEDGE_CACHE["tfidf_matrix"]
            valid_sources = list(_KNOWLEDGE_CACHE["valid_sources"])
            doc_texts = list(_KNOWLEDGE_CACHE.get("doc_texts", []))
    hint_source_cap = int(get_config_value("writer.hint_source_cap", 120))
    if not cache_hit:
        # 2. 캐시 미스: 신규 백터화 수행
        corpus = []
        valid_sources = []
        for source in sources:
            if not source.pattern:
                continue
            valid_sources.append(source)
        valid_sources = _compress_hint_sources(
            valid_sources,
            max_sources=hint_source_cap,
        )
        for source in valid_sources:
            pattern = source.pattern
            doc_parts = [
                pattern.company_name,
                pattern.job_title,
                " ".join(pattern.retrieval_terms),
                " ".join([qt.value for qt in pattern.question_types]),
            ]
            corpus.append(" ".join(doc_parts))
        doc_texts = [_build_source_doc_text(source) for source in valid_sources]

        if not corpus:
            return []

        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # 캐시 업데이트
        with _KNOWLEDGE_CACHE_LOCK:
            _KNOWLEDGE_CACHE["hash"] = current_hash
            _KNOWLEDGE_CACHE["vectorizer"] = vectorizer
            _KNOWLEDGE_CACHE["tfidf_matrix"] = tfidf_matrix
            _KNOWLEDGE_CACHE["valid_sources"] = list(valid_sources)
            _KNOWLEDGE_CACHE["doc_texts"] = list(doc_texts)

    semantic_hint_cap = int(get_config_value("writer.semantic_hint_cap", 32))
    use_semantic_hinting = len(valid_sources) <= semantic_hint_cap
    hints = _rank_knowledge_hints(
        valid_sources,
        vectorizer=vectorizer,
        tfidf_matrix=tfidf_matrix,
        project=project,
        doc_texts=doc_texts,
        question=None,
        use_semantic_hinting=use_semantic_hinting,
        limit=5,
    )
    if applicant_profile:
        hints.insert(0, _build_personalized_profile_hint(applicant_profile, project))
    return hints[:6]


def _build_personalized_profile_hint(
    applicant_profile: dict[str, Any],
    project: ApplicationProject,
) -> dict[str, Any]:
    profile = applicant_profile.get("personalized_profile", applicant_profile)
    strengths = list(
        profile.get("strength_keywords", [])
        or applicant_profile.get("signature_strengths", [])
        or []
    )
    weaknesses = list(
        profile.get("weakness_details", [])
        or applicant_profile.get("blind_spots", [])
        or []
    )
    recommendations = list(
        profile.get("recommendation_summary", [])
        or applicant_profile.get("coaching_focus", [])
        or []
    )
    writing_style = profile.get(
        "writing_style",
        applicant_profile.get("writing_style", {}),
    ) or {}

    return {
        "title": "지원자 프로파일 힌트",
        "company_name": project.company_name,
        "job_title": project.job_title,
        "signal": (
            f"개인화 코칭 / {writing_style.get('dominant_tone', 'balanced')} / "
            f"{', '.join(strengths[:2]) or '직무 적합성'}"
        ),
        "structure_summary": "지원자 고유 문체와 강약점을 반영한 답변 방향입니다.",
        "caution": weaknesses[0] if weaknesses else "강점만 반복하지 말고 약점 보완 문장도 함께 준비하세요.",
        "question_types": [],
        "applicable_question_types": [],
        "evidence_focus": strengths[:3],
        "structure_signals": {
            "has_star": True,
            "has_metrics": "low_metrics" not in set(profile.get("weakness_codes", [])),
            "warns_against_copying": True,
        },
        "match_reasons": recommendations[:3] or ["지원자 프로파일 기반 추천"],
    }


def _fallback_build_knowledge_hints(
    sources: List[KnowledgeSource], project: ApplicationProject
) -> List[dict[str, Any]]:
    # 이전 로직 그대로 유지
    company = project.company_name.strip()
    job = project.job_title.strip()
    question_terms: List[str] = []
    question_types: List[QuestionType] = []
    for question in project.questions:
        text = question.question_text
        question_terms.extend(extract_question_keywords(text))
        question_types.append(classify_question(text))

    ranked: List[tuple[int, KnowledgeSource]] = []
    for source in sources:
        if not source.pattern:
            continue
        pattern = source.pattern
        score = 0
        retrieval_terms = set(pattern.retrieval_terms)
        if company and company in retrieval_terms:
            score += 8
        if job and job in retrieval_terms:
            score += 8
        score += sum(2 for term in question_terms[:8] if term in retrieval_terms)
        score += sum(3 for qtype in question_types if qtype in pattern.question_types)
        if pattern.structure_signals.has_metrics:
            score += 1
        bonus, reasons = _match_reason_summary(project=project, pattern=pattern)
        score += int(round(bonus * 10))
        if score > 0:
            ranked.append((score, source, reasons))

    ranked.sort(key=lambda item: item[0], reverse=True)
    hints: List[dict[str, Any]] = []
    for score, source, reasons in ranked[:5]:
        pattern = source.pattern
        hints.append(
            {
                "title": source.title,
                "company_name": pattern.company_name,
                "job_title": pattern.job_title,
                "signal": f"{pattern.company_name or '일반'} / {pattern.job_title or '직무 미상'} / score {score}",
                "structure_summary": pattern.structure_summary,
                "caution": pattern.caution,
                "question_types": [qt.value for qt in pattern.question_types],
                "applicable_question_types": [qt.value for qt in pattern.question_types],
                "evidence_focus": _derive_evidence_focus(source),
                "structure_signals": pattern.structure_signals.model_dump(),
                "match_reasons": reasons,
            }
        )
    return hints


def build_coach_artifact(
    project: ApplicationProject,
    experiences: List[Experience],
    gap_report: dict[str, Any],
    outcome_summary: dict[str, Any] | None = None,
    strategy_outcome_summary: dict[str, Any] | None = None,
    current_pattern: str | None = None,
    feedback_adaptation_plan: dict[str, Any] | None = None,
    question_strategies: List[dict[str, Any]] | None = None,
    writer_contract: dict[str, Any] | None = None,
    candidate_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    allocations = allocate_experiences(
        project.questions,
        experiences,
        project.priority_experience_order,
        outcome_summary=outcome_summary,
        strategy_outcome_summary=strategy_outcome_summary,
        current_pattern=current_pattern,
        feedback_adaptation_plan=feedback_adaptation_plan,
        candidate_profile=candidate_profile,
    )
    current_summary: List[str] = []
    required_inputs: List[str] = []

    for allocation in allocations:
        experience = find_experience(experiences, allocation["experience_id"])
        if not experience:
            continue
        current_summary.append(
            f"{allocation['order_no']}번 문항은 {QUESTION_TYPE_LABELS.get(allocation['question_type'], allocation['question_type'])}으로 분류했고, "
            f"주력 경험은 {experience.title}입니다."
        )
        if not metric_present(experience):
            required_inputs.append(
                f"{experience.title}: 정량 또는 비교 근거를 보강하세요."
            )
        if not experience.evidence_text.strip():
            required_inputs.append(
                f"{experience.title}: 면접 방어용 증빙 텍스트를 추가하세요."
            )

    needs_verification = [
        f"[NEEDS_VERIFICATION] {title}"
        for title in gap_report.get("needs_verification", [])
    ]
    if not any(exp.evidence_level == EvidenceLevel.L3 for exp in experiences):
        needs_verification.append(
            "[NEEDS_VERIFICATION] L3 수준의 증거 경험이 없습니다."
        )

    assumptions = [
        f"[ASSUMPTION] 답변 톤은 '{project.tone_style}' 기준으로 유지합니다."
    ]
    if not project.priority_experience_order:
        assumptions.append(
            "[ASSUMPTION] 우선순위가 비어 있어 현재 점수 기준으로 경험을 배분합니다."
        )

    question_risks: List[str] = []
    for item in gap_report.get("question_risks", []):
        question_risks.append(
            f"{item['order_no']}번 문항 / {QUESTION_TYPE_LABELS.get(item['question_type'], item['question_type'])} / "
            f"best_score={item['best_score']} / risk={item['risk']}"
        )

    artifact = {
        "current_stage": "HANDOFF_READY",
        "purpose": f"{project.company_name} / {project.job_title} 문항에 대한 경험 배분과 리스크를 정리합니다.",
        "current_summary": current_summary or ["배분 가능한 경험이 아직 없습니다."],
        "required_inputs": required_inputs or ["추가 입력 없음"],
        "next_step": "WRITER_HANDOFF" if allocations else "ADD_EXPERIENCES_FIRST",
        "assumptions": assumptions,
        "needs_verification": needs_verification,
        "question_risks": question_risks or ["질문별 리스크 정보가 아직 없습니다."],
        "recommendations": gap_report.get("recommendations", [])
        or ["즉시 보강이 필요한 추천 사항이 없습니다."],
        "allocations": allocations,
        "question_strategies": question_strategies or [],
        "writer_contract": writer_contract or {},
    }
    artifact["rendered"] = render_coach_artifact(artifact)
    return artifact


def render_coach_artifact(artifact: dict[str, Any]) -> str:
    lines = [
        "## CURRENT STAGE",
        artifact["current_stage"],
        "",
        "## PURPOSE",
        artifact["purpose"],
        "",
        "## CURRENT SUMMARY",
        *[f"- {item}" for item in artifact["current_summary"]],
        "",
        "## REQUIRED INPUTS",
        *[f"- {item}" for item in artifact["required_inputs"]],
        "",
        "## NEXT STEP",
        artifact["next_step"],
    ]
    if artifact.get("assumptions"):
        lines.extend(
            ["", "## ASSUMPTIONS", *[f"- {item}" for item in artifact["assumptions"]]]
        )
    if artifact.get("needs_verification"):
        lines.extend(
            [
                "",
                "## NEEDS VERIFICATION",
                *[f"- {item}" for item in artifact["needs_verification"]],
            ]
        )
    if artifact.get("question_risks"):
        lines.extend(
            [
                "",
                "## QUESTION RISKS",
                *[f"- {item}" for item in artifact["question_risks"]],
            ]
        )
    if artifact.get("recommendations"):
        lines.extend(
            [
                "",
                "## RECOMMENDATIONS",
                *[f"- {item}" for item in artifact["recommendations"]],
            ]
        )
    if artifact.get("allocations"):
        lines.extend(["", "## ALLOCATIONS"])
        for item in artifact["allocations"]:
            lines.extend(
                [
                    f"### Q{item['order_no']}",
                    f"- Experience: {item['experience_title']}",
                    f"- Type: {item['question_type']}",
                    f"- Score: {item['score']}",
                    f"- Reason: {item['reason']}",
                ]
            )
            if item.get("reuse_reason"):
                lines.append(f"- Reuse: {item['reuse_reason']}")
    if artifact.get("question_strategies"):
        lines.extend(["", "## QUESTION STRATEGIES"])
        for item in artifact["question_strategies"]:
            lines.extend(
                [
                    f"### Q{item.get('question_order', '?')}",
                    f"- Core message: {item.get('core_message', '미정')}",
                    f"- Winning angle: {item.get('winning_angle', '미정')}",
                    f"- Losing angle: {item.get('losing_angle', '미정')}",
                    f"- Primary experience: {item.get('primary_experience_title', '미정')}",
                ]
            )
            supporting = item.get("supporting_experience_titles", [])
            if supporting:
                lines.append(f"- Supporting experiences: {', '.join(supporting)}")
            forbidden = item.get("forbidden_points", [])
            if forbidden:
                lines.append(f"- Forbidden points: {', '.join(forbidden)}")
            attack_points = item.get("expected_attack_points", [])
            if attack_points:
                lines.append(f"- Expected attacks: {', '.join(attack_points)}")
            required_evidence = item.get("required_evidence", [])
            if required_evidence:
                lines.append(f"- Required evidence: {', '.join(required_evidence)}")
            differentiation = item.get("differentiation_line")
            if differentiation:
                lines.append(f"- Differentiation line: {differentiation}")
    if artifact.get("writer_contract"):
        contract = artifact["writer_contract"]
        lines.extend(
            [
                "",
                "## WRITER CONTRACT",
                f"- Mode: {contract.get('mode_label', 'heuristic mode')}",
                f"- Headline: {contract.get('headline', '문항별 단일 전략을 고정합니다.')}",
            ]
        )
        checklist = contract.get("answer_checklist", [])
        if checklist:
            lines.extend([f"- Checklist: {item}" for item in checklist])
        principles = contract.get("decision_principles", [])
        if principles:
            lines.extend([f"- Principle: {item}" for item in principles])
    return "\n".join(lines)


def _extract_section_body(text: str, heading: str, headings: List[str]) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    start += len(heading)
    end = len(text)
    for candidate in headings:
        if candidate == heading:
            continue
        idx = text.find(candidate, start)
        if idx != -1 and idx < end:
            end = idx
    return text[start:end].strip()


def _section_has_content(text: str, heading: str, headings: List[str]) -> bool:
    body = _extract_section_body(text, heading, headings)
    if not body:
        return False
    return any(line.strip("- ").strip() for line in body.splitlines())


def validate_coach_contract(text: str) -> dict[str, Any]:
    headings = [
        "## CURRENT STAGE",
        "## PURPOSE",
        "## CURRENT SUMMARY",
        "## REQUIRED INPUTS",
        "## NEXT STEP",
        "## ASSUMPTIONS",
        "## NEEDS VERIFICATION",
        "## QUESTION RISKS",
        "## RECOMMENDATIONS",
    ]
    missing = [heading for heading in headings if heading not in text]
    empty = [
        heading
        for heading in headings
        if heading in text and not _section_has_content(text, heading, headings)
    ]
    return {"passed": not missing and not empty, "missing": missing, "empty": empty}


def validate_block_contract(text: str, headings: List[str]) -> dict[str, Any]:
    missing = [heading for heading in headings if heading not in text]
    empty = [
        heading
        for heading in headings
        if heading in text and not _section_has_content(text, heading, headings)
    ]
    return {"passed": not missing and not empty, "missing": missing, "empty": empty}


def validate_writer_contract(text: str) -> dict[str, Any]:
    headings = [
        "## 블록 1: ASSUMPTIONS & MISSING FACTS",
        "## 블록 2: OUTLINE",
        "## 블록 3: DRAFT ANSWERS",
        "## 블록 4: SELF-CHECK",
    ]
    result = validate_block_contract(text, headings)
    semantic_missing: List[str] = []
    if "글자수:" not in text:
        semantic_missing.append("문항별 글자수 표기")
    if "PASS" not in text and "FAIL" not in text:
        semantic_missing.append("SELF-CHECK PASS/FAIL")
    result["passed"] = result["passed"] and not semantic_missing
    result["semantic_missing"] = semantic_missing
    return result


def validate_interview_contract(text: str) -> dict[str, Any]:
    headings = [
        "## 블록 1: INTERVIEW ASSUMPTIONS",
        "## 블록 2: INTERVIEW STRATEGY",
        "## 블록 3: EXPECTED QUESTIONS MAP",
        "## 블록 4: ANSWER FRAMES",
    ]
    result = validate_block_contract(text, headings)
    semantic_missing: List[str] = []
    if not any(token in text for token in ["2차", "3차", "꼬리질문", "follow-up"]):
        semantic_missing.append("연쇄 꼬리질문")
    if "30초" not in text and "150~200자" not in text and "150-200자" not in text:
        semantic_missing.append("30초 답변 프레임")
    result["passed"] = result["passed"] and not semantic_missing
    result["semantic_missing"] = semantic_missing
    return result


def validate_company_research_contract(text: str) -> dict[str, Any]:
    headings = [
        "## 블록 1: 확정 정보",
        "## 블록 2: 입력 기반 핵심 신호",
        "## 블록 3: 직무 분석",
        "## 블록 4: 회사/조직 적합성 해석",
        "## 블록 5: 자소서 연결 전략",
        "## 블록 6: 면접 대비 포인트",
        "## 블록 7: SELF-CHECK",
    ]
    result = validate_block_contract(text, headings)
    semantic_missing: List[str] = []
    if "[NEEDS_VERIFICATION]" not in text:
        semantic_missing.append("[NEEDS_VERIFICATION] 표기")
    if "PASS" not in text and "FAIL" not in text:
        semantic_missing.append("SELF-CHECK PASS/FAIL")
    if not any(token in text for token in ["TYPE_A", "TYPE_B", "TYPE_E"]):
        semantic_missing.append("자소서 유형 연결")
    result["passed"] = result["passed"] and not semantic_missing
    result["semantic_missing"] = semantic_missing
    return result
