from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any


EVIDENCE_BONUS = {"L1": 1, "L2": 3, "L3": 6}
QUESTION_TYPE_PATTERNS = {
    "TYPE_A": [r"지원동기", r"지원.*이유", r"왜 .*지원", r"직무.*적합", r"관심.*계기"],
    "TYPE_B": [r"직무역량", r"역량", r"강점", r"업무 수행.*노력", r"전문성"],
    "TYPE_C": [r"협업", r"협력", r"갈등", r"소통", r"의사소통", r"팀워크"],
    "TYPE_D": [r"성장", r"배운 점", r"자기개발", r"학습", r"개선", r"보완"],
    "TYPE_E": [r"입사 후", r"포부", r"기여", r"발전 방향", r"향후 계획"],
    "TYPE_F": [r"원칙", r"기준", r"신뢰", r"책임감", r"약속"],
    "TYPE_G": [r"실패", r"어려운 문제", r"극복", r"위기", r"재발 방지"],
    "TYPE_H": [r"고객", r"민원", r"응대", r"만족", r"보호자", r"서비스"],
    "TYPE_I": [r"우선순위", r"압박", r"판단", r"시간", r"제한된 자원", r"협상"],
}
QUESTION_TYPE_LABELS = {
    "TYPE_A": "지원동기와 직무 적합성",
    "TYPE_B": "핵심 역량",
    "TYPE_C": "협업과 조정",
    "TYPE_D": "성장과 학습 루프",
    "TYPE_E": "입사 후 기여",
    "TYPE_F": "원칙과 신뢰",
    "TYPE_G": "실패와 복기",
    "TYPE_H": "고객응대",
    "TYPE_I": "상황판단과 우선순위",
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
    "TYPE_A": {"직무역량", "성과"},
    "TYPE_B": {"직무역량", "데이터", "문제해결"},
    "TYPE_C": {"협업", "의사소통", "리더십"},
    "TYPE_D": {"성장", "문제해결"},
    "TYPE_E": {"직무역량", "성과"},
    "TYPE_F": {"성과", "의사소통"},
    "TYPE_G": {"실패", "문제해결"},
    "TYPE_H": {"고객응대", "의사소통"},
    "TYPE_I": {"상황판단", "문제해결"},
}
MARKETING_PATTERNS = [
    "링커리어 자소서 만능검색기",
    "더 많은 최신 합격 자소서",
    "문항별 예시는",
    "AI 개요",
]


def classify_question(text: str) -> str:
    normalized = text.strip()
    for question_type, patterns in QUESTION_TYPE_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            return question_type
    return "TYPE_B"


def extract_question_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z가-힣]{2,}", text)
    seen: list[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token not in seen:
            seen.append(token)
    return seen[:8]


def analyze_gaps(project: dict[str, Any], experiences: list[dict[str, Any]]) -> dict[str, Any]:
    questions = project.get("questions", [])
    missing_metrics = [exp["title"] for exp in experiences if not metric_present(exp)]
    missing_evidence = [exp["title"] for exp in experiences if not str(exp.get("evidence_text", "")).strip()]
    needs_verification = [exp["title"] for exp in experiences if exp.get("verification_status") != "verified"]
    l3_count = sum(1 for exp in experiences if exp.get("evidence_level") == "L3")

    question_risks: list[dict[str, Any]] = []
    for question in questions:
        candidates = [
            score_experience(question, exp, project.get("priority_experience_order", []), [], None)
            for exp in experiences
        ]
        best_score = max((item["score"] for item in candidates), default=0)
        question_risks.append(
            {
                "question_id": question.get("id"),
                "order_no": question.get("order_no"),
                "question_type": classify_question(str(question.get("question_text", ""))),
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
    recommendations: list[str] = []
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


def allocate_experiences(
    questions: list[dict[str, Any]],
    experiences: list[dict[str, Any]],
    priority_order: list[str],
) -> list[dict[str, Any]]:
    allocations: list[dict[str, Any]] = []
    used_experience_ids: list[str] = []
    previous_organization: str | None = None

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
                "question_id": question.get("id"),
                "order_no": question.get("order_no"),
                "question_type": detail["question_type"],
                "experience_id": exp.get("id"),
                "experience_title": exp.get("title"),
                "score": detail["score"],
                "reason": (
                    f"문항 유형은 {QUESTION_TYPE_LABELS.get(detail['question_type'], detail['question_type'])}으로 분류했고, "
                    f"키워드({', '.join(detail['keywords'][:3]) or '기본'})와 증거 수준, 태그 적합도를 반영했습니다."
                ),
                "reuse_reason": (
                    "다른 경험보다 적합도가 높아 재사용되었으며 관점을 다르게 써야 합니다."
                    if exp.get("id") in used_experience_ids
                    else None
                ),
            }
        )
        used_experience_ids.append(str(exp.get("id")))
        previous_organization = str(exp.get("organization", "")).strip() or None

    if allocations and not any(find_experience(experiences, item["experience_id"]).get("evidence_level") == "L3" for item in allocations):
        l3_candidates = [exp for exp in experiences if exp.get("evidence_level") == "L3"]
        if l3_candidates:
            strongest = l3_candidates[0]
            allocations[0]["experience_id"] = strongest.get("id")
            allocations[0]["experience_title"] = strongest.get("title")
            allocations[0]["reason"] += " 최소 1개의 L3 경험을 상위 문항에 강제로 배치했습니다."

    return allocations


def build_coach_artifact(project: dict[str, Any], experiences: list[dict[str, Any]], gap_report: dict[str, Any]) -> dict[str, Any]:
    allocations = allocate_experiences(
        project.get("questions", []),
        experiences,
        list(project.get("priority_experience_order", [])),
    )
    current_summary: list[str] = []
    required_inputs: list[str] = []

    for allocation in allocations:
        experience = find_experience(experiences, allocation["experience_id"])
        current_summary.append(
            f"{allocation['order_no']}번 문항은 {QUESTION_TYPE_LABELS.get(allocation['question_type'], allocation['question_type'])}으로 분류했고, "
            f"주력 경험은 {experience.get('title', '미배정')}입니다."
        )
        if not metric_present(experience):
            required_inputs.append(f"{experience.get('title', '미상 경험')}: 정량 또는 비교 근거를 보강하세요.")
        if not str(experience.get("evidence_text", "")).strip():
            required_inputs.append(f"{experience.get('title', '미상 경험')}: 면접 방어용 증빙 텍스트를 추가하세요.")

    needs_verification = [
        f"[NEEDS_VERIFICATION] {title}"
        for title in gap_report.get("needs_verification", [])
    ]
    if not any(exp.get("evidence_level") == "L3" for exp in experiences):
        needs_verification.append("[NEEDS_VERIFICATION] L3 수준의 증거 경험이 없습니다.")

    artifact = {
        "current_stage": "HANDOFF_READY",
        "purpose": f"{project.get('company_name', '')} / {project.get('job_title', '')} 문항에 대한 경험 배분과 리스크를 정리합니다.",
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


def validate_block_contract(text: str, headings: list[str]) -> dict[str, Any]:
    missing = [heading for heading in headings if heading not in text]
    return {"passed": not missing, "missing": missing}


def score_experience(
    question: dict[str, Any],
    experience: dict[str, Any],
    priority_order: list[str],
    already_used: list[str],
    previous_organization: str | None,
) -> dict[str, Any]:
    question_text = str(question.get("question_text", ""))
    question_type = classify_question(question_text)
    keywords = extract_question_keywords(question_text)
    haystack = " ".join(
        str(experience.get(key, ""))
        for key in (
            "title",
            "organization",
            "situation",
            "task",
            "action",
            "result",
            "personal_contribution",
            "metrics",
            "evidence_text",
        )
    )
    tags = {str(tag) for tag in experience.get("tags", [])}

    score = EVIDENCE_BONUS.get(str(experience.get("evidence_level", "L1")), 0)
    score += 3 if experience.get("verification_status") == "verified" else -2
    score += sum(1 for keyword in keywords if keyword in haystack) * 2
    score += len(tags & TAG_HINTS.get(question_type, set())) * 3
    if metric_present(experience):
        score += 2
    if str(experience.get("title", "")) in priority_order:
        score += (len(priority_order) - priority_order.index(str(experience.get("title", "")))) * 3
    if str(experience.get("id")) in already_used:
        score -= 7
    if previous_organization and previous_organization == str(experience.get("organization", "")):
        score -= 4

    return {"score": score, "question_type": question_type, "keywords": keywords}


def ingest_source_file(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return ingest_csv(path)
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    return [build_generic_source(path, text)]


def ingest_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    sources: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        title = str(row.get("제목", "")).strip() or f"{path.stem}-{index}"
        url = str(row.get("출처URL", "")).strip() or None
        raw_text = str(row.get("자소서본문", "")).strip()
        spec_text = str(row.get("합격스펙", "")).strip()
        cleaned_text = clean_source_text(raw_text)
        meta = parse_title_meta(title)
        question_lines = extract_question_lines(cleaned_text)
        question_types = [classify_question(line) for line in question_lines[:6]]
        structure_signals = {
            "has_star": bool(re.search(r"상황|과제|행동|결과|이를 위해|그 결과", cleaned_text)),
            "has_metrics": bool(re.search(r"\d+[%명건회배점]|[0-9]+\.[0-9]+", cleaned_text)),
            "warns_against_copying": True,
        }
        source = {
            "id": stable_id("csv", title, url or "", str(index)),
            "source_type": "local_csv_row",
            "title": title,
            "url": url,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "meta": {
                **meta,
                "spec_text": spec_text,
                "question_count": len(question_lines),
            },
            "pattern": {
                "company_name": meta["company_name"],
                "job_title": meta["job_title"],
                "season": meta["season"],
                "question_types": question_types,
                "structure_summary": summarize_structure(meta["company_name"], meta["job_title"], question_types, len(question_lines)),
                "structure_signals": structure_signals,
                "spec_keywords": extract_spec_keywords(spec_text),
                "retrieval_terms": build_retrieval_terms(meta, spec_text, question_lines),
                "caution": "표현 복제 금지. 구조만 참고.",
                "source_url": url,
            },
        }
        sources.append(source)
    return sources


def build_generic_source(path: Path, text: str) -> dict[str, Any]:
    cleaned_text = clean_source_text(text)
    return {
        "id": stable_id("file", path.name, cleaned_text[:80]),
        "source_type": "local_markdown" if path.suffix.lower() == ".md" else "local_text",
        "title": path.stem,
        "url": None,
        "raw_text": text,
        "cleaned_text": cleaned_text,
        "meta": {
            "company_name": "",
            "job_title": "",
            "season": "",
            "question_count": len(extract_question_lines(cleaned_text)),
        },
        "pattern": {
            "company_name": "",
            "job_title": "",
            "season": "",
            "question_types": [classify_question(line) for line in extract_question_lines(cleaned_text)[:6]],
            "structure_summary": "일반 참고 문서",
            "structure_signals": {
                "has_star": bool(re.search(r"상황|행동|결과", cleaned_text)),
                "has_metrics": bool(re.search(r"\d", cleaned_text)),
                "warns_against_copying": True,
            },
            "spec_keywords": [],
            "retrieval_terms": [],
            "caution": "표현 복제 금지. 구조만 참고.",
            "source_url": None,
        },
    }


def clean_source_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(pattern in stripped for pattern in MARKETING_PATTERNS):
            continue
        if stripped.startswith("👉"):
            continue
        cleaned_lines.append(line.rstrip())
    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def parse_title_meta(title: str) -> dict[str, str]:
    parts = [part.strip() for part in title.split("/")]
    return {
        "company_name": parts[0] if len(parts) > 0 else "",
        "job_title": parts[1] if len(parts) > 1 else "",
        "season": parts[2] if len(parts) > 2 else "",
    }


def extract_question_lines(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"(?m)^\s*\d+\.\s*(.+)$", text)]


def summarize_structure(company: str, job: str, question_types: list[str], question_count: int) -> str:
    labels = [QUESTION_TYPE_LABELS.get(item, item) for item in question_types[:4]]
    if labels:
        return f"{company or '일반'} {job or '직무'} 문항 {question_count}개 기준, {' / '.join(labels)} 중심 구조"
    return f"{company or '일반'} {job or '직무'} 기준 구조 참고"


def extract_spec_keywords(spec_text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z가-힣]{2,}", spec_text)
    seen: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return seen[:10]


def build_retrieval_terms(meta: dict[str, str], spec_text: str, question_lines: list[str]) -> list[str]:
    terms = [
        meta.get("company_name", ""),
        meta.get("job_title", ""),
        meta.get("season", ""),
        *extract_spec_keywords(spec_text)[:5],
    ]
    for line in question_lines[:3]:
        terms.extend(extract_question_keywords(line)[:3])
    deduped: list[str] = []
    for term in terms:
        if term and term not in deduped:
            deduped.append(term)
    return deduped[:15]


def summarize_knowledge_sources(sources: list[dict[str, Any]]) -> dict[str, Any]:
    source_types = Counter(source["source_type"] for source in sources)
    companies = Counter(source["pattern"].get("company_name", "") for source in sources if source["pattern"].get("company_name"))
    return {
        "count": len(sources),
        "source_types": dict(source_types),
        "top_companies": companies.most_common(10),
    }


def build_knowledge_hints(sources: list[dict[str, Any]], project: dict[str, Any]) -> list[dict[str, Any]]:
    company = str(project.get("company_name", "")).strip()
    job = str(project.get("job_title", "")).strip()
    question_terms: list[str] = []
    question_types: list[str] = []
    for question in project.get("questions", []):
        text = str(question.get("question_text", ""))
        question_terms.extend(extract_question_keywords(text))
        question_types.append(classify_question(text))

    ranked: list[tuple[int, dict[str, Any]]] = []
    for source in sources:
        pattern = source.get("pattern", {})
        score = 0
        retrieval_terms = set(pattern.get("retrieval_terms", []))
        if company and company in retrieval_terms:
            score += 8
        if job and job in retrieval_terms:
            score += 8
        score += sum(2 for term in question_terms[:8] if term in retrieval_terms)
        score += sum(3 for qtype in question_types if qtype in pattern.get("question_types", []))
        if pattern.get("structure_signals", {}).get("has_metrics"):
            score += 1
        if score > 0:
            ranked.append((score, source))

    ranked.sort(key=lambda item: item[0], reverse=True)
    hints: list[dict[str, Any]] = []
    for score, source in ranked[:5]:
        pattern = source.get("pattern", {})
        hints.append(
            {
                "title": source.get("title"),
                "signal": f"{pattern.get('company_name') or '일반'} / {pattern.get('job_title') or '직무 미상'} / score {score}",
                "structure_summary": pattern.get("structure_summary", "구조 요약 없음"),
                "caution": pattern.get("caution", "표현 복제 금지. 구조만 참고."),
                "question_types": pattern.get("question_types", []),
            }
        )
    return hints


def metric_present(experience: dict[str, Any]) -> bool:
    metric_text = str(experience.get("metrics", "")).strip()
    return bool(metric_text and metric_text != "정량 수치 없음")


def find_experience(experiences: list[dict[str, Any]], experience_id: str) -> dict[str, Any]:
    for experience in experiences:
        if str(experience.get("id")) == str(experience_id):
            return experience
    return {}


def stable_id(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:12]
