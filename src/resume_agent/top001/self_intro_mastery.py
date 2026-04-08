from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, TYPE_CHECKING

from .base_types import (
    Hook,
    Story,
    IntroVersions,
    PracticeIteration,
    PracticeHistory,
)

if TYPE_CHECKING:
    from ..models import Experience, CompanyAnalysis


HOOK_TEMPLATES = {
    "problem_hook": "가장 큰 도전을 발견하고 직접 해결한 경험이 있습니다",
    "impact_hook": "팀의 업무 방식을 근본적으로 바꾼 경험이 있습니다",
    "connection_hook": "귀사의 {company} 방향성과 직접 연결되는 경험입니다",
    "result_hook": "정량적 성과를 증명한 구체적 경험이 있습니다",
}


def _extract_story_from_experience(exp: Experience) -> Story:
    return Story(
        situation=getattr(exp, "situation", "") or "",
        task=getattr(exp, "task", "") or "",
        action=getattr(exp, "action", "") or "",
        result=getattr(exp, "result", "") or "",
        personal_contribution=getattr(exp, "personal_contribution", "") or "",
        metrics=getattr(exp, "metrics", "") or "",
    )


def _build_elevator_pitch(story: Story, company: str, job: str) -> str:
    if story.action and story.result:
        action_short = (
            story.action[:30] + "..." if len(story.action) > 30 else story.action
        )
        return f"{job}에서 {action_short} 경험을 바탕으로 핵심 성과를 만들고자 합니다"
    return f"{company}의 {job}에서 기여할 준비가 된 지원자입니다"


def _build_30sec_intro(story: Story, company: str, job: str) -> str:
    parts = []
    if story.action:
        parts.append(f"저는 {story.action}")
    if story.result:
        parts.append(f"그 결과 {story.result}")
    if company and job:
        parts.append(f"이를 {job}에 기여할 수 있는 역량으로 발전시키고 싶습니다")
    return " ".join(parts) if parts else f"{company} {job} 지원자입니다"


def _build_60sec_intro(story: Story, company: str, job: str) -> str:
    parts = []
    if story.situation:
        parts.append(f"저는 {story.situation} 상황에서")
    if story.task:
        parts.append(f"{story.task}를 해결해야 했습니다")
    if story.action:
        parts.append(f"그때 {story.action}")
    if story.result:
        parts.append(f"결과적으로 {story.result}")
    if company:
        parts.append(f"이러한 경험을 {company}에서 발전시키고 싶습니다")
    return " ".join(parts) if parts else f"{company} {job} 지원자입니다"


def _build_90sec_intro(story: Story, company: str, job: str) -> str:
    intro_60 = _build_60sec_intro(story, company, job)
    additional = []
    if story.personal_contribution:
        additional.append(
            f"그 과정에서 제가 중점적으로 맡은 부분은 {story.personal_contribution}이었습니다"
        )
    if story.metrics:
        additional.append(f"구체적으로 {story.metrics}의 성과를 냈습니다")
    if company and job:
        additional.append(f"이 경험을 {company}의 {job}에서 실질적 기여로 연결하고 싶습니다")
    return intro_60 + " " + " ".join(additional)


def _generate_hook_candidates(story: Story, company: str) -> List[Hook]:
    hooks = []
    if story.situation and ("문제" in story.situation or "어려움" in story.situation):
        hooks.append(
            Hook(
                hook_type="problem_hook",
                content="가장 큰 도전을 발견하고 직접 해결한 경험이 있습니다",
                impact_score=0.8,
                supporting_evidence=story.situation,
            )
        )
    if story.result and any(
        c in story.result for c in ["30%", "50%", "100%", "배", "증가"]
    ):
        hooks.append(
            Hook(
                hook_type="impact_hook",
                content="팀의 업무 방식을 근본적으로 바꾼 경험이 있습니다",
                impact_score=0.9,
                supporting_evidence=story.result,
            )
        )
    if company:
        hooks.append(
            Hook(
                hook_type="connection_hook",
                content=f"귀사의 {company} 방향성과 직접 연결되는 경험입니다",
                impact_score=0.7,
                supporting_evidence=story.action,
            )
        )
    if story.metrics:
        hooks.append(
            Hook(
                hook_type="result_hook",
                content=f"정량적 성과를 증명한 구체적 경험이 있습니다: {story.metrics}",
                impact_score=0.95,
                supporting_evidence=story.metrics,
            )
        )
    return hooks


class SelfIntroMastery:
    def __init__(self):
        self.practice_history: PracticeHistory = PracticeHistory()
        self.current_versions: Optional[IntroVersions] = None

    def generate_hook_candidates(
        self, experiences: List[Experience], company: str
    ) -> List[Hook]:
        all_hooks = []
        for exp in experiences[:3]:
            story = _extract_story_from_experience(exp)
            hooks = _generate_hook_candidates(story, company)
            all_hooks.extend(hooks)
        all_hooks.sort(key=lambda h: h.impact_score, reverse=True)
        return all_hooks[:4]

    def build_progressive_versions(
        self,
        core_story: Story,
        company: str,
        job: str,
    ) -> IntroVersions:
        return IntroVersions(
            elevator_pitch=_build_elevator_pitch(core_story, company, job),
            thirty_second=_build_30sec_intro(core_story, company, job),
            sixty_second=_build_60sec_intro(core_story, company, job),
            ninety_second=_build_90sec_intro(core_story, company, job),
            hooks=_generate_hook_candidates(core_story, company),
            core_story=core_story,
        )

    def simulate_interview_flow(self, intro: str) -> List[str]:
        follow_ups = []
        if any(kw in intro for kw in ["행동", "수행", "진행"]):
            follow_ups.append(
                "방금 말씀하신 행동에서 본인의 역할은 구체적으로 무엇이었나요?"
            )
        if any(kw in intro for kw in ["결과", "성과", "달성"]):
            follow_ups.append("그 결과는 어떻게 측정하거나 확인하셨나요?")
        if "회사" in intro or "귀사" in intro:
            follow_ups.append("왜 우리 회사를 선택하셨나요?")
        if len(follow_ups) < 2:
            follow_ups.append("그 경험에서 가장 어려웠던 부분은 무엇이었나요?")
        return follow_ups[:3]

    def provide_delivery_feedback(self, intro: str) -> Dict[str, Any]:
        feedback = {
            "score": 0.5,
            "first_impression": "",
            "pace_suggestion": "",
            "emphasis_points": [],
            "issues": [],
        }

        if len(intro) < 50:
            feedback["issues"].append("너무 짧습니다. 조금 더 구체적으로 말씀해 주세요.")
            feedback["score"] -= 0.2
        elif len(intro) > 300:
            feedback["issues"].append("너무 깁니다. 90초 내로 줄여주세요")
            feedback["score"] -= 0.1

        if intro.startswith("저는"):
            feedback["issues"].append(
                "'저는'으로 시작하기보다 행동이나 성과로 시작하면 더 강한 인상을 줄 수 있습니다."
            )
            feedback["score"] -= 0.1

        if any(cliche in intro for cliche in ["항상", "최선을", "열정적"]):
            feedback["issues"].append("클리셰 표현은 피하고 본인 경험의 결을 살려 주세요.")
            feedback["score"] -= 0.1

        numbers = re.findall(r"\d+", intro)
        if numbers:
            feedback["emphasis_points"].append(
                f"수치({numbers[0]})를 더 또렷하게 강조하면 설득력이 높아집니다."
            )
            feedback["score"] += 0.1

        if "저는" not in intro and "제가" not in intro:
            feedback["emphasis_points"].append("개인 기여를 명확히 드러내주세요")

        feedback["first_impression"] = (
            "괜찮은 도입부입니다" if feedback["score"] >= 0.5 else "수정 필요"
        )
        feedback["pace_suggestion"] = "60초 기준으로 또박또박 읽되, 핵심 문장은 한 템포 쉬어 강조하세요."
        feedback["score"] = max(0.0, min(1.0, feedback["score"]))
        return feedback

    def add_practice_iteration(
        self,
        version: str,
        content: str,
        feedback: str,
        score: float,
    ):
        iteration = PracticeIteration(
            timestamp=datetime.now(),
            version=version,
            content=content,
            feedback=feedback,
            score=score,
            improvements=[],
        )
        self.practice_history.iterations.append(iteration)
        if score > self.practice_history.best_score:
            self.practice_history.best_score = score
            self.practice_history.best_version = version
        self.practice_history.current_version = version

    def get_practice_summary(self) -> Dict[str, Any]:
        iterations = self.practice_history.iterations
        if not iterations:
            return {
                "total_practices": 0,
                "avg_score": 0.0,
                "improvement_trend": "데이터 없음",
            }
        scores = [i.score for i in iterations]
        return {
            "total_practices": len(iterations),
            "avg_score": round(sum(scores) / len(scores), 2),
            "best_score": max(scores),
            "best_version": self.practice_history.best_version or "",
            "recent_practices": len(
                [i for i in iterations if (datetime.now() - i.timestamp).days < 7]
            ),
        }
