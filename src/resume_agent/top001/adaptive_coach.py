from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base_types import (
    CoachingState,
    CoachingFeedback,
    SocraticQuestion,
)

if TYPE_CHECKING:
    from ..models import Experience, Question


SOCRATIC_QUESTION_TEMPLATES = {
    "experience_depth": [
        "그 상황에서 가장难度가 컸던 부분은 무엇이었나요?",
        "만약 같은 상황을 다시 맞이한다면 무엇을 다르게 하실 건가요?",
        "그 경험에서 您가 가장 많이 배운 점은 무엇인가요?",
    ],
    "personal_contribution": [
        "만약 您가 그 팀에 합류하지 않았다면 결과는 달라졌을까요?",
        "团队에서 您만의 독특한 기여는 무엇이었나요?",
        "其他 팀원들과 구별되는 您의 접근법은 무엇이었나요?",
    ],
    "result_verification": [
        "그 결과는 어떻게 측정하거나 확인하셨나요?",
        "改善의 정도를 다른 방식으로 표현하면 어떻게 되나요?",
        "그 결과에 대해 다른 관점이나 해석은 없었나요?",
    ],
    "goal_clarity": [
        "그 목표를 정할 때 누군가와 상의하셨나요?",
        "목표의 우선순위나 기준은 무엇이었나요?",
        "그 목표가 조직 전체의 목표와 어떻게 연결되나요?",
    ],
    "difficulty_facing": [
        "그困难를 해결하지 못했다면 어떤后果가 있었을까요?",
        "가장 결정적인 순간은 언제였나요?",
        "왜 그困难이 발생했다고 보시나요?",
    ],
}


class AdaptiveCoachEngine:
    def __init__(self):
        self.state = CoachingState.RAPPORT
        self.history: List[Dict[str, Any]] = []
        self.experience_quality: Dict[str, int] = {}

    def diagnose_user_state(
        self,
        experiences: List[Experience],
        project_questions: List[Question],
    ) -> CoachingState:
        if not experiences:
            return CoachingState.RAPPORT
        l3_count = sum(
            1
            for e in experiences
            if getattr(e, "evidence_level", None)
            and "L3" in str(getattr(e, "evidence_level", ""))
        )
        if l3_count >= 2 and len(experiences) >= 3:
            return CoachingState.DISCOVERY
        elif l3_count >= 1:
            return CoachingState.STRATEGY
        return CoachingState.VALIDATION

    def generate_socratic_questions(
        self, experience: Experience, focus_area: str = "experience_depth"
    ) -> List[SocraticQuestion]:
        templates = SOCRATIC_QUESTION_TEMPLATES.get(
            focus_area, SOCRATIC_QUESTION_TEMPLATES["experience_depth"]
        )
        questions = []
        for i, template in enumerate(templates[:2]):
            question_text = template
            intent_map = {
                "experience_depth": "深度 있는 스토리 발굴",
                "personal_contribution": "个人 기여 구분",
                "result_verification": "결과 신뢰성 확보",
                "goal_clarity": "목표와 동기 명확화",
                "difficulty_facing": "困難 해결 능력 검증",
            }
            questions.append(
                SocraticQuestion(
                    question=question_text,
                    intent=intent_map.get(focus_area, "경험 이해 증진"),
                    expected_insight="구체적 사실과个人적 관점",
                    follow_up_if_vague=f"좀 더 구체적으로 말씀해 주시겠어요? 예를 들면...",
                )
            )
        return questions

    def provide_realtime_feedback(
        self, user_input: str, context: Optional[str] = None
    ) -> CoachingFeedback:
        strengths: List[str] = []
        improvements: List[str] = []
        suggestions: List[str] = []

        vague_words = ["등", "여러", "다양한", "그림", "보통"]
        if not any(w in user_input for w in vague_words):
            strengths.append("구체적인 표현을 사용하셨네요")

        numbers = re.findall(r"\d+", user_input)
        if numbers:
            strengths.append(f"정량적 근거({numbers[0]})가 포함되어 있습니다")
            improvements.append("그 수치의 산출 기준을 미리 준비해 두세요")
        else:
            improvements.append("구체적 수치를 포함하면 더욱 설득력 있습니다")

        if "저는" in user_input or "제가" in user_input:
            strengths.append("개인 기여를 명확히 하고 계십니다")
        elif "우리" in user_input or "팀" in user_input:
            improvements.append("개인 기여와 팀 성과를 구분해서 말씀해 주세요")

        personal_pronouns = ["저는", "제가", "내가", "담당하여", "주도하여"]
        if any(p in user_input for p in personal_pronouns):
            suggestions.append("30초 안에 핵심만 말씀해 보세요")

        return CoachingFeedback(
            strength_points=strengths,
            improvement_areas=improvements,
            specific_suggestions=suggestions,
            next_action=self._determine_next_action(improvements),
        )

    def _determine_next_action(self, improvements: List[str]) -> str:
        if not improvements:
            return "다음 경험으로 넘어가도 좋습니다"
        if any("수치" in i for i in improvements):
            return "그 경험의 결과를 수치로 표현할 수 있을지 생각해 보세요"
        if any("개인" in i for i in improvements):
            return "본인이 직접 기여한 부분을 분리해서 생각해 보세요"
        return "구체적인 상황과 행동을 추가해 보세요"

    def create_progressive_plan(
        self, experiences: List[Experience], questions: List[Question]
    ) -> List[Dict[str, Any]]:
        plan = []
        l3_experiences = [
            e
            for e in experiences
            if getattr(e, "evidence_level", None)
            and "L3" in str(getattr(e, "evidence_level", ""))
        ]

        plan.append(
            {
                "session": 1,
                "state": CoachingState.DISCOVERY.value,
                "focus": "핵심 경험 3개 발굴 + STAR 구조화",
                "activities": [
                    "가장 설득력 있는 경험 선택",
                    "각 경험의 상황-행동-결과 정리",
                    "면접에서 다시 꺼낼 증빙 문장 만들기",
                ],
                "output": "경험 카드 3개 완성",
            }
        )

        plan.append(
            {
                "session": 2,
                "state": CoachingState.STRATEGY.value,
                "focus": "문항별 경험 매핑 + 차별화 포인트",
                "activities": [
                    "문항 유형별 핵심 메시지 설정",
                    "경험-문항 최적 배분",
                    "회사와 직무 접점 찾기",
                ],
                "output": "경험 배분표 + 차별화 전략",
            }
        )

        plan.append(
            {
                "session": 3,
                "state": CoachingState.VALIDATION.value,
                "focus": "근거 검증 및 보강",
                "activities": [
                    "L3 증거 수준 확인",
                    "수치와 측정 기준 검증",
                    "증빙 자료 준비",
                ],
                "output": "검증 완료 경험列表",
            }
        )

        plan.append(
            {
                "session": 4,
                "state": CoachingState.REHEARSAL.value,
                "focus": "면접 예상 질문 + 방어 연습",
                "activities": [
                    "3-depth 꼬리질문 시뮬레이션",
                    "30초 스피치 연습",
                    "취약점 방어 연습",
                ],
                "output": "완성된 답변 프레임워크",
            }
        )

        return plan

    def track_coaching_progress(self) -> Dict[str, Any]:
        return {
            "current_state": self.state.value,
            "total_turns": len(self.history),
            "experience_quality": self.experience_quality,
            "completed_sessions": len(
                [h for h in self.history if h.get("session_complete", False)]
            ),
        }

    def transition_state(self, new_state: CoachingState):
        self.state = new_state

    def reset(self):
        self.state = CoachingState.RAPPORT
        self.history = []
        self.experience_quality = {}
