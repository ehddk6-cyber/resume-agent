"""
인터랙티브 대화형 인터페이스 - 사용자와 실시간으로 상호작용하며 코칭
"""

from __future__ import annotations

from collections import deque
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .workspace import Workspace
from .models import Experience
from .state import load_experiences, save_experiences


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
        self.history: deque[Dict[str, Any]] = deque(maxlen=max_history)  # undo를 위한 히스토리
        self.redo_stack: List[Dict[str, Any]] = []  # redo를 위한 스택
        
    def run(self) -> None:
        """인터랙티브 코칭 세션 시작"""
        print("\n" + "="*60)
        print("🎯 인터랙티브 코칭 세션을 시작합니다")
        print("="*60)
        
        # 경험 데이터 로드
        self.experiences = load_experiences(self.workspace)
        
        if not self.experiences:
            print("\n⚠️ 등록된 경험이 없습니다.")
            print("먼저 경험을 추가해주세요.")
            return
        
        print(f"\n📚 {len(self.experiences)}개의 경험이 로드되었습니다.")
        
        # 메인 루프
        while True:
            print("\n" + "-"*60)
            print("명령어: [s]uggestion 제안 | [e]dit 편집 | [u]ndo 실행취소 | [r]edo 다시실행 | [q]uit 종료")
            print("-"*60)
            
            command = self._safe_input("\n명령어를 입력하세요: ")
            if command is None:
                print("\n👋 입력이 종료되어 코칭 세션을 종료합니다.")
                break
            command = command.lower().strip()
            
            if command in ['q', 'quit', 'exit']:
                print("\n👋 코칭 세션을 종료합니다.")
                break
            elif command in ['s', 'suggestion']:
                self._show_suggestion()
            elif command in ['e', 'edit']:
                self._edit_experience()
            elif command in ['u', 'undo']:
                self._undo()
            elif command in ['r', 'redo']:
                self._redo()
            elif command in ['l', 'list']:
                self._list_experiences()
            elif command in ['h', 'help']:
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
        
        # 제안 생성 (실제로는 LLM 사용)
        suggestions = self._generate_suggestions(experience)
        
        if not suggestions:
            print("✅ 개선할 사항이 없습니다!")
            return
        
        # 제안 표시
        print(f"\n📋 [{experience.title}]에 대한 제안:")
        print("-"*60)
        
        for i, suggestion in enumerate(suggestions, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(suggestion.priority, "⚪")
            print(f"\n{i}. {priority_icon} [{suggestion.category}] {suggestion.title}")
            print(f"   {suggestion.content}")
        
        # 사용자 선택
        print("\n적용할 제안 번호를 입력하세요 (취소: 0):")
        choice = self._safe_input("선택: ")
        if choice is None:
            print("입력이 종료되어 제안 적용을 취소합니다.")
            return
        choice = choice.strip()
        
        if choice == '0':
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
            suggestions.append(Suggestion(
                id="star_situation",
                category="STAR",
                title="상황 설명 보강",
                content="배경, 맥락, 제약조건 등을 더 구체적으로 설명하세요.",
                priority="high"
            ))
        
        if not experience.task or len(experience.task) < 30:
            suggestions.append(Suggestion(
                id="star_task",
                category="STAR",
                title="과제 설명 보강",
                content="담당 역할, 목표, 기대치 등을 더 구체적으로 설명하세요.",
                priority="high"
            ))
        
        if not experience.action or len(experience.action) < 100:
            suggestions.append(Suggestion(
                id="star_action",
                category="STAR",
                title="행동 설명 보강",
                content="수행한 작업, 사용한 기술, 의사결정 과정 등을 더 구체적으로 설명하세요.",
                priority="medium"
            ))
        
        if not experience.result or len(experience.result) < 50:
            suggestions.append(Suggestion(
                id="star_result",
                category="STAR",
                title="결과 설명 보강",
                content="달성한 성과, 배운 점, 영향 등을 더 구체적으로 설명하세요.",
                priority="high"
            ))
        
        # 구체성 검증
        if experience.result and not any(char.isdigit() for char in experience.result):
            suggestions.append(Suggestion(
                id="specificity",
                category="구체성",
                title="수치 추가",
                content="퍼센트, 개수, 금액 등 정량적 지표를 추가하면 더 효과적입니다.",
                priority="medium"
            ))
        
        return suggestions
    
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
        
        if suggestion.id in {"star_situation", "star_task", "star_action", "star_result"} and new_value:
            save_experiences(self.workspace, self.experiences)
    
    def _edit_experience(self) -> None:
        """경험 편집"""
        exp_idx = self._select_experience()
        if exp_idx is None:
            return
        
        experience = self.experiences[exp_idx]
        
        print(f"\n📝 [{experience.title}] 편집 모드")
        print("-"*60)
        
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
            "5": ("result", "결과")
        }
        
        if choice == "0":
            print("취소되었습니다.")
            return
        
        if choice in field_map:
            field_name, field_label = field_map[choice]
            current_value = getattr(experience, field_name, "")
            
            print(f"\n현재 {field_label}:")
            print(f"  {current_value[:100]}..." if len(current_value) > 100 else f"  {current_value}")
            
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
        print("-"*60)
        
        for i, exp in enumerate(self.experiences, 1):
            evidence_icon = {"L1": "⚪", "L2": "🟡", "L3": "🟢"}.get(exp.evidence_level.value, "⚪")
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
        self.redo_stack.append({
            "experiences": copy.deepcopy(self.experiences)
        })
        
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
        self.history.append({
            "experiences": copy.deepcopy(self.experiences)
        })
        
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
        print("-"*60)
        
        for i, exp in enumerate(self.experiences, 1):
            evidence_icon = {"L1": "⚪", "L2": "🟡", "L3": "🟢"}.get(exp.evidence_level.value, "⚪")
            print(f"{i}. {evidence_icon} {exp.title}")
            if exp.situation:
                print(f"   {exp.situation[:80]}...")
    
    def _show_help(self) -> None:
        """도움말 표시"""
        print("\n📖 도움말:")
        print("-"*60)
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
