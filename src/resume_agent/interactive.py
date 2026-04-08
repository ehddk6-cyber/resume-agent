"""
인터랙티브 대화형 인터페이스 - 사용자와 실시간으로 상호작용하며 코칭
"""

from __future__ import annotations

from collections import deque
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import re

from .workspace import Workspace
from .models import Experience, QuestionType
from .state import (
    load_experiences,
    save_experiences,
    load_project,
    save_project,
    load_success_cases,
)
from .defense_simulator import DefenseSimulator, AGGRESSIVE_PATTERNS
from .classifier import classify_question
from .company_analyzer import analyze_company, build_role_industry_strategy_from_project
from .feedback_learner import create_feedback_learner


@dataclass
class Suggestion:
    """코칭 제안"""

    id: str
    category: str
    title: str
    content: str
    priority: str  # "high", "medium", "low"


class InteractiveCoach:
    """
    대화형 코칭 세션

    기능:
    - 실시간 제안 생성
    - 사용자 피드백 반영
    - undo/redo 기능
    - 편집기 연동
    """

    def __init__(self, workspace: Workspace, max_history: int = 50):
        self.workspace = workspace
        self.experiences: List[Experience] = []
        self.max_history = max_history
        self.history: deque[Dict[str, Any]] = deque(
            maxlen=max_history
        )  # undo를 위한 히스토리
        self.redo_stack: List[Dict[str, Any]] = []  # redo를 위한 스택

    def run(self) -> None:
        """인터랙티브 코칭 세션 시작"""
        print("\n" + "=" * 60)
        print("🎯 인터랙티브 코칭 세션을 시작합니다")
        print("=" * 60)

        # 경험 데이터 로드
        self.experiences = load_experiences(self.workspace)

        if not self.experiences:
            print("\n⚠️ 등록된 경험이 없습니다.")
            print("먼저 경험을 추가해주세요.")
            return

        print(f"\n📚 {len(self.experiences)}개의 경험이 로드되었습니다.")
        candidate_profile = self._build_candidate_profile()
        print(f"🧭 코칭 포인트: {candidate_profile.get('profile_summary', '')}")

        # 메인 루프
        while True:
            print("\n" + "-" * 60)
            print(
                "명령어: [s]uggestion 제안 | [e]dit 편집 | [u]ndo 실행취소 | [r]edo 다시실행 | [q]uit 종료"
            )
            print("-" * 60)

            command = self._safe_input("\n명령어를 입력하세요: ")
            if command is None:
                print("\n👋 입력이 종료되어 코칭 세션을 종료합니다.")
                break
            command = command.lower().strip()

            if command in ["q", "quit", "exit"]:
                print("\n👋 코칭 세션을 종료합니다.")
                break
            elif command in ["s", "suggestion"]:
                self._show_suggestion()
            elif command in ["e", "edit"]:
                self._edit_experience()
            elif command in ["u", "undo"]:
                self._undo()
            elif command in ["r", "redo"]:
                self._redo()
            elif command in ["l", "list"]:
                self._list_experiences()
            elif command in ["h", "help"]:
                self._show_help()
            else:
                print(f"❓ 알 수 없는 명령어: {command}")

    def _show_suggestion(self) -> None:
        """현재 경험에 대한 제안 생성"""
        print("\n💡 제안을 생성합니다...")

        # 경험 선택
        exp_idx = self._select_experience()
        if exp_idx is None:
            return

        experience = self.experiences[exp_idx]
        self._run_socratic_loop(experience)

        # 제안 생성 (실제로는 LLM 사용)
        suggestions = self._generate_suggestions(experience)

        if not suggestions:
            print("✅ 개선할 사항이 없습니다!")
            return

        # 제안 표시
        print(f"\n📋 [{experience.title}]에 대한 제안:")
        print("-" * 60)

        for i, suggestion in enumerate(suggestions, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                suggestion.priority, "⚪"
            )
            print(f"\n{i}. {priority_icon} [{suggestion.category}] {suggestion.title}")
            print(f"   {suggestion.content}")

        # 사용자 선택
        print("\n적용할 제안 번호를 입력하세요 (취소: 0):")
        choice = self._safe_input("선택: ")
        if choice is None:
            print("입력이 종료되어 제안 적용을 취소합니다.")
            return
        choice = choice.strip()

        if choice == "0":
            print("취소되었습니다.")
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                self._apply_suggestion(exp_idx, suggestions[idx])
            else:
                print("❌ 잘못된 번호입니다.")
        except ValueError:
            print("❌ 숫자를 입력해주세요.")

    def _generate_suggestions(self, experience: Experience) -> List[Suggestion]:
        """경험에 대한 제안 생성"""
        suggestions = []

        # STAR 구조 검증
        if not experience.situation or len(experience.situation) < 50:
            suggestions.append(
                Suggestion(
                    id="star_situation",
                    category="STAR",
                    title="상황 설명 보강",
                    content="배경, 맥락, 제약조건 등을 더 구체적으로 설명하세요.",
                    priority="high",
                )
            )

        if not experience.task or len(experience.task) < 30:
            suggestions.append(
                Suggestion(
                    id="star_task",
                    category="STAR",
                    title="과제 설명 보강",
                    content="담당 역할, 목표, 기대치 등을 더 구체적으로 설명하세요.",
                    priority="high",
                )
            )

        if not experience.action or len(experience.action) < 100:
            suggestions.append(
                Suggestion(
                    id="star_action",
                    category="STAR",
                    title="행동 설명 보강",
                    content="수행한 작업, 사용한 기술, 의사결정 과정 등을 더 구체적으로 설명하세요.",
                    priority="medium",
                )
            )

        if not experience.result or len(experience.result) < 50:
            suggestions.append(
                Suggestion(
                    id="star_result",
                    category="STAR",
                    title="결과 설명 보강",
                    content="달성한 성과, 배운 점, 영향 등을 더 구체적으로 설명하세요.",
                    priority="high",
                )
            )

        # 구체성 검증
        if experience.result and not any(char.isdigit() for char in experience.result):
            suggestions.append(
                Suggestion(
                    id="specificity",
                    category="구체성",
                    title="수치 추가",
                    content="퍼센트, 개수, 금액 등 정량적 지표를 추가하면 더 효과적입니다.",
                    priority="medium",
                )
            )

        return suggestions

    def _build_candidate_profile(self) -> Dict[str, Any]:
        if not self.experiences:
            return {
                "communication_style": "balanced",
                "signature_strengths": [],
                "coaching_focus": ["경험을 먼저 충분히 수집하세요."],
                "profile_summary": "경험 데이터가 아직 부족합니다.",
            }
        from .pipeline import build_candidate_profile

        project = load_project(self.workspace)
        return build_candidate_profile(self.workspace, project, self.experiences)

    def _build_socratic_questions(self, experience: Experience) -> List[str]:
        fact_prompt = "[사실] 이 경험에서 실제로 있었던 상황과 본인이 한 행동을 순서대로 다시 말해보세요."
        judgment_prompt = (
            "[판단] 여러 선택지 중 왜 그 대응을 골랐는지 판단 기준을 설명해보세요."
        )
        value_prompt = "[가치관] 이 경험이 본인의 일하는 기준이나 고객 응대 원칙을 어떻게 보여주나요?"

        if not experience.metrics.strip():
            fact_prompt = "[사실] 이 경험의 전후 차이와 성과를 비교 기준이나 수치와 함께 다시 말해보세요."
        if not experience.personal_contribution.strip():
            judgment_prompt = "[판단] 팀과 함께한 일이라면 그중 본인이 직접 판단하고 책임진 부분이 무엇이었는지 설명해보세요."
        if "민원" in f"{experience.title} {experience.situation} {experience.action}":
            value_prompt = "[가치관] 이 경험이 본인의 민원 응대 원칙이나 공공서비스 기준을 어떻게 보여주나요?"

        return [fact_prompt, judgment_prompt, value_prompt]

    def _run_socratic_loop(self, experience: Experience) -> None:
        print("\n🧭 [Socratic 코칭]")
        for question in self._build_socratic_questions(experience):
            print(f"   - {question}")
            answer = self._safe_input("     답변 메모 (건너뛰기: 엔터): ")
            if answer is None:
                print("입력이 종료되어 Socratic 코칭을 마칩니다.")
                return

    def _apply_suggestion(self, exp_idx: int, suggestion: Suggestion) -> None:
        """제안 적용"""
        experience = self.experiences[exp_idx]
        new_value = ""

        # 제안 적용 (실제로는 사용자 편집 필요)
        print(f"\n✏️ 제안을 적용합니다: {suggestion.title}")
        print("편집기에서 수정하거나 직접 입력하세요.")

        # 편집 모드
        if suggestion.id == "star_situation":
            new_value = self._safe_input("새로운 상황 설명 (취소: 빈 입력): ")
            if new_value is None:
                print("입력이 종료되어 취소되었습니다.")
                return
            new_value = new_value.strip()
            if new_value:
                self._save_history()
                experience.situation = new_value
                print("✅ 상황 설명이 업데이트되었습니다.")

        elif suggestion.id == "star_task":
            new_value = self._safe_input("새로운 과제 설명 (취소: 빈 입력): ")
            if new_value is None:
                print("입력이 종료되어 취소되었습니다.")
                return
            new_value = new_value.strip()
            if new_value:
                self._save_history()
                experience.task = new_value
                print("✅ 과제 설명이 업데이트되었습니다.")

        elif suggestion.id == "star_action":
            new_value = self._safe_input("새로운 행동 설명 (취소: 빈 입력): ")
            if new_value is None:
                print("입력이 종료되어 취소되었습니다.")
                return
            new_value = new_value.strip()
            if new_value:
                self._save_history()
                experience.action = new_value
                print("✅ 행동 설명이 업데이트되었습니다.")

        elif suggestion.id == "star_result":
            new_value = self._safe_input("새로운 결과 설명 (취소: 빈 입력): ")
            if new_value is None:
                print("입력이 종료되어 취소되었습니다.")
                return
            new_value = new_value.strip()
            if new_value:
                self._save_history()
                experience.result = new_value
                print("✅ 결과 설명이 업데이트되었습니다.")

        else:
            print("ℹ️ 이 제안은 수동으로 적용해주세요.")

        if (
            suggestion.id
            in {"star_situation", "star_task", "star_action", "star_result"}
            and new_value
        ):
            save_experiences(self.workspace, self.experiences)

    def _edit_experience(self) -> None:
        """경험 편집"""
        exp_idx = self._select_experience()
        if exp_idx is None:
            return

        experience = self.experiences[exp_idx]

        print(f"\n📝 [{experience.title}] 편집 모드")
        print("-" * 60)

        # 필드 선택
        print("편집할 필드를 선택하세요:")
        print("1. 제목")
        print("2. 상황 (Situation)")
        print("3. 과제 (Task)")
        print("4. 행동 (Action)")
        print("5. 결과 (Result)")
        print("0. 취소")

        choice = self._safe_input("선택: ")
        if choice is None:
            print("입력이 종료되어 편집을 취소합니다.")
            return
        choice = choice.strip()

        field_map = {
            "1": ("title", "제목"),
            "2": ("situation", "상황"),
            "3": ("task", "과제"),
            "4": ("action", "행동"),
            "5": ("result", "결과"),
        }

        if choice == "0":
            print("취소되었습니다.")
            return

        if choice in field_map:
            field_name, field_label = field_map[choice]
            current_value = getattr(experience, field_name, "")

            print(f"\n현재 {field_label}:")
            print(
                f"  {current_value[:100]}..."
                if len(current_value) > 100
                else f"  {current_value}"
            )

            new_value = self._safe_input(f"\n새로운 {field_label} (취소: 빈 입력): ")
            if new_value is None:
                print("입력이 종료되어 편집을 취소합니다.")
                return
            new_value = new_value.strip()

            if new_value:
                self._save_history()
                setattr(experience, field_name, new_value)
                save_experiences(self.workspace, self.experiences)
                print(f"✅ {field_label}이(가) 업데이트되었습니다.")
            else:
                print("취소되었습니다.")
        else:
            print("❌ 잘못된 선택입니다.")

    def _select_experience(self) -> Optional[int]:
        """경험 선택"""
        print("\n📚 경험 목록:")
        print("-" * 60)

        for i, exp in enumerate(self.experiences, 1):
            evidence_icon = {"L1": "⚪", "L2": "🟡", "L3": "🟢"}.get(
                exp.evidence_level.value, "⚪"
            )
            print(f"{i}. {evidence_icon} {exp.title}")

        print("0. 취소")

        choice = self._safe_input("\n선택: ")
        if choice is None:
            print("입력이 종료되어 선택을 취소합니다.")
            return None
        choice = choice.strip()

        if choice == "0":
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.experiences):
                return idx
            else:
                print("❌ 잘못된 번호입니다.")
                return None
        except ValueError:
            print("❌ 숫자를 입력해주세요.")
            return None

    def _save_history(self) -> None:
        """현재 상태를 히스토리에 저장 (undo를 위해)"""
        import copy

        self.history.append({"experiences": copy.deepcopy(self.experiences)})
        self.redo_stack.clear()  # 새 변경 시 redo 스택 비우기

    def _undo(self) -> None:
        """실행 취소"""
        if not self.history:
            print("↩️ 실행 취소할 작업이 없습니다.")
            return

        # 현재 상태를 redo 스택에 저장
        import copy

        self.redo_stack.append({"experiences": copy.deepcopy(self.experiences)})

        # 히스토리에서 복원
        prev_state = self.history.pop()
        self.experiences = prev_state["experiences"]
        save_experiences(self.workspace, self.experiences)

        print("↩️ 실행 취소되었습니다.")

    def _redo(self) -> None:
        """다시 실행"""
        if not self.redo_stack:
            print("↪️ 다시 실행할 작업이 없습니다.")
            return

        # 현재 상태를 히스토리에 저장
        import copy

        self.history.append({"experiences": copy.deepcopy(self.experiences)})

        # redo 스택에서 복원
        next_state = self.redo_stack.pop()
        self.experiences = next_state["experiences"]
        save_experiences(self.workspace, self.experiences)

        print("↪️ 다시 실행되었습니다.")

    def _safe_input(self, prompt: str) -> Optional[str]:
        """EOFError를 처리하는 입력 래퍼"""
        try:
            return input(prompt)
        except EOFError:
            return None

    def _list_experiences(self) -> None:
        """경험 목록 표시"""
        print("\n📚 전체 경험 목록:")
        print("-" * 60)

        for i, exp in enumerate(self.experiences, 1):
            evidence_icon = {"L1": "⚪", "L2": "🟡", "L3": "🟢"}.get(
                exp.evidence_level.value, "⚪"
            )
            print(f"{i}. {evidence_icon} {exp.title}")
            if exp.situation:
                print(f"   {exp.situation[:80]}...")

    def _show_help(self) -> None:
        """도움말 표시"""
        print("\n📖 도움말:")
        print("-" * 60)
        print("s, suggestion  - 현재 경험에 대한 개선 제안 생성")
        print("e, edit        - 경험 직접 편집")
        print("u, undo        - 실행 취소")
        print("r, redo        - 다시 실행")
        print("l, list        - 경험 목록 표시")
        print("h, help        - 도움말 표시")
        print("q, quit        - 종료")


def run_interactive_coach(workspace: Workspace) -> None:
    """인터랙티브 코칭 실행 편의 함수"""
    coach = InteractiveCoach(workspace)
    coach.run()


class SelfIntroDrillCoach:
    """자기소개 반복 훈련 코치"""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.application_strategy: Dict[str, Any] = {}
        self.practice_history: List[Dict[str, Any]] = []

    def _load_json(self, path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _safe_input(self, prompt: str) -> Optional[str]:
        try:
            return input(prompt)
        except EOFError:
            return None

    def _load_strategy(self) -> None:
        self.application_strategy = self._load_json(
            self.workspace.analysis_dir / "application_strategy.json", {}
        )
        self.practice_history = self._load_json(
            self.workspace.state_dir / "self_intro_drills.json", []
        )

    def _build_drill_prompts(self) -> Dict[str, Any]:
        intro = self.application_strategy.get("self_intro_candidates", {})
        versions = intro.get("top001_versions", {}) or {}
        expected_follow_ups = intro.get("expected_follow_ups", []) or []
        opening = intro.get("opening_hook", "")
        return {
            "opening_hook": opening,
            "versions": versions,
            "expected_follow_ups": expected_follow_ups[:3],
        }

    def _score_attempt(self, answer: str) -> Dict[str, Any]:
        risks: List[str] = []
        if len(answer.strip()) < 40:
            risks.append("답변이 너무 짧아 핵심 역량과 근거가 충분히 드러나지 않습니다.")
        if not any(char.isdigit() for char in answer):
            risks.append("수치나 비교 기준이 없어 설득력이 떨어질 수 있습니다.")
        if not any(keyword in answer for keyword in ["기여", "개선", "성과", "경험"]):
            risks.append("개인 기여와 성과 연결이 약하게 들릴 수 있습니다.")
        score = max(0.0, 1.0 - (len(risks) * 0.2))
        return {
            "score": round(score, 2),
            "risks": risks,
            "coaching_points": [
                "첫 문장에 지원 직무와 연결되는 핵심 경험을 배치하세요.",
                "둘째 문장에는 수치나 비교 기준을 넣어 설득력을 높이세요.",
                "마지막 문장은 입사 후 기여 방식으로 닫아 주세요.",
            ][: max(1, min(3, len(risks) + 1))],
        }

    def _save_attempt(self, attempt: Dict[str, Any]) -> None:
        self.practice_history.append(attempt)
        path = self.workspace.state_dir / "self_intro_drills.json"
        path.write_text(
            json.dumps(self.practice_history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def run(self) -> None:
        self._load_strategy()
        prompts = self._build_drill_prompts()

        print("\n" + "=" * 60)
        print("🗣️ 자기소개 반복 훈련을 시작합니다")
        print("=" * 60)

        if prompts["opening_hook"]:
            print(f"\n오프닝 훅: {prompts['opening_hook']}")
        if prompts["versions"]:
            print("\n추천 버전:")
            for name, text in prompts["versions"].items():
                print(f"- {name}: {text}")
        if prompts["expected_follow_ups"]:
            print("\n예상 꼬리질문:")
            for item in prompts["expected_follow_ups"]:
                print(f"- {item}")

        answer = self._safe_input("\n자기소개 답변을 입력하세요 (종료: q): ")
        if answer is None or answer.strip().lower() == "q":
            print("\n👋 자기소개 훈련을 종료합니다.")
            return

        evaluation = self._score_attempt(answer)
        print(f"\n점수: {evaluation['score']}")
        if evaluation["risks"]:
            print("리스크:")
            for item in evaluation["risks"]:
                print(f"- {item}")
        print("훈련 포인트:")
        for item in evaluation["coaching_points"]:
            print(f"- {item}")

        self._save_attempt(
            {
                "timestamp": datetime.now().isoformat(),
                "answer": answer,
                "score": evaluation["score"],
                "risks": evaluation["risks"],
                "expected_follow_ups": prompts["expected_follow_ups"],
            }
        )
        print(f"\n💾 자기소개 훈련 결과가 저장되었습니다: {self.workspace.state_dir / 'self_intro_drills.json'}")


@dataclass
class InterviewTurn:
    """면접 턴 기록"""

    question: str
    answer: str
    question_type: QuestionType
    interviewer_persona: str = ""
    interviewer_profile: Dict[str, Any] = field(default_factory=dict)
    risk_areas: List[str] = field(default_factory=list)
    defense_points: List[str] = field(default_factory=list)
    follow_up_question: str = ""
    follow_up_answer: str = ""
    follow_up_risk_areas: List[str] = field(default_factory=list)
    reaction_chain: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_reaction_chain: List[Dict[str, Any]] = field(default_factory=list)
    committee_rounds: List[Dict[str, Any]] = field(default_factory=list)
    committee_summary: Dict[str, Any] = field(default_factory=dict)
    pressure_level: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MockInterviewCoach:
    """
    대화형 모의면접 코치

    기능:
    - 질문 → 답변 → 피드백 → 꼬리질문 루프
    - 실시간 리스크 감지 및 방어 포인트 제안
    - 3회 반복 지원
    - 세션 히스토리 저장
    """

    def __init__(self, workspace: Workspace, mode: str = "normal"):
        self.workspace = workspace
        self.mode = mode  # "hard", "normal", "coach"
        self.experiences: List[Experience] = []
        self.questions: List[Any] = []
        self.turns: List[InterviewTurn] = []
        self.current_question_index = 0
        self.retry_count = 0
        self.max_retries = 3
        self.project = None
        self.company_analysis = None
        self.strategy_pack: Dict[str, Any] = {}
        self.feedback_learning: Dict[str, Any] = {}
        self.committee_personas: List[Dict[str, Any]] = []
        self.application_strategy: Dict[str, Any] = {}

    def run(self) -> None:
        """모의면접 세션 시작"""
        print("\n" + "=" * 60)
        print("🎤 대화형 모의면접 세션을 시작합니다")
        print("=" * 60)

        # 데이터 로드
        self.experiences = load_experiences(self.workspace)
        self.project = load_project(self.workspace)
        self._prepare_project_questions()
        self._prepare_context()

        if not self.questions:
            print("\n⚠️ 등록된 문항이 없습니다.")
            print("먼저 coach를 실행하여 문항을 매핑해주세요.")
            return

        if not self.experiences:
            print("\n⚠️ 등록된 경험이 없습니다.")
            print("먼저 경험을 추가해주세요.")
            return

        print(
            f"\n📚 {len(self.questions)}개 문항, {len(self.experiences)}개 경험 로드 완료"
        )
        print(f"🎯 모드: {self._get_mode_label()}")
        print("\n면접을 시작합니다. 'q'를 입력하면 종료합니다.")

        # 메인 루프
        while self.current_question_index < len(self.questions):
            question = self.questions[self.current_question_index]
            question_type = getattr(
                question, "detected_type", None
            ) or classify_question(question.question_text)

            print("\n" + "-" * 60)
            interviewer_persona = self._select_committee_persona()
            persona_label = interviewer_persona.get("name", "면접관")
            persona_focus = ", ".join(interviewer_persona.get("focus", [])[:2])
            print(f"🎤 {persona_label} (Q{question.order_no}/{len(self.questions)}):")
            if persona_focus:
                print(f"   초점: {persona_focus}")
            print(f"   {question.question_text}")

            # 답변 입력
            answer = self._safe_input("\n👤 답변: ")
            if answer is None or answer.lower() == "q":
                print("\n👋 면접을 종료합니다.")
                break

            if not answer.strip():
                print("⚠️ 답변을 입력해주세요.")
                continue

            interviewer_profile = self._build_interviewer_profile(
                interviewer_persona,
                question_type,
                1,
            )
            simulation = self._provide_feedback(
                question.question_text,
                answer,
                question_type,
                interviewer_profile,
            )
            retry_guidance = self._build_retry_guidance(simulation.risk_areas, question_type)
            if retry_guidance:
                print("\n🎯 [재답변 가이드]")
                for item in retry_guidance:
                    print(f"   - {item}")
            reaction_chain = self._build_reaction_chain(simulation)
            pressure_level = self._determine_pressure_level(simulation.risk_areas)
            panel_personas = self._select_panel_personas(pressure_level)
            interviewer_profile = self._build_interviewer_profile(
                interviewer_persona,
                question_type,
                pressure_level,
            )
            follow_up_questions = list(simulation.follow_up_questions)
            follow_up_question = self._select_follow_up_question(
                follow_up_questions, pressure_level, interviewer_profile
            )
            follow_up_answer = ""
            follow_up_risk_areas: List[str] = []
            committee_rounds: List[Dict[str, Any]] = []

            if follow_up_question:
                print("\n🎯 [적응형 꼬리질문]")
                print(f"   - {follow_up_question}")
                follow_up_answer = (
                    self._safe_input("\n👤 꼬리질문 답변 (건너뛰기: 엔터): ") or ""
                )
                if follow_up_answer.strip():
                    follow_up_simulation = self._provide_follow_up_feedback(
                        follow_up_question, follow_up_answer, question_type
                    )
                    follow_up_risk_areas = follow_up_simulation.risk_areas
                    follow_up_reaction_chain = self._build_reaction_chain(
                        follow_up_simulation
                    )
                    committee_rounds.append(
                        {
                            "persona": persona_label,
                            "question": follow_up_question,
                            "answer": follow_up_answer.strip(),
                            "risk_areas": follow_up_risk_areas,
                            "defense_points": follow_up_simulation.defense_points[:2],
                        }
                    )
                else:
                    follow_up_reaction_chain = []
            else:
                follow_up_reaction_chain = []

            remaining_follow_ups = [
                item for item in follow_up_questions if item != follow_up_question
            ]
            committee_rounds.extend(
                self._run_committee_rounds(
                    question_type=question_type,
                    follow_up_questions=remaining_follow_ups,
                    panel_personas=panel_personas,
                )
            )
            committee_summary = self._summarize_committee_rounds(
                main_risks=simulation.risk_areas,
                committee_rounds=committee_rounds,
            )
            self._print_committee_summary(committee_summary, interviewer_profile)

            self.turns.append(
                InterviewTurn(
                    question=question.question_text,
                    answer=answer,
                    question_type=question_type,
                    interviewer_persona=persona_label,
                    interviewer_profile=interviewer_profile,
                    risk_areas=simulation.risk_areas,
                    defense_points=simulation.defense_points,
                    follow_up_question=follow_up_question,
                    follow_up_answer=follow_up_answer.strip(),
                    follow_up_risk_areas=follow_up_risk_areas,
                    reaction_chain=reaction_chain,
                    follow_up_reaction_chain=follow_up_reaction_chain,
                    committee_rounds=committee_rounds,
                    committee_summary=committee_summary,
                    pressure_level=pressure_level,
                )
            )

            # 다음 질문으로 이동 또는 재시도
            if self.retry_count >= self.max_retries:
                print(
                    f"\n⚠️ 최대 재시도 횟수({self.max_retries})에 도달했습니다. 다음 질문으로 이동합니다."
                )
                self.current_question_index += 1
                self.retry_count = 0
            else:
                # 재시도 여부 확인
                retry = self._safe_input("\n다시 시도하시겠습니까? (y/n, 기본값: n): ")
                if retry and retry.lower() == "y":
                    self.retry_count += 1
                    print(f"\n🔄 재시도 {self.retry_count}/{self.max_retries}")
                else:
                    self.current_question_index += 1
                    self.retry_count = 0

        # 세션 완료
        self._save_session()
        self._show_summary()

    def _provide_feedback(
        self,
        question: str,
        answer: str,
        question_type: QuestionType,
        interviewer_profile: Optional[Dict[str, Any]] = None,
    ):
        """답변에 대한 피드백 생성"""
        simulator = DefenseSimulator(self.company_analysis)
        simulation = simulator.simulate(
            question, answer, question_type, self.experiences
        )
        interviewer_profile = interviewer_profile or {}
        style_label = interviewer_profile.get("verification_style", "")
        scenario_brief = interviewer_profile.get("scenario_brief", "")

        if style_label:
            print(f"\n🧭 [면접관 스타일] {style_label}")
        if scenario_brief:
            print(f"   - {scenario_brief}")

        # 리스크 표시
        if simulation.risk_areas:
            print("\n⚠️ [리스크 감지]")
            for risk in simulation.risk_areas:
                print(f"   - {risk}")

        # 방어 포인트 표시
        if simulation.defense_points:
            print("\n💡 [방어 포인트]")
            for point in simulation.defense_points[:2]:
                print(f"   - {point}")

        # 개선 제안
        if simulation.improvement_suggestions:
            print("\n📝 [개선 제안]")
            for suggestion in simulation.improvement_suggestions[:2]:
                print(f"   - {suggestion}")

        # 꼬리질문 힌트
        if self.mode == "hard" and simulation.follow_up_questions:
            print("\n🔥 [압박 꼬리질문]")
            for fq in simulation.follow_up_questions[:1]:
                print(f"   - {fq}")
        return simulation

    def _build_reaction_chain(self, simulation) -> List[Dict[str, Any]]:
        follow_up_questions = list(simulation.follow_up_questions or [])
        risk_areas = list(simulation.risk_areas or [])
        return [
            {
                "turn": 1,
                "stage": "first_impression",
                "signal": "답변의 첫 인상과 핵심 주장 점검",
            },
            {
                "turn": 2,
                "stage": "probe",
                "signal": (
                    follow_up_questions[0]
                    if follow_up_questions
                    else "근거를 더 구체적으로 설명해 주세요."
                ),
            },
            {
                "turn": 3,
                "stage": "verdict_shift",
                "signal": (
                    risk_areas[0]
                    if risk_areas
                    else "현재 답변은 비교적 안정적으로 들립니다."
                ),
            },
        ]

    def _provide_follow_up_feedback(
        self, question: str, answer: str, question_type: QuestionType
    ):
        simulator = DefenseSimulator(self.company_analysis)
        simulation = simulator.simulate(
            question, answer, question_type, self.experiences
        )

        if simulation.risk_areas:
            print("\n🔍 [꼬리질문 보완 포인트]")
            for risk in simulation.risk_areas[:2]:
                print(f"   - {risk}")

        if simulation.defense_points:
            print("\n🛡️ [즉시 보강 문장]")
            for point in simulation.defense_points[:2]:
                print(f"   - {point}")

        return simulation

    def _prepare_context(self) -> None:
        if not self.project or not self.project.company_name:
            return
        from .pipeline import build_candidate_profile

        try:
            _cases = load_success_cases(self.workspace)
            self.company_analysis = analyze_company(
                company_name=self.project.company_name,
                job_title=self.project.job_title,
                company_type=self.project.company_type,
                success_cases=_cases if _cases else None,
            )
        except Exception:
            self.company_analysis = None

        question_map = self._load_json(
            self.workspace.analysis_dir / "question_map.json", []
        )
        source_grading = self._load_json(
            self.workspace.analysis_dir / "source_grading.json", {}
        )
        self.application_strategy = self._load_json(
            self.workspace.analysis_dir / "application_strategy.json", {}
        )

        if self.company_analysis:
            self.strategy_pack = build_role_industry_strategy_from_project(
                self.project,
                self.company_analysis,
                question_map=question_map,
                source_grading=source_grading,
            )
            self.company_analysis.role_industry_strategy = self.strategy_pack
            self.committee_personas = self.strategy_pack.get("committee_personas", [])

        learner = create_feedback_learner(str(self.workspace.root / "kb" / "feedback"))
        question_types = [
            question.detected_type.value
            for question in self.project.questions
            if getattr(question, "detected_type", None)
        ]
        self.feedback_learning = {
            "recommendations": learner.get_recommendation(
                {
                    "artifact_type": "interview",
                    "artifact": "interview",
                    "stage": "interview",
                    "company_name": self.project.company_name,
                    "job_title": self.project.job_title,
                    "company_type": self.project.company_type,
                    "question_types": question_types,
                }
            )[:3],
            "outcome_summary": learner.get_context_outcome_summary(
                {
                    "artifact_type": "interview",
                    "artifact": "interview",
                    "stage": "interview",
                    "company_name": self.project.company_name,
                    "job_title": self.project.job_title,
                    "company_type": self.project.company_type,
                    "question_types": question_types,
                }
            ),
            "recent_comments": [
                item.comment
                for item in learner.db.get_feedback_history(limit=20)
                if item.artifact_type == "interview" and item.comment
            ][:3],
            "candidate_profile": (
                build_candidate_profile(self.workspace, self.project, self.experiences)
                if self.experiences
                else {}
            ),
            "application_strategy": self.application_strategy,
        }

    def _prepare_project_questions(self) -> None:
        if not self.project:
            self.questions = []
            return
        try:
            from .pipeline import classify_project_questions_with_llm_fallback

            self.project = classify_project_questions_with_llm_fallback(
                self.workspace,
                self.project,
                enabled=True,
            )
            save_project(self.workspace, self.project)
        except Exception:
            for question in self.project.questions:
                question.detected_type = classify_question(question.question_text)
        self.questions = self.project.questions

    def _determine_pressure_level(self, risk_areas: List[str]) -> int:
        level = 1
        if self.mode == "hard":
            level += 1
        if len(risk_areas) >= 2:
            level += 1
        if self.strategy_pack.get("single_source_risks"):
            level += 1
        if self.application_strategy.get("interview_pressure_points"):
            level += 1
        return min(level, 3)

    def _select_follow_up_question(
        self,
        follow_up_questions: List[str],
        pressure_level: int,
        interviewer_profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not follow_up_questions:
            return ""

        interviewer_profile = interviewer_profile or {}
        scenario_tokens: List[str] = []
        for text in [
            interviewer_profile.get("scenario_brief", ""),
            interviewer_profile.get("verification_style", ""),
            interviewer_profile.get("focus_prompt", ""),
            interviewer_profile.get("pressure_theme", ""),
        ]:
            scenario_tokens.extend(re.findall(r"[A-Za-z0-9가-힣]{2,}", str(text)))

        for token in scenario_tokens:
            matched = next(
                (
                    question
                    for question in follow_up_questions
                    if token in question
                ),
                None,
            )
            if matched:
                return matched

        if pressure_level >= 3:
            priority_tokens = self.strategy_pack.get("interview_pressure_themes", []) + [
                str(item)
                for item in self.application_strategy.get("interview_pressure_points", [])
            ]
            for token in priority_tokens:
                matched = next(
                    (
                        question
                        for question in follow_up_questions
                        if token.split()[0] in question
                    ),
                    None,
                )
                if matched:
                    return matched

        return follow_up_questions[0]

    def _select_panel_personas(self, pressure_level: int) -> List[Dict[str, Any]]:
        if not self.committee_personas:
            return []
        count = min(len(self.committee_personas), max(1, pressure_level))
        start_index = self.current_question_index % len(self.committee_personas)
        return [
            self.committee_personas[
                (start_index + offset) % len(self.committee_personas)
            ]
            for offset in range(count)
        ]

    def _run_committee_rounds(
        self,
        question_type: QuestionType,
        follow_up_questions: List[str],
        panel_personas: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        rounds: List[Dict[str, Any]] = []
        if not follow_up_questions or not panel_personas:
            return rounds

        for idx, persona in enumerate(panel_personas[1:], start=0):
            if idx >= len(follow_up_questions):
                break
            question = follow_up_questions[idx]
            persona_name = persona.get("name", "위원")
            focus = ", ".join(persona.get("focus", [])[:2])
            print(f"\n🧑‍⚖️ [{persona_name} 추가 검증]")
            if focus:
                print(f"   초점: {focus}")
            print(f"   - {question}")
            answer = self._safe_input("\n👤 위원 답변 (건너뛰기: 엔터): ") or ""
            if not answer.strip():
                rounds.append(
                    {
                        "persona": persona_name,
                        "question": question,
                        "answer": "",
                        "risk_areas": ["답변 생략"],
                        "defense_points": [],
                    }
                )
                continue

            simulation = self._provide_follow_up_feedback(
                question, answer, question_type
            )
            rounds.append(
                {
                    "persona": persona_name,
                    "question": question,
                    "answer": answer.strip(),
                    "risk_areas": simulation.risk_areas,
                    "defense_points": simulation.defense_points[:2],
                }
            )
        return rounds

    def _summarize_committee_rounds(
        self, main_risks: List[str], committee_rounds: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        total_risks = len(main_risks) + sum(
            len(item.get("risk_areas", [])) for item in committee_rounds
        )
        verdict = "pass"
        if total_risks >= 5:
            verdict = "fail"
        elif total_risks >= 3:
            verdict = "borderline"

        return {
            "verdict": verdict,
            "total_risk_count": total_risks,
            "participating_personas": [
                item.get("persona", "")
                for item in committee_rounds
                if item.get("persona")
            ],
        }

    def _print_committee_summary(
        self,
        committee_summary: Dict[str, Any],
        interviewer_profile: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not committee_summary:
            return
        interviewer_profile = interviewer_profile or {}
        verdict_map = {
            "pass": "통과 가능",
            "borderline": "보완 필요",
            "fail": "추가 연습 권장",
        }
        print("\n🏛️ [위원회 종합 의견]")
        print(
            f"   - 판정: {verdict_map.get(committee_summary.get('verdict', ''), '미정')}"
        )
        print(f"   - 총 리스크 수: {committee_summary.get('total_risk_count', 0)}")
        if interviewer_profile.get("verification_style"):
            print(
                f"   - 검증 관점: {interviewer_profile.get('verification_style')}"
            )
        if interviewer_profile.get("scenario_brief"):
            print(f"   - 시나리오: {interviewer_profile.get('scenario_brief')}")

    def _select_committee_persona(self) -> Dict[str, Any]:
        if not self.committee_personas:
            return {}
        index = self.current_question_index % len(self.committee_personas)
        return self.committee_personas[index]

    def _build_interviewer_profile(
        self,
        persona: Dict[str, Any],
        question_type: QuestionType,
        pressure_level: int,
    ) -> Dict[str, Any]:
        adaptive_layer = self.application_strategy.get("adaptive_strategy_layer", {})
        interview_mode = adaptive_layer.get("interview_mode", "")
        pressure_points = self.application_strategy.get("interview_pressure_points", [])

        if self.mode == "hard" or pressure_level >= 3:
            verification_style = "압박 검증형"
        elif question_type == QuestionType.TYPE_A:
            verification_style = "동기·적합성 검증형"
        elif question_type == QuestionType.TYPE_E:
            verification_style = "입사 후 실행력 검증형"
        else:
            verification_style = "근거 확인형"

        focus_tokens = persona.get("focus", [])[:2]
        pressure_theme = next(
            (item for item in pressure_points if item),
            "",
        )
        focus_prompt = ", ".join(focus_tokens) if focus_tokens else interview_mode
        scenario_by_type = {
            QuestionType.TYPE_A: "지원동기의 진정성과 기관 적합성을 교차 검증합니다.",
            QuestionType.TYPE_B: "핵심 역량의 재현 가능성과 성과 근거를 검증합니다.",
            QuestionType.TYPE_C: "협업 장면에서의 조율 방식과 갈등 처리 기준을 검증합니다.",
            QuestionType.TYPE_E: "입사 후 실행 계획이 현실적인지 구체성을 검증합니다.",
        }
        scenario_brief = scenario_by_type.get(
            question_type,
            "답변의 사실성, 판단 근거, 일관성을 검증합니다.",
        )
        return {
            "persona_name": persona.get("name", "면접관"),
            "verification_style": verification_style,
            "focus_prompt": focus_prompt,
            "pressure_theme": pressure_theme,
            "scenario_brief": scenario_brief,
        }

    def _load_json(self, path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _build_retry_guidance(
        self, risk_areas: List[str], question_type: QuestionType
    ) -> List[str]:
        guidance: List[str] = []
        if not risk_areas:
            guidance.append("현재 답변은 안정적입니다. 핵심 문장만 더 짧게 압축해도 좋습니다.")
            return guidance

        if any("근거" in risk for risk in risk_areas):
            guidance.append("주장 다음 문장에 숫자·비교 기준·증빙 출처를 바로 붙여서 다시 답해보세요.")
        if any("기여" in risk or "역할" in risk for risk in risk_areas):
            guidance.append("팀 성과보다 본인이 직접 판단하고 책임진 부분을 먼저 말해보세요.")
        if question_type == QuestionType.TYPE_A:
            guidance.append("회사 신호와 본인 경험 연결고리를 첫 문장에 배치해 보세요.")
        elif question_type == QuestionType.TYPE_E:
            guidance.append("입사 후 90일 안에 할 수 있는 실행 단위로 바꿔서 답해보세요.")
        else:
            guidance.append("답변 구조를 상황-행동-결과 순으로 다시 정렬해 보세요.")
        return guidance[:3]

    def _build_growth_snapshot(self, previous_sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        current_total_risks = sum(
            len(turn.risk_areas) + len(turn.follow_up_risk_areas) for turn in self.turns
        )
        current_avg = current_total_risks / len(self.turns) if self.turns else 0.0
        if not previous_sessions:
            return {
                "previous_avg_risk": None,
                "current_avg_risk": round(current_avg, 2),
                "delta": None,
                "trend": "first_session",
            }

        latest = previous_sessions[-1]
        previous_turns = latest.get("turns", [])
        previous_total = sum(
            len(turn.get("risk_areas", [])) + len(turn.get("follow_up_risk_areas", []))
            for turn in previous_turns
        )
        previous_avg = previous_total / len(previous_turns) if previous_turns else 0.0
        delta = round(previous_avg - current_avg, 2)
        if delta > 0.2:
            trend = "improving"
        elif delta < -0.2:
            trend = "regressing"
        else:
            trend = "stable"
        return {
            "previous_avg_risk": round(previous_avg, 2),
            "current_avg_risk": round(current_avg, 2),
            "delta": delta,
            "trend": trend,
        }

    def _build_training_focus(self) -> List[str]:
        recurring_risks = []
        for turn in self.turns:
            recurring_risks.extend(turn.risk_areas)
            recurring_risks.extend(turn.follow_up_risk_areas)
        focus: List[str] = []
        adaptation_plan = self.feedback_learning.get("adaptation_plan", {})
        if any("근거" in risk for risk in recurring_risks):
            focus.append("수치·비교 기준을 한 문장 안에 넣는 연습")
        if any("기여" in risk or "역할" in risk for risk in recurring_risks):
            focus.append("개인 기여를 20초 안에 분리 설명하는 연습")
        if self.application_strategy.get("self_intro_candidates", {}).get("expected_follow_ups"):
            focus.append("자기소개 후 예상 꼬리질문 3개를 연속으로 답하는 연습")
        for action in adaptation_plan.get("focus_actions", [])[:2]:
            focus.append(f"학습 루프 우선 과제: {action}")
        if not focus:
            focus.append("핵심 메시지를 1문장으로 압축한 뒤 근거를 붙이는 연습")
        return focus[:4]

    def _show_summary(self) -> None:
        """세션 요약 표시"""
        print("\n" + "=" * 60)
        print("📊 모의면접 세션 요약")
        print("=" * 60)

        if not self.turns:
            print("기록된 턴이 없습니다.")
            return

        total_risks = sum(len(turn.risk_areas) for turn in self.turns)
        avg_risks = total_risks / len(self.turns) if self.turns else 0

        print(f"총 턴 수: {len(self.turns)}")
        print(f"평균 리스크 수: {avg_risks:.1f}")

        # 리스크가 많은 질문 표시
        high_risk_turns = [t for t in self.turns if len(t.risk_areas) >= 2]
        if high_risk_turns:
            print("\n🔴 리스크가 높은 질문:")
            for turn in high_risk_turns:
                print(f"   - {turn.question[:50]}... ({len(turn.risk_areas)}개 리스크)")

        previous_sessions = self._load_json(
            self.workspace.state_dir / "interview_sessions.json", []
        )
        growth = self._build_growth_snapshot(previous_sessions[:-1] if previous_sessions else [])
        if growth.get("trend") != "first_session":
            print("\n📈 세션 성장 추이:")
            print(
                f"   - 이전 평균 리스크: {growth.get('previous_avg_risk', 0)} / 현재: {growth.get('current_avg_risk', 0)}"
            )
            print(f"   - 추세: {growth.get('trend')}")

        training_focus = self._build_training_focus()
        if training_focus:
            print("\n🎯 다음 연습 포인트:")
            for item in training_focus:
                print(f"   - {item}")

    def _save_session(self) -> None:
        """세션 히스토리 저장"""
        if not self.turns:
            return

        session_data = {
            "mode": self.mode,
            "timestamp": datetime.now().isoformat(),
            "turns": [
                {
                    "question": turn.question,
                    "answer": turn.answer,
                    "question_type": turn.question_type.value
                    if hasattr(turn.question_type, "value")
                    else str(turn.question_type),
                    "interviewer_persona": turn.interviewer_persona,
                    "interviewer_profile": turn.interviewer_profile,
                    "risk_areas": turn.risk_areas,
                    "defense_points": turn.defense_points,
                    "follow_up_question": turn.follow_up_question,
                    "follow_up_answer": turn.follow_up_answer,
                    "follow_up_risk_areas": turn.follow_up_risk_areas,
                    "reaction_chain": turn.reaction_chain,
                    "follow_up_reaction_chain": turn.follow_up_reaction_chain,
                    "committee_rounds": turn.committee_rounds,
                    "committee_summary": turn.committee_summary,
                    "pressure_level": turn.pressure_level,
                    "timestamp": turn.timestamp,
                }
                for turn in self.turns
            ],
        }

        session_path = self.workspace.state_dir / "interview_sessions.json"
        existing = []
        if session_path.exists():
            try:
                existing = json.loads(session_path.read_text(encoding="utf-8"))
            except Exception:
                existing = []

        session_data["training_focus"] = self._build_training_focus()
        session_data["self_intro_drill"] = self.application_strategy.get(
            "self_intro_candidates", {}
        )
        session_data["growth_snapshot"] = self._build_growth_snapshot(existing)

        existing.append(session_data)
        session_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n💾 세션이 저장되었습니다: {session_path}")

    def _get_mode_label(self) -> str:
        """모드 레이블 반환"""
        labels = {
            "hard": "🔥 하드 모드 (압박 면접)",
            "normal": "🎯 일반 모드",
            "coach": "💡 코칭 모드 (실시간 피드백)",
        }
        return labels.get(self.mode, self.mode)

    def _safe_input(self, prompt: str) -> Optional[str]:
        """EOFError를 처리하는 입력 래퍼"""
        try:
            return input(prompt)
        except EOFError:
            return None


def run_mock_interview(workspace: Workspace, mode: str = "normal") -> None:
    """모의면접 실행 편의 함수"""
    coach = MockInterviewCoach(workspace, mode)
    coach.run()


def run_self_intro_drill(workspace: Workspace) -> None:
    """자기소개 반복 훈련 실행 편의 함수"""
    coach = SelfIntroDrillCoach(workspace)
    coach.run()
