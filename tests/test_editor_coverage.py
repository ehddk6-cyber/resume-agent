"""editor.py 커버리지 — 누락 라인 53-75"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


def _make_exp(**kwargs) -> Experience:
    defaults = {
        "id": "e1",
        "title": "테스트 경험",
        "organization": "테스트 조직",
        "period_start": "2024-01",
        "situation": "테스트 상황입니다. 충분히 긴 설명입니다.",
        "task": "테스트 과제입니다. 충분히 긴 설명입니다.",
        "action": "테스트 행동을 수행했습니다. 충분히 긴 설명입니다.",
        "result": "테스트 결과입니다. 30% 향상 달성.",
        "personal_contribution": "개인 기여 설명",
        "metrics": "30% 향상",
        "tags": ["테스트"],
        "evidence_level": EvidenceLevel.L3,
        "verification_status": VerificationStatus.VERIFIED,
    }
    defaults.update(kwargs)
    return Experience(**defaults)


class TestEditor:
    def test_run_editor_empty(self, tmp_path: Path):
        """경험이 없을 때"""
        from resume_agent.editor import run_editor

        ws = MagicMock()
        ws.ensure = MagicMock()

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[]):
                run_editor(ws)

    def test_run_editor_with_experiences_quit(self, tmp_path: Path):
        """경험이 있고 바로 종료"""
        from resume_agent.editor import run_editor

        ws = MagicMock()
        ws.ensure = MagicMock()

        exp = _make_exp()

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[exp]):
                with patch("resume_agent.editor.Prompt") as mock_prompt:
                    mock_prompt.ask.return_value = "q"
                    run_editor(ws)

    def test_run_editor_edit_and_quit(self, tmp_path: Path):
        """경험 수정 후 종료"""
        from resume_agent.editor import run_editor

        ws = MagicMock()
        ws.ensure = MagicMock()

        exp = _make_exp(metrics="정량 수치 없음")

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[exp]):
                with patch("resume_agent.editor.Prompt") as mock_prompt:
                    # 선택, 제목, 행동, 수치, 계속Enter, 종료q
                    mock_prompt.ask.side_effect = [
                        "1",
                        "새 제목",
                        "새 행동",
                        "50% 향상",
                        "",
                        "q",
                    ]
                    run_editor(ws)
                    # evidence_level이 L3로 변경되었는지 확인
                    assert exp.evidence_level == EvidenceLevel.L3

    def test_run_editor_edit_with_metrics(self, tmp_path: Path):
        """수치 추가 시 증거수준 L3로 상향"""
        from resume_agent.editor import run_editor

        ws = MagicMock()
        ws.ensure = MagicMock()

        exp = _make_exp(metrics="정량 수치 없음")
        # evidence_level을 L1로 설정 (수정 전)
        exp.evidence_level = EvidenceLevel.L1

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[exp]):
                with patch("resume_agent.editor.Prompt") as mock_prompt:
                    # 선택, 제목, 행동, 수치, 계속Enter, 종료q
                    mock_prompt.ask.side_effect = [
                        "1",
                        "새 제목",
                        "새 행동",
                        "50% 향상",
                        "",
                        "q",
                    ]
                    run_editor(ws)
                    # evidence_level이 L3로 변경되었는지 확인
                    assert exp.evidence_level == EvidenceLevel.L3

    def test_run_editor_save_on_quit(self, tmp_path: Path):
        """종료 시 저장"""
        from resume_agent.editor import run_editor

        ws = MagicMock()
        ws.ensure = MagicMock()

        exp = _make_exp()

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.load_experiences", return_value=[exp]):
                with patch("resume_agent.editor.Prompt") as mock_prompt:
                    mock_prompt.ask.return_value = "q"
                    with patch("resume_agent.editor.save_experiences") as mock_save:
                        run_editor(ws)
                        mock_save.assert_called_once()
