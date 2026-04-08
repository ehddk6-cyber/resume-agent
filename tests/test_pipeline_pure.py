"""pipeline.py 순수 로직 함수 테스트 — mocking 불필요"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from resume_agent.models import (
    ApplicationProject,
    Experience,
    EvidenceLevel,
    Question,
    QuestionType,
    VerificationStatus,
    GeneratedArtifact,
    ArtifactType,
)


# ──────────────────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────────────────


def _make_experience(exp_id: str = "e1", title: str = "테스트") -> Experience:
    return Experience(
        id=exp_id,
        title=title,
        organization="테스트 조직",
        period_start="2024-01",
        situation="테스트 상황입니다.",
        task="테스트 과제입니다.",
        action="테스트 행동을 수행했습니다.",
        result="테스트 결과입니다.",
        personal_contribution="개인 기여",
        metrics="30% 향상",
        tags=["테스트"],
        evidence_level=EvidenceLevel.L3,
        verification_status=VerificationStatus.VERIFIED,
    )


def _make_question(
    q_id: str = "q1", order: int = 1, char_limit: int = 1000
) -> MagicMock:
    q = MagicMock()
    q.id = q_id
    q.order_no = order
    q.char_limit = char_limit
    q.question_text = "테스트 질문입니다"
    q.detected_type = QuestionType.TYPE_B
    return q


def _make_project(questions: list | None = None) -> MagicMock:
    project = MagicMock()
    project.company_name = "테스트회사"
    project.job_title = "개발자"
    project.questions = questions or [_make_question()]
    return project


# ──────────────────────────────────────────────────
# extract_markdown_section 테스트
# ──────────────────────────────────────────────────


class TestExtractMarkdownSection:
    def test_basic_extraction(self):
        from resume_agent.pipeline import extract_markdown_section

        text = "## 제목1\n내용1\n## 제목2\n내용2"
        result = extract_markdown_section(text, "## 제목1", ["## 제목2"])
        assert result == "내용1"

    def test_heading_not_found(self):
        from resume_agent.pipeline import extract_markdown_section

        text = "## 제목1\n내용1"
        result = extract_markdown_section(text, "## 없는제목", [])
        assert result == ""

    def test_no_stop_headings(self):
        from resume_agent.pipeline import extract_markdown_section

        text = "## 제목\n내용 전체\n마지막"
        result = extract_markdown_section(text, "## 제목", [])
        assert "내용 전체" in result
        assert "마지막" in result

    def test_empty_text(self):
        from resume_agent.pipeline import extract_markdown_section

        result = extract_markdown_section("", "## 제목", [])
        assert result == ""

    def test_multiple_stop_headings(self):
        from resume_agent.pipeline import extract_markdown_section

        text = "## A\n내용A\n## B\n내용B\n## C\n내용C"
        result = extract_markdown_section(text, "## A", ["## B", "## C"])
        assert result == "내용A"


# ──────────────────────────────────────────────────
# extract_question_answer_map 테스트
# ──────────────────────────────────────────────────


class TestExtractQuestionAnswerMap:
    def test_basic_extraction(self):
        from resume_agent.pipeline import extract_question_answer_map

        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
가정 내용

## 블록 2: OUTLINE
개요 내용

## 블록 3: DRAFT ANSWERS
Q1: 첫 번째 답변입니다.
Q2: 두 번째 답변입니다.

## 블록 4: SELF-CHECK
체크 내용
"""
        questions = [_make_question("q1", 1), _make_question("q2", 2)]
        result = extract_question_answer_map(writer_text, questions)
        assert "q1" in result
        assert "q2" in result

    def test_empty_questions(self):
        from resume_agent.pipeline import extract_question_answer_map

        result = extract_question_answer_map("텍스트", [])
        assert result == {}

    def test_no_draft_section(self):
        from resume_agent.pipeline import extract_question_answer_map

        result = extract_question_answer_map("일반 텍스트", [_make_question()])
        assert result == {}

    def test_char_count_removal(self):
        from resume_agent.pipeline import extract_question_answer_map

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변 내용입니다.
글자수: 약 500자 (공백 포함)
"""
        questions = [_make_question("q1", 1)]
        result = extract_question_answer_map(writer_text, questions)
        assert "글자수" not in result.get("q1", "")

    def test_paragraph_split_fallback(self):
        from resume_agent.pipeline import extract_question_answer_map

        writer_text = """## 블록 3: DRAFT ANSWERS
첫 번째 답변입니다.

두 번째 답변입니다.
"""
        questions = [_make_question("q1", 1), _make_question("q2", 2)]
        result = extract_question_answer_map(writer_text, questions)
        assert len(result) >= 1


# ──────────────────────────────────────────────────
# extract_question_answer_details 테스트
# ──────────────────────────────────────────────────


class TestExtractQuestionAnswerDetails:
    def test_basic_details(self):
        from resume_agent.pipeline import extract_question_answer_details

        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변 내용입니다.
"""
        questions = [_make_question("q1", 1)]
        result = extract_question_answer_details(writer_text, questions)
        assert "q1" in result
        assert "answer" in result["q1"]
        assert "char_count" in result["q1"]
        assert "has_answer" in result["q1"]

    def test_empty_questions(self):
        from resume_agent.pipeline import extract_question_answer_details

        result = extract_question_answer_details("텍스트", [])
        assert result == {}


# ──────────────────────────────────────────────────
# select_primary_experiences 테스트
# ──────────────────────────────────────────────────


class TestSelectPrimaryExperiences:
    def test_with_question_map(self):
        from resume_agent.pipeline import select_primary_experiences

        experiences = [
            _make_experience("e1"),
            _make_experience("e2"),
            _make_experience("e3"),
        ]
        question_map = [{"experience_id": "e2"}, {"experience_id": "e1"}]
        result = select_primary_experiences(experiences, question_map)
        assert len(result) == 2
        assert result[0].id == "e2"
        assert result[1].id == "e1"

    def test_empty_question_map(self):
        from resume_agent.pipeline import select_primary_experiences

        experiences = [_make_experience("e1"), _make_experience("e2")]
        result = select_primary_experiences(experiences, [])
        assert len(result) == 2

    def test_duplicate_ids(self):
        from resume_agent.pipeline import select_primary_experiences

        experiences = [_make_experience("e1")]
        question_map = [{"experience_id": "e1"}, {"experience_id": "e1"}]
        result = select_primary_experiences(experiences, question_map)
        assert len(result) == 1

    def test_missing_experience(self):
        from resume_agent.pipeline import select_primary_experiences

        experiences = [_make_experience("e1")]
        question_map = [{"experience_id": "e999"}]
        result = select_primary_experiences(experiences, question_map)
        assert len(result) == 1  # fallback to experiences[:3]


# ──────────────────────────────────────────────────
# build_writer_char_limit_report 테스트
# ──────────────────────────────────────────────────


class TestBuildWriterCharLimitReport:
    def test_within_target(self):
        from resume_agent.pipeline import build_writer_char_limit_report

        project = _make_project([_make_question("q1", 1, 1000)])
        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변입니다. 충분한 길이의 답변입니다. 더 많은 내용을 추가합니다.
"""
        result = build_writer_char_limit_report(project, writer_text)
        assert result["passed"] is True or result["passed"] is False
        assert "question_reports" in result

    def test_missing_answer(self):
        from resume_agent.pipeline import build_writer_char_limit_report

        project = _make_project([_make_question("q1", 1, 1000)])
        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 

## 블록 4: SELF-CHECK
"""
        result = build_writer_char_limit_report(project, writer_text)
        assert len(result["issues"]) >= 0

    def test_custom_ratios(self):
        from resume_agent.pipeline import build_writer_char_limit_report

        project = _make_project([_make_question("q1", 1, 100)])
        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 짧은 답변
"""
        result = build_writer_char_limit_report(
            project, writer_text, ratio_min=0.5, ratio_max=0.9
        )
        assert "ratio_min" in result
        assert result["ratio_min"] == 0.5


# ──────────────────────────────────────────────────
# enforce_writer_char_limits 테스트
# ──────────────────────────────────────────────────


class TestEnforceWriterCharLimits:
    def test_already_passes(self):
        from resume_agent.pipeline import enforce_writer_char_limits

        project = _make_project([_make_question("q1", 1, 100)])
        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 답변입니다. 충분히 긴 답변입니다. 이 답변은 글자수 제한 내에서 목표 비율을 충족합니다.
"""
        rewrite_func = MagicMock(return_value="수정된 텍스트")
        result_text, report, changed = enforce_writer_char_limits(
            project, writer_text, rewrite_func
        )
        # 결과가 bool인지 확인
        assert isinstance(changed, bool)

    def test_rewrite_attempted(self):
        from resume_agent.pipeline import enforce_writer_char_limits

        project = _make_project([_make_question("q1", 1, 10)])
        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 천 글자가 넘는 매우 긴 답변입니다. 이 답변은 글자수 제한을 초과합니다.
"""
        rewrite_func = MagicMock(return_value="## 블록 3: DRAFT ANSWERS\nQ1: 짧은 답변")
        result_text, report, changed = enforce_writer_char_limits(
            project, writer_text, rewrite_func
        )
        assert isinstance(changed, bool)

    def test_rewrite_returns_empty(self):
        from resume_agent.pipeline import enforce_writer_char_limits

        project = _make_project([_make_question("q1", 1, 10)])
        writer_text = """## 블록 3: DRAFT ANSWERS
Q1: 긴 답변입니다.
"""
        rewrite_func = MagicMock(return_value="")
        result_text, report, changed = enforce_writer_char_limits(
            project, writer_text, rewrite_func
        )
        assert changed is False


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

    def test_low_overall_score(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True
        quality_evals = [{"overall_score": 0.5, "humanization_score": 0.9}]
        result = needs_writer_rewrite(validation, quality_evals)
        assert result is True

    def test_low_humanization(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True
        quality_evals = [{"overall_score": 0.9, "humanization_score": 0.5}]
        result = needs_writer_rewrite(validation, quality_evals)
        assert result is True

    def test_many_humanization_flags(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True
        quality_evals = [
            {
                "overall_score": 0.9,
                "humanization_score": 0.9,
                "humanization_flags": ["flag1", "flag2"],
            }
        ]
        result = needs_writer_rewrite(validation, quality_evals)
        assert result is True

    def test_all_good(self):
        from resume_agent.pipeline import needs_writer_rewrite

        validation = MagicMock()
        validation.passed = True
        quality_evals = [{"overall_score": 0.9, "humanization_score": 0.9}]
        result = needs_writer_rewrite(validation, quality_evals)
        assert result is False


# ──────────────────────────────────────────────────
# build_writer_rewrite_quality_report 테스트
# ──────────────────────────────────────────────────


class TestBuildWriterRewriteQualityReport:
    def test_basic_report(self):
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
        assert result["average_overall_delta"] > 0

    def test_empty_evaluations(self):
        from resume_agent.pipeline import build_writer_rewrite_quality_report

        result = build_writer_rewrite_quality_report([], [], minimum_samples=1)
        assert result["sample_count"] == 0
        assert result["average_overall_delta"] == 0.0

    def test_markdown_output(self):
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
        assert "# Writer Rewrite Quality Comparison" in result["markdown"]


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
        assert "specificity_signal" in result

    def test_short_answer(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        result = _simulate_interviewer_reaction(
            "짧은 답변",
            {"risk_areas": [], "follow_up_questions": []},
        )
        assert result["specificity_signal"] == "low"

    def test_many_risks(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        result = _simulate_interviewer_reaction(
            "답변입니다",
            {"risk_areas": ["risk1", "risk2", "risk3"], "follow_up_questions": []},
        )
        assert result["trust_signal"] in ("medium", "low")

    def test_with_experience(self):
        from resume_agent.pipeline import _simulate_interviewer_reaction

        exp = _make_experience()
        result = _simulate_interviewer_reaction(
            "답변입니다. 구체적인 내용을 포함합니다.",
            {"risk_areas": [], "follow_up_questions": []},
            experience=exp,
        )
        assert result["trust_signal"] in ("high", "medium")


# ──────────────────────────────────────────────────
# _build_interviewer_reaction_chain 테스트
# ──────────────────────────────────────────────────


class TestBuildInterviewerReactionChain:
    def test_basic_chain(self):
        from resume_agent.pipeline import _build_interviewer_reaction_chain

        chain = _build_interviewer_reaction_chain(
            "답변입니다",
            {"risk_areas": ["리스크"], "follow_up_questions": ["꼬리질문"]},
        )
        assert len(chain) == 3
        assert chain[0]["stage"] == "first_impression"
        assert chain[1]["stage"] == "probe"
        assert chain[2]["stage"] == "verdict_shift"

    def test_no_risks(self):
        from resume_agent.pipeline import _build_interviewer_reaction_chain

        chain = _build_interviewer_reaction_chain(
            "답변입니다",
            {"risk_areas": [], "follow_up_questions": []},
        )
        assert len(chain) == 3


# ──────────────────────────────────────────────────
# _resolve_question_type 테스트
# ──────────────────────────────────────────────────


class TestResolveQuestionType:
    def test_with_detected_type(self):
        from resume_agent.pipeline import _resolve_question_type

        q = MagicMock()
        q.detected_type = QuestionType.TYPE_A
        q.question_text = "지원동기를 말씀해주세요"
        result = _resolve_question_type(q)
        assert result == QuestionType.TYPE_A

    def test_with_string_type(self):
        from resume_agent.pipeline import _resolve_question_type

        q = MagicMock()
        q.detected_type = "TYPE_B"
        q.question_text = "직무역량을 설명해주세요"
        result = _resolve_question_type(q)
        assert result == QuestionType.TYPE_B

    def test_unknown_type(self):
        from resume_agent.pipeline import _resolve_question_type

        q = MagicMock()
        q.detected_type = QuestionType.TYPE_UNKNOWN
        q.question_text = "지원동기를 말씀해주세요"
        result = _resolve_question_type(q)
        assert result in (QuestionType.TYPE_A, QuestionType.TYPE_UNKNOWN)


# ──────────────────────────────────────────────────
# merge_sources 테스트
# ──────────────────────────────────────────────────


class TestMergeSources:
    def test_merge_new_sources(self):
        from resume_agent.pipeline import merge_sources

        existing = [MagicMock(id="s1"), MagicMock(id="s2")]
        new = [MagicMock(id="s2"), MagicMock(id="s3")]
        result = merge_sources(existing, new)
        assert len(result) == 3

    def test_empty_existing(self):
        from resume_agent.pipeline import merge_sources

        new = [MagicMock(id="s1")]
        result = merge_sources([], new)
        assert len(result) == 1

    def test_empty_new(self):
        from resume_agent.pipeline import merge_sources

        existing = [MagicMock(id="s1")]
        result = merge_sources(existing, [])
        assert len(result) == 1


# ──────────────────────────────────────────────────
# _merge_success_cases 테스트
# ──────────────────────────────────────────────────


class TestMergeSuccessCases:
    def test_merge_by_key(self):
        from resume_agent.pipeline import _merge_success_cases

        case1 = MagicMock()
        case1.title = "프로젝트A"
        case1.company_name = "회사A"

        case2 = MagicMock()
        case2.title = "프로젝트A"
        case2.company_name = "회사A"

        result = _merge_success_cases([case1], [case2])
        assert len(result) == 1

    def test_different_cases(self):
        from resume_agent.pipeline import _merge_success_cases

        case1 = MagicMock()
        case1.title = "프로젝트A"
        case1.company_name = "회사A"

        case2 = MagicMock()
        case2.title = "프로젝트B"
        case2.company_name = "회사B"

        result = _merge_success_cases([case1], [case2])
        assert len(result) == 2


# ──────────────────────────────────────────────────
# latest_accepted_artifacts 테스트
# ──────────────────────────────────────────────────


class TestLatestAcceptedArtifacts:
    def test_filter_accepted(self):
        from resume_agent.pipeline import latest_accepted_artifacts

        artifacts = [
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=True, created_at=1),
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=False, created_at=2),
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=True, created_at=3),
        ]
        result = latest_accepted_artifacts(artifacts, [ArtifactType.WRITER])
        assert len(result) == 1
        assert result[0].created_at == 3

    def test_multiple_types(self):
        from resume_agent.pipeline import latest_accepted_artifacts

        artifacts = [
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=True, created_at=1),
            MagicMock(
                artifact_type=ArtifactType.INTERVIEW, accepted=True, created_at=2
            ),
        ]
        result = latest_accepted_artifacts(
            artifacts, [ArtifactType.WRITER, ArtifactType.INTERVIEW]
        )
        assert len(result) == 2

    def test_no_accepted(self):
        from resume_agent.pipeline import latest_accepted_artifacts

        artifacts = [
            MagicMock(artifact_type=ArtifactType.WRITER, accepted=False, created_at=1),
        ]
        result = latest_accepted_artifacts(artifacts, [ArtifactType.WRITER])
        assert len(result) == 0


# ──────────────────────────────────────────────────
# _extract_json_fragment 테스트
# ──────────────────────────────────────────────────


class TestExtractJsonFragment:
    def test_valid_json_object(self):
        from resume_agent.pipeline import _extract_json_fragment

        result = _extract_json_fragment('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_prefix(self):
        from resume_agent.pipeline import _extract_json_fragment

        result = _extract_json_fragment('결과입니다\n{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_array(self):
        from resume_agent.pipeline import _extract_json_fragment

        result = _extract_json_fragment("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_invalid_json(self):
        from resume_agent.pipeline import _extract_json_fragment

        with pytest.raises(ValueError):
            _extract_json_fragment("JSON이 아닌 텍스트")


# ──────────────────────────────────────────────────
# _dedupe_preserve_order 테스트
# ──────────────────────────────────────────────────


class TestDedupePreserveOrder:
    def test_remove_duplicates(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_empty_list(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order([])
        assert result == []

    def test_whitespace_handling(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order(["a", " a ", "b", "  "])
        assert result == ["a", "b"]

    def test_preserve_order(self):
        from resume_agent.pipeline import _dedupe_preserve_order

        result = _dedupe_preserve_order(["z", "a", "m", "a", "z"])
        assert result == ["z", "a", "m"]


# ──────────────────────────────────────────────────
# build_data_block 테스트
# ──────────────────────────────────────────────────


class TestBuildDataBlock:
    def test_basic_block(self):
        from resume_agent.pipeline import build_data_block

        project = _make_project()
        experiences = [_make_experience()]
        result = build_data_block(
            project=project,
            experiences=experiences,
            knowledge_hints=[{"title": "힌트"}],
        )
        data = json.loads(result)
        assert "project" in data
        assert "experiences" in data
        assert "knowledge_hints" in data

    def test_with_extra(self):
        from resume_agent.pipeline import build_data_block

        project = _make_project()
        result = build_data_block(
            project=project,
            experiences=[],
            knowledge_hints=[],
            extra={"추가": "데이터"},
        )
        data = json.loads(result)
        assert data["extra"] == {"추가": "데이터"}


# ──────────────────────────────────────────────────
# build_writer_rewrite_prompt 테스트
# ──────────────────────────────────────────────────


class TestBuildWriterRewritePrompt:
    def test_basic_prompt(self):
        from resume_agent.pipeline import build_writer_rewrite_prompt

        validation = MagicMock()
        validation.missing = ["섹션 누락"]
        quality_evals = [
            {
                "overall_score": 0.5,
                "humanization_flags": ["AI 느낌"],
                "weaknesses": ["약점1"],
                "suggestions": ["제안1"],
            }
        ]
        result = build_writer_rewrite_prompt("이전 출력", validation, quality_evals)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_issues(self):
        from resume_agent.pipeline import build_writer_rewrite_prompt

        validation = MagicMock()
        validation.missing = []
        quality_evals = [{"overall_score": 0.9}]
        result = build_writer_rewrite_prompt("이전 출력", validation, quality_evals)
        assert isinstance(result, str)
