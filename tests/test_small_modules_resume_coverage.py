from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _stub_sentence_transformers():
    module = types.ModuleType("sentence_transformers")

    class _SentenceTransformer:
        def __init__(self, *_args, **_kwargs):
            pass

        def encode(self, text, normalize_embeddings=True):
            if isinstance(text, list):
                return [[1.0, 0.0], [0.0, 1.0]][: len(text)]
            return [0.8, 0.2]

    module.SentenceTransformer = _SentenceTransformer
    original = sys.modules.get("sentence_transformers")
    sys.modules["sentence_transformers"] = module
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop("sentence_transformers", None)
        else:
            sys.modules["sentence_transformers"] = original


def _writer_text() -> str:
    return """### Q1. 질문 하나
**[소제목] 소제목**
첫 번째 답변 본문입니다.

글자수: 12자
---
### Q2. 질문 둘
두 번째 답변 본문입니다.

글자수: 11자
"""


def _build_patina_tree(base: Path) -> None:
    (base / "patterns").mkdir(parents=True)
    (base / "profiles").mkdir()
    (base / "custom" / "profiles").mkdir(parents=True)
    (base / "core").mkdir()
    (base / "SKILL.md").write_text("skill-body", encoding="utf-8")
    (base / ".patina.default.yaml").write_text("profile: default", encoding="utf-8")
    (base / "patterns" / "ko-style.md").write_text("pattern-body", encoding="utf-8")
    (base / "core" / "voice.md").write_text("voice-body", encoding="utf-8")
    (base / "core" / "scoring.md").write_text("scoring-body", encoding="utf-8")
    (base / "profiles" / "resume.md").write_text("resume-profile", encoding="utf-8")
    (base / "profiles" / "default.md").write_text("default-profile", encoding="utf-8")
    (base / "custom" / "profiles" / "customized.md").write_text(
        "custom-profile",
        encoding="utf-8",
    )


class TestPatinaBridgeCoverage:
    def test_loaders_extractors_and_status(self, tmp_path: Path):
        from resume_agent import patina_bridge as pb

        skill_dir = tmp_path / "patina"
        _build_patina_tree(skill_dir)

        with patch.object(pb, "get_patina_skill_dir", return_value=skill_dir):
            assert pb.load_patina_skill_md() == "skill-body"
            assert "ko-style.md" in pb.load_patina_patterns()
            assert pb.load_patina_scoring() == "scoring-body"
            assert pb.load_patina_voice() == "voice-body"
            assert pb.load_patina_profile("customized") == "custom-profile"
            assert pb.load_patina_profile("missing") == "default-profile"
            assert pb.load_patina_config() == "profile: default"

            answers = pb.extract_answers(_writer_text())
            assert answers["Q1"]["subtitle"].startswith("**[소제목]")
            rebuilt = pb.reassemble_answers(_writer_text(), {"Q1": "바뀐 본문"})
            assert "바뀐 본문" in rebuilt
            delta = pb.measure_char_delta("12345", "123")
            assert delta["delta_pct"] == -40.0

            prompt = pb.build_patina_prompt("본문", mode="score")
            assert "scoring-body" in prompt
            assert "### AI 유사도 점수" in prompt
            assert "audit" in pb.build_patina_audit_report_prompt("본문")
            assert "rewrite" in pb.build_patina_rewrite_prompt("본문")
            assert "score" in pb.build_patina_score_prompt("본문")
            assert "ouroboros" in pb.build_patina_ouroboros_prompt("본문")

            status = pb.get_patina_status()
            assert status["available"] is True
            assert "resume" in status["profiles"]

        with patch.object(pb, "get_patina_skill_dir", side_effect=FileNotFoundError("없음")):
            status = pb.get_patina_status()
        assert status["available"] is False

    def test_parse_helpers_and_run_patina_paths(self, tmp_path: Path):
        from resume_agent import patina_bridge as pb

        skill_dir = tmp_path / "patina"
        _build_patina_tree(skill_dir)

        with pytest.raises(ValueError):
            pb.run_patina("본문", mode="invalid")

        no_answers = pb.run_patina("본문만 있습니다.", mode="audit")
        assert no_answers["warnings"]

        score = pb.parse_score_from_output("| 전체 | x | y | z | **72** |")
        assert score["interpretation"] == "AI 생성"
        assert pb.parse_score_from_output("점수 없음")["overall_score"] is None

        parsed = pb._parse_rewrite_output(
            "### Q1\n바뀐 답변\n### Q2\n또 다른 답변",
            {"Q1": {"body": "원본1"}, "Q2": {"body": "원본2"}},
        )
        assert parsed["Q1"] == "바뀐 답변"

        parsed2 = pb._parse_rewrite_output(
            "Q1: 간단한 답변",
            {"Q1": {"body": "원본1"}},
        )
        assert parsed2["Q1"] == "간단한 답변"

        with patch.object(pb, "get_patina_skill_dir", return_value=skill_dir):
            with patch("resume_agent.cli_tool_manager.get_available_tools", return_value=["codex"]):
                with patch("resume_agent.executor.run_codex", return_value=0) as run_codex:
                    with patch.object(
                        pb,
                        "_parse_rewrite_output",
                        return_value={"Q1": "교정된 본문", "Q2": "둘째 본문"},
                    ):
                        result = pb.run_patina(
                            _writer_text(),
                            tool="missing",
                            mode="rewrite",
                        )
        assert run_codex.called
        assert "교정된 본문" in result["reassembled_text"]
        assert result["char_deltas"]["Q1"]["original_chars"] > 0

        with patch.object(pb, "get_patina_skill_dir", return_value=skill_dir):
            with patch("resume_agent.cli_tool_manager.get_available_tools", return_value=["claude"]):
                with patch("subprocess.run") as sub_run:
                    sub_run.return_value = MagicMock(returncode=1, stdout="SCORE", stderr="fail")
                    score_result = pb.run_patina(_writer_text(), tool="claude", mode="score")
        assert score_result["score_output"] == "SCORE"

        with patch.object(pb, "get_patina_skill_dir", return_value=skill_dir):
            with patch("resume_agent.cli_tool_manager.get_available_tools", return_value=["codex"]):
                with patch("resume_agent.executor.run_codex", return_value=0):
                    ouroboros = pb.run_patina_ouroboros(_writer_text(), tool="codex")
        assert ouroboros["mode"] == "ouroboros"


class TestVectorStoreCoverage:
    def test_store_load_embed_and_kb_helpers(self, tmp_path: Path):
        from resume_agent import vector_store as vs

        index_file = tmp_path / "index.json"
        index_file.write_text(
            json.dumps(
                {
                    "embedding_dimension": 99,
                    "documents": [
                        {
                            "id": "d1",
                            "text": "Python 개발 경험",
                            "metadata": {"company": "기관A", "question_type": "TYPE_A"},
                            "embedding": [0.1, 0.2],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with patch("resume_agent.vector_store.get_config_value", side_effect=lambda key, default=None: 2 if key == "embedding.dimension" else default):
            with patch.object(vs, "_USE_ST", True):
                fake_model = MagicMock()
                fake_model.encode.side_effect = [
                    [0.3, 0.7],
                    RuntimeError("fallback"),
                ]
                with patch.object(vs, "_get_st_model", return_value=fake_model):
                    store = vs.SimpleVectorStore(str(tmp_path))
                    assert "d1" in store.documents
                    doc_id = store.add_document("새 문서", {"company": "기관B"}, doc_id="d2")
                    assert doc_id == "d2"
                    assert store.get_document("d2") is not None
                    assert store.delete_document("missing") is False
                    assert store.delete_document("d2") is True
                    assert store._extract_features("") == []
                    assert store._feature_index("abc", 10) < 10
                    assert store._cosine_similarity([1.0], [1.0, 2.0]) == 0.0
                    assert store._cosine_similarity([0.0], [1.0]) == 0.0
                    assert store.search("Python", min_similarity=0.0)
                    docs = store.list_documents()
                    assert docs[0]["metadata"]["company"] == "기관A"
                    store.clear()
                    assert store.documents == {}

        kb = vs.VectorKnowledgeBase(str(tmp_path / "kb"))
        kb.index_pattern("p1", "협업 경험", {"company": "기관A", "question_type": "TYPE_C"})
        kb.index_pattern("p2", "데이터 분석", {"company": "기관B", "question_type": "TYPE_B"})
        assert kb.search_similar("협업", n_results=1)
        assert kb.search_by_company("기관A")[0]["id"] == "p1"
        assert kb.search_by_question_type("type_b")[0]["id"] == "p2"
        stats = kb.get_statistics()
        assert stats["total_patterns"] == 2
        assert vs.create_vector_knowledge_base(str(tmp_path / "factory")).store is not None


class TestClassifierCoverage:
    def test_classifier_regex_and_embedding_paths(self):
        from resume_agent import classifier as cl
        from resume_agent.models import QuestionType

        assert cl.classify_question("지원동기를 설명해 주세요.") == QuestionType.TYPE_A
        qtype, confidence = cl.classify_question_with_confidence("직무역량과 강점을 말해주세요.")
        assert qtype == QuestionType.TYPE_B
        assert confidence > 0.0
        assert cl.extract_question_keywords("지원 직무 경험과 Python 역량을 설명")[:2]

        with patch.object(cl, "_compute_type_centroids", return_value=None):
            assert cl.classify_question_by_embedding("미분류 질문") == (QuestionType.TYPE_UNKNOWN, 0.0)

        fake_model = MagicMock()
        fake_model.encode.return_value = [1.0, 0.0]
        with patch.object(cl, "_compute_type_centroids", return_value={QuestionType.TYPE_C: [1.0, 0.0]}):
            with patch.object(cl, "_get_st_model_classifier", return_value=fake_model):
                qtype, confidence = cl.classify_question_by_embedding("협업 질문")
        assert qtype == QuestionType.TYPE_C
        assert confidence == 1.0

        with patch.object(cl, "_compute_type_centroids", return_value={QuestionType.TYPE_D: [0.0, 1.0]}):
            with patch.object(cl, "_get_st_model_classifier", return_value=fake_model):
                qtype, confidence = cl.classify_question_by_embedding("낮은 유사도")
        assert qtype == QuestionType.TYPE_UNKNOWN
        assert confidence < 0.3

        failing_model = MagicMock()
        failing_model.encode.side_effect = RuntimeError("boom")
        with patch.object(cl, "_compute_type_centroids", return_value={QuestionType.TYPE_A: [1.0, 0.0]}):
            with patch.object(cl, "_get_st_model_classifier", return_value=failing_model):
                assert cl.classify_question_by_embedding("예외") == (QuestionType.TYPE_UNKNOWN, 0.0)


class TestCliToolManagerCoverage:
    def test_cli_tool_manager_paths(self, tmp_path: Path):
        from resume_agent.cli_tool_manager import CLIToolManager, create_cli_tool_manager, get_available_tools

        with pytest.raises(ValueError):
            CLIToolManager("unknown")

        with patch("resume_agent.cli_tool_manager.shutil.which", return_value="/usr/bin/codex"):
            manager = CLIToolManager("codex")
            with patch("resume_agent.cli_tool_manager.subprocess.run") as sub_run:
                sub_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")
                assert manager.execute("prompt") == "done"
            info = manager.get_tool_info()
            assert info["tool"] == "codex"

        with patch("resume_agent.cli_tool_manager.shutil.which", return_value="/usr/bin/kilo"):
            manager = CLIToolManager("kilo")
            with patch("resume_agent.cli_tool_manager.subprocess.run") as sub_run:
                sub_run.return_value = MagicMock(returncode=0, stdout="kilo-ok", stderr="")
                assert manager.execute("stdin prompt") == "kilo-ok"

        with patch("resume_agent.cli_tool_manager.shutil.which", return_value=None):
            with pytest.raises(RuntimeError):
                CLIToolManager("claude")

        with patch("resume_agent.cli_tool_manager.shutil.which", return_value="/usr/bin/codex"):
            manager = CLIToolManager("codex")
            with patch("resume_agent.cli_tool_manager.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="codex", timeout=1)):
                with pytest.raises(TimeoutError):
                    manager.execute("prompt", timeout=1)
            with patch("resume_agent.cli_tool_manager.subprocess.run", side_effect=FileNotFoundError):
                with pytest.raises(RuntimeError):
                    manager.execute("prompt")
            with patch("resume_agent.cli_tool_manager.subprocess.run") as sub_run:
                sub_run.return_value = MagicMock(returncode=1, stdout="", stderr="bad")
                with pytest.raises(RuntimeError):
                    manager.execute("prompt")

            prompt_file = tmp_path / "prompt.md"
            prompt_file.write_text("hello", encoding="utf-8")
            with patch.object(manager, "execute", return_value="file-ok") as execute:
                assert manager.execute_with_file(prompt_file) == "file-ok"
            execute.assert_called_once()
            with pytest.raises(FileNotFoundError):
                manager.execute_with_file(tmp_path / "missing.md")

        with patch("resume_agent.cli_tool_manager.shutil.which", side_effect=lambda name: "/bin/x" if name in {"codex", "gemini"} else None):
            assert get_available_tools() == ["codex", "gemini"]

        with patch("resume_agent.cli_tool_manager.shutil.which", return_value="/usr/bin/codex"):
            assert create_cli_tool_manager("codex").tool.value == "codex"


class TestParsingCoverage:
    def test_parsing_public_helpers(self, tmp_path: Path):
        from resume_agent import parsing as ps

        source = ps.build_generic_source(tmp_path / "doc.txt", "1. 질문\n상황 행동 결과 20%")
        assert source.pattern.structure_signals.has_metrics is True

        url_source = ps.build_url_source(
            "https://example.com",
            "<html><title>예시</title><body>1. 질문</body></html>",
            title=None,
        )
        assert url_source.title == "https://example.com"

        csv_file = tmp_path / "cases.csv"
        csv_file.write_text(
            "제목,출처URL,자소서본문,합격스펙\n회사/직무/2024,https://a.test,\"1. 지원동기\\n공공기관 채용 서류전형 합격 NCS 기반 평가\",Python\n",
            encoding="utf-8",
        )
        sources, cases = ps.ingest_csv(csv_file)
        assert len(sources) == 1
        assert len(cases) == 1

        url_file = tmp_path / "links.url"
        url_file.write_text("https://a.test\nhttps://b.test\n", encoding="utf-8")
        with patch("resume_agent.parsing.ingest_public_url", side_effect=[[source], [url_source]]):
            url_sources, _ = ps.ingest_source_file(url_file)
        assert len(url_sources) == 2

        pdf_file = tmp_path / "job.pdf"
        pdf_file.write_bytes(b"%PDF")
        with patch("resume_agent.parsing.extract_text_from_pdf", return_value=""):
            assert ps.ingest_source_file(pdf_file) == ([], [])

        html_response = MagicMock()
        html_response.text = """
        <html><title>테스트 문서</title>
        <a class=\"result__a\" href=\"https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com\">링크</a>
        </html>
        """
        html_response.raise_for_status = MagicMock()
        with patch("resume_agent.parsing.requests.get", return_value=html_response):
            discovered = ps.discover_public_urls("테스트", limit=1)
            ingested = ps.ingest_public_url("https://example.com")
        assert discovered[0]["url"] == "https://example.com"
        assert ingested[0].title == "테스트 문서"
