import builtins
from pathlib import Path

import pytest

from resume_agent.checkpoint import CheckpointManager
from resume_agent.feedback_learner import FeedbackLearner
from resume_agent.interactive import InteractiveCoach
from resume_agent.models import Experience
from resume_agent.progress import ProgressBar, progress_bar
from resume_agent.quality_evaluator import QualityEvaluator
from resume_agent.vector_store import SimpleVectorStore
from resume_agent.workspace import Workspace


def test_checkpoint_manager_creates_nested_directories(tmp_path):
    nested_workspace = tmp_path / "missing" / "workspace"
    manager = CheckpointManager(nested_workspace)

    assert manager.checkpoint_dir.exists()


def test_checkpoint_resume_point_requires_contiguous_pipeline(tmp_path):
    manager = CheckpointManager(tmp_path)
    manager.save_checkpoint("export", {"done": True})

    assert manager.get_resume_point() is None


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


def test_vector_store_prefers_relevant_document_for_simple_query(tmp_path):
    store = SimpleVectorStore(str(tmp_path))
    store.add_document("안녕하세요 성과 10%", {"label": "relevant"}, doc_id="relevant")
    store.add_document("테스트 문장", {"label": "irrelevant"}, doc_id="irrelevant")

    results = store.search("성과", n_results=2, min_similarity=0.0)

    assert results[0]["id"] == "relevant"
