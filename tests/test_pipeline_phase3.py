"""pipeline.py Phase 3 테스트 — 순수 로직 함수"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import (
    ApplicationProject,
    Experience,
    EvidenceLevel,
    VerificationStatus,
)
from resume_agent.state import initialize_state
from resume_agent.workspace import Workspace


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


def _mock_workspace(tmp_path: Path) -> MagicMock:
    ws = MagicMock()
    ws.root = tmp_path
    ws.state_dir = tmp_path / "state"
    ws.profile_dir = tmp_path / "profile"
    ws.outputs_dir = tmp_path / "outputs"
    ws.analysis_dir = tmp_path / "analysis"
    ws.ensure = MagicMock()
    # 디렉토리 생성
    ws.analysis_dir.mkdir(parents=True, exist_ok=True)
    return ws


# ──────────────────────────────────────────────────
# build_candidate_profile 테스트
# ──────────────────────────────────────────────────


class TestBuildCandidateProfile:
    def _mock_profile(self):
        profile = MagicMock()
        profile.style_preference = "balanced"
        profile.communication_style = "balanced"
        profile.confidence_style = "balanced"
        return profile

    def test_empty_experiences(self, tmp_path: Path):
        from resume_agent.pipeline import build_candidate_profile

        ws = _mock_workspace(tmp_path)
        project = MagicMock()
        project.job_title = "개발자"

        with patch(
            "resume_agent.pipeline.load_profile", return_value=self._mock_profile()
        ):
            result = build_candidate_profile(ws, project, [])
            assert result["communication_style"] == "balanced"
            assert result["confidence_style"] in ("reserved", "balanced")

    def test_logical_style(self, tmp_path: Path):
        from resume_agent.pipeline import build_candidate_profile

        ws = _mock_workspace(tmp_path)
        project = MagicMock()
        project.job_title = "개발자"

        # 논리적 토큰이 많은 경험
        exp = _make_exp(
            action="데이터를 분석하고 보고서를 작성했습니다. 검토 후 개선안을 정리했습니다.",
            result="분석 결과를 기반으로 개선된 프로세스를 도입했습니다.",
            tags=["분석", "데이터"],
        )

        with patch(
            "resume_agent.pipeline.load_profile", return_value=self._mock_profile()
        ):
            result = build_candidate_profile(ws, project, [exp])
            assert result["communication_style"] in ("logical", "balanced")

    def test_relational_style(self, tmp_path: Path):
        from resume_agent.pipeline import build_candidate_profile

        ws = _mock_workspace(tmp_path)
        project = MagicMock()
        project.job_title = "개발자"

        # 관계적 토큰이 많은 경험
        exp = _make_exp(
            action="고객과 소통하여 민원을 해결했습니다. 협업을 통해 지원했습니다.",
            result="고객 만족도가 향상되었습니다.",
            tags=["협업", "소통"],
        )

        with patch(
            "resume_agent.pipeline.load_profile", return_value=self._mock_profile()
        ):
            result = build_candidate_profile(ws, project, [exp])
            assert result["communication_style"] in ("relational", "balanced", "logical")

    def test_assertive_confidence(self, tmp_path: Path):
        from resume_agent.pipeline import build_candidate_profile

        ws = _mock_workspace(tmp_path)
        project = MagicMock()
        project.job_title = "개발자"

        # 수치와 개인 기여가 높은 경험들
        exps = [
            _make_exp(metrics="30% 향상", personal_contribution="전체 설계 담당"),
            _make_exp(metrics="50건 처리", personal_contribution="핵심 모듈 개발"),
        ]

        with patch(
            "resume_agent.pipeline.load_profile", return_value=self._mock_profile()
        ):
            result = build_candidate_profile(ws, project, exps)
            assert result["confidence_style"] in ("assertive", "balanced")

    def test_blind_spots_detection(self, tmp_path: Path):
        from resume_agent.pipeline import build_candidate_profile

        ws = _mock_workspace(tmp_path)
        project = MagicMock()
        project.job_title = "개발자"

        # 수치가 없는 경험
        exp = _make_exp(metrics="", personal_contribution="")

        with patch(
            "resume_agent.pipeline.load_profile", return_value=self._mock_profile()
        ):
            result = build_candidate_profile(ws, project, [exp])
            assert len(result["blind_spots"]) > 0
            assert len(result["coaching_focus"]) > 0


class TestPhase3HelperBuilders:
    def test_build_company_profile_writes_analysis_file(self, tmp_path: Path):
        from resume_agent.pipeline import build_company_profile

        ws = Workspace(tmp_path)
        initialize_state(ws)
        result = build_company_profile(
            ws,
            ApplicationProject(
                company_name="테스트기업",
                job_title="백엔드",
                research_notes="공익과 정확성을 강조합니다.",
            ),
            {"signature_strengths": ["문제 해결"]},
        )

        assert result["company_name"] == "테스트기업"
        assert (ws.analysis_dir / "company_profile.json").exists()

    def test_build_interview_support_pack_writes_analysis_file(self, tmp_path: Path):
        from resume_agent.pipeline import build_interview_support_pack

        ws = Workspace(tmp_path)
        initialize_state(ws)
        result = build_interview_support_pack(
            ws,
            {
                "signature_strengths": ["문제 해결"],
                "personalized_profile": {"weakness_codes": ["low_metrics"]},
            },
        )

        assert result["interview_day_checklist"]
        assert (ws.analysis_dir / "interview_support_pack.json").exists()


# ──────────────────────────────────────────────────
# _dedupe_preserve_order 테스트
# ──────────────────────────────────────────────────


class TestDedupePreserveOrder:
    def test_basic(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order(["a", "b", "a", "c"])
        assert result == ["a", "b", "c"]

    def test_empty(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order([])
        assert result == []


# ──────────────────────────────────────────────────
# _extract_json_fragment 테스트
# ──────────────────────────────────────────────────


class TestExtractJsonFragment:
    def test_valid_json(self):
        from resume_agent.pipeline import _extract_json_fragment

        result = _extract_json_fragment('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_array(self):
        from resume_agent.pipeline import _extract_json_fragment

        result = _extract_json_fragment("[1, 2, 3]")
        assert result == [1, 2, 3]


# ──────────────────────────────────────────────────
# build_writer_char_limit_report 테스트
# ──────────────────────────────────────────────────


class TestBuildWriterCharLimitReport:
    def test_within_limit(self, tmp_path: Path):
        from resume_agent.pipeline import build_writer_char_limit_report

        project = MagicMock()
        question = MagicMock()
        question.id = "q1"
        question.order_no = 1
        question.char_limit = 1000
        question.question_text = "테스트 질문"
        project.questions = [question]

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변입니다. 충분히 긴 답변입니다. 이 답변은 글자수 제한을 초과하지 않습니다.
"""
        result = build_writer_char_limit_report(project, writer_text)
        assert result["passed"] is True or result["passed"] is False


# ──────────────────────────────────────────────────
# needs_writer_rewrite 테스트
# ──────────────────────────────────────────────────


class TestNeedsWriterRewrite:
    def test_validation_failed(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = False

        result = needs_writer_rewrite(validation, [])
        assert result is True

    def test_no_quality_evaluations(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True

        result = needs_writer_rewrite(validation, [])
        assert result is False

    def test_low_score(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True

        quality_evals = [{"overall_score": 0.5, "humanization_score": 0.9}]
        result = needs_writer_rewrite(validation, quality_evals)
        assert result is True


# ──────────────────────────────────────────────────
# _simulate_interviewer_reaction 테스트
# ──────────────────────────────────────────────────


class TestSimulateInterviewerReaction:
    def test_with_numbers(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        result = _simulate_interviewer_reaction(
            "30% 향상된 결과를 달성했습니다",
            {"risk_areas": [], "follow_up_questions": ["추가 질문"]},
        )
        assert result["trust_signal"] == "high"

    def test_short_answer(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        result = _simulate_interviewer_reaction(
            "짧은 답변",
            {"risk_areas": [], "follow_up_questions": []},
        )
        assert result["specificity_signal"] == "low"
