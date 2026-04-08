"""wizard.py 추가 커버리지 — import_experiences_from_file, parse_experience_docx, parse_experience_json"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestImportExperiencesFromFile:
    """import_experiences_from_file 테스트 — 라인 255-265"""

    def test_import_docx(self, tmp_path: Path):
        """DOCX 파일 가져오기"""
        from resume_agent.wizard import import_experiences_from_file

        docx_file = tmp_path / "experience.docx"
        docx_file.write_bytes(b"PK dummy")

        with patch.dict("sys.modules", {"docx": MagicMock()}):
            import sys

            sys.modules["docx"].Document = MagicMock(
                return_value=MagicMock(paragraphs=[MagicMock(text="테스트 이력서")])
            )
            result = import_experiences_from_file(docx_file)
            assert isinstance(result, list)

    def test_import_txt(self, tmp_path: Path):
        """TXT 파일 가져오기"""
        from resume_agent.wizard import import_experiences_from_file

        txt_file = tmp_path / "experience.txt"
        txt_file.write_text(
            """1. 테스트 경험: 경험 설명
상황(Situation): 상황
과제(Task): 과제
행동(Action): 행동
결과(Result): 결과
""",
            encoding="utf-8",
        )

        result = import_experiences_from_file(txt_file)
        assert isinstance(result, list)

    def test_import_json(self, tmp_path: Path):
        """JSON 파일 가져오기"""
        from resume_agent.wizard import import_experiences_from_file
        import json

        json_file = tmp_path / "experience.json"
        data = [
            {
                "id": "e1",
                "title": "테스트 경험",
                "organization": "테스트 조직",
                "period_start": "2024-01",
                "situation": "상황",
                "task": "과제",
                "action": "행동",
                "result": "결과",
                "personal_contribution": "기여",
                "metrics": "30% 향상",
                "tags": ["테스트"],
                "evidence_level": "L3",
                "verification_status": "verified",
            }
        ]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = import_experiences_from_file(json_file)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_import_unsupported_format(self, tmp_path: Path):
        """지원하지 않는 파일 형식"""
        from resume_agent.wizard import import_experiences_from_file

        pdf_file = tmp_path / "experience.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with patch("resume_agent.wizard.console"):
            result = import_experiences_from_file(pdf_file)
            assert result == []


class TestParseExperienceDocx:
    """parse_experience_docx 테스트 — 라인 278-287"""

    def test_parse_docx_success(self, tmp_path: Path):
        """DOCX 파싱 성공"""
        from resume_agent.wizard import parse_experience_docx

        docx_file = tmp_path / "experience.docx"
        docx_file.write_bytes(b"PK dummy")

        with patch.dict("sys.modules", {"docx": MagicMock()}):
            import sys

            sys.modules["docx"].Document = MagicMock(
                return_value=MagicMock(paragraphs=[MagicMock(text="테스트 이력서")])
            )
            result = parse_experience_docx(docx_file)
            assert isinstance(result, list)

    def test_parse_docx_no_python_docx(self, tmp_path: Path):
        """python-docx 없음"""
        from resume_agent.wizard import parse_experience_docx

        docx_file = tmp_path / "experience.docx"
        docx_file.write_bytes(b"PK dummy")

        with patch.dict("sys.modules", {"docx": None}):
            with patch("resume_agent.wizard.console"):
                result = parse_experience_docx(docx_file)
                assert result == []


class TestParseExperienceJson:
    """parse_experience_json 테스트 — 라인 302-311"""

    def test_parse_json_success(self, tmp_path: Path):
        """JSON 파싱 성공"""
        from resume_agent.wizard import parse_experience_json
        import json

        json_file = tmp_path / "experience.json"
        data = [
            {
                "id": "e1",
                "title": "테스트 경험",
                "organization": "테스트 조직",
                "period_start": "2024-01",
                "situation": "상황",
                "task": "과제",
                "action": "행동",
                "result": "결과",
                "personal_contribution": "기여",
                "metrics": "30% 향상",
                "tags": ["테스트"],
                "evidence_level": "L3",
                "verification_status": "verified",
            }
        ]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = parse_experience_json(json_file)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_parse_json_empty(self, tmp_path: Path):
        """빈 JSON"""
        from resume_agent.wizard import parse_experience_json

        json_file = tmp_path / "empty.json"
        json_file.write_text("[]", encoding="utf-8")

        result = parse_experience_json(json_file)
        assert result == []

    def test_parse_json_invalid(self, tmp_path: Path):
        """잘못된 JSON"""
        from resume_agent.wizard import parse_experience_json

        json_file = tmp_path / "invalid.json"
        json_file.write_text("invalid json", encoding="utf-8")

        with pytest.raises(Exception):
            parse_experience_json(json_file)


class TestExtractOrganization:
    """_extract_organization 테스트 — 라인 413"""

    def test_extract_organization(self):
        from resume_agent.wizard import _extract_organization

        text = "삼성전자에서 개발자로 근무했습니다."
        result = _extract_organization(text)
        assert result is not None

    def test_extract_organization_none(self):
        from resume_agent.wizard import _extract_organization

        text = "단순한 텍스트입니다."
        result = _extract_organization(text)
        assert result == ""
