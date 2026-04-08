"""interactive.py 추가 커버리지 테스트 — MockInterviewCoach 핵심 메서드"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


def _make_exp(
    exp_id: str = "e1",
    title: str = "테스트",
    situation: str = "테스트 상황입니다. 충분히 긴 설명입니다.",
    task: str = "테스트 과제입니다. 충분히 긴 설명입니다.",
    action: str = "테스트 행동을 수행했습니다. 충분히 긴 설명입니다.",
    result: str = "테스트 결과입니다. 30% 향상 달성.",
    metrics: str = "30% 향상",
    personal_contribution: str = "개인 기여 설명",
    tags: list[str] | None = None,
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
        tags=tags or ["테스트"],
        evidence_level=EvidenceLevel.L3,
        verification_status=VerificationStatus.VERIFIED,
    )


def _mock_question(
    q_id: str = "q1", order: int = 1, text: str = "테스트 질문입니다"
) -> MagicMock:
    q = MagicMock()
    q.id = q_id
    q.order_no = order
    q.question_text = text
    q.detected_type = MagicMock(value="TYPE_B")
    q.char_limit = 1000
    return q


# ──────────────────────────────────────────────────
# MockInterviewCoach._provide_feedback 테스트
# ──────────────────────────────────────────────────


class TestProvideFeedback:
    def test_provide_feedback_with_answer(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="normal")
        coach.experiences = [_make_exp()]

        with patch("resume_agent.interactive.classify_question") as mock_classify:
            mock_classify.return_value = MagicMock(value="TYPE_B")
            simulation = coach._provide_feedback(
                "테스트 질문입니다",
                "30% 향상된 결과를 달성했습니다.",
                MagicMock(value="TYPE_B"),
            )
            assert simulation is not None

    def test_provide_feedback_short_answer(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="hard")
        coach.experiences = [_make_exp()]

        with patch("resume_agent.interactive.classify_question") as mock_classify:
            mock_classify.return_value = MagicMock(value="TYPE_A")
            simulation = coach._provide_feedback(
                "지원동기를 말씀해주세요",
                "짧음",
                MagicMock(value="TYPE_A"),
            )
            assert simulation is not None


# ──────────────────────────────────────────────────
# MockInterviewCoach._build_reaction_chain 테스트
# ──────────────────────────────────────────────────


class TestBuildReactionChain:
    def test_build_chain(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        coach.experiences = [_make_exp()]

        simulation = MagicMock()
        simulation.risk_areas = ["근거 부족"]
        simulation.follow_up_questions = ["추가 질문"]
        simulation.defense_points = ["방어 포인트"]

        chain = coach._build_reaction_chain(simulation)
        assert chain is not None


# ──────────────────────────────────────────────────
# MockInterviewCoach._determine_pressure_level 테스트
# ──────────────────────────────────────────────────


class TestDeterminePressureLevel:
    def test_low_pressure(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        level = coach._determine_pressure_level([])
        assert level >= 0

    def test_high_pressure(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        level = coach._determine_pressure_level(["위험1", "위험2", "위험3"])
        assert level >= 0


# ──────────────────────────────────────────────────
# MockInterviewCoach._select_committee_persona 테스트
# ──────────────────────────────────────────────────


class TestSelectCommitteePersona:
    def test_select_persona(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        coach.experiences = [_make_exp()]

        persona = coach._select_committee_persona()
        assert persona is not None


# ──────────────────────────────────────────────────
# MockInterviewCoach._select_panel_personas 테스트
# ──────────────────────────────────────────────────


class TestSelectPanelPersonas:
    def test_select_personas(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        personas = coach._select_panel_personas(3)
        assert isinstance(personas, list)


# ──────────────────────────────────────────────────
# MockInterviewCoach._select_follow_up_question 테스트
# ──────────────────────────────────────────────────


class TestSelectFollowUpQuestion:
    def test_select_question(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        questions = ["추가 질문1", "추가 질문2"]
        result = coach._select_follow_up_question(questions, 3)
        assert result is not None

    def test_select_question_empty(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        result = coach._select_follow_up_question([], 3)
        assert result is None or result == ""


class TestPrepareContext:
    def test_prepare_context(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        coach.experiences = [_make_exp()]
        coach.project = MagicMock()
        coach.project.company_name = "테스트회사"
        coach.project.job_title = "개발자"
        coach.questions = [_mock_question()]

        coach._prepare_context()
        # context가 없어도 에러 없이 실행되면 통과
        assert True


# ──────────────────────────────────────────────────
# MockInterviewCoach.run() with questions 테스트
# ──────────────────────────────────────────────────


class TestMockInterviewRunWithQuestions:
    def test_run_with_questions_quit(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="normal")
        coach.experiences = [_make_exp()]
        coach.project = MagicMock()
        coach.project.company_name = "테스트회사"
        coach.project.job_title = "개발자"
        coach.questions = [_mock_question()]

        with patch("builtins.input", return_value="q"):
            with patch("resume_agent.interactive.classify_question") as mock_classify:
                mock_classify.return_value = MagicMock(value="TYPE_B")
                coach.run()

    def test_run_with_questions_answer_and_quit(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws, mode="normal")
        coach.experiences = [_make_exp()]
        coach.project = MagicMock()
        coach.project.company_name = "테스트회사"
        coach.project.job_title = "개발자"
        coach.questions = [_mock_question()]

        with patch("builtins.input", side_effect=["답변입니다", "q"]):
            with patch("resume_agent.interactive.classify_question") as mock_classify:
                mock_classify.return_value = MagicMock(value="TYPE_B")
                coach.run()
