"""
외부 CLI 도구 실행 엔진 - Codex, Claude 등 외부 도구 호출 담당
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .logger import get_logger
from .config import get_config_value

logger = get_logger(__name__)


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


def _run_with_cli_tool(prompt_path: Path, output_path: Path, tool: str) -> int:
    """CLIToolManager를 사용하여 codex 외 CLI 도구로 실행합니다."""
    from .cli_tool_manager import CLIToolManager, get_available_tools

    available = get_available_tools()
    if tool not in available:
        logger.error(f"CLI 도구 '{tool}'를 찾을 수 없습니다. 사용 가능: {available}")
        fallback = (
            f"# CLI 도구 '{tool}' 실행 실패\n\n"
            f"사용 가능한 도구: {', '.join(available) if available else '없음'}\n"
            f"다른 도구를 시도하거나 codex를 기본으로 사용하세요.\n"
        )
        output_path.write_text(fallback, encoding="utf-8")
        return 1

    try:
        manager = CLIToolManager(tool)
        prompt_text = prompt_path.read_text(encoding="utf-8")
        wrapped_prompt = build_exec_prompt(prompt_text)
        result = manager.execute(wrapped_prompt, timeout=300)
        output_path.write_text(result, encoding="utf-8")
        logger.info(f"{tool} CLI 실행 성공: {output_path.name}")
        return 0
    except Exception as e:
        logger.error(f"{tool} CLI 실행 실패: {e}")
        fallback = (
            f"# {tool} CLI 실행 실패\n\n"
            f"오류: {e}\n\n"
            f"### 해결 방법\n"
            f"1. `{tool}` CLI가 설치되어 있는지 확인하세요.\n"
            f"2. 기본 codex를 사용해 보세요: `resume-agent writer <workspace> --run-codex`\n"
        )
        output_path.write_text(fallback, encoding="utf-8")
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
        tool: 사용할 CLI 도구 (codex, claude, gemini, cline)

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    from .estimator import estimate_cost_and_log

    prompt_text = prompt_path.read_text(encoding="utf-8")
    estimate_cost_and_log(prompt_text, context_name=output_path.name)

    if tool != "codex":
        return _run_with_cli_tool(prompt_path, output_path, tool)

    if shutil.which("codex") is None:
        logger.error("`codex` is not available on PATH.")
        raise RuntimeError("`codex` is not available on PATH.")

    prompt = build_exec_prompt(prompt_text)

    max_retries = int(get_config_value("codex.max_retries", 3))
    retry_delay = int(get_config_value("codex.retry_delay_base", 2))

    for attempt in range(max_retries):
        logger.info(
            f"Running codex for {output_path.name} (Attempt {attempt + 1}/{max_retries})"
        )
        try:
            result = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--skip-git-repo-check",
                    "-C",
                    str(cwd),
                    "--color",
                    "never",
                    "-o",
                    str(output_path),
                    "-",
                ],
                cwd=str(cwd),
                input=prompt,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"Codex execution successful for {output_path.name}")
                if (not output_path.exists()) or not output_path.read_text(
                    encoding="utf-8", errors="ignore"
                ).strip():
                    extracted = extract_last_codex_message(result.stdout or "")
                    output_path.write_text(
                        extracted
                        or (
                            (result.stdout or "")
                            + ("\n" + result.stderr if result.stderr else "")
                        ),
                        encoding="utf-8",
                    )
                return 0
            else:
                logger.warning(
                    f"Codex execution failed with code {result.returncode}. Stderr: {result.stderr.strip()[:200]}"
                )

        except Exception as e:
            logger.error(f"Error during codex execution: {e}")

        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2

    logger.error(f"Failed to execute codex after {max_retries} attempts.")

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
        f"5. 다른 CLI 도구를 사용해 보세요: `--tool claude` 또는 `--tool gemini`\n"
    )
    output_path.write_text(fallback_content, encoding="utf-8")
    logger.warning(f"Fallback output written to {output_path}")
    return 1
