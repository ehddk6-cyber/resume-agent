"""
피드백 학습 루프 - 사용자 피드백을 기반으로 패턴 학습 및 추천 개선
"""

from __future__ import annotations

import json
import threading
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from .logger import get_logger

logger = get_logger(__name__)


_POSITIVE_OUTCOME_WEIGHTS = {
    "offer": 4,
    "final_pass": 3,
    "pass": 3,
    "interview_pass": 2,
    "document_pass": 2,
}

_NEGATIVE_OUTCOME_WEIGHTS = {
    "fail_interview": 3,
    "interview_fail": 3,
    "document_fail": 1,
    "reject": 2,
    "rejected": 2,
}


@dataclass
class UserFeedback:
    """사용자 피드백"""

    draft_id: str
    pattern_used: str
    accepted: bool
    rating: Optional[int] = None  # 1-5
    comment: Optional[str] = None
    artifact_type: str = ""
    company_name: str = ""
    job_title: str = ""
    company_type: str = ""
    question_types: List[str] = field(default_factory=list)
    stage: str = ""
    final_outcome: Optional[str] = None
    rejection_reason: Optional[str] = None
    selected_experience_ids: List[str] = field(default_factory=list)
    question_experience_map: List[Dict[str, str]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PatternStats:
    """패턴 통계"""

    pattern_id: str
    total_uses: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    avg_rating: float = 0.0
    success_rate: float = 0.0
    last_used: Optional[str] = None


class FeedbackDatabase:
    """피드백 데이터베이스"""

    def __init__(self, db_path: str = "./kb/feedback"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self.feedback_file = self.db_path / "feedback.json"
        self.stats_file = self.db_path / "pattern_stats.json"

        self.feedback_history: List[UserFeedback] = []
        self.pattern_stats: Dict[str, PatternStats] = {}

        self._load()

    def _load(self) -> None:
        """데이터 로드"""
        # 피드백 히스토리 로드
        if self.feedback_file.exists():
            with open(self.feedback_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("feedback", []):
                    self.feedback_history.append(UserFeedback(**item))

        # 패턴 통계 로드
        if self.stats_file.exists():
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for pattern_id, stats_data in data.get("stats", {}).items():
                    self.pattern_stats[pattern_id] = PatternStats(**stats_data)

    def _save(self) -> None:
        """데이터 저장"""
        feedback_payload = {"feedback": [asdict(fb) for fb in self.feedback_history]}
        stats_payload = {
            "stats": {pid: asdict(stats) for pid, stats in self.pattern_stats.items()}
        }

        # 피드백 히스토리 저장
        with open(self.feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_payload, f, ensure_ascii=False, indent=2)

        # 패턴 통계 저장
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(stats_payload, f, ensure_ascii=False, indent=2)

    def save_feedback(self, feedback: UserFeedback) -> None:
        """피드백 저장"""
        with self._lock:
            self.feedback_history.append(feedback)

            # 패턴 통계 업데이트
            if feedback.pattern_used not in self.pattern_stats:
                self.pattern_stats[feedback.pattern_used] = PatternStats(
                    pattern_id=feedback.pattern_used
                )

            stats = self.pattern_stats[feedback.pattern_used]
            stats.total_uses += 1
            stats.last_used = feedback.timestamp

            if feedback.accepted:
                stats.accepted_count += 1
            else:
                stats.rejected_count += 1

            # 평점 업데이트
            if feedback.rating is not None:
                ratings = [
                    fb.rating
                    for fb in self.feedback_history
                    if fb.pattern_used == feedback.pattern_used
                    and fb.rating is not None
                ]
                stats.avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

            # 성공률 계산
            if stats.total_uses > 0:
                stats.success_rate = stats.accepted_count / stats.total_uses

            self._save()

    def find_similar(
        self, context: Dict[str, Any], limit: int = 10
    ) -> List[PatternStats]:
        """유사한 컨텍스트의 패턴 검색"""
        grouped: Dict[str, Dict[str, Any]] = {}

        for feedback in self.feedback_history:
            match_score = _calculate_context_match_score(feedback, context)
            if match_score <= 0:
                continue

            bucket = grouped.setdefault(
                feedback.pattern_used,
                {
                    "feedback": [],
                    "score_sum": 0,
                },
            )
            bucket["feedback"].append(feedback)
            bucket["score_sum"] += match_score

        if not grouped:
            all_stats = list(self.pattern_stats.values())
            all_stats.sort(
                key=lambda item: (item.success_rate, item.total_uses), reverse=True
            )
            return all_stats[:limit]

        similar_stats: List[PatternStats] = []
        for pattern_id, bucket in grouped.items():
            feedbacks: List[UserFeedback] = bucket["feedback"]
            ratings = [fb.rating for fb in feedbacks if fb.rating is not None]
            accepted_count = sum(1 for fb in feedbacks if fb.accepted)
            total_uses = len(feedbacks)
            similar_stats.append(
                PatternStats(
                    pattern_id=pattern_id,
                    total_uses=total_uses,
                    accepted_count=accepted_count,
                    rejected_count=total_uses - accepted_count,
                    avg_rating=(sum(ratings) / len(ratings)) if ratings else 0.0,
                    success_rate=accepted_count / total_uses if total_uses else 0.0,
                    last_used=max(fb.timestamp for fb in feedbacks),
                )
            )

        similar_stats.sort(
            key=lambda item: (
                grouped[item.pattern_id]["score_sum"],
                item.success_rate,
                item.total_uses,
            ),
            reverse=True,
        )
        return similar_stats[:limit]

    def get_pattern_stats(self, pattern_id: str) -> Optional[PatternStats]:
        """패턴 통계 조회"""
        return self.pattern_stats.get(pattern_id)

    def get_top_patterns(self, n: int = 10) -> List[PatternStats]:
        """상위 패턴 반환 (성공률 기준)"""
        all_stats = list(self.pattern_stats.values())
        all_stats.sort(key=lambda x: x.success_rate, reverse=True)
        return all_stats[:n]

    def get_feedback_history(
        self, pattern_id: Optional[str] = None, limit: int = 50
    ) -> List[UserFeedback]:
        """피드백 히스토리 조회"""
        history = list(self.feedback_history)

        if pattern_id:
            history = [fb for fb in history if fb.pattern_used == pattern_id]

        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]


class FeedbackLearner:
    """
    피드백 학습 엔진

    기능:
    - 사용자 피드백 기록
    - 패턴별 성공률 추적
    - 학습된 패턴 기반 추천
    - 피드백 분석 및 인사이트
    """

    def __init__(self, db_path: str = "./kb/feedback"):
        self.db = FeedbackDatabase(db_path)

    def record_feedback(
        self,
        draft_id: str,
        pattern_used: str,
        accepted: bool,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        artifact_type: str = "",
        company_name: str = "",
        job_title: str = "",
        company_type: str = "",
        question_types: Optional[List[str]] = None,
        stage: str = "",
        final_outcome: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        selected_experience_ids: Optional[List[str]] = None,
        question_experience_map: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """
        사용자 피드백 기록

        Args:
            draft_id: 초안 ID
            pattern_used: 사용된 패턴
            accepted: 수락 여부
            rating: 평점 (1-5, 선택)
            comment: 코멘트 (선택)
        """
        feedback = UserFeedback(
            draft_id=draft_id,
            pattern_used=pattern_used,
            accepted=accepted,
            rating=rating,
            comment=comment,
            artifact_type=artifact_type,
            company_name=company_name,
            job_title=job_title,
            company_type=company_type,
            question_types=question_types or [],
            stage=stage,
            final_outcome=final_outcome,
            rejection_reason=rejection_reason,
            selected_experience_ids=selected_experience_ids or [],
            question_experience_map=question_experience_map or [],
        )

        self.db.save_feedback(feedback)

    def get_recommendation(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        학습된 패턴 기반 추천

        Args:
            context: 현재 컨텍스트 (회사, 직무, 질문 유형 등)

        Returns:
            추천 패턴 리스트
        """
        similar_patterns = self.db.find_similar(context)

        recommendations = []
        for stats in similar_patterns:
            if stats.success_rate > 0.5:  # 50% 이상 성공률만 추천
                recommendations.append(
                    {
                        "pattern_id": stats.pattern_id,
                        "success_rate": stats.success_rate,
                        "avg_rating": stats.avg_rating,
                        "total_uses": stats.total_uses,
                        "confidence": self._calculate_confidence(stats),
                    }
                )

        return recommendations

    def get_context_outcome_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """유사 컨텍스트의 실제 결과 요약"""
        matched = [
            feedback
            for feedback in self.db.feedback_history
            if _calculate_context_match_score(feedback, context) > 0
        ]
        outcome_breakdown: Dict[str, int] = {}
        rejection_reasons: Dict[str, int] = {}

        for feedback in matched:
            outcome = (feedback.final_outcome or "unknown").strip() or "unknown"
            outcome_breakdown[outcome] = outcome_breakdown.get(outcome, 0) + 1
            if feedback.rejection_reason:
                rejection_reasons[feedback.rejection_reason] = (
                    rejection_reasons.get(feedback.rejection_reason, 0) + 1
                )

        top_rejection_reasons = [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                rejection_reasons.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ]

        return {
            "matched_feedback_count": len(matched),
            "outcome_breakdown": outcome_breakdown,
            "top_rejection_reasons": top_rejection_reasons,
        }

    def get_learned_outcome_weights(self, context: Dict[str, Any]) -> Dict[str, float]:
        """컨텍스트에 맞춰 경험적으로 보정된 outcome 가중치"""
        matched = [
            feedback
            for feedback in self.db.feedback_history
            if _calculate_context_match_score(feedback, context) > 0
        ]
        base_weights: Dict[str, float] = {
            **{key: float(value) for key, value in _POSITIVE_OUTCOME_WEIGHTS.items()},
            **{key: float(value) for key, value in _NEGATIVE_OUTCOME_WEIGHTS.items()},
        }
        if not matched:
            return base_weights

        outcome_counts: Dict[str, int] = {}
        for feedback in matched:
            outcome = (feedback.final_outcome or "").strip().lower()
            if not outcome:
                outcome = "accepted" if feedback.accepted else "rejected"
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        total = len(matched)
        learned = dict(base_weights)
        for outcome, count in outcome_counts.items():
            frequency = count / max(1, total)
            base = learned.get(outcome)
            if base is None:
                if "offer" in outcome:
                    base = 4.0
                elif "pass" in outcome:
                    base = 3.0
                elif "fail" in outcome or "reject" in outcome:
                    base = 2.0
                else:
                    base = 1.0
            multiplier = 1.0 + min(0.6, frequency * 0.5)
            if outcome in {"offer", "final_pass"}:
                multiplier += 0.15
            if outcome in {"fail_interview", "interview_fail"}:
                multiplier += 0.1
            learned[outcome] = round(base * multiplier, 2)
        return learned

    def get_strategy_outcome_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """pattern_id / question_type / selected_experience_id 단위 결과 통계"""
        matched = [
            feedback
            for feedback in self.db.feedback_history
            if _calculate_context_match_score(feedback, context) > 0
        ]
        learned_weights = self.get_learned_outcome_weights(context)
        experience_stats_by_question_type: Dict[str, Dict[str, Any]] = {}

        for feedback in matched:
            for item in feedback.question_experience_map:
                question_type = str(item.get("question_type") or "").strip()
                experience_id = str(item.get("experience_id") or "").strip()
                if not question_type or not experience_id:
                    continue

                type_bucket = experience_stats_by_question_type.setdefault(question_type, {})
                exp_bucket = type_bucket.setdefault(
                    experience_id,
                    {
                        "total_uses": 0,
                        "pass_count": 0,
                        "fail_count": 0,
                        "weighted_pass_score": 0,
                        "weighted_fail_score": 0,
                        "weighted_net_score": 0,
                        "pass_rate": 0.0,
                        "pattern_breakdown": {},
                        "top_rejection_reasons": [],
                    },
                )
                exp_bucket["total_uses"] += 1

                pattern_bucket = exp_bucket["pattern_breakdown"].setdefault(
                    feedback.pattern_used,
                    {
                        "total_uses": 0,
                        "pass_count": 0,
                        "fail_count": 0,
                        "weighted_pass_score": 0,
                        "weighted_fail_score": 0,
                        "weighted_net_score": 0,
                        "pass_rate": 0.0,
                    },
                )
                pattern_bucket["total_uses"] += 1

                pass_weight, fail_weight = _feedback_outcome_weights(
                    feedback, learned_weights
                )
                if _feedback_is_pass(feedback):
                    exp_bucket["pass_count"] += 1
                    pattern_bucket["pass_count"] += 1
                else:
                    exp_bucket["fail_count"] += 1
                    pattern_bucket["fail_count"] += 1
                exp_bucket["weighted_pass_score"] += pass_weight
                exp_bucket["weighted_fail_score"] += fail_weight
                pattern_bucket["weighted_pass_score"] += pass_weight
                pattern_bucket["weighted_fail_score"] += fail_weight

                if feedback.rejection_reason:
                    reasons = exp_bucket.setdefault("_reason_counts", {})
                    reasons[feedback.rejection_reason] = (
                        reasons.get(feedback.rejection_reason, 0) + 1
                    )

        for type_bucket in experience_stats_by_question_type.values():
            for exp_bucket in type_bucket.values():
                total_uses = int(exp_bucket.get("total_uses", 0))
                pass_count = int(exp_bucket.get("pass_count", 0))
                exp_bucket["pass_rate"] = (
                    round(pass_count / total_uses, 3) if total_uses else 0.0
                )
                exp_bucket["weighted_net_score"] = int(
                    exp_bucket.get("weighted_pass_score", 0)
                ) - int(exp_bucket.get("weighted_fail_score", 0))
                for pattern_bucket in exp_bucket["pattern_breakdown"].values():
                    pattern_total = int(pattern_bucket.get("total_uses", 0))
                    pattern_pass = int(pattern_bucket.get("pass_count", 0))
                    pattern_bucket["pass_rate"] = (
                        round(pattern_pass / pattern_total, 3) if pattern_total else 0.0
                    )
                    pattern_bucket["weighted_net_score"] = int(
                        pattern_bucket.get("weighted_pass_score", 0)
                    ) - int(pattern_bucket.get("weighted_fail_score", 0))
                reason_counts = exp_bucket.pop("_reason_counts", {})
                exp_bucket["top_rejection_reasons"] = [
                    {"reason": reason, "count": count}
                    for reason, count in sorted(
                        reason_counts.items(),
                        key=lambda pair: (-pair[1], pair[0]),
                    )[:5]
                ]

        return {
            "matched_feedback_count": len(matched),
            "learned_outcome_weights": learned_weights,
            "experience_stats_by_question_type": experience_stats_by_question_type,
        }

    def _calculate_confidence(self, stats: PatternStats) -> float:
        """추천 신뢰도 계산"""
        # 사용 횟수와 성공률을 기반으로 신뢰도 계산
        usage_factor = min(1.0, stats.total_uses / 10)  # 10회 이상이면 최대
        success_factor = stats.success_rate

        confidence = (usage_factor * 0.4) + (success_factor * 0.6)
        return round(confidence, 2)

    def get_insights(self) -> Dict[str, Any]:
        """피드백 분석 인사이트"""
        top_patterns = self.db.get_top_patterns(5)

        # 전체 통계
        all_stats = list(self.db.pattern_stats.values())
        total_feedback = sum(s.total_uses for s in all_stats)
        total_accepted = sum(s.accepted_count for s in all_stats)

        overall_success_rate = (
            total_accepted / total_feedback if total_feedback > 0 else 0
        )

        # 평점 분석
        ratings = [
            fb.rating for fb in self.db.feedback_history if fb.rating is not None
        ]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        return {
            "total_feedback": total_feedback,
            "overall_success_rate": round(overall_success_rate, 2),
            "average_rating": round(avg_rating, 2),
            "top_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "success_rate": p.success_rate,
                    "uses": p.total_uses,
                }
                for p in top_patterns
            ],
            "improvement_areas": self._identify_improvement_areas(),
        }

    def _identify_improvement_areas(self) -> List[str]:
        """개선 영역 식별"""
        areas = []

        # 성공률이 낮은 패턴 식별
        for pattern_id, stats in self.db.pattern_stats.items():
            if stats.total_uses >= 3 and stats.success_rate < 0.5:
                areas.append(
                    f"패턴 '{pattern_id}'의 성공률이 낮습니다 ({stats.success_rate:.0%})"
                )

        # 평점이 낮은 피드백 분석
        low_rated = [
            fb
            for fb in self.db.feedback_history
            if fb.rating is not None and fb.rating <= 2
        ]

        if len(low_rated) > 5:
            areas.append("낮은 평점의 피드백이 많습니다. 품질 개선이 필요합니다.")

        return areas

    def export_report(self, output_path: str) -> None:
        """피드백 리포트 내보내기"""
        insights = self.get_insights()
        output_file = Path(output_path)
        if output_file.exists() and output_file.is_dir():
            raise RuntimeError(f"리포트 경로가 디렉토리입니다: {output_file}")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_feedback": insights["total_feedback"],
                "success_rate": insights["overall_success_rate"],
                "average_rating": insights["average_rating"],
            },
            "top_patterns": insights["top_patterns"],
            "improvement_areas": insights["improvement_areas"],
            "detailed_stats": {
                pid: asdict(stats) for pid, stats in self.db.pattern_stats.items()
            },
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise RuntimeError(f"리포트 저장 실패: {output_file}") from exc


def create_feedback_learner(db_path: str = "./kb/feedback") -> FeedbackLearner:
    """FeedbackLearner 인스턴스 생성 편의 함수"""
    return FeedbackLearner(db_path)


def _tokenize_text(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9가-힣]{2,}", value.lower())
        if token.strip()
    }


def _calculate_context_match_score(
    feedback: UserFeedback, context: Dict[str, Any]
) -> int:
    score = 0

    artifact = str(context.get("artifact_type") or context.get("artifact") or "").strip()
    if artifact and artifact == feedback.artifact_type:
        score += 5

    stage = str(context.get("stage") or "").strip()
    if stage and stage == feedback.stage:
        score += 3

    company_type = str(context.get("company_type") or "").strip()
    if company_type and company_type == feedback.company_type:
        score += 4

    company_name = str(context.get("company_name") or "").strip().lower()
    if company_name and company_name == feedback.company_name.lower():
        score += 3

    context_job_tokens = _tokenize_text(str(context.get("job_title") or ""))
    feedback_job_tokens = _tokenize_text(feedback.job_title)
    if context_job_tokens and feedback_job_tokens:
        overlap = context_job_tokens & feedback_job_tokens
        if overlap:
            score += min(3, len(overlap))

    context_types = {
        str(item)
        for item in (context.get("question_types") or [])
        if str(item).strip()
    }
    feedback_types = {str(item) for item in feedback.question_types if str(item).strip()}
    if context_types and feedback_types:
        overlap = context_types & feedback_types
        if overlap:
            score += min(3, len(overlap))

    final_outcome = str(context.get("final_outcome") or "").strip()
    if final_outcome and final_outcome == (feedback.final_outcome or ""):
        score += 1

    if not score and artifact and feedback.pattern_used.startswith(f"{artifact}|"):
        score += 1

    return score


def _feedback_is_pass(feedback: UserFeedback) -> bool:
    outcome = (feedback.final_outcome or "").strip().lower()
    if not outcome:
        return bool(feedback.accepted)
    if "fail" in outcome or "reject" in outcome:
        return False
    if outcome in {"pass", "document_pass", "offer", "final_pass"}:
        return True
    return bool(feedback.accepted)


def _feedback_outcome_weights(
    feedback: UserFeedback,
    learned_weights: Dict[str, float] | None = None,
) -> tuple[float, float]:
    outcome = (feedback.final_outcome or "").strip().lower()
    weight_map = learned_weights or {}
    if outcome in _POSITIVE_OUTCOME_WEIGHTS:
        return float(weight_map.get(outcome, _POSITIVE_OUTCOME_WEIGHTS[outcome])), 0.0
    if outcome in _NEGATIVE_OUTCOME_WEIGHTS:
        return 0.0, float(weight_map.get(outcome, _NEGATIVE_OUTCOME_WEIGHTS[outcome]))
    if outcome and "offer" in outcome:
        return float(weight_map.get(outcome, 4)), 0.0
    if outcome and "pass" in outcome:
        return float(weight_map.get(outcome, 3)), 0.0
    if outcome and ("fail" in outcome or "reject" in outcome):
        return 0.0, float(weight_map.get(outcome, 2))
    if feedback.accepted:
        return float(weight_map.get("accepted", 1)), 0.0
    return 0.0, float(weight_map.get("rejected", 1))
