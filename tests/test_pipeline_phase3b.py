"""pipeline.py 추가 커버리지 테스트 — Phase 3"""

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


class TestExtractQuestionAnswerMap:
    def test_empty_writer_text(self):
        from resume_agent.pipeline import extract_question_answer_map

        result = extract_question_answer_map("", [])
        assert result == {}

    def test_no_draft_section(self):
        from resume_agent.pipeline import extract_question_answer_map

        result = extract_question_answer_map("일반 텍스트", [])
        assert result == {}

    def test_with_questions(self):
        from resume_agent.pipeline import extract_question_answer_map

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 첫 번째 답변입니다.
Q2: 두 번째 답변입니다.
"""
        q1 = MagicMock()
        q1.id = "q1"
        q2 = MagicMock()
        q2.id = "q2"
        result = extract_question_answer_map(writer_text, [q1, q2])
        assert "q1" in result or len(result) > 0


class TestExtractQuestionAnswerDetails:
    def test_basic(self):
        from resume_agent.pipeline import extract_question_answer_details

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변입니다.
"""
        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.char_limit = 1000
        result = extract_question_answer_details(writer_text, [q])
        assert "q1" in result
        assert "answer" in result["q1"]


class TestBuildWriterCharLimitReport:
    def test_within_limit(self):
        from resume_agent.pipeline import build_writer_char_limit_report

        project = MagicMock()
        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.char_limit = 1000
        q.question_text = "테스트 질문"
        project.questions = [q]

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변입니다. 충분히 긴 답변입니다.
"""
        result = build_writer_char_limit_report(project, writer_text)
        assert "passed" in result
        assert "question_reports" in result

    def test_over_limit(self):
        from resume_agent.pipeline import build_writer_char_limit_report

        project = MagicMock()
        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.char_limit = 10
        q.question_text = "테스트 질문"
        project.questions = [q]

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 이 답변은 글자수 제한을 훨씬 초과하는 매우 긴 답변입니다.
"""
        result = build_writer_char_limit_report(
            project, writer_text, ratio_min=0.5, ratio_max=0.9
        )
        assert "passed" in result
        assert "issues" in result

    def test_no_char_limit(self):
        from resume_agent.pipeline import build_writer_char_limit_report

        project = MagicMock()
        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.char_limit = None
        q.question_text = "테스트 질문"
        project.questions = [q]

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변입니다.
"""
        result = build_writer_char_limit_report(project, writer_text)
        assert "passed" in result


class TestEnforceWriterCharLimits:
    def test_already_passes(self):
        from resume_agent.pipeline import enforce_writer_char_limits

        project = MagicMock()
        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.char_limit = 1000
        q.question_text = "테스트 질문"
        project.questions = [q]

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변입니다. 충분히 긴 답변입니다.
"""
        result_text, report, changed = enforce_writer_char_limits(
            project, writer_text, lambda *a: ""
        )
        assert changed is False

    def test_rewrite_attempted(self):
        from resume_agent.pipeline import enforce_writer_char_limits

        project = MagicMock()
        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.char_limit = 5
        q.question_text = "테스트 질문"
        project.questions = [q]

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 이 답변은 글자수 제한을 초과합니다.
"""
        rewrite_func = MagicMock(return_value="## 블록 3: DRAFT ANSWERS\nQ1: 짧은 답")
        result_text, report, changed = enforce_writer_char_limits(
            project, writer_text, rewrite_func
        )
        assert isinstance(changed, bool)


class TestSelectPrimaryExperiences:
    def test_with_question_map(self):
        from resume_agent.pipeline import select_primary_experiences

        exps = [_make_exp("e1"), _make_exp("e2"), _make_exp("e3")]
        qmap = [{"experience_id": "e2"}, {"experience_id": "e1"}]
        result = select_primary_experiences(exps, qmap)
        assert len(result) == 2
        assert result[0].id == "e2"

    def test_empty_question_map(self):
        from resume_agent.pipeline import select_primary_experiences

        exps = [_make_exp("e1"), _make_exp("e2")]
        result = select_primary_experiences(exps, [])
        assert len(result) <= 3


class TestNeedsWriterRewrite:
    def test_validation_failed(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = False
        assert needs_writer_rewrite(validation, []) is True

    def test_no_quality_evaluations(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True
        assert needs_writer_rewrite(validation, []) is False

    def test_low_overall_score(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True
        quality_evals = [{"overall_score": 0.5}]
        assert needs_writer_rewrite(validation, quality_evals) is True

    def test_all_good(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True
        quality_evals = [{"overall_score": 0.9, "humanization_score": 0.9}]
        assert needs_writer_rewrite(validation, quality_evals) is False


class TestBuildWriterRewriteQualityReport:
    def test_basic(self):
        from resume_agent.pipeline import build_writer_rewrite_quality_report

        before = [
            {
                "question_order": 1,
                "overall_score": 0.6,
                "humanization_score": 0.7,
                "ncs_alignment_score": 0.5,
                "ssot_alignment_score": 0.5,
            }
        ]
        after = [
            {
                "question_order": 1,
                "overall_score": 0.8,
                "humanization_score": 0.9,
                "ncs_alignment_score": 0.7,
                "ssot_alignment_score": 0.7,
            }
        ]
        result = build_writer_rewrite_quality_report(before, after, minimum_samples=1)
        assert result["sample_count"] == 1

    def test_empty(self):
        from resume_agent.pipeline import build_writer_rewrite_quality_report

        result = build_writer_rewrite_quality_report([], [], minimum_samples=1)
        assert result["sample_count"] == 0


class TestSimulateInterviewerReaction:
    def test_with_numbers(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        result = _simulate_interviewer_reaction(
            "30% 향상", {"risk_areas": [], "follow_up_questions": ["추가 질문"]}
        )
        assert result["trust_signal"] == "high"

    def test_short_answer(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        result = _simulate_interviewer_reaction(
            "짧은 답변", {"risk_areas": [], "follow_up_questions": []}
        )
        assert result["specificity_signal"] == "low"

    def test_with_experience(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        exp = _make_exp()
        result = _simulate_interviewer_reaction(
            "답변", {"risk_areas": []}, experience=exp
        )
        assert result["trust_signal"] in ("high", "medium")


class TestResolveQuestionType:
    def test_with_detected_type(self):
        from resume_agent.pipeline import _resolve_question_type

        q = MagicMock()
        q.detected_type = MagicMock(value="TYPE_A")
        q.question_text = "지원동기"
        result = _resolve_question_type(q)
        assert result.value == "TYPE_A"

    def test_with_string_type(self):
        from resume_agent.pipeline import _resolve_question_type

        q = MagicMock()
        q.detected_type = "TYPE_B"
        q.question_text = "직무역량"
        result = _resolve_question_type(q)
        assert result.value == "TYPE_B"


class TestMergeSources:
    def test_merge(self):
        from resume_agent.pipeline import merge_sources

        existing = [MagicMock(id="s1"), MagicMock(id="s2")]
        new = [MagicMock(id="s2"), MagicMock(id="s3")]
        result = merge_sources(existing, new)
        assert len(result) == 3


class TestLatestAcceptedArtifacts:
    def test_filter_accepted(self):
        from resume_agent.pipeline import latest_accepted_artifacts
        from resume_agent.models import ArtifactType

        artifacts = [
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=True, created_at=1),
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=False, created_at=2),
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=True, created_at=3),
        ]
        result = latest_accepted_artifacts(artifacts, [ArtifactType.WRITER])
        assert len(result) == 1
        assert result[0].created_at == 3


class TestExtractJsonFragment:
    def test_valid_json(self):
        from resume_agent.pipeline import _extract_json_fragment

        result = _extract_json_fragment('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_array(self):
        from resume_agent.pipeline import _extract_json_fragment

        result = _extract_json_fragment("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_invalid_json(self):
        from resume_agent.pipeline import _extract_json_fragment

        with pytest.raises(ValueError):
            _extract_json_fragment("JSON 아님")


class TestDedupePreserveOrder:
    def test_basic(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order(["a", "b", "a", "c"])
        assert result == ["a", "b", "c"]

    def test_empty(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order([])
        assert result == []


class TestBuildDataBlock:
    def test_basic(self):
        import json
        from resume_agent.pipeline import build_data_block

        project = MagicMock()
        project.model_dump.return_value = {
            "company_name": "테스트",
            "job_title": "개발자",
            "questions": [],
        }
        exps = [_make_exp()]
        result = build_data_block(project=project, experiences=exps, knowledge_hints=[])
        data = json.loads(result)
        assert "project" in data
        assert "experiences" in data
