"""executor.py 커버리지 — 누락 라인 23, 67-98, 122, 125-126, 169-191, 205-210"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestExecutor:
    def test_build_exec_prompt_basic(self):
        """기본 프롬프트 빌드"""
        from resume_agent.executor import build_exec_prompt

        result = build_exec_prompt("테스트 프롬프트")
        assert "테스트 프롬프트" in result

    def test_extract_last_codex_message(self):
        """마지막 codex 메시지 추출"""
        from resume_agent.executor import extract_last_codex_message

        text = "[assistant] 첫 번째\n[assistant] 마지막"
        result = extract_last_codex_message(text)
        assert "마지막" in result

    def test_extract_last_codex_message_empty(self):
        """빈 텍스트"""
        from resume_agent.executor import extract_last_codex_message

        result = extract_last_codex_message("")
        assert result == ""

    def test_extract_last_codex_message_no_assistant(self):
        """assistant 태그 없음"""
        from resume_agent.executor import extract_last_codex_message

        result = extract_last_codex_message("일반 텍스트")
        assert result == "일반 텍스트"

    def test_run_codex_with_other_tool(self, tmp_path: Path):
        """codex 외 도구 사용 — 라인 121-122"""
        from resume_agent.executor import run_codex

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch(
            "resume_agent.executor._run_with_cli_tool", return_value=0
        ) as mock_run:
            result = run_codex(prompt_path, tmp_path, output_path, tool="claude")
            assert result == 0
            mock_run.assert_called_once()

    def test_run_codex_not_found(self, tmp_path: Path):
        """codex 없음 — 라인 124-126"""
        from resume_agent.executor import run_codex

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="codex"):
                run_codex(prompt_path, tmp_path, output_path)

    def test_run_codex_success(self, tmp_path: Path):
        """codex 성공 — 라인 168-191"""
        from resume_agent.executor import run_codex

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch("resume_agent.executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="응답입니다.",
                    stderr="",
                )
                with patch("resume_agent.executor.get_config_value") as mock_config:
                    mock_config.side_effect = lambda key, default: {
                        "codex.max_retries": 1,
                        "codex.retry_delay_base": 2,
                        "codex.timeout_seconds": 300,
                    }.get(key, default)
                    result = run_codex(prompt_path, tmp_path, output_path)
                    assert result == 0

    def test_run_codex_failure_retry(self, tmp_path: Path):
        """codex 실패 후 재시도 — 라인 192-210"""
        from resume_agent.executor import run_codex

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch("resume_agent.executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="에러 발생",
                )
                with patch("resume_agent.executor.get_config_value") as mock_config:
                    mock_config.side_effect = lambda key, default: {
                        "codex.max_retries": 2,
                        "codex.retry_delay_base": 0,
                        "codex.timeout_seconds": 300,
                    }.get(key, default)
                    with patch("resume_agent.executor.time.sleep"):
                        result = run_codex(prompt_path, tmp_path, output_path)
                        assert result == 1

    def test_run_codex_falls_back_to_opencode_on_usage_limit(self, tmp_path: Path):
        from resume_agent.executor import run_codex

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch("resume_agent.executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="ERROR: You've hit your usage limit",
                )
                with patch("resume_agent.executor._execute_cli_tool_once") as mock_cli:
                    mock_cli.return_value = {"success": True, "text": "opencode output"}
                    with patch("resume_agent.executor.get_config_value") as mock_config:
                        mock_config.side_effect = lambda key, default: {
                            "codex.max_retries": 1,
                            "codex.retry_delay_base": 0,
                            "codex.timeout_seconds": 300,
                        }.get(key, default)
                        result = run_codex(prompt_path, tmp_path, output_path)

        assert result == 0
        assert output_path.read_text(encoding="utf-8") == "opencode output"
        metadata = json.loads(output_path.with_suffix(".meta.json").read_text())
        assert metadata["selected_tool"] == "opencode"
        assert metadata["attempted_tools"] == ["codex", "opencode"]
        assert metadata["fallback_reason"] == "usage_limit"

    def test_run_codex_falls_through_multiple_tools(self, tmp_path: Path):
        from resume_agent.executor import run_codex

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch("resume_agent.executor.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="skill frontmatter yaml parse error",
                )
                with patch("resume_agent.executor._execute_cli_tool_once") as mock_cli:
                    mock_cli.side_effect = [
                        {
                            "success": False,
                            "error": "opencode failed",
                            "failure_kind": "nonzero_exit",
                        },
                        {"success": True, "text": "claude output"},
                    ]
                    with patch("resume_agent.executor.get_config_value") as mock_config:
                        mock_config.side_effect = lambda key, default: {
                            "codex.max_retries": 1,
                            "codex.retry_delay_base": 0,
                            "codex.timeout_seconds": 300,
                        }.get(key, default)
                        result = run_codex(prompt_path, tmp_path, output_path)

        assert result == 0
        metadata = json.loads(output_path.with_suffix(".meta.json").read_text())
        assert metadata["selected_tool"] == "claude"
        assert metadata["attempted_tools"] == ["codex", "opencode", "claude"]
        assert metadata["fallback_reason"] == "skill_loader_error"

    def test_run_codex_timeout(self, tmp_path: Path):
        """codex 타임아웃 — 라인 200-204"""
        from resume_agent.executor import run_codex
        import subprocess

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch(
                "resume_agent.executor.subprocess.run",
                side_effect=subprocess.TimeoutExpired("cmd", 300),
            ):
                with patch("resume_agent.executor.get_config_value") as mock_config:
                    mock_config.side_effect = lambda key, default: {
                        "codex.max_retries": 1,
                        "codex.retry_delay_base": 0,
                        "codex.timeout_seconds": 300,
                    }.get(key, default)
                    result = run_codex(prompt_path, tmp_path, output_path)
                    assert result == 1

    def test_run_codex_exception(self, tmp_path: Path):
        """codex 예외 — 라인 205-210"""
        from resume_agent.executor import run_codex

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch("resume_agent.executor.shutil.which", return_value="/usr/bin/codex"):
            with patch(
                "resume_agent.executor.subprocess.run",
                side_effect=OSError("테스트 오류"),
            ):
                with patch("resume_agent.executor.get_config_value") as mock_config:
                    mock_config.side_effect = lambda key, default: {
                        "codex.max_retries": 1,
                        "codex.retry_delay_base": 0,
                        "codex.timeout_seconds": 300,
                    }.get(key, default)
                    result = run_codex(prompt_path, tmp_path, output_path)
                    assert result == 1

    def test_run_with_cli_tool_success(self, tmp_path: Path):
        """CLI 도구 성공 — 라인 67-87"""
        from resume_agent.executor import _run_with_cli_tool

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch(
            "resume_agent.cli_tool_manager.get_available_tools", return_value=["claude"]
        ):
            with patch("resume_agent.cli_tool_manager.CLIToolManager") as mock_manager:
                mock_manager.return_value.execute.return_value = "응답"
                result = _run_with_cli_tool(prompt_path, output_path, "claude")
                assert result == 0

    def test_run_with_cli_tool_not_found(self, tmp_path: Path):
        """CLI 도구 없음 — 라인 70-78"""
        from resume_agent.executor import _run_with_cli_tool

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch(
            "resume_agent.cli_tool_manager.get_available_tools", return_value=["codex"]
        ):
            result = _run_with_cli_tool(prompt_path, output_path, "claude")
            assert result == 1

    def test_run_with_cli_tool_exception(self, tmp_path: Path):
        """CLI 도구 예외 — 라인 88-98"""
        from resume_agent.executor import _run_with_cli_tool

        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text("프롬프트", encoding="utf-8")
        output_path = tmp_path / "output.md"

        with patch(
            "resume_agent.cli_tool_manager.get_available_tools", return_value=["claude"]
        ):
            with patch("resume_agent.cli_tool_manager.CLIToolManager") as mock_manager:
                mock_manager.return_value.execute.side_effect = Exception("테스트 오류")
                result = _run_with_cli_tool(prompt_path, output_path, "claude")
                assert result == 1

    def test_metadata_path_with_suffix(self):
        """메타데이터 경로 — 라인 21-23"""
        from resume_agent.executor import _metadata_path

        path = Path("/tmp/output.md")
        result = _metadata_path(path)
        assert str(result).endswith(".meta.json")

    def test_metadata_path_without_suffix(self):
        """메타데이터 경로 (확장자 없음)"""
        from resume_agent.executor import _metadata_path

        path = Path("/tmp/output")
        result = _metadata_path(path)
        assert str(result).endswith(".meta.json")

    def test_write_run_metadata(self, tmp_path: Path):
        """메타데이터 작성"""
        from resume_agent.executor import _write_run_metadata, _metadata_path

        output_path = tmp_path / "output.md"
        _write_run_metadata(
            output_path,
            status="success",
            attempt_count=1,
            timeout_seconds=300,
            attempts=[],
        )
        meta_path = _metadata_path(output_path)
        assert meta_path.exists()
