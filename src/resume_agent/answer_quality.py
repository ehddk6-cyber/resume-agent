"""
답변 품질 평가 모듈 - linkareer 합격 데이터 기반 답변 품질 분석 및 피드백
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

from .models import (
    AnswerQuality,
    Experience,
    QuestionType,
    SuccessPattern,
    CompanyAnalysis,
)
from .company_analyzer import SUCCESS_PATTERN_KEYWORDS


# 클리셰 패턴 (사용 지양)
CLICHE_PATTERNS = [
    "최선을 다하겠습니다",
    "열정적으로 임하겠습니다",
    "팀원들과 소통하며",
    "맡은 바 책임을 다하겠습니다",
    "성실하게 근무하겠습니다",
    "항상 배우는 자세로",
    "도전을 두려워하지 않는",
    "창의적인 사고를 바탕으로",
    "저만의 강점은",
    "어릴 때부터",
    "꿈꿔왔습니다",
]

# 강력한 표현 패턴
STRONG_EXPRESSIONS = [
    "주도적으로",
    "솔선수범하여",
    "개선했습니다",
    "달성했습니다",
    "해결했습니다",
    "도입했습니다",
    "구축했습니다",
    "향상시켰습니다",
    "감소시켰습니다",
    "증가시켰습니다",
]


class AnswerQualityEvaluator:
    """답변 품질 평가기"""

    def __init__(self, company_analysis: Optional[CompanyAnalysis] = None):
        self.company_analysis = company_analysis

    def evaluate(
        self,
        answer: str,
        question: str,
        question_type: QuestionType,
        experience: Optional[Experience] = None,
    ) -> AnswerQuality:
        """
        답변 품질 종합 평가

        Args:
            answer: 답변 텍스트
            question: 질문 텍스트
            question_type: 질문 유형
            experience: 연결된 경험 데이터

        Returns:
            AnswerQuality 객체
        """
        question_id = f"q_{hash(question) % 10000}"

        # 1. 관련성 평가
        relevance_score = self._calculate_relevance(answer, question, question_type)

        # 2. 구체성 평가
        specificity_score = self._calculate_specificity(answer)

        # 3. 방어 가능성 평가
        defensibility_score = self._calculate_defensibility(answer, experience)

        # 4. 독창성 평가
        originality_score = self._calculate_originality(answer)

        # 5. 패턴 감지
        detected_patterns = self._detect_patterns(answer)

        # 6. 종합 점수 계산
        overall_score = self._calculate_overall_score(
            relevance_score,
            specificity_score,
            defensibility_score,
            originality_score,
        )

        # 7. 강점/약점 분석
        strengths, weaknesses = self._analyze_strengths_weaknesses(
            answer, question_type, detected_patterns
        )

        # 8. 개선 제안
        suggestions = self._generate_suggestions(
            answer, question_type, detected_patterns, weaknesses
        )

        return AnswerQuality(
            question_id=question_id,
            answer_text=answer,
            relevance_score=relevance_score,
            specificity_score=specificity_score,
            defensibility_score=defensibility_score,
            originality_score=originality_score,
            overall_score=overall_score,
            detected_patterns=detected_patterns,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _calculate_relevance(
        self, answer: str, question: str, question_type: QuestionType
    ) -> float:
        """질문-답변 관련성 점수 계산"""
        score = 0.5  # 기본 점수

        # 질문 키워드 추출
        question_keywords = set(re.findall(r'[가-힣]{2,}', question))
        answer_keywords = set(re.findall(r'[가-힣]{2,}', answer))

        # 키워드 매칭률
        if question_keywords:
            matches = len(question_keywords & answer_keywords)
            match_ratio = matches / len(question_keywords)
            score += match_ratio * 0.3

        # 질문 유형별 적합성 키워드
        type_keywords = {
            QuestionType.TYPE_A: ["지원", "동기", "관심", "이유", "목표"],
            QuestionType.TYPE_B: ["역량", "경험", "성과", "능력", "스킬"],
            QuestionType.TYPE_C: ["협업", "갈등", "소통", "팀", "조율"],
            QuestionType.TYPE_D: ["성장", "학습", "변화", "개선", "발전"],
            QuestionType.TYPE_E: ["입사", "포부", "계획", "기여", "목표"],
            QuestionType.TYPE_F: ["가치", "원칙", "신념", "윤리", "철학"],
            QuestionType.TYPE_G: ["실패", "좌절", "극복", "교훈", "배움"],
            QuestionType.TYPE_H: ["고객", "서비스", "응대", "만족", "불만"],
            QuestionType.TYPE_I: ["우선순위", "판단", "결정", "기준", "압박"],
        }

        relevant_keywords = type_keywords.get(question_type, [])
        for kw in relevant_keywords:
            if kw in answer:
                score += 0.04

        return min(1.0, score)

    def _calculate_specificity(self, answer: str) -> float:
        """구체성 점수 계산"""
        score = 0.3  # 기본 점수

        # 숫자 포함 여부
        numbers = re.findall(r'\d+', answer)
        if numbers:
            score += min(0.3, len(numbers) * 0.05)

        # 구체적 표현 패턴
        specific_patterns = [
            r'\d+%', r'\d+건', r'\d+명', r'\d+배', r'\d+시간',
            r'\d+개월', r'\d+일', r'\d+원', r'\d+만원',
        ]
        for pattern in specific_patterns:
            if re.search(pattern, answer):
                score += 0.05

        # STAR 구조 키워드
        star_keywords = ["상황", "과제", "행동", "결과", "문제", "해결"]
        star_count = sum(1 for kw in star_keywords if kw in answer)
        score += min(0.2, star_count * 0.03)

        # 문장 길이 (너무 짧으면 감점)
        sentences = re.split(r'[.!?]\s+', answer)
        avg_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
        if avg_length > 50:
            score += 0.1

        return min(1.0, score)

    def _calculate_defensibility(
        self, answer: str, experience: Optional[Experience]
    ) -> float:
        """방어 가능성 점수 계산 (30초 내 방어 가능한지)"""
        score = 0.5  # 기본 점수

        # 개인 기여 명시 여부
        personal_indicators = [
            "저는", "제가", "개인적으로", "담당하여", "주도하여",
            "제안하여", "설계하여", "분석하여",
        ]
        for indicator in personal_indicators:
            if indicator in answer:
                score += 0.05
                break

        # 구체적 행동 서술
        action_verbs = [
            "수행", "진행", "분석", "설계", "구현", "제안", "개선",
            "관리", "운영", "기획", "개발", "구축",
        ]
        action_count = sum(1 for verb in action_verbs if verb in answer)
        score += min(0.2, action_count * 0.04)

        # 결과 명시
        result_indicators = ["결과", "성과", "달성", "완료", "성공", "효과"]
        for indicator in result_indicators:
            if indicator in answer:
                score += 0.05
                break

        # 경험 데이터와의 일치성
        if experience:
            # 경험의 핵심 요소가 답변에 포함되어 있는지 확인
            exp_keywords = set(
                re.findall(
                    r'[가-힣]{2,}',
                    f"{experience.situation} {experience.action} {experience.result}"
                )
            )
            answer_keywords = set(re.findall(r'[가-힣]{2,}', answer))
            if exp_keywords:
                overlap = len(exp_keywords & answer_keywords) / len(exp_keywords)
                score += overlap * 0.2

        return min(1.0, score)

    def _calculate_originality(self, answer: str) -> float:
        """독창성 점수 계산 (클리셰 회피)"""
        score = 0.8  # 기본 점수 (독창적이라고 가정)

        # 클리셰 패턴 검출
        cliche_count = 0
        for cliche in CLICHE_PATTERNS:
            if cliche in answer:
                cliche_count += 1

        # 클리셰 발견 시 감점
        score -= min(0.5, cliche_count * 0.1)

        # 강력한 표현 사용 시 가점
        strong_count = sum(1 for expr in STRONG_EXPRESSIONS if expr in answer)
        score += min(0.2, strong_count * 0.04)

        return max(0.0, min(1.0, score))

    def _detect_patterns(self, answer: str) -> List[SuccessPattern]:
        """답변에서 성공 패턴 감지"""
        detected = []

        for pattern, keywords in SUCCESS_PATTERN_KEYWORDS.items():
            # 키워드 매칭률 계산
            matches = sum(1 for kw in keywords if kw in answer)
            if matches >= 2:  # 2개 이상의 키워드가 매칭되면 해당 패턴으로 판정
                detected.append(pattern)

        return detected

    def _calculate_overall_score(
        self,
        relevance: float,
        specificity: float,
        defensibility: float,
        originality: float,
    ) -> float:
        """종합 점수 계산"""
        # 가중치 적용
        weights = {
            "relevance": 0.3,
            "specificity": 0.25,
            "defensibility": 0.25,
            "originality": 0.2,
        }

        overall = (
            relevance * weights["relevance"]
            + specificity * weights["specificity"]
            + defensibility * weights["defensibility"]
            + originality * weights["originality"]
        )

        return round(overall, 2)

    def _analyze_strengths_weaknesses(
        self,
        answer: str,
        question_type: QuestionType,
        detected_patterns: List[SuccessPattern],
    ) -> Tuple[List[str], List[str]]:
        """강점/약점 분석"""
        strengths = []
        weaknesses = []

        # 강점 체크
        if SuccessPattern.QUANTIFIED_RESULT in detected_patterns:
            strengths.append("정량적 성과가 구체적으로 표현되어 있습니다")

        if SuccessPattern.STAR_STRUCTURE in detected_patterns:
            strengths.append("STAR 구조가 잘 드러나 있습니다")

        if SuccessPattern.PROBLEM_SOLVING in detected_patterns:
            strengths.append("문제 해결 과정이 명확하게 서술되어 있습니다")

        # 숫자 포함 여부
        if re.search(r'\d+', answer):
            strengths.append("구체적인 수치가 포함되어 있습니다")

        # 약점 체크
        if SuccessPattern.QUANTIFIED_RESULT not in detected_patterns:
            weaknesses.append("정량적 성과 표현이 부족합니다")

        # 클리셰 검출
        found_cliches = [c for c in CLICHE_PATTERNS if c in answer]
        if found_cliches:
            weaknesses.append(f"클리셰 표현이 포함되어 있습니다: {found_cliches[0]}")

        # STAR 구조 부족
        star_keywords = ["상황", "과제", "행동", "결과"]
        star_count = sum(1 for kw in star_keywords if kw in answer)
        if star_count < 2:
            weaknesses.append("STAR 구조 요소가 부족합니다")

        return strengths, weaknesses

    def _generate_suggestions(
        self,
        answer: str,
        question_type: QuestionType,
        detected_patterns: List[SuccessPattern],
        weaknesses: List[str],
    ) -> List[str]:
        """개선 제안 생성"""
        suggestions = []

        # 구체성 개선
        if not re.search(r'\d+', answer):
            suggestions.append(
                "구체적인 수치를 추가하세요. 예: '30% 향상', '50건 처리'"
            )

        # STAR 구조 개선
        if SuccessPattern.STAR_STRUCTURE not in detected_patterns:
            suggestions.append(
                "STAR 구조를 명확히 하세요: 상황 → 과제 → 행동 → 결과"
            )

        # 클리셰 제거
        found_cliches = [c for c in CLICHE_PATTERNS if c in answer]
        if found_cliches:
            suggestions.append(
                f"클리셰 표현('{found_cliches[0]}')을 구체적인 표현으로 대체하세요"
            )

        # 질문 유형별 맞춤 제안
        type_suggestions = {
            QuestionType.TYPE_A: "지원동기는 회사와 직무의 접점을 구체적으로 언급하세요",
            QuestionType.TYPE_B: "직무역량은 한 역량당 하나의 경험을 중심으로 서술하세요",
            QuestionType.TYPE_C: "협업 경험은 갈등 원인, 조정 과정, 결과를 분리하여 설명하세요",
            QuestionType.TYPE_D: "성장 경험은 이전 한계 → 개선 행동 → 현재 변화까지 포함하세요",
            QuestionType.TYPE_G: "실패 경험은 자기 책임, 개선 행동, 재발 방지 루틴을 포함하세요",
        }

        if question_type in type_suggestions:
            suggestions.append(type_suggestions[question_type])

        # 기업 유형별 맞춤 제안
        if self.company_analysis:
            if "정량적 성과" in self.company_analysis.preferred_evidence_types:
                if SuccessPattern.QUANTIFIED_RESULT not in detected_patterns:
                    suggestions.append(
                        f"{self.company_analysis.company_type} 기업은 정량적 성과를 중시합니다"
                    )

        return suggestions


def evaluate_answer_quality(
    answer: str,
    question: str,
    question_type: QuestionType,
    experience: Optional[Experience] = None,
    company_analysis: Optional[CompanyAnalysis] = None,
) -> AnswerQuality:
    """답변 품질 평가 편의 함수"""
    evaluator = AnswerQualityEvaluator(company_analysis)
    return evaluator.evaluate(answer, question, question_type, experience)


def calculate_relevance(answer: str, question: str, question_type: QuestionType) -> float:
    """관련성 점수 계산 편의 함수"""
    evaluator = AnswerQualityEvaluator()
    return evaluator._calculate_relevance(answer, question, question_type)


def calculate_specificity(answer: str) -> float:
    """구체성 점수 계산 편의 함수"""
    evaluator = AnswerQualityEvaluator()
    return evaluator._calculate_specificity(answer)


def calculate_defensibility(answer: str, experience: Optional[Experience] = None) -> float:
    """방어 가능성 점수 계산 편의 함수"""
    evaluator = AnswerQualityEvaluator()
    return evaluator._calculate_defensibility(answer, experience)


def calculate_originality(answer: str) -> float:
    """독창성 점수 계산 편의 함수"""
    evaluator = AnswerQualityEvaluator()
    return evaluator._calculate_originality(answer)