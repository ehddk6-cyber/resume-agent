from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from resume_agent.models import EvidenceLevel, Experience, QuestionType, VerificationStatus


@pytest.fixture(autouse=True)
def _stub_sentence_transformers():
    module = types.ModuleType("sentence_transformers")

    class _SentenceTransformer:
        def __init__(self, *_args, **_kwargs):
            pass

        def encode(self, _text, normalize_embeddings=True):
            return [0.1, 0.2, 0.3]

    module.SentenceTransformer = _SentenceTransformer
    original = sys.modules.get("sentence_transformers")
    sys.modules["sentence_transformers"] = module
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop("sentence_transformers", None)
        else:
            sys.modules["sentence_transformers"] = original


def _workspace(tmp_path: Path) -> SimpleNamespace:
    analysis_dir = tmp_path / "analysis"
    state_dir = tmp_path / "state"
    root = tmp_path / "root"
    analysis_dir.mkdir()
    state_dir.mkdir()
    (root / "kb" / "feedback").mkdir(parents=True)
    return SimpleNamespace(
        root=root,
        analysis_dir=analysis_dir,
        state_dir=state_dir,
    )


def _experience(**overrides) -> Experience:
    data = {
        "id": "exp-1",
        "title": "민원 시스템 개선",
        "organization": "테스트기관",
        "period_start": "2024-01",
        "situation": "민원 처리 지연과 문의 증가로 현장 혼선이 커졌습니다.",
        "task": "처리 흐름을 정리하고 응대 품질을 높이는 역할을 맡았습니다.",
        "action": "데이터를 분석하고 민원 유형을 재분류한 뒤 응대 스크립트와 대시보드를 정비했습니다.",
        "result": "평균 처리 시간이 30% 단축되었습니다.",
        "personal_contribution": "분석 기준 수립과 현장 조율을 맡았습니다.",
        "metrics": "30% 단축",
        "tags": ["민원", "개선"],
        "evidence_level": EvidenceLevel.L3,
        "verification_status": VerificationStatus.VERIFIED,
    }
    data.update(overrides)
    return Experience(**data)


def _question(order_no: int = 1, text: str = "지원 동기를 말씀해 주세요."):
    return SimpleNamespace(
        order_no=order_no,
        question_text=text,
        detected_type=QuestionType.TYPE_A,
    )


@dataclass
class _Simulation:
    risk_areas: list[str]
    defense_points: list[str]
    improvement_suggestions: list[str]
    follow_up_questions: list[str]


class TestInteractiveCoachCoverage:
    def test_run_handles_unknown_help_and_eof(self, tmp_path: Path):
        from resume_agent.interactive import InteractiveCoach

        ws = _workspace(tmp_path)
        coach = InteractiveCoach(ws)

        with patch("resume_agent.interactive.load_experiences", return_value=[_experience()]):
            with patch.object(
                coach,
                "_build_candidate_profile",
                return_value={"profile_summary": "테스트 요약"},
            ):
                with patch.object(coach, "_show_help") as show_help:
                    with patch.object(coach, "_list_experiences") as list_experiences:
                        with patch.object(
                            coach,
                            "_safe_input",
                            side_effect=["weird", "h", "l", None],
                        ):
                            coach.run()

        show_help.assert_called_once()
        list_experiences.assert_called_once()

    def test_show_suggestion_branches(self, tmp_path: Path):
        from resume_agent.interactive import InteractiveCoach

        ws = _workspace(tmp_path)
        coach = InteractiveCoach(ws)
        coach.experiences = [_experience()]

        with patch.object(coach, "_select_experience", return_value=0):
            with patch.object(coach, "_run_socratic_loop"):
                with patch.object(coach, "_generate_suggestions", return_value=[]):
                    coach._show_suggestion()

        suggestion = SimpleNamespace(
            id="star_result",
            category="STAR",
            title="결과 설명 보강",
            content="성과 수치를 더 자세히 적으세요.",
            priority="high",
        )
        with patch.object(coach, "_select_experience", return_value=0):
            with patch.object(coach, "_run_socratic_loop"):
                with patch.object(coach, "_generate_suggestions", return_value=[suggestion]):
                    with patch.object(coach, "_safe_input", return_value="9"):
                        coach._show_suggestion()
        with patch.object(coach, "_select_experience", return_value=0):
            with patch.object(coach, "_run_socratic_loop"):
                with patch.object(coach, "_generate_suggestions", return_value=[suggestion]):
                    with patch.object(coach, "_safe_input", return_value="abc"):
                        coach._show_suggestion()

    def test_edit_and_select_experience_error_paths(self, tmp_path: Path):
        from resume_agent.interactive import InteractiveCoach

        ws = _workspace(tmp_path)
        coach = InteractiveCoach(ws)
        coach.experiences = [_experience()]

        with patch.object(coach, "_safe_input", side_effect=["bad"]):
            assert coach._select_experience() is None
        with patch.object(coach, "_safe_input", side_effect=[None]):
            assert coach._select_experience() is None

        with patch.object(coach, "_select_experience", return_value=0):
            with patch.object(coach, "_safe_input", side_effect=["9"]):
                coach._edit_experience()
        with patch.object(coach, "_select_experience", return_value=0):
            with patch.object(coach, "_safe_input", side_effect=["0"]):
                coach._edit_experience()

    def test_run_socratic_loop_stops_on_eof(self, tmp_path: Path):
        from resume_agent.interactive import InteractiveCoach

        ws = _workspace(tmp_path)
        coach = InteractiveCoach(ws)
        experience = _experience()

        with patch.object(coach, "_safe_input", side_effect=[None]):
            coach._run_socratic_loop(experience)


class TestMockInterviewCoachCoverage:
    def test_prepare_context_success_and_error(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws)
        coach.experiences = [_experience()]
        coach.project = SimpleNamespace(
            company_name="테스트기관",
            job_title="분석가",
            company_type="public",
            questions=[_question()],
        )
        (ws.analysis_dir / "question_map.json").write_text("[]", encoding="utf-8")
        (ws.analysis_dir / "source_grading.json").write_text("{}", encoding="utf-8")
        (ws.analysis_dir / "application_strategy.json").write_text(
            json.dumps({"interview_pressure_points": ["근거"], "self_intro_candidates": {"expected_follow_ups": ["왜 우리 기관인가요?"]}}, ensure_ascii=False),
            encoding="utf-8",
        )

        learner = SimpleNamespace(
            get_recommendation=lambda _payload: ["추천1", "추천2", "추천3", "추천4"],
            get_context_outcome_summary=lambda _payload: "요약",
            db=SimpleNamespace(
                get_feedback_history=lambda limit=20: [
                    SimpleNamespace(artifact_type="interview", comment="코멘트1"),
                    SimpleNamespace(artifact_type="other", comment="무시"),
                    SimpleNamespace(artifact_type="interview", comment="코멘트2"),
                ]
            ),
        )

        with patch("resume_agent.interactive.analyze_company", return_value=SimpleNamespace()):
            with patch(
                "resume_agent.interactive.build_role_industry_strategy_from_project",
                return_value={"committee_personas": [{"name": "위원장", "focus": ["논리"]}]},
            ):
                with patch("resume_agent.interactive.create_feedback_learner", return_value=learner):
                    coach._prepare_context()

        assert coach.company_analysis is not None
        assert coach.feedback_learning["recommendations"] == ["추천1", "추천2", "추천3"]
        assert coach.committee_personas[0]["name"] == "위원장"
        assert coach.application_strategy["interview_pressure_points"] == ["근거"]

        coach.company_analysis = "sentinel"
        with patch("resume_agent.interactive.analyze_company", side_effect=RuntimeError("boom")):
            with patch("resume_agent.interactive.create_feedback_learner", return_value=learner):
                coach._prepare_context()
        assert coach.company_analysis is None

    def test_prepare_project_questions_fallback(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws)
        coach.project = SimpleNamespace(questions=[_question(text="협업 경험을 말씀해 주세요.")])

        with patch(
            "resume_agent.interactive.classify_project_questions_with_llm_fallback",
            side_effect=RuntimeError("fallback"),
            create=True,
        ):
            coach._prepare_project_questions()

        assert coach.questions
        assert coach.project.questions[0].detected_type == QuestionType.TYPE_C

    def test_committee_rounds_and_summary(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws)

        with patch.object(
            coach,
            "_safe_input",
            side_effect=["", "위원 답변입니다."],
        ):
            with patch.object(
                coach,
                "_provide_follow_up_feedback",
                return_value=SimpleNamespace(
                    risk_areas=["구체성 부족"],
                    defense_points=["수치로 다시 설명"],
                ),
            ):
                rounds = coach._run_committee_rounds(
                    question_type=QuestionType.TYPE_A,
                    follow_up_questions=["추가 질문 1", "추가 질문 2"],
                    panel_personas=[
                        {"name": "메인", "focus": ["전략"]},
                        {"name": "실무", "focus": ["구체성"]},
                        {"name": "임원", "focus": ["책임"]},
                    ],
                )

        assert rounds[0]["risk_areas"] == ["답변 생략"]
        assert rounds[1]["defense_points"] == ["수치로 다시 설명"]

        summary = coach._summarize_committee_rounds(["위험1", "위험2", "위험3"], rounds)
        assert summary["verdict"] == "fail"

        with patch("builtins.print") as mock_print:
            coach._print_committee_summary(summary)
        assert mock_print.called

    def test_save_session_load_json_and_show_summary(self, tmp_path: Path):
        from resume_agent.interactive import InterviewTurn, MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws)
        session_path = ws.state_dir / "interview_sessions.json"
        session_path.write_text("{invalid", encoding="utf-8")
        broken_path = ws.analysis_dir / "broken.json"
        broken_path.write_text("{invalid", encoding="utf-8")
        coach.application_strategy = {
            "self_intro_candidates": {"expected_follow_ups": ["왜 우리 기관인가요?"]}
        }

        turn = InterviewTurn(
            question="질문",
            answer="답변",
            question_type=QuestionType.TYPE_B,
            interviewer_persona="위원장",
            risk_areas=["근거 부족", "수치 부족"],
            committee_rounds=[{"persona": "실무", "risk_areas": ["추가 위험"]}],
            committee_summary={"verdict": "borderline", "total_risk_count": 3},
        )
        coach.turns = [turn]

        assert coach._load_json(broken_path, {"fallback": True}) == {"fallback": True}

        coach._save_session()
        saved = json.loads(session_path.read_text(encoding="utf-8"))
        assert saved[0]["turns"][0]["question_type"] == QuestionType.TYPE_B.value
        assert "interviewer_profile" in saved[0]["turns"][0]
        assert saved[0]["training_focus"]
        assert "growth_snapshot" in saved[0]

        with patch("builtins.print") as mock_print:
            coach._show_summary()
        assert mock_print.called

        with patch("builtins.print") as mock_print:
            coach._print_committee_summary(
                {"verdict": "borderline", "total_risk_count": 3},
                {
                    "verification_style": "압박 검증형",
                    "scenario_brief": "핵심 근거와 기관 적합성을 함께 검증합니다.",
                },
            )
        printed = " ".join(" ".join(map(str, call.args)) for call in mock_print.call_args_list)
        assert "압박 검증형" in printed
        assert "기관 적합성" in printed

    def test_retry_guidance_and_growth_snapshot(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws)
        coach.turns = [
            SimpleNamespace(
                risk_areas=["근거 부족"],
                follow_up_risk_areas=["개인 기여 부족"],
            )
        ]
        previous_sessions = [
            {
                "turns": [
                    {"risk_areas": ["근거 부족", "수치 부족"], "follow_up_risk_areas": []}
                ]
            }
        ]

        guidance = coach._build_retry_guidance(["근거 부족"], QuestionType.TYPE_A)
        growth = coach._build_growth_snapshot(previous_sessions)

        assert any("숫자" in item or "근거" in item for item in guidance)
        assert growth["trend"] in {"improving", "stable", "regressing"}

    def test_training_focus_includes_feedback_adaptation_actions(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws)
        coach.feedback_learning = {
            "adaptation_plan": {
                "focus_actions": ["반복 탈락 사유 '근거 부족' 보강"]
            }
        }

        focus = coach._build_training_focus()

        assert any("학습 루프 우선 과제" in item for item in focus)

    def test_build_interviewer_profile_reflects_pressure_and_strategy(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws, mode="hard")
        coach.application_strategy = {
            "adaptive_strategy_layer": {
                "interview_mode": "압박형 검증 + 협업/우선순위 판단 확인"
            },
            "interview_pressure_points": ["왜 우리 기관인가요?"],
        }

        profile = coach._build_interviewer_profile(
            {"name": "실무위원", "focus": ["구체성", "판단 기준"]},
            QuestionType.TYPE_A,
            3,
        )

        assert profile["verification_style"] == "압박 검증형"
        assert profile["focus_prompt"] == "구체성, 판단 기준"
        assert profile["pressure_theme"] == "왜 우리 기관인가요?"
        assert "기관 적합성" in profile["scenario_brief"]

    def test_select_follow_up_question_respects_interviewer_profile(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws, mode="hard")

        selected = coach._select_follow_up_question(
            [
                "지원동기를 한 문장으로 다시 압축해보시겠어요?",
                "수치로 성과를 다시 설명해보시겠어요?",
            ],
            pressure_level=2,
            interviewer_profile={
                "scenario_brief": "지원동기의 진정성과 기관 적합성을 교차 검증합니다.",
                "verification_style": "동기·적합성 검증형",
                "focus_prompt": "구체성",
                "pressure_theme": "",
            },
        )

        assert "지원동기" in selected


class TestSelfIntroDrillCoverage:
    def test_run_self_intro_drill_saves_attempt(self, tmp_path: Path):
        from resume_agent.interactive import SelfIntroDrillCoach

        ws = _workspace(tmp_path)
        (ws.analysis_dir / "application_strategy.json").write_text(
            json.dumps(
                {
                    "self_intro_candidates": {
                        "opening_hook": "기관 가치와 맞닿은 경험이 있습니다.",
                        "top001_versions": {"30s": "30초 버전"},
                        "expected_follow_ups": ["왜 우리 기관인가요?"],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        coach = SelfIntroDrillCoach(ws)

        with patch.object(
            coach,
            "_safe_input",
            return_value="저는 직접 데이터를 정리해 처리 시간을 20% 줄인 경험이 있습니다.",
        ):
            coach.run()

        saved = json.loads((ws.state_dir / "self_intro_drills.json").read_text(encoding="utf-8"))
        assert saved[0]["score"] > 0
        assert saved[0]["expected_follow_ups"] == ["왜 우리 기관인가요?"]

    def test_run_happy_path_and_retry(self, tmp_path: Path):
        from resume_agent.interactive import MockInterviewCoach

        ws = _workspace(tmp_path)
        coach = MockInterviewCoach(ws, mode="hard")
        coach.experiences = [_experience()]
        coach.project = SimpleNamespace(
            company_name="테스트기관",
            job_title="분석가",
            company_type="public",
            questions=[_question()],
        )
        coach.questions = coach.project.questions
        coach.committee_personas = [
            {"name": "위원장", "focus": ["전략"]},
            {"name": "실무", "focus": ["구체성"]},
        ]
        coach.strategy_pack = {
            "single_source_risks": ["검증 부족"],
            "interview_pressure_themes": ["사실"],
        }

        with patch("resume_agent.interactive.load_experiences", return_value=[_experience()]):
            with patch("resume_agent.interactive.load_project", return_value=coach.project):
                with patch.object(coach, "_prepare_project_questions"):
                    with patch.object(coach, "_prepare_context"):
                        with patch.object(
                            coach,
                            "_provide_feedback",
                            return_value=_Simulation(
                                risk_areas=["구조 부족", "근거 부족"],
                                defense_points=["STAR로 재정리"],
                                improvement_suggestions=["핵심 먼저 제시"],
                                follow_up_questions=["[사실] 수치를 포함해 다시 설명해보세요."],
                            ),
                        ):
                            with patch.object(
                                coach,
                                "_provide_follow_up_feedback",
                                return_value=SimpleNamespace(
                                    risk_areas=["보완 필요"],
                                    defense_points=["비교 기준 명시"],
                                    follow_up_questions=[],
                                ),
                            ):
                                with patch.object(coach, "_run_committee_rounds", return_value=[]):
                                    with patch.object(coach, "_save_session") as save_session:
                                        with patch.object(coach, "_show_summary") as show_summary:
                                            with patch.object(
                                                coach,
                                                "_safe_input",
                                                side_effect=[
                                                    "첫 답변입니다.",
                                                    "꼬리 답변입니다.",
                                                    "n",
                                                ],
                                            ):
                                                coach.run()

        assert len(coach.turns) == 1
        assert coach.turns[0].follow_up_question.startswith("[사실]")
        save_session.assert_called_once()
        show_summary.assert_called_once()
