"""parsing.py 커버리지 — 누락 라인 41, 43, 60-61, 77-83, 97-102, 108-120, 215-287, 293, 297, 300-310, 346-375"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestCleanSourceText:
    def test_removes_marketing_patterns(self):
        from resume_agent.parsing import clean_source_text

        text = "일반 텍스트\n👉 중요 포인트\n마케팅 문구 - 지원하세요!"
        result = clean_source_text(text)
        assert "👉" not in result

    def test_removes_emoji_lines(self):
        from resume_agent.parsing import clean_source_text

        text = "일반 텍스트\n👉 이 줄은 제거됨\n정상 텍스트"
        result = clean_source_text(text)
        assert "제거됨" not in result

    def test_removes_extra_newlines(self):
        from resume_agent.parsing import clean_source_text

        text = "텍스트1\n\n\n\n텍스트2"
        result = clean_source_text(text)
        assert "\n\n\n" not in result

    def test_removes_linkareer_promo_and_standalone_link(self):
        from resume_agent.parsing import clean_source_text

        text = (
            "본문 시작\n"
            "🔥신용보증기금 합격 자소서 함께 확인하세요!\n"
            "https://linkareer.com/cover-letter/35152\n"
            "본문 끝"
        )
        result = clean_source_text(text)
        assert "함께 확인하세요" not in result
        assert "linkareer.com/cover-letter/35152" not in result
        assert "본문 시작" in result
        assert "본문 끝" in result


class TestParseTitleMeta:
    def test_basic_parsing(self):
        from resume_agent.parsing import parse_title_meta

        result = parse_title_meta("회사명/직무명/계절")
        assert result["company_name"] == "회사명"
        assert result["job_title"] == "직무명"
        assert result["season"] == "계절"

    def test_partial_parsing(self):
        from resume_agent.parsing import parse_title_meta

        result = parse_title_meta("회사명")
        assert result["company_name"] == "회사명"
        assert result["job_title"] == ""
        assert result["season"] == ""


class TestExtractQuestionLines:
    def test_basic_extraction(self):
        from resume_agent.parsing import extract_question_lines

        text = "1. 첫 번째 질문\n2. 두 번째 질문\n3. 세 번째 질문"
        result = extract_question_lines(text)
        assert len(result) == 3
        assert result[0] == "첫 번째 질문"

    def test_no_questions(self):
        from resume_agent.parsing import extract_question_lines

        result = extract_question_lines("질문 없음")
        assert result == []


class TestSummarizeStructure:
    def test_with_labels(self):
        from resume_agent.parsing import summarize_structure

        result = summarize_structure("회사", "직무", ["TYPE_A", "TYPE_B"], 5)
        assert "회사" in result
        assert "직무" in result

    def test_without_labels(self):
        from resume_agent.parsing import summarize_structure

        result = summarize_structure("회사", "직무", [], 5)
        assert "회사" in result
        assert "직무" in result


class TestExtractSpecKeywords:
    def test_basic_extraction(self):
        from resume_agent.parsing import extract_spec_keywords

        result = extract_spec_keywords("Python 개발자 모집 Django 경험 필수")
        assert len(result) <= 10
        assert "Python" in result

    def test_empty_text(self):
        from resume_agent.parsing import extract_spec_keywords

        result = extract_spec_keywords("")
        assert result == []


class TestDetectPatterns:
    def test_detect_public_patterns(self):
        from resume_agent.parsing import detect_patterns
        from resume_agent.models import SuccessPattern

        text = "공공기관 채용 서류전형 합격 NCS 기반 평가"
        result = detect_patterns(text)
        assert isinstance(result, list)

    def test_no_patterns(self):
        from resume_agent.parsing import detect_patterns

        text = "일반 텍스트"
        result = detect_patterns(text)
        assert isinstance(result, list)


class TestBuildRetrievalTerms:
    def test_basic_terms(self):
        from resume_agent.parsing import build_retrieval_terms

        meta = {"company_name": "회사", "job_title": "직무", "season": "2024"}
        result = build_retrieval_terms(meta, "Python 개발", ["질문1", "질문2"])
        assert isinstance(result, list)
        assert "회사" in result

    def test_deduplication(self):
        from resume_agent.parsing import build_retrieval_terms

        meta = {"company_name": "회사", "job_title": "회사", "season": ""}
        result = build_retrieval_terms(meta, "", [])
        # 중복 제거 확인
        assert result.count("회사") <= 1


class TestSummarizeKnowledgeSources:
    def test_basic_summary(self):
        from resume_agent.parsing import summarize_knowledge_sources

        source = MagicMock()
        source.source_type = MagicMock()
        source.source_type.value = "job_posting"
        source.pattern = MagicMock()
        source.pattern.company_name = "테스트회사"

        result = summarize_knowledge_sources([source])
        assert isinstance(result, dict)

    def test_empty_sources(self):
        from resume_agent.parsing import summarize_knowledge_sources

        result = summarize_knowledge_sources([])
        assert isinstance(result, dict)


class TestCalculateSourcesHash:
    def test_basic_hash(self):
        from resume_agent.parsing import calculate_sources_hash

        sources = [MagicMock(id="s1"), MagicMock(id="s2")]
        result = calculate_sources_hash(sources)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_sources(self):
        from resume_agent.parsing import calculate_sources_hash

        result = calculate_sources_hash([])
        assert isinstance(result, str)


class TestExtractTextFromPdf:
    def test_basic_extraction(self):
        from resume_agent.pdf_utils import extract_text_from_pdf
        from pathlib import Path
        from unittest.mock import patch

        with patch("resume_agent.pdf_utils.PdfReader", side_effect=FileNotFoundError):
            result = extract_text_from_pdf(Path("/nonexistent/file.pdf"))
            assert result == ""


class TestExtractJdKeywords:
    def test_basic_extraction(self):
        from resume_agent.pdf_utils import extract_jd_keywords

        result = extract_jd_keywords("Python 개발자 모집")
        assert isinstance(result, list)

    def test_empty_text(self):
        from resume_agent.pdf_utils import extract_jd_keywords

        result = extract_jd_keywords("")
        assert result == []


class TestAnalyzeJdStructure:
    def test_basic_analysis(self):
        from resume_agent.pdf_utils import analyze_jd_structure

        result = analyze_jd_structure("자격요건: Python 3년 경험\n우대사항: AWS 경험")
        assert isinstance(result, dict)

    def test_empty_text(self):
        from resume_agent.pdf_utils import analyze_jd_structure

        result = analyze_jd_structure("")
        assert isinstance(result, dict)


class TestGenerateQuestionsFromJd:
    def test_basic_generation(self):
        from resume_agent.pdf_utils import generate_questions_from_jd

        jd = {
            "required_qualifications": ["Python 3년"],
            "preferred_qualifications": ["AWS"],
            "responsibilities": ["API 개발"],
        }
        result = generate_questions_from_jd(jd)
        assert isinstance(result, list)

    def test_empty_jd(self):
        from resume_agent.pdf_utils import generate_questions_from_jd

        result = generate_questions_from_jd({})
        assert isinstance(result, list)
