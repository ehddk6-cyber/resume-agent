from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base_types import (
    VulnerableLink,
    QuestionChain,
    AttackVector,
    QuestionDepth,
)


VULNERABILITY_QUESTION_TEMPLATES = {
    "insufficient_evidence": {
        QuestionDepth.DEPTH_1: [
            "그 주장에 대한 구체적 근거는 무엇인가요?",
            "그 내용에 대해 어떻게 알고 계신가요?",
        ],
        QuestionDepth.DEPTH_2: [
            "그 근거는 어떤 방식으로 확인하셨나요?",
            "그 데이터나 정보는 어디서 얻으신 거예요?",
        ],
        QuestionDepth.DEPTH_3: [
            "그 근거 외에 다른 해석이나 관점은 없었나요?",
            "만약 그 근거가 부정된다면 어떻게 대답하시겠어요?",
        ],
    },
    "unclear_attribution": {
        QuestionDepth.DEPTH_1: [
            "팀 활동에서 본인의 구체적 역할은 무엇이었나요?",
            "본인이 직접 수행한 부분과 다른 분이 하신 부분을 나눠서 말씀해 주시겠어요?",
        ],
        QuestionDepth.DEPTH_2: [
            "만약 본인이 그 업무를 맡지 않았다면 결과는 달라졌을까요?",
            "팀원 각각이 어떤 기여를 했는지 구체적으로 알고 계신가요?",
        ],
        QuestionDepth.DEPTH_3: [
            "본인의 기여가 반드시 필요했을까요? 다른 방법도 있었을 것 같은데",
            "팀 성과에서 본인의 기여도를百分比로 표현하면 어느 정도라고 보세요?",
        ],
    },
    "overgeneralization": {
        QuestionDepth.DEPTH_1: [
            "'항상' 혹은 '모두'라는 표현의 근거가 되나요?",
            "그 이야기는 구체적으로 어떤 상황에 해당하는 건가요?",
        ],
        QuestionDepth.DEPTH_2: [
            "그 일반화가 해당되지 않는 상황이나 예외는 없었나요?",
            "그 주장을 뒷받침하는 구체적 사례를 들어주실 수 있나요?",
        ],
        QuestionDepth.DEPTH_3: [
            "그 일반화가 항상 성립한다고 확신하시나요?",
            "만약 반례가 제시된다면 어떻게 생각하시겠어요?",
        ],
    },
    "unverified_metrics": {
        QuestionDepth.DEPTH_1: [
            "그 수치(예: {metric})는 어떻게 산출된 것인가요?",
            "그 수치의 기준이나 측정 방법은 무엇인가요?",
        ],
        QuestionDepth.DEPTH_2: [
            "그 수치와 비교한 기준점(대조군)은 무엇이었나요?",
            "그 수치를 수집하거나 측정하신 분이 따로 있으신가요?",
        ],
        QuestionDepth.DEPTH_3: [
            "그 수치에 오차나 오류 가능성은 없었을까요?",
            "측정 환경이나 조건이 달라졌다면 같은 결과가 나왔을까요?",
        ],
    },
    "weak_causality": {
        QuestionDepth.DEPTH_1: [
            "그 결과와 您의 행동 사이에 直接적인 인과관계가 있다고 보시는 근거는 뭔가요?",
            "그 상황이 발생하기 전과 후를 비교하면 무엇이 달라졌나요?",
        ],
        QuestionDepth.DEPTH_2: [
            "그 결과에 영향을 미친 다른 요인이나 변수는 없었나요?",
            "만약 그 행동을 하지 않았다면 결과는 어떻게 달랐을 것으로 예상하세요?",
        ],
        QuestionDepth.DEPTH_3: [
            "그 인과관계를 확인하기 위해 통제하거나 확인하셨던 방법이 있나요?",
            "그 관계가 우연인지 우연이 아닌지 어떻게 판단하셨나요?",
        ],
    },
}


def _extract_claim_keywords(claim: str) -> List[str]:
    keywords = re.findall(r"[가-힣]{2,}", claim)
    important = [
        k
        for k in keywords
        if len(k) >= 2
        and k
        not in {
            "저는",
            "제가",
            "그리고",
            "하지만",
            "따라서",
            "그래서",
        }
    ]
    return important[:5]


def _build_metric_pressure(metric: str) -> str:
    if "%" in metric:
        return f"'{metric}'라는 비율은 어떤 설문이나 측정에서 나온 건가요?"
    if "배" in metric:
        return f"'{metric}' 증가는 무슨 기준으로 판단하신 거예요?"
    return f"'{metric}'라는 수치를 어떻게 확인하셨나요?"


def _build_alternative_scenario(context: str) -> str:
    alt_templates = [
        "만약 {context}하지 않았다면 결과는 어떻게 달라졌을까요?",
        "다른 접근법이나 방법을 고려하셨나요? 왜 그 방법을 선택하셨나요?",
    ]
    return alt_templates[0].format(context=context[:10])


class DeepInterrogator:
    def __init__(self):
        self.used_chains: List[str] = []

    def build_question_chain(self, vulnerable_link: VulnerableLink) -> QuestionChain:
        v_type = vulnerable_link.vulnerability_type
        context = vulnerable_link.description

        templates = VULNERABILITY_QUESTION_TEMPLATES.get(
            v_type, VULNERABILITY_QUESTION_TEMPLATES["insufficient_evidence"]
        )

        d1 = [
            q.format(
                metric=_extract_claim_keywords(context)[0]
                if _extract_claim_keywords(context)
                else "해당 수치"
            )
            for q in templates[QuestionDepth.DEPTH_1]
        ]
        d2 = templates[QuestionDepth.DEPTH_2].copy()
        d3 = templates[QuestionDepth.DEPTH_3].copy()

        if v_type == "unverified_metrics":
            metrics_in_context = re.findall(r"\d+(?:\.\d+)?%|\d+배|\d+건", context)
            if metrics_in_context:
                metric = metrics_in_context[0]
                d1 = [q.format(metric=metric) for q in templates[QuestionDepth.DEPTH_1]]

        attack_vectors = self._build_attack_vectors(vulnerable_link)

        chain_key = f"{v_type}:{d1[0][:20]}"
        if chain_key in self.used_chains:
            d1 = [f"{(d1[0])[:-1]}다시 한번 더 여쭤볼게요. {d1[0][:-1]}?"]
        self.used_chains.append(chain_key)

        return QuestionChain(
            primary_question=vulnerable_link.description,
            depth_1_questions=d1,
            depth_2_questions=d2,
            depth_3_questions=d3,
            attack_vectors=attack_vectors,
        )

    def _build_attack_vectors(self, link: VulnerableLink) -> List[AttackVector]:
        vectors = []
        v_type = link.vulnerability_type

        if v_type == "insufficient_evidence":
            vectors.append(
                AttackVector(
                    name="근거 부재 공격",
                    description="주장만 있고 실질적 근거가 없는情况进行 압박",
                    target_type="evidence",
                    severity="high",
                    example_questions=["근거가 없으면 주장 자체가 무너집니다"],
                )
            )
        elif v_type == "unclear_attribution":
            vectors.append(
                AttackVector(
                    name="역할 모호 공격",
                    description="팀 성과에서 개인 기여도를 구분하기 어려운情况进行 공격",
                    target_type="contribution",
                    severity="high",
                    example_questions=["본인의 기여분을 конкретно表述해주세요"],
                )
            )
        elif v_type == "unverified_metrics":
            vectors.append(
                AttackVector(
                    name="수치 허위 공격",
                    description="측정 기반이 불명한 수치를 사용하여 과장 가능성을狙击",
                    target_type="metric",
                    severity="high",
                    example_questions=["수치의 산출 근거를 명확히해주세요"],
                )
            )
        elif v_type == "overgeneralization":
            vectors.append(
                AttackVector(
                    name="과generalization 공격",
                    description="일반화의 예외情况和한계를 지적하여 논리적 허점暴력",
                    target_type="generality",
                    severity="medium",
                    example_questions=["모든 상황에 적용된다고 확신하나요?"],
                )
            )
        elif v_type == "weak_causality":
            vectors.append(
                AttackVector(
                    name="인과관계 약화 공격",
                    description="원인과 결과 사이의 연결 고리가薄弱한情况进行 공격",
                    target_type="causality",
                    severity="medium",
                    example_questions=["다른 요인의 가능성은 없었나요?"],
                )
            )

        return vectors

    def generate_depth_questions(
        self, vulnerability_type: str, context: str
    ) -> Dict[str, List[str]]:
        templates = VULNERABILITY_QUESTION_TEMPLATES.get(
            vulnerability_type,
            VULNERABILITY_QUESTION_TEMPLATES["insufficient_evidence"],
        )
        metrics = re.findall(r"\d+(?:\.\d+)?%|\d+배|\d+건", context)
        metric = metrics[0] if metrics else "해당 수치"

        return {
            "depth_1": [
                q.format(metric=metric) for q in templates[QuestionDepth.DEPTH_1]
            ],
            "depth_2": templates[QuestionDepth.DEPTH_2],
            "depth_3": templates[QuestionDepth.DEPTH_3],
        }

    def validate_chain(self, chain: QuestionChain) -> bool:
        if not chain.depth_1_questions:
            return False
        if not chain.depth_2_questions and not chain.depth_3_questions:
            return False
        if chain.depth_1_questions == chain.depth_2_questions:
            return False
        return True

    def reset(self):
        self.used_chains = []
