"""interview_engine.py 커버리지 — 누락 라인 27-99"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRunRecursiveInterviewChain:
    def test_with_prepared_answers(self, tmp_path: Path):
        from resume_agent.interview_engine import run_recursive_interview_chain
        from resume_agent.models import (
            ApplicationProject,
            Experience,
            EvidenceLevel,
            VerificationStatus,
        )

        project = MagicMock()
        project.company_name = "테스트회사"
        project.job_title = "개발자"
        project.company_type = "대기업"
        project.research_notes = "전략적 노트"

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="테스트 행동을 수행했습니다.",
            result="테스트 결과입니다. 30% 향상 달성.",
            personal_contribution="개인 기여 설명",
            metrics="30% 향상",
            tags=["테스트"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        questions = ["질문1", "질문2"]
        answers = ["답변1", "답변2"]

        with patch(
            "resume_agent.interview_engine._call_codex_simple", return_value="꼬리질문"
        ):
            with patch("resume_agent.interview_engine.analyze_company") as mock_analyze:
                mock_analyze.return_value = MagicMock()
                with patch(
                    "resume_agent.interview_engine.build_role_industry_strategy_from_project"
                ) as mock_strategy:
                    mock_strategy.return_value = {"committee_personas": []}
                    with patch(
                        "resume_agent.interview_engine.load_success_cases",
                        return_value=[],
                    ):
                        result = run_recursive_interview_chain(
                            tmp_path, project, [exp], questions, answers
                        )
                        assert len(result) == 2
                        assert result[0]["primary_question"] == "질문1"
                        assert result[0]["simulated_answer"] == "답변1"

    def test_without_prepared_answers(self, tmp_path: Path):
        from resume_agent.interview_engine import run_recursive_interview_chain
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        project = MagicMock()
        project.company_name = "테스트회사"
        project.job_title = "개발자"
        project.company_type = "대기업"
        project.research_notes = "전략적 노트"

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="테스트 행동을 수행했습니다.",
            result="테스트 결과입니다. 30% 향상 달성.",
            personal_contribution="개인 기여 설명",
            metrics="30% 향상",
            tags=["테스트"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        questions = ["질문1"]

        call_count = [0]

        def mock_codex(ws_root, prompt_text):
            call_count[0] += 1
            if call_count[0] == 1:
                return "시뮬레이션 답변"
            return "꼬리질문"

        with patch(
            "resume_agent.interview_engine._call_codex_simple", side_effect=mock_codex
        ):
            with patch("resume_agent.interview_engine.analyze_company") as mock_analyze:
                mock_analyze.return_value = MagicMock()
                with patch(
                    "resume_agent.interview_engine.build_role_industry_strategy_from_project"
                ) as mock_strategy:
                    mock_strategy.return_value = {"committee_personas": []}
                    with patch(
                        "resume_agent.interview_engine.load_success_cases",
                        return_value=[],
                    ):
                        with patch(
                            "resume_agent.interview_engine.json.dumps",
                            return_value="[]",
                        ):
                            result = run_recursive_interview_chain(
                                tmp_path, project, [exp], questions
                            )
                            assert len(result) == 1
                            assert result[0]["simulated_answer"] == "시뮬레이션 답변"

    def test_with_committee_personas(self, tmp_path: Path):
        from resume_agent.interview_engine import run_recursive_interview_chain
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        project = MagicMock()
        project.company_name = "테스트회사"
        project.job_title = "개발자"
        project.company_type = "대기업"
        project.research_notes = "전략적 노트"

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="테스트 행동을 수행했습니다.",
            result="테스트 결과입니다. 30% 향상 달성.",
            personal_contribution="개인 기여 설명",
            metrics="30% 향상",
            tags=["테스트"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        questions = ["질문1"]
        answers = ["답변1"]

        personas = [
            {"name": "위원장", "role": "종합 평가", "focus": ["논리성"]},
            {"name": "실무위원", "role": "실무 검증", "focus": ["기술력"]},
        ]

        with patch(
            "resume_agent.interview_engine._call_codex_simple", return_value="꼬리질문"
        ):
            with patch("resume_agent.interview_engine.analyze_company") as mock_analyze:
                mock_analyze.return_value = MagicMock()
                with patch(
                    "resume_agent.interview_engine.build_role_industry_strategy_from_project"
                ) as mock_strategy:
                    mock_strategy.return_value = {"committee_personas": personas}
                    with patch(
                        "resume_agent.interview_engine.load_success_cases",
                        return_value=[],
                    ):
                        result = run_recursive_interview_chain(
                            tmp_path, project, [exp], questions, answers
                        )
                        assert len(result) == 1
                        assert len(result[0]["committee_rounds"]) == 2

    def test_with_analysis_exception(self, tmp_path: Path):
        from resume_agent.interview_engine import run_recursive_interview_chain
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        project = MagicMock()
        project.company_name = "테스트회사"
        project.job_title = "개발자"
        project.company_type = "대기업"
        project.research_notes = "전략적 노트"

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="테스트 행동을 수행했습니다.",
            result="테스트 결과입니다. 30% 향상 달성.",
            personal_contribution="개인 기여 설명",
            metrics="30% 향상",
            tags=["테스트"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        questions = ["질문1"]
        answers = ["답변1"]

        with patch(
            "resume_agent.interview_engine._call_codex_simple", return_value="꼬리질문"
        ):
            with patch(
                "resume_agent.interview_engine.analyze_company",
                side_effect=Exception("분석 실패"),
            ):
                with patch(
                    "resume_agent.interview_engine.load_success_cases", return_value=[]
                ):
                    result = run_recursive_interview_chain(
                        tmp_path, project, [exp], questions, answers
                    )
                    assert len(result) == 1


class TestBuildCommitteeRounds:
    def test_empty_personas(self):
        from resume_agent.interview_engine import _build_committee_rounds

        result = _build_committee_rounds([], 0, "질문")
        assert result == []

    def test_with_personas(self):
        from resume_agent.interview_engine import _build_committee_rounds

        personas = [
            {"name": "위원장", "role": "종합 평가", "focus": ["논리성"]},
            {"name": "실무위원", "role": "실무 검증", "focus": ["기술력"]},
            {"name": "인사위원", "role": "인성 평가", "focus": ["협업"]},
        ]
        result = _build_committee_rounds(personas, 0, "질문")
        assert len(result) == 3
        assert result[0]["stance"] == "주질문 검증"
        assert result[1]["stance"] == "실무 적합성 검증"
        assert result[2]["stance"] == "리스크 및 반례 검증"


class TestPersonaReframeQuestion:
    def test_with_focus(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {"focus": ["논리성", "근거"]}
        result = _persona_reframe_question("원래 질문", persona)
        assert "논리성" in result
        assert "근거" in result

    def test_no_focus(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {}
        result = _persona_reframe_question("원래 질문", persona)
        assert result == "원래 질문"


class TestCallCodexSimple:
    def test_success(self, tmp_path: Path):
        from resume_agent.interview_engine import _call_codex_simple

        with patch("resume_agent.interview_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="[assistant] 테스트 응답",
                stderr="",
                returncode=0,
            )
            result = _call_codex_simple(tmp_path, "프롬프트")
            assert "테스트 응답" in result

    def test_failure(self, tmp_path: Path):
        from resume_agent.interview_engine import _call_codex_simple

        with patch("resume_agent.interview_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="에러",
                returncode=1,
            )
            result = _call_codex_simple(tmp_path, "프롬프트")
            assert "Error" in result
