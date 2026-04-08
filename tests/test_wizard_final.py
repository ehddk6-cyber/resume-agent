"""wizard.py run_wizard 함수 테스트 — 전체 흐름"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRunWizard:
    """run_wizard 함수 테스트"""

    def test_wizard_minimal_flow(self, tmp_path: Path):
        """최소 위자드 실행"""
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
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = []
                                                mock_vault.return_value.verify_experiences.return_value = 0
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                # Confirm: global vault(n), manual import(n), jd analysis(n), save(y), continue(y)
                                                mock_confirm.ask.side_effect = [
                                                    False,
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                ]
                                                # Prompt: 회사명, 직무명, 기업유형, 질문1, 글자수1, 질문2(빈문자열=종료)
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(tmp_path)

                                                assert result is not None
                                                assert "project" in result

    def test_wizard_with_global_experiences(self, tmp_path: Path):
        """Global Vault 경험"""
        from resume_agent.wizard import run_wizard
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
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
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = [
                                                    exp
                                                ]
                                                mock_vault.return_value.verify_experiences.return_value = 1
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                # Confirm: global vault(y), manual import(n), jd analysis(n), save(y), continue(y)
                                                mock_confirm.ask.side_effect = [
                                                    True,
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                ]
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(tmp_path)

                                                assert result is not None
                                                mock_vault.return_value.verify_experiences.assert_called()

    def test_wizard_with_import_path_exists(self, tmp_path: Path):
        """import_path로 경험"""
        from resume_agent.wizard import run_wizard

        import_file = tmp_path / "experiences.json"
        import_file.write_text("[]", encoding="utf-8")

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
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = []
                                                mock_vault.return_value.verify_experiences.return_value = 0
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                mock_confirm.ask.side_effect = [
                                                    False,
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                ]
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(
                                                    tmp_path, import_path=import_file
                                                )

                                                assert result is not None

    def test_wizard_with_import_path_not_exists(self, tmp_path: Path):
        """import_path 파일 없음"""
        from resume_agent.wizard import run_wizard

        import_file = tmp_path / "nonexistent.json"

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
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = []
                                                mock_vault.return_value.verify_experiences.return_value = 0
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                mock_confirm.ask.side_effect = [
                                                    False,
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                ]
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(
                                                    tmp_path, import_path=import_file
                                                )

                                                assert result is not None

    def test_wizard_with_jd_analysis(self, tmp_path: Path):
        """JD 분석"""
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

    def test_wizard_with_jd_path_not_exists(self, tmp_path: Path):
        """jd_path 파일 없음"""
        from resume_agent.wizard import run_wizard

        jd_file = tmp_path / "nonexistent.pdf"

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
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = []
                                                mock_vault.return_value.verify_experiences.return_value = 0
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                mock_confirm.ask.side_effect = [
                                                    False,
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                ]
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(
                                                    tmp_path, jd_path=jd_file
                                                )

                                                assert result is not None

    def test_wizard_with_manual_import(self, tmp_path: Path):
        """수동 경험 가져오기"""
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
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
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

                                                result = run_wizard(tmp_path)

                                                assert result is not None

    def test_wizard_with_verified_experiences(self, tmp_path: Path):
        """검증된 경험들"""
        from resume_agent.wizard import run_wizard
        from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

        exp = Experience(
            id="e1",
            title="테스트 경험",
            organization="테스트 조직",
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
                                                "resume_agent.wizard.import_experiences_from_file",
                                                return_value=[],
                                            ):
                                                mock_vault.return_value.load_global_experiences.return_value = [
                                                    exp
                                                ]
                                                mock_vault.return_value.verify_experiences.return_value = 1
                                                mock_vault.return_value.sync_to_global = MagicMock()

                                                mock_confirm.ask.side_effect = [
                                                    True,
                                                    False,
                                                    False,
                                                    True,
                                                    True,
                                                ]
                                                mock_prompt.ask.side_effect = [
                                                    "테스트회사",
                                                    "개발자",
                                                    "대기업",
                                                    "",
                                                    "",
                                                ]
                                                mock_int_prompt.ask.return_value = 1000

                                                result = run_wizard(tmp_path)

                                                assert result is not None
                                                assert (
                                                    mock_vault.return_value.verify_experiences.call_count
                                                    == 1
                                                )
