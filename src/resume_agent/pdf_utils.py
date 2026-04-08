import re
from pathlib import Path
from typing import List, Dict, Any

from .logger import get_logger

logger = get_logger(__name__)

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


def extract_text_from_pdf(pdf_path: Path) -> str:
    """PDF 파일(또는 폴더 내의 모든 PDF)에서 텍스트를 추출합니다."""
    if not PdfReader:
        return ""

    texts = []

    # 단일 파일인 경우
    if pdf_path.is_file() and pdf_path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(pdf_path)
            text = "\n".join(
                page.extract_text() for page in reader.pages if page.extract_text()
            )
            texts.append(text)
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")

    # 디렉토리인 경우 (다중 JD 분석)
    elif pdf_path.is_dir():
        for file in pdf_path.glob("*.pdf"):
            try:
                reader = PdfReader(file)
                text = "\n".join(
                    page.extract_text() for page in reader.pages if page.extract_text()
                )
                texts.append(text)
            except Exception as e:
                logger.error(f"Error reading PDF {file}: {e}")

    return "\n\n".join(texts)


def extract_text_from_docx(docx_path: Path) -> str:
    """DOCX 파일에서 텍스트를 추출합니다."""
    if not Document:
        return ""

    if not docx_path.is_file() or docx_path.suffix.lower() != ".docx":
        return ""

    try:
        doc = Document(docx_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
    except Exception as e:
        logger.error(f"Error reading DOCX {docx_path}: {e}")
        return ""


def extract_jd_keywords(text: str) -> List[str]:
    """
    직무기술서 텍스트에서 명사형 키워드를 추출합니다.
    자주 등장하는 키워드(직무, 역량 관련)를 필터링하여 상위 10개를 반환합니다.
    """
    if not text:
        return []

    # 불용어(의미가 적은 일반 명사나 조사 등)
    stopwords = {
        "업무",
        "수행",
        "관련",
        "분야",
        "내용",
        "지원",
        "사항",
        "해당",
        "기타",
        "필요",
        "직무",
        "자격",
        "우대",
        "경험",
        "능력",
        "활용",
        "이해",
        "지식",
        "제출",
        "기준",
        "담당",
    }

    # 2글자 이상 한글/영문 단어 추출
    words = re.findall(r"[가-힣a-zA-Z]{2,}", text)

    # 단어 빈도 계산
    freq = {}
    for word in words:
        if word not in stopwords:
            freq[word] = freq.get(word, 0) + 1

    # 빈도순 정렬
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:10]]


def _split_ncs_items(text: str) -> List[str]:
    normalized = re.sub(r"[•·●▪■▶○]+", ",", text)
    normalized = normalized.replace(" / ", ",").replace("/", ",")
    normalized = normalized.replace("‧", ",").replace("·", ",")
    candidates = [
        item.strip(" -,\t")
        for item in re.split(r"[,;\n]+", normalized)
        if item.strip(" -,\t")
    ]
    deduped: List[str] = []
    for item in candidates:
        compact = re.sub(r"\s+", " ", item).strip()
        if len(compact) < 2:
            continue
        if compact not in deduped:
            deduped.append(compact)
    return deduped


def extract_ncs_job_spec(text: str) -> Dict[str, Any]:
    """직무기술서/JD 텍스트에서 NCS 능력단위, 요소, 직업기초·공통능력을 추출합니다."""
    if not text:
        return {
            "ability_units": [],
            "ability_unit_elements": [],
            "ncs_competencies": [],
        }

    normalized = re.sub(r"[ \t]+", " ", text)
    ability_units: List[str] = []
    ability_unit_elements: List[str] = []
    ncs_competencies: List[str] = []

    section_patterns = [
        ("ability_units", r"능력단위\s*[o:：]?\s*(.+?)(?=(?:능력단위요소|직업기초능력|직업공통능력|전형방법|참고|$))"),
        ("ability_unit_elements", r"능력단위요소\s*[o:：]?\s*(.+?)(?=(?:직업기초능력|직업공통능력|전형방법|참고|$))"),
        ("ncs_competencies", r"직업(?:기초|공통)능력\s*[o:：]?\s*(.+?)(?=(?:전형방법|참고|$))"),
    ]
    for bucket, pattern in section_patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE | re.DOTALL):
            items = _split_ncs_items(match.group(1))
            if bucket == "ability_units":
                ability_units.extend(items)
            elif bucket == "ability_unit_elements":
                ability_unit_elements.extend(items)
            else:
                ncs_competencies.extend(items)

    # "(의사소통능력) 경청 능력, 문서이해 능력" 같은 직무기초능력 하위요소를 잡습니다.
    for match in re.finditer(r"\(([가-힣A-Za-z]+능력)\)\s*([^()]+)", normalized):
        competency = re.sub(r"\s+", "", match.group(1))
        detail = match.group(2)
        ncs_competencies.append(competency)
        ability_unit_elements.extend(_split_ncs_items(detail))

    # 명시적 능력단위가 없어도 주요직무수행내용을 임시 능력단위 후보로 보존합니다.
    if not ability_units:
        for match in re.finditer(
            r"주요직무수행내용\s*[o:：]?\s*(.+?)(?=(?:지원자격요건|필요지식|필요기술|직무수행태도|직업(?:기초|공통)능력|전형방법|$))",
            normalized,
            re.IGNORECASE | re.DOTALL,
        ):
            for item in _split_ncs_items(match.group(1)):
                if 2 <= len(item) <= 40:
                    ability_units.append(item)

    def _dedupe(items: List[str]) -> List[str]:
        result: List[str] = []
        for item in items:
            compact = re.sub(r"\s+", " ", item).strip()
            if compact and compact not in result:
                result.append(compact)
        return result

    return {
        "ability_units": _dedupe(ability_units)[:12],
        "ability_unit_elements": _dedupe(ability_unit_elements)[:20],
        "ncs_competencies": _dedupe(ncs_competencies)[:12],
    }


def split_text(text: str, chunk_size: int = 3000, overlap: int = 500) -> List[str]:
    """
    텍스트를 chunk_size 크기로 나눕니다.
    문단 단위(\n\n)로 먼저 나누어 문맥 파편화를 최소화합니다.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            # 단일 문단이 chunk_size보다 큰 경우 강제 분할
            if len(para) > chunk_size:
                start = 0
                while start < len(para):
                    chunks.append(para[start : start + chunk_size].strip())
                    start += chunk_size - overlap
                current_chunk = ""
            else:
                current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def analyze_jd_structure(text: str) -> Dict[str, Any]:
    """
    JD 텍스트를 섹션별로 분석합니다.

    Returns:
        Dict with keys: required_qualifications, preferred_qualifications,
                        responsibilities, tech_stack, culture_keywords
    """
    if not text:
        return _empty_jd_analysis()

    # 섹션 분리 패턴
    sections = {
        "required_qualifications": [],
        "preferred_qualifications": [],
        "responsibilities": [],
        "tech_stack": [],
        "culture_keywords": [],
    }

    lines = text.split("\n")
    current_section = None

    # 섹션 헤더 패턴
    section_patterns = {
        "required_qualifications": [
            r"자격\s*요건",
            r"필수\s*자격",
            r"자격\s*조건",
            r"최소\s*자격",
            r"required",
            r"qualifications",
            r"minimum",
        ],
        "preferred_qualifications": [
            r"우대\s*사항",
            r"우대\s*자격",
            r"preferred",
            r"nice.to.have",
            r"plus",
            r"bonus",
        ],
        "responsibilities": [
            r"담당\s*업무",
            r"주요\s*업무",
            r"하는\s*일",
            r"업무\s*내용",
            r"responsibilities",
            r"duties",
            r"role",
        ],
        "tech_stack": [
            r"기술\s*스택",
            r"사용\s*기술",
            r"필수\s*기술",
            r"tech",
            r"tools",
            r"stack",
        ],
        "culture": [
            r"조직\s*문화",
            r"기업\s*문화",
            r"근무\s*환경",
            r"복지",
            r"culture",
            r"benefits",
        ],
    }

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 섹션 헤더 감지
        detected_section = None
        for section_key, patterns in section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    detected_section = section_key
                    break
            if detected_section:
                break

        if detected_section:
            current_section = detected_section
            continue

        # 현재 섹션에 내용 추가
        if current_section and line.startswith(("-", "•", "·", "–", "*", "○", "▶")):
            content = re.sub(r"^[-•·–*○▶\s]+", "", line).strip()
            if content and len(content) > 2:
                if current_section == "culture":
                    sections["culture_keywords"].append(content)
                else:
                    sections[current_section].append(content)

    # 기술스택이 비어있으면 텍스트에서 추출
    if not sections["tech_stack"]:
        sections["tech_stack"] = _extract_tech_keywords(text)

    return sections


def _empty_jd_analysis() -> Dict[str, Any]:
    """빈 JD 분석 결과를 반환합니다."""
    return {
        "required_qualifications": [],
        "preferred_qualifications": [],
        "responsibilities": [],
        "tech_stack": [],
        "culture_keywords": [],
    }


def _extract_tech_keywords(text: str) -> List[str]:
    """텍스트에서 기술 키워드를 추출합니다."""
    tech_patterns = [
        r"Python",
        r"Java(?:Script)?",
        r"TypeScript",
        r"React",
        r"Vue",
        r"Angular",
        r"Node\.js",
        r"Spring",
        r"Django",
        r"Flask",
        r"FastAPI",
        r"SQL",
        r"MySQL",
        r"PostgreSQL",
        r"MongoDB",
        r"Redis",
        r"AWS",
        r"GCP",
        r"Azure",
        r"Docker",
        r"Kubernetes",
        r"Git",
        r"Jenkins",
        r"CI/CD",
        r"Linux",
        r"Machine\s*Learning",
        r"Deep\s*Learning",
        r"TensorFlow",
        r"PyTorch",
        r"Figma",
        r"Sketch",
        r"Adobe\s*\w+",
        r"Excel",
        r"PowerPoint",
        r"Tableau",
        r"Power\s*BI",
    ]

    found = []
    for pattern in tech_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                found.append(match.group())

    return list(set(found))


def generate_questions_from_jd(jd_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    JD 분석 결과를 기반으로 예상 자소서 문항을 생성합니다.

    Returns:
        List of dicts with keys: question_text, char_limit, detected_type
    """
    questions = []

    # 자격요건 → 직무역량 질문
    for i, qual in enumerate(jd_analysis.get("required_qualifications", [])[:2]):
        qual_short = qual[:30] + "..." if len(qual) > 30 else qual
        questions.append(
            {
                "question_text": f"지원 직무의 필수 역량({qual_short})을 어떻게 갖추셨나요?",
                "char_limit": 1000,
                "detected_type": "TYPE_B",
            }
        )

    # 담당업무 → 경험 질문
    for i, resp in enumerate(jd_analysis.get("responsibilities", [])[:2]):
        resp_short = resp[:30] + "..." if len(resp) > 30 else resp
        questions.append(
            {
                "question_text": f"유사한 업무({resp_short})를 수행한 경험을 설명해주세요.",
                "char_limit": 1000,
                "detected_type": "TYPE_B",
            }
        )

    # 기술스택 → 기술 경험 질문
    tech_stack = jd_analysis.get("tech_stack", [])
    if tech_stack:
        tech_str = ", ".join(tech_stack[:3])
        questions.append(
            {
                "question_text": f"언급된 기술({tech_str}) 활용 경험과 성과를 말씀해주세요.",
                "char_limit": 1000,
                "detected_type": "TYPE_B",
            }
        )

    # 우대사항 → 성장 경험 질문
    for i, pref in enumerate(jd_analysis.get("preferred_qualifications", [])[:1]):
        pref_short = pref[:30] + "..." if len(pref) > 30 else pref
        questions.append(
            {
                "question_text": f"우대 조건({pref_short})에 해당하는 성장 경험은?",
                "char_limit": 1000,
                "detected_type": "TYPE_D",
            }
        )

    # 중복 제거 및 최대 5개 반환
    seen = set()
    unique_questions = []
    for q in questions:
        if q["question_text"] not in seen:
            seen.add(q["question_text"])
            unique_questions.append(q)

    return unique_questions[:5]
