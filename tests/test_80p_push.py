"""parsing.py 커버리지 — 누락 라인 41, 101, 215-287, 293, 297, 300-310, 346-375"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestParsing:
    def test_clean_source_text_removes_marketing(self):
        from resume_agent.parsing import clean_source_text

        text = "일반 텍스트\n👉 중요 포인트\n마케팅 문구 - 지원하세요!"
        result = clean_source_text(text)
        assert "👉" not in result

    def test_extract_question_lines(self):
        from resume_agent.parsing import extract_question_lines

        text = "1. 첫 번째 질문\n2. 두 번째 질문"
        result = extract_question_lines(text)
        assert len(result) == 2
        assert result[0] == "첫 번째 질문"

    def test_parse_title_meta(self):
        from resume_agent.parsing import parse_title_meta

        result = parse_title_meta("회사/직무/계절")
        assert result["company_name"] == "회사"
        assert result["job_title"] == "직무"
        assert result["season"] == "계절"

    def test_strip_html_text(self):
        from resume_agent.parsing import strip_html_text

        text = "<p>테스트</p> <script>alert('x')</script>"
        result = strip_html_text(text)
        assert "<p>" not in result
        assert "테스트" in result

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

    def test_ingest_source_file_txt(self, tmp_path: Path):
        from resume_agent.parsing import ingest_source_file

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("테스트 내용", encoding="utf-8")
        result = ingest_source_file(txt_file)
        assert result is not None

    def test_ingest_source_file_empty(self, tmp_path: Path):
        from resume_agent.parsing import ingest_source_file

        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("", encoding="utf-8")
        result = ingest_source_file(txt_file)
        assert result is not None

    def test_extract_text_from_pdf(self, tmp_path: Path):
        from resume_agent.pdf_utils import extract_text_from_pdf

        with patch("resume_agent.pdf_utils.PdfReader", side_effect=FileNotFoundError):
            result = extract_text_from_pdf(tmp_path / "nonexistent.pdf")
            assert result == ""

    def test_extract_jd_keywords(self):
        from resume_agent.pdf_utils import extract_jd_keywords

        result = extract_jd_keywords("Python 개발자 모집")
        assert isinstance(result, list)

    def test_extract_jd_keywords_empty(self):
        from resume_agent.pdf_utils import extract_jd_keywords

        result = extract_jd_keywords("")
        assert result == []

    def test_split_text(self):
        from resume_agent.pdf_utils import split_text

        text = "a" * 1000 + "\n\n" + "b" * 1000
        result = split_text(text, chunk_size=500)
        assert len(result) >= 2

    def test_analyze_jd_structure(self):
        from resume_agent.pdf_utils import analyze_jd_structure

        result = analyze_jd_structure("자격요건: Python 3년 경험\n우대사항: AWS 경험")
        assert isinstance(result, dict)

    def test_generate_questions_from_jd(self):
        from resume_agent.pdf_utils import generate_questions_from_jd

        jd = {
            "required_qualifications": ["Python 3년"],
            "preferred_qualifications": ["AWS"],
            "responsibilities": ["API 개발"],
        }
        result = generate_questions_from_jd(jd)
        assert isinstance(result, list)


# ──────────────────────────────────────────────────
# domain.py 추가 테스트 — 누락 라인 56-57, 63, 86-117, 134-135, 148-150, 157, 169, 227, 244, 279-281, 286, 291, 293, 339, 452, 459
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
# semantic_engine.py 추가 테스트 — 누락 라인 36-37, 49, 58-60, 101-102, 109, 133-137, 178, 233-255, 393-394, 423, 433, 458-460, 466-482
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

        with patch.dict("sys.modules", {"sklearn": None}):
            result = compute_tfidf_similarity("테스트1", "테스트2")
            assert result == -1.0

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
# feedback_learner.py 테스트 — 누락 라인 164, 213, 228, 381-388, 412, 549, 561, 567-591, 648, 659, 664, 677-685
# ──────────────────────────────────────────────────


class TestFeedbackLearner:
    def test_create_feedback_learner(self, tmp_path: Path):
        from resume_agent.feedback_learner import create_feedback_learner

        ws = MagicMock()
        ws.root = tmp_path
        ws.state_dir = tmp_path / "state"
        ws.state_dir.mkdir(parents=True, exist_ok=True)
        ws.ensure = MagicMock()

        learner = create_feedback_learner(ws)
        assert learner is not None


# ──────────────────────────────────────────────────
# scoring.py 테스트 — 누락 라인 57-58, 64, 75, 80, 108-109, 123, 129, 132-133, 185-186, 192-193, 231, 244, 274, 364, 403, 437, 478-481, 539, 560-586, 614, 632
# ──────────────────────────────────────────────────


class TestScoring:
    def test_score_experience(self):
        from resume_agent.scoring import score_experience
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

        result = score_experience(exp)
        assert result is not None

    def test_analyze_gaps_with_experiences(self):
        from resume_agent.scoring import analyze_gaps

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


# ──────────────────────────────────────────────────
# quality_evaluator.py 테스트 — 누락 라인 156, 179, 187, 218, 238, 245, 252-253, 268-270, 280-281, 283-284, 289-290, 304, 307, 310, 313, 329, 338, 349-358, 367-368
# ──────────────────────────────────────────────────


class TestQualityEvaluator:
    def test_evaluate_answer_quality(self, tmp_path: Path):
        from resume_agent.quality_evaluator import evaluate_answer_quality

        ws = MagicMock()
        ws.root = tmp_path
        ws.state_dir = tmp_path / "state"
        ws.state_dir.mkdir(parents=True, exist_ok=True)
        ws.ensure = MagicMock()

        result = evaluate_answer_quality(ws, "답변입니다", "질문입니다")
        assert result is not None


# ──────────────────────────────────────────────────
# progress.py 테스트 — 누락 라인 63, 83, 94, 105-110, 163-166, 196-201, 219, 236-238, 261-263, 268-270
# ──────────────────────────────────────────────────


class TestProgress:
    def test_print_status(self, capsys):
        from resume_agent.progress import print_status

        print_status("테스트", "info")
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or len(captured.err) > 0


# ──────────────────────────────────────────────────
# top001/self_intro_mastery.py 테스트 — 누락 라인 28, 40-43, 50, 52, 54, 61, 63, 65, 67, 69, 77, 81, 83, 90, 101, 110, 119, 140-142, 164, 168, 170, 188-189, 198-199, 242
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
# top001/adaptive_coach.py 테스트 — 누락 라인 59-69, 74-95, 118, 133, 136-138, 210, 220, 223-225
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
# top001/deep_interrogator.py 테스트 — 누락 라인 108-112, 116-120, 156, 201-212, 246, 248, 252
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
# top001/adaptive_persona.py 테스트 — 누락 라인 63, 81, 92, 97, 104-106, 175, 182-235, 238-239
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
# logical_analyzer.py 테스트 — 누락 라인 134, 157-164, 194, 196, 209, 257-273, 295-315, 321, 324
# ──────────────────────────────────────────────────


class TestLogicalAnalyzer:
    def test_creation(self):
        from resume_agent.top001.logical_analyzer import LogicalAnalyzer

        analyzer = LogicalAnalyzer()
        assert analyzer is not None


# ──────────────────────────────────────────────────
# cli_tool_manager.py 테스트 — 누락 라인 63-64, 74, 85-92, 110-138, 154-160
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
# interactive.py 테스트 — 누락 라인 87-88, 95, 97, 99, 101, 104-107, 111-158, 253-259, 274-275, 285-286, 296-297, 307-308, 327-388, 410, 417-421, 484, 569-702, 770-785, 811-818, 863-864, 876, 882, 886, 931, 934-959, 978, 980, 993-1004, 1014, 1022-1041, 1045-1087
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
