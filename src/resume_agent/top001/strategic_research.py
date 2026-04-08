from __future__ import annotations

import re
from typing import Any, Dict, List, TYPE_CHECKING

from .base_types import (
    StrategicSignals,
    EvidenceMap,
    DefenseStrategy,
)

if TYPE_CHECKING:
    from ..models import Experience, CompanyAnalysis, Question


QUESTION_HOOK_TEMPLATES = {
    "TYPE_A": [
        "귀사의 {value}와 맞닿아 있는 저의 경험은 다음과 같습니다",
        "지원동기: {value}에 공감해 지원하게 되었습니다",
    ],
    "TYPE_B": [
        "저의 {competency} 역량은 이러한 경험에서 증명됩니다",
        "{competency}를 활용한 구체적 사례를 말씀드리겠습니다",
    ],
    "TYPE_E": [
        "입사 후 저는 {value}를 우선 과제로 삼아 기여하겠습니다",
        "저의 첫 90일 계획은 다음과 같습니다",
    ],
}


class StrategicResearchTranslator:
    def extract_strategic_signals(
        self, company_analysis: Any, job_description: str = ""
    ) -> StrategicSignals:
        signals = StrategicSignals()
        if not company_analysis:
            return signals

        if hasattr(company_analysis, "core_values"):
            signals.core_values_alignment = company_analysis.core_values[:3]

        if hasattr(company_analysis, "preferred_evidence_types"):
            signals.competency_matches = company_analysis.preferred_evidence_types[:3]

        interview_style = getattr(company_analysis, "interview_style", None)
        if interview_style:
            style_str = str(
                interview_style.value
                if hasattr(interview_style, "value")
                else interview_style
            )
            signals.interview_prediction = self._predict_interview_questions(style_str)

        signals.differentiation_points = [
            f"귀사 {getattr(company_analysis, 'company_name', '해당')}에서 필요로 하는",
            f"{getattr(company_analysis, 'industry', '업종')} 특화 역량",
        ]

        return signals

    def _predict_interview_questions(self, interview_style: str) -> List[str]:
        predictions = {
            "FORMAL": [
                "성장과정을 말씀해 주세요",
                "지원동기를 구체적으로 말씀해 주세요",
            ],
            "BEHAVIORAL": ["협업 경험을 말씀해 주세요", "갈등 상황을 해결한 경험은?"],
            "TECHNICAL": [
                "기술적 문제 해결 경험을 말씀해 주세요",
                "구체적 구현 방법을 설명해 주세요",
            ],
            "CASUAL": ["왜 우리 회사인가요?", "앞으로 어떻게 발전하고 싶으신가요?"],
        }
        return predictions.get(interview_style, predictions["FORMAL"])

    def generate_question_specific_hooks(
        self,
        questions: List[Question],
        company_analysis: Any,
        experiences: List[Any],
    ) -> Dict[str, List[str]]:
        hooks = {}
        if not company_analysis:
            return hooks

        core_values = getattr(company_analysis, "core_values", [])[:2]
        preferred = getattr(company_analysis, "preferred_evidence_types", [])[:2]

        for q in questions[:4]:
            q_type = getattr(q, "detected_type", None)
            q_type_str = (
                str(q_type.value if hasattr(q_type, "value") else q_type)
                if q_type
                else "TYPE_B"
            )

            if q_type_str == "TYPE_A" and core_values:
                hooks[q.id] = [
                    f"'{core_values[0]}'와 맞닿아 있는 저의 경험은 다음과 같습니다",
                    f"'{core_values[0]}'가 중요한 이유와 제 경험의 연결고리를 말씀드리겠습니다",
                ]
            elif q_type_str == "TYPE_B" and preferred:
                hooks[q.id] = [
                    f"'{preferred[0]}' 역량을 증명하는 경험은 다음과 같습니다",
                    f"구체적 사례를 들어 '{preferred[0]}'를 설명드리겠습니다",
                ]
            elif q_type_str == "TYPE_E":
                hooks[q.id] = [
                    "입사 후 제 첫 기여는 다음과 같습니다",
                    "단기적으로 달성할 수 있는 목표를 말씀드리겠습니다",
                ]
            else:
                hooks[q.id] = [
                    "구체적인 경험을 말씀드리겠습니다",
                    "핵심만 간략히 설명드리겠습니다",
                ]

        return hooks

    def create_evidence_mapping(
        self, experiences: List[Any], company_analysis: Any
    ) -> List[EvidenceMap]:
        if not experiences:
            return []

        maps = []
        preferred = []
        if company_analysis and hasattr(company_analysis, "preferred_evidence_types"):
            preferred = company_analysis.preferred_evidence_types[:2]

        for i, exp in enumerate(experiences[:4]):
            exp_id = getattr(exp, "id", f"exp_{i}")
            exp_title = getattr(exp, "title", "") or ""
            exp_action = getattr(exp, "action", "") or ""
            exp_result = getattr(exp, "result", "") or ""

            signals = []
            if preferred:
                for p in preferred:
                    if p in exp_action or p in exp_result:
                        signals.append(f"'{p}' 가치를 증명하는 경험")
                    else:
                        signals.append(f"귀사에서 중시하는{p} 관련 경험")

            proof_points = []
            if getattr(exp, "metrics", ""):
                proof_points.append(f"정량적 근거: {exp.metrics}")
            if getattr(exp, "evidence_text", ""):
                proof_points.append(f"증빙: {exp.evidence_text[:30]}...")
            if getattr(exp, "personal_contribution", ""):
                proof_points.append(f"개인 기여: {exp.personal_contribution[:30]}...")

            maps.append(
                EvidenceMap(
                    experience_id=exp_id,
                    question_types=["TYPE_B", "TYPE_C"],
                    strategic_signals=signals,
                    proof_points=proof_points,
                )
            )

        return maps

    def build_interview_prediction(
        self, company_analysis: Any, job_description: str = ""
    ) -> List[Dict[str, str]]:
        predictions = []
        if not company_analysis:
            return predictions

        company_type = getattr(company_analysis, "company_type", "일반")
        interview_style = getattr(company_analysis, "interview_style", None)
        style_str = str(
            interview_style.value if hasattr(interview_style, "value") else "FORMAL"
        )

        base_predictions = {
            "공공": [
                {
                    "q": "공익과 관련하여 본인이 실천한 경험은?",
                    "intent": "공익성 검증",
                    "score_point": "시민 서비스 관점",
                },
                {
                    "q": "규정 준수와 관련된 어려움을 겪은 경험은?",
                    "intent": "규정 준수 태도",
                    "score_point": "원칙성 + 실용성",
                },
            ],
            "공기업": [
                {
                    "q": "안전 관리와 관련된 본인의 경험은?",
                    "intent": "안전 의식",
                    "score_point": "실제 대응 능력",
                },
                {
                    "q": "민원 대응 경험을 말씀해 주세요",
                    "intent": "서비스 품질",
                    "score_point": "고객 관점",
                },
            ],
            "대기업": [
                {
                    "q": "조직 내 갈등을 해결한 경험은?",
                    "intent": "조율 능력",
                    "score_point": "논리적 해결책",
                },
                {
                    "q": "목표 달성을 위해 우선순위를 조정했던 경험은?",
                    "intent": "성과 지향",
                    "score_point": "우선순위 판단",
                },
            ],
            "스타트업": [
                {
                    "q": "자원 부족 상황에서 해결한 문제는?",
                    "intent": "실행력",
                    "score_point": "창의적 해결책",
                },
                {
                    "q": "위험을 감수하고 결정했던 경험은?",
                    "intent": "리스크 감수",
                    "score_point": "판단 근거",
                },
            ],
        }

        predictions = base_predictions.get(company_type, base_predictions["대기업"])
        return predictions[:5]

    def generate_defense_strategy(
        self, company_analysis: Any, experiences: List[Any]
    ) -> List[DefenseStrategy]:
        strategies = []

        vulnerable_points = [
            (
                "unclear_attribution",
                "본인의 역할이 모호합니다",
                "제가 직접 담당한 부분은 [구체적 행동]이었습니다",
            ),
            (
                "unverified_metrics",
                "수치의 근거가 불분명합니다",
                "측정 기준은 [기준]이며 [비교 대상]과 비교했습니다",
            ),
            (
                "weak_causality",
                "인과관계가 약합니다",
                "다른 요인도 있었지만, 핵심 원인은 [행동]이었다고 봅니다",
            ),
        ]

        for v_type, vuln, defense in vulnerable_points:
            strategies.append(
                DefenseStrategy(
                    vulnerable_point=vuln,
                    defense_script=defense,
                    backup_evidence=None,
                    alternative_frames=[
                        "뿐만 아니라 다양한 요인이 복합적으로 작용했습니다",
                        "다만, 제가 기여한 핵심 부분은 명시적으로 있었습니다",
                    ],
                )
            )

        return strategies
