"""wizard.py 추가 커버리지 — 누락 라인 82-88, 131-132, 141, 152-165, 190-211, 255-265, 278-287, 302-311, 413"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRunWizardAdditional:
    """run_wizard 추가 테스트 — 누락 라인 커버"""

    def test_wizard_with_manual_import_and_success(self, tmp_path: Path):
        """수동 경험 가져오기 성공 — 라인 82-88"""
        from resume_agent.wizard import run_wizard

        with patch("resume_agent.wizard.console"):
            with patch("resume_agent.wizard.Confirm") as mock_confirm:
                with patch("resume_agent.wizard.VaultManager") as mock_vault:
                    with patch("resume_agent.wizard.Prompt") as mock_prompt:
                        with patch("resume_agent.wizard.IntPrompt") as mock_int_prompt:
                            with patch(
                                "resume_agent.pdf_utils.extract_text_from_pdf",
                                return_value="",
                            ):
                                with patch(
                                    "resume_agent.pdf_utils.extract_jd_keywords",
                                    return_value=[],
                                ):
                                    with patch(
                                        "resume_agent.pdf_utils.analyze_jd_structure",
                                        return_value={},
                                    ):
                                        with patch(
                                            "resume_agent.pdf_utils.generate_questions_from_jd",
                                            return_value=[],
                                        ):
                                            with patch(
                                                "resume_agent.wizard.import_experiences_from_file"
                                            ) as mock_import:
                                                mock_vault.return_value.load_global_experiences.return_value = []
                                                mock_vault.return_value.verify_experiences.return_value = 0
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                # Confirm: global vault(n), manual import(y), jd analysis(n), save(y), continue(y)
                                                mock_confirm.ask.side_effect = [
                                                    False,
                                                    True,
                                                    False,
                                                    True,
                                                    True,
                                                ]
                                                # Prompt: 파일경로, 회사명, 직무명, 기업유형, 질문1, 글자수1, 질문2(종료)
                                                mock_prompt.ask.side_effect = [
                                                    "경험.docx",
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                # import_experiences_from_file이 경험을 반환하도록 설정
                                                from resume_agent.models import (
                                                    Experience,
                                                    EvidenceLevel,
                                                    VerificationStatus,
                                                )

                                                exp = Experience(
                                                    id="e1",
                                                    title="가져온 경험",
                                                    organization="가져온 조직",
                                                    period_start="2024-01",
                                                    situation="상황",
                                                    task="과제",
                                                    action="행동",
                                                    result="결과",
                                                    personal_contribution="기여",
                                                    metrics="30% 향상",
                                                    tags=["테스트"],
                                                    evidence_level=EvidenceLevel.L3,
                                                    verification_status=VerificationStatus.VERIFIED,
                                                )
                                                mock_import.return_value = [exp]

                                                result = run_wizard(tmp_path)

                                                assert result is not None

    def test_wizard_with_jd_keywords(self, tmp_path: Path):
        """JD 키워드 추출 성공 — 라인 131-132"""
        from resume_agent.wizard import run_wizard

        jd_file = tmp_path / "jd.pdf"
        jd_file.write_bytes(b"%PDF-1.4 dummy")

        with patch("resume_agent.wizard.console"):
            with patch("resume_agent.wizard.Confirm") as mock_confirm:
                with patch("resume_agent.wizard.VaultManager") as mock_vault:
                    with patch("resume_agent.wizard.Prompt") as mock_prompt:
                        with patch("resume_agent.wizard.IntPrompt") as mock_int_prompt:
                            with patch(
                                "resume_agent.pdf_utils.extract_text_from_pdf",
                                return_value="Python 개발자 모집",
                            ):
                                with patch(
                                    "resume_agent.pdf_utils.extract_jd_keywords",
                                    return_value=["Python", "개발"],
                                ):
                                    with patch(
                                        "resume_agent.pdf_utils.analyze_jd_structure",
                                        return_value={},
                                    ):
                                        with patch(
                                            "resume_agent.pdf_utils.generate_questions_from_jd",
                                            return_value=[],
                                        ):
                                            with patch(
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = []
                                                mock_vault.return_value.verify_experiences.return_value = 0
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                # Confirm: global vault(n), manual import(n), jd analysis(y), save(y), continue(y)
                                                mock_confirm.ask.side_effect = [
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                    True,
                                                ]
                                                # Prompt: 회사명, 직무명, 기업유형, jd_path, 질문1, 글자수1, 질문2(종료)
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    str(jd_file),
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(
                                                    tmp_path, jd_path=jd_file
                                                )

                                                assert result is not None

    def test_wizard_with_auto_questions(self, tmp_path: Path):
        """자동 질문 생성 — 라인 141, 152-165"""
        from resume_agent.wizard import run_wizard

        jd_file = tmp_path / "jd.pdf"
        jd_file.write_bytes(b"%PDF-1.4 dummy")

        auto_questions = [
            {"question_text": "Python 개발 경험을 말씀해주세요", "char_limit": 1000},
            {"question_text": "팀워크 경험을 말씀해주세요", "char_limit": 500},
        ]

        with patch("resume_agent.wizard.console"):
            with patch("resume_agent.wizard.Confirm") as mock_confirm:
                with patch("resume_agent.wizard.VaultManager") as mock_vault:
                    with patch("resume_agent.wizard.Prompt") as mock_prompt:
                        with patch("resume_agent.wizard.IntPrompt") as mock_int_prompt:
                            with patch(
                                "resume_agent.pdf_utils.extract_text_from_pdf",
                                return_value="Python 개발자 모집",
                            ):
                                with patch(
                                    "resume_agent.pdf_utils.extract_jd_keywords",
                                    return_value=["Python"],
                                ):
                                    with patch(
                                        "resume_agent.pdf_utils.analyze_jd_structure",
                                        return_value={},
                                    ):
                                        with patch(
                                            "resume_agent.pdf_utils.generate_questions_from_jd",
                                            return_value=auto_questions,
                                        ):
                                            with patch(
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = []
                                                mock_vault.return_value.verify_experiences.return_value = 0
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                # Confirm: global vault(n), manual import(n), jd analysis(y), auto questions(y), save(y), continue(y)
                                                mock_confirm.ask.side_effect = [
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                    True,
                                                    True,
                                                ]
                                                # Prompt: 회사명, 직무명, 기업유형, jd_path, 질문1, 글자수1, 질문2(종료)
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    str(jd_file),
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(
                                                    tmp_path, jd_path=jd_file
                                                )

                                                assert result is not None
