"""
회사 분석 모듈 - linkareer 합격 데이터 기반 회사/직무 분석 및 맞춤형 전략 수립
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from collections import Counter

from .models import (
    ApplicationProject,
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
        "상황",
        "과제",
        "행동",
        "결과",
        "문제",
        "해결",
        "개선",
        "맡아",
        "진행",
        "수행",
        "달성",
        "완료",
    ],
    SuccessPattern.QUANTIFIED_RESULT: [
        "%",
        "배",
        "건",
        "명",
        "억",
        "만원",
        "개",
        "시간",
        "일",
        "증가",
        "감소",
        "향상",
        "달성",
        "기록",
    ],
    SuccessPattern.PROBLEM_SOLVING: [
        "문제",
        "어려움",
        "갈등",
        "위기",
        "실패",
        "극복",
        "해결",
        "개선",
        "대응",
        "처치",
        "수습",
    ],
    SuccessPattern.COLLABORATION: [
        "팀",
        "협업",
        "소통",
        "조율",
        "합의",
        "협력",
        "공동",
        "함께",
        "조원",
        "팀원",
        "부서",
    ],
    SuccessPattern.GROWTH_STORY: [
        "성장",
        "배움",
        "학습",
        "발전",
        "변화",
        "개선",
        "깨달음",
        "이전",
        "이후",
        "처음",
        "지금",
    ],
    SuccessPattern.CUSTOMER_FOCUS: [
        "고객",
        "민원",
        "응대",
        "서비스",
        "만족",
        "불편",
        "편의",
        "이용객",
        "사용자",
        "수요자",
    ],
    SuccessPattern.INNOVATION: [
        "혁신",
        "개선",
        "제안",
        "도입",
        "변화",
        "새로운",
        "창의",
        "아이디어",
        "시스템",
        "자동화",
    ],
    SuccessPattern.ETHICS: [
        "정직",
        "윤리",
        "청렴",
        "투명",
        "공정",
        "원칙",
        "규정",
        "준수",
        "책임",
        "성실",
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
        relevant_cases = self._select_relevant_cases(company_name, job_title)
        success_patterns = self._analyze_success_patterns(company_name, job_title)
        success_case_stats = self._summarize_success_case_stats(
            company_name, job_title, relevant_cases
        )
        discouraged_phrases = self._extract_discouraged_phrases(relevant_cases)

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
            success_case_stats=success_case_stats,
            similar_case_titles=[case.title for case in relevant_cases[:5]],
            discouraged_phrases=discouraged_phrases,
            role_industry_strategy=build_role_industry_strategy(
                company_type=detected_type,
                industry=self._detect_industry(all_text),
                job_title=job_title,
                question_types=[
                    case.question_type.value
                    for case in self.success_cases
                    if case.company_name == company_name and case.question_type
                ],
                core_values=core_values,
                preferred_evidence_types=preferred_evidence,
                interview_style=interview_style.value,
            ),
        )

    def _normalize_match_text(self, text: str) -> str:
        return re.sub(r"[\s\(\)\[\]·,./_-]+", "", (text or "").lower())

    def _company_aliases(self, company_name: str) -> set[str]:
        normalized = self._normalize_match_text(company_name)
        aliases = {normalized} if normalized else set()

        if any(token in normalized for token in ["새마을금고", "mg"]):
            aliases.update({"새마을금고", "mg", "상호금융", "지역금융"})
        if any(token in normalized for token in ["농축협", "농협", "축협"]):
            aliases.update(
                {"농축협", "농협", "축협", "협동조합", "상호금융", "지역금융"}
            )
        if "신협" in normalized:
            aliases.update({"신협", "협동조합", "상호금융", "지역금융"})
        return {alias for alias in aliases if alias}

    def _select_relevant_cases(
        self, company_name: str, job_title: str
    ) -> List[SuccessCase]:
        if not self.success_cases:
            return []

        company_aliases = self._company_aliases(company_name)
        normalized_job = self._normalize_match_text(job_title)
        relevant_cases: List[SuccessCase] = []

        for case in self.success_cases:
            case_company = self._normalize_match_text(case.company_name)
            case_job = self._normalize_match_text(case.job_title)
            company_match = bool(
                company_aliases
                and any(alias and alias in case_company for alias in company_aliases)
            )
            job_match = bool(normalized_job and normalized_job in case_job)
            if company_match or job_match:
                relevant_cases.append(case)

        if not relevant_cases:
            return self.success_cases[:20]
        return relevant_cases

    def extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 핵심 키워드 추출"""
        # 불용어 제거
        stopwords = {
            "및",
            "등",
            "또한",
            "그리고",
            "하지만",
            "그러나",
            "때문에",
            "위해",
            "통해",
            "대한",
            "있는",
            "하는",
            "되는",
            "된",
            "할",
            "수",
            "것",
            "이",
            "그",
            "저",
            "우리",
            "여러",
            "다양한",
        }

        # 한글 2글자 이상 단어 추출
        words = re.findall(r"[가-힣]{2,}", text)

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
        base_style = COMPANY_INTERVIEW_STYLES.get(company_type, InterviewStyle.FORMAL)

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
        relevant_cases = self._select_relevant_cases(company_name, job_title)

        # 패턴 빈도 계산 (detected_patterns가 없으면 텍스트에서 직접 감지)
        pattern_counter = Counter()
        for case in relevant_cases:
            patterns = case.detected_patterns
            if not patterns and case.answer_text:
                # detected_patterns가 비어있으면 텍스트에서 키워드 매칭으로 감지
                patterns = self._detect_patterns_from_text(case.answer_text)
            for pattern in patterns:
                pattern_counter[pattern] += 1

        if not pattern_counter:
            # 패턴이 전혀 감지되지 않으면 기본값 반환
            return [
                SuccessPattern.STAR_STRUCTURE,
                SuccessPattern.QUANTIFIED_RESULT,
            ]

        # 상위 패턴 반환
        return [pattern for pattern, _ in pattern_counter.most_common(5)]

    def _summarize_success_case_stats(
        self,
        company_name: str,
        job_title: str,
        relevant_cases: List[SuccessCase],
    ) -> Dict[str, Any]:
        if not relevant_cases:
            return {
                "match_case_count": 0,
                "exact_company_match_count": 0,
                "job_match_count": 0,
                "pattern_distribution": {},
                "recommended_writing_focus": [],
            }

        company_aliases = self._company_aliases(company_name)
        normalized_job = self._normalize_match_text(job_title)
        exact_company_matches = 0
        job_matches = 0
        pattern_counter: Counter[str] = Counter()

        for case in relevant_cases:
            case_company = self._normalize_match_text(case.company_name)
            case_job = self._normalize_match_text(case.job_title)
            if company_aliases and any(alias == case_company for alias in company_aliases):
                exact_company_matches += 1
            if normalized_job and normalized_job and normalized_job in case_job:
                job_matches += 1
            patterns = case.detected_patterns or self._detect_patterns_from_text(
                case.answer_text
            )
            for pattern in patterns:
                pattern_counter[pattern.value] += 1

        total = len(relevant_cases)

        def _ratio(pattern_name: SuccessPattern) -> float:
            return round(pattern_counter.get(pattern_name.value, 0) / total, 3)

        recommended_focus: List[str] = []
        if _ratio(SuccessPattern.QUANTIFIED_RESULT) >= 0.35:
            recommended_focus.append("정량 결과를 포함한 문장을 우선 배치")
        if _ratio(SuccessPattern.STAR_STRUCTURE) >= 0.35:
            recommended_focus.append("상황-행동-결과가 분리된 STAR 구조 유지")
        if _ratio(SuccessPattern.CUSTOMER_FOCUS) >= 0.3:
            recommended_focus.append("고객/이용자 관점의 가치 연결 강조")
        if _ratio(SuccessPattern.PROBLEM_SOLVING) >= 0.3:
            recommended_focus.append("문제 원인과 해결 판단 기준을 구체화")
        if _ratio(SuccessPattern.COLLABORATION) >= 0.3:
            recommended_focus.append("협업 시 개인 판단과 조율 역할을 분리해 설명")

        return {
            "match_case_count": total,
            "exact_company_match_count": exact_company_matches,
            "job_match_count": job_matches,
            "pattern_distribution": dict(pattern_counter.most_common(6)),
            "quantified_result_rate": _ratio(SuccessPattern.QUANTIFIED_RESULT),
            "star_structure_rate": _ratio(SuccessPattern.STAR_STRUCTURE),
            "customer_focus_rate": _ratio(SuccessPattern.CUSTOMER_FOCUS),
            "problem_solving_rate": _ratio(SuccessPattern.PROBLEM_SOLVING),
            "collaboration_rate": _ratio(SuccessPattern.COLLABORATION),
            "recommended_writing_focus": recommended_focus[:4],
        }

    def _extract_discouraged_phrases(
        self, relevant_cases: List[SuccessCase], limit: int = 5
    ) -> List[str]:
        if not relevant_cases:
            return []

        sentence_counter: Counter[str] = Counter()
        for case in relevant_cases:
            for raw_sentence in re.split(r"[.!?\n]+", case.answer_text or ""):
                sentence = re.sub(r"\s+", " ", raw_sentence).strip()
                if len(sentence) < 8 or len(sentence) > 42:
                    continue
                if not re.search(r"[가-힣A-Za-z]", sentence):
                    continue
                sentence_counter[sentence] += 1

        repeated = [
            sentence
            for sentence, count in sentence_counter.most_common()
            if count >= 2
            and any(
                keyword in sentence
                for keyword in ["기여", "성장", "노력", "역량", "최선을 다", "배웠"]
            )
        ]
        return repeated[:limit]

    def _detect_patterns_from_text(self, text: str) -> List[SuccessPattern]:
        """텍스트에서 키워드 매칭으로 성공 패턴 감지 (폴백용)"""
        detected: List[SuccessPattern] = []
        for pattern, keywords in SUCCESS_PATTERN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches >= 2:
                detected.append(pattern)
        return detected

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


def build_role_industry_strategy(
    company_type: str,
    industry: str,
    job_title: str = "",
    question_types: Optional[List[str]] = None,
    core_values: Optional[List[str]] = None,
    preferred_evidence_types: Optional[List[str]] = None,
    interview_style: str = "",
    source_grading: Optional[Dict[str, Any]] = None,
    question_map: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """직무·업종 맥락을 writer/interview 프롬프트에서 재사용할 전략 팩 생성"""
    question_types = question_types or []
    core_values = core_values or []
    preferred_evidence_types = preferred_evidence_types or []
    source_grading = source_grading or {}
    question_map = question_map or []

    evidence_priority = _dedupe(
        preferred_evidence_types
        + _strategy_evidence_by_company_type(company_type)
        + _strategy_evidence_by_job(job_title)
    )
    tone_rules = _dedupe(
        [
            COMPANY_TONE_GUIDES.get(company_type, "담백하고 근거 중심으로 답변합니다."),
            f"{industry} 산업 맥락을 과장 없이 연결합니다." if industry else "",
            f"{job_title} 직무에서 바로 쓰일 행동/성과 중심으로 정리합니다."
            if job_title
            else "",
        ]
    )
    banned_patterns = _dedupe(
        _strategy_banned_patterns(company_type, industry, question_types)
    )
    interview_pressure_themes = _dedupe(
        _strategy_pressure_themes(
            company_type=company_type,
            industry=industry,
            question_types=question_types,
            interview_style=interview_style,
            source_grading=source_grading,
        )
    )
    writer_focus = _dedupe(
        [
            "지원동기와 직무 적합성을 사용자 경험으로 연결한다.",
            "문항별로 한 경험의 역할·행동·성과를 분리해 제시한다.",
            "입사 후 포부는 실행 가능한 첫 기여 단위까지 내려쓴다.",
        ]
        + [f"{value} 가치와 맞닿는 행동 근거를 포함한다." for value in core_values[:3]]
    )
    interview_focus = _dedupe(
        [
            "수치/기준/비교 근거를 30초 안에 다시 설명할 수 있게 준비한다.",
            "팀 성과와 개인 기여를 구분해서 답한다.",
            "단일 출처 정보는 확정 표현 대신 검증 예정 표현으로 낮춘다.",
        ]
        + [
            f"{theme} 관점의 압박 질문을 대비한다."
            for theme in interview_pressure_themes[:3]
        ]
    )
    committee_personas = _build_committee_personas(
        company_type=company_type,
        industry=industry,
        job_title=job_title,
        interview_style=interview_style,
        pressure_themes=interview_pressure_themes,
    )

    return {
        "target_role": job_title or "일반 직무",
        "target_industry": industry or "일반",
        "company_type": company_type or "일반",
        "question_types": question_types[:6],
        "writer_focus": writer_focus[:6],
        "interview_focus": interview_focus[:6],
        "evidence_priority": evidence_priority[:6],
        "tone_rules": tone_rules[:4],
        "banned_patterns": banned_patterns[:6],
        "interview_pressure_themes": interview_pressure_themes[:6],
        "committee_personas": committee_personas,
        "single_source_risks": [
            item["area"]
            for item in source_grading.get("cross_check", {}).get("key_areas", [])
            if item.get("status") == "single_source"
        ][:4],
        "question_map_signals": [
            item.get("recommended_focus")
            for item in question_map
            if item.get("recommended_focus")
        ][:4],
    }


def build_role_industry_strategy_from_project(
    project: ApplicationProject,
    company_analysis: CompanyAnalysis,
    question_map: Optional[List[Dict[str, Any]]] = None,
    source_grading: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    question_types = [
        question.detected_type.value
        for question in project.questions
        if getattr(question, "detected_type", None)
    ]
    return build_role_industry_strategy(
        company_type=company_analysis.company_type,
        industry=company_analysis.industry,
        job_title=project.job_title,
        question_types=question_types,
        core_values=company_analysis.core_values,
        preferred_evidence_types=company_analysis.preferred_evidence_types,
        interview_style=company_analysis.interview_style.value,
        source_grading=source_grading,
        question_map=question_map,
    )


def _strategy_evidence_by_company_type(company_type: str) -> List[str]:
    mapping = {
        "공공": ["정확성", "규정 준수", "민원/서비스 품질"],
        "공기업": ["공익성", "안정적 운영", "협업 정확성"],
        "대기업": ["정량 성과", "프로세스 개선", "조직 적합성"],
        "중견": ["실무 기여", "멀티태스킹", "빠른 적응"],
        "스타트업": ["실행 속도", "문제해결", "자기주도성"],
    }
    return mapping.get(company_type, ["정량 성과", "직무 연관 행동"])


def _strategy_evidence_by_job(job_title: str) -> List[str]:
    title = job_title.lower()
    if any(token in title for token in ["데이터", "분석", "analytics"]):
        return ["지표 해석", "SQL/도구 활용", "의사결정 지원"]
    if any(token in title for token in ["영업", "마케팅", "세일즈"]):
        return ["고객 반응", "성과 전환", "관계 구축"]
    if any(token in title for token in ["행정", "사무", "운영"]):
        return ["정확한 처리", "문서/프로세스 관리", "민원 대응"]
    return []


def _strategy_banned_patterns(
    company_type: str,
    industry: str,
    question_types: List[str],
) -> List[str]:
    banned = [
        "검증 불가 수치 확대",
        "회사 정보 복붙형 지원동기",
        "팀 성과를 개인 성과처럼 포장",
    ]
    if company_type in {"공공", "공기업"}:
        banned.append("사명감만 강조하고 실행 근거가 없는 표현")
    if industry == "IT":
        banned.append("기술 용어만 나열하고 실제 문제 해결 맥락이 없는 표현")
    if "TYPE_E" in question_types:
        banned.append("입사 후 포부를 추상적 성장 서사로만 마무리하는 표현")
    return banned


def _strategy_pressure_themes(
    company_type: str,
    industry: str,
    question_types: List[str],
    interview_style: str,
    source_grading: Dict[str, Any],
) -> List[str]:
    themes = ["수치 검증", "개인 기여 검증", "대안 비교"]
    if company_type in {"공공", "공기업"}:
        themes.append("규정 준수와 공익성")
    if industry:
        themes.append(f"{industry} 도메인 이해도")
    if interview_style == InterviewStyle.TECHNICAL.value:
        themes.append("기술 선택 기준")
    if "TYPE_A" in question_types:
        themes.append("지원동기 진정성")
    if "TYPE_E" in question_types:
        themes.append("입사 후 90일 실행계획")
    if source_grading.get("cross_check", {}).get("single_source_area_count", 0) > 0:
        themes.append("단일 출처 주장 방어")
    return themes


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _build_committee_personas(
    company_type: str,
    industry: str,
    job_title: str,
    interview_style: str,
    pressure_themes: List[str],
) -> List[Dict[str, Any]]:
    base_personas = [
        {
            "id": "chair",
            "name": "위원장",
            "role": "전체 논리와 답변 일관성 점검",
            "focus": ["지원동기 진정성", "논리 일관성", "직무 적합성"],
            "tone": "정중하지만 냉정함",
        },
        {
            "id": "domain",
            "name": "실무위원",
            "role": f"{job_title or industry or '직무'} 실무 적합성 검증",
            "focus": pressure_themes[:3] or ["직무 이해도", "실행 경험", "성과 근거"],
            "tone": "구체 사례를 집요하게 확인함",
        },
        {
            "id": "risk",
            "name": "리스크위원",
            "role": "과장, 단일 출처 주장, 실패 대응 검증",
            "focus": ["개인 기여 검증", "대안 비교", "실패 복구"],
            "tone": "반례와 허점을 먼저 찾음",
        },
    ]

    if company_type in {"공공", "공기업"}:
        base_personas.append(
            {
                "id": "public_value",
                "name": "공공가치위원",
                "role": "공익성, 규정 준수, 민원/서비스 품질 검증",
                "focus": ["공익성", "규정 준수", "서비스 품질"],
                "tone": "원칙과 책임을 강조함",
            }
        )
    elif company_type == "스타트업":
        base_personas.append(
            {
                "id": "execution",
                "name": "실행위원",
                "role": "짧은 시간 내 실행력과 우선순위 판단 검증",
                "focus": ["실행 속도", "우선순위", "자기주도성"],
                "tone": "직설적이고 빠른 판단을 요구함",
            }
        )
    else:
        base_personas.append(
            {
                "id": "culture",
                "name": "조직적합성위원",
                "role": "협업 방식과 조직 적합성 검증",
                "focus": ["협업 방식", "조직 적응", "커뮤니케이션"],
                "tone": "차분하지만 비교 질문이 많음",
            }
        )

    if interview_style == InterviewStyle.TECHNICAL.value:
        base_personas[1]["name"] = "기술위원"
        base_personas[1]["focus"] = _dedupe(
            base_personas[1]["focus"] + ["기술 선택 기준"]
        )

    return base_personas
