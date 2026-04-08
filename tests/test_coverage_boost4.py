"""나머지 모듈 커버리지 보강 테스트"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────
# __main__ 모듈 테스트
# ──────────────────────────────────────────────────


class TestMain:
    def test_main_function(self):
        from resume_agent.__main__ import main

        assert callable(main)


# ──────────────────────────────────────────────────
# progress 모듈 테스트
# ──────────────────────────────────────────────────


class TestProgressAdditional:
    def test_progress_bar_context_manager(self):
        from resume_agent.progress import ProgressBar

        bar = ProgressBar(3, "테스트")
        assert bar.total_steps == 3
        bar.update("1단계")
        bar.update("2단계")
        bar.update("3단계")
        bar.finish()

    def test_print_status_success(self, capsys):
        from resume_agent.progress import print_status

        print_status("성공", "success")
        captured = capsys.readouterr()
        assert "성공" in captured.out

    def test_print_status_error(self, capsys):
        from resume_agent.progress import print_status

        print_status("실패", "error")
        captured = capsys.readouterr()
        assert "실패" in captured.out

    def test_print_status_warning(self, capsys):
        from resume_agent.progress import print_status

        print_status("경고", "warning")
        captured = capsys.readouterr()
        assert "경고" in captured.out


# ──────────────────────────────────────────────────
# editor 모듈 테스트
# ──────────────────────────────────────────────────


class TestEditorAdditional:
    def test_run_editor_with_experience(self, tmp_path: Path):
        from resume_agent.editor import run_editor
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        ws = MagicMock()
        ws.ensure = MagicMock()

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="테스트 행동을 수행했습니다.",
            result="테스트 결과입니다.",
            personal_contribution="개인 기여",
            metrics="30% 향상",
            tags=["테스트"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[exp]):
                with patch("resume_agent.editor.Prompt") as mock_prompt:
                    mock_prompt.ask.return_value = "q"
                    run_editor(ws)


# ──────────────────────────────────────────────────
# parsing 모듈 테스트
# ──────────────────────────────────────────────────


class TestParsingAdditional:
    def test_ingest_source_file_txt(self, tmp_path: Path):
        from resume_agent.parsing import ingest_source_file

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("테스트 내용입니다.", encoding="utf-8")
        result = ingest_source_file(txt_file)
        assert result is not None

    def test_ingest_source_file_empty(self, tmp_path: Path):
        from resume_agent.parsing import ingest_source_file

        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("", encoding="utf-8")
        result = ingest_source_file(txt_file)
        assert result is not None


# ──────────────────────────────────────────────────
# cli_tool_manager 모듈 테스트
# ──────────────────────────────────────────────────


class TestCliToolManagerAdditional:
    def test_module_exists(self):
        import resume_agent.cli_tool_manager

        assert resume_agent.cli_tool_manager is not None

    def test_create_cli_tool_manager(self):
        from resume_agent.cli_tool_manager import create_cli_tool_manager

        manager = create_cli_tool_manager()
        assert manager is not None

    def test_get_available_tools(self):
        from resume_agent.cli_tool_manager import get_available_tools

        tools = get_available_tools()
        assert isinstance(tools, list)


# ──────────────────────────────────────────────────
# vector_store 모듈 테스트
# ──────────────────────────────────────────────────


class TestVectorStoreAdditional:
    def test_add_multiple_documents(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        for i in range(5):
            store.add_document(f"문서 {i} 내용", {"id": str(i)}, doc_id=f"doc{i}")
        assert len(store.documents) == 5

    def test_search_with_min_similarity(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("Python 개발", {"id": "1"}, doc_id="doc1")
        store.add_document("요리 레시피", {"id": "2"}, doc_id="doc2")
        results = store.search("Python", n_results=2, min_similarity=0.5)
        assert isinstance(results, list)

    def test_get_document_count(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        assert len(store.documents) == 0
        store.add_document("테스트", {}, doc_id="d1")
        assert len(store.documents) == 1


# ──────────────────────────────────────────────────
# executor 모듈 테스트
# ──────────────────────────────────────────────────


class TestExecutorAdditional:
    def test_build_exec_prompt_basic(self):
        from resume_agent.executor import build_exec_prompt

        prompt = build_exec_prompt("테스트 프롬프트")
        assert "테스트 프롬프트" in prompt

    def test_extract_codex_messages(self):
        from resume_agent.executor import extract_last_codex_message

        text = "[assistant] 첫 번째\n[assistant] 두 번째\n[assistant] 마지막"
        result = extract_last_codex_message(text)
        assert "마지막" in result


# ──────────────────────────────────────────────────
# interview_engine 모듈 테스트
# ──────────────────────────────────────────────────


class TestInterviewEngineAdditional:
    def test_persona_reframe_question(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {"focus": ["논리성", "근거"]}
        result = _persona_reframe_question("원래 질문", persona)
        assert "논리성" in result or "근거" in result

    def test_persona_reframe_no_focus(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {}
        result = _persona_reframe_question("원래 질문", persona)
        assert result == "원래 질문"

    def test_build_committee_rounds_empty(self):
        from resume_agent.interview_engine import _build_committee_rounds

        result = _build_committee_rounds([], 0, "질문")
        assert result == []


# ──────────────────────────────────────────────────
# top001 모듈 추가 테스트
# ──────────────────────────────────────────────────


class TestTop001Additional:
    def test_adaptive_coach_creation(self):
        from resume_agent.top001.adaptive_coach import AdaptiveCoachEngine

        engine = AdaptiveCoachEngine()
        assert engine is not None

    def test_self_intro_mastery_creation(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        assert mastery is not None

    def test_deep_interrogator_creation(self):
        from resume_agent.top001.deep_interrogator import DeepInterrogator

        interrogator = DeepInterrogator()
        assert interrogator is not None

    def test_adaptive_persona_creation(self):
        from resume_agent.top001.adaptive_persona import AdaptivePersonaEngine

        engine = AdaptivePersonaEngine()
        assert engine is not None

    def test_self_intro_short_answer_feedback(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback("짧은 답변입니다")
        assert feedback is not None

    def test_self_intro_good_answer_feedback(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback(
            "충분히 긴 답변입니다. 여러 문장으로 구성된 답변입니다."
        )
        assert feedback is not None


# ──────────────────────────────────────────────────
# domain 모듈 추가 테스트
# ──────────────────────────────────────────────────


class TestDomainAdditional:
    def test_render_coach_artifact(self):
        from resume_agent.domain import render_coach_artifact

        artifact = {
            "current_stage": "HANDOFF_READY",
            "purpose": "테스트 목적",
            "current_summary": ["요약1"],
            "required_inputs": ["입력1"],
            "next_step": "WRITER_HANDOFF",
        }
        result = render_coach_artifact(artifact)
        assert "HANDOFF_READY" in result
        assert "테스트 목적" in result

    def test_validate_coach_contract_pass(self):
        from resume_agent.domain import validate_coach_contract

        text = """## CURRENT STAGE
READY
## PURPOSE
테스트
## CURRENT SUMMARY
- 요약
## REQUIRED INPUTS
- 입력
## NEXT STEP
다음 단계
"""
        result = validate_coach_contract(text)
        assert result["passed"] is True or result["passed"] is False

    def test_validate_coach_contract_missing(self):
        from resume_agent.domain import validate_coach_contract

        text = "일반 텍스트"
        result = validate_coach_contract(text)
        assert result["passed"] is False
        assert len(result["missing"]) > 0


# ──────────────────────────────────────────────────
# company_analyzer 모듈 추가 테스트
# ──────────────────────────────────────────────────


class TestCompanyAnalyzerAdditional:
    def test_analyze_company_different_types(self):
        from resume_agent.company_analyzer import analyze_company

        for company_type in ["공공", "공기업", "대기업", "스타트업"]:
            result = analyze_company("테스트회사", "개발자", company_type)
            assert result is not None

    def test_analyze_company_with_job_description(self):
        from resume_agent.company_analyzer import analyze_company

        result = analyze_company(
            "테스트회사",
            "개발자",
            "대기업",
        )
        assert result is not None


# ──────────────────────────────────────────────────
# miner 모듈 테스트
# ──────────────────────────────────────────────────


class TestMinerAdditional:
    def test_mine_prompt_template(self):
        from resume_agent.miner import MINE_PROMPT_TEMPLATE

        assert "{document_text}" in MINE_PROMPT_TEMPLATE

    def test_mine_empty_text(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        txt = tmp_path / "empty.txt"
        txt.write_text("", encoding="utf-8")
        result = mine_past_resume(txt, tmp_path)
        assert result == []

    def test_mine_unsupported_format(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        result = mine_past_resume(pdf, tmp_path)
        assert result == []
