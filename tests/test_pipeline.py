"""파이프라인 핵심 함수 테스트"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from resume_agent.pipeline import (
    normalize_contract_output,
    build_data_block,
    timestamp_slug,
    slugify,
    latest_accepted_artifacts,
    build_exec_prompt,
    extract_last_codex_message,
    select_primary_experiences,
    read_json_if_exists,
    safe_read_text,
    relative,
    extract_question_answer_map,
    needs_writer_rewrite,
    build_writer_rewrite_prompt,
    build_writer_rewrite_quality_report,
    build_writer_quality_evaluations,
    should_accept_writer_rewrite,
    build_interview_defense_simulations,
    build_experience_competition_report,
    build_writer_differentiation_report,
    build_adaptive_strategy_layer,
    build_feedback_adaptation_plan,
    build_outcome_dashboard,
    build_kpi_dashboard,
    build_writer_result_quality_evaluations,
    build_coach_prompt,
    build_interview_prompt,
    build_research_strategy_translation,
    _assess_recent_change_action_coverage,
    _assess_recent_change_priority_rule_coverage,
    build_self_intro_pack,
    run_coach,
    run_writer,
    run_writer_with_codex,
    run_interview_with_codex,
    run_self_intro,
    build_ncs_profile,
    classify_project_questions_with_llm_fallback,
    build_source_grading,
    build_live_source_update_summary,
    build_feedback_learning_context,
    build_blind_benchmark_frame,
    extract_question_answer_details,
    build_writer_char_limit_report,
    enforce_writer_char_limits,
    enforce_patina_char_limits,
    update_application_strategy,
)
from resume_agent.scoring import allocate_experiences
from resume_agent.models import (
    ApplicationProject,
    ArtifactType,
    Experience,
    GeneratedArtifact,
    ValidationResult,
    EvidenceLevel,
    KnowledgeSource,
    KnowledgeSourceMeta,
    Question,
    QuestionType,
    SourceType,
)
from resume_agent.domain import build_knowledge_hints, build_question_specific_knowledge_hints
from datetime import datetime, timezone
from pathlib import Path

from resume_agent.state import (
    initialize_state,
    save_knowledge_sources,
    save_project,
    write_json,
    load_live_source_cache,
)
from resume_agent.workspace import Workspace
from resume_agent.parsing import ingest_source_file


class TestNormalizeContractOutput:
    def test_extracts_from_primary_heading(self):
        text = "noise\n## 블록 1: A\ncontent here\n## 블록 2: B"
        result = normalize_contract_output(text, ["## 블록 1: A", "## 블록 2: B"])
        assert result.startswith("## 블록 1: A")
        assert "content here" in result

    def test_returns_stripped_text_when_no_headings_found(self):
        text = "some random text without headings"
        result = normalize_contract_output(text, ["## MISSING"])
        assert result == "some random text without headings"

    def test_empty_text_returns_empty(self):
        assert normalize_contract_output("", ["## X"]) == ""

    def test_falls_back_to_earliest_heading(self):
        text = "prefix\n## 블록 2: B\ncontent\n## 블록 1: A\nmore"
        result = normalize_contract_output(text, ["## 블록 1: A", "## 블록 2: B"])
        # rfind returns last position; min of last positions is the earlier block
        assert "## 블록 2: B" in result or "## 블록 1: A" in result


class TestBuildDataBlock:
    def test_returns_valid_json(self):
        project = ApplicationProject(company_name="TestCo", job_title="Engineer")
        result = build_data_block(project=project, experiences=[], knowledge_hints=[])
        data = json.loads(result)
        assert data["project"]["company_name"] == "TestCo"

    def test_includes_extra_fields(self):
        project = ApplicationProject()
        result = build_data_block(
            project=project, experiences=[], knowledge_hints=[], extra={"key": "val"}
        )
        data = json.loads(result)
        assert data["extra"]["key"] == "val"


class TestTimestampSlug:
    def test_format(self):
        slug = timestamp_slug()
        assert len(slug) == 15
        assert slug[8] == "_"

    def test_is_utc(self):
        slug = timestamp_slug()
        now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        assert slug[:8] == now[:8]


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Test!@#$%") == "test"

    def test_truncates_long(self):
        long = "a" * 100
        assert len(slugify(long)) <= 80

    def test_empty_returns_source(self):
        assert slugify("---") == "source"


class TestLatestAcceptedArtifacts:
    def test_returns_latest_per_type(self):
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        artifacts = [
            GeneratedArtifact(
                id="a1",
                artifact_type=ArtifactType.WRITER,
                accepted=True,
                output_path="a1",
                raw_output_path="a1",
                created_at=t1,
            ),
            GeneratedArtifact(
                id="a2",
                artifact_type=ArtifactType.WRITER,
                accepted=True,
                output_path="a2",
                raw_output_path="a2",
                created_at=t2,
            ),
        ]
        result = latest_accepted_artifacts(artifacts, [ArtifactType.WRITER])
        assert len(result) == 1
        assert result[0].id == "a2"

    def test_skips_rejected(self):
        artifacts = [
            GeneratedArtifact(
                id="r1",
                artifact_type=ArtifactType.WRITER,
                accepted=False,
                output_path="r1",
                raw_output_path="r1",
                created_at=datetime.now(timezone.utc),
            ),
        ]
        result = latest_accepted_artifacts(artifacts, [ArtifactType.WRITER])
        assert len(result) == 0


class TestBuildExecPrompt:
    def test_wraps_prompt(self):
        result = build_exec_prompt("test prompt")
        assert "test prompt" in result
        assert "Return only the final answer" in result


class TestExtractLastCodexMessage:
    def test_extracts_after_marker(self):
        stdout = "noise\ncodex\nactual answer"
        assert extract_last_codex_message(stdout) == "actual answer"

    def test_no_marker_returns_full(self):
        assert extract_last_codex_message("full text") == "full text"


class TestSelectPrimaryExperiences:
    def test_returns_first_3_when_no_map(self):
        experiences = [
            Experience(
                id=f"e{i}",
                title=f"Exp {i}",
                organization="Org",
                period_start="2024-01-01",
                situation="s",
                task="t",
                action="a",
                result="r",
            )
            for i in range(5)
        ]
        result = select_primary_experiences(experiences, [])
        assert len(result) == 3

    def test_selects_by_map(self):
        experiences = [
            Experience(
                id="e1",
                title="E1",
                organization="Org",
                period_start="2024-01-01",
                situation="s",
                task="t",
                action="a",
                result="r",
            ),
            Experience(
                id="e2",
                title="E2",
                organization="Org",
                period_start="2024-01-01",
                situation="s",
                task="t",
                action="a",
                result="r",
            ),
        ]
        qmap = [{"experience_id": "e2"}]
        result = select_primary_experiences(experiences, qmap)
        assert len(result) == 1
        assert result[0].id == "e2"


class TestExtractQuestionAnswerMap:
    def test_extracts_answers_by_question_order_markers(self):
        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
Q1: 첫 번째 답변입니다.
글자수: 약 120 자 (공백 포함) / 제한 대비 80%

Q2: 두 번째 답변입니다.
글자수: 약 130 자 (공백 포함) / 제한 대비 86%

## 블록 4: SELF-CHECK
- PASS
"""
        questions = [
            Question(id="q1", order_no=1, question_text="첫 질문"),
            Question(id="q2", order_no=2, question_text="둘째 질문"),
        ]

        result = extract_question_answer_map(writer_text, questions)

        assert result["q1"] == "첫 번째 답변입니다."
        assert result["q2"] == "두 번째 답변입니다."


class TestCoachReasoning:
    def test_allocate_experiences_reason_explains_fit_and_risk(self):
        question = Question(
            id="q1",
            order_no=1,
            question_text="지원동기와 직무 적합성을 설명하세요.",
        )
        experience = Experience(
            id="exp1",
            title="국민연금 민원 규정 설명",
            organization="국민연금공단",
            period_start="2024-01-01",
            situation="민원인이 기준소득월액 변경 특례 제도를 이해하지 못함",
            task="규정과 서류 기준을 설명하고 민원을 안정적으로 처리",
            action="규정을 쉬운 언어로 재구성해 안내하고 필요한 서류를 재확인함",
            result="민원인이 처리 기준을 이해하고 재방문 문의를 줄임",
            evidence_text="민원 응대 메모와 처리 기록",
            metrics="반복 문의 메모 12건 정리",
            tags=["고객응대", "직무역량", "의사소통"],
        )

        allocations = allocate_experiences([question], [experience], [])

        assert "질문 기대:" in allocations[0]["reason"]
        assert "이 경험의 강점:" in allocations[0]["reason"]
        assert "면접관 꼬리질문:" in allocations[0]["reason"]


class TestWriterRewriteHelpers:
    def test_needs_writer_rewrite_when_quality_is_low(self):
        validation = ValidationResult(passed=True)
        quality = [{"overall_score": 0.61}]

        assert needs_writer_rewrite(validation, quality) is True

    def test_needs_writer_rewrite_when_humanization_is_low(self):
        validation = ValidationResult(passed=True)
        quality = [
            {
                "overall_score": 0.9,
                "humanization_score": 0.6,
                "humanization_flags": ["기계적 도입부", "클리셰 표현"],
            }
        ]

        assert needs_writer_rewrite(validation, quality) is True

    def test_needs_writer_rewrite_when_strategy_axes_are_weak(self):
        validation = ValidationResult(passed=True)
        quality = [
            {
                "overall_score": 0.88,
                "humanization_score": 0.9,
                "humanization_flags": [],
                "differentiation_score": 0.5,
                "committee_reaction_score": 0.55,
                "committee_attack_points": ["개인 판단 기준이 모호함"],
                "message_discipline_score": 0.6,
                "cliche_score": 0.6,
                "cliche_flags": ["성장", "노력", "배움"],
            }
        ]

        assert needs_writer_rewrite(validation, quality) is True

    def test_needs_writer_rewrite_when_priority_rule_coverage_is_low(self):
        validation = ValidationResult(passed=True)
        quality = [{"overall_score": 0.9, "humanization_score": 0.9}]
        result_quality = [{"overall": 0.9}]

        assert (
            needs_writer_rewrite(
                validation,
                quality,
                result_quality,
                {
                    "checked_count": 1,
                    "covered_count": 0,
                    "missing_count": 1,
                    "coverage_rate": 0.0,
                },
            )
            is True
        )

    def test_build_writer_rewrite_prompt_includes_validation_and_feedback(self):
        validation = ValidationResult(passed=False, missing=["문항별 글자수 표기"])
        quality = [
            {
                "question_order": 1,
                "overall_score": 0.6,
                "weaknesses": ["정량적 성과 표현이 부족합니다"],
                "suggestions": ["구체적인 수치를 추가하세요"],
            }
        ]

        prompt = build_writer_rewrite_prompt("이전 출력", validation, quality)
        assert "문항별 글자수 표기" in prompt
        assert "Q1 품질점수 0.60" in prompt
        assert "구체적인 수치를 추가하세요" in prompt

    def test_build_writer_rewrite_prompt_includes_result_quality_guidance(self):
        validation = ValidationResult(passed=True, missing=[])
        quality = [{"question_order": 1, "overall_score": 0.8, "weaknesses": [], "suggestions": []}]
        result_quality = [
            {
                "question_order": 1,
                "overall": 0.68,
                "details": {
                    "persuasiveness": 0.62,
                    "defensibility": 0.81,
                    "company_fit": 0.55,
                },
                "suggestions": ["회사 연결 문장을 첫 문장으로 당기세요."],
            }
        ]

        prompt = build_writer_rewrite_prompt(
            "이전 출력",
            validation,
            quality,
            result_quality_evaluations=result_quality,
        )

        assert "Q1 결과중심 품질 0.68" in prompt
        assert "persuasiveness=0.62" in prompt
        assert "회사 연결 문장을 첫 문장으로 당기세요." in prompt

    def test_build_writer_rewrite_prompt_includes_adaptation_actions(self):
        validation = ValidationResult(passed=True, missing=[])
        quality = [{"question_order": 1, "overall_score": 0.8, "weaknesses": [], "suggestions": []}]

        prompt = build_writer_rewrite_prompt(
            "이전 출력",
            validation,
            quality,
            feedback_learning={
                "adaptation_plan": {
                    "focus_actions": ["반복 탈락 사유 '근거 부족' 보강"]
                }
            },
        )

        assert "학습 루프 우선 과제" in prompt
        assert "근거 부족" in prompt

    def test_should_accept_writer_rewrite_uses_result_quality_when_overall_tied(self):
        validation = ValidationResult(passed=True, missing=[])
        current_quality = [{"overall_score": 0.8}]
        candidate_quality = [{"overall_score": 0.8}]
        current_result_quality = [{"overall": 0.62}]
        candidate_result_quality = [{"overall": 0.74}]

        accepted = should_accept_writer_rewrite(
            validation,
            current_quality,
            candidate_quality,
            current_result_quality,
            candidate_result_quality,
        )

        assert accepted is True


class TestWriterCharLimitEnforcement:
    def test_extract_question_answer_details_counts_spaces_in_body(self):
        writer_text = """
## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
Q1: 첫 번째 답변 입니다.
글자수: 약 9 자 (공백 포함) / 제한 대비 90%

## 블록 4: SELF-CHECK
- PASS
"""
        questions = [
            Question(id="q1", order_no=1, question_text="첫 질문", char_limit=10)
        ]

        details = extract_question_answer_details(writer_text, questions)

        assert details["q1"]["answer"] == "첫 번째 답변 입니다."
        assert details["q1"]["char_count"] == len("첫 번째 답변 입니다.")

    def test_build_writer_char_limit_report_fails_when_out_of_target_range(self):
        writer_text = """
## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
Q1: 너무 짧다.
글자수: 약 6 자 (공백 포함) / 제한 대비 30%

Q2: 이 답변은 제한보다 훨씬 길게 작성되어 있어서 분량 초과를 명확하게 만든다.
글자수: 약 40 자 (공백 포함) / 제한 대비 130%

## 블록 4: SELF-CHECK
- PASS
"""
        project = ApplicationProject(
            questions=[
                Question(id="q1", order_no=1, question_text="질문1", char_limit=20),
                Question(id="q2", order_no=2, question_text="질문2", char_limit=30),
            ]
        )

        report = build_writer_char_limit_report(project, writer_text)

        assert report["passed"] is False
        assert any(
            item["status"] == "under_target" for item in report["question_reports"]
        )
        assert any(
            item["status"] == "over_limit" for item in report["question_reports"]
        )

    def test_enforce_writer_char_limits_rewrites_until_pass(self):
        initial_text = """
## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
Q1: 짧다.
글자수: 약 3 자 (공백 포함) / 제한 대비 15%

## 블록 4: SELF-CHECK
- PASS
"""
        rewritten_text = """
## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
Q1: 지원 직무에서 바로 활용할 수 있는 문제 해결 경험을 중심으로 역량을 설명하겠습니다.
글자수: 약 43 자 (공백 포함) / 제한 대비 95%

## 블록 4: SELF-CHECK
- PASS
"""
        project = ApplicationProject(
            questions=[
                Question(id="q1", order_no=1, question_text="질문1", char_limit=50)
            ]
        )

        calls = []

        def fake_rewriter(
            previous_output: str, report: dict[str, any], attempt: int
        ) -> str:
            calls.append((attempt, report["passed"]))
            return rewritten_text

        final_text, final_report, changed = enforce_writer_char_limits(
            project,
            initial_text,
            rewrite_func=fake_rewriter,
            max_attempts=2,
        )

        assert changed is True
        assert len(calls) == 1
        assert final_report["passed"] is True
        assert "지원 직무에서 바로 활용할 수 있는 문제 해결 경험" in final_text

    def test_enforce_patina_char_limits_rewrites_patina_output(self):
        project = ApplicationProject(
            questions=[
                Question(id="q1", order_no=1, question_text="질문1", char_limit=35)
            ]
        )
        patina_result = {
            "mode": "rewrite",
            "reassembled_text": """
## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
Q1: 너무 짧다.
글자수: 약 5 자 (공백 포함) / 제한 대비 25%

## 블록 4: SELF-CHECK
- PASS
""",
            "warnings": [],
        }
        rewritten = """
## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
Q1: 지원 직무와 연결되는 실무 경험을 구체적으로 설명하겠습니다.
글자수: 약 18 자 (공백 포함) / 제한 대비 90%

## 블록 4: SELF-CHECK
- PASS
"""

        calls = []

        def fake_rewriter(
            previous_output: str, report: dict[str, object], attempt: int
        ) -> str:
            calls.append((attempt, report["passed"]))
            return rewritten

        updated = enforce_patina_char_limits(
            project,
            patina_result,
            rewrite_func=fake_rewriter,
            max_attempts=2,
        )

        assert len(calls) == 1
        assert updated["char_limit_report"]["passed"] is True
        assert updated["reassembled_text"] == rewritten
        assert updated["char_limit_adjusted"] is True

    def test_build_writer_rewrite_prompt_includes_humanization_and_feedback_learning(
        self,
    ):
        validation = ValidationResult(passed=True)
        quality = [
            {
                "question_order": 1,
                "overall_score": 0.85,
                "weaknesses": [],
                "suggestions": [],
                "humanization_flags": ["기계적 도입부: 안녕하세요"],
                "humanization_suggestions": ["도입부는 직무 접점부터 시작하세요."],
            }
        ]

        prompt = build_writer_rewrite_prompt(
            "이전 출력",
            validation,
            quality,
            feedback_learning={
                "recent_rejection_comments": ["문장이 너무 교과서적입니다."],
                "insights": {"improvement_areas": ["writer 패턴 성공률이 낮습니다."]},
            },
        )

        assert "인간화 이슈" in prompt
        assert "문장이 너무 교과서적입니다." in prompt
        assert "writer 패턴 성공률이 낮습니다." in prompt

    def test_build_writer_rewrite_prompt_includes_strategy_outcome_guidance(self):
        validation = ValidationResult(passed=True)
        quality = [
            {
                "question_order": 1,
                "overall_score": 0.83,
                "weaknesses": [],
                "suggestions": [],
            }
        ]

        prompt = build_writer_rewrite_prompt(
            "이전 출력",
            validation,
            quality,
            feedback_learning={
                "strategy_outcome_summary": {
                    "experience_stats_by_question_type": {
                        "TYPE_A": {
                            "exp-risky": {
                                "total_uses": 4,
                                "pass_count": 1,
                                "fail_count": 3,
                                "weighted_pass_score": 2,
                                "weighted_fail_score": 7,
                                "weighted_net_score": -5,
                                "top_rejection_reasons": [
                                    {"reason": "개인 기여 불명확", "count": 2}
                                ],
                            }
                        }
                    }
                },
                "question_experience_map": [
                    {
                        "question_id": "q1",
                        "question_type": "TYPE_A",
                        "experience_id": "exp-risky",
                        "question_order": 1,
                    }
                ],
            },
        )

        assert "실제 결과 통계 경고" in prompt
        assert "개인 기여 불명확" in prompt

    def test_build_writer_rewrite_prompt_includes_jd_ncs_match_rationale(self):
        validation = ValidationResult(passed=True)
        quality = [
            {
                "question_order": 2,
                "overall_score": 0.84,
                "weaknesses": [],
                "suggestions": [],
                "ncs_alignment_score": 0.58,
                "ncs_expected_competencies": ["문제해결능력", "의사소통능력"],
                "ncs_matched_competencies": ["문제해결능력"],
                "ncs_missing_competencies": ["의사소통능력"],
                "ncs_missing_ability_units": ["문서작성"],
            }
        ]

        prompt = build_writer_rewrite_prompt("이전 출력", validation, quality)

        assert "JD/NCS 매칭 근거" in prompt
        assert "기대역량=문제해결능력, 의사소통능력" in prompt
        assert "현재매칭=문제해결능력" in prompt
        assert "미충족=의사소통능력" in prompt

    def test_build_writer_rewrite_prompt_includes_strategy_contract_axes(self):
        validation = ValidationResult(passed=True)
        quality = [
            {
                "question_order": 1,
                "overall_score": 0.83,
                "weaknesses": [],
                "suggestions": [],
                "committee_attack_points": ["개인 판단 기준이 모호함"],
                "message_discipline_score": 0.61,
                "message_competing_points": ["성장 이야기", "협업 이야기"],
                "cliche_flags": ["성장", "노력"],
                "differentiation_score": 0.5,
                "differentiation_gaps": ["수치·비교 기준이 부족합니다."],
            }
        ]

        prompt = build_writer_rewrite_prompt(
            "이전 출력",
            validation,
            quality,
            writer_brief={
                "question_strategies": [
                    {
                        "question_order": 1,
                        "core_message": "운영 안정성을 입증한다.",
                        "winning_angle": "열정보다 운영 기준",
                        "forbidden_points": ["추상적 성장담"],
                    }
                ]
            },
        )

        assert "위원회 예상 공격" in prompt
        assert "메시지 축 흔들림" in prompt
        assert "클리셰 차단 필요" in prompt
        assert "writer contract" in prompt

    def test_build_writer_rewrite_quality_report_builds_minimum_three_samples(self):
        before = [
            {
                "question_order": 1,
                "overall_score": 0.61,
                "humanization_score": 0.6,
                "ncs_alignment_score": 0.42,
                "ssot_alignment_score": 0.4,
                "ncs_expected_competencies": ["문제해결능력"],
                "ncs_matched_competencies": [],
                "ncs_missing_competencies": ["문제해결능력"],
            },
            {
                "question_order": 2,
                "overall_score": 0.66,
                "humanization_score": 0.67,
                "ncs_alignment_score": 0.51,
                "ssot_alignment_score": 0.46,
                "ncs_expected_competencies": ["의사소통능력"],
                "ncs_matched_competencies": [],
                "ncs_missing_competencies": ["의사소통능력"],
            },
            {
                "question_order": 3,
                "overall_score": 0.69,
                "humanization_score": 0.68,
                "ncs_alignment_score": 0.55,
                "ssot_alignment_score": 0.5,
                "ncs_expected_competencies": ["자원관리능력"],
                "ncs_matched_competencies": [],
                "ncs_missing_competencies": ["자원관리능력"],
            },
        ]
        after = [
            {
                "question_order": 1,
                "overall_score": 0.8,
                "humanization_score": 0.79,
                "ncs_alignment_score": 0.7,
                "ssot_alignment_score": 0.65,
                "ncs_expected_competencies": ["문제해결능력"],
                "ncs_matched_competencies": ["문제해결능력"],
                "ncs_missing_competencies": [],
            },
            {
                "question_order": 2,
                "overall_score": 0.78,
                "humanization_score": 0.76,
                "ncs_alignment_score": 0.68,
                "ssot_alignment_score": 0.61,
                "ncs_expected_competencies": ["의사소통능력"],
                "ncs_matched_competencies": ["의사소통능력"],
                "ncs_missing_competencies": [],
            },
            {
                "question_order": 3,
                "overall_score": 0.77,
                "humanization_score": 0.75,
                "ncs_alignment_score": 0.66,
                "ssot_alignment_score": 0.6,
                "ncs_expected_competencies": ["자원관리능력"],
                "ncs_matched_competencies": ["자원관리능력"],
                "ncs_missing_competencies": [],
            },
        ]

        report = build_writer_rewrite_quality_report(before, after)

        assert report["sample_count"] == 3
        assert report["minimum_sample_met"] is True
        assert report["average_overall_delta"] > 0
        assert "Q1" in report["markdown"]
        assert "JD/NCS 근거" in report["markdown"]

    def test_build_writer_rewrite_quality_report_includes_result_quality_delta(self):
        before = [{"question_order": 1, "overall_score": 0.7, "humanization_score": 0.7, "ncs_alignment_score": 0.6, "ssot_alignment_score": 0.6}]
        after = [{"question_order": 1, "overall_score": 0.7, "humanization_score": 0.72, "ncs_alignment_score": 0.61, "ssot_alignment_score": 0.63}]
        before_result = [{"question_order": 1, "overall": 0.58}]
        after_result = [{"question_order": 1, "overall": 0.74}]

        report = build_writer_rewrite_quality_report(
            before,
            after,
            minimum_samples=1,
            before_result_quality_evaluations=before_result,
            after_result_quality_evaluations=after_result,
        )

        assert report["average_result_quality_delta"] == 0.16
        assert "평균 result quality 변화" in report["markdown"]


class TestWriterQualityHumanization:
    def test_build_writer_quality_evaluations_includes_humanization(self):
        project = ApplicationProject(
            company_name="테스트",
            job_title="데이터 분석",
            questions=[
                Question(id="q1", order_no=1, question_text="지원동기를 작성하세요.")
            ],
        )
        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
### Q1
안녕하세요, 저는 항상 배우는 자세로 귀사에 기여하고자 합니다.
글자수: 약 34자 / 제한 대비 95%

## 블록 4: SELF-CHECK
- PASS
"""
        evaluations = build_writer_quality_evaluations(
            project=project,
            writer_text=writer_text,
            experiences=[],
            question_map=[],
            company_analysis=None,
            ncs_profile={
                "priority_competencies": ["의사소통능력"],
                "question_alignment": [
                    {
                        "question_id": "q1",
                        "recommended_competencies": ["의사소통능력"],
                        "recommended_ability_units": ["문서작성"],
                    }
                ],
            },
        )

        assert evaluations
        assert "humanization_score" in evaluations[0]
        assert "ncs_alignment_score" in evaluations[0]
        assert evaluations[0]["humanization_score"] <= 0.78
        assert evaluations[0]["ncs_expected_competencies"] == ["의사소통능력"]
        assert evaluations[0]["ncs_expected_ability_units"] == ["문서작성"]
        assert evaluations[0]["ncs_missing_ability_units"] == ["문서작성"]
        assert "interviewer_checklist" in evaluations[0]
        assert "expected_followups" in evaluations[0]
        assert evaluations[0]["expected_followups"][:3]
        assert "defense_gaps" in evaluations[0]

    def test_build_interview_defense_simulations_includes_ncs_fields(self):
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="협업 경험을 말해주세요.",
                    detected_type=QuestionType.TYPE_C,
                )
            ],
        )
        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
### Q1
민원인의 질문을 규정 중심으로 설명하고 동료와 협업해 처리했습니다.
글자수: 약 38자 / 제한 대비 90%

## 블록 4: SELF-CHECK
- PASS
"""
        simulations = build_interview_defense_simulations(
            project=project,
            writer_text=writer_text,
            experiences=[],
            question_map=[],
            company_analysis=None,
            ncs_profile={
                "priority_competencies": ["의사소통능력", "대인관계능력"],
                "question_alignment": [
                    {
                        "question_id": "q1",
                        "recommended_competencies": [
                            "의사소통능력",
                            "대인관계능력",
                        ],
                        "recommended_ability_units": ["민원 응대"],
                    }
                ],
            },
        )

        assert simulations
        assert "ncs_alignment_score" in simulations[0]
        assert simulations[0]["ncs_priority_competencies"] == [
            "의사소통능력",
            "대인관계능력",
        ]
        assert simulations[0]["ncs_priority_ability_units"] == ["민원 응대"]
        assert simulations[0]["follow_up_questions"][0].startswith("[사실]")
        assert simulations[0]["follow_up_questions"][1].startswith("[판단]")
        assert simulations[0]["follow_up_questions"][2].startswith("[가치관]")

    def test_build_interview_defense_simulations_includes_historical_outcome_signal(
        self,
    ):
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="협업 경험을 말해주세요.",
                    detected_type=QuestionType.TYPE_C,
                )
            ],
        )
        experience = Experience(
            id="exp-risky",
            title="지원 경험",
            organization="기관",
            period_start="2024-01-01",
            situation="민원 응대를 했습니다.",
            task="질문에 답했습니다.",
            action="안내했습니다.",
            result="처리를 마쳤습니다.",
        )
        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
### Q1
민원인의 질문을 규정 중심으로 설명하고 동료와 협업해 처리했습니다.
글자수: 약 38자 / 제한 대비 90%

## 블록 4: SELF-CHECK
- PASS
"""
        simulations = build_interview_defense_simulations(
            project=project,
            writer_text=writer_text,
            experiences=[experience],
            question_map=[
                {
                    "question_id": "q1",
                    "question_type": "TYPE_C",
                    "experience_id": "exp-risky",
                }
            ],
            company_analysis=None,
            strategy_outcome_summary={
                "experience_stats_by_question_type": {
                    "TYPE_C": {
                        "exp-risky": {
                            "total_uses": 4,
                            "pass_count": 1,
                            "fail_count": 3,
                            "weighted_pass_score": 2,
                            "weighted_fail_score": 7,
                            "weighted_net_score": -5,
                            "top_rejection_reasons": [
                                {"reason": "개인 기여 불명확", "count": 2}
                            ],
                            "pattern_breakdown": {},
                        }
                    }
                }
            },
        )

        assert "historical_outcome_signal" in simulations[0]
        assert "개인 기여 불명확" in simulations[0]["historical_outcome_signal"]
        assert "interviewer_reaction" in simulations[0]
        assert "next_probe" in simulations[0]["interviewer_reaction"]
        assert len(simulations[0]["interviewer_reaction_chain"]) == 3

    def test_build_writer_quality_evaluations_exposes_rubric_breakdown(self):
        project = ApplicationProject(
            company_name="테스트기관",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="고객 응대 경험을 설명하세요.",
                    detected_type=QuestionType.TYPE_H,
                )
            ],
        )
        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
Q1: 민원 응대 절차를 정리해 반복 문의를 줄였고, 기준 문구를 통일해 응대 시간을 줄였습니다.
글자수: 약 90 자 (공백 포함) / 제한 대비 70%

## 블록 4: SELF-CHECK
- PASS
"""
        evaluations = build_writer_quality_evaluations(
            project=project,
            writer_text=writer_text,
            experiences=[],
            question_map=[],
            company_analysis=None,
        )

        assert "evaluation_rubric" in evaluations[0]
        assert "strong_points" in evaluations[0]["evaluation_rubric"]
        assert "risk_points" in evaluations[0]["evaluation_rubric"]
        assert "improvement_points" in evaluations[0]["evaluation_rubric"]

    def test_build_interview_defense_simulations_resolves_unknown_for_two_job_scenarios(
        self,
    ):
        project = ApplicationProject(
            company_name="테스트기관",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="민원인이 불만을 제기했을 때 어떻게 응대했는지 설명하세요.",
                    detected_type=QuestionType.TYPE_UNKNOWN,
                ),
                Question(
                    id="q2",
                    order_no=2,
                    question_text="데이터 정합성 문제를 발견했을 때 직무역량을 어떻게 발휘했는지 설명하세요.",
                    detected_type=QuestionType.TYPE_UNKNOWN,
                ),
            ],
        )
        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
Q1: 민원 문의를 유형화하고 기준 답변을 정리해 응대 품질을 맞췄습니다.

Q2: 데이터 검증 규칙을 정의하고 오류 로그를 추적해 기준값을 재정의했습니다.

## 블록 4: SELF-CHECK
- PASS
"""
        simulations = build_interview_defense_simulations(
            project=project,
            writer_text=writer_text,
            experiences=[],
            question_map=[],
            company_analysis=None,
        )

        assert simulations[0]["resolved_question_type"] == QuestionType.TYPE_H.value
        assert simulations[1]["resolved_question_type"] == QuestionType.TYPE_B.value
        assert any(
            "고객" in item or "민원" in item
            for item in simulations[0]["follow_up_questions"]
        )
        assert any(
            "역량" in item or "수치" in item
            for item in simulations[1]["follow_up_questions"]
        )


class TestQuestionTypeLlmFallback:
    def test_classify_project_questions_with_llm_fallback_updates_unknown(
        self, tmp_path
    ):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="우리 기관에서 일하고 싶은 이유와 잘할 수 있는 점을 함께 설명하세요.",
                )
            ],
        )

        def fake_run_codex(prompt_path, root, output_path, tool="codex"):
            output_path.write_text(
                '[{"question_id":"q1","question_type":"TYPE_A"}]', encoding="utf-8"
            )
            return 0

        with patch("resume_agent.pipeline.run_codex", side_effect=fake_run_codex):
            updated = classify_project_questions_with_llm_fallback(workspace, project)

        assert updated.questions[0].detected_type.value == "TYPE_A"


class TestSemanticSourceCrossCheck:
    def test_build_source_grading_includes_semantic_review(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        save_knowledge_sources(
            workspace,
            [
                KnowledgeSource(
                    id="src1",
                    source_type=SourceType.USER_URL_PUBLIC,
                    title="공식 채용공고",
                    url="https://example.go.kr/jobs",
                    raw_text="민원 응대와 문서관리 역량을 요구합니다.",
                    cleaned_text="민원 응대와 문서관리 역량을 요구합니다.",
                    meta=KnowledgeSourceMeta(
                        company_name="테스트공사", job_title="사무행정"
                    ),
                ),
                KnowledgeSource(
                    id="src2",
                    source_type=SourceType.LOCAL_TEXT,
                    title="기관 소개 메모",
                    raw_text="정확한 문서관리와 공공 민원 커뮤니케이션이 중요합니다.",
                    cleaned_text="정확한 문서관리와 공공 민원 커뮤니케이션이 중요합니다.",
                    meta=KnowledgeSourceMeta(
                        company_name="테스트공사", job_title="사무행정"
                    ),
                ),
            ],
        )

        def fake_run_codex(prompt_path, root, output_path, tool="codex"):
            output_path.write_text(
                json.dumps(
                    {
                        "summary": "핵심 신호가 서로 보강됩니다.",
                        "agreements": ["민원 응대 역량 중요"],
                        "conflicts": [],
                        "essay_implications": [
                            "지원동기와 직무역량 문항에서 민원 응대 경험을 전면 배치"
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return 0

        with patch("resume_agent.pipeline.run_codex", side_effect=fake_run_codex):
            grading = build_source_grading(
                workspace,
                use_semantic_review=True,
                tool="codex",
            )

        assert "semantic_review" in grading
        assert "민원 응대 역량 중요" in grading["semantic_review"]["agreements"]


class TestBuildCompanyResearchPrompt:
    def test_includes_company_analysis_and_jd_keywords_in_data_block(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        (workspace.profile_dir / "jd.md").write_text(
            "데이터 분석 역량과 SQL 활용 능력을 요구합니다.",
            encoding="utf-8",
        )

        from resume_agent.pipeline import build_company_research_prompt

        prompt_path = build_company_research_prompt(workspace)
        content = Path(prompt_path).read_text(encoding="utf-8")

        assert '"company_analysis"' in content
        assert '"jd_keywords"' in content
        assert '"research_brief"' in content
        assert '"source_grading"' in content
        assert '"ncs_profile"' in content
        assert '"live_source_updates"' in content
        assert '"priority_live_updates"' in content


class TestRunCompanyResearchWithCodex:
    def test_saves_source_trace_even_when_codex_fails(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)

        from resume_agent.pipeline import run_company_research_with_codex

        with patch("resume_agent.pipeline.run_codex", return_value=1):
            result = run_company_research_with_codex(workspace)

        source_trace = Path(result["source_trace_path"])
        assert source_trace.exists()
        payload = json.loads(source_trace.read_text(encoding="utf-8"))
        assert "knowledge_source_titles" in payload
        assert Path(result["research_brief_path"]).exists()
        assert Path(result["source_grading_path"]).exists()
        assert result["validation"]["passed"] is False


class TestResearchBriefAndSourceGrading:
    def test_build_source_grading_marks_corroborated_area(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트데이터",
            job_title="데이터 분석",
            company_type="공공",
            questions=[
                Question(id="q1", order_no=1, question_text="지원동기와 직무역량")
            ],
        )
        save_project(workspace, project)
        (workspace.profile_dir / "jd.md").write_text(
            "데이터 분석, SQL, 협업 역량을 요구합니다.",
            encoding="utf-8",
        )
        save_knowledge_sources(
            workspace,
            [
                KnowledgeSource(
                    id="src1",
                    source_type=SourceType.USER_URL_PUBLIC,
                    title="채용 공고",
                    url="https://example.com/careers/data-analyst",
                    raw_text="데이터 분석과 SQL 활용 능력을 요구합니다.",
                    cleaned_text="데이터 분석과 SQL 활용 능력을 요구합니다.",
                    meta=KnowledgeSourceMeta(
                        company_name="테스트데이터", job_title="데이터 분석"
                    ),
                ),
                KnowledgeSource(
                    id="src2",
                    source_type=SourceType.LOCAL_TEXT,
                    title="회사 소개 메모",
                    raw_text="테스트데이터는 데이터 기반 협업 문화를 강조합니다.",
                    cleaned_text="테스트데이터는 데이터 기반 협업 문화를 강조합니다.",
                    meta=KnowledgeSourceMeta(
                        company_name="테스트데이터", job_title="데이터 분석"
                    ),
                ),
            ],
        )

        from resume_agent.pipeline import build_research_brief, build_source_grading

        brief = build_research_brief(workspace)
        grading = build_source_grading(workspace, research_brief=brief)

        assert brief["key_questions"]
        assert any(
            item["status"] == "corroborated"
            for item in grading["cross_check"]["key_areas"]
        )

    def test_build_source_grading_prioritizes_changed_live_sources(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트데이터",
            job_title="데이터 분석",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        save_knowledge_sources(
            workspace,
            [
                KnowledgeSource(
                    id="src1",
                    source_type=SourceType.USER_URL_PUBLIC,
                    title="채용 공고",
                    url="https://example.com/jobs",
                    raw_text="데이터 분석 역량",
                    cleaned_text="데이터 분석 역량",
                    meta=KnowledgeSourceMeta(),
                ),
                KnowledgeSource(
                    id="src2",
                    source_type=SourceType.LOCAL_TEXT,
                    title="로컬 메모",
                    raw_text="데이터 분석 문화",
                    cleaned_text="데이터 분석 문화",
                    meta=KnowledgeSourceMeta(),
                ),
            ],
        )
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://example.com/jobs": {
                    "url": "https://example.com/jobs",
                    "change_status": "changed",
                }
            },
        )

        from resume_agent.pipeline import build_source_grading

        grading = build_source_grading(workspace)

        assert grading["assessments"][0]["url"] == "https://example.com/jobs"
        assert grading["assessments"][0]["freshness_status"] == "changed"

    def test_build_research_brief_includes_live_source_updates(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://example.com/jobs": {
                    "url": "https://example.com/jobs",
                    "title": "채용 공고",
                    "content_hash": "hash-1",
                    "fetched_at": "2026-04-09T01:02:03+00:00",
                    "change_status": "changed",
                }
            },
        )

        from resume_agent.pipeline import build_research_brief

        brief = build_research_brief(workspace)

        assert brief["live_source_updates"]["tracked_url_count"] == 1
        assert brief["live_source_updates"]["changed_url_count"] == 1
        assert brief["priority_live_updates"][0]["url"] == "https://example.com/jobs"


class TestCrawlWebSourcesLiveTracking:
    def test_crawl_web_sources_tracks_change_status(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)

        from resume_agent.pipeline import crawl_web_sources

        snapshots = [
            {
                "url": "https://example.com/jobs",
                "title": "Example Jobs",
                "raw_text": "<html><title>Example Jobs</title><body>first</body></html>",
                "cleaned_text": "first",
                "content_hash": "hash-1",
                "fetched_at": "2026-04-09T00:00:00+00:00",
                "status_code": 200,
            },
            {
                "url": "https://example.com/jobs",
                "title": "Example Jobs",
                "raw_text": "<html><title>Example Jobs</title><body>second</body></html>",
                "cleaned_text": "second",
                "content_hash": "hash-2",
                "fetched_at": "2026-04-09T00:05:00+00:00",
                "status_code": 200,
            },
        ]

        with patch(
            "resume_agent.pipeline.fetch_public_url_snapshot",
            side_effect=snapshots,
        ):
            first = crawl_web_sources(workspace, ["https://example.com/jobs"])
            second = crawl_web_sources(workspace, ["https://example.com/jobs"])

        assert first["new_url_count"] == 1
        assert second["changed_url_count"] == 1
        cache = load_live_source_cache(workspace)
        assert cache["https://example.com/jobs"]["content_hash"] == "hash-2"
        assert "추가 신호" in cache["https://example.com/jobs"]["change_summary"]
        assert (workspace.analysis_dir / "live_source_updates.json").exists()

    def test_build_live_source_update_summary_returns_recent_items(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://a.example.com": {
                    "url": "https://a.example.com",
                    "title": "A",
                    "content_hash": "a",
                    "fetched_at": "2026-04-09T00:00:00+00:00",
                    "change_status": "unchanged",
                },
                "https://b.example.com": {
                    "url": "https://b.example.com",
                    "title": "B",
                    "content_hash": "b",
                    "fetched_at": "2026-04-09T01:00:00+00:00",
                    "change_status": "changed",
                },
            },
        )

        summary = build_live_source_update_summary(workspace)

        assert summary["tracked_url_count"] == 2
        assert summary["changed_url_count"] == 1
        assert summary["priority_update_count"] == 1
        assert summary["priority_live_updates"][0]["url"] == "https://b.example.com"
        assert summary["latest_updates"][0]["url"] == "https://b.example.com"

    def test_refresh_existing_public_sources_uses_stored_public_urls(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        save_knowledge_sources(
            workspace,
            [
                KnowledgeSource(
                    id="src1",
                    source_type=SourceType.USER_URL_PUBLIC,
                    title="채용 공고",
                    url="https://example.com/jobs",
                    raw_text="raw",
                    cleaned_text="clean",
                    meta=KnowledgeSourceMeta(),
                ),
                KnowledgeSource(
                    id="src2",
                    source_type=SourceType.LOCAL_TEXT,
                    title="로컬 메모",
                    raw_text="memo",
                    cleaned_text="memo",
                    meta=KnowledgeSourceMeta(),
                ),
            ],
        )

        from resume_agent.pipeline import refresh_existing_public_sources

        with patch(
            "resume_agent.pipeline.refresh_live_web_sources",
            return_value={
                "source_count": 1,
                "stored_count": 2,
                "new_url_count": 0,
                "changed_url_count": 1,
                "unchanged_url_count": 0,
                "live_updates_path": str(workspace.analysis_dir / "live_source_updates.json"),
            },
        ) as mock_refresh:
            result = refresh_existing_public_sources(workspace)

        mock_refresh.assert_called_once_with(workspace, ["https://example.com/jobs"])
        assert result["tracked_url_count"] == 1
        assert result["changed_url_count"] == 1


class TestNcsProfile:
    def test_build_ncs_profile_creates_priority_map(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            company_type="공공",
            questions=[
                Question(id="q1", order_no=1, question_text="협업 경험을 작성하세요.")
            ],
        )
        save_project(workspace, project)
        experiences = [
            Experience(
                id="exp1",
                title="민원 응대 및 규정 설명",
                organization="공공기관",
                period_start="2024-01-01",
                situation="민원인이 규정을 어려워함",
                task="쉽게 설명하고 정확히 처리",
                action="고객 눈높이에 맞춰 설명하고 서류를 검토함",
                result="민원 이해도 향상",
                tags=["민원응대", "규정준수", "협업"],
            )
        ]
        write_json(
            workspace.analysis_dir / "question_map.json",
            [
                {
                    "question_id": "q1",
                    "question_type": "TYPE_C",
                    "recommended_focus": "협업과 민원 소통",
                }
            ],
        )

        profile = build_ncs_profile(
            workspace,
            project=project,
            experiences=experiences,
            question_map=read_json_if_exists(
                workspace.analysis_dir / "question_map.json"
            ),
            jd_keywords=["민원", "협업", "정확한 문서 처리"],
            company_analysis=None,
        )

        assert "의사소통능력" in profile["priority_competencies"]
        assert Path(workspace.analysis_dir / "ncs_profile.json").exists()
        assert profile["question_alignment"][0]["question_id"] == "q1"

    def test_build_ncs_profile_extracts_ability_units_from_job_spec_source(
        self, tmp_path
    ):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            company_type="공공",
            questions=[
                Question(
                    id="q1", order_no=1, question_text="민원 응대 경험을 작성하세요."
                )
            ],
        )
        save_project(workspace, project)
        save_knowledge_sources(
            workspace,
            [
                KnowledgeSource(
                    id="src-job-spec",
                    source_type=SourceType.LOCAL_TEXT,
                    title="직무기술서_사무행정",
                    raw_text="능력단위 o 민원 응대, 문서관리\n능력단위요소 o 고객응대, 문서작성\n직업기초능력 o 의사소통능력, 문제해결능력",
                    cleaned_text="능력단위 o 민원 응대, 문서관리\n능력단위요소 o 고객응대, 문서작성\n직업기초능력 o 의사소통능력, 문제해결능력",
                    meta=KnowledgeSourceMeta(
                        company_name="테스트공사", job_title="사무행정"
                    ),
                )
            ],
        )
        write_json(
            workspace.analysis_dir / "question_map.json",
            [
                {
                    "question_id": "q1",
                    "question_type": "TYPE_H",
                    "recommended_focus": "민원 응대와 규정 설명",
                }
            ],
        )

        profile = build_ncs_profile(
            workspace,
            project=project,
            experiences=[],
            question_map=read_json_if_exists(
                workspace.analysis_dir / "question_map.json"
            ),
            jd_keywords=["민원", "문서관리"],
            company_analysis=None,
        )

        assert "민원 응대" in profile["ability_units"]
        assert "고객응대" in profile["ability_unit_elements"]
        assert "의사소통능력" in profile["job_spec_competencies"]
        assert profile["question_alignment"][0]["recommended_ability_units"]
        assert Path(workspace.analysis_dir / "ncs_job_spec.json").exists()


class TestPdfIngestion:
    def test_ingest_source_file_reads_pdf_via_pdf_utils(self, tmp_path):
        pdf_path = tmp_path / "직무기술서.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")

        with patch(
            "resume_agent.parsing.extract_text_from_pdf",
            return_value="직업기초능력 o 의사소통능력, 문제해결능력",
        ):
            sources, cases = ingest_source_file(pdf_path)

        assert len(sources) == 1
        assert sources[0].title == "직무기술서"
        assert "의사소통능력" in sources[0].cleaned_text
        assert cases == []


class TestFeedbackLearningAndAutoWebResearch:
    def test_build_feedback_learning_context_includes_outcome_summary(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트기업",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)

        from resume_agent.feedback_learner import create_feedback_learner

        learner = create_feedback_learner(str(workspace.root / "kb" / "feedback"))
        learner.record_feedback(
            draft_id="writer-1",
            pattern_used="writer|공공|TYPE_A",
            accepted=False,
            artifact_type="writer",
            company_type="공공",
            question_types=["TYPE_A"],
            final_outcome="fail_interview",
            rejection_reason="근거 부족",
        )

        context = build_feedback_learning_context(workspace, "writer", project=project)

        assert context["outcome_summary"]["matched_feedback_count"] == 1
        assert context["outcome_summary"]["outcome_breakdown"]["fail_interview"] == 1
        assert "adaptation_plan" in context

    def test_build_feedback_adaptation_plan_collects_risky_question_types(self):
        project = ApplicationProject(
            company_name="테스트기업",
            job_title="데이터 분석",
            company_type="공공",
        )
        plan = build_feedback_adaptation_plan(
            project,
            {
                "recommended_pattern": "writer|공공|TYPE_A",
                "outcome_summary": {
                    "matched_feedback_count": 2,
                    "top_rejection_reasons": [{"reason": "근거 부족", "count": 2}],
                },
                "strategy_outcome_summary": {
                    "matched_feedback_count": 2,
                    "experience_stats_by_question_type": {
                        "TYPE_A": {
                            "exp-weak": {
                                "pass_rate": 0.25,
                                "weighted_net_score": -2,
                                "top_rejection_reasons": [{"reason": "근거 부족", "count": 2}],
                            }
                        }
                    },
                },
            },
        )

        assert plan["recommended_pattern"] == "writer|공공|TYPE_A"
        assert plan["risky_question_types"][0]["question_type"] == "TYPE_A"
        assert any("근거 부족" in item for item in plan["focus_actions"])

    def test_build_draft_prompt_includes_feedback_learning(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트기업",
            job_title="데이터 분석",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        (workspace.profile_dir / "jd.md").write_text(
            "SQL과 분석 역량", encoding="utf-8"
        )

        from resume_agent.feedback_learner import create_feedback_learner
        from resume_agent.pipeline import build_draft_prompt

        learner = create_feedback_learner(str(workspace.root / "kb" / "feedback"))
        learner.record_feedback(
            draft_id="writer-1",
            pattern_used="writer|공공|TYPE_A",
            accepted=False,
            comment="지원동기 표현이 추상적입니다",
        )
        write_json(
            workspace.analysis_dir / "writer_brief.json",
            {
                "mode": "heuristic",
                "question_strategies": [
                    {
                        "question_id": "q1",
                        "question_order": 1,
                        "core_message": "운영 안정성을 입증한다.",
                    }
                ],
                "writer_contract": {"headline": "단일 전략 유지"},
            },
        )

        prompt_path = build_draft_prompt(
            workspace,
            workspace.targets_dir / "example_target.md",
        )
        content = Path(prompt_path).read_text(encoding="utf-8")

        assert '"feedback_learning"' in content
        assert '"writer_brief"' in content
        assert "지원동기 표현이 추상적입니다" in content
        assert '"outcome_summary"' in content

    def test_build_draft_prompt_includes_role_industry_strategy(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        (workspace.profile_dir / "jd.md").write_text(
            "데이터 분석과 정확한 보고 역량", encoding="utf-8"
        )
        write_json(
            workspace.analysis_dir / "source_grading.json",
            {
                "cross_check": {
                    "key_areas": [{"area": "company_fit", "status": "single_source"}],
                    "single_source_area_count": 1,
                }
            },
        )
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://example.com/jobs": {
                    "url": "https://example.com/jobs",
                    "title": "채용 공고",
                    "change_status": "changed",
                    "change_summary": "추가 신호: 데이터, 자동화",
                    "keywords": ["데이터", "자동화"],
                    "fetched_at": "2026-04-09T00:00:00+00:00",
                }
            },
        )

        from resume_agent.company_analyzer import analyze_company
        from resume_agent.pipeline import build_draft_prompt

        prompt_path = build_draft_prompt(
            workspace,
            workspace.targets_dir / "example_target.md",
            company_analysis=analyze_company(
                company_name="테스트공사",
                job_title="데이터 분석",
                company_type="공공",
            ),
        )
        content = Path(prompt_path).read_text(encoding="utf-8")

        assert '"role_industry_strategy"' in content
        assert '"evidence_priority"' in content
        assert '"committee_personas"' in content
        assert '"self_intro_pack"' in content
        assert '"ncs_profile"' in content
        assert '"candidate_profile"' in content
        assert '"narrative_ssot"' in content
        assert '"outcome_dashboard"' in content
        assert '"research_strategy_translation"' in content
        assert '"recent_change_actions"' in content
        assert '"recent_change_priority_rules"' in content
        assert "추가 신호: 데이터, 자동화" in content

    def test_build_interview_prompt_includes_recent_change_actions(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://example.com/jobs": {
                    "url": "https://example.com/jobs",
                    "title": "채용 공고",
                    "change_status": "changed",
                    "change_summary": "추가 신호: 데이터, 자동화",
                    "keywords": ["데이터", "자동화"],
                    "fetched_at": "2026-04-09T00:00:00+00:00",
                }
            },
        )

        prompt_path = build_interview_prompt(workspace)
        content = Path(prompt_path).read_text(encoding="utf-8")

        assert '"research_strategy_translation"' in content
        assert '"recent_change_actions"' in content
        assert '"recent_change_priority_rules"' in content
        assert "추가 신호: 데이터, 자동화" in content

    def test_build_knowledge_hints_includes_semantic_score(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트기관",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="민원 처리 경험을 설명하세요.",
                    detected_type="TYPE_H",
                )
            ],
        )
        save_project(workspace, project)
        source = KnowledgeSource(
            id="src1",
            title="민원 대응 우수사례",
            source_type=SourceType.LOCAL_TEXT,
            raw_text="민원 처리와 고객 응대 경험",
            cleaned_text="민원 처리와 고객 응대 경험",
            pattern={
                "company_name": "테스트기관",
                "job_title": "사무행정",
                "question_types": ["TYPE_H"],
                "structure_summary": "민원 대응 경험",
                "retrieval_terms": ["민원", "고객응대", "사무행정"],
            },
        )
        save_knowledge_sources(workspace, [source])

        hints = build_knowledge_hints([source], project)

        assert hints
        assert "semantic_score" in hints[0]
        assert "vector_score" in hints[0]

    def test_build_knowledge_hints_prefers_exact_company_match(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="국민연금공단",
            job_title="사무직",
            company_type="공공기관",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="지원 직무와 관련한 경험을 설명하세요.",
                    detected_type=QuestionType.TYPE_B,
                )
            ],
        )
        exact_source = KnowledgeSource(
            id="src-exact",
            title="국민연금공단 / 일반 / 2024 하반기",
            source_type=SourceType.LOCAL_TEXT,
            raw_text="정량 성과와 민원 개선",
            cleaned_text="정량 성과와 민원 개선",
            pattern={
                "company_name": "국민연금공단",
                "job_title": "사무직",
                "question_types": ["TYPE_B"],
                "structure_summary": "직무역량 구조",
                "retrieval_terms": ["국민연금공단", "사무직", "민원", "정량"],
            },
        )
        similar_source = KnowledgeSource(
            id="src-similar",
            title="국민건강보험공단 / 행정 / 2024 하반기",
            source_type=SourceType.LOCAL_TEXT,
            raw_text="정량 성과와 민원 개선",
            cleaned_text="정량 성과와 민원 개선",
            pattern={
                "company_name": "국민건강보험공단",
                "job_title": "행정",
                "question_types": ["TYPE_B"],
                "structure_summary": "직무역량 구조",
                "retrieval_terms": ["민원", "행정", "정량"],
            },
        )

        hints = build_knowledge_hints([similar_source, exact_source], project)
        assert hints
        assert hints[0]["company_name"] == "국민연금공단"
        assert "회사명 exact match" in hints[0]["match_reasons"]

    def test_build_question_specific_knowledge_hints_returns_per_question(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트기관",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="민원 처리 경험을 설명하세요.",
                    detected_type=QuestionType.TYPE_H,
                ),
                Question(
                    id="q2",
                    order_no=2,
                    question_text="협업 경험을 설명하세요.",
                    detected_type=QuestionType.TYPE_C,
                ),
            ],
        )
        source = KnowledgeSource(
            id="src1",
            title="민원 대응 우수사례",
            source_type=SourceType.LOCAL_TEXT,
            raw_text="민원 처리와 고객 응대 경험",
            cleaned_text="민원 처리와 고객 응대 경험",
            pattern={
                "company_name": "테스트기관",
                "job_title": "사무행정",
                "question_types": ["TYPE_H", "TYPE_C"],
                "structure_summary": "민원 대응 경험",
                "retrieval_terms": ["민원", "고객응대", "사무행정", "협업"],
            },
        )

        hints = build_question_specific_knowledge_hints([source], project)
        assert len(hints) == 2
        assert hints[0]["question_id"] == "q1"
        assert hints[0]["hints"]
        assert "문항유형 match (TYPE_H)" in hints[0]["hints"][0]["match_reasons"]

    def test_evaluate_writer_cliche_blocking_uses_discouraged_phrases(self):
        from resume_agent.pipeline import evaluate_writer_cliche_blocking

        result = evaluate_writer_cliche_blocking(
            "저는 성장했고 귀사에 기여하고자 합니다.",
            discouraged_phrases=["귀사에 기여하고자 합니다"],
        )
        assert result["score"] < 0.9
        assert "귀사에 기여하고자 합니다" in result["flags"]

    def test_build_candidate_profile_includes_deeper_signals(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트기관",
            job_title="사무행정",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        write_json(
            workspace.state_dir / "experiences.json",
            [
                {
                    "id": "exp1",
                    "title": "민원 응대 개선",
                    "organization": "기관",
                    "period_start": "2024-01-01",
                    "situation": "반복 민원이 많았습니다.",
                    "task": "응대 기준을 정리해야 했습니다.",
                    "action": "안내 기준과 문안을 만들었습니다.",
                    "result": "응대 시간이 줄었습니다.",
                    "personal_contribution": "기준표 초안을 직접 만들고 수정했습니다.",
                    "metrics": "반복 문의 12건 정리",
                    "tags": ["민원", "고객응대", "개선"],
                }
            ],
        )

        from resume_agent.pipeline import build_candidate_profile
        from resume_agent.state import load_experiences

        profile = build_candidate_profile(
            workspace, project, load_experiences(workspace)
        )

        assert "confidence_style" in profile
        assert "blind_spots" in profile
        assert "interview_strategy" in profile
        assert "abstraction_ratio" in profile
        assert "collaboration_ratio" in profile

    def test_build_writer_quality_evaluations_includes_ssot_alignment(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트기관",
            job_title="사무행정",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="지원동기를 설명하세요.",
                    detected_type=QuestionType.TYPE_A,
                )
            ],
        )
        experience = Experience(
            id="exp1",
            title="민원 응대 개선",
            organization="기관",
            period_start="2024-01-01",
            situation="반복 민원이 많았습니다.",
            task="응대 기준을 정리해야 했습니다.",
            action="안내 기준과 문안을 만들었습니다.",
            result="응대 시간이 줄었습니다.",
            personal_contribution="기준표 초안을 직접 만들고 수정했습니다.",
            metrics="반복 문의 12건 정리",
            tags=["민원", "고객응대", "개선"],
        )
        writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
Q1: 저는 사무행정 직무에 바로 투입 가능한 근거 중심 문제해결형 지원자입니다. 민원 응대 기준을 정리하고 안내 품질을 높인 경험을 바탕으로 정확한 서비스 운영에 기여하겠습니다.
글자수: 약 120 자 (공백 포함) / 제한 대비 80%

## 블록 4: SELF-CHECK
- PASS
"""

        evaluations = build_writer_quality_evaluations(
            project=project,
            writer_text=writer_text,
            experiences=[experience],
            question_map=[{"question_id": "q1", "experience_id": "exp1"}],
            company_analysis=None,
            ncs_profile=None,
            narrative_ssot={
                "core_claims": ["사무행정 직무에 바로 투입 가능한 검증형 실무자"],
                "evidence_experience_ids": ["exp1"],
                "answer_anchor": "주장보다 근거를 먼저 제시합니다.",
            },
        )

        assert evaluations[0]["ssot_alignment_score"] > 0
        assert evaluations[0]["ssot_expected_claims"]

    def test_build_blind_benchmark_frame_writes_scaffold(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트기관",
            job_title="사무행정",
            questions=[
                Question(id="q1", order_no=1, question_text="지원동기를 설명하세요."),
                Question(id="q2", order_no=2, question_text="협업 경험을 설명하세요."),
            ],
        )
        save_project(workspace, project)

        frame = build_blind_benchmark_frame(workspace, project=project)

        assert frame["candidate_count"] == 3
        assert len(frame["questions"]) == 2
        assert (workspace.analysis_dir / "blind_benchmark_frame.json").exists()

    def test_build_coach_prompt_includes_committee_feedback_and_self_intro(
        self, tmp_path
    ):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        write_json(
            workspace.state_dir / "interview_sessions.json",
            [
                {
                    "mode": "hard",
                    "turns": [
                        {
                            "interviewer_persona": "위원장",
                            "risk_areas": ["팀 성과와 개인 기여가 구분되지 않음"],
                            "follow_up_risk_areas": [],
                            "committee_rounds": [],
                            "committee_summary": {"verdict": "borderline"},
                        }
                    ],
                }
            ],
        )

        prompt_path = build_coach_prompt(workspace)
        content = Path(prompt_path).read_text(encoding="utf-8")

        assert '"committee_feedback"' in content
        assert '"self_intro_pack"' in content
        assert '"ncs_profile"' in content
        assert "팀 성과와 개인 기여가 구분되지 않음" in content

    def test_run_self_intro_writes_artifact(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
        )
        save_project(workspace, project)

        result = run_self_intro(workspace)

        artifact_path = Path(result["path"])
        assert artifact_path.exists()
        content = artifact_path.read_text(encoding="utf-8")
        assert "## 30초 자기소개 오프닝" in content
        assert "## 60초 답변 프레임" in content

    def test_build_experience_competition_report_ranks_primary_and_secondary(self):
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="협업 경험과 정량 성과를 설명하세요",
                    detected_type=QuestionType.TYPE_C,
                )
            ],
        )
        experiences = [
            Experience(
                id="exp-1",
                title="협업 개선",
                organization="기관A",
                period_start="2024-01",
                action="협업 체계를 정리했습니다.",
                result="정량 성과 20% 개선",
            ),
            Experience(
                id="exp-2",
                title="대체 경험",
                organization="기관B",
                period_start="2024-02",
                action="협업과 소통을 지원했습니다.",
                result="운영 개선",
            ),
        ]
        allocations = [
            {
                "question_id": "q1",
                "experience_id": "exp-1",
                "question_type": "TYPE_C",
                "reason": "핵심 경험",
            }
        ]

        report = build_experience_competition_report(project, experiences, allocations)

        assert report[0]["primary_experience_id"] == "exp-1"
        assert report[0]["secondary_experience_id"] == "exp-2"
        assert report[0]["primary_reason"] == "핵심 경험"

    def test_build_writer_differentiation_report_includes_top001_strategy(self):
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
        )
        report = build_writer_differentiation_report(
            project,
            [
                {
                    "question_order": 1,
                    "question_id": "q1",
                    "question_text": "지원동기",
                    "overall_score": 0.76,
                    "weaknesses": ["근거 부족"],
                    "defense_gaps": ["수치 약함"],
                    "suggestions": ["회사 신호를 문장 앞에 배치"],
                }
            ],
            research_strategy_translation={
                "top001": {
                    "strategic_signals": {"differentiation": ["현장 실행력"]},
                }
            },
            application_strategy={
                "question_strategy": {"q1": ["공공성에 맞닿은 경험으로 시작"]},
                "interview_pressure_points": ["왜 우리 기관인가요?"],
            },
        )

        assert report["pressure_points"] == ["왜 우리 기관인가요?"]
        assert report["rows"][0]["top001_strategy"][0] == "공공성에 맞닿은 경험으로 시작"

    def test_build_adaptive_strategy_layer_varies_by_company_type(self):
        project = ApplicationProject(
            company_name="테스트스타트업",
            job_title="PM",
            company_type="스타트업",
        )

        layer = build_adaptive_strategy_layer(
            project,
            candidate_profile={"confidence_style": "logical"},
        )

        assert layer["company_profile"] == "스타트업"
        assert "가설-실험-학습" in layer["writer_logic"]
        assert "수치와 비교 기준" in layer["coaching_mode"]

    def test_build_kpi_dashboard_collects_result_metrics(self, tmp_path):
        from datetime import datetime, timezone

        from resume_agent.models import (
            ArtifactType,
            GeneratedArtifact,
            ValidationResult,
        )
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        write_json(
            workspace.analysis_dir / "application_strategy.json",
            {
                "question_strategy": {"q1": ["공공성 연결"]},
                "company_signal_summary": {"core_values": ["공공성"]},
            },
        )
        write_json(
            workspace.state_dir / "self_intro_drills.json",
            [{"score": 0.8}, {"score": 0.6}],
        )
        write_json(
            workspace.state_dir / "interview_sessions.json",
            [{"turns": [{"risk_areas": ["근거 부족"], "follow_up_risk_areas": []}]}],
        )
        write_json(
            workspace.artifacts_dir / "writer_quality.json",
            [
                {
                    "overall_score": 0.8,
                    "defensibility_score": 0.7,
                    "ncs_alignment_score": 0.9,
                    "ssot_alignment_score": 0.6,
                    "humanization_score": 0.85,
                },
                {
                    "overall_score": 0.6,
                    "defensibility_score": 0.5,
                    "ncs_alignment_score": 0.7,
                    "ssot_alignment_score": 0.8,
                    "humanization_score": 0.65,
                },
            ],
        )
        write_json(
            workspace.artifacts_dir / "writer_result_quality.json",
            [
                {
                    "overall": 0.75,
                    "details": {
                        "persuasiveness": 0.8,
                        "defensibility": 0.7,
                        "company_fit": 0.6,
                    },
                },
                {
                    "overall": 0.65,
                    "details": {
                        "persuasiveness": 0.7,
                        "defensibility": 0.5,
                        "company_fit": 0.8,
                    },
                },
            ],
        )
        artifact = GeneratedArtifact(
            id="writer-001",
            artifact_type=ArtifactType.WRITER,
            accepted=True,
            input_snapshot={
                "recent_change_priority_rule_check": {
                    "checked_count": 2,
                    "covered_count": 1,
                    "missing_count": 1,
                    "coverage_rate": 0.5,
                    "items": [
                        {"title": "채용 공고", "covered": True},
                        {"title": "조직 소개", "covered": False},
                    ],
                }
            },
            output_path="artifacts/writer.md",
            raw_output_path="artifacts/writer_raw.md",
            validation=ValidationResult(passed=True),
            created_at=datetime.now(timezone.utc),
        )
        write_json(workspace.state_dir / "artifacts.json", [artifact.model_dump()])

        feedback_context = {
            "strategy_outcome_summary": {
                "experience_stats_by_question_type": {
                    "TYPE_A": {"exp-1": {"pass_rate": 0.75}}
                }
            },
            "outcome_summary": {
                "outcome_breakdown": {
                    "document_pass": 1,
                    "interview_pass": 1,
                    "offer": 1,
                }
            },
        }

        with patch(
            "resume_agent.pipeline.build_feedback_learning_context",
            return_value=feedback_context,
        ):
            dashboard = build_kpi_dashboard(workspace, project)

        assert dashboard["question_experience_match_accuracy"] == 0.75
        assert dashboard["self_intro_follow_up_hit_rate"] == 0.7
        assert dashboard["offer_rate"] == 0.333
        assert dashboard["writer_quality_metrics"]["overall_score"] == 0.7
        assert dashboard["writer_quality_metrics"]["defensibility_score"] == 0.6
        assert dashboard["result_quality_metrics"]["overall"] == 0.7
        assert dashboard["result_quality_metrics"]["persuasiveness"] == 0.75
        assert dashboard["priority_rule_coverage_rate"] == 0.5
        assert dashboard["priority_rule_latest_coverage_rate"] == 0.5
        assert dashboard["priority_rule_low_coverage_rate"] == 1.0
        assert dashboard["priority_rule_quality_summary"]["top_missing_titles"][0]["title"] == "조직 소개"
        assert dashboard["live_change_linked_outcomes"] == 0
        assert dashboard["live_change_success_gap"] == 0.0
        assert (workspace.analysis_dir / "kpi_dashboard.json").exists()

    def test_update_application_strategy_records_recent_change_action_learning(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )

        strategy = update_application_strategy(
            workspace,
            project=project,
            stage="writer",
            recent_change_action_check={
                "checked_count": 2,
                "covered_count": 1,
                "missing_count": 1,
                "coverage_rate": 0.5,
                "items": [
                    {"title": "채용 공고", "covered": True},
                    {"title": "조직 소개", "covered": False},
                ],
            },
        )

        learning = strategy["live_change_action_learning"]
        assert learning["latest_stage"] == "writer"
        assert learning["average_coverage_rate"] == 0.5
        assert learning["focus_titles"] == ["조직 소개"]
        assert learning["stage_reports"]["writer"]["covered_titles"] == ["채용 공고"]

    def test_build_outcome_dashboard_includes_live_change_action_learning(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        write_json(
            workspace.analysis_dir / "application_strategy.json",
            {
                "live_change_action_learning": {
                    "latest_stage": "interview",
                    "average_coverage_rate": 0.75,
                    "focus_titles": ["조직 소개"],
                    "stage_reports": {
                        "writer": {"coverage_rate": 0.5},
                        "interview": {"coverage_rate": 1.0},
                    },
                }
            },
        )

        dashboard = build_outcome_dashboard(workspace, project, "writer")

        assert dashboard["live_change_action_learning"]["latest_stage"] == "interview"
        assert dashboard["live_change_action_learning"]["average_coverage_rate"] == 0.75
        assert dashboard["live_change_action_learning"]["focus_titles"] == ["조직 소개"]

    def test_build_writer_result_quality_evaluations_exposes_result_dimensions(self):
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기와 문제해결 경험을 말씀해 주세요.")],
        )
        experiences = [
            Experience(
                id="exp-1",
                title="민원 분석",
                organization="테스트기관",
                period_start="2024-01-01",
                situation="민원 처리 기준이 모호했습니다.",
                task="분석 기준을 정리해야 했습니다.",
                action="직접 데이터를 분석하고 기준표를 만들었습니다.",
                result="처리 시간을 20% 줄였습니다.",
            )
        ]
        writer_text = """
## 블록 1: ASSUMPTIONS & MISSING FACTS

없음

## 블록 2: OUTLINE

개요

## 블록 3: DRAFT ANSWERS

Q1. 저는 직접 데이터를 분석하고 기준표를 만들어 처리 시간을 20% 줄였습니다. 이 경험을 바탕으로 기관 업무에서도 빠르게 기여하겠습니다.

## 블록 4: SELF-CHECK

확인 완료
"""
        result = build_writer_result_quality_evaluations(
            project,
            writer_text,
            experiences,
            [{"question_id": "q1", "experience_id": "exp-1"}],
        )

        assert result[0]["overall"] > 0
        assert "persuasiveness" in result[0]["details"]
        assert "defensibility" in result[0]["details"]
        assert "company_fit" in result[0]["details"]

    def test_build_self_intro_pack_merges_top001_and_updates_strategy(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
        )
        save_project(workspace, project)

        top001_pack = {
            "hooks": [{"content": "핵심 훅", "score": 0.9}],
            "versions": {"30s": "30초 버전", "60s": "60초 버전"},
            "expected_follow_ups": ["왜 우리 회사인가요?"],
        }

        with patch(
            "resume_agent.top001.integrator.Top001CoachEngine",
            return_value=MagicMock(generate_self_intro_pack=MagicMock(return_value=top001_pack)),
        ):
            intro_pack = build_self_intro_pack(workspace, project)

        assert intro_pack["top001_hooks"][0]["content"] == "핵심 훅"
        strategy = read_json_if_exists(workspace.analysis_dir / "application_strategy.json")
        assert strategy["self_intro_candidates"]["top001_versions"]["30s"] == "30초 버전"
        assert (workspace.analysis_dir / "self_intro_top001.json").exists()

    def test_build_research_strategy_translation_merges_top001_strategy(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기", detected_type=QuestionType.TYPE_A)],
        )
        save_project(workspace, project)
        company_analysis = MagicMock()
        company_analysis.answer_tone_hint = "근거 중심"
        company_analysis.taboo_phrases = ["열정"]
        company_analysis.core_values = ["공공성", "책임감"]
        company_analysis.preferred_evidence_types = ["협업"]

        top001_translation = {
            "strategic_signals": {
                "core_values": ["공공성"],
                "competencies": ["협업"],
                "interview_predictions": ["지원동기"],
                "differentiation": ["현장 실행력"],
            },
            "question_hooks": {"q1": ["공공성에 맞닿은 경험입니다"]},
            "interview_predictions": [{"q": "왜 우리 기관인가요?"}],
        }

        with patch(
            "resume_agent.top001.integrator.Top001ResearchTranslator",
            return_value=MagicMock(
                translate_research_to_strategy=MagicMock(return_value=top001_translation)
            ),
        ):
            translation = build_research_strategy_translation(
                workspace,
                project,
                company_analysis=company_analysis,
                source_grading={"cross_check": {"single_source_area_count": 0, "missing_area_count": 0}},
            )

        assert translation["top001"]["strategic_signals"]["core_values"] == ["공공성"]
        strategy = read_json_if_exists(workspace.analysis_dir / "application_strategy.json")
        assert strategy["company_signal_summary"]["core_values"] == ["공공성"]
        assert (workspace.analysis_dir / "research_strategy_translation_top001.json").exists()

    def test_build_research_strategy_translation_includes_recent_change_actions(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://example.com/jobs": {
                    "url": "https://example.com/jobs",
                    "title": "채용 공고",
                    "change_status": "changed",
                    "change_summary": "추가 신호: 데이터, 자동화",
                    "keywords": ["데이터", "자동화"],
                    "fetched_at": "2026-04-09T00:00:00+00:00",
                }
            },
        )

        translation = build_research_strategy_translation(
            workspace,
            project,
            source_grading={"cross_check": {"single_source_area_count": 0, "missing_area_count": 0}},
        )

        assert translation["recent_change_actions"]
        assert "추가 신호: 데이터, 자동화" in translation["recent_change_actions"][0]

    def test_build_research_strategy_translation_includes_effectiveness_priority_rules(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            questions=[Question(id="q1", order_no=1, question_text="지원동기")],
        )
        save_project(workspace, project)
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://example.com/jobs": {
                    "url": "https://example.com/jobs",
                    "title": "채용 공고",
                    "change_status": "changed",
                    "change_summary": "추가 신호: 데이터, 자동화",
                    "keywords": ["데이터", "자동화"],
                    "fetched_at": "2026-04-09T00:00:00+00:00",
                }
            },
        )
        artifact = GeneratedArtifact(
            id="writer-001",
            artifact_type=ArtifactType.WRITER,
            accepted=True,
            input_snapshot={
                "recent_change_action_check": {
                    "checked_count": 1,
                    "covered_count": 0,
                    "missing_count": 1,
                    "coverage_rate": 0.0,
                    "items": [{"title": "채용 공고", "covered": False}],
                }
            },
            output_path="artifacts/writer.md",
            raw_output_path="artifacts/writer_raw.md",
            validation=ValidationResult(passed=True),
            created_at=datetime.now(timezone.utc),
        )
        write_json(workspace.state_dir / "artifacts.json", [artifact.model_dump()])
        write_json(
            workspace.state_dir / "outcomes.json",
            [
                {
                    "artifact_id": "writer-001",
                    "company_name": "테스트공사",
                    "job_title": "데이터 분석",
                    "outcome": "interview_fail",
                }
            ],
        )

        translation = build_research_strategy_translation(
            workspace,
            project,
            source_grading={"cross_check": {"single_source_area_count": 0, "missing_area_count": 0}},
        )

        assert translation["recent_change_priority_rules"]
        assert "채용 공고" in " ".join(translation["recent_change_priority_rules"])
        assert translation["recent_change_effectiveness"]["linked_outcome_count"] == 1

    def test_assess_recent_change_action_coverage_detects_keywords(self):
        report = _assess_recent_change_action_coverage(
            "저는 데이터 자동화 역량을 바탕으로 지원했습니다.",
            [
                {
                    "title": "채용 공고",
                    "change_status": "changed",
                    "change_summary": "추가 신호: 데이터, 자동화",
                    "keywords": ["데이터", "자동화"],
                }
            ],
        )

        assert report["checked_count"] == 1
        assert report["covered_count"] == 1
        assert report["items"][0]["covered_keywords"] == ["데이터", "자동화"]

    def test_assess_recent_change_priority_rule_coverage_detects_missing_title_keywords(self):
        report = _assess_recent_change_priority_rule_coverage(
            "저는 데이터 자동화 역량을 기반으로 지원했습니다.",
            priority_live_updates=[
                {
                    "title": "채용 공고",
                    "keywords": ["데이터", "자동화"],
                }
            ],
            research_strategy_translation={
                "recent_change_effectiveness": {
                    "top_missing_titles": ["채용 공고"]
                }
            },
        )

        assert report["checked_count"] == 1
        assert report["covered_count"] == 1
        assert report["items"][0]["covered_keywords"] == ["데이터", "자동화"]

    def test_run_coach_writes_top001_analysis_and_application_strategy(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="협업 경험", detected_type=QuestionType.TYPE_C)],
        )
        save_project(workspace, project)
        artifact = {"rendered": "# coach", "allocations": [{"question_id": "q1", "experience_id": "exp_er_flow", "reason": "핵심 경험"}]}
        top001_analysis = {"suggestions": ["경험 근거를 더 명확히 정리하세요"], "coverage_report": {"top_experience_ids": ["exp_er_flow"]}}

        with patch("resume_agent.pipeline.classify_project_questions_with_llm_fallback", return_value=project):
            with patch("resume_agent.pipeline.analyze_gaps", return_value={"gaps": []}):
                with patch("resume_agent.pipeline.build_feedback_learning_context", return_value={}):
                    with patch("resume_agent.pipeline.build_coach_artifact", return_value=artifact):
                        with patch("resume_agent.pipeline.validate_coach_contract", return_value={"passed": True, "missing": []}):
                            with patch("resume_agent.pipeline.build_coach_prompt", return_value=workspace.outputs_dir / "latest_coach_prompt.md"):
                                with patch("resume_agent.pipeline.upsert_artifact"):
                                    with patch("resume_agent.pipeline.CheckpointManager"):
                                        with patch(
                                            "resume_agent.top001.integrator.Top001CoachEngine",
                                            return_value=MagicMock(analyze_experiences=MagicMock(return_value=top001_analysis)),
                                        ):
                                            result = run_coach(workspace)

        assert Path(result["top001_analysis_path"]).exists()
        strategy = read_json_if_exists(workspace.analysis_dir / "application_strategy.json")
        assert strategy["experience_priority"][0]["experience_id"] == "exp_er_flow"
        assert strategy["coach_recommendations"] == ["경험 근거를 더 명확히 정리하세요"]

    def test_run_interview_with_codex_writes_top001_defense_and_strategy(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="지원동기", detected_type=QuestionType.TYPE_A)],
        )
        save_project(workspace, project)
        (workspace.artifacts_dir / "writer.md").write_text(
            "## 블록 3: DRAFT ANSWERS\n\nQ1. 기관 가치와 맞닿은 협업 경험을 바탕으로 지원했습니다.",
            encoding="utf-8",
        )
        write_json(
            workspace.state_dir / "live_source_cache.json",
            {
                "https://example.com/jobs": {
                    "url": "https://example.com/jobs",
                    "title": "채용 공고",
                    "change_status": "changed",
                    "change_summary": "추가 신호: 데이터, 자동화",
                    "keywords": ["데이터", "자동화"],
                    "fetched_at": "2026-04-09T00:00:00+00:00",
                }
            },
        )
        top001_response = {
            "vulnerabilities": ["근거 부족"],
            "weak_response": True,
            "recommendations": ["수치 근거를 추가하세요"],
        }

        with patch("resume_agent.pipeline.analyze_company", return_value=MagicMock()):
            with patch("resume_agent.pipeline._get_success_cases_for_analysis", return_value=[]):
                with patch("resume_agent.pipeline.build_interview_prompt", return_value=workspace.outputs_dir / "latest_interview_prompt.md"):
                    with patch("resume_agent.pipeline.run_codex", return_value=0):
                        with patch("resume_agent.pipeline.normalize_contract_output", return_value="## 블록 1: INTERVIEW ASSUMPTIONS\n데이터 자동화"):
                            with patch("resume_agent.pipeline.validate_interview_contract", return_value={"passed": True, "missing": [], "semantic_missing": []}):
                                with patch("resume_agent.pipeline.build_interview_defense_simulations", return_value=[]):
                                    with patch("resume_agent.pipeline.upsert_artifact"):
                                        with patch("resume_agent.pipeline.CheckpointManager"):
                                            with patch(
                                                "resume_agent.top001.integrator.Top001InterviewEngine",
                                                return_value=MagicMock(simulate_interview=MagicMock(return_value=top001_response)),
                                            ):
                                                result = run_interview_with_codex(workspace)

        assert Path(result["top001_defense_path"]).exists()
        assert Path(result["interview_change_action_path"]).exists()
        assert Path(result["interview_priority_rule_audit_path"]).exists()
        strategy = read_json_if_exists(workspace.analysis_dir / "application_strategy.json")
        assert "근거 부족" in strategy["interview_pressure_points"]
        assert strategy["interview_strategy"]["weak_response_count"] == 1
        assert (
            strategy["live_change_action_learning"]["stage_reports"]["interview"][
                "coverage_rate"
            ]
            == 1.0
        )
        assert result["recent_change_action_check"]["covered_count"] == 1
        assert result["recent_change_priority_rule_check"]["checked_count"] >= 0
        assert result["priority_rule_quality_metric"]["coverage_rate"] >= 0.0

    def test_build_interview_defense_simulations_merges_top001_logic(self):
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="데이터 분석",
            company_type="공공",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="협업 경험을 설명해주세요",
                    detected_type=QuestionType.TYPE_C,
                )
            ],
        )
        experiences = [
            Experience(
                id="exp-1",
                title="협업 경험",
                organization="기관A",
                period_start="2024-01",
                action="협업 체계를 정리했습니다.",
                result="20% 개선",
            )
        ]
        writer_text = "## 블록 3: DRAFT ANSWERS\n\nQ1. 협업 체계를 정리해 20% 개선했습니다."
        question_map = [{"question_id": "q1", "experience_id": "exp-1"}]

        with patch(
            "resume_agent.top001.integrator.Top001InterviewEngine",
            return_value=MagicMock(
                simulate_interview=MagicMock(
                    return_value={
                        "vulnerabilities": ["근거 부족"],
                        "question_chains": [
                            {
                                "primary_question": "왜 그렇게 판단했나요?",
                                "depth_1_questions": ["비교 기준은 무엇인가요?"],
                            }
                        ],
                        "pressure_level": "high",
                        "recommendations": ["측정 기준을 먼저 제시하세요"],
                    }
                )
            ),
        ):
            simulations = build_interview_defense_simulations(
                project,
                writer_text,
                experiences,
                question_map,
                company_analysis=None,
            )

        assert "근거 부족" in simulations[0]["logical_vulnerabilities"]
        assert simulations[0]["logical_pressure_level"] == "high"
        assert "측정 기준을 먼저 제시하세요" in simulations[0]["improvement_suggestions"]

    def test_crawl_web_sources_auto_discovers_and_ingests(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(company_name="테스트기업", job_title="데이터 분석")
        save_project(workspace, project)

        from resume_agent.pipeline import crawl_web_sources_auto

        discovered = [
            {
                "query": "테스트기업 데이터 분석 채용",
                "url": "https://example.com/careers/data",
                "title": "채용 공고",
            }
        ]
        source = KnowledgeSource(
            id="web1",
            source_type=SourceType.USER_URL_PUBLIC,
            title="채용 공고",
            url="https://example.com/careers/data",
            raw_text="<html>공고</html>",
            cleaned_text="데이터 분석 채용 공고",
            meta=KnowledgeSourceMeta(),
        )

        with patch(
            "resume_agent.pipeline.discover_public_urls", return_value=discovered
        ):
            with patch(
                "resume_agent.pipeline.fetch_public_url_snapshot",
                return_value={
                    "url": "https://example.com/careers/data",
                    "title": "채용 공고",
                    "raw_text": "<html>공고</html>",
                    "cleaned_text": "데이터 분석 채용 공고",
                    "content_hash": "web-hash-1",
                    "fetched_at": "2026-04-09T00:00:00+00:00",
                    "status_code": 200,
                },
            ):
                with patch(
                    "resume_agent.pipeline.ingest_public_url", return_value=[source]
                ):
                    result = crawl_web_sources_auto(
                        workspace, max_results_per_query=1, max_urls=1
                    )

        assert result["discovered_url_count"] == 1
        assert result["ingested_url_count"] == 1
        assert Path(result["discovery_path"]).exists()


class TestCrawlWebSources:
    def test_ingests_public_url_into_knowledge_base(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)

        from resume_agent.pipeline import crawl_web_sources

        class DummyResponse:
            def __init__(self):
                self.text = "<html><head><title>테스트 회사</title></head><body><h1>채용 공고</h1><p>데이터 분석 및 협업 역량</p></body></html>"

            def raise_for_status(self):
                return None

        with patch("resume_agent.parsing.requests.get", return_value=DummyResponse()):
            result = crawl_web_sources(workspace, ["https://example.com/job"])

        assert result["source_count"] == 1
        kb = json.loads(
            (workspace.state_dir / "knowledge_sources.json").read_text(encoding="utf-8")
        )
        assert kb[0]["source_type"] == "user_url_public"
        assert kb[0]["url"] == "https://example.com/job"


class TestSafeReadText:
    def test_returns_empty_for_missing(self, tmp_path):
        assert safe_read_text(tmp_path / "nope.md") == ""

    def test_reads_content(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello", encoding="utf-8")
        assert safe_read_text(f) == "hello"


class TestReadJsonIfExists:
    def test_returns_default_for_missing(self, tmp_path):
        assert read_json_if_exists(tmp_path / "nope.json") == []

    def test_reads_json(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "val"}', encoding="utf-8")
        assert read_json_if_exists(f) == {"key": "val"}


class TestRelative:
    def test_returns_relative_string(self, tmp_path):
        root = tmp_path / "ws"
        child = root / "sub" / "file.md"
        assert relative(root, child) == "sub/file.md"


class TestRunCodexFallback:
    def test_writes_fallback_on_all_retries_fail(self, tmp_path):
        from resume_agent.executor import run_codex

        prompt = tmp_path / "prompt.md"
        prompt.write_text("test prompt", encoding="utf-8")
        output = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch("resume_agent.executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stderr="error", stdout=""
                )
                result = run_codex(prompt, tmp_path, output)

        assert result == 1
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "실패" in content
        assert "해결 방법" in content


class TestWriterPreconditions:
    def _project_with_question(self) -> ApplicationProject:
        return ApplicationProject(
            company_name="테스트회사",
            job_title="개발자",
            questions=[
                Question(
                    id="q1",
                    order_no=1,
                    question_text="지원 동기를 설명해주세요",
                    detected_type=QuestionType.TYPE_A,
                    char_limit=500,
                )
            ],
        )

    def _workspace_with_target(self, tmp_path: Path) -> Workspace:
        workspace = Workspace(tmp_path)
        workspace.ensure()
        (workspace.targets_dir / "example_target.md").write_text(
            "# target", encoding="utf-8"
        )
        return workspace

    def test_run_writer_requires_question_map(self, tmp_path: Path):
        workspace = self._workspace_with_target(tmp_path)
        save_project(workspace, self._project_with_question())

        with pytest.raises(RuntimeError) as exc:
            run_writer(workspace)

        assert "question_map.json" in str(exc.value)
        assert "resume-agent coach" in str(exc.value)

    def test_run_writer_requires_questions(self, tmp_path: Path):
        workspace = self._workspace_with_target(tmp_path)
        save_project(
            workspace,
            ApplicationProject(company_name="테스트회사", job_title="개발자"),
        )
        write_json(
            workspace.analysis_dir / "question_map.json",
            [{"question_id": "q1", "experience_ids": ["exp-1"]}],
        )

        with pytest.raises(RuntimeError) as exc:
            run_writer(workspace)

        assert "질문이 없습니다" in str(exc.value)

    def test_run_writer_with_codex_requires_target_file(self, tmp_path: Path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        save_project(workspace, self._project_with_question())
        write_json(
            workspace.analysis_dir / "question_map.json",
            [{"question_id": "q1", "experience_ids": ["exp-1"]}],
        )

        with patch(
            "resume_agent.cli_tool_manager.get_available_tools",
            return_value={"codex": "codex"},
        ):
            with pytest.raises(RuntimeError) as exc:
                run_writer_with_codex(workspace)

        assert "writer target 파일이 없습니다" in str(exc.value)

    def test_run_writer_with_codex_requires_writer_brief(self, tmp_path: Path):
        workspace = self._workspace_with_target(tmp_path)
        save_project(workspace, self._project_with_question())
        write_json(
            workspace.analysis_dir / "question_map.json",
            [{"question_id": "q1", "experience_id": "exp-1"}],
        )

        with patch(
            "resume_agent.cli_tool_manager.get_available_tools",
            return_value={"codex": "codex"},
        ):
            with pytest.raises(RuntimeError) as exc:
                run_writer_with_codex(workspace)

        assert "writer_brief.json" in str(exc.value)
        assert "resume-agent coach" in str(exc.value)

    def test_run_writer_with_codex_requires_selected_tool(self, tmp_path: Path):
        workspace = self._workspace_with_target(tmp_path)
        save_project(workspace, self._project_with_question())
        write_json(
            workspace.analysis_dir / "question_map.json",
            [{"question_id": "q1", "experience_ids": ["exp-1"]}],
        )

        with patch(
            "resume_agent.cli_tool_manager.get_available_tools",
            return_value={"codex": "codex"},
        ):
            with pytest.raises(RuntimeError) as exc:
                run_writer_with_codex(workspace, tool="gemini")

        assert "선택한 CLI 도구를 찾을 수 없습니다: gemini" in str(exc.value)
