"""
외부 CLI 도구 실행 엔진 - Codex, Claude 등 외부 도구 호출 담당
"""

from __future__ import annotations

import json
import fcntl
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .logger import get_logger
from .config import get_config_value

logger = get_logger(__name__)
FALLBACK_TOOL_CHAIN = ["codex", "opencode", "claude", "gemini"]


@contextmanager
def _codex_run_lock() -> Any:
    """
    Codex CLI가 전역 상태/스냅샷을 사용하므로, 동시에 여러 프로세스가
    실행되면 충돌할 수 있습니다. 사용자 홈 아래의 공용 락으로 직렬화합니다.
    """
    lock_dir = Path.home() / ".codex"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "resume-agent-run.lock"
    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _metadata_path(output_path: Path) -> Path:
    if output_path.suffix:
        return output_path.with_suffix(".meta.json")
    return Path(str(output_path) + ".meta.json")


def _write_run_metadata(
    output_path: Path,
    *,
    status: str,
    attempt_count: int,
    timeout_seconds: int,
    attempts: list[dict[str, Any]],
    selected_tool: str | None = None,
    attempted_tools: list[str] | None = None,
    fallback_reason: str | None = None,
) -> None:
    payload = {
        "status": status,
        "attempt_count": attempt_count,
        "timeout_seconds": timeout_seconds,
        "attempts": attempts,
        "output_path": str(output_path),
        "selected_tool": selected_tool,
        "attempted_tools": attempted_tools or [],
        "fallback_reason": fallback_reason,
    }
    _metadata_path(output_path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _classify_failure_message(message: str) -> str:
    lowered = message.lower()
    if "usage limit" in lowered or "hit your usage limit" in lowered:
        return "usage_limit"
    if (
        "yaml" in lowered
        or "frontmatter" in lowered
        or "skill" in lowered
        and (
            "parse" in lowered
            or "loader" in lowered
            or "failed to stat" in lowered
            or "symlink" in lowered
        )
    ):
        return "skill_loader_error"
    if "featured plugin" in lowered and "sync" in lowered:
        return "plugin_sync_error"
    if "failed to stat" in lowered or "broken symlink" in lowered:
        return "skill_loader_error"
    return "nonzero_exit"


def _is_fallback_eligible(failure_kind: str | None) -> bool:
    return failure_kind in {
        "usage_limit",
        "skill_loader_error",
        "plugin_sync_error",
        "timeout",
        "nonzero_exit",
        "exception",
    }


def build_exec_prompt(prompt: str) -> str:
    """LLM 호출용 프롬프트 래퍼 - 파일 검사/셸 명령 등을 금지하는 지시 포함"""
    return (
        "This is a pure text-generation task.\n"
        "Do not inspect files, do not run shell commands, do not plan aloud, and do not acknowledge the request.\n"
        "Return only the final answer that satisfies the requested output contract.\n\n"
        f"{prompt}"
    )


def extract_last_codex_message(stdout: str) -> str:
    """Codex CLI 출력에서 마지막 메시지 추출"""
    marker = "\ncodex\n"
    if marker in stdout:
        return stdout.rsplit(marker, 1)[-1].strip()
    return stdout.strip()


def _execute_cli_tool_once(prompt_path: Path, tool: str) -> dict[str, Any]:
    """codex 외 CLI 도구를 1회 실행하고, 텍스트/실패 원인을 반환합니다."""
    from .cli_tool_manager import CLIToolManager, get_available_tools, OpencodeTool

    prompt_text = prompt_path.read_text(encoding="utf-8")
    wrapped_prompt = build_exec_prompt(prompt_text)

    if tool == "opencode":
        try:
            opencode_tool = OpencodeTool()
            result = opencode_tool.execute(wrapped_prompt, timeout=300)
            return {"success": True, "text": result}
        except Exception as e:
            error_text = str(e)
            return {
                "success": False,
                "error": error_text,
                "failure_kind": _classify_failure_message(error_text)
                if error_text
                else "exception",
            }

    available = get_available_tools()
    if tool not in available:
        error_text = (
            f"CLI 도구 '{tool}'를 찾을 수 없습니다. 사용 가능: {', '.join(available) if available else '없음'}"
        )
        return {
            "success": False,
            "error": error_text,
            "failure_kind": "tool_not_found",
        }

    try:
        manager = CLIToolManager(tool)
        result = manager.execute(wrapped_prompt, timeout=300)
        return {"success": True, "text": result}
    except Exception as e:
        error_text = str(e)
        return {
            "success": False,
            "error": error_text,
            "failure_kind": _classify_failure_message(error_text)
            if error_text
            else "exception",
        }


def _run_with_cli_tool(prompt_path: Path, output_path: Path, tool: str) -> int:
    """CLIToolManager를 사용하여 codex 외 CLI 도구로 실행합니다."""
    execution = _execute_cli_tool_once(prompt_path, tool)
    if execution["success"]:
        output_path.write_text(execution["text"], encoding="utf-8")
        logger.info(f"{tool} CLI 실행 성공: {output_path.name}")
        _write_run_metadata(
            output_path,
            status="success",
            attempt_count=1,
            timeout_seconds=300,
            attempts=[{"tool": tool, "attempt": 1, "failure_kind": None}],
            selected_tool=tool,
            attempted_tools=[tool],
            fallback_reason=None,
        )
        return 0

    error_text = execution.get("error", "")
    logger.error(f"{tool} CLI 실행 실패: {error_text}")
    fallback = (
        f"# {tool} CLI 실행 실패\n\n"
        f"오류: {error_text}\n\n"
        f"### 해결 방법\n"
        f"1. `{tool}` CLI가 설치되어 있고 실행 가능한지 확인하세요.\n"
        f"2. 기본 codex를 사용해 보세요: `resume-agent writer <workspace> --run-codex`\n"
    )
    output_path.write_text(fallback, encoding="utf-8")
    _write_run_metadata(
        output_path,
        status="failed",
        attempt_count=1,
        timeout_seconds=300,
        attempts=[
            {
                "tool": tool,
                "attempt": 1,
                "failure_kind": execution.get("failure_kind", "exception"),
                "error": error_text[:400],
            }
        ],
        selected_tool=None,
        attempted_tools=[tool],
        fallback_reason=execution.get("failure_kind", "exception"),
    )
    return 1


def run_codex(
    prompt_path: Path, cwd: Path, output_path: Path, tool: str = "codex"
) -> int:
    """
    외부 CLI 도구로 프롬프트를 실행합니다.

    Args:
        prompt_path: 프롬프트 파일 경로
        cwd: 작업 디렉토리
        output_path: 출력 파일 경로
        tool: 사용할 CLI 도구 (codex, claude, gemini, kilo, cline)

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    from .estimator import estimate_cost_and_log

    prompt_path = prompt_path.resolve()
    cwd = cwd.resolve()
    output_path = output_path.resolve()
    prompt_text = prompt_path.read_text(encoding="utf-8")
    estimate_cost_and_log(prompt_text, context_name=output_path.name)

    if tool != "codex":
        return _run_with_cli_tool(prompt_path, output_path, tool)

    codex_bin = shutil.which("codex")
    if codex_bin is None:
        logger.error("`codex` is not available on PATH.")
        raise RuntimeError("`codex` is not available on PATH.")

    prompt = build_exec_prompt(prompt_text)

    max_retries = int(get_config_value("codex.max_retries", 3))
    retry_delay = int(get_config_value("codex.retry_delay_base", 2))
    timeout_seconds = int(get_config_value("codex.timeout_seconds", 300))
    attempts_meta: list[dict[str, Any]] = []
    attempted_tools: list[str] = []
    fallback_reason: str | None = None

    def _record_selected_output(selected_tool: str, text: str) -> int:
        output_path.write_text(text, encoding="utf-8")
        _write_run_metadata(
            output_path,
            status="success",
            attempt_count=len(attempts_meta),
            timeout_seconds=timeout_seconds,
            attempts=attempts_meta,
            selected_tool=selected_tool,
            attempted_tools=attempted_tools,
            fallback_reason=fallback_reason,
        )
        return 0

    with _codex_run_lock():
        attempted_tools.append("codex")
        temp_output_path = output_path.parent / f".{output_path.stem}.codex.tmp.md"
        last_failure_kind: str | None = None
        for attempt in range(max_retries):
            logger.info(
                f"Running codex for {output_path.name} (Attempt {attempt + 1}/{max_retries})"
            )
            started = time.time()
            attempt_meta: dict[str, Any] = {
                "tool": "codex",
                "attempt": attempt + 1,
                "timeout_seconds": timeout_seconds,
            }
            try:
                if temp_output_path.exists():
                    temp_output_path.unlink()
                result = subprocess.run(
                    [
                        codex_bin,
                        "exec",
                        "--skip-git-repo-check",
                        "-C",
                        str(cwd),
                        "--color",
                        "never",
                        "-o",
                        str(temp_output_path),
                        "-",
                    ],
                    cwd=str(cwd),
                    input=prompt,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout_seconds,
                )
                attempt_meta["returncode"] = result.returncode
                attempt_meta["duration_ms"] = int((time.time() - started) * 1000)

                if result.returncode == 0:
                    logger.info(f"Codex execution successful for {output_path.name}")
                    text = ""
                    if temp_output_path.exists():
                        text = temp_output_path.read_text(
                            encoding="utf-8", errors="ignore"
                        ).strip()
                    if not text:
                        text = extract_last_codex_message(result.stdout or "") or (
                            (result.stdout or "")
                            + ("\n" + result.stderr if result.stderr else "")
                        )
                    attempt_meta["failure_kind"] = None
                    attempts_meta.append(attempt_meta)
                    return _record_selected_output("codex", text)

                stderr_excerpt = (result.stderr or "").strip()[:400]
                failure_kind = _classify_failure_message(stderr_excerpt)
                logger.warning(
                    f"Codex execution failed with code {result.returncode}. Stderr: {stderr_excerpt[:200]}"
                )
                attempt_meta["failure_kind"] = failure_kind
                attempt_meta["stderr_excerpt"] = stderr_excerpt
                attempts_meta.append(attempt_meta)
                last_failure_kind = failure_kind
            except subprocess.TimeoutExpired as e:
                logger.error(f"Codex execution timed out: {e}")
                attempt_meta["duration_ms"] = int((time.time() - started) * 1000)
                attempt_meta["failure_kind"] = "timeout"
                attempts_meta.append(attempt_meta)
                last_failure_kind = "timeout"
            except Exception as e:
                logger.error(f"Error during codex execution: {e}")
                attempt_meta["duration_ms"] = int((time.time() - started) * 1000)
                attempt_meta["failure_kind"] = "exception"
                attempt_meta["error"] = str(e)
                attempts_meta.append(attempt_meta)
                last_failure_kind = "exception"

            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2

    if last_failure_kind and _is_fallback_eligible(last_failure_kind):
        fallback_reason = last_failure_kind
    else:
        logger.error(f"Failed to execute codex after {max_retries} attempts.")
        fallback_reason = last_failure_kind
        fallback_content = (
            f"# Codex 실행 실패 (폴백 출력)\n\n"
            f"## 안내\n"
            f"Codex CLI 실행이 {max_retries}회 실패했습니다.\n\n"
            f"### 해결 방법\n"
            f"1. `codex` CLI가 설치되어 있고 PATH에 등록되어 있는지 확인하세요.\n"
            f"   - 설치: `npm install -g @openai/codex`\n"
            f"2. 네트워크 연결 상태를 확인하세요.\n"
            f"3. 프롬프트 파일(`{prompt_path}`)의 크기가 토큰 한도를 초과하지 않는지 확인하세요.\n"
            f"4. 수동으로 Codex를 실행해 보세요:\n"
            f"   ```\n"
            f"   codex exec --skip-git-repo-check -C {cwd} -o {output_path} - < {prompt_path}\n"
            f"   ```\n"
            f"5. 다른 CLI 도구를 사용해 보세요: `--tool opencode`, `--tool claude`, `--tool gemini`\n"
        )
        output_path.write_text(fallback_content, encoding="utf-8")
        _write_run_metadata(
            output_path,
            status="failed",
            attempt_count=len(attempts_meta),
            timeout_seconds=timeout_seconds,
            attempts=attempts_meta,
            selected_tool=None,
            attempted_tools=attempted_tools,
            fallback_reason=fallback_reason,
        )
        logger.warning(f"Fallback output written to {output_path}")
        return 1

    for fallback_tool in FALLBACK_TOOL_CHAIN[1:]:
        attempted_tools.append(fallback_tool)
        execution = _execute_cli_tool_once(prompt_path, fallback_tool)
        attempt_meta = {
            "tool": fallback_tool,
            "attempt": 1,
            "timeout_seconds": 300,
        }
        if execution["success"]:
            attempt_meta["failure_kind"] = None
            attempts_meta.append(attempt_meta)
            logger.info(f"{fallback_tool} fallback execution successful")
            return _record_selected_output(fallback_tool, execution["text"])

        attempt_meta["failure_kind"] = execution.get("failure_kind", "exception")
        attempt_meta["error"] = str(execution.get("error", ""))[:400]
        attempts_meta.append(attempt_meta)
        logger.warning(
            f"{fallback_tool} fallback execution failed: {attempt_meta['failure_kind']}"
        )

    fallback_content = (
        f"# Codex 실행 실패 (폴백 출력)\n\n"
        f"## 안내\n"
        f"Codex 및 폴백 도구 실행이 모두 실패했습니다.\n\n"
        f"### 해결 방법\n"
        f"1. `codex` CLI가 설치되어 있고 PATH에 등록되어 있는지 확인하세요.\n"
        f"   - 설치: `npm install -g @openai/codex`\n"
        f"2. `opencode`, `claude`, `gemini` CLI 환경을 확인하세요.\n"
        f"3. 네트워크 연결 상태를 확인하세요.\n"
        f"4. 프롬프트 파일(`{prompt_path}`)의 크기가 토큰 한도를 초과하지 않는지 확인하세요.\n"
        f"5. 수동으로 Codex를 실행해 보세요:\n"
        f"   ```\n"
        f"   codex exec --skip-git-repo-check -C {cwd} -o {output_path} - < {prompt_path}\n"
        f"   ```\n"
        f"6. 다른 CLI 도구를 직접 지정해 보세요: `--tool opencode`, `--tool claude`, `--tool gemini`\n"
    )
    output_path.write_text(fallback_content, encoding="utf-8")
    _write_run_metadata(
        output_path,
        status="failed",
        attempt_count=len(attempts_meta),
        timeout_seconds=timeout_seconds,
        attempts=attempts_meta,
        selected_tool=None,
        attempted_tools=attempted_tools,
        fallback_reason=fallback_reason,
    )
    logger.warning(f"Fallback output written to {output_path}")
    return 1
