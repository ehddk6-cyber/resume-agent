import csv
import hashlib
import html
import re
from collections import Counter
from pathlib import Path
from typing import Any, List
from urllib.parse import parse_qs, unquote, urlparse

import requests

from .models import (
    KnowledgeSource,
    PatternKB,
    SourceType,
    StructureSignals,
    QuestionType,
    SuccessCase,
    SuccessPattern,
)
from .classifier import (
    classify_question,
    extract_question_keywords,
    QUESTION_TYPE_LABELS,
    MARKETING_PATTERNS,
)
from .pdf_utils import extract_text_from_pdf
from .company_analyzer import SUCCESS_PATTERN_KEYWORDS


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
        if stripped.startswith("🔥"):
            continue
        if re.fullmatch(r"https?://(?:www\.)?linkareer\.com/cover-letter/\S+", stripped):
            continue
        cleaned_lines.append(line.rstrip())
    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def strip_html_text(text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_title_meta(title: str) -> dict[str, str]:
    parts = [part.strip() for part in title.split("/")]
    return {
        "company_name": parts[0] if len(parts) > 0 else "",
        "job_title": parts[1] if len(parts) > 1 else "",
        "season": parts[2] if len(parts) > 2 else "",
    }


def extract_question_lines(text: str) -> List[str]:
    return [
        match.group(1).strip() for match in re.finditer(r"(?m)^\s*\d+\.\s*(.+)$", text)
    ]


def summarize_structure(
    company: str, job: str, question_types: List[str], question_count: int
) -> str:
    labels = [
        QUESTION_TYPE_LABELS.get(QuestionType(item), item)
        for item in question_types[:4]
    ]
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


def detect_patterns(text: str) -> List[SuccessPattern]:
    """텍스트에서 성공 패턴을 감지합니다. (키워드 매칭 기반, 2개 이상 매칭 시 해당 패턴)"""
    detected: List[SuccessPattern] = []
    for pattern, keywords in SUCCESS_PATTERN_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text)
        if matches >= 2:
            detected.append(pattern)
    return detected


def build_retrieval_terms(
    meta: dict[str, str], spec_text: str, question_lines: List[str]
) -> List[str]:
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
    companies = Counter(
        source.pattern.company_name
        for source in sources
        if source.pattern and source.pattern.company_name
    )
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
        source_type=SourceType.LOCAL_MARKDOWN
        if path.suffix.lower() == ".md"
        else SourceType.LOCAL_TEXT,
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
        ),
    )


def build_url_source(url: str, text: str, title: str | None = None) -> KnowledgeSource:
    cleaned_text = clean_source_text(strip_html_text(text))
    question_lines = extract_question_lines(cleaned_text)
    question_types = [classify_question(line) for line in question_lines[:6]]
    source_title = title or url

    return KnowledgeSource(
        id=stable_id("url", source_title, url),
        source_type=SourceType.USER_URL_PUBLIC,
        title=source_title,
        url=url,
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
            structure_summary="공개 웹 조사 문서",
            structure_signals=StructureSignals(
                has_star=bool(re.search(r"상황|행동|결과", cleaned_text)),
                has_metrics=bool(re.search(r"\d", cleaned_text)),
                warns_against_copying=True,
            ),
            spec_keywords=[],
            retrieval_terms=extract_spec_keywords(cleaned_text)[:10],
            caution="외부 웹 문서. 사실 여부와 최신성은 별도 검증 필요.",
            source_url=url,
        ),
    )


def ingest_csv(path: Path) -> tuple[List[KnowledgeSource], List[SuccessCase]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    sources: List[KnowledgeSource] = []
    success_cases: List[SuccessCase] = []
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
            has_star=bool(
                re.search(r"상황|과제|행동|결과|이를 위해|그 결과", cleaned_text)
            ),
            has_metrics=bool(
                re.search(r"\d+[%명건회배점]|[0-9]+\.[0-9]+", cleaned_text)
            ),
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
                structure_summary=summarize_structure(
                    meta_dict["company_name"],
                    meta_dict["job_title"],
                    [qt.value for qt in question_types],
                    len(question_lines),
                ),
                structure_signals=structure_signals,
                spec_keywords=extract_spec_keywords(spec_text),
                retrieval_terms=build_retrieval_terms(
                    meta_dict, spec_text, question_lines
                ),
                caution="표현 복제 금지. 구조만 참고.",
                source_url=url,
            ),
        )
        sources.append(source)

        # SuccessCase 생성 (패턴 감지 포함)
        patterns = detect_patterns(cleaned_text)
        case = SuccessCase.from_csv_row(
            title=title,
            company_name=meta_dict["company_name"],
            job_title=meta_dict["job_title"],
            spec_summary=spec_text,
            answer_text=cleaned_text,
            source_url=url,
            detected_patterns=patterns,
        )
        success_cases.append(case)

    return sources, success_cases


def ingest_source_file(path: Path) -> tuple[List[KnowledgeSource], List[SuccessCase]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return ingest_csv(path)
    if suffix == ".pdf":
        text = extract_text_from_pdf(path)
        if not text.strip():
            return [], []
        return [build_generic_source(path, text)], []
    if suffix == ".docx":
        from .pdf_utils import extract_text_from_docx

        text = extract_text_from_docx(path)
        if not text.strip():
            return [], []
        return [build_generic_source(path, text)], []
    if suffix == ".url":
        urls = [
            line.strip()
            for line in path.read_text(
                encoding="utf-8-sig", errors="ignore"
            ).splitlines()
            if line.strip()
        ]
        sources: List[KnowledgeSource] = []
        for url in urls:
            sources.extend(ingest_public_url(url))
        return sources, []
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    return [build_generic_source(path, text)], []
    if suffix == ".url":
        urls = [
            line.strip()
            for line in path.read_text(
                encoding="utf-8-sig", errors="ignore"
            ).splitlines()
            if line.strip()
        ]
        sources: List[KnowledgeSource] = []
        for url in urls:
            sources.extend(ingest_public_url(url))
        return sources
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    return [build_generic_source(path, text)]


def ingest_public_url(url: str, timeout: int = 15) -> List[KnowledgeSource]:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "resume-agent/0.1 (+public knowledge ingestion)"},
    )
    response.raise_for_status()
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", response.text)
    title = strip_html_text(title_match.group(1)) if title_match else url
    return [build_url_source(url=url, text=response.text, title=title)]


def discover_public_urls(
    query: str,
    limit: int = 5,
    timeout: int = 15,
) -> List[dict[str, str]]:
    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        timeout=timeout,
        headers={"User-Agent": "resume-agent/0.1 (+public web discovery)"},
    )
    response.raise_for_status()

    results: List[dict[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(response.text):
        href = html.unescape(match.group(1))
        title = strip_html_text(match.group(2))
        parsed = urlparse(href)
        if "uddg" in parsed.query:
            url = parse_qs(parsed.query).get("uddg", [href])[0]
            url = unquote(url)
        else:
            url = href
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        results.append({"query": query, "url": url, "title": title or url})
        if len(results) >= limit:
            break
    return results


def calculate_sources_hash(sources: List[KnowledgeSource]) -> str:
    """모든 지식 소스의 ID와 내용을 기반으로 전체 해시를 생성합니다."""
    combined = "".join(sorted([s.id for s in sources]))
    return hashlib.sha1(combined.encode("utf-8")).hexdigest()[:16]


def extract_keywords_morphological(text: str, top_n: int = 20) -> List[str]:
    """형태소 분석 기반 키워드 추출 (kiwipiepy 활용)
    
    Kiwi 형태소 분석기를 사용하여 명사/동사/형용사를 추출합니다.
    - 일반적인 조사/어미 제거
    - 불용어 필터링
    """
    from kiwipiepy import Kiwi
    
    kiwi = Kiwi()
    keywords: List[str] = []
    stopwords = {
        "것", "수", "등", "및", "에", "을", "를", "의", "가", "이", "은", "들",
        "에", "에서", "에게", "한테", "께", "랑", "이랑", "나", "과", "와",
        "때", "더", "년", "월", "일", "시", "분", "초",
        "있습니다", "합니다", "했습니다", "했습니다", "했습니다",
        "위해", "대한", "통해", "대해", "위한", "따라", "함으로써"
    }
    
    # 형태소 분석
    result = kiwi.tokenize(text)
    
    for token in result:
        word = token.form
        pos = token.tag
        
        # 명사(NNG, NNP), 동사(VV), 형용사(VA)만 추출
        if pos in ['NNG', 'NNP', 'VV', 'VA'] and len(word) >= 2:
            if word not in stopwords and not word.isdigit():
                keywords.append(word)
    
    # 빈도수 기준 정렬
    keyword_freq: Counter = Counter(keywords)
    
    # 중복 제거 후 상위 N개 반환
    seen: List[str] = []
    for kw, count in keyword_freq.most_common(top_n * 2):
        if kw not in seen:
            seen.append(kw)
            if len(seen) >= top_n:
                break
    
    return seen


def compute_morphological_similarity(text1: str, text2: str) -> float:
    """형태소 분석 기반 Jaccard 유사도 계산
    
    두 텍스트의 형태소 기반 키워드 Jaccard 유사도를 반환합니다.
    """
    kw1 = set(extract_keywords_morphological(text1, top_n=30))
    kw2 = set(extract_keywords_morphological(text2, top_n=30))
    
    if not kw1 or not kw2:
        return 0.0
    
    intersection = len(kw1 & kw2)
    union = len(kw1 | kw2)
    
    return intersection / union if union > 0 else 0.0
