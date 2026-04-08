from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .logger import get_logger
from .patina_bridge import (
    _parse_rewrite_output,
    extract_answers,
    load_patina_config,
    load_patina_patterns,
    load_patina_profile,
    load_patina_voice,
    measure_char_delta,
    reassemble_answers,
)

logger = get_logger(__name__)

DEFAULT_MAX_MODELS = ["claude", "codex", "opencode", "gemini"]
VALID_MODELS = {"claude", "codex", "opencode", "gemini"}


def get_patina_max_skill_dir() -> Path:
    candidates = [
        Path.home() / ".codex" / "skills" / "patina" / "patina-max",
        Path.home() / ".codex" / "skills" / "patina-max",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "patina-max 스킬 디렉토리를 찾을 수 없습니다. "
        f"확인 경로: {', '.join(str(path) for path in candidates)}"
    )


def load_patina_max_skill_md() -> str:
    skill_dir = get_patina_max_skill_dir()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_md}")
    return skill_md.read_text(encoding="utf-8")


def _load_project_patina_config(workspace_root: Path) -> dict[str, Any]:
    config_path = workspace_root / ".patina.yaml"
    if not config_path.exists():
        return {}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning(f".patina.yaml 로드 실패: {exc}")
        return {}


def resolve_patina_max_models(
    workspace_root: Path, models: str | list[str] | None
) -> list[str]:
    requested: list[str]
    if isinstance(models, str):
        requested = [item.strip() for item in models.split(",") if item.strip()]
    elif isinstance(models, list):
        requested = [str(item).strip() for item in models if str(item).strip()]
    else:
        config = _load_project_patina_config(workspace_root)
        requested = [str(item).strip() for item in config.get("max-models", [])]
    if not requested:
        requested = list(DEFAULT_MAX_MODELS)

    selected: list[str] = []
    for model in requested:
        if model in VALID_MODELS and model not in selected:
            selected.append(model)
    return selected or list(DEFAULT_MAX_MODELS)


def resolve_patina_max_dispatch(workspace_root: Path, dispatch: str | None) -> str:
    requested = (dispatch or "").strip()
    if not requested:
        config = _load_project_patina_config(workspace_root)
        requested = str(config.get("dispatch", "direct")).strip()
    return requested or "direct"


def build_patina_max_prompt(
    text: str,
    profile_name: str = "resume",
    lang: str = "ko",
) -> str:
    orchestration = load_patina_max_skill_md()
    patterns = load_patina_patterns(lang)
    profile = load_patina_profile(profile_name)
    voice = load_patina_voice()
    config = load_patina_config()
    return f"""# Task: AI 글쓰기 패턴 제거 (patina-max candidate)

당신은 여러 모델 중 하나로 실행되는 humanization 작업자입니다.
아래 규칙에 따라 입력 텍스트를 자연스럽게 다듬으세요.

## patina-max 오케스트레이션 참고
{orchestration}

## 설정
```yaml
{config}
```

## 프로필
{profile}

## 패턴 팩
{patterns}

## 목소리 지침
{voice}

## 작업 지시
- 각 답변 본문만 자연스럽게 다듬으세요.
- `### Q숫자` 헤더는 유지하세요.
- 수치와 고유명사는 바꾸지 마세요.
- 과장된 AI 문체, 상투적 연결문, 균일한 문단 리듬을 줄이세요.
- 출력에는 설명 없이 최종 본문만 포함하세요.

## 입력 텍스트
{text}
"""


def _extract_opencode_text(raw_output: str) -> str:
    texts: list[str] = []
    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = str(payload.get("type") or "")
        if event_type == "message":
            message = payload.get("message") or {}
            parts = message.get("parts") or []
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = str(part.get("text") or "").strip()
                    if text:
                        texts.append(text)
        elif event_type == "text":
            text = str(payload.get("text") or "").strip()
            if text:
                texts.append(text)
    if texts:
        return "\n".join(texts).strip()
    return raw_output.strip()


def _run_model_prompt(model: str, prompt_text: str, timeout: int = 900) -> dict[str, Any]:
    if model == "codex":
        from .executor import run_codex

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as prompt_file:
            prompt_file.write(prompt_text)
            prompt_path = Path(prompt_file.name)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as output_file:
            output_path = Path(output_file.name)
        try:
            exit_code = run_codex(prompt_path, Path.cwd(), output_path, tool="codex")
            raw_output = output_path.read_text(encoding="utf-8", errors="ignore")
            return {
                "success": exit_code == 0 and raw_output.strip() != "",
                "raw_output": raw_output,
                "exit_code": exit_code,
                "error": None if exit_code == 0 else f"codex exit code {exit_code}",
            }
        finally:
            prompt_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

    if model == "claude":
        cmd = ["claude-stdin-pty"]
        use_stdin = True
    elif model == "gemini":
        cmd = ["gemini", "-p", prompt_text, "--output-format", "text"]
        use_stdin = False
    elif model == "opencode":
        cmd = ["opencode", "run", prompt_text, "--format", "json"]
        use_stdin = False
    else:
        return {
            "success": False,
            "raw_output": "",
            "exit_code": 1,
            "error": f"지원하지 않는 patina-max 모델: {model}",
        }

    try:
        result = subprocess.run(
            cmd,
            input=prompt_text if use_stdin else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        raw_output = result.stdout or ""
        if model == "opencode":
            raw_output = _extract_opencode_text(raw_output)
        error_text = (result.stderr or "").strip()
        return {
            "success": result.returncode == 0 and raw_output.strip() != "",
            "raw_output": raw_output,
            "exit_code": result.returncode,
            "error": error_text[:500] if result.returncode != 0 else None,
        }
    except Exception as exc:
        return {
            "success": False,
            "raw_output": "",
            "exit_code": 1,
            "error": str(exc),
        }


def _select_best_candidate(
    outputs_by_model: dict[str, dict[str, Any]],
    expected_question_count: int,
) -> tuple[str | None, dict[str, Any] | None]:
    best_model: str | None = None
    best_candidate: dict[str, Any] | None = None
    best_score: tuple[int, int, int, int] | None = None

    for model, candidate in outputs_by_model.items():
        parseable = bool(candidate.get("parseable"))
        preserved = int(candidate.get("processed_count", 0) == expected_question_count)
        char_limit_issues = int(candidate.get("char_limit_issue_count", 9999))
        total_abs_delta = int(candidate.get("total_abs_delta", 10**9))
        score = (
            1 if parseable else 0,
            preserved,
            -char_limit_issues,
            -total_abs_delta,
        )
        if best_score is None or score > best_score:
            best_score = score
            best_model = model
            best_candidate = candidate
    return best_model, best_candidate


def run_patina_max(
    writer_text: str,
    workspace_root: Path,
    project,
    models: str | list[str] | None = None,
    dispatch: str | None = None,
    profile_name: str = "resume",
    lang: str = "ko",
) -> dict[str, Any]:
    from .pipeline import build_writer_char_limit_report

    answers = extract_answers(writer_text)
    if not answers:
        return {
            "mode": "max",
            "models": [],
            "dispatch": "direct",
            "selected_model": None,
            "selected_text": "",
            "outputs_by_model": {},
            "warnings": ["답변 블록을 추출하지 못했습니다."],
            "reassembled_text": writer_text,
            "selection_report": {"reason": "no_answers"},
            "run_meta": {"requested_dispatch": dispatch, "effective_dispatch": "direct"},
        }

    combined_body = ""
    for q_id in sorted(answers.keys()):
        combined_body += f"\n\n### {q_id} 답변 본문\n\n{answers[q_id]['body']}"
    prompt_text = build_patina_max_prompt(
        combined_body.strip(),
        profile_name=profile_name,
        lang=lang,
    )

    selected_models = resolve_patina_max_models(workspace_root, models)
    requested_dispatch = resolve_patina_max_dispatch(workspace_root, dispatch)
    effective_dispatch = "direct"
    warnings: list[str] = []
    if requested_dispatch == "omc":
        warnings.append("patina-max dispatch=omc는 아직 지원하지 않아 direct로 강등했습니다.")

    outputs_by_model: dict[str, dict[str, Any]] = {}
    for model in selected_models:
        execution = _run_model_prompt(model, prompt_text)
        raw_output = str(execution.get("raw_output") or "").strip()
        processed = _parse_rewrite_output(raw_output, answers) if raw_output else {}
        reassembled_text = (
            reassemble_answers(writer_text, processed) if processed else writer_text
        )
        char_deltas = {
            q_id: measure_char_delta(answers[q_id]["body"], new_body)
            for q_id, new_body in processed.items()
            if q_id in answers
        }
        char_limit_report = build_writer_char_limit_report(project, reassembled_text)
        model_warnings = []
        if execution.get("error"):
            model_warnings.append(str(execution["error"]))
        outputs_by_model[model] = {
            "success": bool(execution.get("success")),
            "raw_output": raw_output,
            "processed": processed,
            "processed_count": len(processed),
            "parseable": bool(processed) and reassembled_text.strip() != "",
            "reassembled_text": reassembled_text,
            "char_deltas": char_deltas,
            "char_limit_report": char_limit_report,
            "char_limit_issue_count": len(char_limit_report.get("issues", [])),
            "total_abs_delta": sum(
                abs(int(item.get("delta", 0))) for item in char_deltas.values()
            ),
            "warnings": model_warnings,
            "exit_code": execution.get("exit_code"),
        }
        if not execution.get("success"):
            warnings.append(f"{model} 실행 실패: {execution.get('error') or '빈 출력'}")

    successful_outputs = {
        model: output
        for model, output in outputs_by_model.items()
        if output.get("success") and output.get("parseable")
    }
    selected_model, selected_candidate = _select_best_candidate(
        successful_outputs or outputs_by_model,
        expected_question_count=len(answers),
    )

    if not selected_candidate or not successful_outputs:
        warnings.append("patina-max 결과를 선택하지 못해 writer 원문을 유지합니다.")
        return {
            "mode": "max",
            "models": selected_models,
            "dispatch": effective_dispatch,
            "selected_model": None,
            "selected_text": "",
            "outputs_by_model": outputs_by_model,
            "warnings": warnings,
            "reassembled_text": writer_text,
            "selection_report": {
                "reason": "all_failed",
                "requested_dispatch": requested_dispatch,
                "effective_dispatch": effective_dispatch,
            },
            "run_meta": {
                "requested_dispatch": requested_dispatch,
                "effective_dispatch": effective_dispatch,
                "selected_model": None,
            },
        }

    return {
        "mode": "max",
        "models": selected_models,
        "dispatch": effective_dispatch,
        "selected_model": selected_model,
        "selected_text": selected_candidate.get("reassembled_text", ""),
        "outputs_by_model": outputs_by_model,
        "warnings": warnings,
        "reassembled_text": selected_candidate.get("reassembled_text", writer_text),
        "selection_report": {
            "reason": "selected_best_candidate",
            "requested_dispatch": requested_dispatch,
            "effective_dispatch": effective_dispatch,
            "selected_model": selected_model,
            "candidate_order": list((successful_outputs or outputs_by_model).keys()),
        },
        "run_meta": {
            "requested_dispatch": requested_dispatch,
            "effective_dispatch": effective_dispatch,
            "selected_model": selected_model,
        },
    }
