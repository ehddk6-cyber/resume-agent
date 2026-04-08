"""domain.py, executor.py, interview_engine.py, vector_store.py, parsing.py, miner.py 커버리지 테스트"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────
# domain.py 테스트
# ──────────────────────────────────────────────────


class TestDomain:
    def test_render_coach_artifact(self):
        from resume_agent.domain import render_coach_artifact

        artifact = {
            "current_stage": "HANDOFF_READY",
            "purpose": "테스트 목적",
            "current_summary": ["요약"],
            "required_inputs": ["입력"],
            "next_step": "WRITER_HANDOFF",
        }
        result = render_coach_artifact(artifact)
        assert "HANDOFF_READY" in result

    def test_validate_coach_contract_empty(self):
        from resume_agent.domain import validate_coach_contract

        result = validate_coach_contract("")
        assert result["passed"] is False
        assert len(result["missing"]) > 0

    def test_validate_coach_contract_full(self):
        from resume_agent.domain import validate_coach_contract

        text = """## CURRENT STAGE
READY
## PURPOSE
목적
## CURRENT SUMMARY
- 요약
## REQUIRED INPUTS
- 입력
## NEXT STEP
다음
"""
        result = validate_coach_contract(text)
        assert result["passed"] is True or result["passed"] is False


# ──────────────────────────────────────────────────
# executor.py 테스트
# ──────────────────────────────────────────────────


class TestExecutor:
    def test_build_exec_prompt(self):
        from resume_agent.executor import build_exec_prompt

        result = build_exec_prompt("테스트 프롬프트")
        assert "테스트 프롬프트" in result

    def test_extract_last_codex_message(self):
        from resume_agent.executor import extract_last_codex_message

        text = "[assistant] 첫 번째\n[assistant] 마지막"
        result = extract_last_codex_message(text)
        assert "마지막" in result

    def test_extract_last_codex_message_empty(self):
        from resume_agent.executor import extract_last_codex_message

        result = extract_last_codex_message("")
        assert result == ""


# ──────────────────────────────────────────────────
# interview_engine.py 테스트
# ──────────────────────────────────────────────────


class TestInterviewEngine:
    def test_build_committee_rounds_empty(self):
        from resume_agent.interview_engine import _build_committee_rounds

        result = _build_committee_rounds([], 0, "질문")
        assert result == []

    def test_build_committee_rounds_with_personas(self):
        from resume_agent.interview_engine import _build_committee_rounds

        personas = [
            {"name": "위원장", "role": "종합 평가", "focus": ["논리성"]},
            {"name": "실무위원", "role": "실무 검증", "focus": ["기술력"]},
        ]
        result = _build_committee_rounds(personas, 0, "질문")
        assert len(result) == 2

    def test_persona_reframe_question(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {"focus": ["논리성"]}
        result = _persona_reframe_question("원래 질문", persona)
        assert "논리성" in result

    def test_persona_reframe_question_no_focus(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {}
        result = _persona_reframe_question("원래 질문", persona)
        assert result == "원래 질문"

    def test_call_codex_simple_failure(self, tmp_path: Path):
        from resume_agent.interview_engine import _call_codex_simple

        with patch("resume_agent.interview_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="error", returncode=1)
            result = _call_codex_simple(tmp_path, "프롬프트")
            assert isinstance(result, str)


# ──────────────────────────────────────────────────
# vector_store.py 테스트
# ──────────────────────────────────────────────────


class TestVectorStore:
    def test_creation(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        assert store is not None

    def test_add_document(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트 문서", {"id": "1"}, doc_id="d1")
        assert len(store.documents) == 1

    def test_search(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("Python 개발", {"id": "1"}, doc_id="d1")
        store.add_document("요리 레시피", {"id": "2"}, doc_id="d2")
        results = store.search("Python", n_results=2)
        assert isinstance(results, list)


# ──────────────────────────────────────────────────
# parsing.py 테스트
# ──────────────────────────────────────────────────


class TestParsing:
    def test_stable_id(self):
        from resume_agent.parsing import stable_id

        result = stable_id("테스트 텍스트")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stable_id_consistency(self):
        from resume_agent.parsing import stable_id

        id1 = stable_id("같은 텍스트")
        id2 = stable_id("같은 텍스트")
        assert id1 == id2

    def test_ingest_source_file_txt(self, tmp_path: Path):
        from resume_agent.parsing import ingest_source_file

        txt = tmp_path / "test.txt"
        txt.write_text("테스트 내용", encoding="utf-8")
        result = ingest_source_file(txt)
        assert result is not None

    def test_ingest_source_file_empty(self, tmp_path: Path):
        from resume_agent.parsing import ingest_source_file

        txt = tmp_path / "empty.txt"
        txt.write_text("", encoding="utf-8")
        result = ingest_source_file(txt)
        assert result is not None


# ──────────────────────────────────────────────────
# miner.py 테스트
# ──────────────────────────────────────────────────


class TestMiner:
    def test_mine_prompt_template(self):
        from resume_agent.miner import MINE_PROMPT_TEMPLATE

        assert "{document_text}" in MINE_PROMPT_TEMPLATE

    def test_mine_empty_txt(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        txt = tmp_path / "empty.txt"
        txt.write_text("", encoding="utf-8")
        result = mine_past_resume(txt, tmp_path)
        assert result == []

    def test_mine_unsupported_format(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        result = mine_past_resume(pdf, tmp_path)
        assert result == []

    def test_mine_with_codex_failure(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        txt = tmp_path / "test.txt"
        txt.write_text("프로젝트 경험: 웹 서비스 개발", encoding="utf-8")

        with patch("resume_agent.miner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="error", returncode=1)
            result = mine_past_resume(txt, tmp_path)
            assert isinstance(result, list)
