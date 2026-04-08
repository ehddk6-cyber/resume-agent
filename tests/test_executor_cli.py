from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from resume_agent import cli
from resume_agent.executor import run_codex


def test_run_codex_records_timeout_retry_metadata(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("test prompt", encoding="utf-8")
    output = tmp_path / "output.md"

    timeout_error = subprocess.TimeoutExpired(cmd=["codex"], timeout=30)
    with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
        with patch("resume_agent.executor.subprocess.run", side_effect=timeout_error):
            with patch("resume_agent.executor.time.sleep"):
                result = run_codex(prompt, tmp_path, output)

    assert result == 1
    metadata_path = output.with_suffix(".meta.json")
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["status"] == "failed"
    assert metadata["attempt_count"] == 6
    assert metadata["attempts"][0]["failure_kind"] == "timeout"


def test_cli_main_returns_130_on_keyboard_interrupt(capsys) -> None:
    parser = MagicMock()
    parser.parse_args.return_value = SimpleNamespace(
        func=lambda _args: (_ for _ in ()).throw(KeyboardInterrupt()),
        debug=False,
    )

    with patch("resume_agent.cli.build_parser", return_value=parser):
        exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 130
    assert "프로그램을 종료합니다." in captured.out


def test_cli_main_returns_1_and_prints_error(capsys) -> None:
    def _raise_runtime(_args):
        raise RuntimeError("boom")

    parser = MagicMock()
    parser.parse_args.return_value = SimpleNamespace(func=_raise_runtime, debug=False)

    with patch("resume_agent.cli.build_parser", return_value=parser):
        exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[오류 발생] boom" in captured.out


def test_cli_main_debug_prints_traceback(capsys) -> None:
    def _raise_runtime(_args):
        raise RuntimeError("boom")

    parser = MagicMock(spec=argparse.ArgumentParser)
    parser.parse_args.return_value = SimpleNamespace(func=_raise_runtime, debug=True)

    with patch("resume_agent.cli.build_parser", return_value=parser):
        exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "RuntimeError: boom" in captured.err


def test_writer_accepts_kilo_tool_option() -> None:
    parser = cli.build_parser()

    args = parser.parse_args(["writer", "my_run", "--tool", "kilo"])

    assert args.command == "writer"
    assert args.tool == "kilo"
