"""interactive.py 커버리지 — 핵심 함수 테스트"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


def _make_exp(**kwargs) -> Experience:
    defaults = {
        "id": "e1",
        "title": "테스트 경험",
        "organization": "테스트 조직",
        "period_start": "2024-01",
        "situation": "테스트 상황입니다. 충분히 긴 설명입니다.",
        "task": "테스트 과제입니다. 충분히 긴 설명입니다.",
        "action": "테스트 행동을 수행했습니다. 충분히 긴 설명입니다.",
        "result": "테스트 결과입니다. 30% 향상 달성.",
        "personal_contribution": "개인 기여 설명",
        "metrics": "30% 향상",
        "tags": ["테스트"],
        "evidence_level": EvidenceLevel.L3,
        "verification_status": VerificationStatus.VERIFIED,
    }
    defaults.update(kwargs)
    return Experience(**defaults)


class TestInteractiveCoachApplySuggestion:
    """InteractiveCoach._apply_suggestion 테스트"""

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
            assert coach.experiences[0].situation == "새로운 상황 설명입니다."

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
            assert coach.experiences[0].task == "새로운 과제 설명입니다."

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
            assert coach.experiences[0].action == "새로운 행동 설명입니다."

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
            assert coach.experiences[0].result == "새로운 결과 설명입니다."

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
            assert coach.experiences[0].metrics == "30% 향상"


class TestInteractiveCoachSelectExperience:
    """InteractiveCoach._select_experience 테스트"""

    def test_select_experience(self, tmp_path: Path):
        """경험 선택"""
        from resume_agent.interactive import InteractiveCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = InteractiveCoach(ws)
        coach.experiences = [_make_exp(id="e1"), _make_exp(id="e2")]

        with patch("builtins.input", side_effect=["1", "0"]):
            coach._select_experience()


class TestMockInterviewCoachProvideFeedback:
    """MockInterviewCoach._provide_feedback 테스트"""

    def test_provide_feedback(self, tmp_path: Path):
        """피드백 제공"""
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


class TestMockInterviewCoachBuildReactionChain:
    """MockInterviewCoach._build_reaction_chain 테스트"""

    def test_build_reaction_chain(self, tmp_path: Path):
        """반응 체인 구축"""
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


class TestMockInterviewCoachDeterminePressureLevel:
    """MockInterviewCoach._determine_pressure_level 테스트"""

    def test_low_pressure(self, tmp_path: Path):
        """낮은 압박 수준"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        level = coach._determine_pressure_level([])
        assert level >= 0

    def test_high_pressure(self, tmp_path: Path):
        """높은 압박 수준"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        level = coach._determine_pressure_level(["위험1", "위험2", "위험3"])
        assert level >= 0


class TestMockInterviewCoachSelectCommitteePersona:
    """MockInterviewCoach._select_committee_persona 테스트"""

    def test_select_persona(self, tmp_path: Path):
        """위원회 페르소나 선택"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        coach.experiences = [_make_exp()]

        persona = coach._select_committee_persona()
        assert persona is not None


class TestMockInterviewCoachSelectPanelPersonas:
    """MockInterviewCoach._select_panel_personas 테스트"""

    def test_select_personas(self, tmp_path: Path):
        """패널 페르소나 선택"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        personas = coach._select_panel_personas(3)
        assert isinstance(personas, list)


class TestMockInterviewCoachSelectFollowUpQuestion:
    """MockInterviewCoach._select_follow_up_question 테스트"""

    def test_select_question(self, tmp_path: Path):
        """꼬리질문 선택"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        questions = ["추가 질문1", "추가 질문2"]
        result = coach._select_follow_up_question(questions, 3)
        assert result is not None

    def test_select_question_empty(self, tmp_path: Path):
        """빈 꼬리질문"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        result = coach._select_follow_up_question([], 3)
        assert result is None or result == ""


class TestMockInterviewCoachRunCommitteeRounds:
    """MockInterviewCoach._run_committee_rounds 테스트"""

    def test_run_rounds(self, tmp_path: Path):
        """위원회 라운드 실행"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        rounds = coach._run_committee_rounds(
            question_type=MagicMock(value="TYPE_B"),
            follow_up_questions=["꼬리질문1"],
            panel_personas=[{"name": "위원장", "focus": ["논리성"]}],
        )
        assert isinstance(rounds, list)


class TestMockInterviewCoachSummarizeCommitteeRounds:
    """MockInterviewCoach._summarize_committee_rounds 테스트"""

    def test_summarize(self, tmp_path: Path):
        """위원회 라운드 요약"""
        from resume_agent.interactive import MockInterviewCoach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        coach = MockInterviewCoach(ws)
        summary = coach._summarize_committee_rounds(
            main_risks=["위험1"],
            committee_rounds=[{"persona": "위원장", "question": "질문"}],
        )
        assert summary is not None
