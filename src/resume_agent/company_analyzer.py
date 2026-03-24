"""
회사 분석 모듈 - linkareer 합격 데이터 기반 회사/직무 분석 및 맞춤형 전략 수립
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from collections import Counter

from .models import (
    CompanyAnalysis,
    InterviewStyle,
    SuccessPattern,
    QuestionType,
    SuccessCase,
)


# 기업 유형별 톤 가이드
COMPANY_TONE_GUIDES = {
    "대기업": "구조화되고 체계적인 표현. 조직 적합성 강조. 안정성과 성장 가능성 균형.",
    "중견": "실무 기여도 강조. 다기능성과 확장성 표현. 구체적 성과 중심.",
    "스타트업": "실행력과 자기주도성 강조. 담백하고 직접적인 톤. 문제해결 역량 중심.",
    "공공": "공익과 공정성 강조. 규정 준수와 정확성 표현. 단정하고 신뢰감 있는 톤.",
    "공기업": "공익 가치와 사회적 책임 강조. 안정성과 전문성 균형. 책임감 있는 표현.",
}

# 기업 유형별 면접 스타일
COMPANY_INTERVIEW_STYLES = {
    "대기업": InterviewStyle.FORMAL,
    "중견": InterviewStyle.BEHAVIORAL,
    "스타트업": InterviewStyle.CASUAL,
    "공공": InterviewStyle.FORMAL,
    "공기업": InterviewStyle.FORMAL,
}

# 성공 패턴 키워드 매핑
SUCCESS_PATTERN_KEYWORDS = {
    SuccessPattern.STAR_STRUCTURE: [
        "상황", "과제", "행동", "결과", "문제", "해결", "개선",
        "맡아", "진행", "수행", "달성", "완료",
    ],
    SuccessPattern.QUANTIFIED_RESULT: [
        "%", "배", "건", "명", "억", "만원", "개", "시간", "일",
        "증가", "감소", "향상", "달성", "기록",
    ],
    SuccessPattern.PROBLEM_SOLVING: [
        "문제", "어려움", "갈등", "위기", "실패", "극복", "해결",
        "개선", "대응", "처치", "수습",
    ],
    SuccessPattern.COLLABORATION: [
        "팀", "협업", "소통", "조율", "합의", "협력", "공동",
        "함께", "조원", "팀원", "부서",
    ],
    SuccessPattern.GROWTH_STORY: [
        "성장", "배움", "학습", "발전", "변화", "개선", "깨달음",
        "이전", "이후", "처음", "지금",
    ],
    SuccessPattern.CUSTOMER_FOCUS: [
        "고객", "민원", "응대", "서비스", "만족", "불편", "편의",
        "이용객", "사용자", "수요자",
    ],
    SuccessPattern.INNOVATION: [
        "혁신", "개선", "제안", "도입", "변화", "새로운", "창의",
        "아이디어", "시스템", "자동화",
    ],
    SuccessPattern.ETHICS: [
        "정직", "윤리", "청렴", "투명", "공정", "원칙", "규정",
        "준수", "책임", "성실",
    ],
}

# 질문 유형별 성공 패턴 매핑
QUESTION_TYPE_PATTERNS = {
    QuestionType.TYPE_A: [  # 지원동기
        SuccessPattern.GROWTH_STORY,
        SuccessPattern.CUSTOMER_FOCUS,
    ],
    QuestionType.TYPE_B: [  # 직무역량
        SuccessPattern.STAR_STRUCTURE,
        SuccessPattern.QUANTIFIED_RESULT,
        SuccessPattern.PROBLEM_SOLVING,
    ],
    QuestionType.TYPE_C: [  # 협업/갈등
        SuccessPattern.COLLABORATION,
        SuccessPattern.PROBLEM_SOLVING,
    ],
    QuestionType.TYPE_D: [  # 성장/학습
        SuccessPattern.GROWTH_STORY,
        SuccessPattern.INNOVATION,
    ],
    QuestionType.TYPE_E: [  # 입사 후 포부
        SuccessPattern.CUSTOMER_FOCUS,
        SuccessPattern.INNOVATION,
    ],
    QuestionType.TYPE_F: [  # 가치관
        SuccessPattern.ETHICS,
        SuccessPattern.GROWTH_STORY,
    ],
    QuestionType.TYPE_G: [  # 실패 경험
        SuccessPattern.PROBLEM_SOLVING,
        SuccessPattern.GROWTH_STORY,
    ],
    QuestionType.TYPE_H: [  # 고객 응대
        SuccessPattern.CUSTOMER_FOCUS,
        SuccessPattern.PROBLEM_SOLVING,
    ],
    QuestionType.TYPE_I: [  # 우선순위/압박
        SuccessPattern.PROBLEM_SOLVING,
        SuccessPattern.STAR_STRUCTURE,
    ],
}


class CompanyAnalyzer:
    """회사 분석기 - linkareer 합격 데이터 기반 분석"""

    def __init__(self, success_cases: Optional[List[SuccessCase]] = None):
        self.success_cases = success_cases or []

    def analyze(
        self,
        company_name: str,
        job_title: str = "",
        job_description: str = "",
        company_type: str = "공공",
    ) -> CompanyAnalysis:
        """
        회사 분석 수행

        Args:
            company_name: 회사명
            job_title: 직무명
            job_description: 채용 공고문
            company_type: 기업 유형

        Returns:
            CompanyAnalysis 객체
        """
        # 1. 기업 유형 분석
        detected_type = self._detect_company_type(company_name, company_type)

        # 2. 키워드 추출
        all_text = f"{company_name} {job_title} {job_description}"
        keywords = self.extract_keywords(all_text)

        # 3. 핵심 가치 추출
        core_values = self._extract_core_values(all_text, detected_type)

        # 4. 문화 키워드 추출
        culture_keywords = self._extract_culture_keywords(all_text, detected_type)

        # 5. 면접 스타일 결정
        interview_style = self._determine_interview_style(detected_type, keywords)

        # 6. 성공 패턴 분석 (linkareer 데이터 기반)
        success_patterns = self._analyze_success_patterns(company_name, job_title)

        # 7. 선호 증거 유형 분석
        preferred_evidence = self._analyze_preferred_evidence(detected_type)

        # 8. 톤 가이드 생성
        tone_guide = self._generate_tone_guide(detected_type, keywords)

        return CompanyAnalysis(
            company_name=company_name,
            company_type=detected_type,
            industry=self._detect_industry(all_text),
            core_values=core_values,
            culture_keywords=culture_keywords,
            interview_style=interview_style,
            success_patterns=success_patterns,
            preferred_evidence_types=preferred_evidence,
            tone_guide=tone_guide,
        )

    def extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 핵심 키워드 추출"""
        # 불용어 제거
        stopwords = {
            "및", "등", "또한", "그리고", "하지만", "그러나", "때문에",
            "위해", "통해", "대한", "있는", "하는", "되는", "된", "할",
            "수", "것", "이", "그", "저", "우리", "여러", "다양한",
        }

        # 한글 2글자 이상 단어 추출
        words = re.findall(r'[가-힣]{2,}', text)

        # 불용어 제거 및 빈도 계산
        filtered = [w for w in words if w not in stopwords]
        counter = Counter(filtered)

        # 상위 20개 키워드 반환
        return [word for word, _ in counter.most_common(20)]

    def _detect_company_type(self, company_name: str, default: str) -> str:
        """기업 유형 자동 감지"""
        public_keywords = ["공단", "공사", "공단", "관리공", "진흥원", "연구원"]
        large_keywords = ["그룹", "전자", "자동차", "화학", "건설", "보험", "은행"]
        startup_keywords = ["테크", "랩", "스튜디오", "플랫폼"]

        name_lower = company_name.lower()

        for kw in public_keywords:
            if kw in company_name:
                return "공공"

        for kw in large_keywords:
            if kw in company_name:
                return "대기업"

        for kw in startup_keywords:
            if kw in company_name:
                return "스타트업"

        return default

    def _detect_industry(self, text: str) -> str:
        """산업 분야 감지"""
        industry_keywords = {
            "금융": ["금융", "은행", "보험", "증권", "자산", "투자", "대출", "보증"],
            "IT": ["IT", "소프트웨어", "개발", "시스템", "데이터", "인공지능", "AI"],
            "제조": ["제조", "생산", "공장", "품질", "설비", "엔지니어링"],
            "건설": ["건설", "토목", "건축", "부동산", "주택", "인프라"],
            "공공": ["공공", "정부", "행정", "정책", "복지", "보건"],
            "에너지": ["에너지", "전력", "가스", "발전", "신재생", "원자력"],
            "유통": ["유통", "물류", "판매", "소매", "도매", "상품"],
        }

        for industry, keywords in industry_keywords.items():
            for kw in keywords:
                if kw in text:
                    return industry

        return "일반"

    def _extract_core_values(self, text: str, company_type: str) -> List[str]:
        """핵심 가치 추출"""
        value_keywords = {
            "공정": ["공정", "공평", "투명"],
            "혁신": ["혁신", "창의", "도전", "변화"],
            "상생": ["상생", "협력", "동반성장", "상호"],
            "고객중심": ["고객", "서비스", "이용자", "시민"],
            "안전": ["안전", "보건", "환경", "건강"],
            "전문성": ["전문", "역량", "기술", "지식"],
            "책임": ["책임", "헌신", "성실", "정직"],
            "소통": ["소통", "대화", "경청", "배려"],
        }

        values = []
        for value, keywords in value_keywords.items():
            for kw in keywords:
                if kw in text:
                    values.append(value)
                    break

        # 기업 유형별 기본 가치 추가
        if company_type in ["공공", "공기업"]:
            if "공익" not in values:
                values.append("공익")
            if "책임" not in values:
                values.append("책임")

        return values[:5]  # 최대 5개

    def _extract_culture_keywords(self, text: str, company_type: str) -> List[str]:
        """문화 키워드 추출"""
        culture_patterns = {
            "수평적": ["수평", "자율", "열린", "자유로운"],
            "체계적": ["체계", "시스템", "프로세스", "규정"],
            "도전적": ["도전", "혁신", "창의", "실험"],
            "안정적": ["안정", "장기", "지속", "성장"],
            "협력적": ["협력", "팀워크", "소통", "화합"],
        }

        keywords = []
        for culture, patterns in culture_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    keywords.append(culture)
                    break

        return keywords

    def _determine_interview_style(
        self, company_type: str, keywords: List[str]
    ) -> InterviewStyle:
        """면접 스타일 결정"""
        # 기업 유형 기반
        base_style = COMPANY_INTERVIEW_STYLES.get(
            company_type, InterviewStyle.FORMAL
        )

        # 키워드 기반 조정
        tech_keywords = ["기술", "개발", "엔지니어", "시스템", "IT", "데이터"]
        if any(kw in keywords for kw in tech_keywords):
            return InterviewStyle.TECHNICAL

        behavior_keywords = ["영업", "마케팅", "고객", "서비스", "상담"]
        if any(kw in keywords for kw in behavior_keywords):
            return InterviewStyle.BEHAVIORAL

        return base_style

    def _analyze_success_patterns(
        self, company_name: str, job_title: str
    ) -> List[SuccessPattern]:
        """linkareer 합격 데이터에서 성공 패턴 분석"""
        if not self.success_cases:
            # 데이터가 없는 경우 기업 유형별 기본 패턴 반환
            return [
                SuccessPattern.STAR_STRUCTURE,
                SuccessPattern.QUANTIFIED_RESULT,
            ]

        # 해당 회사/직무의 합격 사례 필터링
        relevant_cases = [
            case
            for case in self.success_cases
            if company_name in case.company_name
            or (job_title and job_title in case.job_title)
        ]

        if not relevant_cases:
            relevant_cases = self.success_cases[:10]  # 샘플링

        # 패턴 빈도 계산
        pattern_counter = Counter()
        for case in relevant_cases:
            for pattern in case.detected_patterns:
                pattern_counter[pattern] += 1

        # 상위 패턴 반환
        return [pattern for pattern, _ in pattern_counter.most_common(5)]

    def _analyze_preferred_evidence(self, company_type: str) -> List[str]:
        """선호 증거 유형 분석"""
        evidence_preferences = {
            "공공": ["정량적 성과", "제도 개선", "고객 만족", "규정 준수"],
            "공기업": ["정량적 성과", "공익 기여", "안전 관리", "서비스 품질"],
            "대기업": ["매출/효율", "프로젝트 성과", "조직 기여", "혁신 사례"],
            "스타트업": ["문제 해결", "빠른 실행", "창의적 접근", "고객 반응"],
        }

        return evidence_preferences.get(
            company_type,
            ["정량적 성과", "문제 해결", "협업 성과"],
        )

    def _generate_tone_guide(self, company_type: str, keywords: List[str]) -> str:
        """톤 가이드 생성"""
        base_guide = COMPANY_TONE_GUIDES.get(
            company_type,
            "명확하고 구체적인 표현. 근거 중심.",
        )

        # 키워드 기반 추가 가이드
        additions = []

        if any(kw in keywords for kw in ["혁신", "창의", "도전"]):
            additions.append("혁신적 사고와 도전 정신을 강조하세요.")

        if any(kw in keywords for kw in ["고객", "시민", "이용자"]):
            additions.append("고객/시민 중심의 관점을 드러내세요.")

        if any(kw in keywords for kw in ["안전", "품질", "보건"]):
            additions.append("안전과 품질에 대한 책임감을 표현하세요.")

        if additions:
            return f"{base_guide}\n\n추가 지침:\n" + "\n".join(additions)

        return base_guide


def analyze_company(
    company_name: str,
    job_title: str = "",
    job_description: str = "",
    company_type: str = "공공",
    success_cases: Optional[List[SuccessCase]] = None,
) -> CompanyAnalysis:
    """회사 분석 편의 함수"""
    analyzer = CompanyAnalyzer(success_cases)
    return analyzer.analyze(company_name, job_title, job_description, company_type)


def extract_keywords(text: str) -> List[str]:
    """키워드 추출 편의 함수"""
    analyzer = CompanyAnalyzer()
    return analyzer.extract_keywords(text)