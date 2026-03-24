from typing import Any, List, Optional
from .models import ApplicationProject, Experience, Question, EvidenceLevel, VerificationStatus
from .classifier import classify_question, extract_question_keywords, TAG_HINTS, QUESTION_TYPE_LABELS

EVIDENCE_BONUS = {EvidenceLevel.L1: 1, EvidenceLevel.L2: 4, EvidenceLevel.L3: 8}
REUSE_PENALTY = 7

def metric_present(experience: Experience) -> bool:
    metric_text = experience.metrics.strip()
    return bool(metric_text and metric_text != "정량 수치 없음")

def score_experience(
    question: Question,
    experience: Experience,
    priority_order: List[str],
    already_used: List[str],
    previous_organization: Optional[str],
) -> dict[str, Any]:
    question_text = question.question_text
    question_type = classify_question(question_text)
    keywords = extract_question_keywords(question_text)
    
    haystack = " ".join([
        experience.title,
        experience.organization,
        experience.situation,
        experience.task,
        experience.action,
        experience.result,
        experience.personal_contribution,
        experience.metrics,
        experience.evidence_text,
    ])
    tags = set(experience.tags)

    score = EVIDENCE_BONUS.get(experience.evidence_level, 0)
    score += 3 if experience.verification_status == VerificationStatus.VERIFIED else -2
    score += sum(1 for keyword in keywords if keyword in haystack) * 2
    score += len(tags & TAG_HINTS.get(question_type, set())) * 3
    if metric_present(experience):
        score += 2
    if experience.title in priority_order:
        score += (len(priority_order) - priority_order.index(experience.title)) * 3
    if experience.id in already_used:
        score -= REUSE_PENALTY
    if previous_organization and previous_organization == experience.organization.strip():
        score -= 4

    return {"score": score, "question_type": question_type, "keywords": keywords}

def find_experience(experiences: List[Experience], experience_id: str) -> Optional[Experience]:
    for experience in experiences:
        if experience.id == experience_id:
            return experience
    return None

def allocate_experiences(
    questions: List[Question],
    experiences: List[Experience],
    priority_order: List[str],
) -> List[dict[str, Any]]:
    allocations: List[dict[str, Any]] = []
    used_experience_ids: List[str] = []
    previous_organization: Optional[str] = None

    for question in questions:
        candidates = [
            {
                "experience": exp,
                "detail": score_experience(question, exp, priority_order, used_experience_ids, previous_organization),
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
                    f"문항 유형은 {QUESTION_TYPE_LABELS.get(detail['question_type'], detail['question_type'])}으로 분류했고, "
                    f"키워드({', '.join(detail['keywords'][:3]) or '기본'})와 증거 수준, 태그 적합도를 반영했습니다."
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
    if allocations and not any(find_experience(experiences, item["experience_id"]).evidence_level == EvidenceLevel.L3 for item in allocations):
        l3_candidates = [exp for exp in experiences if exp.evidence_level == EvidenceLevel.L3]
        if l3_candidates:
            strongest = l3_candidates[0]
            allocations[0]["experience_id"] = strongest.id
            allocations[0]["experience_title"] = strongest.title
            allocations[0]["reason"] += " 최소 1개의 L3 경험을 상위 문항에 강제로 배치했습니다."

    return allocations

def analyze_gaps(project: ApplicationProject, experiences: List[Experience]) -> dict[str, Any]:
    questions = project.questions
    missing_metrics = [exp.title for exp in experiences if not metric_present(exp)]
    missing_evidence = [exp.title for exp in experiences if not exp.evidence_text.strip()]
    needs_verification = [exp.title for exp in experiences if exp.verification_status != VerificationStatus.VERIFIED]
    l3_count = sum(1 for exp in experiences if exp.evidence_level == EvidenceLevel.L3)

    question_risks: List[dict[str, Any]] = []
    for question in questions:
        candidates = [
            score_experience(question, exp, project.priority_experience_order, [], None)
            for exp in experiences
        ]
        best_score = max((item["score"] for item in candidates), default=0)
        question_risks.append(
            {
                "question_id": question.id,
                "order_no": question.order_no,
                "question_type": classify_question(question.question_text),
                "best_score": best_score,
                "risk": "high" if best_score < 5 else "medium" if best_score < 10 else "low",
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
        recommendations.append("정량 근거가 비어 있는 경험에 수치 또는 비교 근거를 보강하세요.")
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
        "recommendations": recommendations or ["즉시 보강이 필요한 위험 신호가 크지 않습니다."],
    }

def calculate_readability_score(text: str) -> dict[str, Any]:
    """텍스트의 가독성 점수와 개선 피드백을 반환합니다."""
    import re
    if not text.strip():
        return {"score": 0, "feedback": ["내용이 없습니다."]}
        
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
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
        feedback.append("STAR(상황/행동/결과) 구조를 나타내는 명확한 표현이 부족합니다.")
        
    return {"score": max(0, score), "feedback": feedback or ["가독성이 좋습니다."]}

def audit_facts(generated_text: str, source_experiences: List[Experience]) -> List[str]:
    """생성된 텍스트에 포함된 수치가 원본 경험 데이터에 존재하는지 엄격하게 검증합니다."""
    import re
    warnings = []
    
    # 1. 정교한 수치 패턴 추출 (숫자+단위 결합)
    metric_patterns = [
        r'\d+(?:\.\d+)?%',
        r'\d+건',
        r'\d+명',
        r'\d+배',
        r'\d+위',
        r'\d+시간',
        r'\d+일',
        r'\d+개월',
        r'\d+년',
        r'\d+월',
        r'\d+\.\d+/\d+\.\d+',
    ]
    
    combined_pattern = "|".join(metric_patterns)
    metrics_in_text = re.findall(combined_pattern, generated_text)
    
    if not metrics_in_text:
        return warnings
        
    # 2. 원본 데이터의 모든 수치 토큰화 (situation, task, action, result, metrics 모두 포함)
    source_text = " ".join([
        f"{exp.metrics} {exp.result} {exp.situation} {exp.action} {exp.task}" 
        for exp in source_experiences
    ])
    
    # 3. 엄격한 매칭
    for metric in set(metrics_in_text):
        if metric not in source_text:
            # 보조 확인: 수치가 분수 형태(학점 등)인 경우 부분 일치 허용
            is_partial_match = False
            if '/' in metric:
                num_part = metric.split('/')[0]
                if num_part in source_text:
                    is_partial_match = True
            
            if not is_partial_match:
                warnings.append(f"⚠️ [환각 의심] 생성된 수치 '{metric}'가 원본 데이터 어디에서도 발견되지 않았습니다.")
            
    return warnings
