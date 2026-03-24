"""
피드백 학습 루프 - 사용자 피드백을 기반으로 패턴 학습 및 추천 개선
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class UserFeedback:
    """사용자 피드백"""
    draft_id: str
    pattern_used: str
    accepted: bool
    rating: Optional[int] = None  # 1-5
    comment: Optional[str] = None
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
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get("feedback", []):
                    self.feedback_history.append(UserFeedback(**item))
        
        # 패턴 통계 로드
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for pattern_id, stats_data in data.get("stats", {}).items():
                    self.pattern_stats[pattern_id] = PatternStats(**stats_data)
    
    def _save(self) -> None:
        """데이터 저장"""
        feedback_payload = {"feedback": [asdict(fb) for fb in self.feedback_history]}
        stats_payload = {"stats": {pid: asdict(stats) for pid, stats in self.pattern_stats.items()}}

        # 피드백 히스토리 저장
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_payload, f, ensure_ascii=False, indent=2)
        
        # 패턴 통계 저장
        with open(self.stats_file, 'w', encoding='utf-8') as f:
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
                    fb.rating for fb in self.feedback_history
                    if fb.pattern_used == feedback.pattern_used and fb.rating is not None
                ]
                stats.avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            
            # 성공률 계산
            if stats.total_uses > 0:
                stats.success_rate = stats.accepted_count / stats.total_uses
            
            self._save()
    
    def find_similar(self, context: Dict[str, Any], limit: int = 10) -> List[PatternStats]:
        """유사한 컨텍스트의 패턴 검색"""
        # 간단한 구현: 성공률 기준 정렬
        all_stats = list(self.pattern_stats.values())
        all_stats.sort(key=lambda x: x.success_rate, reverse=True)
        return all_stats[:limit]
    
    def get_pattern_stats(self, pattern_id: str) -> Optional[PatternStats]:
        """패턴 통계 조회"""
        return self.pattern_stats.get(pattern_id)
    
    def get_top_patterns(self, n: int = 10) -> List[PatternStats]:
        """상위 패턴 반환 (성공률 기준)"""
        all_stats = list(self.pattern_stats.values())
        all_stats.sort(key=lambda x: x.success_rate, reverse=True)
        return all_stats[:n]
    
    def get_feedback_history(
        self,
        pattern_id: Optional[str] = None,
        limit: int = 50
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
        comment: Optional[str] = None
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
            comment=comment
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
                recommendations.append({
                    "pattern_id": stats.pattern_id,
                    "success_rate": stats.success_rate,
                    "avg_rating": stats.avg_rating,
                    "total_uses": stats.total_uses,
                    "confidence": self._calculate_confidence(stats)
                })
        
        return recommendations
    
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
        
        overall_success_rate = total_accepted / total_feedback if total_feedback > 0 else 0
        
        # 평점 분석
        ratings = [
            fb.rating for fb in self.db.feedback_history
            if fb.rating is not None
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
                    "uses": p.total_uses
                }
                for p in top_patterns
            ],
            "improvement_areas": self._identify_improvement_areas()
        }
    
    def _identify_improvement_areas(self) -> List[str]:
        """개선 영역 식별"""
        areas = []
        
        # 성공률이 낮은 패턴 식별
        for pattern_id, stats in self.db.pattern_stats.items():
            if stats.total_uses >= 3 and stats.success_rate < 0.5:
                areas.append(f"패턴 '{pattern_id}'의 성공률이 낮습니다 ({stats.success_rate:.0%})")
        
        # 평점이 낮은 피드백 분석
        low_rated = [
            fb for fb in self.db.feedback_history
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
                "average_rating": insights["average_rating"]
            },
            "top_patterns": insights["top_patterns"],
            "improvement_areas": insights["improvement_areas"],
            "detailed_stats": {
                pid: asdict(stats)
                for pid, stats in self.db.pattern_stats.items()
            }
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise RuntimeError(f"리포트 저장 실패: {output_file}") from exc


def create_feedback_learner(db_path: str = "./kb/feedback") -> FeedbackLearner:
    """FeedbackLearner 인스턴스 생성 편의 함수"""
    return FeedbackLearner(db_path)
