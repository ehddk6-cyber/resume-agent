"""interactive.py Phase 2 테스트 — stdin/stdout mocking"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


def _make_exp(
    exp_id: str = "e1",
    title: str = "테스트",
    situation: str = "",
    task: str = "",
    action: str = "",
    result: str = "",
    metrics: str = "",
    personal_contribution: str = "",
) -> Experience:
    return Experience(
        id=exp_id,
        title=title,
        organization="테스트 조직",
        period_start="2024-01",
        situation=situation,
        task=task,
        action=action,
        result=result,
        personal_contribution=personal_contribution,
        metrics=metrics,
        tags=[],
        evidence_level=EvidenceLevel.L1,
        verification_status=VerificationStatus.NEEDS_VERIFICATION,
    )


# ──────────────────────────────────────────────────
# InteractiveCoach.run() 테스트
# ──────────────────────────────────────────────────


class TestInteractiveCoachRun:
    def test_run_quit_immediately(self, tmp_path: Path):
        """바로 종료"""
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch("resume_agent.interactive.load_experiences", return_value=[]):
            with patch("resume_agent.interactive.save_experiences"):
                with patch("builtins.input", return_value="q"):
                    coach = InteractiveCoach(ws)
                    coach.run()

    def test_run_list_experiences(self, tmp_path: Path):
        """경험 목록 표시 후 종료"""
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch(
            "resume_agent.interactive.load_experiences", return_value=[_make_exp()]
        ):
            with patch("resume_agent.interactive.save_experiences"):
                with patch("builtins.input", side_effect=["l", "q"]):
                    coach = InteractiveCoach(ws)
                    coach.run()

    def test_run_help_command(self, tmp_path: Path):
        """도움말 표시 후 종료"""
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch("resume_agent.interactive.load_experiences", return_value=[]):
            with patch("resume_agent.interactive.save_experiences"):
                with patch("builtins.input", side_effect=["h", "q"]):
                    coach = InteractiveCoach(ws)
                    coach.run()


# ──────────────────────────────────────────────────
# InteractiveCoach._apply_suggestion 테스트
# ──────────────────────────────────────────────────


class TestApplySuggestion:
    def test_apply_star_situation(self, tmp_path: Path):
        """STAR 상황 제안 적용"""
        from resume_agent.interactive import InteractiveCoach, Suggestion

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp()]

        suggestion = Suggestion(
            id="star_situation",
            category="STAR",
            title="상황 설명 보강",
            content="배경을 더 구체적으로 설명하세요.",
            priority="high",
        )

        with patch("builtins.input", return_value="새로운 상황 설명입니다."):
            coach._apply_suggestion(0, suggestion)

    def test_apply_star_task(self, tmp_path: Path):
        """STAR 과제 제안 적용"""
        from resume_agent.interactive import InteractiveCoach, Suggestion

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp()]

        suggestion = Suggestion(
            id="star_task",
            category="STAR",
            title="과제 설명 보강",
            content="담당 역할을 설명하세요.",
            priority="high",
        )

        with patch("builtins.input", return_value="새로운 과제 설명입니다."):
            coach._apply_suggestion(0, suggestion)

    def test_apply_star_action(self, tmp_path: Path):
        """STAR 행동 제안 적용"""
        from resume_agent.interactive import InteractiveCoach, Suggestion

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp()]

        suggestion = Suggestion(
            id="star_action",
            category="STAR",
            title="행동 설명 보강",
            content="수행한 작업을 설명하세요.",
            priority="medium",
        )

        with patch("builtins.input", return_value="새로운 행동 설명입니다."):
            coach._apply_suggestion(0, suggestion)

    def test_apply_star_result(self, tmp_path: Path):
        """STAR 결과 제안 적용"""
        from resume_agent.interactive import InteractiveCoach, Suggestion

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp()]

        suggestion = Suggestion(
            id="star_result",
            category="STAR",
            title="결과 설명 보강",
            content="성과를 설명하세요.",
            priority="high",
        )

        with patch("builtins.input", return_value="새로운 결과 설명입니다."):
            coach._apply_suggestion(0, suggestion)

    def test_apply_specificity(self, tmp_path: Path):
        """구체성 제안 적용"""
        from resume_agent.interactive import InteractiveCoach, Suggestion

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp()]

        suggestion = Suggestion(
            id="specificity",
            category="구체성",
            title="수치 추가",
            content="정량적 지표를 추가하세요.",
            priority="medium",
        )

        with patch("builtins.input", return_value="30% 향상"):
            coach._apply_suggestion(0, suggestion)


# ──────────────────────────────────────────────────
# InteractiveCoach._edit_experience 테스트
# ──────────────────────────────────────────────────


class TestEditExperience:
    def test_edit_title(self, tmp_path: Path):
        """제목 편집"""
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp()]

        # _select_experience를 호출하여 경험 선택 시뮬레이션
        with patch("builtins.input", side_effect=["1", "0"]):
            coach._select_experience()


class TestGetModeLabel:
    def test_all_modes(self, tmp_path: Path):
        """모든 모드 레이블 확인"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        for mode in ["hard", "normal", "coach"]:
            coach = MockInterviewCoach(ws, mode=mode)
            label = coach._get_mode_label()
            assert label is not None


# ──────────────────────────────────────────────────
# MockInterviewCoach._safe_input 테스트
# ──────────────────────────────────────────────────


class TestSafeInput:
    def test_normal_input(self, tmp_path: Path):
        """정상 입력"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        with patch("builtins.input", return_value="테스트 입력"):
            result = coach._safe_input("프롬프트: ")
            assert result == "테스트 입력"

    def test_eof_input(self, tmp_path: Path):
        """EOF 입력"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        with patch("builtins.input", side_effect=EOFError):
            result = coach._safe_input("프롬프트: ")
            assert result == "" or result is None


# ──────────────────────────────────────────────────
# run_mock_interview 테스트
# ──────────────────────────────────────────────────


class TestRunMockInterview:
    def test_run_quit_immediately(self, tmp_path: Path):
        """바로 종료"""
        from resume_agent.interactive import run_mock_interview

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch("resume_agent.interactive.load_experiences", return_value=[]):
            with patch("resume_agent.interactive.load_project") as mock_project:
                mock_project.return_value = MagicMock(
                    company_name="테스트",
                    job_title="개발자",
                    questions=[],
                )
                with patch("builtins.input", return_value="q"):
                    run_mock_interview(ws, "normal")


# ──────────────────────────────────────────────────
# run_interactive_coach 테스트
# ──────────────────────────────────────────────────


class TestRunInteractiveCoach:
    def test_run_quit(self, tmp_path: Path):
        """바로 종료"""
        from resume_agent.interactive import run_interactive_coach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch("resume_agent.interactive.load_experiences", return_value=[]):
            with patch("resume_agent.interactive.save_experiences"):
                with patch("builtins.input", return_value="q"):
                    run_interactive_coach(ws)
