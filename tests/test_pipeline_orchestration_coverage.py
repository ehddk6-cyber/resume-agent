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
    ws.outputs_dir = tmp_path / "outputs"
    ws.profile_dir = tmp_path / "profile"
    ws.state_dir = tmp_path / "state"
    ws.targets_dir = tmp_path / "targets"
    ws.artifacts_dir = tmp_path / "artifacts"
    ws.runs_dir = tmp_path / "runs"
    for path in [
        ws.analysis_dir,
        ws.outputs_dir,
        ws.profile_dir,
        ws.state_dir,
        ws.targets_dir,
        ws.artifacts_dir,
        ws.runs_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    ws.ensure = MagicMock()
    return ws


def _project():
    from resume_agent.models import ApplicationProject, Question, QuestionType

    return ApplicationProject(
        company_name="테스트회사",
        job_title="개발자",
        company_type="공공",
        questions=[
            Question(
                id="q1",
                order_no=1,
                question_text="협업 경험을 설명해주세요",
                detected_type=QuestionType.TYPE_C,
                char_limit=1000,
            )
        ],
    )


def _experience():
    from resume_agent.models import EvidenceLevel, Experience, VerificationStatus

    return Experience(
        id="exp-1",
        title="협업 경험",
        organization="테스트기관",
        period_start="2024-01",
        situation="상황",
        task="과제",
        action="행동",
        result="결과 30% 향상",
        personal_contribution="기여",
        metrics="30% 향상",
        tags=["협업", "성과"],
        evidence_level=EvidenceLevel.L3,
        verification_status=VerificationStatus.VERIFIED,
    )


def _validation(passed: bool = True, missing: list[str] | None = None):
    return {"passed": passed, "missing": missing or [], "semantic_missing": []}


def test_run_coach_success_flow(tmp_path: Path):
    from resume_agent.models import ArtifactType
    from resume_agent.pipeline import run_coach

    ws = _workspace(tmp_path)
    project = _project()
    artifact = {"rendered": "# coach", "allocations": [{"question_id": "q1"}]}

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch(
            "resume_agent.pipeline.classify_project_questions_with_llm_fallback",
            return_value=project,
        ):
            with patch("resume_agent.pipeline.save_project") as mock_save_project:
                with patch(
                    "resume_agent.pipeline.load_experiences", return_value=[_experience()]
                ):
                    with patch(
                        "resume_agent.pipeline.analyze_gaps", return_value={"gaps": []}
                    ):
                        with patch(
                            "resume_agent.pipeline.build_feedback_learning_context",
                            return_value={
                                "outcome_summary": {"score": 1},
                                "strategy_outcome_summary": {"foo": "bar"},
                                "current_pattern": "coach|공공|TYPE_C",
                            },
                        ):
                            with patch(
                                "resume_agent.pipeline.build_coach_artifact",
                                return_value=artifact,
                            ):
                                with patch(
                                    "resume_agent.pipeline.validate_coach_contract",
                                    return_value={"passed": True, "missing": []},
                                ):
                                    with patch(
                                        "resume_agent.pipeline.build_coach_prompt",
                                        return_value=ws.outputs_dir
                                        / "latest_coach_prompt.md",
                                    ):
                                        with patch(
                                            "resume_agent.pipeline.upsert_artifact"
                                        ) as mock_upsert:
                                            with patch(
                                                "resume_agent.pipeline.CheckpointManager"
                                            ) as mock_cp_mgr:
                                                result = run_coach(ws)

    mock_save_project.assert_called_once()
    mock_upsert.assert_called_once()
    snapshot = mock_upsert.call_args[0][1]
    assert snapshot.artifact_type == ArtifactType.COACH
    assert result["validation"]["passed"] is True
    mock_cp_mgr.return_value.save_checkpoint.assert_called_once()


def test_run_writer_with_codex_failure_skips_accept_and_patina(tmp_path: Path):
    from resume_agent.pipeline import run_writer_with_codex

    ws = _workspace(tmp_path)
    project = _project()
    raw_output = ws.runs_dir / "run1" / "raw_writer.md"
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text("bad output", encoding="utf-8")

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch(
            "resume_agent.pipeline.build_draft_prompt",
            return_value=ws.outputs_dir / "latest_draft_prompt.md",
        ):
            with patch("resume_agent.pipeline.run_codex", return_value=1):
                with patch(
                    "resume_agent.pipeline.normalize_contract_output",
                    return_value="normalized",
                ):
                    with patch(
                        "resume_agent.pipeline.validate_writer_contract",
                        return_value=_validation(False, ["missing-block"]),
                    ):
                        with patch(
                            "resume_agent.pipeline.build_writer_char_limit_report",
                            return_value={"passed": False, "issues": []},
                        ):
                            with patch(
                                "resume_agent.pipeline.merge_writer_validation_with_char_report",
                                side_effect=lambda validation, report: validation,
                            ):
                                with patch(
                                    "resume_agent.pipeline.load_experiences",
                                    return_value=[_experience()],
                                ):
                                    with patch(
                                        "resume_agent.pipeline.audit_facts",
                                        return_value=[],
                                    ):
                                        with patch(
                                            "resume_agent.pipeline.calculate_readability_score",
                                            return_value={"score": 100, "feedback": []},
                                        ):
                                            with patch(
                                                "resume_agent.pipeline.upsert_artifact"
                                            ) as mock_upsert:
                                                with patch(
                                                    "resume_agent.pipeline.CheckpointManager"
                                                ) as mock_cp_mgr:
                                                    result = run_writer_with_codex(
                                                        ws, patina=True
                                                    )

    assert result["exit_code"] == 1
    assert result["validation"]["passed"] is False
    assert result["patina_result"] is None
    mock_upsert.assert_called_once()
    mock_cp_mgr.return_value.save_checkpoint.assert_called_once()
    assert not (ws.artifacts_dir / "writer.md").exists()


def test_run_writer_with_codex_success_and_patina_failure_fallback(tmp_path: Path):
    from resume_agent.models import CompanyAnalysis
    from resume_agent.pipeline import run_writer_with_codex

    ws = _workspace(tmp_path)
    project = _project()
    raw_output = ws.runs_dir / "run2" / "raw_writer.md"
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text("writer output", encoding="utf-8")
    company = CompanyAnalysis(company_name="테스트회사", company_type="공공")

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch("resume_agent.pipeline.analyze_company", return_value=company):
            with patch(
                "resume_agent.pipeline._get_success_cases_for_analysis",
                return_value=[],
            ):
                with patch(
                    "resume_agent.pipeline.build_draft_prompt",
                    return_value=ws.outputs_dir / "latest_draft_prompt.md",
                ):
                    with patch("resume_agent.pipeline.run_codex", return_value=0):
                        with patch(
                            "resume_agent.pipeline.normalize_contract_output",
                            return_value="normalized writer output",
                        ):
                            with patch(
                                "resume_agent.pipeline.validate_writer_contract",
                                return_value=_validation(True),
                            ):
                                with patch(
                                    "resume_agent.pipeline.build_writer_char_limit_report",
                                    return_value={"passed": True, "issues": []},
                                ):
                                    with patch(
                                        "resume_agent.pipeline.merge_writer_validation_with_char_report",
                                        side_effect=lambda validation, report: validation,
                                    ):
                                        with patch(
                                            "resume_agent.pipeline.load_experiences",
                                            return_value=[_experience()],
                                        ):
                                            with patch(
                                                "resume_agent.pipeline.audit_facts",
                                                return_value=[],
                                            ):
                                                with patch(
                                                    "resume_agent.pipeline.read_json_if_exists",
                                                    return_value=[],
                                                ):
                                                    with patch(
                                                        "resume_agent.pipeline.build_ncs_profile",
                                                        return_value={},
                                                    ):
                                                        with patch(
                                                            "resume_agent.pipeline.build_writer_quality_evaluations",
                                                            return_value=[],
                                                        ):
                                                            with patch(
                                                                "resume_agent.pipeline.needs_writer_rewrite",
                                                                return_value=False,
                                                            ):
                                                                with patch(
                                                                    "resume_agent.pipeline.enforce_writer_char_limits",
                                                                    return_value=(
                                                                        "normalized writer output",
                                                                        {
                                                                            "passed": True,
                                                                            "issues": [],
                                                                        },
                                                                        False,
                                                                    ),
                                                                ):
                                                                    with patch(
                                                                        "resume_agent.pipeline.calculate_readability_score",
                                                                        return_value={
                                                                            "score": 100,
                                                                            "feedback": [],
                                                                        },
                                                                    ):
                                                                        with patch.dict(
                                                                            sys.modules,
                                                                            {
                                                                                "resume_agent.feedback_learner": SimpleNamespace(
                                                                                    create_feedback_learner=lambda *_: (_ for _ in ()).throw(
                                                                                        RuntimeError(
                                                                                            "feedback down"
                                                                                        )
                                                                                    )
                                                                                ),
                                                                                "resume_agent.patina_bridge": SimpleNamespace(
                                                                                    run_patina=lambda **kwargs: (_ for _ in ()).throw(
                                                                                        RuntimeError(
                                                                                            "patina boom"
                                                                                        )
                                                                                    )
                                                                                ),
                                                                            },
                                                                        ):
                                                                            result = run_writer_with_codex(
                                                                                ws,
                                                                                patina=True,
                                                                            )

    assert result["validation"]["passed"] is True
    assert result["patina_result"]["warnings"]
    assert "patina 실행 실패" in result["patina_result"]["warnings"][0]
    assert (ws.artifacts_dir / "writer.md").exists()
    assert (ws.artifacts_dir / "writer_quality.json").exists()


def test_run_self_intro_builds_artifact_and_snapshot(tmp_path: Path):
    from resume_agent.pipeline import run_self_intro

    ws = _workspace(tmp_path)
    project = _project()
    intro_pack = {
        "opening_hook": "저는 문제를 해결하는 지원자입니다.",
        "thirty_second_frame": ["핵심 경험", "기여 포인트"],
        "sixty_second_frame": ["문제", "행동", "결과"],
        "focus_keywords": ["협업"],
        "banned_patterns": ["항상"],
        "committee_watchouts": ["수치 근거 부족"],
    }

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch("resume_agent.pipeline.analyze_company", side_effect=RuntimeError("no company")):
            with patch(
                "resume_agent.pipeline.build_self_intro_pack",
                return_value=intro_pack,
            ):
                with patch(
                    "resume_agent.pipeline.build_committee_feedback_context",
                    return_value={"recurring_risks": ["근거 부족"]},
                ):
                    with patch("resume_agent.pipeline.upsert_artifact") as mock_upsert:
                        result = run_self_intro(ws)

    assert (ws.artifacts_dir / "self_intro.md").exists()
    assert result["analysis_path"].endswith("self_intro_pack.json")
    mock_upsert.assert_called_once()


def test_run_interview_with_codex_handles_defense_and_feedback_failures(tmp_path: Path):
    from resume_agent.models import CompanyAnalysis
    from resume_agent.pipeline import run_interview_with_codex

    ws = _workspace(tmp_path)
    project = _project()
    raw_output = ws.runs_dir / "run3" / "raw_interview.md"
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text("interview output", encoding="utf-8")
    company = CompanyAnalysis(company_name="테스트회사", company_type="공공")

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch("resume_agent.pipeline.analyze_company", return_value=company):
            with patch(
                "resume_agent.pipeline._get_success_cases_for_analysis",
                return_value=[],
            ):
                with patch(
                    "resume_agent.pipeline.build_interview_prompt",
                    return_value=ws.outputs_dir / "latest_interview_prompt.md",
                ):
                    with patch("resume_agent.pipeline.run_codex", return_value=0):
                        with patch(
                            "resume_agent.pipeline.normalize_contract_output",
                            return_value="normalized interview output",
                        ):
                            with patch(
                                "resume_agent.pipeline.validate_interview_contract",
                                return_value=_validation(False, ["missing-interview"]),
                            ):
                                with patch(
                                    "resume_agent.pipeline.load_experiences",
                                    return_value=[_experience()],
                                ):
                                    with patch(
                                        "resume_agent.pipeline.read_json_if_exists",
                                        return_value=[],
                                    ):
                                        with patch(
                                            "resume_agent.pipeline.build_feedback_learning_context",
                                            return_value={},
                                        ):
                                            with patch(
                                                "resume_agent.pipeline.build_ncs_profile",
                                                return_value={},
                                            ):
                                                with patch(
                                                    "resume_agent.pipeline.build_interview_defense_simulations",
                                                    side_effect=RuntimeError("defense fail"),
                                                ):
                                                    with patch.dict(
                                                        sys.modules,
                                                        {
                                                            "resume_agent.feedback_learner": SimpleNamespace(
                                                                create_feedback_learner=lambda *_: (_ for _ in ()).throw(
                                                                    RuntimeError("feedback fail")
                                                                )
                                                            )
                                                        },
                                                    ):
                                                        result = run_interview_with_codex(ws)

    assert result["validation"]["passed"] is False
    assert result["defense_simulations"] == []
    assert (ws.artifacts_dir / "interview_defense.json").exists()
    assert not (ws.artifacts_dir / "interview.md").exists()


def test_run_export_success_with_docx_skip(tmp_path: Path):
    from resume_agent.models import ArtifactType, GeneratedArtifact, ValidationResult
    from resume_agent.pipeline import run_export

    ws = _workspace(tmp_path)
    project = _project()
    artifacts = [
        GeneratedArtifact(
            id="writer-1",
            artifact_type=ArtifactType.WRITER,
            accepted=True,
            input_snapshot={},
            output_path="artifacts/writer.md",
            raw_output_path="artifacts/writer.md",
            validation=ValidationResult(passed=True),
        )
    ]
    (ws.artifacts_dir / "writer.md").write_text("# writer", encoding="utf-8")
    (ws.artifacts_dir / "interview.md").write_text("# interview", encoding="utf-8")
    (ws.artifacts_dir / "coach.md").write_text("# coach", encoding="utf-8")
    (ws.artifacts_dir / "self_intro.md").write_text("# self intro", encoding="utf-8")

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch("resume_agent.pipeline.load_artifacts", return_value=artifacts):
            with patch(
                "resume_agent.pipeline.latest_accepted_artifacts",
                return_value=artifacts,
            ):
                with patch("resume_agent.pipeline.read_json_if_exists", return_value={}):
                    with patch("resume_agent.pipeline.upsert_artifact") as mock_upsert:
                        with patch("resume_agent.pipeline.CheckpointManager") as mock_cp_mgr:
                            with patch.dict(
                                sys.modules,
                                {
                                    "resume_agent.docx_export": SimpleNamespace(
                                        export_artifacts_to_docx=lambda **kwargs: None,
                                        is_docx_available=lambda: False,
                                    )
                                },
                            ):
                                result = run_export(ws)

    assert result["accepted_count"] == 1
    assert result["docx_path"] is None
    assert (ws.artifacts_dir / "export.md").exists()
    assert (ws.artifacts_dir / "export.json").exists()
    mock_upsert.assert_called_once()
    mock_cp_mgr.return_value.save_checkpoint.assert_called_once()
