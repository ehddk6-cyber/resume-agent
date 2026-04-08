from __future__ import annotations

import pytest
from resume_agent.top001 import (
    LogicalStructureAnalyzer,
    DeepInterrogator,
    AdaptivePersonaEngine,
    AdaptiveCoachEngine,
    SelfIntroMastery,
    StrategicResearchTranslator,
    EvidenceChainValidator,
    Top001InterviewEngine,
    Top001CoachEngine,
    Top001ResearchTranslator,
    AnswerStyle,
    VulnerableLink,
    CoachingState,
)


class TestLogicalStructureAnalyzer:
    def setup_method(self):
        self.analyzer = LogicalStructureAnalyzer()

    def test_parse_simple_answer(self):
        answer = "저는 팀의 업무 효율을 30% 향상시켰습니다. 자동화 스크립트를 도입했기 때문입니다."
        graph = self.analyzer.parse(answer)
        assert graph is not None
        assert len(graph.nodes) >= 2
        assert graph.root_claim is not None

    def test_identify_vulnerable_links_no_evidence(self):
        answer = "저는 열심히 일했습니다."
        graph = self.analyzer.parse(answer)
        vulnerabilities = self.analyzer.identify_vulnerable_links(graph)
        assert len(vulnerabilities) > 0

    def test_identify_vulnerable_links_with_metric(self):
        answer = "저는 팀의 업무 효율을 30% 향상시켰습니다."
        graph = self.analyzer.parse(answer)
        vulnerabilities = self.analyzer.identify_vulnerable_links(graph)
        assert any(
            v.vulnerability_type == "unverified_metrics" for v in vulnerabilities
        )

    def test_identify_vulnerable_links_vague_attribution(self):
        answer = "우리 팀은 좋은 결과를 달성했습니다."
        graph = self.analyzer.parse(answer)
        vulnerabilities = self.analyzer.identify_vulnerable_links(graph)
        assert any(
            v.vulnerability_type == "unclear_attribution" for v in vulnerabilities
        )

    def test_calculate_confidence_score(self):
        answer = "저는 고객 만족도를 95% 향상시켰습니다. 설문조사를 통해 측정했습니다."
        graph = self.analyzer.parse(answer)
        score = self.analyzer.calculate_confidence_score(graph)
        assert 0.0 <= score <= 1.0
        assert score > 0.5


class TestDeepInterrogator:
    def setup_method(self):
        self.interrogator = DeepInterrogator()

    def test_build_question_chain_insufficient_evidence(self):
        vuln = VulnerableLink(
            source_id="n1",
            target_id="",
            link_type="none",
            vulnerability_type="insufficient_evidence",
            severity="high",
            description="주장에 근거가 없습니다",
            attack_vectors=[],
        )
        chain = self.interrogator.build_question_chain(vuln)
        assert chain is not None
        assert len(chain.depth_1_questions) > 0
        assert len(chain.depth_2_questions) > 0
        assert len(chain.depth_3_questions) > 0

    def test_build_question_chain_unclear_attribution(self):
        vuln = VulnerableLink(
            source_id="n1",
            target_id="",
            link_type="vague",
            vulnerability_type="unclear_attribution",
            severity="high",
            description="개인 기여가 불분명합니다",
            attack_vectors=[],
        )
        chain = self.interrogator.build_question_chain(vuln)
        assert chain.primary_question is not None

    def test_generate_depth_questions(self):
        result = self.interrogator.generate_depth_questions(
            "unverified_metrics", "30% 향상시켰습니다"
        )
        assert "depth_1" in result
        assert "depth_2" in result
        assert "depth_3" in result

    def test_validate_chain_valid(self):
        from resume_agent.top001.base_types import QuestionChain

        chain = QuestionChain(
            primary_question="테스트",
            depth_1_questions=["Q1"],
            depth_2_questions=["Q2"],
            depth_3_questions=["Q3"],
            attack_vectors=[],
        )
        assert self.interrogator.validate_chain(chain) is True

    def test_validate_chain_invalid_empty(self):
        from resume_agent.top001.base_types import QuestionChain

        chain = QuestionChain(
            primary_question="테스트",
            depth_1_questions=[],
            depth_2_questions=[],
            depth_3_questions=[],
            attack_vectors=[],
        )
        assert self.interrogator.validate_chain(chain) is False


class TestAdaptivePersonaEngine:
    def setup_method(self):
        self.engine = AdaptivePersonaEngine()

    def test_classify_answer_style_evasive(self):
        answer = "저는 다양한 경험을 했습니다. 여러 분야에서等活动했습니다."
        style = self.engine.classify_answer_style(answer)
        assert style == AnswerStyle.EVASIVE

    def test_classify_answer_style_balanced(self):
        answer = "저는 2023년 고객 만족도를 30% 향상시켰습니다. 설문조사를 통해 측정했습니다."
        style = self.engine.classify_answer_style(answer)
        assert style in [
            AnswerStyle.BALANCED,
            AnswerStyle.OVERSTATED,
            AnswerStyle.FRAGMENTED,
        ]

    def test_select_persona_evasive(self):
        persona = self.engine.select_persona(AnswerStyle.EVASIVE, 1)
        assert persona.id == "specificity_inspector"
        assert persona.aggression_level >= 5

    def test_select_persona_overstated(self):
        persona = self.engine.select_persona(AnswerStyle.OVERSTATED, 1)
        assert persona.id == "exaggeration_hunter"
        assert persona.aggression_level >= 7

    def test_escalate_pressure(self):
        pressure = self.engine.escalate_pressure(turn=3, weak_response=True)
        assert pressure >= 5
        assert pressure <= 10

    def test_rotate_focus_area(self):
        personas = []
        area = self.engine.rotate_focus_area(personas, "수량 검증")
        assert area in [
            "수량 검증",
            "역할 검증",
            "인과성 검증",
            "대안 검증",
            "일관성 검증",
        ]


class TestAdaptiveCoachEngine:
    def setup_method(self):
        self.coach = AdaptiveCoachEngine()

    def test_diagnose_user_state_no_experiences(self):
        state = self.coach.diagnose_user_state([], [])
        assert state == CoachingState.RAPPORT

    def test_provide_realtime_feedback_specific(self):
        answer = "저는 30% 효율을 향상시켰습니다."
        feedback = self.coach.provide_realtime_feedback(answer)
        assert len(feedback.strength_points) > 0 or len(feedback.improvement_areas) > 0

    def test_provide_realtime_feedback_vague(self):
        answer = "저는 열심히 일했습니다."
        feedback = self.coach.provide_realtime_feedback(answer)
        assert len(feedback.improvement_areas) > 0

    def test_create_progressive_plan(self):
        plan = self.coach.create_progressive_plan([], [])
        assert len(plan) == 4
        assert plan[0]["session"] == 1


class TestSelfIntroMastery:
    def setup_method(self):
        self.mastery = SelfIntroMastery()

    def test_provide_delivery_feedback_short(self):
        intro = "저는 일했습니다."
        feedback = self.mastery.provide_delivery_feedback(intro)
        assert "score" in feedback
        assert feedback["score"] < 0.7

    def test_provide_delivery_feedback_good(self):
        intro = "저는 2023년 고객 만족도를 30% 향상시켰습니다. 설문조사 결과입니다."
        feedback = self.mastery.provide_delivery_feedback(intro)
        assert "score" in feedback

    def test_add_practice_iteration(self):
        self.mastery.add_practice_iteration(
            version="30s",
            content="테스트 내용",
            feedback="좋습니다",
            score=0.8,
        )
        summary = self.mastery.get_practice_summary()
        assert summary["total_practices"] == 1
        assert summary["best_score"] == 0.8


class TestEvidenceChainValidator:
    def setup_method(self):
        self.validator = EvidenceChainValidator()

    def test_validate_temporal_consistency_empty(self):
        result = self.validator.validate_temporal_consistency([])
        assert result == []

    def test_validate_cross_question_allocation_empty(self):
        result = self.validator.validate_cross_question_allocation([], [])
        assert result == []

    def test_suggest_experience_additions_empty(self):
        result = self.validator.suggest_experience_additions([], [], [])
        assert len(result) > 0

    def test_get_coverage_report(self):
        report = self.validator.get_coverage_report([], [], [])
        assert "coverage_rate" in report


class TestTop001Integrators:
    def setup_method(self):
        self.interview_engine = Top001InterviewEngine()
        self.coach_engine = Top001CoachEngine()
        self.research_engine = Top001ResearchTranslator()

    def test_simulate_interview(self):
        result = self.interview_engine.simulate_interview(
            question="경험을 말씀해 주세요",
            answer="저는 고객 만족도를 30% 향상시켰습니다.",
            experience=None,
            company_analysis=None,
        )
        assert "confidence_score" in result
        assert "vulnerabilities" in result
        assert "answer_style" in result

    def test_coach_realtime(self):
        feedback = self.coach_engine.coach_realtime("저는 30% 효율을 향상시켰습니다.")
        assert feedback is not None

    def test_analyze_experiences_empty(self):
        result = self.coach_engine.analyze_experiences([], [], [])
        assert "coaching_state" in result
        assert "suggestions" in result

    def test_generate_self_intro_pack_empty(self):
        result = self.coach_engine.generate_self_intro_pack([], "", "")
        assert "hooks" in result
        assert "versions" in result

    def test_translate_research_to_strategy(self):
        result = self.research_engine.translate_research_to_strategy(None, [], [])
        assert "strategic_signals" in result
        assert "question_hooks" in result
        assert "defense_strategies" in result
