from __future__ import annotations

from typing import Any, List
from .models import ApplicationProject, Experience, KnowledgeSource, QuestionType, EvidenceLevel

# 파사드(Facade) 패턴: 분리된 모듈들을 기존처럼 도메인에서 가져다 쓸 수 있도록 함
from .classifier import classify_question, extract_question_keywords, QUESTION_TYPE_LABELS
from .scoring import score_experience, analyze_gaps, allocate_experiences, metric_present, find_experience, calculate_readability_score, audit_facts
from .parsing import ingest_source_file, summarize_knowledge_sources, stable_id, calculate_sources_hash

# [전역 캐시 변수]
_KNOWLEDGE_CACHE = {
    "hash": "",
    "vectorizer": None,
    "tfidf_matrix": None,
    "valid_sources": []
}

def auto_classify_project_questions(project: ApplicationProject) -> None:
    for question in project.questions:
        question.detected_type = classify_question(question.question_text)

def build_knowledge_hints(sources: List[KnowledgeSource], project: ApplicationProject) -> List[dict[str, Any]]:
    if not sources:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return _fallback_build_knowledge_hints(sources, project)

    global _KNOWLEDGE_CACHE
    current_hash = calculate_sources_hash(sources)
    
    # 1. 캐시 히트 체크 (지식 베이스 데이터가 변경되지 않았다면 재사용)
    if _KNOWLEDGE_CACHE["hash"] == current_hash and _KNOWLEDGE_CACHE["vectorizer"] is not None:
        vectorizer = _KNOWLEDGE_CACHE["vectorizer"]
        tfidf_matrix = _KNOWLEDGE_CACHE["tfidf_matrix"]
        valid_sources = _KNOWLEDGE_CACHE["valid_sources"]
    else:
        # 2. 캐시 미스: 신규 백터화 수행
        corpus = []
        valid_sources = []
        for source in sources:
            if not source.pattern:
                continue
            valid_sources.append(source)
            pattern = source.pattern
            doc_parts = [
                pattern.company_name, 
                pattern.job_title,
                " ".join(pattern.retrieval_terms),
                " ".join([qt.value for qt in pattern.question_types])
            ]
            corpus.append(" ".join(doc_parts))
            
        if not corpus:
            return []

        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(corpus)
        
        # 캐시 업데이트
        _KNOWLEDGE_CACHE["hash"] = current_hash
        _KNOWLEDGE_CACHE["vectorizer"] = vectorizer
        _KNOWLEDGE_CACHE["tfidf_matrix"] = tfidf_matrix
        _KNOWLEDGE_CACHE["valid_sources"] = valid_sources

    company = project.company_name.strip()
    job = project.job_title.strip()
    
    # 3. 쿼리 텍스트 구성 및 유사도 계산
    query_parts = [company, job]
    for question in project.questions:
        query_parts.extend(extract_question_keywords(question.question_text))
        query_parts.append(question.detected_type.value)
        
    query_text = " ".join(query_parts)
    query_vector = vectorizer.transform([query_text])
    cosine_similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    
    # 4. 점수 정렬 및 상위 5개 추출
    ranked_indices = cosine_similarities.argsort()[::-1]
    
    hints: List[dict[str, Any]] = []
    for idx in ranked_indices[:5]:
        score = cosine_similarities[idx]
        if score <= 0.01:
            continue
            
        source = valid_sources[idx]
        pattern = source.pattern
        
        if pattern.structure_signals.has_metrics:
            score += 0.05
            
        hints.append(
            {
                "title": source.title,
                "signal": f"{pattern.company_name or '일반'} / {pattern.job_title or '직무 미상'} / TF-IDF score {score:.3f}",
                "structure_summary": pattern.structure_summary,
                "caution": pattern.caution,
                "question_types": [qt.value for qt in pattern.question_types],
            }
        )
    return hints

def _fallback_build_knowledge_hints(sources: List[KnowledgeSource], project: ApplicationProject) -> List[dict[str, Any]]:
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
        if score > 0:
            ranked.append((score, source))

    ranked.sort(key=lambda item: item[0], reverse=True)
    hints: List[dict[str, Any]] = []
    for score, source in ranked[:5]:
        pattern = source.pattern
        hints.append(
            {
                "title": source.title,
                "signal": f"{pattern.company_name or '일반'} / {pattern.job_title or '직무 미상'} / score {score}",
                "structure_summary": pattern.structure_summary,
                "caution": pattern.caution,
                "question_types": [qt.value for qt in pattern.question_types],
            }
        )
    return hints

def build_coach_artifact(project: ApplicationProject, experiences: List[Experience], gap_report: dict[str, Any]) -> dict[str, Any]:
    allocations = allocate_experiences(
        project.questions,
        experiences,
        project.priority_experience_order,
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
            required_inputs.append(f"{experience.title}: 정량 또는 비교 근거를 보강하세요.")
        if not experience.evidence_text.strip():
            required_inputs.append(f"{experience.title}: 면접 방어용 증빙 텍스트를 추가하세요.")

    needs_verification = [
        f"[NEEDS_VERIFICATION] {title}"
        for title in gap_report.get("needs_verification", [])
    ]
    if not any(exp.evidence_level == EvidenceLevel.L3 for exp in experiences):
        needs_verification.append("[NEEDS_VERIFICATION] L3 수준의 증거 경험이 없습니다.")

    artifact = {
        "current_stage": "HANDOFF_READY",
        "purpose": f"{project.company_name} / {project.job_title} 문항에 대한 경험 배분과 리스크를 정리합니다.",
        "current_summary": current_summary or ["배분 가능한 경험이 아직 없습니다."],
        "required_inputs": required_inputs or ["추가 입력 없음"],
        "next_step": "WRITER_HANDOFF" if allocations else "ADD_EXPERIENCES_FIRST",
        "assumptions": [],
        "needs_verification": needs_verification,
        "allocations": allocations,
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
    if artifact.get("needs_verification"):
        lines.extend(["", "## NEEDS VERIFICATION", *[f"- {item}" for item in artifact["needs_verification"]]])
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
    return "\n".join(lines)

def validate_coach_contract(text: str) -> dict[str, Any]:
    headings = [
        "## CURRENT STAGE",
        "## PURPOSE",
        "## CURRENT SUMMARY",
        "## REQUIRED INPUTS",
        "## NEXT STEP",
    ]
    missing = [heading for heading in headings if heading not in text]
    return {"passed": not missing, "missing": missing}

def validate_block_contract(text: str, headings: List[str]) -> dict[str, Any]:
    missing = [heading for heading in headings if heading not in text]
    return {"passed": not missing, "missing": missing}

def validate_writer_contract(text: str) -> dict[str, Any]:
    headings = [
        "## 블록 1: ASSUMPTIONS & MISSING FACTS",
        "## 블록 2: OUTLINE",
        "## 블록 3: DRAFT ANSWERS",
        "## 블록 4: SELF-CHECK",
    ]
    missing = [heading for heading in headings if heading not in text]
    return {"passed": not missing, "missing": missing}

def validate_interview_contract(text: str) -> dict[str, Any]:
    headings = [
        "## 블록 1: INTERVIEW ASSUMPTIONS",
        "## 블록 2: INTERVIEW STRATEGY",
        "## 블록 3: EXPECTED QUESTIONS MAP",
        "## 블록 4: ANSWER FRAMES",
    ]
    missing = [heading for heading in headings if heading not in text]
    return {"passed": not missing, "missing": missing}
