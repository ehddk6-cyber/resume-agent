"""pipeline.py 추가 커버리지 — 누락 라인 115-159, 163-195, 247-252, 355-356, 453, 593-594, 708, 716, 740, 853-854, 952, 955-956, 1161-1163, 1170, 1195, 1442-1445, 1570-1572, 1592, 1653, 1669, 1682-1684, 1705-1712, 1747, 1755-1756, 1763, 1901, 1922-1947, 1996-2044, 2048-2057, 2061-2142, 2151-2154, 2167-2654, 2672-2723, 2741-2742, 2769, 2798-2801, 2808-2987, 3001-3041, 3045-3161, 3206-3207, 3260-3261, 3269-3281, 3285-3293, 3368, 3384-3385, 3395-3470, 3474-3483, 3509-3510, 3594, 3645, 3707-3723, 3935, 3961, 3985, 4007, 4010-4016, 4028-4030, 4038-4043, 4059, 4077, 4177, 4195, 4206, 4285-4286, 4339-4340, 4499, 4505, 4511, 4533, 4548, 4553, 4558, 4564-4572, 4606-4611, 4644, 4651, 4655-4662, 4666, 4670"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


def _make_exp(**kwargs) -> Experience:
    defaults = {
        "id": "e1",
        "title": "테스트",
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


class TestInitWorkspace:
    """init_workspace 테스트 — 라인 115-159"""

    def test_init_workspace(self, tmp_path: Path):
        from resume_agent.pipeline import init_workspace

        ws = init_workspace(tmp_path)
        assert ws is not None
        assert ws.root == tmp_path


class TestCrawlBase:
    """crawl_base 테스트 — 라인 163-195"""

    def test_crawl_base_with_path(self, tmp_path: Path):
        from resume_agent.pipeline import crawl_base

        source_dir = tmp_path / "sources"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("테스트 내용", encoding="utf-8")

        with patch("resume_agent.pipeline.Workspace") as MockWS:
            with patch("resume_agent.pipeline.ingest_source_file") as mock_ingest:
                with patch(
                    "resume_agent.pipeline.read_json_if_exists", return_value=None
                ):
                    with patch(
                        "resume_agent.pipeline._extract_jd_keywords_for_research",
                        return_value=[],
                    ):
                        source = MagicMock()
                        source.id = "s1"
                        mock_ingest.return_value = (source, [])
                        ws = MagicMock()
                        ws.root = tmp_path
                        ws.sources_dir = tmp_path / "sources"
                        MockWS.return_value = ws
                        result = crawl_base(ws, source_dir)
                        assert result is not None


class TestCrawlWebSources:
    """crawl_web_sources 테스트 — 라인 247-252"""

    def test_crawl_web_sources(self, tmp_path: Path):
        from resume_agent.pipeline import crawl_web_sources

        with patch("resume_agent.pipeline.Workspace") as MockWS:
            with patch("resume_agent.pipeline.ingest_public_url") as mock_ingest:
                with patch("resume_agent.pipeline.write_source_artifacts"):
                    with patch(
                        "resume_agent.pipeline.load_knowledge_sources", return_value=[]
                    ):
                        with patch(
                            "resume_agent.pipeline.merge_sources", return_value=[]
                        ):
                            with patch("resume_agent.pipeline.save_knowledge_sources"):
                                with patch(
                                    "resume_agent.pipeline.summarize_knowledge_sources",
                                    return_value={},
                                ):
                                    with patch("resume_agent.pipeline.write_json"):
                                        with patch(
                                            "resume_agent.pipeline.read_json_if_exists",
                                            return_value=None,
                                        ):
                                            with patch(
                                                "resume_agent.pipeline._extract_jd_keywords_for_research",
                                                return_value=[],
                                            ):
                                                source = MagicMock()
                                                source.id = "s1"
                                                mock_ingest.return_value = [source]
                                                ws = MagicMock()
                                                ws.root = tmp_path
                                                ws.analysis_dir = tmp_path / "analysis"
                                                ws.analysis_dir.mkdir(
                                                    parents=True, exist_ok=True
                                                )
                                                MockWS.return_value = ws
                                                result = crawl_web_sources(
                                                    ws, ["https://example.com"]
                                                )
                                                assert result is not None


class TestExtractMarkdownSection:
    def test_basic(self):
        from resume_agent.pipeline import extract_markdown_section

        text = "## A\n내용A\n## B\n내용B"
        result = extract_markdown_section(text, "## A", ["## B"])
        assert "내용A" in result

    def test_not_found(self):
        from resume_agent.pipeline import extract_markdown_section

        result = extract_markdown_section("텍스트", "## 없는것", [])
        assert result == ""

    def test_no_stop(self):
        from resume_agent.pipeline import extract_markdown_section

        text = "## A\n내용전체"
        result = extract_markdown_section(text, "## A", [])
        assert "내용전체" in result


class TestBuildDataBlock:
    def test_basic(self):
        import json
        from resume_agent.pipeline import build_data_block

        project = MagicMock()
        project.model_dump.return_value = {"name": "test"}
        result = build_data_block(
            project=project,
            experiences=[_make_exp()],
            knowledge_hints=[{"title": "힌트"}],
        )
        data = json.loads(result)
        assert "project" in data
        assert "experiences" in data
        assert "knowledge_hints" in data

    def test_with_extra(self):
        import json
        from resume_agent.pipeline import build_data_block

        project = MagicMock()
        project.model_dump.return_value = {"name": "test"}
        result = build_data_block(
            project=project,
            experiences=[],
            knowledge_hints=[],
            extra={"추가": "데이터"},
        )
        data = json.loads(result)
        assert data["extra"] == {"추가": "데이터"}


class TestBuildWriterRewritePrompt:
    def test_with_validation_issues(self):
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

    def test_no_issues(self):
        from resume_agent.pipeline import build_writer_rewrite_prompt

        validation = MagicMock()
        validation.missing = []
        quality_evals = [{"question_order": 1, "overall_score": 0.9}]
        result = build_writer_rewrite_prompt("이전출력", validation, quality_evals)
        assert isinstance(result, str)


class TestBuildCommitteeFeedbackContext:
    def test_no_sessions(self, tmp_path: Path):
        from resume_agent.pipeline import build_committee_feedback_context

        ws = MagicMock()
        ws.root = tmp_path
        ws.state_dir = tmp_path / "state"
        ws.state_dir.mkdir(parents=True, exist_ok=True)
        ws.ensure = MagicMock()

        with patch("resume_agent.pipeline.read_json_if_exists", return_value=[]):
            result = build_committee_feedback_context(ws)
            assert result is not None


class TestGetSuccessCasesForAnalysis:
    def test_with_success_cases(self, tmp_path: Path):
        from resume_agent.pipeline import _get_success_cases_for_analysis

        ws = MagicMock()
        ws.root = tmp_path

        with patch("resume_agent.pipeline.load_success_cases") as mock_load:
            mock_load.return_value = [MagicMock(), MagicMock()]
            result = _get_success_cases_for_analysis(ws)
            assert result is not None
            assert len(result) == 2

    def test_with_empty_success_cases(self, tmp_path: Path):
        from resume_agent.pipeline import _get_success_cases_for_analysis

        ws = MagicMock()
        ws.root = tmp_path

        with patch("resume_agent.pipeline.load_success_cases") as mock_load:
            mock_load.return_value = []
            result = _get_success_cases_for_analysis(ws)
            assert result is None

    def test_with_exception(self, tmp_path: Path):
        from resume_agent.pipeline import _get_success_cases_for_analysis

        ws = MagicMock()
        ws.root = tmp_path

        with patch(
            "resume_agent.pipeline.load_success_cases",
            side_effect=Exception("테스트 오류"),
        ):
            result = _get_success_cases_for_analysis(ws)
            assert result is None
