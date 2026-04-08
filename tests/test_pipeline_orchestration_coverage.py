from __future__ import annotations

import json
import sys
import types
from contextlib import ExitStack
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
    ws.prompts_dir = tmp_path / "prompts"
    ws.profile_dir = tmp_path / "profile"
    ws.state_dir = tmp_path / "state"
    ws.targets_dir = ws.profile_dir / "targets"
    ws.artifacts_dir = tmp_path / "artifacts"
    ws.runs_dir = tmp_path / "runs"
    for path in [
        ws.analysis_dir,
        ws.outputs_dir,
        ws.prompts_dir,
        ws.profile_dir,
        ws.state_dir,
        ws.targets_dir,
        ws.artifacts_dir,
        ws.runs_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    (ws.targets_dir / "example_target.md").write_text("# target", encoding="utf-8")
    (ws.analysis_dir / "question_map.json").write_text(
        '[{"question_id": "q1", "experience_ids": ["exp-1"]}]', encoding="utf-8"
    )
    (ws.analysis_dir / "writer_brief.json").write_text(
        '{"question_strategies":[{"question_id":"q1","core_message":"핵심"}]}',
        encoding="utf-8",
    )
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


def _read_json_side_effect(path):
    if Path(path).name == "question_map.json":
        return [{"question_id": "q1", "experience_ids": ["exp-1"]}]
    if Path(path).name == "writer_brief.json":
        return {"question_strategies": [{"question_id": "q1", "core_message": "핵심"}]}
    return []


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
            "resume_agent.cli_tool_manager.get_available_tools",
            return_value={"codex": "codex"},
        ):
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
        with patch(
            "resume_agent.cli_tool_manager.get_available_tools",
            return_value={"codex": "codex"},
        ):
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
                                                        side_effect=_read_json_side_effect,
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
                                                                    "resume_agent.pipeline.build_writer_result_quality_evaluations",
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
    assert (ws.artifacts_dir / "writer_result_quality.json").exists()


def test_run_writer_with_codex_prefers_patina_max_over_patina(tmp_path: Path):
    from resume_agent.models import CompanyAnalysis
    from resume_agent.pipeline import run_writer_with_codex

    ws = _workspace(tmp_path)
    project = _project()
    raw_output = ws.runs_dir / "run_patina_max" / "raw_writer.md"
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text("writer output", encoding="utf-8")
    company = CompanyAnalysis(company_name="테스트회사", company_type="공공")

    with patch("resume_agent.pipeline.load_project", return_value=project):
        with patch(
            "resume_agent.cli_tool_manager.get_available_tools",
            return_value={"codex": "codex"},
        ):
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
                                                        side_effect=_read_json_side_effect,
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
                                                                    "resume_agent.pipeline.build_writer_result_quality_evaluations",
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
                                                                                                AssertionError(
                                                                                                    "single patina should not run"
                                                                                                )
                                                                                            )
                                                                                        ),
                                                                                        "resume_agent.patina_max_bridge": SimpleNamespace(
                                                                                            run_patina_max=lambda **kwargs: {
                                                                                                "mode": "max",
                                                                                                "models": ["codex"],
                                                                                                "dispatch": "direct",
                                                                                                "selected_model": "codex",
                                                                                                "selected_text": "normalized writer output",
                                                                                                "outputs_by_model": {
                                                                                                    "codex": {
                                                                                                        "success": True,
                                                                                                        "processed_count": 1,
                                                                                                        "char_limit_report": {"issues": []},
                                                                                                        "total_abs_delta": 0,
                                                                                                    }
                                                                                                },
                                                                                                "warnings": [],
                                                                                                "reassembled_text": "normalized writer output",
                                                                                                "selection_report": {"reason": "selected"},
                                                                                                "run_meta": {"selected_model": "codex"},
                                                                                            }
                                                                                        ),
                                                                                    },
                                                                                ):
                                                                                    result = run_writer_with_codex(
                                                                                        ws,
                                                                                        patina=True,
                                                                                        patina_max=True,
                                                                                    )

    assert result["patina_result"] is None
    assert result["patina_max_result"]["selected_model"] == "codex"
    assert (ws.artifacts_dir / "writer_draft_patina_max.md").exists()


def test_run_writer_with_codex_propagates_tool_to_all_rewrites(tmp_path: Path):
    from resume_agent.pipeline import run_writer_with_codex

    ws = _workspace(tmp_path)
    project = _project()
    run_outputs = [
        "initial output",
        "corrected output",
        "rewritten output",
    ]
    tool_calls: list[str] = []

    def fake_run_codex(prompt_path, cwd, output_path, tool="codex"):
        tool_calls.append(tool)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(run_outputs[len(tool_calls) - 1], encoding="utf-8")
        return 0

    quality_before = [{"question_order": 1, "overall_score": 0.6}]
    quality_after = [{"question_order": 1, "overall_score": 0.9}]
    result_quality_before = [{"question_order": 1, "result_quality_score": 0.5}]
    result_quality_after = [{"question_order": 1, "result_quality_score": 0.8}]

    with ExitStack() as stack:
        stack.enter_context(
            patch("resume_agent.pipeline.load_project", return_value=project)
        )
        stack.enter_context(
            patch(
                "resume_agent.cli_tool_manager.get_available_tools",
                return_value={"gemini": "gemini"},
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_draft_prompt",
                return_value=ws.outputs_dir / "latest_draft_prompt.md",
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.run_codex", side_effect=fake_run_codex)
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.normalize_contract_output",
                side_effect=lambda text, headings: text,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.validate_writer_contract",
                side_effect=[
                    _validation(True),
                    _validation(True),
                    _validation(True),
                ],
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_char_limit_report",
                return_value={"passed": True, "issues": []},
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.merge_writer_validation_with_char_report",
                side_effect=lambda validation, report: validation,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.load_experiences",
                return_value=[_experience()],
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.audit_facts",
                side_effect=[["fact mismatch"], []],
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.read_json_if_exists",
                side_effect=_read_json_side_effect,
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.build_ncs_profile", return_value={})
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_quality_evaluations",
                side_effect=[quality_before, quality_after],
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_result_quality_evaluations",
                side_effect=[result_quality_before, result_quality_after],
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.needs_writer_rewrite", return_value=True)
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_rewrite_quality_report",
                return_value={"markdown": "report"},
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.should_accept_writer_rewrite",
                return_value=True,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.enforce_writer_char_limits",
                return_value=(
                    "rewritten output",
                    {"passed": True, "issues": []},
                    False,
                ),
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.calculate_readability_score",
                return_value={"score": 100, "feedback": []},
            )
        )
        stack.enter_context(patch("resume_agent.pipeline.upsert_artifact"))
        stack.enter_context(patch("resume_agent.pipeline.CheckpointManager"))
        result = run_writer_with_codex(ws, tool="gemini")

    assert result["tool"] == "gemini"
    assert tool_calls == ["gemini", "gemini", "gemini"]


def test_run_writer_with_codex_quality_error_writes_structured_status(tmp_path: Path):
    from resume_agent.pipeline import run_writer_with_codex

    ws = _workspace(tmp_path)
    project = _project()

    def fake_run_codex(prompt_path, cwd, output_path, tool="codex"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("normalized writer output", encoding="utf-8")
        return 0

    with ExitStack() as stack:
        stack.enter_context(
            patch("resume_agent.pipeline.load_project", return_value=project)
        )
        stack.enter_context(
            patch(
                "resume_agent.cli_tool_manager.get_available_tools",
                return_value={"codex": "codex"},
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_draft_prompt",
                return_value=ws.outputs_dir / "latest_draft_prompt.md",
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.run_codex", side_effect=fake_run_codex)
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.normalize_contract_output",
                side_effect=lambda text, headings: text,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.validate_writer_contract",
                return_value=_validation(True),
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_char_limit_report",
                return_value={"passed": True, "issues": []},
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.merge_writer_validation_with_char_report",
                side_effect=lambda validation, report: validation,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.load_experiences",
                return_value=[_experience()],
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.audit_facts", return_value=[])
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.read_json_if_exists",
                side_effect=_read_json_side_effect,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline._read_llm_run_meta",
                side_effect=[
                    {
                        "selected_tool": "opencode",
                        "attempted_tools": ["codex", "opencode"],
                        "fallback_reason": "usage_limit",
                    },
                    {
                        "selected_tool": "opencode",
                        "attempted_tools": ["codex", "opencode"],
                        "fallback_reason": "usage_limit",
                    },
                ],
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.build_ncs_profile", return_value={})
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_quality_evaluations",
                side_effect=RuntimeError("quality offline"),
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_result_quality_evaluations",
                return_value=[],
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.needs_writer_rewrite", return_value=False)
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.enforce_writer_char_limits",
                return_value=(
                    "normalized writer output",
                    {"passed": True, "issues": []},
                    False,
                ),
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.calculate_readability_score",
                return_value={"score": 100, "feedback": []},
            )
        )
        stack.enter_context(patch("resume_agent.pipeline.upsert_artifact"))
        stack.enter_context(patch("resume_agent.pipeline.CheckpointManager"))
        run_writer_with_codex(ws)

    quality_payload = __import__("json").loads(
        (ws.artifacts_dir / "writer_quality.json").read_text(encoding="utf-8")
    )
    assert quality_payload == [
        {"status": "error", "error_reason": "quality offline"}
    ]


def test_run_writer_with_codex_fact_warning_blocks_approval_but_keeps_draft(
    tmp_path: Path,
):
    from resume_agent.pipeline import run_writer_with_codex

    ws = _workspace(tmp_path)
    project = _project()

    def fake_run_codex(prompt_path, cwd, output_path, tool="codex"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("normalized writer output", encoding="utf-8")
        output_path.with_suffix(".meta.json").write_text(
            json.dumps(
                {
                    "selected_tool": "opencode",
                    "attempted_tools": ["codex", "opencode"],
                    "fallback_reason": "usage_limit",
                }
            ),
            encoding="utf-8",
        )
        return 0

    with ExitStack() as stack:
        stack.enter_context(
            patch("resume_agent.pipeline.load_project", return_value=project)
        )
        stack.enter_context(
            patch(
                "resume_agent.cli_tool_manager.get_available_tools",
                return_value={"codex": "codex"},
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_draft_prompt",
                return_value=ws.outputs_dir / "latest_draft_prompt.md",
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.run_codex", side_effect=fake_run_codex)
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.normalize_contract_output",
                return_value=(
                    "## 블록 1: ASSUMPTIONS & MISSING FACTS\n"
                    "a\n## 블록 2: OUTLINE\nb\n## 블록 3: DRAFT ANSWERS\n"
                    "Q1. answer\n## 블록 4: SELF-CHECK\nc"
                ),
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.validate_writer_contract",
                return_value=_validation(True),
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_char_limit_report",
                return_value={"passed": True, "issues": []},
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.merge_writer_validation_with_char_report",
                side_effect=lambda validation, report: validation,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.load_experiences",
                return_value=[_experience()],
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.audit_facts", return_value=["fact warning"])
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.read_json_if_exists",
                side_effect=_read_json_side_effect,
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline._read_llm_run_meta",
                side_effect=[
                    {
                        "selected_tool": "opencode",
                        "attempted_tools": ["codex", "opencode"],
                        "fallback_reason": "usage_limit",
                    },
                    {
                        "selected_tool": "opencode",
                        "attempted_tools": ["codex", "opencode"],
                        "fallback_reason": "usage_limit",
                    },
                ],
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.build_ncs_profile", return_value={})
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_quality_evaluations",
                return_value=[],
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.build_writer_result_quality_evaluations",
                return_value=[],
            )
        )
        stack.enter_context(
            patch("resume_agent.pipeline.needs_writer_rewrite", return_value=False)
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.enforce_writer_char_limits",
                return_value=(
                    "## 블록 1: ASSUMPTIONS & MISSING FACTS\n"
                    "a\n## 블록 2: OUTLINE\nb\n## 블록 3: DRAFT ANSWERS\n"
                    "Q1. answer\n## 블록 4: SELF-CHECK\nc",
                    {"passed": True, "issues": []},
                    False,
                ),
            )
        )
        stack.enter_context(
            patch(
                "resume_agent.pipeline.calculate_readability_score",
                return_value={"score": 100, "feedback": []},
            )
        )
        stack.enter_context(patch("resume_agent.pipeline.upsert_artifact"))
        stack.enter_context(patch("resume_agent.pipeline.CheckpointManager"))
        result = run_writer_with_codex(ws)

    assert result["approved"] is False
    assert result["selected_tool"] == "opencode"
    assert result["attempted_tools"] == ["codex", "opencode"]
    assert result["fallback_reason"] == "usage_limit"
    assert not (ws.artifacts_dir / "writer.md").exists()
    assert (ws.artifacts_dir / "writer_draft.md").exists()


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
