from __future__ import annotations

import hashlib
import re
import threading
import tempfile
from typing import Any, List
from .models import ApplicationProject, Experience, KnowledgeSource, QuestionType, EvidenceLevel

# 파사드(Facade) 패턴: 분리된 모듈들을 기존처럼 도메인에서 가져다 쓸 수 있도록 함
from .classifier import classify_question, extract_question_keywords, QUESTION_TYPE_LABELS
from .scoring import score_experience, analyze_gaps, allocate_experiences, metric_present, find_experience, calculate_readability_score, audit_facts
from .parsing import ingest_source_file, summarize_knowledge_sources, stable_id, calculate_sources_hash
from .vector_store import SimpleVectorStore

# [전역 캐시 변수]
_KNOWLEDGE_CACHE = {
    "hash": "",
    "vectorizer": None,
    "tfidf_matrix": None,
    "valid_sources": []
}
_KNOWLEDGE_CACHE_LOCK = threading.Lock()


def _semantic_similarity(query_text: str, doc_text: str) -> float:
    if not query_text.strip() or not doc_text.strip():
        return 0.0

    def _features(text: str) -> List[str]:
        tokens = re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
        compact_text = re.sub(r"\s+", "", text.lower())
        bigrams = [
            compact_text[index:index + 2]
            for index in range(len(compact_text) - 1)
            if compact_text[index:index + 2].strip()
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
    if not cache_hit:
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
        with _KNOWLEDGE_CACHE_LOCK:
            _KNOWLEDGE_CACHE["hash"] = current_hash
            _KNOWLEDGE_CACHE["vectorizer"] = vectorizer
            _KNOWLEDGE_CACHE["tfidf_matrix"] = tfidf_matrix
            _KNOWLEDGE_CACHE["valid_sources"] = list(valid_sources)

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
    with tempfile.TemporaryDirectory(prefix="resume-agent-vector-") as vector_dir:
        vector_store = SimpleVectorStore(vector_dir)
        for source in valid_sources:
            pattern = source.pattern
            doc_text = " ".join(
                [
                    pattern.company_name,
                    pattern.job_title,
                    pattern.structure_summary,
                    " ".join(pattern.retrieval_terms),
                    source.cleaned_text[:500],
                ]
            ).strip()
            vector_store.add_document(
                doc_text,
                {"source_id": source.id},
                doc_id=source.id,
            )
        vector_scores = {
            item["id"]: float(item.get("similarity", 0.0))
            for item in vector_store.search(
                query_text,
                n_results=max(5, len(valid_sources)),
                min_similarity=0.0,
            )
        }
    
    # 4. 점수 정렬 및 상위 5개 추출
    ranked_indices = cosine_similarities.argsort()[::-1]
    
    hints: List[dict[str, Any]] = []
    for idx in ranked_indices[:5]:
        score = cosine_similarities[idx]
        if score <= 0.01:
            continue
            
        source = valid_sources[idx]
        pattern = source.pattern
        doc_text = " ".join(
            [
                pattern.company_name,
                pattern.job_title,
                pattern.structure_summary,
                " ".join(pattern.retrieval_terms),
                source.cleaned_text[:300],
            ]
        ).strip()
        semantic_score = _semantic_similarity(query_text, doc_text)
        vector_score = vector_scores.get(source.id, 0.0)

        if pattern.structure_signals.has_metrics:
            score += 0.05
        combined_score = score + (semantic_score * 0.15) + (vector_score * 0.2)
            
        hints.append(
            {
                "title": source.title,
                "signal": f"{pattern.company_name or '일반'} / {pattern.job_title or '직무 미상'} / TF-IDF score {score:.3f}",
                "structure_summary": pattern.structure_summary,
                "caution": pattern.caution,
                "question_types": [qt.value for qt in pattern.question_types],
                "semantic_score": round(semantic_score, 3),
                "vector_score": round(vector_score, 3),
                "combined_score": round(combined_score, 3),
            }
        )
    hints.sort(
        key=lambda item: (
            float(item.get("combined_score", 0.0)),
            float(item.get("vector_score", 0.0)),
            float(item.get("semantic_score", 0.0)),
        ),
        reverse=True,
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

def build_coach_artifact(
    project: ApplicationProject,
    experiences: List[Experience],
    gap_report: dict[str, Any],
    outcome_summary: dict[str, Any] | None = None,
    strategy_outcome_summary: dict[str, Any] | None = None,
    current_pattern: str | None = None,
) -> dict[str, Any]:
    allocations = allocate_experiences(
        project.questions,
        experiences,
        project.priority_experience_order,
        outcome_summary=outcome_summary,
        strategy_outcome_summary=strategy_outcome_summary,
        current_pattern=current_pattern,
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

    assumptions = [f"[ASSUMPTION] 답변 톤은 '{project.tone_style}' 기준으로 유지합니다."]
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
        lines.extend(["", "## ASSUMPTIONS", *[f"- {item}" for item in artifact["assumptions"]]])
    if artifact.get("needs_verification"):
        lines.extend(["", "## NEEDS VERIFICATION", *[f"- {item}" for item in artifact["needs_verification"]]])
    if artifact.get("question_risks"):
        lines.extend(["", "## QUESTION RISKS", *[f"- {item}" for item in artifact["question_risks"]]])
    if artifact.get("recommendations"):
        lines.extend(["", "## RECOMMENDATIONS", *[f"- {item}" for item in artifact["recommendations"]]])
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
    empty = [heading for heading in headings if heading in text and not _section_has_content(text, heading, headings)]
    return {"passed": not missing and not empty, "missing": missing, "empty": empty}

def validate_block_contract(text: str, headings: List[str]) -> dict[str, Any]:
    missing = [heading for heading in headings if heading not in text]
    empty = [heading for heading in headings if heading in text and not _section_has_content(text, heading, headings)]
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
