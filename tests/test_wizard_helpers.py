"""wizard.py 보조 함수 테스트 — parse_experience_text, _extract_tags, _extract_organization, _show_experience_table, _recommend_experiences"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestParseExperienceText:
    """parse_experience_txt 테스트 — 라인 290-311"""

    def test_parse_single_experience(self, tmp_path: Path):
        from resume_agent.wizard import parse_experience_txt

        txt_file = tmp_path / "experience.txt"
        txt_file.write_text(
            """1. 웹 서비스 개발 프로젝트: Python Django를 사용한 쇼핑몰 개발
상황(Situation): 기존 시스템의 성능 문제로 개선 필요
과제(Task): API 응답 시간 1초 이내 단축
행동(Action): Redis 캐싱 도입, DB 쿼리 최적화
결과(Result): 응답 시간 84% 단축, 처리량 3배 증가
""",
            encoding="utf-8",
        )

        result = parse_experience_txt(txt_file)
        assert len(result) >= 1

    def test_parse_multiple_experiences(self, tmp_path: Path):
        from resume_agent.wizard import parse_experience_txt

        txt_file = tmp_path / "experience.txt"
        txt_file.write_text(
            """1. 첫 번째 프로젝트: 프로젝트 설명
상황(Situation): 상황1
과제(Task): 과제1
행동(Action): 행동1
결과(Result): 결과1

2. 두 번째 프로젝트: 프로젝트 설명2
상황(Situation): 상황2
과제(Task): 과제2
행동(Action): 행동2
결과(Result): 결과2
""",
            encoding="utf-8",
        )

        result = parse_experience_txt(txt_file)
        assert len(result) == 2

    def test_parse_empty_text(self, tmp_path: Path):
        from resume_agent.wizard import parse_experience_txt

        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("", encoding="utf-8")

        result = parse_experience_txt(txt_file)
        assert result == []

    def test_parse_experience_with_metrics(self, tmp_path: Path):
        from resume_agent.wizard import parse_experience_txt
        from resume_agent.models import EvidenceLevel

        txt_file = tmp_path / "experience.txt"
        txt_file.write_text(
            """1. 데이터 분석 프로젝트: 데이터 분석
상황(Situation): 데이터 분석 필요
과제(Task): 분석 과제
행동(Action): 분석 행동
결과(Result): 30% 향상, 50건 처리
""",
            encoding="utf-8",
        )

        result = parse_experience_txt(txt_file)
        assert len(result) == 1
        assert result[0].evidence_level == EvidenceLevel.L3


class TestExtractTags:
    """_extract_tags 테스트 — 라인 383-399"""

    def test_extract_collaboration_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "팀원들과 협업하여 프로젝트를 완료했습니다."
        result = _extract_tags(text)
        assert "협업" in result

    def test_extract_problem_solving_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "문제를 해결하고 개선 방안을 마련했습니다."
        result = _extract_tags(text)
        assert "문제해결" in result

    def test_extract_customer_service_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "고객 응대 및 민원 처리를 담당했습니다."
        result = _extract_tags(text)
        assert "고객응대" in result

    def test_extract_data_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "데이터를 분석하고 엑셀로 수치를 정리했습니다."
        result = _extract_tags(text)
        assert "데이터" in result

    def test_extract_leadership_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "프로젝트를 주도하고 팀을 이끌었습니다."
        result = _extract_tags(text)
        assert "리더십" in result

    def test_extract_achievement_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "성과를 내고 결과를 개선했습니다."
        result = _extract_tags(text)
        assert "성과" in result

    def test_extract_conflict_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "갈등을 중재하고 조율했습니다."
        result = _extract_tags(text)
        assert "갈등" in result

    def test_extract_crisis_tag(self):
        from resume_agent.wizard import _extract_tags

        text = "위기 상황에서 긴급하게 대응했습니다."
        result = _extract_tags(text)
        assert "위기" in result

    def test_extract_no_tags(self):
        from resume_agent.wizard import _extract_tags

        text = "단순한 텍스트입니다."
        result = _extract_tags(text)
        assert result == []

    def test_extract_max_5_tags(self):
        from resume_agent.wizard import _extract_tags

        text = "협업 문제해결 고객응대 데이터 리더십 성과 갈등 위기"
        result = _extract_tags(text)
        assert len(result) <= 5


class TestExtractOrganization:
    """_extract_organization 테스트 — 라인 405-415"""

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


class TestShowExperienceTable:
    """_show_experience_table 테스트 — 라인 420-434"""

    def test_show_table(self, tmp_path: Path):
        from resume_agent.wizard import _show_experience_table
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
            with patch("resume_agent.wizard.Table"):
                _show_experience_table([exp])


class TestRecommendExperiences:
    """_recommend_experiences 테스트 — 라인 441-449"""

    def test_basic_recommendation(self, tmp_path: Path):
        from resume_agent.wizard import _recommend_experiences
        from resume_agent.models import (
            Experience,
            EvidenceLevel,
            VerificationStatus,
            Question,
            QuestionType,
        )

        exp = Experience(
            id="e1",
            title="Python 개발 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="Python으로 개발했습니다.",
            result="테스트 결과입니다.",
            personal_contribution="개인 기여",
            metrics="30% 향상",
            tags=["Python", "개발"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        question = MagicMock()
        question.question_text = "Python 개발 경험을 말씀해주세요"
        question.detected_type = QuestionType.TYPE_B

        result = _recommend_experiences(question, [exp])
        assert isinstance(result, list)

    def test_no_matching_experiences(self, tmp_path: Path):
        from resume_agent.wizard import _recommend_experiences
        from resume_agent.models import (
            Experience,
            EvidenceLevel,
            VerificationStatus,
            Question,
            QuestionType,
        )

        exp = Experience(
            id="e1",
            title="요리 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="요리를 했습니다.",
            result="맛있는 요리 완성.",
            personal_contribution="개인 기여",
            metrics="10인분",
            tags=["요리"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

        question = MagicMock()
        question.question_text = "Python 개발 경험을 말씀해주세요"
        question.detected_type = QuestionType.TYPE_B

        result = _recommend_experiences(question, [exp])
        assert isinstance(result, list)
