"""cli.py Phase 1 테스트 — cmd_writer, cmd_status, cmd_resume mocking"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
# cmd_writer 테스트 (간소화)
# ──────────────────────────────────────────────────


class TestCmdWriterPhase1:
    def test_writer_prompt_only(self, tmp_path: Path):
        """프롬프트만 생성 (run_codex=False)"""
        from resume_agent.cli import cmd_writer

        args = _make_args(
            str(tmp_path),
            target="profile/targets/example_target.md",
            run_codex=False,
            tool="codex",
            patina=False,
            patina_mode="audit",
            patina_profile="resume",
        )

        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.run_writer") as mock_writer:
                MockWS.return_value = _mock_workspace(tmp_path)
                mock_writer.return_value = {"prompt_path": "/tmp/prompt.md"}
                cmd_writer(args)
                mock_writer.assert_called_once()


class TestCmdStatusPhase1:
    def test_status_basic(self, tmp_path: Path):
        """기본 상태 확인"""
        from resume_agent.cli import cmd_status

        args = _make_args(str(tmp_path))

        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.checkpoint.CheckpointManager") as MockCP:
                with patch("resume_agent.pipeline.load_artifacts") as mock_artifacts:
                    with patch("resume_agent.utils.read_json_if_exists") as mock_json:
                        with patch("resume_agent.state.load_project") as mock_project:
                            with patch("rich.console.Console.print") as mock_print:
                                MockWS.return_value = _mock_workspace(tmp_path)

                                cp = MagicMock()
                                cp.list_checkpoints.return_value = ["coach", "writer"]
                                cp.get_checkpoint_info.return_value = {
                                    "timestamp": "2026-04-02T12:00:00",
                                    "status": "success",
                                }
                                MockCP.return_value = cp

                                mock_artifacts.return_value = []
                                mock_json.return_value = None
                                mock_project.return_value = MagicMock(
                                    company_name="테스트회사",
                                    job_title="개발자",
                                )

                                cmd_status(args)
                                assert mock_print.called


class TestCmdResumePhase1:
    def test_resume_no_checkpoint(self, tmp_path: Path):
        """체크포인트 없음"""
        from resume_agent.cli import cmd_resume

        args = _make_args(str(tmp_path))

        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.checkpoint.CheckpointManager") as MockCP:
                MockWS.return_value = _mock_workspace(tmp_path)

                cp = MagicMock()
                cp.get_resume_point.return_value = None
                cp.list_checkpoints.return_value = []
                MockCP.return_value = cp

                cmd_resume(args)


# ──────────────────────────────────────────────────
# build_parser 테스트
# ──────────────────────────────────────────────────


class TestBuildParserPhase1:
    def test_parser_creation(self):
        """파서 생성 확인"""
        from resume_agent.cli import build_parser

        parser = build_parser()
        assert parser is not None

    def test_writer_subparser_options(self):
        """writer 서브커맨드 옵션 확인"""
        from resume_agent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["writer", "/tmp/ws", "--run-codex", "--tool", "codex", "--patina"]
        )

        assert args.workspace == "/tmp/ws"
        assert args.run_codex is True
        assert args.tool == "codex"
        assert args.patina is True

    def test_feedback_subparser_options(self):
        """feedback 서브커맨드 옵션 확인"""
        from resume_agent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "feedback",
                "/tmp/ws",
                "--artifact",
                "writer",
                "--rating",
                "5",
                "--comment",
                "좋습니다",
            ]
        )

        assert args.workspace == "/tmp/ws"
        assert args.artifact == "writer"
        assert args.rating == 5
        assert args.comment == "좋습니다"

    def test_company_research_subparser_options(self):
        """company-research 서브커맨드 옵션 확인"""
        from resume_agent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "company-research",
                "/tmp/ws",
                "--run-codex",
                "--auto-web",
                "--max-results-per-query",
                "5",
                "--max-urls",
                "10",
            ]
        )

        assert args.workspace == "/tmp/ws"
        assert args.run_codex is True
        assert args.auto_web is True
        assert args.max_results_per_query == 5
        assert args.max_urls == 10

    def test_sync_subparser_options(self):
        """sync 서브커맨드 옵션 확인"""
        from resume_agent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["sync", "/tmp/ws", "--path", "/tmp/source"])

        assert args.workspace == "/tmp/ws"
        assert args.path == "/tmp/source"

    def test_mock_interview_subparser_options(self):
        """mock-interview 서브커맨드 옵션 확인"""
        from resume_agent.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["mock-interview", "/tmp/ws", "--mode", "hard"])

        assert args.workspace == "/tmp/ws"
        assert args.mode == "hard"
