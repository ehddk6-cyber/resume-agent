from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def stub_sentence_transformers(monkeypatch):
    fake_module = types.ModuleType("sentence_transformers")

    class DummySentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

        def encode(self, *args, **kwargs):
            return [0.0]

    fake_module.SentenceTransformer = DummySentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)


def _build_experience():
    from resume_agent.models import EvidenceLevel, Experience, VerificationStatus

    return Experience(
        id="exp_1",
        title="협업 프로젝트",
        organization="테스트센터",
        period_start="2024-01",
        situation="상황",
        task="과제",
        action="행동",
        result="결과 30% 향상",
        personal_contribution="기여",
        metrics="30% 향상",
        tags=["협업", "성과"],
        evidence_level=EvidenceLevel.L3,
        verification_status=VerificationStatus.VERIFIED,
    )


def test_run_wizard_covers_manual_import_and_experience_selection(tmp_path: Path):
    from resume_agent.models import QuestionType
    from resume_agent.wizard import run_wizard

    imported_experience = _build_experience()

    with patch("resume_agent.wizard.console"):
        with patch("resume_agent.wizard.Confirm") as mock_confirm:
            with patch("resume_agent.wizard.Prompt") as mock_prompt:
                with patch("resume_agent.wizard.VaultManager") as mock_vault:
                    with patch(
                        "resume_agent.wizard.import_experiences_from_file",
                        return_value=[imported_experience],
                    ):
                        with patch(
                            "resume_agent.wizard.classify_question",
                            side_effect=[
                                QuestionType.TYPE_B,
                                QuestionType.TYPE_C,
                                QuestionType.TYPE_C,
                            ],
                        ):
                            with patch(
                                "resume_agent.wizard._recommend_experiences",
                                return_value=[imported_experience],
                            ):
                                mock_vault.return_value.load_global_experiences.return_value = []
                                mock_vault.return_value.verify_experiences.return_value = 1
                                mock_vault.return_value.sync_to_global = MagicMock()
                                mock_confirm.ask.side_effect = [True, False]
                                mock_prompt.ask.side_effect = [
                                    "manual.docx",
                                    "테스트회사",
                                    "개발자",
                                    "대기업",
                                    "협업 경험을 설명해주세요",
                                    "1000",
                                    "",
                                    "1",
                                ]

                                result = run_wizard(tmp_path)

    assert len(result["experiences"]) == 1
    assert result["project"].questions[0].char_limit == 1000


def test_run_wizard_covers_jd_keyword_and_auto_question_flow(tmp_path: Path):
    from resume_agent.models import QuestionType
    from resume_agent.wizard import run_wizard

    jd_file = tmp_path / "jd.pdf"
    jd_file.write_bytes(b"%PDF-1.4 dummy")
    auto_questions = [
        {"question_text": "지원 동기를 설명해주세요", "char_limit": 700},
        {"question_text": "협업 사례를 설명해주세요", "char_limit": 500},
    ]

    with patch("resume_agent.wizard.console"):
        with patch("resume_agent.wizard.Confirm") as mock_confirm:
            with patch("resume_agent.wizard.Prompt") as mock_prompt:
                with patch("resume_agent.wizard.VaultManager") as mock_vault:
                    with patch(
                        "resume_agent.wizard.extract_text_from_pdf",
                        return_value="지원동기 협업 데이터",
                    ):
                        with patch(
                            "resume_agent.wizard.extract_jd_keywords",
                            return_value=["지원동기", "협업"],
                        ):
                            with patch(
                                "resume_agent.pdf_utils.analyze_jd_structure",
                                return_value={"sections": ["dummy"]},
                            ):
                                with patch(
                                    "resume_agent.pdf_utils.generate_questions_from_jd",
                                    return_value=auto_questions,
                                ):
                                    with patch(
                                        "resume_agent.wizard.classify_question",
                                        side_effect=[
                                            QuestionType.TYPE_A,
                                            QuestionType.TYPE_C,
                                        ],
                                    ):
                                        mock_vault.return_value.load_global_experiences.return_value = []
                                        mock_vault.return_value.verify_experiences.return_value = 0
                                        mock_vault.return_value.sync_to_global = MagicMock()
                                        mock_confirm.ask.side_effect = [True, True]
                                        mock_prompt.ask.side_effect = [
                                            "테스트회사",
                                            "개발자",
                                            "공공",
                                            "",
                                            "",
                                        ]

                                        result = run_wizard(tmp_path, jd_path=jd_file)

    assert result["project"].research_notes.startswith("[JD 자동추출 키워드]")
    assert [q.char_limit for q in result["project"].questions] == [700, 500]


def test_parse_experience_json_supports_wrapped_payload_and_unknown_payload(tmp_path: Path):
    from resume_agent.wizard import parse_experience_json

    wrapped_file = tmp_path / "wrapped.json"
    wrapped_file.write_text(
        """
        {
          "experiences": [
            {
              "id": "exp_json",
              "title": "JSON 경험",
              "organization": "테스트원",
              "period_start": "2024-01",
              "situation": "상황",
              "task": "과제",
              "action": "행동",
              "result": "결과",
              "personal_contribution": "기여",
              "metrics": "1건",
              "tags": ["테스트"],
              "evidence_level": "L2",
              "verification_status": "verified"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    unknown_file = tmp_path / "unknown.json"
    unknown_file.write_text('{"unexpected": []}', encoding="utf-8")

    wrapped = parse_experience_json(wrapped_file)
    unknown = parse_experience_json(unknown_file)

    assert len(wrapped) == 1
    assert wrapped[0].title == "JSON 경험"
    assert unknown == []


def test_extract_organization_matches_second_pattern():
    from resume_agent.wizard import _extract_organization

    assert _extract_organization("이후 행정안전부와 협의해 절차를 정리했습니다.") == "행정안전부"
