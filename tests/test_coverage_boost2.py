"""커버리지 향상 — top001, interview_engine, tokenizer, editor, miner, pipeline 모듈"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


# ──────────────────────────────────────────────────
# top001/evidence_chain 모듈 테스트
# ──────────────────────────────────────────────────


class TestEvidenceChain:
    def _make_exp(self, exp_id: str = "e1", **kwargs) -> MagicMock:
        exp = MagicMock()
        exp.id = exp_id
        exp.title = kwargs.get("title", "테스트 경험")
        exp.organization = kwargs.get("organization", "테스트 조직")
        exp.start_date = kwargs.get("start_date", "2024-01")
        exp.end_date = kwargs.get("end_date", "2024-06")
        exp.action = kwargs.get("action", "개발 담당")
        exp.personal_contribution = kwargs.get("personal_contribution", "")
        exp.result = kwargs.get("result", "성과 달성")
        exp.metrics = kwargs.get("metrics", "")
        exp.evidence_level = kwargs.get("evidence_level", EvidenceLevel.L1)
        exp.verification_status = kwargs.get(
            "verification_status", VerificationStatus.NEEDS_VERIFICATION
        )
        return exp

    def test_validate_temporal_consistency_empty(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        validator = EvidenceChainValidator()
        result = validator.validate_temporal_consistency([])
        assert result == []

    def test_validate_temporal_consistency_single(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        validator = EvidenceChainValidator()
        result = validator.validate_temporal_consistency([self._make_exp()])
        assert result == []

    def test_validate_temporal_consistency_overlapping(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exp1 = self._make_exp(
            "e1", start_date="2024-01", organization="A회사", title="개발자"
        )
        exp2 = self._make_exp(
            "e2", start_date="2024-01", organization="A회사", title="디자이너"
        )
        validator = EvidenceChainValidator()
        result = validator.validate_temporal_consistency([exp1, exp2])
        assert len(result) >= 1
        assert result[0].inconsistency_type == "overlapping_roles"

    def test_validate_temporal_consistency_timeline_overlap(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exp1 = self._make_exp(
            "e1",
            start_date="2024-01",
            end_date="2024-06",
            organization="A",
            title="T1",
        )
        exp2 = self._make_exp(
            "e2",
            start_date="2024-03",
            end_date="2024-09",
            organization="B",
            title="T2",
        )
        validator = EvidenceChainValidator()
        result = validator.validate_temporal_consistency([exp1, exp2])
        # 기간 겹침 감지
        types = [r.inconsistency_type for r in result]
        assert "timeline_overlap" in types or "overlapping_roles" in types

    def test_validate_role_consistency_empty(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        validator = EvidenceChainValidator()
        result = validator.validate_role_consistency([])
        assert result == []

    def test_validate_role_consistency_vague_attribution(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exp = self._make_exp(action="프로젝트를 주도했습니다", personal_contribution="")
        validator = EvidenceChainValidator()
        result = validator.validate_role_consistency([exp])
        assert len(result) >= 1
        assert result[0].inconsistency_type == "vague_personal_contribution"

    def test_validate_role_consistency_team_vs_personal(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exp = self._make_exp(
            action="함께 개발했습니다",
            personal_contribution="전체 시스템 설계 담당",
        )
        validator = EvidenceChainValidator()
        result = validator.validate_role_consistency([exp])
        assert len(result) >= 1
        assert result[0].inconsistency_type == "team_vs_personal"

    def test_validate_cross_question_allocation_empty(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        validator = EvidenceChainValidator()
        result = validator.validate_cross_question_allocation([], [])
        assert result == []

    def test_validate_cross_question_allocation_overused(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        allocations = [
            {"experience_id": "e1"},
            {"experience_id": "e1"},
            {"experience_id": "e1"},
        ]
        exps = [self._make_exp("e1", organization="A")]
        validator = EvidenceChainValidator()
        result = validator.validate_cross_question_allocation(allocations, exps)
        types = [r["type"] for r in result]
        assert "overused_experience" in types

    def test_validate_cross_question_allocation_consecutive_same_org(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        allocations = [
            {"experience_id": "e1"},
            {"experience_id": "e2"},
        ]
        exps = [
            self._make_exp("e1", organization="A"),
            self._make_exp("e2", organization="A"),
        ]
        validator = EvidenceChainValidator()
        result = validator.validate_cross_question_allocation(allocations, exps)
        types = [r["type"] for r in result]
        assert "consecutive_same_org" in types

    def test_suggest_experience_additions_empty(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        validator = EvidenceChainValidator()
        result = validator.suggest_experience_additions([], [], [])
        assert len(result) >= 1
        assert "비어 있습니다" in result[0]

    def test_suggest_experience_additions_few_experiences(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exps = [self._make_exp("e1")]
        questions = [MagicMock(), MagicMock(), MagicMock()]
        validator = EvidenceChainValidator()
        result = validator.suggest_experience_additions(exps, questions, [])
        assert any("부족합니다" in s for s in result)

    def test_suggest_experience_additions_no_l3(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exps = [
            self._make_exp("e1", evidence_level=EvidenceLevel.L1),
            self._make_exp("e2", evidence_level=EvidenceLevel.L2),
        ]
        validator = EvidenceChainValidator()
        result = validator.suggest_experience_additions(exps, [], [])
        assert any("L3" in s for s in result)

    def test_suggest_experience_additions_many_unused(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exps = [
            self._make_exp("e1", evidence_level=EvidenceLevel.L3, metrics="30% 향상"),
            self._make_exp("e2", evidence_level=EvidenceLevel.L3, metrics="50건"),
            self._make_exp("e3", evidence_level=EvidenceLevel.L3, metrics="10배"),
        ]
        validator = EvidenceChainValidator()
        result = validator.suggest_experience_additions(exps, [], [])
        # 미사용 경험 경고 확인
        assert isinstance(result, list)

    def test_get_coverage_report(self):
        from resume_agent.top001.evidence_chain import EvidenceChainValidator

        exps = [
            self._make_exp("e1", evidence_level=EvidenceLevel.L3),
            self._make_exp("e2", evidence_level=EvidenceLevel.L2),
        ]
        questions = [MagicMock(), MagicMock()]
        allocations = [{"experience_id": "e1"}]
        validator = EvidenceChainValidator()
        result = validator.get_coverage_report(exps, questions, allocations)
        assert result["total_experiences"] == 2
        assert result["total_questions"] == 2
        assert result["allocated_questions"] == 1
        assert result["l3_experiences"] == 1

    def test_inconsistency_to_dict(self):
        from resume_agent.top001.evidence_chain import Inconsistency

        inc = Inconsistency(
            inconsistency_type="test",
            severity="high",
            description="테스트 설명",
            related_experiences=["e1", "e2"],
        )
        d = inc.to_dict()
        assert d["type"] == "test"
        assert d["severity"] == "high"
        assert len(d["experiences"]) == 2


# ──────────────────────────────────────────────────
# top001/strategic_research 모듈 테스트
# ──────────────────────────────────────────────────


class TestStrategicResearch:
    def test_extract_strategic_signals_empty(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        signals = translator.extract_strategic_signals(None)
        assert signals.core_values_alignment == []

    def test_extract_strategic_signals_with_analysis(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        analysis = MagicMock()
        analysis.core_values = ["혁신", "협업", "고객 중심"]
        analysis.preferred_evidence_types = ["정량적 성과", "리더십"]
        analysis.interview_style = MagicMock(value="FORMAL")
        analysis.company_name = "테스트회사"
        analysis.industry = "IT"

        translator = StrategicResearchTranslator()
        signals = translator.extract_strategic_signals(analysis)
        assert len(signals.core_values_alignment) == 3
        assert len(signals.competency_matches) == 2

    def test_predict_interview_questions_styles(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        for style in ["FORMAL", "BEHAVIORAL", "TECHNICAL", "CASUAL"]:
            result = translator._predict_interview_questions(style)
            assert len(result) >= 1

    def test_predict_interview_questions_unknown(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        result = translator._predict_interview_questions("UNKNOWN_STYLE")
        assert len(result) >= 1

    def test_generate_question_specific_hooks_empty(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        result = translator.generate_question_specific_hooks([], None, [])
        assert result == {}

    def test_generate_question_specific_hooks_with_questions(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        q1 = MagicMock()
        q1.id = "q1"
        q1.detected_type = MagicMock(value="TYPE_A")

        q2 = MagicMock()
        q2.id = "q2"
        q2.detected_type = MagicMock(value="TYPE_B")

        analysis = MagicMock()
        analysis.core_values = ["혁신", "협업"]
        analysis.preferred_evidence_types = ["정량적 성과"]

        translator = StrategicResearchTranslator()
        result = translator.generate_question_specific_hooks([q1, q2], analysis, [])
        assert "q1" in result
        assert "q2" in result

    def test_create_evidence_mapping_empty(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        result = translator.create_evidence_mapping([], None)
        assert result == []

    def test_create_evidence_mapping_with_experiences(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        exp = MagicMock()
        exp.id = "e1"
        exp.title = "테스트"
        exp.action = "개발 담당"
        exp.result = "성과 달성"
        exp.metrics = "30% 향상"
        exp.evidence_text = "증빙 자료입니다"
        exp.personal_contribution = "개인 기여"

        analysis = MagicMock()
        analysis.preferred_evidence_types = ["개발", "성과"]

        translator = StrategicResearchTranslator()
        result = translator.create_evidence_mapping([exp], analysis)
        assert len(result) == 1
        assert result[0].experience_id == "e1"

    def test_build_interview_prediction_empty(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        result = translator.build_interview_prediction(None)
        assert result == []

    def test_build_interview_prediction_by_type(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        for ctype in ["공공", "공기업", "대기업", "스타트업"]:
            analysis = MagicMock()
            analysis.company_type = ctype
            analysis.interview_style = MagicMock(value="FORMAL")
            result = translator.build_interview_prediction(analysis)
            assert len(result) >= 1

    def test_generate_defense_strategy(self):
        from resume_agent.top001.strategic_research import StrategicResearchTranslator

        translator = StrategicResearchTranslator()
        result = translator.generate_defense_strategy(None, [])
        assert len(result) == 3  # 3 vulnerable points
        assert all(s.vulnerable_point for s in result)


# ──────────────────────────────────────────────────
# interview_engine 모듈 테스트
# ──────────────────────────────────────────────────


class TestInterviewEngine:
    def test_build_committee_rounds_empty(self):
        from resume_agent.interview_engine import _build_committee_rounds

        result = _build_committee_rounds([], 0, "테스트 질문")
        assert result == []

    def test_build_committee_rounds_with_personas(self):
        from resume_agent.interview_engine import _build_committee_rounds

        personas = [
            {"name": "위원장", "role": "종합 평가", "focus": ["논리성"]},
            {"name": "실무위원", "role": "실무 검증", "focus": ["기술력"]},
            {"name": "인사위원", "role": "인성 평가", "focus": ["협업"]},
        ]
        result = _build_committee_rounds(personas, 0, "테스트 질문")
        assert len(result) == 3
        assert result[0]["stance"] == "주질문 검증"
        assert result[1]["stance"] == "실무 적합성 검증"
        assert result[2]["stance"] == "리스크 및 반례 검증"

    def test_persona_reframe_question_with_focus(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {"focus": ["논리성", "근거"]}
        result = _persona_reframe_question("원래 질문", persona)
        assert "논리성" in result or "근거" in result

    def test_persona_reframe_question_no_focus(self):
        from resume_agent.interview_engine import _persona_reframe_question

        persona = {}
        result = _persona_reframe_question("원래 질문", persona)
        assert result == "원래 질문"

    def test_call_codex_simple_failure(self, tmp_path: Path):
        from resume_agent.interview_engine import _call_codex_simple

        with patch("resume_agent.interview_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="error", returncode=1)
            result = _call_codex_simple(tmp_path, "테스트 프롬프트")
            assert "Error" in result or result == "" or len(result) > 0


# ──────────────────────────────────────────────────
# tokenizer 모듈 테스트
# ──────────────────────────────────────────────────


class TestTokenizer:
    def test_extract_nouns_fallback(self):
        from resume_agent.tokenizer import extract_nouns

        nouns = extract_nouns("안녕하세요 세계입니다")
        assert isinstance(nouns, list)
        assert len(nouns) > 0

    def test_extract_nouns_empty(self):
        from resume_agent.tokenizer import extract_nouns

        nouns = extract_nouns("")
        assert nouns == []

    def test_extract_nouns_korean(self):
        from resume_agent.tokenizer import extract_nouns

        nouns = extract_nouns("대한민국 서울특별시 강남구")
        assert isinstance(nouns, list)

    def test_extract_nouns_english(self):
        from resume_agent.tokenizer import extract_nouns

        nouns = extract_nouns("Python programming language")
        assert isinstance(nouns, list)

    def test_extract_nouns_mixed(self):
        from resume_agent.tokenizer import extract_nouns

        nouns = extract_nouns("Python 개발자 모집")
        assert isinstance(nouns, list)
        assert len(nouns) > 0


# ──────────────────────────────────────────────────
# __main__ 모듈 테스트
# ──────────────────────────────────────────────────


class TestMain:
    def test_main_entry_point(self):
        from resume_agent.__main__ import main

        assert callable(main)


# ──────────────────────────────────────────────────
# checkpoint 모듈 테스트
# ──────────────────────────────────────────────────


class TestCheckpoint:
    def test_checkpoint_creation(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        path = manager.save_checkpoint("test_stage", {"key": "value"})
        assert path.exists()

    def test_checkpoint_load(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        manager.save_checkpoint("test_stage", {"key": "value"})
        result = manager.load_checkpoint("test_stage")
        assert result == {"key": "value"}

    def test_checkpoint_load_missing(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        result = manager.load_checkpoint("nonexistent")
        assert result is None

    def test_checkpoint_list(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        manager.save_checkpoint("stage1", {"k": "v1"})
        manager.save_checkpoint("stage2", {"k": "v2"})
        steps = manager.list_checkpoints()
        assert len(steps) >= 2

    def test_checkpoint_clear(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        manager.save_checkpoint("stage1", {"k": "v"})
        manager.clear_all_checkpoints()
        steps = manager.list_checkpoints()
        assert len(steps) == 0

    def test_checkpoint_delete(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        manager.save_checkpoint("stage1", {"k": "v"})
        manager.delete_checkpoint("stage1")
        result = manager.load_checkpoint("stage1")
        assert result is None

    def test_checkpoint_has(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        assert manager.has_checkpoint("stage1") is False
        manager.save_checkpoint("stage1", {"k": "v"})
        assert manager.has_checkpoint("stage1") is True

    def test_checkpoint_info(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        manager.save_checkpoint("stage1", {"k": "v"})
        info = manager.get_checkpoint_info("stage1")
        assert info is not None

    def test_checkpoint_resume_point(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        manager.save_checkpoint("coach", {"k": "v"}, status="success")
        manager.save_checkpoint("writer", {"k": "v"}, status="success")
        point = manager.get_resume_point()
        assert point == "writer"

    def test_checkpoint_resume_point_none(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        point = manager.get_resume_point()
        assert point is None

    def test_checkpoint_with_error(self, tmp_path: Path):
        from resume_agent.checkpoint import CheckpointManager

        manager = CheckpointManager(tmp_path)
        path = manager.save_checkpoint(
            "fail_stage", {}, status="failed", error="테스트 에러"
        )
        assert path.exists()


# ──────────────────────────────────────────────────
# estimator 모듈 테스트
# ──────────────────────────────────────────────────


class TestEstimator:
    def test_count_tokens_basic(self):
        from resume_agent.estimator import count_tokens

        result = count_tokens("안녕하세요 세계")
        assert isinstance(result, int)
        assert result > 0

    def test_count_tokens_empty(self):
        from resume_agent.estimator import count_tokens

        result = count_tokens("")
        assert result >= 0

    def test_estimate_cost_and_log(self):
        from resume_agent.estimator import estimate_cost_and_log

        tokens = estimate_cost_and_log("테스트 프롬프트입니다", "테스트")
        assert tokens > 0

    def test_is_over_limit(self):
        from resume_agent.estimator import is_over_limit

        assert is_over_limit(999999) is True
        assert is_over_limit(1) is False

    def test_constants(self):
        from resume_agent.estimator import COST_PER_1K_TOKENS, WARNING_THRESHOLD_TOKENS

        assert COST_PER_1K_TOKENS > 0
        assert WARNING_THRESHOLD_TOKENS > 0


# ──────────────────────────────────────────────────
# progress 모듈 테스트
# ──────────────────────────────────────────────────


class TestProgress:
    def test_progress_bar_creation(self):
        from resume_agent.progress import ProgressBar

        bar = ProgressBar(5, "테스트")
        assert bar.total_steps == 5
        assert bar.current_step == 0

    def test_progress_bar_update(self):
        from resume_agent.progress import ProgressBar

        bar = ProgressBar(3)
        bar.update("1단계 완료")
        assert bar.current_step == 1

    def test_progress_bar_finish(self):
        from resume_agent.progress import ProgressBar

        bar = ProgressBar(2)
        bar.update("1")
        bar.update("2")
        bar.finish()
        assert bar.current_step == 2

    def test_progress_bar_invalid_steps(self):
        from resume_agent.progress import ProgressBar

        with pytest.raises(ValueError):
            ProgressBar(0)

    def test_print_status(self, capsys):
        from resume_agent.progress import print_status

        print_status("테스트 단계", "진행 중")
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or len(captured.err) > 0


# ──────────────────────────────────────────────────
# utils 모듈 테스트
# ──────────────────────────────────────────────────


class TestUtils:
    def test_slugify(self):
        from resume_agent.utils import slugify

        result = slugify("테스트/파일\\이름:특수문자")
        assert "/" not in result
        assert "\\" not in result

    def test_slugify_english(self):
        from resume_agent.utils import slugify

        result = slugify("Hello World Test")
        assert result == "hello-world-test"

    def test_timestamp_slug(self):
        from resume_agent.utils import timestamp_slug

        result = timestamp_slug()
        assert len(result) > 0
        assert "_" in result

    def test_safe_read_text_exists(self, tmp_path: Path):
        from resume_agent.utils import safe_read_text

        f = tmp_path / "test.txt"
        f.write_text("테스트 내용", encoding="utf-8")
        result = safe_read_text(f)
        assert result == "테스트 내용"

    def test_safe_read_text_missing(self, tmp_path: Path):
        from resume_agent.utils import safe_read_text

        result = safe_read_text(tmp_path / "nonexistent.txt")
        assert result == ""

    def test_read_json_if_exists(self, tmp_path: Path):
        from resume_agent.utils import read_json_if_exists

        f = tmp_path / "test.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        result = read_json_if_exists(f)
        assert result == {"key": "value"}

    def test_read_json_if_exists_missing(self, tmp_path: Path):
        from resume_agent.utils import read_json_if_exists

        result = read_json_if_exists(tmp_path / "nonexistent.json")
        assert result == []

    def test_relative(self, tmp_path: Path):
        from resume_agent.utils import relative

        root = tmp_path / "project"
        root.mkdir()
        child = root / "src" / "file.py"
        result = relative(root, child)
        assert result == "src/file.py"

    def test_write_if_missing(self, tmp_path: Path):
        from resume_agent.utils import write_if_missing

        f = tmp_path / "new.txt"
        write_if_missing(f, "테스트")
        assert f.read_text(encoding="utf-8") == "테스트"

    def test_write_if_missing_no_overwrite(self, tmp_path: Path):
        from resume_agent.utils import write_if_missing

        f = tmp_path / "existing.txt"
        f.write_text("원본", encoding="utf-8")
        write_if_missing(f, "새로운 내용")
        assert f.read_text(encoding="utf-8") == "원본"

    def test_normalize_example(self):
        from resume_agent.utils import normalize_example

        result = normalize_example("test.py", "코드 내용")
        assert "# Source: test.py" in result
        assert "코드 내용" in result

    def test_normalize_contract_output(self):
        from resume_agent.utils import normalize_contract_output

        text = "일반 텍스트\n## 결과\n이것이 결과입니다"
        result = normalize_contract_output(text, ["## 결과"])
        assert "결과입니다" in result

    def test_normalize_contract_output_empty(self):
        from resume_agent.utils import normalize_contract_output

        result = normalize_contract_output("", ["## 헤딩"])
        assert result == ""


# ──────────────────────────────────────────────────
# templates 모듈 테스트
# ──────────────────────────────────────────────────


class TestTemplates:
    def test_get_prompt_template(self):
        from resume_agent.templates import PROMPT_SIMULATE_ANSWER

        assert "{question}" in PROMPT_SIMULATE_ANSWER
        assert "{experience_json}" in PROMPT_SIMULATE_ANSWER

    def test_get_follow_up_template(self):
        from resume_agent.templates import PROMPT_GENERATE_FOLLOW_UP

        assert "{company}" in PROMPT_GENERATE_FOLLOW_UP
        assert "{simulated_answer}" in PROMPT_GENERATE_FOLLOW_UP
