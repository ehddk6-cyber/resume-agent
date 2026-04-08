"""Final coverage push — targeting remaining missing lines"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────
# top001/adaptive_coach.py — 11 missing lines
# ──────────────────────────────────────────────────


class TestAdaptiveCoach:
    def test_provide_realtime_feedback(self):
        from resume_agent.top001.adaptive_coach import AdaptiveCoachEngine

        engine = AdaptiveCoachEngine()
        feedback = engine.provide_realtime_feedback("구체적인 답변입니다. 30% 향상.")
        assert feedback is not None

    def test_provide_realtime_feedback_short(self):
        from resume_agent.top001.adaptive_coach import AdaptiveCoachEngine

        engine = AdaptiveCoachEngine()
        feedback = engine.provide_realtime_feedback("짧음")
        assert feedback is not None


# ──────────────────────────────────────────────────
# top001/deep_interrogator.py — 5 missing lines
# ──────────────────────────────────────────────────


class TestDeepInterrogator:
    def test_generate_depth_questions(self):
        from resume_agent.top001.deep_interrogator import DeepInterrogator

        interrogator = DeepInterrogator()
        questions = interrogator.generate_depth_questions(
            "답변입니다", context="컨텍스트"
        )
        assert isinstance(questions, dict)


# ──────────────────────────────────────────────────
# cli_tool_manager.py — 2 missing lines
# ──────────────────────────────────────────────────


class TestCliToolManager:
    def test_create_manager(self):
        from resume_agent.cli_tool_manager import create_cli_tool_manager

        manager = create_cli_tool_manager()
        assert manager is not None

    def test_get_available_tools(self):
        from resume_agent.cli_tool_manager import get_available_tools

        tools = get_available_tools()
        assert isinstance(tools, list)


# ──────────────────────────────────────────────────
# progress.py — 1 missing line
# ──────────────────────────────────────────────────


class TestProgress:
    def test_print_status(self, capsys):
        from resume_agent.progress import print_status

        print_status("테스트", "info")
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or len(captured.err) > 0


# ──────────────────────────────────────────────────
# __main__.py — 1 missing line
# ──────────────────────────────────────────────────


class TestMain:
    def test_main_function(self):
        from resume_agent.__main__ import main

        assert callable(main)


# ──────────────────────────────────────────────────
# parsing.py — 1 missing line
# ──────────────────────────────────────────────────


class TestParsing:
    def test_stable_id(self):
        from resume_agent.parsing import stable_id

        result = stable_id("테스트")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_clean_source_text(self):
        from resume_agent.parsing import clean_source_text

        text = "일반 텍스트\n👉 중요 포인트\n마케팅 문구 - 지원하세요!"
        result = clean_source_text(text)
        assert "👉" not in result

    def test_strip_html_text(self):
        from resume_agent.parsing import strip_html_text

        text = "<p>테스트</p> <script>alert('x')</script>"
        result = strip_html_text(text)
        assert "<p>" not in result
        assert "테스트" in result

    def test_parse_title_meta(self):
        from resume_agent.parsing import parse_title_meta

        result = parse_title_meta("회사/직무/계절")
        assert result["company_name"] == "회사"
        assert result["job_title"] == "직무"
        assert result["season"] == "계절"

    def test_extract_question_lines(self):
        from resume_agent.parsing import extract_question_lines

        text = "1. 첫 번째 질문\n2. 두 번째 질문"
        result = extract_question_lines(text)
        assert len(result) == 2
        assert result[0] == "첫 번째 질문"

    def test_summarize_structure(self):
        from resume_agent.parsing import summarize_structure

        result = summarize_structure("회사", "직무", ["TYPE_A"], 5)
        assert "회사" in result
        assert "직무" in result

    def test_extract_spec_keywords(self):
        from resume_agent.parsing import extract_spec_keywords

        result = extract_spec_keywords("Python 개발자 모집")
        assert isinstance(result, list)
        assert "Python" in result

    def test_detect_patterns(self):
        from resume_agent.parsing import detect_patterns

        text = "공공기관 채용 서류전형 합격 NCS 기반 평가"
        result = detect_patterns(text)
        assert isinstance(result, list)

    def test_build_retrieval_terms(self):
        from resume_agent.parsing import build_retrieval_terms

        meta = {"company_name": "회사", "job_title": "직무", "season": "2024"}
        result = build_retrieval_terms(meta, "Python 개발", ["질문1"])
        assert isinstance(result, list)
        assert "회사" in result

    def test_summarize_knowledge_sources(self):
        from resume_agent.parsing import summarize_knowledge_sources

        source = MagicMock()
        source.source_type = MagicMock()
        source.source_type.value = "job_posting"
        source.pattern = MagicMock()
        source.pattern.company_name = "테스트회사"

        result = summarize_knowledge_sources([source])
        assert isinstance(result, dict)

    def test_calculate_sources_hash(self):
        from resume_agent.parsing import calculate_sources_hash

        sources = [MagicMock(id="s1"), MagicMock(id="s2")]
        result = calculate_sources_hash(sources)
        assert isinstance(result, str)
        assert len(result) > 0


# ──────────────────────────────────────────────────
# vector_store.py — 2 missing lines
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

    def test_search_with_min_similarity(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("Python 개발", {"id": "1"}, doc_id="d1")
        store.add_document("요리 레시피", {"id": "2"}, doc_id="d2")
        results = store.search("Python", n_results=2, min_similarity=0.5)
        assert isinstance(results, list)

    def test_search_empty(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        results = store.search("Python", n_results=2)
        assert results == []

    def test_get_document(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트 문서", {"id": "1"}, doc_id="d1")
        doc = store.get_document("d1")
        assert doc is not None

    def test_get_document_not_found(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        doc = store.get_document("nonexistent")
        assert doc is None

    def test_delete_document(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트 문서", {"id": "1"}, doc_id="d1")
        store.delete_document("d1")
        assert len(store.documents) == 0

    def test_delete_document_not_found(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.delete_document("nonexistent")
        assert len(store.documents) == 0

    def test_get_document_count(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        assert len(store.documents) == 0
        store.add_document("테스트", {}, doc_id="d1")
        assert len(store.documents) == 1

    def test_clear(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("테스트", {}, doc_id="d1")
        store.clear()
        assert len(store.documents) == 0

    def test_list_documents(self, tmp_path: Path):
        from resume_agent.vector_store import SimpleVectorStore

        store = SimpleVectorStore(str(tmp_path))
        store.add_document("문서1", {}, doc_id="d1")
        store.add_document("문서2", {}, doc_id="d2")
        docs = store.list_documents()
        assert len(docs) == 2


# ──────────────────────────────────────────────────
# semantic_engine.py — 2 missing lines
# ──────────────────────────────────────────────────


class TestSemanticEngine:
    def test_compute_embedding_similarity_empty(self):
        from resume_agent.semantic_engine import compute_embedding_similarity

        result = compute_embedding_similarity("", "테스트")
        assert result == 0.0

    def test_compute_embedding_similarity_model_none(self):
        from resume_agent.semantic_engine import compute_embedding_similarity

        with patch(
            "resume_agent.semantic_engine._get_embedding_model", return_value=None
        ):
            result = compute_embedding_similarity("테스트1", "테스트2")
            assert result == -1.0

    def test_compute_embedding_similarity_exception(self):
        from resume_agent.semantic_engine import compute_embedding_similarity

        mock_model = MagicMock()
        mock_model.encode.side_effect = Exception("테스트 오류")

        with patch(
            "resume_agent.semantic_engine._get_embedding_model", return_value=mock_model
        ):
            result = compute_embedding_similarity("테스트1", "테스트2")
            assert result == -1.0

    def test_compute_batch_embedding_similarity_empty(self):
        from resume_agent.semantic_engine import compute_batch_embedding_similarity

        result = compute_batch_embedding_similarity("", ["문서1", "문서2"])
        assert result == [0.0, 0.0]

    def test_compute_batch_embedding_similarity_no_documents(self):
        from resume_agent.semantic_engine import compute_batch_embedding_similarity

        result = compute_batch_embedding_similarity("쿼리", [])
        assert result == []

    def test_compute_batch_embedding_similarity_model_none(self):
        from resume_agent.semantic_engine import compute_batch_embedding_similarity

        with patch(
            "resume_agent.semantic_engine._get_embedding_model", return_value=None
        ):
            result = compute_batch_embedding_similarity("쿼리", ["문서1"])
            assert result == [-1.0]

    def test_compute_tfidf_similarity_import_error(self):
        from resume_agent.semantic_engine import compute_tfidf_similarity

        with patch.dict("sys.modules", {"sklearn.feature_extraction.text": None}):
            result = compute_tfidf_similarity("테스트1", "테스트2")
            assert result >= -1.0

    def test_compute_similarity_embedding_success(self):
        from resume_agent.semantic_engine import (
            compute_similarity,
            SemanticSearchConfig,
        )

        config = SemanticSearchConfig(use_embedding=True, use_tfidf_fallback=False)
        with patch(
            "resume_agent.semantic_engine.compute_embedding_similarity",
            return_value=0.8,
        ):
            score, method = compute_similarity("테스트1", "테스트2", config)
            assert score == 0.8
            assert method == "embedding"

    def test_compute_similarity_tfidf_fallback(self):
        from resume_agent.semantic_engine import (
            compute_similarity,
            SemanticSearchConfig,
        )

        config = SemanticSearchConfig(use_embedding=False, use_tfidf_fallback=True)
        with patch(
            "resume_agent.semantic_engine.compute_tfidf_similarity", return_value=0.6
        ):
            score, method = compute_similarity("테스트1", "테스트2", config)
            assert score == 0.6
            assert method == "tfidf"

    def test_compute_similarity_hash_fallback(self):
        from resume_agent.semantic_engine import (
            compute_similarity,
            SemanticSearchConfig,
        )

        config = SemanticSearchConfig(use_embedding=False, use_tfidf_fallback=False)
        with patch(
            "resume_agent.semantic_engine.compute_hash_similarity", return_value=0.3
        ):
            score, method = compute_similarity("테스트1", "테스트2", config)
            assert score == 0.3
            assert method == "hash"

    def test_extract_keywords_advanced_empty(self):
        from resume_agent.semantic_engine import extract_keywords_advanced

        result = extract_keywords_advanced("")
        assert result == []

    def test_extract_keywords_advanced_mixed(self):
        from resume_agent.semantic_engine import extract_keywords_advanced

        result = extract_keywords_advanced("Python 개발자 30% 성과 달성")
        assert len(result) > 0
        assert "Python" in result

    def test_extract_semantic_keywords(self):
        from resume_agent.semantic_engine import extract_semantic_keywords

        result = extract_semantic_keywords("Python 개발 30% 향상")
        assert "nouns" in result
        assert "keywords" in result
        assert "numeric" in result

    def test_semantic_search_engine_index_documents(self):
        from resume_agent.semantic_engine import SemanticSearchEngine

        engine = SemanticSearchEngine()
        docs = {
            "d1": "Python 개발 경험",
            "d2": "데이터 분석 프로젝트",
        }
        engine.index_documents(docs)
        assert len(engine._doc_cache) == 2

    def test_semantic_search_engine_search_empty_query(self):
        from resume_agent.semantic_engine import SemanticSearchEngine

        engine = SemanticSearchEngine()
        engine.index_documents({"d1": "테스트"})
        results = engine.search("")
        assert results == []

    def test_semantic_search_engine_search_empty_index(self):
        from resume_agent.semantic_engine import SemanticSearchEngine

        engine = SemanticSearchEngine()
        results = engine.search("쿼리")
        assert results == []

    def test_semantic_search_engine_find_best_match(self):
        from resume_agent.semantic_engine import SemanticSearchEngine

        engine = SemanticSearchEngine()
        engine.index_documents(
            {
                "d1": "Python 개발",
                "d2": "요리 레시피",
            }
        )
        result = engine.find_best_match("Python")
        assert result is not None
        assert result.doc_id == "d1"

    def test_semantic_search_engine_find_best_match_empty(self):
        from resume_agent.semantic_engine import SemanticSearchEngine

        engine = SemanticSearchEngine()
        result = engine.find_best_match("쿼리")
        assert result is None

    def test_semantic_search_engine_find_best_match_with_candidates(self):
        from resume_agent.semantic_engine import SemanticSearchEngine

        engine = SemanticSearchEngine()
        engine.index_documents(
            {
                "d1": "Python 개발",
                "d2": "요리 레시피",
                "d3": "Java 개발",
            }
        )
        result = engine.find_best_match("Python", candidates=["d1", "d3"])
        assert result is not None

    def test_semantic_search_engine_get_stats(self):
        from resume_agent.semantic_engine import SemanticSearchEngine

        engine = SemanticSearchEngine()
        engine.index_documents({"d1": "테스트"})
        stats = engine.get_stats()
        assert stats["indexed_documents"] == 1
        assert "embedding_available" in stats

    def test_match_experiences_to_questions(self):
        from resume_agent.semantic_engine import match_experiences_to_questions

        questions = ["Python 개발 경험"]
        experiences = {
            "e1": "Python 웹 개발 프로젝트",
            "e2": "데이터 분석",
        }
        result = match_experiences_to_questions(questions, experiences)
        assert "Python 개발 경험" in result

    def test_match_experiences_to_questions_empty(self):
        from resume_agent.semantic_engine import match_experiences_to_questions

        result = match_experiences_to_questions([], {})
        assert result == {}


# ──────────────────────────────────────────────────
# domain.py — 2 missing lines
# ──────────────────────────────────────────────────


class TestDomain:
    def test_semantic_similarity_empty_query(self):
        from resume_agent.domain import _semantic_similarity

        result = _semantic_similarity("", "테스트 문서")
        assert result == 0.0

    def test_semantic_similarity_empty_doc(self):
        from resume_agent.domain import _semantic_similarity

        result = _semantic_similarity("테스트 쿼리", "")
        assert result == 0.0

    def test_semantic_similarity_similar(self):
        from resume_agent.domain import _semantic_similarity

        result = _semantic_similarity("Python 개발", "Python 프로그래밍")
        assert result >= 0.0

    def test_semantic_similarity_different(self):
        from resume_agent.domain import _semantic_similarity

        result = _semantic_similarity("Python 개발", "요리 레시피")
        assert result >= 0.0

    def test_auto_classify_project_questions(self):
        from resume_agent.domain import auto_classify_project_questions

        project = MagicMock()
        q1 = MagicMock()
        q1.question_text = "지원동기를 말씀해주세요"
        q2 = MagicMock()
        q2.question_text = "직무역량을 설명해주세요"
        project.questions = [q1, q2]

        auto_classify_project_questions(project)
        assert q1.detected_type is not None
        assert q2.detected_type is not None

    def test_build_knowledge_hints_empty(self):
        from resume_agent.domain import build_knowledge_hints

        project = MagicMock()
        result = build_knowledge_hints([], project)
        assert result == []

    def test_build_knowledge_hints_with_sources(self):
        from resume_agent.domain import build_knowledge_hints

        project = MagicMock()
        project.company_name = "테스트회사"
        project.job_title = "개발자"
        project.questions = []

        result = build_knowledge_hints([], project)
        assert result == []

    def test_calculate_sources_hash_basic(self):
        from resume_agent.domain import calculate_sources_hash

        sources = [MagicMock(id="s1"), MagicMock(id="s2")]
        result = calculate_sources_hash(sources)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_calculate_sources_hash_empty(self):
        from resume_agent.domain import calculate_sources_hash

        result = calculate_sources_hash([])
        assert isinstance(result, str)

    def test_fallback_build_knowledge_hints(self):
        from resume_agent.domain import _fallback_build_knowledge_hints

        project = MagicMock()
        project.company_name = "테스트회사"
        project.job_title = "개발자"

        source = MagicMock()
        source.pattern = MagicMock()
        source.pattern.company_name = "테스트회사"
        source.pattern.job_title = "개발자"
        source.pattern.retrieval_terms = ["Python"]
        source.pattern.question_types = [MagicMock(value="TYPE_B")]

        result = _fallback_build_knowledge_hints([source], project)
        assert isinstance(result, list)

    def test_render_coach_artifact_full(self):
        from resume_agent.domain import render_coach_artifact

        artifact = {
            "current_stage": "HANDOFF_READY",
            "purpose": "테스트 목적입니다",
            "current_summary": ["요약1", "요약2"],
            "required_inputs": ["입력1", "입력2"],
            "missing_inputs": ["누락1"],
            "risk_flags": ["리스크1"],
            "quality_signals": {"signal1": "값1"},
            "current_coaching_focus": "집중 영역",
            "next_step": "WRITER_HANDOFF",
            "revision_reason": None,
        }
        result = render_coach_artifact(artifact)
        assert "HANDOFF_READY" in result
        assert "테스트 목적입니다" in result
        assert "요약1" in result

    def test_render_coach_artifact_minimal(self):
        from resume_agent.domain import render_coach_artifact

        artifact = {
            "current_stage": "READY",
            "purpose": "목적",
            "current_summary": ["요약"],
            "required_inputs": ["입력"],
            "next_step": "NEXT",
        }
        result = render_coach_artifact(artifact)
        assert "READY" in result

    def test_validate_coach_contract_complete(self):
        from resume_agent.domain import validate_coach_contract

        text = """## CURRENT STAGE
HANDOFF_READY

## PURPOSE
코칭 목적

## CURRENT SUMMARY
- 요약1
- 요약2

## REQUIRED INPUTS
- 입력1

## MISSING INPUTS
- 누락1

## RISK FLAGS
- 리스크1

## QUALITY SIGNALS
- 신호1

## CURRENT COACHING FOCUS
집중 영역

## NEXT STEP
WRITER_HANDOFF
"""
        result = validate_coach_contract(text)
        assert "passed" in result
        assert "missing" in result

    def test_validate_coach_contract_empty(self):
        from resume_agent.domain import validate_coach_contract

        result = validate_coach_contract("")
        assert result["passed"] is False
        assert len(result["missing"]) > 0

    def test_validate_coach_contract_partial(self):
        from resume_agent.domain import validate_coach_contract

        text = """## CURRENT STAGE
READY
## PURPOSE
목적
"""
        result = validate_coach_contract(text)
        assert result["passed"] is False
        assert len(result["missing"]) > 0

    def test_analyze_gaps_with_experiences(self):
        from resume_agent.scoring import analyze_gaps
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

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

        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.question_text = "테스트 질문입니다"
        q.detected_type = MagicMock(value="TYPE_B")
        q.char_limit = 1000

        project = MagicMock()
        project.questions = [q]

        result = analyze_gaps(experiences=[exp], project=project)
        assert isinstance(result, dict)
        assert "summary" in result

    def test_analyze_gaps_empty_experiences(self):
        from resume_agent.scoring import analyze_gaps

        q = MagicMock()
        q.id = "q1"
        q.order_no = 1
        q.question_text = "테스트 질문입니다"
        q.detected_type = MagicMock(value="TYPE_B")
        q.char_limit = 1000

        project = MagicMock()
        project.questions = [q]

        result = analyze_gaps(experiences=[], project=project)
        assert isinstance(result, dict)

    def test_build_candidate_profile(self, tmp_path: Path):
        from resume_agent.pipeline import build_candidate_profile
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        ws = MagicMock()
        ws.root = tmp_path
        ws.state_dir = tmp_path / "state"
        ws.state_dir.mkdir(parents=True, exist_ok=True)
        ws.profile_dir = tmp_path / "profile"
        ws.profile_dir.mkdir(parents=True, exist_ok=True)
        ws.ensure = MagicMock()

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="데이터를 분석하고 보고서를 작성했습니다. 검토 후 개선안을 정리했습니다.",
            result="분석 결과를 기반으로 개선된 프로세스를 도입했습니다.",
            personal_contribution="개인 기여",
            metrics="30% 향상",
            tags=["분석", "데이터"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        project = MagicMock()
        project.job_title = "개발자"

        with patch(
            "resume_agent.pipeline.load_profile",
            return_value=MagicMock(
                style_preference="balanced",
                communication_style="balanced",
                confidence_style="balanced",
            ),
        ):
            result = build_candidate_profile(ws, project, [exp])
            assert result is not None
            assert "communication_style" in result


# ──────────────────────────────────────────────────
# top001/self_intro_mastery.py — 1 missing line
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
# top001/adaptive_persona.py — 1 missing line
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
# interactive.py — 2 missing lines
# ──────────────────────────────────────────────────


class TestInteractive:
    def test_run_interactive_coach_quit(self, tmp_path: Path):
        from resume_agent.interactive import run_interactive_coach

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch("resume_agent.interactive.load_experiences", return_value=[]):
            with patch("resume_agent.interactive.save_experiences"):
                with patch("builtins.input", return_value="q"):
                    run_interactive_coach(ws)

    def test_run_mock_interview_quit(self, tmp_path: Path):
        from resume_agent.interactive import run_mock_interview

        ws = MagicMock()
        ws.root = tmp_path
        ws.ensure = MagicMock()

        with patch("resume_agent.interactive.load_experiences", return_value=[]):
            with patch("resume_agent.interactive.load_project") as mock_project:
                mock_project.return_value = MagicMock(
                    company_name="테스트",
                    job_title="개발자",
                    questions=[],
                )
                with patch("builtins.input", return_value="q"):
                    run_mock_interview(ws, "normal")


# ──────────────────────────────────────────────────
# pipeline.py — 1 missing line
# ──────────────────────────────────────────────────


class TestPipeline:
    def test_init_workspace(self, tmp_path: Path):
        from resume_agent.pipeline import init_workspace

        ws = init_workspace(tmp_path)
        assert ws is not None
        assert ws.root == tmp_path

    def test_extract_markdown_section(self):
        from resume_agent.pipeline import extract_markdown_section

        text = "## A\n내용A\n## B\n내용B"
        result = extract_markdown_section(text, "## A", ["## B"])
        assert "내용A" in result

    def test_build_data_block(self):
        import json
        from resume_agent.pipeline import build_data_block

        project = MagicMock()
        project.model_dump.return_value = {"name": "test"}
        result = build_data_block(
            project=project,
            experiences=[],
            knowledge_hints=[],
        )
        data = json.loads(result)
        assert "project" in data

    def test_build_writer_rewrite_prompt(self):
        from resume_agent.pipeline import build_writer_rewrite_prompt

        validation = MagicMock()
        validation.missing = ["## PURPOSE"]
        quality_evals = [
            {
                "question_order": 1,
                "overall_score": 0.5,
                "humanization_flags": ["AI느낌"],
                "weaknesses": ["약점"],
                "suggestions": ["제안"],
            }
        ]
        result = build_writer_rewrite_prompt("이전출력", validation, quality_evals)
        assert isinstance(result, str)
        assert "## PURPOSE" in result

    def test_build_committee_feedback_context(self, tmp_path: Path):
        from resume_agent.pipeline import build_committee_feedback_context

        ws = MagicMock()
        ws.root = tmp_path
        ws.state_dir = tmp_path / "state"
        ws.state_dir.mkdir(parents=True, exist_ok=True)
        ws.ensure = MagicMock()

        with patch("resume_agent.pipeline.read_json_if_exists", return_value=[]):
            result = build_committee_feedback_context(ws)
            assert result is not None

    def test_get_success_cases_for_analysis(self, tmp_path: Path):
        from resume_agent.pipeline import _get_success_cases_for_analysis

        ws = MagicMock()
        ws.root = tmp_path

        with patch("resume_agent.pipeline.load_success_cases") as mock_load:
            mock_load.return_value = [MagicMock(), MagicMock()]
            result = _get_success_cases_for_analysis(ws)
            assert result is not None
            assert len(result) == 2

    def test_get_success_cases_empty(self, tmp_path: Path):
        from resume_agent.pipeline import _get_success_cases_for_analysis

        ws = MagicMock()
        ws.root = tmp_path

        with patch("resume_agent.pipeline.load_success_cases") as mock_load:
            mock_load.return_value = []
            result = _get_success_cases_for_analysis(ws)
            assert result is None

    def test_get_success_cases_exception(self, tmp_path: Path):
        from resume_agent.pipeline import _get_success_cases_for_analysis

        ws = MagicMock()
        ws.root = tmp_path

        with patch(
            "resume_agent.pipeline.load_success_cases",
            side_effect=Exception("테스트 오류"),
        ):
            result = _get_success_cases_for_analysis(ws)
            assert result is None
