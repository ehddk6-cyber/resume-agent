from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def stub_sentence_transformers(monkeypatch):
    fake_module = types.ModuleType("sentence_transformers")

    class DummySentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

        def encode(self, *args, **kwargs):
            return [0.0]

    fake_module.SentenceTransformer = DummySentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)


def _workspace(tmp_path: Path):
    ws = MagicMock()
    ws.root = tmp_path
    ws.analysis_dir = tmp_path / "analysis"
    ws.artifacts_dir = tmp_path / "artifacts"
    ws.outputs_dir = tmp_path / "outputs"
    ws.profile_dir = tmp_path / "profile"
    ws.state_dir = tmp_path / "state"
    ws.sources_raw_dir = tmp_path / "sources" / "raw"
    ws.analysis_dir.mkdir(parents=True, exist_ok=True)
    ws.artifacts_dir.mkdir(parents=True, exist_ok=True)
    ws.outputs_dir.mkdir(parents=True, exist_ok=True)
    ws.profile_dir.mkdir(parents=True, exist_ok=True)
    ws.state_dir.mkdir(parents=True, exist_ok=True)
    ws.sources_raw_dir.mkdir(parents=True, exist_ok=True)
    ws.ensure = MagicMock()
    return ws


def _question(qid: str = "q1", qtype=None):
    from resume_agent.models import Question, QuestionType

    return Question(
        id=qid,
        order_no=1,
        question_text="협업 경험을 설명해주세요",
        detected_type=qtype or QuestionType.TYPE_C,
    )


def _project():
    from resume_agent.models import ApplicationProject

    return ApplicationProject(
        company_name="테스트회사",
        job_title="분석가",
        company_type="공공",
        questions=[_question()],
    )


def _experience(exp_id: str = "exp-1", **kwargs):
    from resume_agent.models import EvidenceLevel, Experience, VerificationStatus

    defaults = dict(
        id=exp_id,
        title="협업 경험",
        organization="테스트기관",
        period_start="2024-01",
        situation="팀 이슈를 정리했습니다.",
        task="조율 과제가 있었습니다.",
        action="협업과 조율 중심으로 대응했습니다.",
        result="성과를 냈습니다.",
        personal_contribution="핵심 판단을 맡았습니다.",
        metrics="",
        tags=["협업"],
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
    )
    defaults.update(kwargs)
    return Experience(**defaults)


def _knowledge_source(title: str, cleaned_text: str, source_type=None, url: str | None = None):
    from resume_agent.models import KnowledgeSource, SourceType

    return KnowledgeSource(
        id=title,
        title=title,
        cleaned_text=cleaned_text,
        raw_text=cleaned_text,
        source_type=source_type or SourceType.LOCAL_TEXT,
        url=url,
    )


def test_build_feedback_selection_payload_skips_blank_ids():
    from resume_agent.pipeline import _build_feedback_selection_payload

    payload = _build_feedback_selection_payload(
        [
            {"question_id": "q1", "question_type": "TYPE_A", "experience_id": "exp-1"},
            {"question_id": "q2", "question_type": "TYPE_B", "experience_id": "  "},
            {"question_id": "q3", "question_type": "TYPE_C", "experience_id": "exp-1"},
        ],
        writer_brief={
            "question_strategies": [
                {
                    "question_id": "q1",
                    "question_order": 1,
                    "question_type": "TYPE_A",
                    "primary_experience_id": "exp-1",
                    "core_message": "운영 안정성을 입증한다.",
                    "winning_angle": "운영 기준 중심",
                    "differentiation_line": "기준과 증빙으로 차별화",
                    "target_impression": "책임감 있는 운영형",
                }
            ]
        },
    )

    assert payload["selected_experience_ids"] == ["exp-1"]
    assert len(payload["question_experience_map"]) == 2
    assert payload["question_strategy_map"][0]["winning_angle"] == "운영 기준 중심"


def test_build_feedback_learning_context_handles_learner_failure(tmp_path: Path):
    from resume_agent.pipeline import build_feedback_learning_context

    ws = _workspace(tmp_path)
    project = _project()

    with patch.dict(
        sys.modules,
        {"resume_agent.feedback_learner": SimpleNamespace(create_feedback_learner=lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))}
    ):
        with patch("resume_agent.pipeline.read_json_if_exists", return_value=[]):
            context = build_feedback_learning_context(ws, "writer", project=project)

    assert context["top_patterns"] == []
    assert context["current_pattern"].startswith("writer|")


def test_build_candidate_profile_adds_abstraction_blind_spot(tmp_path: Path):
    from resume_agent.pipeline import build_candidate_profile

    ws = _workspace(tmp_path)
    project = _project()
    profile = SimpleNamespace(style_preference="담백")
    abstract_exp = _experience(
        action="항상 가치와 역량 성장을 고민했습니다.",
        result="성장과 기여라는 추상 성과를 강조했습니다.",
        personal_contribution="",
        metrics="",
        tags=[],
    )

    with patch("resume_agent.pipeline.load_profile", return_value=profile):
        result = build_candidate_profile(ws, project, [abstract_exp])

    assert any("추상 표현 비중" in item for item in result["blind_spots"])


def test_build_outcome_dashboard_collects_hotspots(tmp_path: Path):
    from resume_agent.pipeline import build_outcome_dashboard

    ws = _workspace(tmp_path)
    project = _project()
    feedback_context = {
        "strategy_outcome_summary": {
            "experience_stats_by_question_type": {
                "TYPE_A": {"exp-1": {"weighted_net_score": 4, "total_uses": 2}}
            }
        },
        "current_pattern": "writer|공공|TYPE_A",
        "overall_success_rate": 0.7,
        "outcome_summary": {},
        "recommended_pattern": "writer|공공|TYPE_A",
    }

    with patch("resume_agent.pipeline.build_feedback_learning_context", return_value=feedback_context):
        dashboard = build_outcome_dashboard(ws, project)

    assert dashboard["high_risk_hotspots"][0]["experience_id"] == "exp-1"


def test_build_outcome_dashboard_includes_live_change_effectiveness(tmp_path: Path):
    from datetime import datetime, timezone

    from resume_agent.models import ArtifactType, GeneratedArtifact, OutcomeResult, ValidationResult
    from resume_agent.pipeline import build_outcome_dashboard
    from resume_agent.state import write_json

    ws = _workspace(tmp_path)
    project = _project()
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
            },
            "recent_change_action_check": {
                "checked_count": 1,
                "covered_count": 1,
                "missing_count": 0,
                "coverage_rate": 1.0,
                "items": [
                    {"title": "채용 공고", "covered": True},
                ],
            }
        },
        output_path="artifacts/writer.md",
        raw_output_path="artifacts/writer_raw.md",
        validation=ValidationResult(passed=True),
        created_at=datetime.now(timezone.utc),
    )
    outcome = OutcomeResult(
        artifact_id="writer-001",
        company_name=project.company_name,
        job_title=project.job_title,
        outcome="offer_received",
    )
    write_json(ws.state_dir / "artifacts.json", [artifact.model_dump()])
    write_json(ws.state_dir / "outcomes.json", [outcome.model_dump()])

    feedback_context = {
        "strategy_outcome_summary": {
            "experience_stats_by_question_type": {
                "TYPE_A": {"exp-1": {"weighted_net_score": 4, "total_uses": 2}}
            }
        },
        "current_pattern": "writer|공공|TYPE_A",
        "overall_success_rate": 0.7,
        "outcome_summary": {},
        "recommended_pattern": "writer|공공|TYPE_A",
    }

    with patch("resume_agent.pipeline.build_feedback_learning_context", return_value=feedback_context):
        dashboard = build_outcome_dashboard(ws, project, "writer")

    assert dashboard["live_change_effectiveness"]["linked_outcome_count"] == 1
    assert dashboard["live_change_effectiveness"]["coverage_bands"]["high"]["success_rate"] == 1.0
    assert dashboard["priority_rule_quality_summary"]["average_coverage_rate"] == 0.5
    assert dashboard["priority_rule_quality_summary"]["top_missing_titles"][0]["title"] == "조직 소개"


def test_build_cumulative_effect_report_writes_combined_payload(tmp_path: Path):
    from datetime import datetime, timezone

    from resume_agent.models import ArtifactType, GeneratedArtifact, OutcomeResult, ValidationResult
    from resume_agent.pipeline import build_cumulative_effect_report
    from resume_agent.state import write_json

    ws = _workspace(tmp_path)
    project = _project()
    artifact = GeneratedArtifact(
        id="writer-001",
        artifact_type=ArtifactType.WRITER,
        accepted=True,
        input_snapshot={
            "recent_change_action_check": {
                "checked_count": 1,
                "covered_count": 1,
                "missing_count": 0,
                "coverage_rate": 1.0,
                "items": [
                    {"title": "채용 공고", "covered": True},
                ],
            }
        },
        output_path="artifacts/writer.md",
        raw_output_path="artifacts/writer_raw.md",
        validation=ValidationResult(passed=True),
        created_at=datetime.now(timezone.utc),
    )
    outcome = OutcomeResult(
        artifact_id="writer-001",
        company_name=project.company_name,
        job_title=project.job_title,
        outcome="offer_received",
    )
    write_json(ws.state_dir / "artifacts.json", [artifact.model_dump()])
    write_json(ws.state_dir / "outcomes.json", [outcome.model_dump()])

    feedback_context = {
        "strategy_outcome_summary": {
            "experience_stats_by_question_type": {
                "TYPE_A": {"exp-1": {"weighted_net_score": 4, "total_uses": 2}}
            }
        },
        "current_pattern": "writer|공공|TYPE_A",
        "overall_success_rate": 0.7,
        "outcome_summary": {"outcome_breakdown": {"offer_received": 1}},
        "recommended_pattern": "writer|공공|TYPE_A",
    }

    with patch("resume_agent.pipeline.build_feedback_learning_context", return_value=feedback_context):
        report = build_cumulative_effect_report(ws, project, "writer")

    assert report["outcome_dashboard"]["live_change_effectiveness"]["linked_outcome_count"] == 1
    assert report["live_change_effectiveness"]["linked_outcome_count"] == 1
    assert isinstance(report["live_change_action_learning"], dict)
    assert report["tracked_outcomes"]["offer_received"] == 1
    assert (ws.analysis_dir / "cumulative_effect_report.json").exists()


def test_evaluate_narrative_ssot_alignment_marks_missing_claims_and_offtrack():
    from resume_agent.pipeline import evaluate_narrative_ssot_alignment

    result = evaluate_narrative_ssot_alignment(
        "협업으로 문제를 해결했습니다.",
        experience=_experience("exp-2"),
        narrative_ssot={
            "core_claims": ["고객 응대를 개선했다", "정량 성과를 냈다"],
            "evidence_experience_ids": ["exp-1"],
            "answer_anchor": "정량 근거",
        },
    )

    assert result["missing_claims"] == ["고객 응대를 개선했다", "정량 성과를 냈다"]
    assert any("우선 선정되지 않은 경험" in item for item in result["offtrack_signals"])


def test_build_committee_feedback_context_reads_committee_round_risks(tmp_path: Path):
    from resume_agent.pipeline import build_committee_feedback_context

    ws = _workspace(tmp_path)
    sessions = [
        {
            "mode": "committee",
            "turns": [
                {
                    "risk_areas": ["근거 부족"],
                    "follow_up_risk_areas": ["수치 약함"],
                    "interviewer_persona": "위원장",
                    "committee_rounds": [{"risk_areas": ["재질문 취약"], "persona": "실무위원"}],
                    "committee_summary": {"verdict": "보완 필요"},
                }
            ],
        }
    ]

    with patch("resume_agent.pipeline.read_json_if_exists", return_value=sessions):
        context = build_committee_feedback_context(ws)

    assert "재질문 취약" in context["recurring_risks"]
    assert "실무위원" in context["persona_panel"]


def test_discover_company_public_urls_skips_blank_queries_and_handles_errors(tmp_path: Path):
    from resume_agent.pipeline import discover_company_public_urls

    ws = _workspace(tmp_path)
    project = _project()
    brief = {"key_questions": ["", "핵심 문화는 무엇인가?"]}

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch("resume_agent.pipeline.build_research_brief", return_value=brief):
            with patch(
                "resume_agent.pipeline.discover_public_urls",
                side_effect=[[{"url": "https://a.com"}], RuntimeError("search fail"), []],
            ):
                payload = discover_company_public_urls(ws, max_results_per_query=1)

    assert payload["results"][0]["url"] == "https://a.com"


def test_build_ncs_profile_handles_job_spec_and_filters_non_ncs_sources(tmp_path: Path):
    from resume_agent.models import SourceType
    from resume_agent.pipeline import build_ncs_profile

    ws = _workspace(tmp_path)
    (ws.profile_dir / "jd.md").write_text("능력단위 데이터", encoding="utf-8")
    source_with_marker = _knowledge_source("JD", "직업기초능력 의사소통", SourceType.LOCAL_TEXT)
    source_without_marker = _knowledge_source("Memo", "일반 메모", SourceType.LOCAL_TEXT)

    with patch("resume_agent.pipeline.load_knowledge_sources", return_value=[source_with_marker, source_without_marker]):
        with patch("resume_agent.pipeline._extract_jd_keywords_for_research", return_value=["분석"]):
            with patch("resume_agent.pipeline.read_json_if_exists", return_value=[]):
                with patch.dict(
                    sys.modules,
                    {
                        "resume_agent.pdf_utils": SimpleNamespace(
                            extract_ncs_job_spec=lambda text: {
                                "ability_units": ["자료 분석"],
                                "ability_unit_elements": ["지표 정리"],
                                "ncs_competencies": ["의사소통능력"],
                            }
                        )
                    },
                ):
                    profile = build_ncs_profile(
                        ws,
                        project=_project(),
                        experiences=[_experience()],
                        question_map=[],
                        company_analysis=None,
                    )

    assert "의사소통능력" in profile["priority_competencies"]
    assert "profile/jd.md" in profile["job_spec_source_titles"]


def test_expected_ncs_competencies_falls_back_to_type_mapping():
    from resume_agent.models import QuestionType
    from resume_agent.pipeline import _expected_ncs_competencies

    result = _expected_ncs_competencies("missing", QuestionType.TYPE_C, {"question_alignment": []})

    assert result


def test_extract_jd_keywords_for_research_falls_back_to_tokenization(tmp_path: Path):
    from resume_agent.pipeline import _extract_jd_keywords_for_research

    ws = _workspace(tmp_path)
    (ws.profile_dir / "jd.md").write_text("데이터 분석과 정확한 보고 역량", encoding="utf-8")

    with patch("resume_agent.pdf_utils.extract_jd_keywords", side_effect=RuntimeError("broken")):
        keywords = _extract_jd_keywords_for_research(ws)

    assert "데이터" in keywords


def test_build_research_brief_adds_question_map_prompt(tmp_path: Path):
    from resume_agent.pipeline import build_research_brief

    ws = _workspace(tmp_path)
    project = _project()

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch("resume_agent.pipeline.load_knowledge_sources", return_value=[]):
            with patch("resume_agent.pipeline._extract_jd_keywords_for_research", return_value=[]):
                with patch("resume_agent.pipeline.read_json_if_exists", return_value=[{"question_id": "q1"}]):
                    brief = build_research_brief(ws)

    assert any("문항별" in item for item in brief["key_questions"])


def test_grade_source_reliability_covers_multiple_branches():
    from resume_agent.models import SourceType
    from resume_agent.pipeline import _grade_source_reliability

    blog_source = _knowledge_source(
        "blog",
        "내용",
        SourceType.USER_URL_PUBLIC,
        "https://blog.naver.com/post",
    )
    neutral_source = _knowledge_source(
        "neutral",
        "내용",
        SourceType.USER_URL_PUBLIC,
        "https://example.com/random",
    )
    manual_source = _knowledge_source("manual", "내용", SourceType.MANUAL_NOTE)

    assert _grade_source_reliability(blog_source)[0] == "E"
    assert _grade_source_reliability(neutral_source)[0] == "C"
    assert _grade_source_reliability(manual_source)[0] == "D"


def test_detect_source_conflicts_finds_conflicting_pairs():
    from resume_agent.pipeline import _detect_source_conflicts

    left = _knowledge_source("left", "정규직 채용 공고")
    right = _knowledge_source("right", "계약직 전환 가능")

    conflicts = _detect_source_conflicts([left, right])

    assert conflicts[0]["topic"] == "고용 형태"


def test_run_semantic_source_review_handles_fallback_paths(tmp_path: Path):
    from resume_agent.pipeline import _run_semantic_source_review

    ws = _workspace(tmp_path)
    brief = {"objective": "test", "key_questions": []}

    with patch("resume_agent.pipeline.run_codex", return_value=1):
        failed = _run_semantic_source_review(ws, brief, [], [])

    assert "자동 의미 검증에 실패" in failed["summary"]

    with patch("resume_agent.pipeline.run_codex", return_value=0):
        with patch("resume_agent.pipeline.safe_read_text", return_value="not-json"):
            unparsable = _run_semantic_source_review(ws, brief, [], [])

    assert "파싱하지 못해" in unparsable["summary"]

    with patch("resume_agent.pipeline.run_codex", return_value=0):
        with patch("resume_agent.pipeline.safe_read_text", return_value='["bad"]'):
            invalid = _run_semantic_source_review(ws, brief, [], [])

    assert "형식이 올바르지" in invalid["summary"]


def test_build_humanization_guard_returns_expected_sections():
    from resume_agent.pipeline import build_humanization_guard

    guard = build_humanization_guard()

    assert "avoid_openers" in guard
    assert "preferred_moves" in guard


def test_load_feedback_context_supports_success_and_fallback(tmp_path: Path):
    from resume_agent.pipeline import load_feedback_context

    ws = _workspace(tmp_path)
    history_item = SimpleNamespace(comment="코멘트", artifact_type="writer", pattern_used="writer|공공|TYPE_A")
    learner = SimpleNamespace(
        get_recommendation=lambda context: [{"pattern_id": "writer|공공|TYPE_A"}],
        get_insights=lambda: {"total_feedback": 3},
        db=SimpleNamespace(get_feedback_history=lambda limit=10: [history_item]),
    )

    with patch("resume_agent.pipeline.load_project", return_value=_project()):
        with patch.dict(
            sys.modules,
            {"resume_agent.feedback_learner": SimpleNamespace(create_feedback_learner=lambda *_: learner)},
        ):
            success = load_feedback_context(ws, "writer")

    assert success["recommendations"]
    assert success["recent_comments"] == ["코멘트"]

    with patch.dict(
        sys.modules,
        {"resume_agent.feedback_learner": SimpleNamespace(create_feedback_learner=lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))}
    ):
        fallback = load_feedback_context(ws, "writer")

    assert fallback["recommendations"] == []


def test_classify_project_questions_with_llm_fallback_handles_multiple_payload_shapes(tmp_path: Path):
    from resume_agent.models import QuestionType
    from resume_agent.pipeline import classify_project_questions_with_llm_fallback

    ws = _workspace(tmp_path)
    project = _project()

    with patch("resume_agent.pipeline.classify_question_with_confidence", return_value=(QuestionType.TYPE_UNKNOWN, 0.1)):
        with patch("resume_agent.pipeline.run_codex", return_value=1):
            unchanged = classify_project_questions_with_llm_fallback(ws, project)
    assert unchanged.questions[0].detected_type == QuestionType.TYPE_UNKNOWN

    with patch("resume_agent.pipeline.classify_question_with_confidence", return_value=(QuestionType.TYPE_UNKNOWN, 0.1)):
        with patch("resume_agent.pipeline.run_codex", side_effect=RuntimeError("oauth failure")):
            exception_fallback = classify_project_questions_with_llm_fallback(ws, project)
    assert exception_fallback.questions[0].detected_type == QuestionType.TYPE_UNKNOWN

    with patch("resume_agent.pipeline.classify_question_with_confidence", return_value=(QuestionType.TYPE_UNKNOWN, 0.1)):
        with patch("resume_agent.pipeline.run_codex", return_value=0):
            with patch("resume_agent.pipeline.safe_read_text", return_value="not-json"):
                invalid_json = classify_project_questions_with_llm_fallback(ws, project)
    assert invalid_json.questions[0].detected_type == QuestionType.TYPE_UNKNOWN

    with patch("resume_agent.pipeline.classify_question_with_confidence", return_value=(QuestionType.TYPE_UNKNOWN, 0.1)):
        with patch("resume_agent.pipeline.run_codex", return_value=0):
            with patch("resume_agent.pipeline.safe_read_text", return_value='{"bad": true}'):
                wrong_shape = classify_project_questions_with_llm_fallback(ws, project)
    assert wrong_shape.questions[0].detected_type == QuestionType.TYPE_UNKNOWN

    with patch("resume_agent.pipeline.classify_question_with_confidence", return_value=(QuestionType.TYPE_UNKNOWN, 0.1)):
        with patch("resume_agent.pipeline.run_codex", return_value=0):
            with patch(
                "resume_agent.pipeline.safe_read_text",
                return_value='[1, {"question_id":"missing","question_type":"TYPE_A"}, {"question_id":"q1","question_type":"BAD"}, {"question_id":"q1","question_type":"TYPE_A"}]',
            ):
                updated = classify_project_questions_with_llm_fallback(ws, project)
    assert updated.questions[0].detected_type == QuestionType.TYPE_A


def test_run_gap_analysis_saves_project_and_gap_report(tmp_path: Path):
    from resume_agent.pipeline import run_gap_analysis

    ws = _workspace(tmp_path)
    project = _project()

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch("resume_agent.pipeline.classify_project_questions_with_llm_fallback", return_value=project):
            with patch("resume_agent.pipeline.save_project") as mock_save_project:
                with patch("resume_agent.pipeline.load_experiences", return_value=[_experience()]):
                    with patch("resume_agent.pipeline.analyze_gaps", return_value={"gaps": []}):
                        result = run_gap_analysis(ws)

    mock_save_project.assert_called_once()
    assert result["report"] == {"gaps": []}
