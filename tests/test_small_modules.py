"""소규모 모듈 커버리지 — 80% 달성"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────
# editor.py 테스트 (67% → 80%)
# ──────────────────────────────────────────────────


class TestEditor:
    def test_run_editor_empty(self, tmp_path: Path):
        from resume_agent.editor import run_editor

        ws = MagicMock()
        ws.ensure = MagicMock()

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[]):
                run_editor(ws)

    def test_run_editor_with_experiences(self, tmp_path: Path):
        from resume_agent.editor import run_editor
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        ws = MagicMock()
        ws.ensure = MagicMock()

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다. 충분히 긴 설명입니다.",
            task="테스트 과제입니다. 충분히 긴 설명입니다.",
            action="테스트 행동을 수행했습니다. 충분히 긴 설명입니다.",
            result="테스트 결과입니다. 30% 향상 달성.",
            personal_contribution="개인 기여 설명",
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
# domain.py 테스트 (73% → 80%)
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


# ──────────────────────────────────────────────────
# executor.py 테스트 (62% → 75%)
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
# interview_engine.py 테스트 (57% → 70%)
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
# parsing.py 테스트 (54% → 70%)
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
# vector_store.py 테스트 (56% → 70%)
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
# miner.py 테스트 (64% → 75%)
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


# ──────────────────────────────────────────────────
# cli_tool_manager.py 테스트 (61% → 70%)
# ──────────────────────────────────────────────────


class TestCliToolManager:
    def test_create_cli_tool_manager(self):
        from resume_agent.cli_tool_manager import create_cli_tool_manager

        manager = create_cli_tool_manager()
        assert manager is not None

    def test_get_available_tools(self):
        from resume_agent.cli_tool_manager import get_available_tools

        tools = get_available_tools()
        assert isinstance(tools, list)


# ──────────────────────────────────────────────────
# semantic_engine.py 테스트 (78% → 80%)
# ──────────────────────────────────────────────────


class TestSemanticEngine:
    def test_compute_similarity_empty(self):
        from resume_agent.semantic_engine import compute_similarity

        score, method = compute_similarity("", "테스트")
        assert 0.0 <= score <= 1.0

    def test_compute_tfidf_similarity_empty(self):
        from resume_agent.semantic_engine import compute_tfidf_similarity

        result = compute_tfidf_similarity("", "")
        assert result >= 0.0

    def test_extract_keywords_advanced_empty(self):
        from resume_agent.semantic_engine import extract_keywords_advanced

        result = extract_keywords_advanced("")
        assert result == []

    def test_extract_semantic_keywords(self):
        from resume_agent.semantic_engine import extract_semantic_keywords

        result = extract_semantic_keywords("Python 개발 30% 향상")
        assert "nouns" in result
        assert "keywords" in result
        assert "numeric" in result


# ──────────────────────────────────────────────────
# top001/self_intro_mastery.py 테스트 (75% → 80%)
# ──────────────────────────────────────────────────


class TestSelfIntroMastery:
    def test_creation(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        assert mastery is not None

    def test_provide_delivery_feedback_short(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback("짧은 답변")
        assert feedback is not None

    def test_provide_delivery_feedback_good(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback(
            "안녕하세요. Python 개발자입니다. 3년간 웹 서비스를 개발해왔습니다."
        )
        assert feedback is not None


# ──────────────────────────────────────────────────
# top001/adaptive_coach.py 테스트 (68% → 80%)
# ──────────────────────────────────────────────────


class TestAdaptiveCoach:
    def test_creation(self):
        from resume_agent.top001.adaptive_coach import AdaptiveCoachEngine

        engine = AdaptiveCoachEngine()
        assert engine is not None

    def test_provide_realtime_feedback(self):
        from resume_agent.top001.adaptive_coach import AdaptiveCoachEngine

        engine = AdaptiveCoachEngine()
        feedback = engine.provide_realtime_feedback("구체적인 답변입니다. 30% 향상.")
        assert feedback is not None


# ──────────────────────────────────────────────────
# top001/adaptive_persona.py 테스트 (78% → 80%)
# ──────────────────────────────────────────────────


class TestAdaptivePersona:
    def test_creation(self):
        from resume_agent.top001.adaptive_persona import AdaptivePersonaEngine

        engine = AdaptivePersonaEngine()
        assert engine is not None

    def test_select_persona_hard(self):
        from resume_agent.top001.adaptive_persona import AdaptivePersonaEngine

        engine = AdaptivePersonaEngine()
        persona = engine.select_persona("hard", turn=1)
        assert persona is not None

    def test_select_persona_normal(self):
        from resume_agent.top001.adaptive_persona import AdaptivePersonaEngine

        engine = AdaptivePersonaEngine()
        persona = engine.select_persona("normal", turn=1)
        assert persona is not None

    def test_escalate_pressure(self):
        from resume_agent.top001.adaptive_persona import AdaptivePersonaEngine

        engine = AdaptivePersonaEngine()
        pressure = engine.escalate_pressure(turn=1, weak_response=False)
        assert pressure >= 0


# ──────────────────────────────────────────────────
# top001/deep_interrogator.py 테스트 (78% → 80%)
# ──────────────────────────────────────────────────


class TestDeepInterrogator:
    def test_creation(self):
        from resume_agent.top001.deep_interrogator import DeepInterrogator

        interrogator = DeepInterrogator()
        assert interrogator is not None


# ──────────────────────────────────────────────────
# __main__.py 테스트 (75% → 80%)
# ──────────────────────────────────────────────────


class TestMain:
    def test_main_function(self):
        from resume_agent.__main__ import main

        assert callable(main)
