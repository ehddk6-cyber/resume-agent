"""miner.py 커버리지 — 누락 라인 51-58, 77, 108, 110, 114-143"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMinePastResume:
    def test_docx_file_with_python_docx(self, tmp_path: Path):
        """DOCX 파일 처리 (python-docx 사용)"""
        from resume_agent.miner import mine_past_resume

        docx_file = tmp_path / "resume.docx"
        docx_file.write_bytes(b"PK dummy")

        with patch.dict("sys.modules", {"docx": MagicMock()}):
            import sys

            sys.modules["docx"].Document = MagicMock(
                return_value=MagicMock(
                    paragraphs=[MagicMock(text="테스트 이력서 내용")]
                )
            )

            with patch(
                "resume_agent.miner.split_text", return_value=["테스트 이력서 내용"]
            ):
                with patch("resume_agent.miner.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(
                        stdout='[assistant] ```json\n[{"title": "테스트 경험", "organization": "테스트 조직", "situation": "상황", "task": "과제", "action": "행동", "result": "결과 30% 향상", "personal_contribution": "기여", "metrics": "30%", "tags": ["테스트"]}]\n```',
                        stderr="",
                        returncode=0,
                    )
                    result = mine_past_resume(docx_file, tmp_path)
                    assert len(result) == 1
                    assert result[0].title == "테스트 경험"

    def test_docx_file_without_python_docx(self, tmp_path: Path):
        """DOCX 파일 처리 (python-docx 없음)"""
        from resume_agent.miner import mine_past_resume

        docx_file = tmp_path / "resume.docx"
        docx_file.write_bytes(b"PK dummy")

        with patch.dict("sys.modules", {"docx": None}):
            result = mine_past_resume(docx_file, tmp_path)
            assert result == []

    def test_txt_file_with_json_markdown_block(self, tmp_path: Path):
        """TXT 파일 처리 (```json 블록 포함)"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["이력서 내용"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] ```json\n[{"title": "테스트 경험", "organization": "테스트 조직", "situation": "상황", "task": "과제", "action": "행동", "result": "결과 30% 향상", "personal_contribution": "기여", "metrics": "30%", "tags": ["테스트"]}]\n```',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                assert len(result) == 1

    def test_txt_file_with_plain_markdown_block(self, tmp_path: Path):
        """TXT 파일 처리 (``` 블록 포함, json 없음)"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["이력서 내용"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] ```\n[{"title": "테스트 경험", "organization": "테스트 조직", "situation": "상황", "task": "과제", "action": "행동", "result": "결과 30% 향상", "personal_contribution": "기여", "metrics": "30%", "tags": ["테스트"]}]\n```',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                assert len(result) == 1

    def test_txt_file_with_multiple_chunks(self, tmp_path: Path):
        """TXT 파일 처리 (여러 청크)"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["청크1", "청크2"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] [{"title": "경험1", "organization": "조직1", "situation": "상황", "task": "과제", "action": "행동", "result": "결과", "personal_contribution": "기여", "metrics": "", "tags": []}]',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                # 두 청크 모두 처리
                assert mock_run.call_count == 2

    def test_txt_file_with_json_decode_error(self, tmp_path: Path):
        """TXT 파일 처리 (JSON 파싱 오류)"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["이력서 내용"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout="[assistant] 유효하지 않은 JSON",
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                assert result == []

    def test_txt_file_with_non_list_json(self, tmp_path: Path):
        """TXT 파일 처리 (JSON이 리스트가 아님)"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["이력서 내용"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] {"title": "테스트"}',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                assert result == []

    def test_txt_file_with_empty_title(self, tmp_path: Path):
        """TXT 파일 처리 (빈 제목)"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["이력서 내용"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] [{"title": "", "organization": "테스트 조직", "situation": "상황", "task": "과제", "action": "행동", "result": "결과", "personal_contribution": "기여", "metrics": "", "tags": []}]',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                assert result == []

    def test_txt_file_with_duplicate_title(self, tmp_path: Path):
        """TXT 파일 처리 (중복 제목)"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch(
            "resume_agent.miner.split_text",
            return_value=["이력서 내용", "이력서 내용2"],
        ):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] ```json\n[{"title": "테스트 경험", "organization": "조직1", "situation": "상황", "task": "과제", "action": "행동", "result": "결과", "personal_contribution": "기여", "metrics": "", "tags": []}]\n```',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                # 중복 제목은 하나만 포함
                assert len(result) == 1

    def test_txt_file_with_metrics_evidence_level_upgrade(self, tmp_path: Path):
        """TXT 파일 처리 (수치 기반 증거수준 L3 상향)"""
        from resume_agent.miner import mine_past_resume
        from resume_agent.models import EvidenceLevel

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["이력서 내용"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] ```json\n[{"title": "테스트 경험", "organization": "테스트 조직", "situation": "상황", "task": "과제", "action": "행동", "result": "결과 30% 향상", "personal_contribution": "기여", "metrics": "30%", "tags": ["테스트"]}]\n```',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                assert len(result) == 1
                assert result[0].evidence_level == EvidenceLevel.L3

    def test_txt_file_with_result_metrics_evidence_level_upgrade(self, tmp_path: Path):
        """TXT 파일 처리 (결과에 수치 포함 시 증거수준 L3 상향)"""
        from resume_agent.miner import mine_past_resume
        from resume_agent.models import EvidenceLevel

        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("이력서 내용", encoding="utf-8")

        with patch("resume_agent.miner.split_text", return_value=["이력서 내용"]):
            with patch("resume_agent.miner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='[assistant] ```json\n[{"title": "테스트 경험", "organization": "테스트 조직", "situation": "상황", "task": "과제", "action": "행동", "result": "결과 50건 처리", "personal_contribution": "기여", "metrics": "", "tags": ["테스트"]}]\n```',
                    stderr="",
                    returncode=0,
                )
                result = mine_past_resume(txt_file, tmp_path)
                assert len(result) == 1
                assert result[0].evidence_level == EvidenceLevel.L3

    def test_unsupported_format(self, tmp_path: Path):
        """지원하지 않는 파일 형식"""
        from resume_agent.miner import mine_past_resume

        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        result = mine_past_resume(pdf_file, tmp_path)
        assert result == []

    def test_empty_text(self, tmp_path: Path):
        """빈 텍스트"""
        from resume_agent.miner import mine_past_resume

        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("   \n\n   ", encoding="utf-8")

        result = mine_past_resume(txt_file, tmp_path)
        assert result == []
