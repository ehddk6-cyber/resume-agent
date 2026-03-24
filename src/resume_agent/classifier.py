import re
from typing import List
from .models import QuestionType

QUESTION_TYPE_PATTERNS = {
    QuestionType.TYPE_A: [r"지원동기", r"지원.*이유", r"왜 .*지원", r"직무.*적합", r"관심.*계기"],
    QuestionType.TYPE_B: [r"직무역량", r"역량", r"강점", r"업무 수행.*노력", r"전문성"],
    QuestionType.TYPE_C: [r"협업", r"협력", r"갈등", r"소통", r"의사소통", r"팀워크"],
    QuestionType.TYPE_D: [r"성장", r"배운 점", r"자기개발", r"학습", r"개선", r"보완"],
    QuestionType.TYPE_E: [r"입사 후", r"포부", r"기여", r"발전 방향", r"향후 계획"],
    QuestionType.TYPE_F: [r"원칙", r"기준", r"신뢰", r"책임감", r"약속"],
    QuestionType.TYPE_G: [r"실패", r"어려운 문제", r"극복", r"위기", r"재발 방지"],
    QuestionType.TYPE_H: [r"고객", r"민원", r"응대", r"만족", r"보호자", r"서비스"],
    QuestionType.TYPE_I: [r"우선순위", r"압박", r"판단", r"시간", r"제한된 자원", r"협상"],
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
}

STOPWORDS = {
    "자기소개서", "기술", "주십시오", "무엇", "통해", "본인", 
    "지원", "직무", "경험", "입사", "이후", "관련",
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
}

MARKETING_PATTERNS = [
    "링커리어 자소서 만능검색기",
    "더 많은 최신 합격 자소서",
    "문항별 예시는",
    "AI 개요",
]

def classify_question(text: str) -> QuestionType:
    normalized = text.strip()
    for question_type, patterns in QUESTION_TYPE_PATTERNS.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            return question_type
    return QuestionType.TYPE_B

def extract_question_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z가-힣]{2,}", text)
    seen: List[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token not in seen:
            seen.append(token)
    return seen[:8]
