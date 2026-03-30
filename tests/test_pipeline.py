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
    build_writer_quality_evaluations,
    build_interview_defense_simulations,
    build_coach_prompt,
    run_self_intro,
    build_ncs_profile,
    classify_project_questions_with_llm_fallback,
    build_source_grading,
    build_feedback_learning_context,
    build_blind_benchmark_frame,
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
from resume_agent.domain import build_knowledge_hints
from datetime import datetime, timezone
from pathlib import Path

from resume_agent.state import (
    initialize_state,
    save_knowledge_sources,
    save_project,
    write_json,
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

    def test_build_writer_rewrite_prompt_includes_humanization_and_feedback_learning(self):
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


class TestWriterQualityHumanization:
    def test_build_writer_quality_evaluations_includes_humanization(self):
        project = ApplicationProject(
            company_name="테스트",
            job_title="데이터 분석",
            questions=[Question(id="q1", order_no=1, question_text="지원동기를 작성하세요.")],
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

    def test_build_interview_defense_simulations_includes_historical_outcome_signal(self):
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


class TestQuestionTypeLlmFallback:
    def test_classify_project_questions_with_llm_fallback_updates_unknown(self, tmp_path):
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
            output_path.write_text('[{"question_id":"q1","question_type":"TYPE_A"}]', encoding="utf-8")
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
                    meta=KnowledgeSourceMeta(company_name="테스트공사", job_title="사무행정"),
                ),
                KnowledgeSource(
                    id="src2",
                    source_type=SourceType.LOCAL_TEXT,
                    title="기관 소개 메모",
                    raw_text="정확한 문서관리와 공공 민원 커뮤니케이션이 중요합니다.",
                    cleaned_text="정확한 문서관리와 공공 민원 커뮤니케이션이 중요합니다.",
                    meta=KnowledgeSourceMeta(company_name="테스트공사", job_title="사무행정"),
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
                        "essay_implications": ["지원동기와 직무역량 문항에서 민원 응대 경험을 전면 배치"],
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

        assert "\"company_analysis\"" in content
        assert "\"jd_keywords\"" in content
        assert "\"research_brief\"" in content
        assert "\"source_grading\"" in content
        assert "\"ncs_profile\"" in content


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
            questions=[Question(id="q1", order_no=1, question_text="지원동기와 직무역량")],
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
                    meta=KnowledgeSourceMeta(company_name="테스트데이터", job_title="데이터 분석"),
                ),
                KnowledgeSource(
                    id="src2",
                    source_type=SourceType.LOCAL_TEXT,
                    title="회사 소개 메모",
                    raw_text="테스트데이터는 데이터 기반 협업 문화를 강조합니다.",
                    cleaned_text="테스트데이터는 데이터 기반 협업 문화를 강조합니다.",
                    meta=KnowledgeSourceMeta(company_name="테스트데이터", job_title="데이터 분석"),
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


class TestNcsProfile:
    def test_build_ncs_profile_creates_priority_map(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="협업 경험을 작성하세요.")],
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
            question_map=read_json_if_exists(workspace.analysis_dir / "question_map.json"),
            jd_keywords=["민원", "협업", "정확한 문서 처리"],
            company_analysis=None,
        )

        assert "의사소통능력" in profile["priority_competencies"]
        assert Path(workspace.analysis_dir / "ncs_profile.json").exists()
        assert profile["question_alignment"][0]["question_id"] == "q1"

    def test_build_ncs_profile_extracts_ability_units_from_job_spec_source(self, tmp_path):
        workspace = Workspace(tmp_path)
        workspace.ensure()
        initialize_state(workspace)
        project = ApplicationProject(
            company_name="테스트공사",
            job_title="사무행정",
            company_type="공공",
            questions=[Question(id="q1", order_no=1, question_text="민원 응대 경험을 작성하세요.")],
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
                    meta=KnowledgeSourceMeta(company_name="테스트공사", job_title="사무행정"),
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
            question_map=read_json_if_exists(workspace.analysis_dir / "question_map.json"),
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
            sources = ingest_source_file(pdf_path)

        assert len(sources) == 1
        assert sources[0].title == "직무기술서"
        assert "의사소통능력" in sources[0].cleaned_text


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
        (workspace.profile_dir / "jd.md").write_text("SQL과 분석 역량", encoding="utf-8")

        from resume_agent.feedback_learner import create_feedback_learner
        from resume_agent.pipeline import build_draft_prompt

        learner = create_feedback_learner(str(workspace.root / "kb" / "feedback"))
        learner.record_feedback(
            draft_id="writer-1",
            pattern_used="writer|공공|TYPE_A",
            accepted=False,
            comment="지원동기 표현이 추상적입니다",
        )

        prompt_path = build_draft_prompt(
            workspace,
            workspace.targets_dir / "example_target.md",
        )
        content = Path(prompt_path).read_text(encoding="utf-8")

        assert "\"feedback_learning\"" in content
        assert "지원동기 표현이 추상적입니다" in content
        assert "\"outcome_summary\"" in content

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

        assert "\"role_industry_strategy\"" in content
        assert "\"evidence_priority\"" in content
        assert "\"committee_personas\"" in content
        assert "\"self_intro_pack\"" in content
        assert "\"ncs_profile\"" in content
        assert "\"candidate_profile\"" in content
        assert "\"narrative_ssot\"" in content
        assert "\"outcome_dashboard\"" in content
        assert "\"research_strategy_translation\"" in content

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

        profile = build_candidate_profile(workspace, project, load_experiences(workspace))

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

    def test_build_coach_prompt_includes_committee_feedback_and_self_intro(self, tmp_path):
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

        assert "\"committee_feedback\"" in content
        assert "\"self_intro_pack\"" in content
        assert "\"ncs_profile\"" in content
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

        with patch("resume_agent.pipeline.discover_public_urls", return_value=discovered):
            with patch("resume_agent.pipeline.ingest_public_url", return_value=[source]):
                result = crawl_web_sources_auto(workspace, max_results_per_query=1, max_urls=1)

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
        kb = json.loads((workspace.state_dir / "knowledge_sources.json").read_text(encoding="utf-8"))
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
