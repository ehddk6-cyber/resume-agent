"""
면접 방어 시뮬레이션 모듈 - 꼬리질문 생성 및 방어 전략 검증
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

from .models import (
    DefenseSimulation,
    QuestionType,
    CompanyAnalysis,
    InterviewStyle,
    Experience,
)
from .company_analyzer import QUESTION_TYPE_PATTERNS, SUCCESS_PATTERN_KEYWORDS


# 질문 유형별 꼬리질문 패턴
FOLLOW_UP_PATTERNS = {
    QuestionType.TYPE_A: [  # 지원동기
        "다른 회사가 아닌 왜 우리 회사인가요?",
        "지원동기에서 언급한 부분을 구체적으로 설명해주세요.",
        "입사 후 가장 먼저 기여하고 싶은 부분은 무엇인가요?",
    ],
    QuestionType.TYPE_B: [  # 직무역량
        "그 경험에서 본인만의 차별화된 역할은 무엇이었나요?",
        "그 역량을 어떻게 수치로 증명할 수 있나요?",
        "비슷한 상황에서 다른 방법을 시도해본 적이 있나요?",
    ],
    QuestionType.TYPE_C: [  # 협업/갈등
        "갈등이 더 심해졌다면 어떻게 대응했을 것인가요?",
        "상대방이 계속 협조하지 않았다면 어떻게 했을까요?",
        "그 경험 이후 협업 방식이 어떻게 달라졌나요?",
    ],
    QuestionType.TYPE_D: [  # 성장/학습
        "그 한계를 인식하게 된 계기는 무엇이었나요?",
        "개선 과정에서 가장 힘들었던 부분은 무엇인가요?",
        "현재는 그 부분이 어떻게 달라졌나요?",
    ],
    QuestionType.TYPE_G: [  # 실패 경험
        "그 실패의 근본 원인은 무엇이라고 생각하나요?",
        "재발 방지를 위해 구체적으로 어떤 시스템을 만들었나요?",
        "비슷한 상황이 다시 온다면 어떻게 대처할 건가요?",
    ],
    QuestionType.TYPE_H: [  # 고객 응대
        "고객이 계속 불만을 제기한다면 어떻게 하시겠어요?",
        "그 경험이 고객 서비스 철학에 어떤 영향을 줬나요?",
        "동료가 비슷한 상황에서 어려움을 겪는다면 어떻게 도와주겠어요?",
    ],
}

# 면접 스타일별 공격적 질문 패턴
AGGRESSIVE_PATTERNS = {
    InterviewStyle.FORMAL: [
        "그 부분에 대해 더 구체적으로 설명해주시겠어요?",
        "그 성과가 본인의 기여 때문이라고 확신하시나요?",
        "다른 관점에서 보면 어떻게 평가하시겠어요?",
    ],
    InterviewStyle.CASUAL: [
        "솔직히 말해서 그때 좀 힘들지 않았어요?",
        "그냥 넘어갈 수도 있었을 텐데 왜 그렇게까지 했어요?",
        "다시 돌아간다면 같은 선택을 할까요?",
    ],
    InterviewStyle.TECHNICAL: [
        "그 기술을 선택한 기준은 무엇이었나요?",
        "다른 대안과 비교했을 때 어떤 장점이 있었나요?",
        "해당 기술의 한계는 어떻게 극복했나요?",
    ],
    InterviewStyle.BEHAVIORAL: [
        "그 상황에서 가장 어려웠던 판단은 무엇이었나요?",
        "팀원들이 반대 의견을 냈다면 어떻게 설득했을까요?",
        "그 경험이 리더십에 어떤 교훈을 줬나요?",
    ],
}


class DefenseSimulator:
    """면접 방어 시뮬레이터"""

    def __init__(self, company_analysis: Optional[CompanyAnalysis] = None):
        self.company_analysis = company_analysis

    def simulate(
        self,
        primary_question: str,
        answer: str,
        question_type: QuestionType,
        experiences: Optional[List[Experience]] = None,
    ) -> DefenseSimulation:
        """
        면접 방어 시뮬레이션 수행

        Args:
            primary_question: 주 질문
            answer: 답변 텍스트
            question_type: 질문 유형
            experiences: 관련 경험 데이터

        Returns:
            DefenseSimulation 객체
        """
        # 1. 취약점 분석
        risk_areas = self._identify_risk_areas(answer, question_type)

        # 2. 꼬리질문 생성
        follow_up_questions = self._generate_follow_up_questions(
            answer, question_type, risk_areas
        )

        # 3. 방어 포인트 제안
        defense_points = self._suggest_defense_points(answer, risk_areas)

        # 4. 개선 제안
        improvement_suggestions = self._generate_improvement_suggestions(
            answer, risk_areas, question_type
        )

        return DefenseSimulation(
            primary_question=primary_question,
            simulated_answer=answer,
            follow_up_questions=follow_up_questions,
            defense_points=defense_points,
            risk_areas=risk_areas,
            improvement_suggestions=improvement_suggestions,
        )

    def _identify_risk_areas(
        self, answer: str, question_type: QuestionType
    ) -> List[str]:
        """답변의 취약점 식별"""
        risks = []

        # 1. 구체성 부족
        if not re.search(r'\d+', answer):
            risks.append("구체적인 수치가 없어 증빙이 어려움")

        # 2. 개인 기여 불명확
        team_indicators = ["팀이", "함께", "공동으로", "협력하여"]
        personal_indicators = ["저는", "제가", "개인적으로"]

        has_team = any(ind in answer for ind in team_indicators)
        has_personal = any(ind in answer for ind in personal_indicators)

        if has_team and not has_personal:
            risks.append("팀 성과와 개인 기여가 구분되지 않음")

        # 3. STAR 구조 부족
        star_keywords = ["상황", "과제", "행동", "결과"]
        star_count = sum(1 for kw in star_keywords if kw in answer)
        if star_count < 3:
            risks.append("STAR 구조가 불완전하여 꼬리질문에 취약")

        # 4. 과도한 일반화
        vague_patterns = ["항상", "모두", "완벽하게", "절대적으로"]
        if any(pattern in answer for pattern in vague_patterns):
            risks.append("과도한 일반화 표현 사용")

        # 5. 수비적 표현 부족
        defensive_indicators = ["다만", "물론", "다만", "한편으로는"]
        if not any(ind in answer for ind in defensive_indicators):
            risks.append("균형 잡힌 시각 표현 부족")

        return risks

    def _generate_follow_up_questions(
        self,
        answer: str,
        question_type: QuestionType,
        risk_areas: List[str],
    ) -> List[str]:
        """꼬리질문 생성"""
        questions = []

        # 1. 질문 유형별 기본 꼬리질문
        type_questions = FOLLOW_UP_PATTERNS.get(question_type, [])
        if type_questions:
            questions.extend(type_questions[:2])

        # 2. 면접 스타일별 공격적 질문
        if self.company_analysis:
            style = self.company_analysis.interview_style
            aggressive_questions = AGGRESSIVE_PATTERNS.get(style, [])
            if aggressive_questions:
                questions.append(aggressive_questions[0])

        # 3. 취약점 기반 꼬리질문
        if "구체적인 수치가 없어 증빙이 어려움" in risk_areas:
            questions.append("그 성과를 수치로 표현한다면 어떻게 설명하시겠어요?")

        if "팀 성과와 개인 기여가 구분되지 않음" in risk_areas:
            questions.append("팀 프로젝트에서 본인만의 기여도를 퍼센트로 표현한다면?")

        if "STAR 구조가 불완전하여 꼬리질문에 취약" in risk_areas:
            questions.append("그 상황에서 가장 먼저 한 행동은 무엇이었나요?")

        # 4. 답변 내용 기반 꼬리질문
        # 수치가 있으면 근거 질문
        numbers = re.findall(r'(\d+)%?', answer)
        if numbers:
            questions.append(f"{numbers[0]}이라는 수치는 어떻게 측정하셨나요?")

        # 중복 제거 및 최대 5개 반환
        seen = set()
        unique_questions = []
        for q in questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)

        return unique_questions[:5]

    def _suggest_defense_points(
        self, answer: str, risk_areas: List[str]
    ) -> List[str]:
        """방어 포인트 제안"""
        defense_points = []

        # 구체성 관련 방어
        if "구체적인 수치가 없어 증빙이 어려움" in risk_areas:
            defense_points.append(
                "수치를 제시할 때는 측정 방법과 비교 기준을 함께 설명하세요"
            )

        # 개인 기여 관련 방어
        if "팀 성과와 개인 기여가 구분되지 않음" in risk_areas:
            defense_points.append(
                "팀 성과를 언급한 후 '저는 ~부분을 담당하여 ~성과를 냈습니다'로 전환하세요"
            )

        # STAR 구조 관련 방어
        if "STAR 구조가 불완전하여 꼬리질문에 취약" in risk_areas:
            defense_points.append(
                "꼬리질문 시 '그 상황에서는 ~했고, 그 결과 ~되었습니다'로 대응하세요"
            )

        # 일반적 방어 포인트
        defense_points.append(
            "답변 후 '혹시 더 궁금하신 부분이 있으시면 말씀해주세요'로 여지를 남기세요"
        )

        if "과도한 일반화 표현 사용" in risk_areas:
            defense_points.append(
                "'항상', '모두' 대신 '대부분', '주로' 같은 조건부 표현을 사용하세요"
            )

        return defense_points

    def _generate_improvement_suggestions(
        self,
        answer: str,
        risk_areas: List[str],
        question_type: QuestionType,
    ) -> List[str]:
        """개선 제안 생성"""
        suggestions = []

        # 취약점별 개선 제안
        if risk_areas:
            suggestions.append(
                f"식별된 취약점 {len(risk_areas)}개를 보완하세요: "
                + ", ".join(risk_areas[:2])
            )

        # 질문 유형별 맞춤 제안
        type_improvements = {
            QuestionType.TYPE_B: "직무역량 답변은 '역량 선언 → 경험 검증 → 수치 증명' 구조를 유지하세요",
            QuestionType.TYPE_C: "협업 답변은 '갈등 원인 → 조정 노력 → 합의 결과 → 교훈' 순서로 전개하세요",
            QuestionType.TYPE_G: "실패 답변은 '실패 인정 → 원인 분석 → 개선 행동 → 재발 방지' 루틴을 포함하세요",
        }

        if question_type in type_improvements:
            suggestions.append(type_improvements[question_type])

        # 30초 답변 준비 제안
        suggestions.append(
            "핵심만 담은 30초 답변 버전을 별도로 준비하세요"
        )

        return suggestions


def simulate_interview_defense(
    primary_question: str,
    answer: str,
    question_type: QuestionType,
    company_analysis: Optional[CompanyAnalysis] = None,
    experiences: Optional[List[Experience]] = None,
) -> DefenseSimulation:
    """면접 방어 시뮬레이션 편의 함수"""
    simulator = DefenseSimulator(company_analysis)
    return simulator.simulate(primary_question, answer, question_type, experiences)


def generate_follow_up_questions(
    answer: str,
    question_type: QuestionType,
    company_analysis: Optional[CompanyAnalysis] = None,
) -> List[str]:
    """꼬리질문 생성 편의 함수"""
    simulator = DefenseSimulator(company_analysis)
    risk_areas = simulator._identify_risk_areas(answer, question_type)
    return simulator._generate_follow_up_questions(answer, question_type, risk_areas)


def identify_risk_areas(answer: str, question_type: QuestionType) -> List[str]:
    """취약점 식별 편의 함수"""
    simulator = DefenseSimulator()
    return simulator._identify_risk_areas(answer, question_type)


def suggest_defense_points(answer: str, risk_areas: List[str]) -> List[str]:
    """방어 포인트 제안 편의 함수"""
    simulator = DefenseSimulator()
    return simulator._suggest_defense_points(answer, risk_areas)