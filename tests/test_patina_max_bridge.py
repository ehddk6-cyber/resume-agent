from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from resume_agent.models import ApplicationProject, Question
from resume_agent.patina_max_bridge import (
    get_patina_max_skill_dir,
    resolve_patina_max_models,
    run_patina_max,
)


def test_get_patina_max_skill_dir_prefers_nested_codex_path(tmp_path: Path):
    nested = tmp_path / ".codex" / "skills" / "patina" / "patina-max"
    nested.mkdir(parents=True)
    fallback = tmp_path / ".codex" / "skills" / "patina-max"
    fallback.mkdir(parents=True)

    with patch("resume_agent.patina_max_bridge.Path.home", return_value=tmp_path):
        assert get_patina_max_skill_dir() == nested


def test_resolve_patina_max_models_uses_workspace_config(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / ".patina.yaml").write_text(
        "max-models:\n  - gemini\n  - codex\n", encoding="utf-8"
    )

    models = resolve_patina_max_models(workspace, None)
    assert models == ["gemini", "codex"]


def test_run_patina_max_keeps_writer_text_when_all_models_fail(tmp_path: Path):
    project = ApplicationProject(
        questions=[Question(id="q1", order_no=1, question_text="질문", char_limit=30)]
    )
    writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
### Q1. 질문
**[소제목] 테스트**
원문 답변입니다.

글자수: 약 10 자 (공백 포함) / 제한 대비 30%

## 블록 4: SELF-CHECK
- PASS
"""

    with patch(
        "resume_agent.patina_max_bridge.build_patina_max_prompt",
        return_value="prompt",
    ):
        with patch(
            "resume_agent.patina_max_bridge._run_model_prompt",
            return_value={
                "success": False,
                "raw_output": "",
                "exit_code": 1,
                "error": "boom",
            },
        ):
            result = run_patina_max(
                writer_text=writer_text,
                workspace_root=tmp_path,
                project=project,
                models="claude,codex",
    )

    assert result["selected_model"] is None
    assert result["reassembled_text"] == writer_text
    assert "writer 원문을 유지" in result["warnings"][-1]


def test_run_patina_max_selects_successful_model(tmp_path: Path):
    project = ApplicationProject(
        questions=[Question(id="q1", order_no=1, question_text="질문", char_limit=60)]
    )
    writer_text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 없음

## 블록 2: OUTLINE
- 없음

## 블록 3: DRAFT ANSWERS
### Q1. 질문
**[소제목] 테스트**
원문 답변입니다.

글자수: 약 10 자 (공백 포함) / 제한 대비 30%

## 블록 4: SELF-CHECK
- PASS
"""

    def fake_runner(model: str, prompt_text: str, timeout: int = 900):
        if model == "claude":
            return {
                "success": False,
                "raw_output": "",
                "exit_code": 1,
                "error": "fail",
            }
        return {
            "success": True,
            "raw_output": "### Q1\n지원 직무와 연결되는 실무 경험을 자연스럽게 설명합니다.",
            "exit_code": 0,
            "error": None,
        }

    with patch(
        "resume_agent.patina_max_bridge.build_patina_max_prompt",
        return_value="prompt",
    ):
        with patch(
            "resume_agent.patina_max_bridge._run_model_prompt",
            side_effect=fake_runner,
        ):
            result = run_patina_max(
                writer_text=writer_text,
                workspace_root=tmp_path,
                project=project,
                models="claude,codex",
            )

    assert result["selected_model"] == "codex"
    assert result["outputs_by_model"]["claude"]["success"] is False
    assert result["outputs_by_model"]["codex"]["success"] is True
    assert "지원 직무와 연결되는 실무 경험" in result["reassembled_text"]
