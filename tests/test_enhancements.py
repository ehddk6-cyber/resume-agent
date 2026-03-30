import builtins
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from resume_agent.checkpoint import CheckpointManager
from resume_agent.answer_quality import calculate_originality
from resume_agent.defense_simulator import DefenseSimulator
from resume_agent.feedback_learner import FeedbackLearner
from resume_agent.interactive import InteractiveCoach, MockInterviewCoach
from resume_agent.interview_engine import _build_committee_rounds
from resume_agent.models import (
    ApplicationProject,
    Experience,
    Question,
    QuestionType,
    VerificationStatus,
)
from resume_agent.progress import ProgressBar, progress_bar
from resume_agent.quality_evaluator import QualityEvaluator
from resume_agent import scoring
from resume_agent.vector_store import SimpleVectorStore
from resume_agent.state import initialize_state, save_project
from resume_agent.workspace import Workspace


def test_checkpoint_manager_creates_nested_directories(tmp_path):
    nested_workspace = tmp_path / "missing" / "workspace"
    manager = CheckpointManager(nested_workspace)

    assert manager.checkpoint_dir.exists()


def test_checkpoint_resume_point_requires_contiguous_pipeline(tmp_path):
    manager = CheckpointManager(tmp_path)
    manager.save_checkpoint("export", {"done": True})

    assert manager.get_resume_point() is None


def test_checkpoint_manager_persists_failed_status(tmp_path):
    manager = CheckpointManager(tmp_path)

    manager.save_checkpoint(
        "writer",
        {"artifact_path": "artifacts/writer.md"},
        status="failed",
        error="missing heading",
    )

    info = manager.get_checkpoint_info("writer")
    raw = json.loads((manager.checkpoint_dir / "writer.json").read_text(encoding="utf-8"))

    assert info is not None
    assert info["status"] == "failed"
    assert info["error"] == "missing heading"
    assert raw["status"] == "failed"
    assert raw["error"] == "missing heading"


def test_progress_bar_rejects_zero_total_steps():
    with pytest.raises(ValueError):
        ProgressBar(0)


def test_progress_bar_failed_context_reports_failure(capsys):
    with pytest.raises(RuntimeError):
        with progress_bar(1, "테스트 진행") as bar:
            bar.update("1단계", "failed")
            raise RuntimeError("boom")

    output = capsys.readouterr().out
    assert "실패" in output
    assert "완료" not in output.splitlines()[-1]


def test_quality_evaluator_detects_problem_solving_question_type():
    evaluator = QualityEvaluator()

    score = evaluator.evaluate_draft(
        "문제를 분석하고 해결 방안을 실행해 결과적으로 처리 시간을 20% 줄였습니다.",
        "문제해결 경험을 말해주세요.",
    )

    assert not any("역량" in item for item in score.feedback)


def test_quality_evaluator_splits_korean_sentences_without_breaking_on_da():
    evaluator = QualityEvaluator()

    sentences = evaluator._split_sentences(
        "저는 데이터를 분석하다 보니 기준이 불명확하다고 판단했습니다. 그래서 정의를 다시 세웠습니다."
    )

    assert len(sentences) == 2


def test_feedback_history_does_not_mutate_internal_order(tmp_path):
    learner = FeedbackLearner(str(tmp_path))
    learner.record_feedback("d1", "pattern-a", True, 5)
    learner.record_feedback("d2", "pattern-b", False, 1)

    original_order = [item.draft_id for item in learner.db.feedback_history]
    history = learner.db.get_feedback_history()

    assert [item.draft_id for item in learner.db.feedback_history] == original_order
    assert [item.draft_id for item in history] == ["d2", "d1"]


def test_feedback_learner_prefers_matching_context(tmp_path):
    learner = FeedbackLearner(str(tmp_path))
    learner.record_feedback(
        "d1",
        "writer|공공|TYPE_A",
        True,
        5,
        artifact_type="writer",
        company_name="한국전력",
        job_title="데이터 분석",
        company_type="공공",
        question_types=["TYPE_A"],
        stage="writer",
        final_outcome="document_pass",
    )
    learner.record_feedback(
        "d2",
        "writer|스타트업|TYPE_A",
        False,
        1,
        artifact_type="writer",
        company_name="테스트랩",
        job_title="데이터 분석",
        company_type="스타트업",
        question_types=["TYPE_A"],
        stage="writer",
        final_outcome="document_fail",
    )

    recommendations = learner.get_recommendation(
        {
            "artifact_type": "writer",
            "company_name": "한국전력",
            "job_title": "데이터 분석",
            "company_type": "공공",
            "question_types": ["TYPE_A"],
            "stage": "writer",
        }
    )

    assert recommendations
    assert recommendations[0]["pattern_id"] == "writer|공공|TYPE_A"


def test_feedback_learner_summarizes_context_outcomes(tmp_path):
    learner = FeedbackLearner(str(tmp_path))
    learner.record_feedback(
        "d1",
        "writer|공공|TYPE_A",
        True,
        5,
        artifact_type="writer",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="pass",
    )
    learner.record_feedback(
        "d2",
        "writer|공공|TYPE_A",
        False,
        2,
        artifact_type="writer",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="fail_interview",
        rejection_reason="근거 부족",
    )

    summary = learner.get_context_outcome_summary(
        {
            "artifact_type": "writer",
            "company_type": "공공",
            "question_types": ["TYPE_A"],
        }
    )

    assert summary["matched_feedback_count"] == 2
    assert summary["outcome_breakdown"]["pass"] == 1
    assert summary["outcome_breakdown"]["fail_interview"] == 1
    assert summary["top_rejection_reasons"][0]["reason"] == "근거 부족"


def test_feedback_learner_summarizes_strategy_outcomes(tmp_path):
    learner = FeedbackLearner(str(tmp_path))
    learner.record_feedback(
        "d1",
        "coach|공공|TYPE_A",
        True,
        5,
        artifact_type="coach",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="pass",
        selected_experience_ids=["exp-strong"],
        question_experience_map=[
            {
                "question_id": "q1",
                "question_type": "TYPE_A",
                "experience_id": "exp-strong",
            }
        ],
    )
    learner.record_feedback(
        "d2",
        "coach|공공|TYPE_A",
        False,
        2,
        artifact_type="coach",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="fail_interview",
        rejection_reason="근거 부족",
        selected_experience_ids=["exp-weak"],
        question_experience_map=[
            {
                "question_id": "q1",
                "question_type": "TYPE_A",
                "experience_id": "exp-weak",
            }
        ],
    )

    summary = learner.get_strategy_outcome_summary(
        {
            "artifact_type": "coach",
            "company_type": "공공",
            "question_types": ["TYPE_A"],
        }
    )

    type_stats = summary["experience_stats_by_question_type"]["TYPE_A"]
    assert type_stats["exp-strong"]["pass_count"] == 1
    assert type_stats["exp-strong"]["pass_rate"] == 1.0
    assert type_stats["exp-weak"]["fail_count"] == 1
    assert (
        type_stats["exp-weak"]["pattern_breakdown"]["coach|공공|TYPE_A"]["fail_count"]
        == 1
    )


def test_feedback_learner_strategy_outcomes_include_weighted_scores(tmp_path):
    learner = FeedbackLearner(str(tmp_path))
    learner.record_feedback(
        "d1",
        "writer|공공|TYPE_A",
        True,
        5,
        artifact_type="writer",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="offer",
        selected_experience_ids=["exp-strong"],
        question_experience_map=[
            {
                "question_id": "q1",
                "question_type": "TYPE_A",
                "experience_id": "exp-strong",
            }
        ],
    )
    learner.record_feedback(
        "d2",
        "writer|공공|TYPE_A",
        False,
        2,
        artifact_type="writer",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="document_fail",
        rejection_reason="근거 부족",
        selected_experience_ids=["exp-strong"],
        question_experience_map=[
            {
                "question_id": "q1",
                "question_type": "TYPE_A",
                "experience_id": "exp-strong",
            }
        ],
    )

    summary = learner.get_strategy_outcome_summary(
        {
            "artifact_type": "writer",
            "company_type": "공공",
            "question_types": ["TYPE_A"],
        }
    )

    stats = summary["experience_stats_by_question_type"]["TYPE_A"]["exp-strong"]
    assert stats["weighted_pass_score"] > stats["weighted_fail_score"]
    assert stats["weighted_net_score"] > 0


def test_feedback_learner_learns_contextual_outcome_weights(tmp_path):
    learner = FeedbackLearner(str(tmp_path))
    learner.record_feedback(
        "d1",
        "writer|공공|TYPE_A",
        True,
        5,
        artifact_type="writer",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="offer",
    )
    learner.record_feedback(
        "d2",
        "writer|공공|TYPE_A",
        False,
        2,
        artifact_type="writer",
        company_type="공공",
        question_types=["TYPE_A"],
        final_outcome="fail_interview",
    )

    weights = learner.get_learned_outcome_weights(
        {
            "artifact_type": "writer",
            "company_type": "공공",
            "question_types": ["TYPE_A"],
        }
    )

    assert weights["offer"] > 4
    assert weights["fail_interview"] >= 3


def test_interactive_coach_handles_eof_gracefully(tmp_path, monkeypatch, capsys):
    workspace = Workspace(tmp_path)
    coach = InteractiveCoach(workspace)
    coach.experiences = [
        Experience(id="exp-1", title="테스트", organization="org", period_start="2024-01-01")
    ]

    monkeypatch.setattr(builtins, "input", lambda _: (_ for _ in ()).throw(EOFError))

    assert coach._select_experience() is None

    output = capsys.readouterr().out
    assert "취소" in output or "종료" in output


def test_interactive_history_is_bounded(tmp_path):
    workspace = Workspace(tmp_path)
    coach = InteractiveCoach(workspace, max_history=2)
    coach.experiences = []

    coach._save_history()
    coach._save_history()
    coach._save_history()

    assert len(coach.history) == 2


def test_interactive_coach_builds_socratic_questions_for_thin_experience(tmp_path):
    workspace = Workspace(tmp_path)
    coach = InteractiveCoach(workspace)
    experience = Experience(
        id="exp-1",
        title="민원 응대",
        organization="기관",
        period_start="2024-01-01",
        situation="민원인이 제도를 이해하지 못함",
        task="설명 필요",
        action="제도를 안내함",
        result="처리 완료",
    )

    questions = coach._build_socratic_questions(experience)

    assert len(questions) == 3
    assert questions[0].startswith("[사실]")
    assert questions[1].startswith("[판단]")
    assert questions[2].startswith("[가치관]")


def test_interactive_coach_builds_candidate_profile(tmp_path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    initialize_state(workspace)
    coach = InteractiveCoach(workspace)
    coach.experiences = [
        Experience(
            id="exp-1",
            title="민원 응대 개선",
            organization="기관",
            period_start="2024-01-01",
            situation="반복 민원이 많았습니다.",
            task="응대 기준을 정리해야 했습니다.",
            action="응대 문안과 기준표를 만들었습니다.",
            result="안내 시간이 줄었습니다.",
            personal_contribution="기준표 초안을 직접 만들고 수정했습니다.",
            metrics="반복 문의 12건 정리",
            tags=["민원", "문서화", "개선"],
        )
    ]

    profile = coach._build_candidate_profile()

    assert profile["communication_style"] in {"logical", "balanced", "relational"}
    assert any("민원" in item for item in profile["signature_strengths"])
    assert profile["profile_summary"]


def test_mock_interview_selects_follow_up_from_pressure_themes(tmp_path):
    workspace = Workspace(tmp_path)
    coach = MockInterviewCoach(workspace, mode="hard")
    coach.strategy_pack = {"interview_pressure_themes": ["수치 검증"]}

    selected = coach._select_follow_up_question(
        [
            "그 성과를 수치로 표현한다면 어떻게 설명하시겠어요?",
            "팀 프로젝트에서 본인만의 기여도를 퍼센트로 표현한다면?",
        ],
        pressure_level=3,
    )

    assert "수치" in selected


def test_mock_interview_rotates_committee_personas(tmp_path):
    workspace = Workspace(tmp_path)
    coach = MockInterviewCoach(workspace, mode="hard")
    coach.committee_personas = [
        {"name": "위원장"},
        {"name": "실무위원"},
        {"name": "리스크위원"},
    ]

    coach.current_question_index = 1
    selected = coach._select_committee_persona()

    assert selected["name"] == "실무위원"


def test_mock_interview_selects_multiple_panel_personas(tmp_path):
    workspace = Workspace(tmp_path)
    coach = MockInterviewCoach(workspace, mode="hard")
    coach.committee_personas = [
        {"name": "위원장"},
        {"name": "실무위원"},
        {"name": "리스크위원"},
    ]

    personas = coach._select_panel_personas(pressure_level=3)

    assert [item["name"] for item in personas] == ["위원장", "실무위원", "리스크위원"]


def test_mock_interview_prepares_questions_with_llm_fallback(tmp_path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    initialize_state(workspace)
    project = ApplicationProject(
        company_name="테스트공사",
        job_title="사무행정",
        questions=[
            Question(
                id="q1",
                order_no=1,
                question_text="우리 기관에서 일하고 싶은 이유와 잘할 수 있는 점을 함께 설명하세요.",
                detected_type=QuestionType.TYPE_UNKNOWN,
            )
        ],
    )
    save_project(workspace, project)
    coach = MockInterviewCoach(workspace, mode="hard")
    coach.project = project

    with patch(
        "resume_agent.pipeline.classify_project_questions_with_llm_fallback",
        side_effect=lambda ws, p, **kwargs: ApplicationProject.model_validate(
            {
                **p.model_dump(),
                "questions": [
                    {
                        **p.questions[0].model_dump(),
                        "detected_type": "TYPE_A",
                    }
                ],
            }
        ),
    ):
        coach._prepare_project_questions()

    assert coach.questions[0].detected_type == QuestionType.TYPE_A


def test_interview_engine_builds_committee_rounds():
    rounds = _build_committee_rounds(
        [
            {"name": "위원장", "focus": ["논리 일관성"]},
            {"name": "실무위원", "focus": ["직무 적합성"]},
            {"name": "리스크위원", "focus": ["반례 검증"]},
        ],
        0,
        "그 성과를 수치로 표현한다면 어떻게 설명하시겠어요?",
    )

    assert len(rounds) == 3
    assert rounds[0]["persona"] == "위원장"
    assert rounds[1]["persona"] == "실무위원"


def test_score_experience_uses_runtime_config(monkeypatch):
    config_values = {
        "scoring.verified_bonus": 11,
        "scoring.unverified_penalty": -5,
        "scoring.reuse_penalty": 13,
        "scoring.same_org_penalty": 17,
    }

    monkeypatch.setattr(
        scoring,
        "get_config_value",
        lambda key, default=None: config_values.get(key, default),
    )
    monkeypatch.setattr(scoring, "extract_question_keywords", lambda _: [])
    monkeypatch.setattr(scoring, "classify_question", lambda _: "TYPE_UNKNOWN")

    question = Question(id="q1", order_no=1, question_text="협업 경험을 말해주세요.")
    experience = Experience(
        id="exp-1",
        title="협업 경험",
        organization="테스트기관",
        period_start="2024-01-01",
        situation="상황",
        task="과제",
        action="조치",
        result="결과",
        evidence_level=scoring.EvidenceLevel.L1,
        verification_status=VerificationStatus.VERIFIED,
    )

    detail = scoring.score_experience(
        question,
        experience,
        priority_order=[],
        already_used=["exp-1"],
        previous_organization="테스트기관",
    )

    assert detail["score"] == -18


def test_vector_store_prefers_relevant_document_for_simple_query(tmp_path):
    store = SimpleVectorStore(str(tmp_path))
    store.add_document("안녕하세요 성과 10%", {"label": "relevant"}, doc_id="relevant")
    store.add_document("테스트 문장", {"label": "irrelevant"}, doc_id="irrelevant")

    results = store.search("성과", n_results=2, min_similarity=0.0)

    assert results[0]["id"] == "relevant"


def test_answer_quality_penalizes_ai_style_phrases():
    repetitive = (
        "이러한 경험을 통해 협업의 중요성을 배웠습니다. "
        "이를 바탕으로 팀과 소통했습니다. "
        "앞으로도 기여하겠습니다."
    )
    concrete = (
        "야간 민원 응대 기준이 없어 문의가 길어졌습니다. "
        "저는 응답 문안을 다시 정리해 3분 내 안내가 가능하도록 바꿨고, "
        "반복 문의 메모 12건을 한 장으로 묶었습니다."
    )

    assert calculate_originality(concrete) > calculate_originality(repetitive)


def test_defense_simulator_adds_pressure_questions_for_weak_answer():
    simulator = DefenseSimulator()
    simulation = simulator.simulate(
        primary_question="협업 경험을 설명해 주세요.",
        answer="팀이 함께 프로젝트를 진행했고 잘 마무리했습니다.",
        question_type=QuestionType.TYPE_C,
    )

    assert any("본인 지분" in item or "산출 기준" in item for item in simulation.follow_up_questions)
    assert any("기준" in item or "측정" in item for item in simulation.defense_points)
