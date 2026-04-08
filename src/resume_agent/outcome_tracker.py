"""결과 추적 및 통계 분석 모듈"""

from typing import Dict, List, Optional
from pathlib import Path
import json
import logging

from .models import OutcomeResult, ExperienceOutcomeStats
from .state import Workspace

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """지원 결과 추적 및 분석"""
    
    def __init__(self, ws: Workspace):
        self.ws = ws
        self.outcomes_file = ws.state_dir / "outcomes.json"
        self._outcomes: List[OutcomeResult] = []
        self._load()
    
    def _load(self):
        if self.outcomes_file.exists():
            with open(self.outcomes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._outcomes = [OutcomeResult(**o) for o in data]
    
    def _save(self):
        self.outcomes_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.outcomes_file, "w", encoding="utf-8") as f:
            json.dump([o.model_dump() for o in self._outcomes], f, ensure_ascii=False, indent=2)
    
    def record_outcome(self, outcome: OutcomeResult) -> OutcomeResult:
        """결과 기록"""
        for i, o in enumerate(self._outcomes):
            if o.artifact_id == outcome.artifact_id:
                self._outcomes[i] = outcome
                self._save()
                return outcome
        
        self._outcomes.append(outcome)
        self._save()
        logger.info(f"Recorded outcome: {outcome.artifact_id} -> {outcome.outcome}")
        return outcome
    
    def get_outcome(self, artifact_id: str) -> Optional[OutcomeResult]:
        """결과 조회"""
        for o in self._outcomes:
            if o.artifact_id == artifact_id:
                return o
        return None
    
    def get_all_outcomes(self) -> List[OutcomeResult]:
        """전체 결과 조회"""
        return self._outcomes
    
    def get_company_outcomes(self, company_name: str) -> List[OutcomeResult]:
        """기업별 결과 조회"""
        return [o for o in self._outcomes if company_name in o.company_name]
    
    def get_success_rate(self) -> float:
        """전체 성공률 계산"""
        if not self._outcomes:
            return 0.0
        success = sum(1 for o in self._outcomes 
                     if o.outcome in ["offer_received", "final_pass", "interview_pass"])
        return success / len(self._outcomes)
    
    def get_outcome_summary(self) -> Dict[str, int]:
        """결과 요약 통계"""
        summary: Dict[str, int] = {
            "pending": 0, "screening_pass": 0, "screening_fail": 0,
            "interview_invited": 0, "interview_pass": 0, "interview_fail": 0,
            "final_pass": 0, "final_fail": 0, "offer_received": 0
        }
        for o in self._outcomes:
            if o.outcome in summary:
                summary[o.outcome] += 1
        return summary
    
    def get_experience_stats(
        self, 
        experience_id: str,
        experience_title: str
    ) -> ExperienceOutcomeStats:
        """경험별 사용 통계 계산"""
        from .feedback_learner import FeedbackLearner
        
        learner = FeedbackLearner(self.ws)
        all_feedback = learner.get_all_feedback()
        relevant = [f for f in all_feedback if experience_id in f.selected_experience_ids]
        
        if not relevant:
            return ExperienceOutcomeStats(experience_id=experience_id, experience_title=experience_title)
        
        success = sum(1 for f in relevant if f.final_outcome in ["offer_received", "final_pass", "interview_pass"])
        fail = sum(1 for f in relevant if f.final_outcome in ["screening_fail", "interview_fail", "final_fail"])
        ratings = [f.rating for f in relevant if f.rating is not None]
        
        return ExperienceOutcomeStats(
            experience_id=experience_id,
            experience_title=experience_title,
            total_uses=len(relevant),
            success_count=success,
            fail_count=fail,
            success_rate=success / len(relevant),
            avg_interview_count=sum(f.interview_count or 0 for f in relevant) / len(relevant),
            question_types_used=list(set(qt for f in relevant for qt in (f.question_types or []))),
            avg_rating=sum(ratings) / len(ratings) if ratings else None
        )
