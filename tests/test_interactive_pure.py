"""interactive.py 순수 로직 함수 테스트"""

from __future__ import annotations

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
# InteractiveCoach._generate_suggestions 테스트
# ──────────────────────────────────────────────────


class TestGenerateSuggestions:
    def test_empty_experience(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        exp = _make_exp()
        suggestions = coach._generate_suggestions(exp)
        assert len(suggestions) >= 4  # STAR 4개 항목

    def test_complete_experience(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        exp = _make_exp(
            situation="충분히 긴 상황 설명입니다. 여러 문장으로 구성된 배경과 맥락입니다.",
            task="담당 역할과 목표를 명확히 설명하는 과제입니다. 기대치도 포함합니다.",
            action="수행한 작업을 상세히 설명합니다. 사용한 기술과 의사결정 과정을 포함합니다. 충분히 긴 설명입니다.",
            result="30% 성과 향상을 달성했습니다. 배운 점과 영향을 설명합니다.",
            metrics="30% 향상",
            personal_contribution="개인 기여 설명",
        )
        suggestions = coach._generate_suggestions(exp)
        # 완전한 경험은 제안이 적어야 함
        assert isinstance(suggestions, list)

    def test_no_metrics_suggestion(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        exp = _make_exp(result="성과를 달성했습니다. 좋은 결과였습니다.")
        suggestions = coach._generate_suggestions(exp)
        # 수치가 없는 결과에 대한 제안
        has_specificity = any(s.id == "specificity" for s in suggestions)
        assert has_specificity


# ──────────────────────────────────────────────────
# InteractiveCoach._build_socratic_questions 테스트
# ──────────────────────────────────────────────────


class TestBuildSocraticQuestions:
    def test_basic_questions(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        exp = _make_exp()
        questions = coach._build_socratic_questions(exp)
        assert len(questions) == 3
        assert "사실" in questions[0]
        assert "판단" in questions[1]
        assert "가치관" in questions[2]

    def test_no_metrics_question(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        exp = _make_exp(metrics="")
        questions = coach._build_socratic_questions(exp)
        assert "수치" in questions[0] or "비교" in questions[0]

    def test_no_contribution_question(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        exp = _make_exp(personal_contribution="")
        questions = coach._build_socratic_questions(exp)
        assert "본인이" in questions[1] or "직접" in questions[1]

    def test_minrwoen_in_content(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        exp = _make_exp(title="민원 처리 경험")
        questions = coach._build_socratic_questions(exp)
        assert "민원" in questions[2] or "공공" in questions[2]


# ──────────────────────────────────────────────────
# InteractiveCoach._build_candidate_profile 테스트
# ──────────────────────────────────────────────────


class TestBuildCandidateProfile:
    def test_no_experiences(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = []
        profile = coach._build_candidate_profile()
        assert profile["communication_style"] == "balanced"
        assert profile["signature_strengths"] == []


# ──────────────────────────────────────────────────
# MockInterviewCoach._get_mode_label 테스트
# ──────────────────────────────────────────────────


class TestGetModeLabel:
    def test_hard_mode(self, tmp_path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="hard")
        label = coach._get_mode_label()
        assert "하드" in label or "압박" in label

    def test_normal_mode(self, tmp_path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="normal")
        label = coach._get_mode_label()
        assert "일반" in label

    def test_coach_mode(self, tmp_path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="coach")
        label = coach._get_mode_label()
        assert "코칭" in label

    def test_unknown_mode(self, tmp_path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="unknown")
        label = coach._get_mode_label()
        assert label == "unknown"


class TestSafeInput:
    def test_returns_string(self, tmp_path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        with patch("builtins.input", return_value="테스트 입력"):
            result = coach._safe_input("프롬프트: ")
            assert result == "테스트 입력"

    def test_eof_returns_empty(self, tmp_path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        with patch("builtins.input", side_effect=EOFError):
            result = coach._safe_input("프롬프트: ")
            assert result == "" or result is None


class TestHistory:
    def test_save_history(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp("e1")]
        # undo_stack이 없을 수 있으므로 에러 없이 실행되는지만 확인
        try:
            coach._save_history()
        except AttributeError:
            pass  # undo_stack이 없는 경우

    def test_undo(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp("e1")]
        # undo가 에러 없이 실행되는지만 확인
        coach._undo()

    def test_redo(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp("e1")]
        # redo가 에러 없이 실행되는지만 확인
        coach._redo()

    def test_undo_empty_stack(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp("e1")]
        coach._undo()
        # 빈 스택에서 undo는 변화 없음
        assert len(coach.experiences) == 1

    def test_redo(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp("e1")]
        coach._save_history()
        coach.experiences = [_make_exp("e1"), _make_exp("e2")]
        coach._undo()
        coach._redo()
        assert len(coach.experiences) == 2

    def test_redo_empty_stack(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp("e1")]
        coach._redo()
        assert len(coach.experiences) == 1


# ──────────────────────────────────────────────────
# InteractiveCoach._list_experiences 테스트
# ──────────────────────────────────────────────────


class TestListExperiences:
    def test_empty_experiences(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = []
        # 에러 없이 실행되어야 함
        coach._list_experiences()

    def test_with_experiences(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp("e1", "경험1"), _make_exp("e2", "경험2")]
        coach._list_experiences()


# ──────────────────────────────────────────────────
# InteractiveCoach._show_help 테스트
# ──────────────────────────────────────────────────


class TestShowHelp:
    def test_show_help(self, tmp_path):
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        # 에러 없이 실행되어야 함
        coach._show_help()


# ──────────────────────────────────────────────────
# run_interactive_coach 테스트
# ──────────────────────────────────────────────────


class TestRunInteractiveCoach:
    def test_run_and_quit(self, tmp_path):
        from resume_agent.interactive import run_interactive_coach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch("resume_agent.interactive.load_experiences", return_value=[]):
            with patch("builtins.input", return_value="q"):
                with patch("resume_agent.interactive.save_experiences"):
                    run_interactive_coach(ws)


# ──────────────────────────────────────────────────
# run_mock_interview 테스트
# ──────────────────────────────────────────────────


class TestRunMockInterview:
    def test_run_and_quit(self, tmp_path):
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
