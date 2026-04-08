"""
Top 0.01% Unified Interview & Coaching Engine

기존 파이프라인과 신규 모듈을 통합하는 핵심 엔진.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Experience, Question, ApplicationProject, CompanyAnalysis
    from .base_types import (
        AnswerStyle,
        CoachingFeedback,
        InterviewPersona,
        LogicalGraph,
        QuestionChain,
        StrategicSignals,
    )


class Top001InterviewEngine:
    """상위 0.01% 면접 시뮬레이션 엔진"""

    def __init__(self):
        from .logical_analyzer import LogicalStructureAnalyzer
        from .deep_interrogator import DeepInterrogator
        from .adaptive_persona import AdaptivePersonaEngine

        self.analyzer = LogicalStructureAnalyzer()
        self.interrogator = DeepInterrogator()
        self.persona_engine = AdaptivePersonaEngine()

    def simulate_interview(
        self,
        question: str,
        answer: str,
        experience: Any,
        company_analysis: Any,
        turn: int = 1,
    ) -> Dict[str, Any]:
        graph = self.analyzer.parse(answer)
        vulnerabilities = self.analyzer.identify_vulnerable_links(graph)
        confidence = self.analyzer.calculate_confidence_score(graph)
        style = self.persona_engine.classify_answer_style(answer)
        persona = self.persona_engine.select_persona(style, turn)
        pressure = self.persona_engine.escalate_pressure(turn, len(vulnerabilities) > 1)

        chains = []
        for vuln in vulnerabilities[:3]:
            chain = self.interrogator.build_question_chain(vuln)
            if self.interrogator.validate_chain(chain):
                chains.append(chain)

        weak_response = confidence < 0.6 or len(vulnerabilities) > 1

        return {
            "logical_graph": graph,
            "confidence_score": confidence,
            "vulnerabilities": vulnerabilities,
            "answer_style": style.value if hasattr(style, "value") else str(style),
            "persona": persona,
            "pressure_level": pressure,
            "question_chains": chains,
            "weak_response": weak_response,
            "recommendations": self._generate_recommendations(
                vulnerabilities, confidence
            ),
        }

    def _generate_recommendations(
        self,
        vulnerabilities: List[Any],
        confidence: float,
    ) -> List[str]:
        recs = []
        if confidence < 0.6:
            recs.append("근거 보강이 필요합니다. 구체적 사실과 수치를 추가하세요.")
        for v in vulnerabilities:
            v_type = getattr(v, "vulnerability_type", "")
            if v_type == "unclear_attribution":
                recs.append("개인 기여와 팀 성과를 구분하여 설명하세요.")
            elif v_type == "unverified_metrics":
                recs.append("수치의 산출 근거와 측정 방법을 준비하세요.")
            elif v_type == "insufficient_evidence":
                recs.append("주장에 대한 구체적 근거를 추가하세요.")
        return list(dict.fromkeys(recs))


class Top001CoachEngine:
    """상위 0.01% 코칭 엔진"""

    def __init__(self):
        from .adaptive_coach import AdaptiveCoachEngine
        from .self_intro_mastery import SelfIntroMastery
        from .evidence_chain import EvidenceChainValidator

        self.coach = AdaptiveCoachEngine()
        self.self_intro = SelfIntroMastery()
        self.evidence = EvidenceChainValidator()

    def analyze_experiences(
        self,
        experiences: List[Any],
        questions: List[Any],
        allocations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        state = self.coach.diagnose_user_state(experiences, questions)
        temporal_issues = self.evidence.validate_temporal_consistency(experiences)
        role_issues = self.evidence.validate_role_consistency(experiences)
        allocation_issues = self.evidence.validate_cross_question_allocation(
            allocations, experiences
        )
        suggestions = self.evidence.suggest_experience_additions(
            experiences, questions, allocations
        )
        coverage = self.evidence.get_coverage_report(
            experiences, questions, allocations
        )

        return {
            "coaching_state": state.value if hasattr(state, "value") else str(state),
            "temporal_inconsistencies": [i.to_dict() for i in temporal_issues],
            "role_inconsistencies": [i.to_dict() for i in role_issues],
            "allocation_issues": allocation_issues,
            "suggestions": suggestions,
            "coverage_report": coverage,
            "progressive_plan": self.coach.create_progressive_plan(
                experiences, questions
            ),
        }

    def coach_realtime(
        self,
        user_input: str,
        context: Optional[str] = None,
    ) -> CoachingFeedback:
        return self.coach.provide_realtime_feedback(user_input, context)

    def generate_self_intro_pack(
        self,
        experiences: List[Any],
        company: str,
        job: str,
    ) -> Dict[str, Any]:
        hooks = self.self_intro.generate_hook_candidates(experiences, company)
        core_story = self._extract_best_story(experiences)
        versions = self.self_intro.build_progressive_versions(core_story, company, job)
        follow_ups = self.self_intro.simulate_interview_flow(versions.thirty_second)

        return {
            "hooks": [
                {"type": h.hook_type, "content": h.content, "score": h.impact_score}
                for h in hooks
            ],
            "versions": {
                "elevator": versions.elevator_pitch,
                "30s": versions.thirty_second,
                "60s": versions.sixty_second,
                "90s": versions.ninety_second,
            },
            "expected_follow_ups": follow_ups,
        }

    def _extract_best_story(self, experiences: List[Any]) -> Any:
        if not experiences:
            from ..models import Experience

            story = Experience(
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
            )
            return story
        best = max(
            experiences,
            key=lambda e: (
                1 if getattr(e, "metrics", "") else 0,
                1 if getattr(e, "evidence_text", "") else 0,
                len(getattr(e, "action", "") or ""),
            ),
        )
        return best


class Top001ResearchTranslator:
    """상위 0.01% 전략적 연구 번역기"""

    def __init__(self):
        from .strategic_research import StrategicResearchTranslator

        self.translator = StrategicResearchTranslator()

    def translate_research_to_strategy(
        self,
        company_analysis: Any,
        experiences: List[Any],
        questions: List[Any],
    ) -> Dict[str, Any]:
        signals = self.translator.extract_strategic_signals(company_analysis)
        question_hooks = self.translator.generate_question_specific_hooks(
            questions, company_analysis, experiences
        )
        evidence_maps = self.translator.create_evidence_mapping(
            experiences, company_analysis
        )
        predictions = self.translator.build_interview_prediction(company_analysis)
        defense_strategies = self.translator.generate_defense_strategy(
            company_analysis, experiences
        )

        return {
            "strategic_signals": {
                "core_values": signals.core_values_alignment,
                "competencies": signals.competency_matches,
                "interview_predictions": signals.interview_prediction,
                "differentiation": signals.differentiation_points,
            },
            "question_hooks": question_hooks,
            "evidence_maps": [
                {
                    "experience_id": m.experience_id,
                    "signals": m.strategic_signals,
                    "proof_points": m.proof_points,
                }
                for m in evidence_maps
            ],
            "interview_predictions": predictions,
            "defense_strategies": [
                {
                    "vulnerable_point": d.vulnerable_point,
                    "defense_script": d.defense_script,
                    "alternatives": d.alternative_frames,
                }
                for d in defense_strategies
            ],
        }
