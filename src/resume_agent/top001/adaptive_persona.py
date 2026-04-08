from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base_types import AnswerStyle, InterviewPersona


CLICHE_PATTERNS = [
    "최선을 다하겠습니다",
    "열정적으로 임하겠습니다",
    "팀원들과 소통하며",
    "맡은 바 책임을 다하겠습니다",
    "성실하게 근무하겠습니다",
    "항상 배우는 자세로",
    "도전을 두려워하지 않는",
    "창의적인 사고를 바탕으로",
]

AI_STYLE_PATTERNS = [
    "이를 바탕으로",
    "이러한 경험을 통해",
    "앞으로도",
    "기여하겠습니다",
    "역량을 발휘하겠습니다",
    "성장할 수 있었습니다",
]

SUPERLATIVES = [
    "최고",
    "유일",
    "완벽",
    "반드시",
    "모두",
    "항상",
    "전부",
    "누구나",
    "끝없이",
    "최상",
    "압도적",
]


def _extract_star_elements(answer: str) -> Dict[str, bool]:
    has_situation = any(kw in answer for kw in ["상황", "当时", "당시", "문제", "과제"])
    has_task = any(kw in answer for kw in ["과제", "목표", "해야 했", "담당"])
    has_action = any(
        kw in answer for kw in ["행동", "수행", "진행", "분석", "개선", "실행"]
    )
    has_result = any(kw in answer for kw in ["결과", "성과", "달성", "완료", "효과"])
    return {
        "S": has_situation,
        "T": has_task,
        "A": has_action,
        "R": has_result,
    }


def _check_superlatives(text: str) -> List[str]:
    found = []
    for sup in SUPERLATIVES:
        if sup in text:
            found.append(sup)
    return found


class AdaptivePersonaEngine:
    def __init__(self):
        self.turn_count = 0
        self.focus_areas = [
            "수량 검증",
            "역할 검증",
            "인과성 검증",
            "대안 검증",
            "일관성 검증",
        ]
        self.current_focus_index = 0

    def classify_answer_style(self, answer: str) -> AnswerStyle:
        if not answer or len(answer.strip()) < 10:
            return AnswerStyle.FRAGMENTED

        vague_count = sum(
            1 for pat in [r"등", r"여러", r"다양한", r"그림"] if re.search(pat, answer)
        )
        if vague_count >= 2:
            return AnswerStyle.EVASIVE

        superlatives = _check_superlatives(answer)
        has_numbers = bool(re.search(r"\d+", answer))
        if superlatives and has_numbers:
            return AnswerStyle.OVERSTATED

        found_cliches = [p for p in CLICHE_PATTERNS if p in answer]
        found_ai = [p for p in AI_STYLE_PATTERNS if p in answer]
        if len(found_cliches) >= 2 or len(found_ai) >= 2:
            return AnswerStyle.FORMULAIC

        star = _extract_star_elements(answer)
        missing_elements = sum(1 for v in star.values() if not v)
        if missing_elements >= 2:
            return AnswerStyle.FRAGMENTED

        if missing_elements == 0 and has_numbers:
            return AnswerStyle.BALANCED
        return AnswerStyle.BALANCED

    def select_persona(self, style: AnswerStyle, turn: int) -> InterviewPersona:
        personas_map = {
            AnswerStyle.EVASIVE: InterviewPersona(
                id="specificity_inspector",
                name="구체성 검증 위원",
                role="추상적 표현을 구체적 사실로 전환",
                focus_areas=["수량 검증", "사실 확인", "구체적 사례"],
                tone="정중하지만 집요하게",
                aggression_level=6,
                attack_patterns=["반복적 구체화 요구", "수치 압박", "근거 확인"],
            ),
            AnswerStyle.OVERSTATED: InterviewPersona(
                id="exaggeration_hunter",
                name="과장 주장 검증 위원",
                role="수치와 주장의 타당성 검증",
                focus_areas=["수량 검증", "기준 확인", "역할 한계"],
                tone="차분하지만 날카롭게",
                aggression_level=8,
                attack_patterns=["수량 산출 기준 질문", "반론 제시", "대안 시나리오"],
            ),
            AnswerStyle.FORMULAIC: InterviewPersona(
                id="originality_tester",
                name="독창성 검증 위원",
                role="차별화 요소와 개인적 특성 탐구",
                focus_areas=["개인 차별화", "상황 특수성", "반복 패턴"],
                tone="관심 있어 보이지만 위험을 찌름",
                aggression_level=5,
                attack_patterns=["비교 질문", "대체 가능성", "패턴 반복 지적"],
            ),
            AnswerStyle.FRAGMENTED: InterviewPersona(
                id="logic_auditor",
                name="논리적 일관성 위원",
                role="인과관계와 논리적 흐름 검증",
                focus_areas=["인과성 검증", "맥락 누락", "전제 가정"],
                tone="냉정하고 분석적",
                aggression_level=7,
                attack_patterns=["연결고리 질문", "모순점 지적", "인과관계 검증"],
            ),
            AnswerStyle.BALANCED: InterviewPersona(
                id="competent_verifier",
                name="역량 검증 위원",
                role="경험의 깊이와 재현 가능성 검증",
                focus_areas=["경험 구체성", "결과 신뢰성", "적용 가능성"],
                tone="공정하고 건설적",
                aggression_level=4,
                attack_patterns=["경험 심화 질문", "결과 확장 질문"],
            ),
        }
        persona = personas_map.get(style, personas_map[AnswerStyle.BALANCED])
        self.turn_count = turn
        return persona

    def escalate_pressure(self, turn: int, weak_response: bool) -> int:
        base_pressure = 3
        escalation = min(turn // 2, 3)
        if weak_response:
            escalation += 2
        pressure = min(10, base_pressure + escalation)
        return pressure

    def rotate_focus_area(self, personas: List[InterviewPersona], current: str) -> str:
        available = [
            f
            for f in self.focus_areas
            if f not in [a for p in personas for a in p.focus_areas[-2:]]
        ]
        if not available:
            available = self.focus_areas
        self.current_focus_index = (self.current_focus_index + 1) % len(available)
        return available[self.current_focus_index]

    def get_committee_personas(
        self, company_type: str = "일반"
    ) -> List[InterviewPersona]:
        committee = [
            InterviewPersona(
                id="chair",
                name="위원장",
                role="전체 논리와 답변 일관성 점검",
                focus_areas=["논리 일관성", "지원동기 진정성", "직무 적합성"],
                tone="정중하지만 냉정함",
                aggression_level=6,
                attack_patterns=["논리 비약 지적", "전제 조건 확인"],
            ),
            InterviewPersona(
                id="domain",
                name="실무위원",
                role="직무 실무 적합성 검증",
                focus_areas=["직무 이해도", "실무 경험", "기술 역량"],
                tone="구체 사례를 집요하게 확인함",
                aggression_level=7,
                attack_patterns=["기술 세부 질문", "경험 깊이 질문"],
            ),
            InterviewPersona(
                id="risk",
                name="리스크위원",
                role="과장, 단일 출처 주장, 실패 대응 검증",
                focus_areas=["개인 기여 검증", "대안 비교", "실패 복구"],
                tone="반례와 허점을 먼저 찾음",
                aggression_level=8,
                attack_patterns=["수량 도전", "역할 분리 요구", "반론 제시"],
            ),
        ]
        if company_type in ["공공", "공기업"]:
            committee.append(
                InterviewPersona(
                    id="public_value",
                    name="공공가치위원",
                    role="공익성, 규정 준수, 서비스 품질 검증",
                    focus_areas=["공익성", "규정 준수", "서비스 품질"],
                    tone="원칙과 책임을 강조함",
                    aggression_level=5,
                    attack_patterns=["규정 관련 질문", "공익성 확인"],
                )
            )
        elif company_type == "스타트업":
            committee.append(
                InterviewPersona(
                    id="execution",
                    name="실행위원",
                    role="짧은 시간 내 실행력과 우선순위 판단 검증",
                    focus_areas=["실행 속도", "우선순위", "자기주도성"],
                    tone="직설적이고 빠른 판단을 요구함",
                    aggression_level=7,
                    attack_patterns=["속도 도전", "우선순위 근거"],
                )
            )
        return committee

    def reset(self):
        self.turn_count = 0
        self.current_focus_index = 0
