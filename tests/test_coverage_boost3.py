"""CLI 명령어 및 대규모 모듈 커버리지 향상 테스트"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


# ──────────────────────────────────────────────────
# CLI 모듈 테스트
# ──────────────────────────────────────────────────


class TestCliParser:
    def test_build_parser(self):
        from resume_agent.cli import build_parser

        parser = build_parser()
        assert parser is not None

    def test_parser_subcommands(self):
        from resume_agent.cli import build_parser

        parser = build_parser()
        subcommands = [
            action.dest
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subcommands) > 0

    def test_init_command(self, tmp_path: Path):
        from resume_agent.cli import cmd_init

        args = argparse.Namespace(workspace=str(tmp_path / "new_ws"))
        with patch("resume_agent.cli.init_workspace") as mock_init:
            mock_ws = MagicMock()
            mock_ws.root = tmp_path / "new_ws"
            mock_ws.state_dir = tmp_path / "new_ws" / "state"
            mock_ws.profile_dir = tmp_path / "new_ws" / "profile"
            mock_init.return_value = mock_ws
            cmd_init(args)

    def test_crawl_base_command(self, tmp_path: Path):
        from resume_agent.cli import cmd_crawl_base

        args = argparse.Namespace(workspace=str(tmp_path / "ws"), path=None)
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.crawl_base") as mock_crawl:
                mock_crawl.return_value = {
                    "source_count": 5,
                    "stored_count": 5,
                    "analysis_path": "/tmp/analysis.md",
                }
                ws = MagicMock()
                MockWS.return_value = ws
                cmd_crawl_base(args)

    def test_crawl_web_command(self, tmp_path: Path):
        from resume_agent.cli import cmd_crawl_web

        args = argparse.Namespace(
            workspace=str(tmp_path / "ws"), url=["https://example.com"]
        )
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.crawl_web_sources") as mock_crawl:
                mock_crawl.return_value = {
                    "source_count": 1,
                    "stored_count": 1,
                    "analysis_path": "/tmp/analysis.md",
                }
                ws = MagicMock()
                MockWS.return_value = ws
                cmd_crawl_web(args)

    def test_ingest_command(self, tmp_path: Path):
        from resume_agent.cli import cmd_ingest

        args = argparse.Namespace(workspace=str(tmp_path / "ws"))
        with patch("resume_agent.cli.Workspace") as MockWS:
            with patch("resume_agent.cli.ingest_examples") as mock_ingest:
                ws = MagicMock()
                MockWS.return_value = ws
                cmd_ingest(args)


# ──────────────────────────────────────────────────
# top001 모듈 테스트
# ──────────────────────────────────────────────────


class TestAdaptivePersona:
    def test_creation(self):
        from resume_agent.top001.adaptive_persona import AdaptivePersonaEngine

        engine = AdaptivePersonaEngine()
        assert engine is not None


class TestDeepInterrogator:
    def test_creation(self):
        from resume_agent.top001.deep_interrogator import DeepInterrogator

        interrogator = DeepInterrogator()
        assert interrogator is not None


class TestAdaptiveCoach:
    def test_creation(self):
        from resume_agent.top001.adaptive_coach import AdaptiveCoachEngine

        engine = AdaptiveCoachEngine()
        assert engine is not None

    def test_provide_realtime_feedback(self):
        from resume_agent.top001.adaptive_coach import AdaptiveCoachEngine

        engine = AdaptiveCoachEngine()
        feedback = engine.provide_realtime_feedback("구체적인 답변입니다")
        assert feedback is not None


class TestSelfIntroMastery:
    def test_creation(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        assert mastery is not None

    def test_provide_delivery_feedback_short(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback("짧은 답변입니다")
        assert feedback is not None

    def test_provide_delivery_feedback_good(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback(
            "충분히 긴 답변입니다. 여러 문장으로 구성된 답변입니다."
        )
        assert feedback is not None


class TestSelfIntroMastery:
    def test_creation(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        assert mastery is not None

    def test_provide_delivery_feedback_short(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback("짧은 답변입니다")
        assert feedback is not None

    def test_provide_delivery_feedback_good(self):
        from resume_agent.top001.self_intro_mastery import SelfIntroMastery

        mastery = SelfIntroMastery()
        feedback = mastery.provide_delivery_feedback(
            "충분히 긴 답변입니다. 여러 문장으로 구성된 답변입니다."
        )
        assert feedback is not None


# ──────────────────────────────────────────────────
# progress 모듈 테스트
# ──────────────────────────────────────────────────


class TestProgressBar:
    def test_creation(self):
        from resume_agent.progress import ProgressBar

        bar = ProgressBar(5, "테스트")
        assert bar.total_steps == 5

    def test_update(self):
        from resume_agent.progress import ProgressBar

        bar = ProgressBar(3)
        bar.update("1단계")
        assert bar.current_step == 1

    def test_finish(self):
        from resume_agent.progress import ProgressBar

        bar = ProgressBar(2)
        bar.update("1")
        bar.update("2")
        bar.finish()
        assert bar.current_step == 2


# ──────────────────────────────────────────────────
# company_analyzer 모듈 테스트
# ──────────────────────────────────────────────────


class TestCompanyAnalyzer:
    def test_analyze_company_basic(self):
        from resume_agent.company_analyzer import analyze_company

        result = analyze_company("테스트회사", "개발자", "대기업")
        assert result is not None
        assert result.company_name == "테스트회사"


class TestEditor:
    def test_run_editor_no_experiences(self, tmp_path: Path):
        from resume_agent.editor import run_editor

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[]):
                ws = MagicMock()
                ws.ensure = MagicMock()
                run_editor(ws)


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

    def test_stable_id_different(self):
        from resume_agent.parsing import stable_id

        id1 = stable_id("텍스트1")
        id2 = stable_id("텍스트2")
        assert id1 != id2


class TestVectorStore:
    def test_creation(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        assert store is not None

    def test_add_document(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트 문서 내용", {"id": "1"}, doc_id="doc1")
        assert len(store.documents) == 1

    def test_search(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("Python 개발 경험", {"id": "1"}, doc_id="doc1")
        store.add_document("요리 레시피", {"id": "2"}, doc_id="doc2")
        results = store.search("Python", n_results=2)
        assert isinstance(results, list)


class TestExecutor:
    def test_build_exec_prompt(self):
        from resume_agent.executor import build_exec_prompt

        result = build_exec_prompt("테스트 프롬프트")
        assert "테스트 프롬프트" in result

    def test_extract_last_codex_message(self):
        from resume_agent.executor import extract_last_codex_message

        text = "일반 텍스트\n[assistant] 테스트 메시지\n[assistant] 마지막 메시지"
        result = extract_last_codex_message(text)
        assert "마지막 메시지" in result

    def test_extract_last_codex_message_empty(self):
        from resume_agent.executor import extract_last_codex_message

        result = extract_last_codex_message("")
        assert result == ""
