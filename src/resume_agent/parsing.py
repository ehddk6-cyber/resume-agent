import csv
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any, List

from .models import KnowledgeSource, PatternKB, SourceType, StructureSignals, QuestionType
from .classifier import classify_question, extract_question_keywords, QUESTION_TYPE_LABELS, MARKETING_PATTERNS

def stable_id(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:12]

def clean_source_text(text: str) -> str:
    cleaned_lines: List[str] = []
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

def extract_question_lines(text: str) -> List[str]:
    return [match.group(1).strip() for match in re.finditer(r"(?m)^\s*\d+\.\s*(.+)$", text)]

def summarize_structure(company: str, job: str, question_types: List[str], question_count: int) -> str:
    labels = [QUESTION_TYPE_LABELS.get(QuestionType(item), item) for item in question_types[:4]]
    if labels:
        return f"{company or '일반'} {job or '직무'} 문항 {question_count}개 기준, {' / '.join(labels)} 중심 구조"
    return f"{company or '일반'} {job or '직무'} 기준 구조 참고"

def extract_spec_keywords(spec_text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z가-힣]{2,}", spec_text)
    seen: List[str] = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return seen[:10]

def build_retrieval_terms(meta: dict[str, str], spec_text: str, question_lines: List[str]) -> List[str]:
    terms = [
        meta.get("company_name", ""),
        meta.get("job_title", ""),
        meta.get("season", ""),
        *extract_spec_keywords(spec_text)[:5],
    ]
    for line in question_lines[:3]:
        terms.extend(extract_question_keywords(line)[:3])
    deduped: List[str] = []
    for term in terms:
        if term and term not in deduped:
            deduped.append(term)
    return deduped[:15]

def summarize_knowledge_sources(sources: List[KnowledgeSource]) -> dict[str, Any]:
    source_types = Counter(source.source_type.value for source in sources)
    companies = Counter(source.pattern.company_name for source in sources if source.pattern and source.pattern.company_name)
    return {
        "count": len(sources),
        "source_types": dict(source_types),
        "top_companies": companies.most_common(10),
    }

def build_generic_source(path: Path, text: str) -> KnowledgeSource:
    cleaned_text = clean_source_text(text)
    question_lines = extract_question_lines(cleaned_text)
    question_types = [classify_question(line) for line in question_lines[:6]]
    
    return KnowledgeSource(
        id=stable_id("file", path.name, cleaned_text[:80]),
        source_type=SourceType.LOCAL_MARKDOWN if path.suffix.lower() == ".md" else SourceType.LOCAL_TEXT,
        title=path.stem,
        url=None,
        raw_text=text,
        cleaned_text=cleaned_text,
        meta={
            "company_name": "",
            "job_title": "",
            "season": "",
            "question_count": len(question_lines),
        },
        pattern=PatternKB(
            company_name="",
            job_title="",
            season="",
            question_types=question_types,
            structure_summary="일반 참고 문서",
            structure_signals=StructureSignals(
                has_star=bool(re.search(r"상황|행동|결과", cleaned_text)),
                has_metrics=bool(re.search(r"\d", cleaned_text)),
                warns_against_copying=True,
            ),
            spec_keywords=[],
            retrieval_terms=[],
            caution="표현 복제 금지. 구조만 참고.",
            source_url=None,
        )
    )

def ingest_csv(path: Path) -> List[KnowledgeSource]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    sources: List[KnowledgeSource] = []
    for index, row in enumerate(rows, start=1):
        title = str(row.get("제목", "")).strip() or f"{path.stem}-{index}"
        url = str(row.get("출처URL", "")).strip() or None
        raw_text = str(row.get("자소서본문", "")).strip()
        spec_text = str(row.get("합격스펙", "")).strip()
        cleaned_text = clean_source_text(raw_text)
        meta_dict = parse_title_meta(title)
        question_lines = extract_question_lines(cleaned_text)
        question_types = [classify_question(line) for line in question_lines[:6]]
        structure_signals = StructureSignals(
            has_star=bool(re.search(r"상황|과제|행동|결과|이를 위해|그 결과", cleaned_text)),
            has_metrics=bool(re.search(r"\d+[%명건회배점]|[0-9]+\.[0-9]+", cleaned_text)),
            warns_against_copying=True,
        )
        
        source = KnowledgeSource(
            id=stable_id("csv", title, url or "", str(index)),
            source_type=SourceType.LOCAL_CSV_ROW,
            title=title,
            url=url,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            meta={
                **meta_dict,
                "spec_text": spec_text,
                "question_count": len(question_lines),
            },
            pattern=PatternKB(
                company_name=meta_dict["company_name"],
                job_title=meta_dict["job_title"],
                season=meta_dict["season"],
                question_types=question_types,
                structure_summary=summarize_structure(meta_dict["company_name"], meta_dict["job_title"], [qt.value for qt in question_types], len(question_lines)),
                structure_signals=structure_signals,
                spec_keywords=extract_spec_keywords(spec_text),
                retrieval_terms=build_retrieval_terms(meta_dict, spec_text, question_lines),
                caution="표현 복제 금지. 구조만 참고.",
                source_url=url,
            )
        )
        sources.append(source)
    return sources

def ingest_source_file(path: Path) -> List[KnowledgeSource]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return ingest_csv(path)
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    return [build_generic_source(path, text)]

def calculate_sources_hash(sources: List[KnowledgeSource]) -> str:
    """모든 지식 소스의 ID와 내용을 기반으로 전체 해시를 생성합니다."""
    combined = "".join(sorted([s.id for s in sources]))
    return hashlib.sha1(combined.encode("utf-8")).hexdigest()[:16]