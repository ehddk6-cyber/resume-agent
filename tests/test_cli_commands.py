"""CLI 명령어 핸들러 테스트 — mocking 패턴"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────
# 공통 유틸리티
# ──────────────────────────────────────────────────


def _make_args(workspace: str = "/tmp/ws", **kwargs) -> argparse.Namespace:
    return argparse.Namespace(workspace=workspace, **kwargs)


def _mock_workspace(tmp_path: Path) -> MagicMock:
    ws = MagicMock()
    ws.root = tmp_path
    ws.state_dir = tmp_path / "state"
    ws.outputs_dir = tmp_path / "outputs"
    ws.analysis_dir = tmp_path / "analysis"
    ws.profile_dir = tmp_path / "profile"
    ws.ensure = MagicMock()
    ws.resolve = MagicMock(side_effect=lambda x: tmp_path / x)
    return ws


# ──────────────────────────────────────────────────
# cmd_init 테스트
# ──────────────────────────────────────────────────


class TestCmdInit:
    def test_basic_init(self, tmp_path: Path):
        from resume_agent.cli import cmd_init

        args = _make_args(str(tmp_path / "new_ws"))
        with patch("resume_agent.cli.init_workspace") as mock_init:
            with patch("resume_agent.cli.crawl_base") as mock_crawl:
                ws = _mock_workspace(tmp_path)
                mock_init.return_value = ws
                mock_crawl.return_value = {
                    "source_count": 5,
                    "stored_count": 5,
                    "analysis_path": "/tmp/analysis.md",
                }
                cmd_init(args)


# ──────────────────────────────────────────────────
# cmd_wizard 테스트
# ──────────────────────────────────────────────────


class TestCmdWizard:
    def test_basic_wizard(self, tmp_path: Path):
        from resume_agent.cli import cmd_wizard

        args = _make_args(str(tmp_path), import_experiences=None, jd=None)
        with patch("resume_agent.cli.run_wizard") as mock_wizard:
            with patch("resume_agent.cli.crawl_base") as mock_crawl:
                ws = _mock_workspace(tmp_path)
                mock_wizard.return_value = {"workspace": ws}
                mock_crawl.return_value = {
                    "source_count": 5,
                    "stored_count": 5,
                    "analysis_path": "/tmp/analysis.md",
                }
                cmd_wizard(args)
            mock_wizard.assert_called_once()


# ──────────────────────────────────────────────────
# cmd_edit 테스트
# ──────────────────────────────────────────────────


class TestCmdEdit:
    def test_basic_edit(self, tmp_path: Path):
        from resume_agent.cli import cmd_edit

        args = _make_args(str(tmp_path))
        with patch("resume_agent.editor.run_editor") as mock_editor:
            with patch("resume_agent.cli.Workspace") as MockWS:
                MockWS.return_value = _mock_workspace(tmp_path)
                cmd_edit(args)
                mock_editor.assert_called_once()


# ──────────────────────────────────────────────────
# cmd_interactive 테스트
# ──────────────────────────────────────────────────


class TestCmdInteractive:
    def test_basic_interactive(self, tmp_path: Path):
        from resume_agent.cli import cmd_interactive

        args = _make_args(str(tmp_path))
        with patch("resume_agent.cli.run_interactive_coach") as mock_interactive:
            with patch("resume_agent.cli.Workspace") as MockWS:
                MockWS.return_value = _mock_workspace(tmp_path)
                cmd_interactive(args)
                mock_interactive.assert_called_once()


# ──────────────────────────────────────────────────
# cmd_crawl_base 테스트
# ──────────────────────────────────────────────────


class TestCmdCrawlBase:
    def test_basic_crawl(self, tmp_path: Path):
        from resume_agent.cli import cmd_crawl_base

        args = _make_args(str(tmp_path), path=None)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.crawl_base") as mock_crawl:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_crawl.return_value = {
                    "source_count": 5,
                    "stored_count": 5,
                    "analysis_path": "/tmp/analysis.md",
                }
                cmd_crawl_base(args)

    def test_with_path(self, tmp_path: Path):
        from resume_agent.cli import cmd_crawl_base

        args = _make_args(str(tmp_path), path=str(tmp_path / "sources"))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.crawl_base") as mock_crawl:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_crawl.return_value = {
                    "source_count": 3,
                    "stored_count": 3,
                    "analysis_path": "/tmp/analysis.md",
                }
                cmd_crawl_base(args)


class TestCmdSyncBase:
    def test_basic_sync(self, tmp_path: Path):
        from resume_agent.cli import cmd_sync_base

        args = _make_args(str(tmp_path), path=None)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.crawl_base") as mock_crawl:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_crawl.return_value = {
                    "source_count": 7,
                    "stored_count": 7,
                    "analysis_path": "/tmp/analysis.md",
                }
                cmd_sync_base(args)


# ──────────────────────────────────────────────────
# cmd_crawl_web 테스트
# ──────────────────────────────────────────────────


class TestCmdCrawlWeb:
    def test_basic_crawl(self, tmp_path: Path):
        from resume_agent.cli import cmd_crawl_web

        args = _make_args(str(tmp_path), url=["https://example.com"])
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.crawl_web_sources") as mock_crawl:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_crawl.return_value = {
                    "source_count": 1,
                    "stored_count": 1,
                    "analysis_path": "/tmp/analysis.md",
                }
                cmd_crawl_web(args)


# ──────────────────────────────────────────────────
# cmd_crawl_web_auto 테스트
# ──────────────────────────────────────────────────


class TestCmdCrawlWebAuto:
    def test_basic_auto_crawl(self, tmp_path: Path):
        from resume_agent.cli import cmd_crawl_web_auto

        args = _make_args(str(tmp_path), max_results_per_query=3, max_urls=8)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.crawl_web_sources_auto") as mock_crawl:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_crawl.return_value = {
                    "discovered_url_count": 10,
                    "ingested_url_count": 8,
                    "stored_count": 8,
                    "discovery_path": "/tmp/discovery.json",
                }
                cmd_crawl_web_auto(args)


# ──────────────────────────────────────────────────
# cmd_ingest 테스트
# ──────────────────────────────────────────────────


class TestCmdIngest:
    def test_basic_ingest(self, tmp_path: Path):
        from resume_agent.cli import cmd_ingest

        args = _make_args(str(tmp_path))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.ingest_examples") as mock_ingest:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_ingest.return_value = ["/tmp/file1.md", "/tmp/file2.md"]
                cmd_ingest(args)


# ──────────────────────────────────────────────────
# cmd_analyze 테스트
# ──────────────────────────────────────────────────


class TestCmdAnalyze:
    def test_without_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_analyze

        args = _make_args(str(tmp_path), run_codex=False)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_analysis_prompt") as mock_build:
                with patch("resume_agent.cli.next_step") as mock_next:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_next.return_value = "다음 단계"
                    cmd_analyze(args)

    def test_with_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_analyze

        args = _make_args(str(tmp_path), run_codex=True, tool="codex")
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_analysis_prompt") as mock_build:
                with patch("resume_agent.cli.run_codex") as mock_codex:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_codex.return_value = 0
                    cmd_analyze(args)


class TestCmdProfile:
    def test_profile_command_updates_snapshot(self, tmp_path: Path):
        from resume_agent.cli import cmd_profile

        args = _make_args(str(tmp_path), answer=["과거 답변"])
        with patch("resume_agent.cli.Workspace") as MockWS:
            ws = _mock_workspace(tmp_path)
            MockWS.return_value = ws
            with patch("resume_agent.state.load_experiences", return_value=[]):
                cmd_profile(args)


class TestCmdCompany:
    def test_company_command_profiles_target_company(self, tmp_path: Path):
        from resume_agent.cli import cmd_company
        from resume_agent.models import ApplicationProject

        args = _make_args(
            str(tmp_path),
            company_name="테스트기업",
            job_title="백엔드",
            company_type="공공",
            job_description_file=None,
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            ws = _mock_workspace(tmp_path)
            MockWS.return_value = ws
            with patch("resume_agent.state.load_project") as mock_project:
                with patch("resume_agent.state.load_experiences", return_value=[]):
                    with patch("resume_agent.state.load_success_cases", return_value=[]):
                        mock_project.return_value = ApplicationProject()
                        cmd_company(args)


# ──────────────────────────────────────────────────
# cmd_draft 테스트
# ──────────────────────────────────────────────────


class TestCmdDraft:
    def test_without_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_draft

        args = _make_args(str(tmp_path), target="profile/target.md", run_codex=False)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_draft_prompt") as mock_build:
                with patch("resume_agent.cli.next_step") as mock_next:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_next.return_value = "다음 단계"
                    cmd_draft(args)

    def test_with_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_draft

        args = _make_args(
            str(tmp_path), target="profile/target.md", run_codex=True, tool="codex"
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_draft_prompt") as mock_build:
                with patch("resume_agent.cli.run_codex") as mock_codex:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_codex.return_value = 0
                    cmd_draft(args)


# ──────────────────────────────────────────────────
# cmd_coach 테스트
# ──────────────────────────────────────────────────


class TestCmdCoach:
    def test_without_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_coach

        args = _make_args(str(tmp_path), run_codex=False)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_coach") as mock_coach:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_coach.return_value = {
                    "path": "/tmp/coach.md",
                    "prompt_path": "/tmp/prompt.md",
                    "validation": {"passed": True, "missing": []},
                }
                cmd_coach(args)

    def test_with_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_coach

        args = _make_args(str(tmp_path), run_codex=True, tool="codex")
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_coach") as mock_coach:
                with patch("resume_agent.cli.run_codex") as mock_codex:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_coach.return_value = {
                        "path": "/tmp/coach.md",
                        "prompt_path": "/tmp/prompt.md",
                        "validation": {"passed": True, "missing": []},
                    }
                    mock_codex.return_value = 0
                    cmd_coach(args)

    def test_with_missing_headings(self, tmp_path: Path):
        from resume_agent.cli import cmd_coach

        args = _make_args(str(tmp_path), run_codex=False)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_coach") as mock_coach:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_coach.return_value = {
                    "path": "/tmp/coach.md",
                    "prompt_path": "/tmp/prompt.md",
                    "validation": {"passed": False, "missing": ["## PURPOSE"]},
                }
                cmd_coach(args)


# ──────────────────────────────────────────────────
# cmd_writer 테스트
# ──────────────────────────────────────────────────


class TestCmdWriter:
    def test_parser_keeps_writer_default_target(self):
        from resume_agent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["writer", "/tmp/ws"])
        assert args.target == "profile/targets/example_target.md"
        assert args.patina_max is False

    def test_parser_accepts_patina_max_options(self):
        from resume_agent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "writer",
                "/tmp/ws",
                "--patina-max",
                "--patina-max-models",
                "claude,codex",
                "--patina-max-dispatch",
                "direct",
            ]
        )
        assert args.patina_max is True
        assert args.patina_max_models == "claude,codex"
        assert args.patina_max_dispatch == "direct"

    def test_without_codex_uses_custom_target(self, tmp_path: Path):
        from resume_agent.cli import cmd_writer

        args = _make_args(
            str(tmp_path),
            target="profile/targets/custom.md",
            run_codex=False,
            patina=False,
            patina_mode="audit",
            patina_profile="resume",
            patina_max=False,
            patina_max_models=None,
            patina_max_dispatch=None,
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_writer") as mock_writer:
                ws = _mock_workspace(tmp_path)
                MockWS.return_value = ws
                mock_writer.return_value = {"prompt_path": "/tmp/prompt.md"}
                cmd_writer(args)
                mock_writer.assert_called_once_with(
                    ws,
                    tmp_path / "profile/targets/custom.md",
                )

    def test_with_codex_uses_default_target(self, tmp_path: Path):
        from resume_agent.cli import cmd_writer

        args = _make_args(
            str(tmp_path),
            target="profile/targets/example_target.md",
            run_codex=True,
            tool="gemini",
            patina=False,
            patina_mode="audit",
            patina_profile="resume",
            patina_max=True,
            patina_max_models="claude,codex",
            patina_max_dispatch="direct",
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch(
                "resume_agent.cli.run_writer_with_codex"
            ) as mock_writer_with_codex:
                ws = _mock_workspace(tmp_path)
                MockWS.return_value = ws
                mock_writer_with_codex.return_value = {
                    "prompt_path": "/tmp/prompt.md",
                    "exit_code": 0,
                    "raw_output_path": "/tmp/raw.md",
                    "artifact_path": "/tmp/artifact.md",
                    "validation": {"passed": True, "missing": []},
                    "patina_result": None,
                    "patina_max_result": None,
                }
                cmd_writer(args)
                mock_writer_with_codex.assert_called_once_with(
                    ws,
                    target_path=tmp_path / "profile/targets/example_target.md",
                    tool="gemini",
                    patina=False,
                    patina_mode="audit",
                    patina_profile="resume",
                    patina_max=True,
                    patina_max_models="claude,codex",
                    patina_max_dispatch="direct",
                )

    def test_with_codex_prints_selected_tool_and_fallback(self, tmp_path: Path, capsys):
        from resume_agent.cli import cmd_writer
        from resume_agent.models import ArtifactType, GeneratedArtifact, ValidationResult

        args = _make_args(
            str(tmp_path),
            target="profile/targets/example_target.md",
            run_codex=True,
            tool="codex",
            patina=False,
            patina_mode="audit",
            patina_profile="resume",
            patina_max=False,
            patina_max_models=None,
            patina_max_dispatch=None,
        )
        draft_path = tmp_path / "artifacts" / "writer_draft.md"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text("draft", encoding="utf-8")
        raw_path = tmp_path / "runs" / "raw_writer.md"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("raw", encoding="utf-8")
        artifacts = [
            GeneratedArtifact(
                id="writer-1",
                artifact_type=ArtifactType.WRITER,
                accepted=False,
                input_snapshot={
                    "selected_tool": "opencode",
                    "attempted_tools": ["codex", "opencode"],
                    "fallback_reason": "usage_limit",
                    "fact_warnings": [],
                },
                output_path="artifacts/writer.md",
                raw_output_path="runs/raw_writer.md",
                validation=ValidationResult(passed=False, missing=[]),
            )
        ]

        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch(
                "resume_agent.cli.run_writer_with_codex"
            ) as mock_writer_with_codex:
                with patch("resume_agent.state.load_artifacts", return_value=artifacts):
                    ws = _mock_workspace(tmp_path)
                    MockWS.return_value = ws
                    mock_writer_with_codex.return_value = {
                        "prompt_path": "/tmp/prompt.md",
                        "exit_code": 0,
                        "raw_output_path": str(raw_path),
                        "artifact_path": str(tmp_path / "artifacts" / "writer.md"),
                        "draft_path": str(draft_path),
                        "error_output_path": str(tmp_path / "artifacts" / "writer_error.md"),
                        "validation": {"passed": True, "missing": []},
                        "approved": False,
                        "selected_tool": "opencode",
                        "attempted_tools": ["codex", "opencode"],
                        "fallback_reason": "usage_limit",
                        "patina_result": None,
                        "patina_max_result": None,
                    }
                    cmd_writer(args)

        captured = capsys.readouterr()
        assert "최종 모델: opencode" in captured.out
        assert "시도한 모델: codex, opencode" in captured.out
        assert "폴백 발생: 예" in captured.out


# ──────────────────────────────────────────────────
# cmd_interview 테스트
# ──────────────────────────────────────────────────


class TestCmdInterview:
    def test_without_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_interview

        args = _make_args(str(tmp_path), run_codex=False)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_interview") as mock_interview:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_interview.return_value = {"prompt_path": "/tmp/prompt.md"}
                cmd_interview(args)

    def test_with_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_interview

        args = _make_args(str(tmp_path), run_codex=True, tool="codex")
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_interview_with_codex") as mock_interview:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_interview.return_value = {
                    "prompt_path": "/tmp/prompt.md",
                    "exit_code": 0,
                    "raw_output_path": "/tmp/raw.md",
                    "artifact_path": "/tmp/artifact.md",
                    "validation": {"passed": True, "missing": []},
                }
                cmd_interview(args)


# ──────────────────────────────────────────────────
# cmd_deep_interview 테스트
# ──────────────────────────────────────────────────


class TestCmdDeepInterview:
    def test_basic(self, tmp_path: Path):
        from resume_agent.cli import cmd_deep_interview

        args = _make_args(str(tmp_path))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_deep_interview") as mock_deep:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_deep.return_value = {"path": "/tmp/deep.md", "count": 3}
                cmd_deep_interview(args)


# ──────────────────────────────────────────────────
# cmd_self_intro 테스트
# ──────────────────────────────────────────────────


class TestCmdSelfIntro:
    def test_basic(self, tmp_path: Path):
        from resume_agent.cli import cmd_self_intro

        args = _make_args(str(tmp_path))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_self_intro") as mock_intro:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_intro.return_value = {
                    "path": "/tmp/intro.md",
                    "analysis_path": "/tmp/analysis.json",
                }
                cmd_self_intro(args)


# ──────────────────────────────────────────────────
# cmd_export 테스트
# ──────────────────────────────────────────────────


class TestCmdExport:
    def test_basic(self, tmp_path: Path):
        from resume_agent.cli import cmd_export

        args = _make_args(str(tmp_path))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_export") as mock_export:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_export.return_value = {
                    "markdown_path": "/tmp/export.md",
                    "json_path": "/tmp/export.json",
                    "docx_path": None,
                    "accepted_count": 3,
                }
                cmd_export(args)

    def test_with_docx(self, tmp_path: Path):
        from resume_agent.cli import cmd_export

        args = _make_args(str(tmp_path))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_export") as mock_export:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_export.return_value = {
                    "markdown_path": "/tmp/export.md",
                    "json_path": "/tmp/export.json",
                    "docx_path": "/tmp/export.docx",
                    "accepted_count": 3,
                }
                cmd_export(args)


# ──────────────────────────────────────────────────
# cmd_review 테스트
# ──────────────────────────────────────────────────


class TestCmdReview:
    def test_without_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_review

        args = _make_args(
            str(tmp_path),
            target="profile/target.md",
            draft="outputs/draft.md",
            run_codex=False,
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_review_prompt") as mock_build:
                with patch("resume_agent.cli.next_step") as mock_next:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_next.return_value = "다음 단계"
                    cmd_review(args)

    def test_with_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_review

        args = _make_args(
            str(tmp_path),
            target="profile/target.md",
            draft="outputs/draft.md",
            run_codex=True,
            tool="codex",
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_review_prompt") as mock_build:
                with patch("resume_agent.cli.run_codex") as mock_codex:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_codex.return_value = 0
                    cmd_review(args)


# ──────────────────────────────────────────────────
# cmd_company_research 테스트
# ──────────────────────────────────────────────────


class TestCmdCompanyResearch:
    def test_without_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_company_research

        args = _make_args(str(tmp_path), run_codex=False, auto_web=False)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_company_research_prompt") as mock_build:
                with patch("resume_agent.cli.next_step") as mock_next:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_next.return_value = "다음 단계"
                    cmd_company_research(args)

    def test_with_codex(self, tmp_path: Path):
        from resume_agent.cli import cmd_company_research

        args = _make_args(str(tmp_path), run_codex=True, auto_web=False, tool="codex")
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_company_research_prompt") as mock_build:
                with patch(
                    "resume_agent.cli.run_company_research_with_codex"
                ) as mock_research:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_build.return_value = "/tmp/prompt.md"
                    mock_research.return_value = {
                        "exit_code": 0,
                        "artifact_path": "/tmp/research.md",
                        "source_trace_path": "/tmp/trace.json",
                    }
                    cmd_company_research(args)

    def test_with_auto_web(self, tmp_path: Path):
        from resume_agent.cli import cmd_company_research

        args = _make_args(
            str(tmp_path),
            run_codex=False,
            auto_web=True,
            max_results_per_query=3,
            max_urls=8,
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.build_company_research_prompt") as mock_build:
                with patch("resume_agent.cli.crawl_web_sources_auto") as mock_auto:
                    with patch("resume_agent.cli.next_step") as mock_next:
                        MockWS.return_value = _mock_workspace(tmp_path)
                        mock_build.return_value = "/tmp/prompt.md"
                        mock_auto.return_value = {
                            "discovered_url_count": 10,
                            "ingested_url_count": 8,
                        }
                        mock_next.return_value = "다음 단계"
                        cmd_company_research(args)


class TestCmdRefreshLive:
    def test_basic(self, tmp_path: Path):
        from resume_agent.cli import cmd_refresh_live

        args = _make_args(str(tmp_path), url=["https://example.com/jobs"])
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.refresh_live_web_sources") as mock_refresh:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_refresh.return_value = {
                    "new_url_count": 1,
                    "changed_url_count": 0,
                    "unchanged_url_count": 0,
                    "stored_count": 1,
                    "live_updates_path": "/tmp/live_source_updates.json",
                }
                cmd_refresh_live(args)
                mock_refresh.assert_called_once()


# ──────────────────────────────────────────────────
# cmd_mock_interview 테스트
# ──────────────────────────────────────────────────


class TestCmdMockInterview:
    def test_basic(self, tmp_path: Path):
        from resume_agent.cli import cmd_mock_interview

        args = _make_args(str(tmp_path), mode="normal")
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.interactive.run_mock_interview") as mock_interview:
                MockWS.return_value = _mock_workspace(tmp_path)
                cmd_mock_interview(args)
                mock_interview.assert_called_once()


# ──────────────────────────────────────────────────
# cmd_benchmark_blind 테스트
# ──────────────────────────────────────────────────


class TestCmdBenchmarkBlind:
    def test_basic(self, tmp_path: Path):
        from resume_agent.cli import cmd_benchmark_blind

        args = _make_args(str(tmp_path))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.load_project") as mock_load:
                with patch(
                    "resume_agent.cli.build_blind_benchmark_frame"
                ) as mock_build:
                    MockWS.return_value = _mock_workspace(tmp_path)
                    mock_load.return_value = MagicMock(
                        company_name="테스트", job_title="개발자", questions=[]
                    )
                    mock_build.return_value = {"candidate_count": 3, "questions": []}
                    cmd_benchmark_blind(args)


# ──────────────────────────────────────────────────
# cmd_feedback 테스트
# ──────────────────────────────────────────────────


class TestCmdFeedback:
    def test_accepted(self, tmp_path: Path):
        from resume_agent.cli import cmd_feedback

        args = _make_args(
            str(tmp_path),
            artifact="writer",
            rejected=False,
            rating=5,
            comment="좋습니다",
            final_outcome=None,
            rejection_reason=None,
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch(
                "resume_agent.feedback_learner.create_feedback_learner"
            ) as mock_learner:
                with patch("resume_agent.state.load_project") as mock_load:
                    with patch("resume_agent.utils.read_json_if_exists") as mock_json:
                        with patch(
                            "resume_agent.pipeline._build_feedback_pattern_id"
                        ) as mock_pattern:
                            with patch(
                                "resume_agent.pipeline._build_feedback_selection_payload"
                            ) as mock_payload:
                                MockWS.return_value = _mock_workspace(tmp_path)
                                mock_load.return_value = MagicMock(
                                    company_name="테스트",
                                    job_title="개발자",
                                    company_type="대기업",
                                    questions=[
                                        MagicMock(
                                            detected_type=MagicMock(value="TYPE_B")
                                        )
                                    ],
                                )
                                mock_json.return_value = []
                                mock_pattern.return_value = "writer-pattern"
                                mock_payload.return_value = {
                                    "selected_experience_ids": [],
                                    "question_experience_map": {},
                                }
                                learner = MagicMock()
                                learner.get_insights.return_value = {
                                    "total_feedback": 1,
                                    "overall_success_rate": 1.0,
                                    "average_rating": 5.0,
                                }
                                mock_learner.return_value = learner
                                with patch("builtins.print") as mock_print:
                                    cmd_feedback(args)
                                printed = " ".join(
                                    " ".join(map(str, call.args))
                                    for call in mock_print.call_args_list
                                )
                                assert "다음 단계 결과 기록 예시" in printed

    def test_rejected(self, tmp_path: Path):
        from resume_agent.cli import cmd_feedback

        args = _make_args(
            str(tmp_path),
            artifact="writer",
            rejected=True,
            rating=None,
            comment=None,
            final_outcome=None,
            rejection_reason="품질 부족",
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch(
                "resume_agent.feedback_learner.create_feedback_learner"
            ) as mock_learner:
                with patch("resume_agent.state.load_project") as mock_load:
                    with patch("resume_agent.utils.read_json_if_exists") as mock_json:
                        with patch(
                            "resume_agent.pipeline._build_feedback_pattern_id"
                        ) as mock_pattern:
                            with patch(
                                "resume_agent.pipeline._build_feedback_selection_payload"
                            ) as mock_payload:
                                MockWS.return_value = _mock_workspace(tmp_path)
                                mock_load.return_value = MagicMock(
                                    company_name="테스트",
                                    job_title="개발자",
                                    company_type="대기업",
                                    questions=[],
                                )
                                mock_json.return_value = []
                                mock_pattern.return_value = "writer-pattern"
                                mock_payload.return_value = {
                                    "selected_experience_ids": [],
                                    "question_experience_map": {},
                                }
                                learner = MagicMock()
                                learner.get_insights.return_value = {
                                    "total_feedback": 0,
                                    "overall_success_rate": 0.0,
                                    "average_rating": 0.0,
                                }
                                mock_learner.return_value = learner
                                cmd_feedback(args)


# ──────────────────────────────────────────────────
# next_step 유틸리티 테스트
# ──────────────────────────────────────────────────


class TestNextStep:
    def test_returns_string(self):
        from resume_agent.cli import next_step

        result = next_step("테스트 메시지")
        assert "Next step" in result
        assert "테스트 메시지" in result
