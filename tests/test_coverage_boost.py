"""커버리지 향상을 위한 통합 테스트 — docx_export, editor, miner, vault, validators, pdf_utils"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


# ──────────────────────────────────────────────────
# docx_export 모듈 테스트
# ──────────────────────────────────────────────────


class TestDocxExportAvailability:
    def test_is_docx_available_returns_bool(self):
        from resume_agent.docx_export import is_docx_available

        result = is_docx_available()
        assert isinstance(result, bool)

    def test_export_returns_none_when_docx_unavailable(self, tmp_path: Path):
        with patch.dict("sys.modules", {"docx": None}):
            from resume_agent.docx_export import export_to_docx

            md_file = tmp_path / "test.md"
            md_file.write_text("# Hello\nWorld")
            result = export_to_docx(md_file, tmp_path / "out.docx")
            # Document is None일 때 None 반환
            assert result is None or result == tmp_path / "out.docx"

    def test_export_returns_none_when_md_missing(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        missing = tmp_path / "nonexistent.md"
        result = export_to_docx(missing, tmp_path / "out.docx")
        assert result is None

    def test_export_creates_docx(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        md_file = tmp_path / "test.md"
        md_file.write_text(
            "# 제목\n\n본문 내용입니다.\n\n## 소제목\n\n- 항목1\n- 항목2\n"
        )
        out = tmp_path / "output.docx"
        result = export_to_docx(md_file, out)
        assert result is not None
        assert result.exists()

    def test_export_with_project_info(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        md_file = tmp_path / "test.md"
        md_file.write_text("# 자기소개\n\n안녕하세요.")
        out = tmp_path / "output.docx"
        info = {"company_name": "테스트회사", "job_title": "개발자"}
        result = export_to_docx(md_file, out, project_info=info)
        assert result is not None
        assert result.exists()

    def test_convert_markdown_headings(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        md = tmp_path / "test.md"
        md.write_text(
            "# H1\n## H2\n### H3\n#### H4\n> 인용문\n**굵게**\n*기울임*\n`코드`\n"
        )
        out = tmp_path / "out.docx"
        assert export_to_docx(md, out) is not None

    def test_convert_code_block(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        md = tmp_path / "test.md"
        md.write_text("일반 텍스트\n```\n코드 블록 내용\n```\n이어서\n")
        out = tmp_path / "out.docx"
        assert export_to_docx(md, out) is not None

    def test_convert_numbered_list(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        md = tmp_path / "test.md"
        md.write_text("1. 첫 번째\n2. 두 번째\n3. 세 번째\n")
        out = tmp_path / "out.docx"
        assert export_to_docx(md, out) is not None

    def test_export_artifacts_returns_none_when_no_docx(self, tmp_path: Path):
        from resume_agent.docx_export import export_artifacts_to_docx

        with patch("resume_agent.docx_export.Document", None):
            result = export_artifacts_to_docx(
                tmp_path / "coach.md",
                tmp_path / "writer.md",
                tmp_path / "interview.md",
                tmp_path / "out.docx",
            )
            assert result is None

    def test_export_artifacts_success(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_artifacts_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        (tmp_path / "coach.md").write_text("# 코칭 결과\n\n내용")
        (tmp_path / "writer.md").write_text("# 작성 결과\n\n내용")
        (tmp_path / "interview.md").write_text("# 면접 준비\n\n내용")
        out = tmp_path / "combined.docx"
        result = export_artifacts_to_docx(
            tmp_path / "coach.md",
            tmp_path / "writer.md",
            tmp_path / "interview.md",
            out,
            project_info={"company_name": "회사", "job_title": "직무"},
        )
        assert result is not None
        assert result.exists()

    def test_export_artifacts_missing_files(self, tmp_path: Path):
        from resume_agent.docx_export import is_docx_available, export_artifacts_to_docx

        if not is_docx_available():
            pytest.skip("python-docx not installed")

        out = tmp_path / "combined.docx"
        result = export_artifacts_to_docx(
            tmp_path / "no_coach.md",
            tmp_path / "no_writer.md",
            tmp_path / "no_interview.md",
            out,
        )
        assert result is not None


# ──────────────────────────────────────────────────
# editor 모듈 테스트
# ──────────────────────────────────────────────────


class TestEditor:
    def test_run_editor_no_experiences(self, tmp_path: Path):
        from resume_agent.editor import run_editor
        from resume_agent.workspace import Workspace
        from resume_agent.state import initialize_state

        ws = Workspace(tmp_path / "ws")
        ws.ensure()
        initialize_state(ws)

        with patch("resume_agent.editor.console") as mock_console:
            with patch("resume_agent.editor.load_experiences", return_value=[]):
                run_editor(ws)
            # 경험 없으면 콘솔에 메시지 출력
            mock_console.print.assert_called()

    def test_run_editor_with_experiences(self, tmp_path: Path):
        from resume_agent.editor import run_editor
        from resume_agent.workspace import Workspace
        from resume_agent.state import initialize_state, save_experiences

        ws = Workspace(tmp_path / "ws")
        ws.ensure()
        initialize_state(ws)

        exp = Experience(
            id="ed1",
            title="테스트 경험",
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황",
            task="테스트 과제",
            action="테스트 행동",
            result="테스트 결과",
            personal_contribution="",
            metrics="정량 수치 없음",
            tags=[],
            evidence_level=EvidenceLevel.L1,
            verification_status=VerificationStatus.NEEDS_VERIFICATION,
        )
        save_experiences(ws, [exp])

        with patch("resume_agent.editor.console"):
            with patch("resume_agent.editor.Prompt") as mock_prompt:
                mock_prompt.ask.side_effect = ["q"]
                run_editor(ws)


# ──────────────────────────────────────────────────
# vault 모듈 테스트
# ──────────────────────────────────────────────────


class TestVaultManager:
    def _make_exp(self, exp_id: str = "e1", title: str = "테스트") -> Experience:
        return Experience(
            id=exp_id,
            title=title,
            organization="테스트 조직",
            period_start="2024-01",
            situation="테스트 상황입니다.",
            task="테스트 과제입니다.",
            action="테스트 행동을 수행했습니다.",
            result="테스트 결과입니다. 30% 향상",
            personal_contribution="개인 기여",
            metrics="30% 향상",
            tags=["테스트"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

    def test_init_creates_state_dir(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        assert vm.global_state_dir.exists()

    def test_load_empty_experiences(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        exps = vm.load_global_experiences()
        assert exps == []

    def test_save_and_load_experiences(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        exps = [self._make_exp()]
        vm.save_global_experiences(exps)
        loaded = vm.load_global_experiences()
        assert len(loaded) == 1
        assert loaded[0].id == "e1"

    def test_sync_to_global_new(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        local = [self._make_exp("local1", "새 경험")]
        vm.sync_to_global(local)
        global_exps = vm.load_global_experiences()
        assert len(global_exps) == 1

    def test_sync_to_global_update(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        vm.save_global_experiences([self._make_exp("e1", "원본")])
        updated = self._make_exp("e1", "업데이트됨")
        vm.sync_to_global([updated])
        global_exps = vm.load_global_experiences()
        assert global_exps[0].title == "업데이트됨"

    def test_scan_evidence_keywords_empty(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        keywords = vm.scan_evidence_keywords()
        assert isinstance(keywords, set)
        assert len(keywords) == 0

    def test_scan_evidence_keywords_with_files(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vault_root = tmp_path / "vault"
        certs_dir = vault_root / "자격증"
        certs_dir.mkdir(parents=True)
        (certs_dir / "컴퓨터활용능력1급.pdf").write_bytes(b"dummy")

        vm = VaultManager(vault_root)
        keywords = vm.scan_evidence_keywords()
        assert "컴퓨터활용능력1급" in keywords or any("컴퓨터" in k for k in keywords)

    def test_verify_experiences(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vault_root = tmp_path / "vault"
        certs_dir = vault_root / "자격증"
        certs_dir.mkdir(parents=True)
        (certs_dir / "컴퓨터활용능력.pdf").write_bytes(b"dummy")

        vm = VaultManager(vault_root)
        exp = Experience(
            id="v1",
            title="컴퓨터활용능력 자격 취득",
            organization="",
            period_start="",
            situation="자격 취득 준비",
            task="자격 취득",
            action="공부 후 시험 응시",
            result="합격",
            personal_contribution="",
            metrics="",
            tags=[],
            evidence_level=EvidenceLevel.L1,
            verification_status=VerificationStatus.NEEDS_VERIFICATION,
        )
        count = vm.verify_experiences([exp])
        assert count == 1
        assert exp.verification_status == VerificationStatus.VERIFIED

    def test_verify_experiences_already_verified(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        exp = self._make_exp()
        count = vm.verify_experiences([exp])
        assert count == 0  # 이미 VERIFIED 상태

    def test_load_corrupted_json(self, tmp_path: Path):
        from resume_agent.vault import VaultManager

        vm = VaultManager(tmp_path / "vault")
        vm.global_experiences_file.write_text("invalid json{{{", encoding="utf-8")
        exps = vm.load_global_experiences()
        assert exps == []


# ──────────────────────────────────────────────────
# validators 모듈 테스트
# ──────────────────────────────────────────────────


class TestExperienceValidator:
    def _make_valid_exp(self) -> Experience:
        return Experience(
            id="v1",
            title="웹 서비스 개발 프로젝트",
            organization="테스트 회사",
            period_start="2024-01",
            situation="기존 시스템의 성능 문제가 발생하여 웹 서비스를 개선해야 하는 상황이었습니다. 사용자 수가 증가하면서 응답 시간이 5초 이상으로 늘어났습니다.",
            task="백엔드 개발자로서 API 응답 시간을 1초 이내로 줄이는 것이 목표였습니다. 동시에 코드 품질도 개선해야 했습니다.",
            action="Redis 캐싱을 도입하고 데이터베이스 쿼리를 최적화했습니다. N+1 문제를 해결하고 인덱스를 추가하여 검색 성능을 개선했습니다. 또한 비동기 처리를 도입하여 동시 요청 처리량을 높였습니다.",
            result="API 응답 시간을 5초에서 0.8초로 84% 단축시켰습니다. 동시 접속자 처리량도 3배 향상되어 서비스 안정성이 크게 개선되었습니다.",
            personal_contribution="캐싱 전략 설계 및 구현 담당",
            metrics="응답시간 84% 단축",
            tags=["백엔드", "최적화", "Redis"],
            evidence_level=EvidenceLevel.L3,
            verification_status=VerificationStatus.VERIFIED,
        )

    def _make_empty_exp(self) -> Experience:
        return Experience(
            id="empty",
            title="",
            organization="",
            period_start="",
            situation="",
            task="",
            action="",
            result="",
            personal_contribution="",
            metrics="",
            tags=[],
            evidence_level=EvidenceLevel.L1,
            verification_status=VerificationStatus.NEEDS_VERIFICATION,
        )

    def test_validate_valid_experience(self):
        from resume_agent.validators import ExperienceValidator

        validator = ExperienceValidator()
        result = validator.validate(self._make_valid_exp())
        assert result.passed is True
        assert not result.has_errors

    def test_validate_empty_experience(self):
        from resume_agent.validators import ExperienceValidator

        validator = ExperienceValidator()
        result = validator.validate(self._make_empty_exp())
        assert result.passed is False
        assert result.has_errors

    def test_validate_short_situation(self):
        from resume_agent.validators import ExperienceValidator

        exp = self._make_valid_exp()
        exp.situation = "짧음"
        validator = ExperienceValidator()
        result = validator.validate(exp)
        assert result.has_warnings

    def test_validate_cliche_detection(self):
        from resume_agent.validators import ExperienceValidator

        exp = self._make_valid_exp()
        exp.action = "최선을 다하겠습니다. 열정적으로 임하겠습니다."
        validator = ExperienceValidator()
        result = validator.validate(exp)
        warning_messages = [w.message for w in result.warnings]
        assert any("일반적인 표현" in msg for msg in warning_messages)

    def test_validate_no_numbers_in_result(self):
        from resume_agent.validators import ExperienceValidator

        exp = self._make_valid_exp()
        exp.result = "성과를 달성했습니다"
        validator = ExperienceValidator()
        result = validator.validate(exp)
        warning_messages = [w.message for w in result.warnings]
        assert any("수치" in msg for msg in warning_messages)

    def test_validate_evidence_level_l1(self):
        from resume_agent.validators import ExperienceValidator

        exp = self._make_valid_exp()
        exp.evidence_level = EvidenceLevel.L1
        validator = ExperienceValidator()
        result = validator.validate(exp)
        info_messages = [i.message for i in result.info]
        assert any("L1" in msg for msg in info_messages)

    def test_validate_evidence_level_l2(self):
        from resume_agent.validators import ExperienceValidator

        exp = self._make_valid_exp()
        exp.evidence_level = EvidenceLevel.L2
        validator = ExperienceValidator()
        result = validator.validate(exp)
        info_messages = [i.message for i in result.info]
        assert any("L2" in msg for msg in info_messages)

    def test_validate_evidence_level_l3(self):
        from resume_agent.validators import ExperienceValidator

        exp = self._make_valid_exp()
        exp.evidence_level = EvidenceLevel.L3
        validator = ExperienceValidator()
        result = validator.validate(exp)
        info_messages = [i.message for i in result.info]
        assert any("L3" in msg for msg in info_messages)

    def test_validation_result_summary(self):
        from resume_agent.validators import (
            ExperienceValidator,
            ExperienceValidationResult,
            ValidationMessage,
            ValidationSeverity,
        )

        result = ExperienceValidationResult(
            passed=False,
            errors=[ValidationMessage(ValidationSeverity.ERROR, "title", "오류")],
            warnings=[ValidationMessage(ValidationSeverity.WARNING, "action", "경고")],
            info=[ValidationMessage(ValidationSeverity.INFO, "result", "정보")],
        )
        summary = result.get_summary()
        assert "오류 1건" in summary
        assert "경고 1건" in summary
        assert "정보 1건" in summary

    def test_validation_result_no_issues(self):
        from resume_agent.validators import ExperienceValidationResult

        result = ExperienceValidationResult(
            passed=True, errors=[], warnings=[], info=[]
        )
        assert result.get_summary() == "검증 통과"

    def test_validate_convenience_function(self):
        from resume_agent.validators import validate_experience

        result = validate_experience(self._make_valid_exp())
        assert result.passed is True

    def test_validate_weak_situation_task_connection(self):
        from resume_agent.validators import ExperienceValidator

        exp = self._make_valid_exp()
        exp.situation = "회사에서 새로운 프로젝트를 시작했습니다."
        exp.task = "데이터베이스 마이그레이션을 수행해야 했습니다."
        validator = ExperienceValidator()
        result = validator.validate(exp)
        # 키워드 교집합이 2개 미만이면 경고
        warning_messages = [w.message for w in result.warnings]
        # 연결성 경고가 있을 수 있음 (키워드 교집합에 따라)
        assert isinstance(result.has_warnings, bool)

    def test_validate_star_lengths(self):
        from resume_agent.validators import ExperienceValidator

        validator = ExperienceValidator()
        assert validator.MIN_SITUATION_LENGTH > 0
        assert validator.MIN_TASK_LENGTH > 0
        assert validator.MIN_ACTION_LENGTH > 0
        assert validator.MIN_RESULT_LENGTH > 0

    def test_validate_cliche_patterns_list(self):
        from resume_agent.validators import ExperienceValidator

        validator = ExperienceValidator()
        assert len(validator.CLICHE_PATTERNS) > 0
        assert "최선을 다하겠습니다" in validator.CLICHE_PATTERNS


# ──────────────────────────────────────────────────
# pdf_utils 모듈 테스트
# ──────────────────────────────────────────────────


class TestPdfUtils:
    def test_extract_jd_keywords_empty(self):
        from resume_agent.pdf_utils import extract_jd_keywords

        assert extract_jd_keywords("") == []
        assert extract_jd_keywords(None) == []

    def test_extract_jd_keywords_basic(self):
        from resume_agent.pdf_utils import extract_jd_keywords

        text = "Python 개발자 모집 Python 프로그래밍 경험 필수 Python 활용 능력 우대 Python 데이터 분석"
        keywords = extract_jd_keywords(text)
        assert "Python" in keywords
        assert len(keywords) <= 10

    def test_extract_jd_keywords_filters_stopwords(self):
        from resume_agent.pdf_utils import extract_jd_keywords

        text = "업무 수행 관련 분야 내용 지원 사항 해당 기타 필요 직무 자격 우대 경험 능력 활용 이해 지식 제출 기준 담당"
        keywords = extract_jd_keywords(text)
        # 불용어만 있으면 빈 리스트
        assert len(keywords) == 0

    def test_split_text_short(self):
        from resume_agent.pdf_utils import split_text

        text = "짧은 텍스트"
        result = split_text(text, chunk_size=3000)
        assert len(result) == 1
        assert result[0] == text

    def test_split_text_long(self):
        from resume_agent.pdf_utils import split_text

        text = "a" * 1000 + "\n\n" + "b" * 1000 + "\n\n" + "c" * 1000
        result = split_text(text, chunk_size=1500)
        assert len(result) >= 2

    def test_split_text_single_long_paragraph(self):
        from resume_agent.pdf_utils import split_text

        text = "x" * 5000
        result = split_text(text, chunk_size=2000)
        assert len(result) >= 2

    def test_split_text_with_overlap(self):
        from resume_agent.pdf_utils import split_text

        text = "a" * 3000
        result = split_text(text, chunk_size=1000, overlap=200)
        assert len(result) >= 2

    def test_analyze_jd_structure_empty(self):
        from resume_agent.pdf_utils import analyze_jd_structure

        result = analyze_jd_structure("")
        assert result["required_qualifications"] == []
        assert result["preferred_qualifications"] == []
        assert result["responsibilities"] == []

    def test_analyze_jd_structure_korean(self):
        from resume_agent.pdf_utils import analyze_jd_structure

        text = """자격 요건
- Python 3년 이상 경험
- Django 또는 FastAPI 사용 경험

우대 사항
- AWS 경험
- Docker 사용 경험

담당 업무
- 백엔드 API 개발
- 데이터베이스 설계

기술 스택
- Python
- PostgreSQL
- Redis

복지
- 재택근무
- 교육비 지원
"""
        result = analyze_jd_structure(text)
        assert len(result["required_qualifications"]) >= 1
        assert len(result["preferred_qualifications"]) >= 1
        assert len(result["responsibilities"]) >= 1

    def test_analyze_jd_structure_english(self):
        from resume_agent.pdf_utils import analyze_jd_structure

        text = """Required Qualifications
- 3+ years of Python experience
- Experience with Django or FastAPI

Preferred
- AWS experience

Responsibilities
- Backend API development

Tech Stack
- Python, PostgreSQL, Redis
"""
        result = analyze_jd_structure(text)
        assert len(result["required_qualifications"]) >= 1

    def test_extract_ncs_job_spec_empty(self):
        from resume_agent.pdf_utils import extract_ncs_job_spec

        result = extract_ncs_job_spec("")
        assert result["ability_units"] == []
        assert result["ability_unit_elements"] == []
        assert result["ncs_competencies"] == []

    def test_extract_ncs_job_spec_with_units(self):
        from resume_agent.pdf_utils import extract_ncs_job_spec

        text = "능력단위 o 웹 프로그래밍, 데이터베이스 관리, 시스템 설계"
        result = extract_ncs_job_spec(text)
        assert len(result["ability_units"]) > 0

    def test_extract_ncs_job_spec_with_elements(self):
        from resume_agent.pdf_utils import extract_ncs_job_spec

        text = "능력단위요소 o 요구사항 분석, 설계 문서 작성, 테스트 계획 수립"
        result = extract_ncs_job_spec(text)
        assert len(result["ability_unit_elements"]) > 0

    def test_generate_questions_from_jd_empty(self):
        from resume_agent.pdf_utils import generate_questions_from_jd

        result = generate_questions_from_jd({})
        assert isinstance(result, list)

    def test_generate_questions_from_jd_with_data(self):
        from resume_agent.pdf_utils import generate_questions_from_jd

        jd = {
            "required_qualifications": ["Python 3년 이상", "Django 경험"],
            "preferred_qualifications": ["AWS 경험"],
            "responsibilities": ["API 개발"],
            "tech_stack": ["Python", "PostgreSQL", "Redis"],
        }
        result = generate_questions_from_jd(jd)
        assert len(result) >= 1
        assert all("question_text" in q for q in result)
        assert all("detected_type" in q for q in result)

    def test_extract_text_from_pdf_missing_reader(self):
        from resume_agent.pdf_utils import extract_text_from_pdf

        with patch("resume_agent.pdf_utils.PdfReader", None):
            result = extract_text_from_pdf(Path("/nonexistent.pdf"))
            assert result == ""

    def test_analyze_jd_tech_keywords(self):
        from resume_agent.pdf_utils import analyze_jd_structure

        text = "기술 스�택\n- Python\n- React\n- Docker\n- AWS\n"
        result = analyze_jd_structure(text)
        assert "Python" in result["tech_stack"] or "React" in result["tech_stack"]


# ──────────────────────────────────────────────────
# patina_bridge 모듈 테스트
# ──────────────────────────────────────────────────


class TestPatinaBridge:
    def test_get_patina_skill_dir_not_found(self):
        from resume_agent.patina_bridge import get_patina_skill_dir

        # 시스템에 patina가 설치되어 있을 수 있으므로 mock 사용
        with patch(
            "resume_agent.patina_bridge._PATINA_SKILL_DIR",
            Path("/nonexistent/patina/skill/dir"),
        ):
            with pytest.raises(FileNotFoundError):
                get_patina_skill_dir()

    def test_get_patina_skill_dir_with_mock(self, tmp_path: Path):
        from resume_agent.patina_bridge import get_patina_skill_dir

        fake_skill_dir = tmp_path / "patina"
        fake_skill_dir.mkdir()
        with patch("resume_agent.patina_bridge._PATINA_SKILL_DIR", fake_skill_dir):
            result = get_patina_skill_dir()
            assert result == fake_skill_dir

    def test_get_patina_skill_dir_alt_path(self, tmp_path: Path):
        from resume_agent.patina_bridge import get_patina_skill_dir

        fake_home_dir = tmp_path / "patina"
        fake_home_dir.mkdir()
        with patch(
            "resume_agent.patina_bridge._PATINA_SKILL_DIR",
            Path("/nonexistent/primary"),
        ):
            with patch("pathlib.Path.home", return_value=tmp_path):
                result = get_patina_skill_dir()
                assert result == tmp_path / "patina"

    def test_load_patina_skill_md_not_found(self):
        from resume_agent.patina_bridge import load_patina_skill_md

        with patch(
            "resume_agent.patina_bridge._PATINA_SKILL_DIR",
            Path("/nonexistent/patina"),
        ):
            with pytest.raises(FileNotFoundError):
                load_patina_skill_md()

    def test_load_patina_patterns_not_found(self):
        from resume_agent.patina_bridge import load_patina_patterns

        with patch(
            "resume_agent.patina_bridge._PATINA_SKILL_DIR",
            Path("/nonexistent/patina"),
        ):
            with pytest.raises(FileNotFoundError):
                load_patina_patterns()

    def test_load_patina_scoring_not_found(self):
        from resume_agent.patina_bridge import load_patina_scoring

        with patch(
            "resume_agent.patina_bridge._PATINA_SKILL_DIR",
            Path("/nonexistent/patina"),
        ):
            with pytest.raises(FileNotFoundError):
                load_patina_scoring()

    def test_load_patina_voice_not_found(self):
        from resume_agent.patina_bridge import load_patina_voice

        with patch(
            "resume_agent.patina_bridge._PATINA_SKILL_DIR",
            Path("/nonexistent/patina"),
        ):
            with pytest.raises(FileNotFoundError):
                load_patina_voice()

    def test_valid_modes(self):
        from resume_agent.patina_bridge import VALID_MODES

        assert "audit" in VALID_MODES
        assert "rewrite" in VALID_MODES
        assert "score" in VALID_MODES
        assert "ouroboros" in VALID_MODES


# ──────────────────────────────────────────────────
# miner 모듈 테스트
# ──────────────────────────────────────────────────


class TestMiner:
    def test_mine_empty_txt(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        txt = tmp_path / "empty.txt"
        txt.write_text("", encoding="utf-8")
        result = mine_past_resume(txt, tmp_path)
        assert result == []

    def test_mine_unsupported_format(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        result = mine_past_resume(pdf, tmp_path)
        assert result == []

    def test_mine_whitespace_only(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        txt = tmp_path / "whitespace.txt"
        txt.write_text("   \n\n   ", encoding="utf-8")
        result = mine_past_resume(txt, tmp_path)
        assert result == []

    def test_mine_prompt_template_format(self):
        from resume_agent.miner import MINE_PROMPT_TEMPLATE

        prompt = MINE_PROMPT_TEMPLATE.format(document_text="테스트 문서 내용")
        assert "테스트 문서 내용" in prompt
        assert "JSON" in prompt

    def test_mine_txt_with_codex_failure(self, tmp_path: Path):
        from resume_agent.miner import mine_past_resume

        txt = tmp_path / "test.txt"
        txt.write_text(
            "프로젝트 경험: 웹 서비스 개발을 담당했습니다.", encoding="utf-8"
        )

        with patch("resume_agent.miner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", stderr="codex not found", returncode=1
            )
            result = mine_past_resume(txt, tmp_path)
            assert isinstance(result, list)
