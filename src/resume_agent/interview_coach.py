"""면접 심리 코칭 모듈."""

from __future__ import annotations

from typing import Any

from .models import ApplicantProfile


class InterviewCoach:
    def build_support_pack(
        self,
        applicant_profile: ApplicantProfile | dict[str, Any] | None,
    ) -> dict[str, list[str]]:
        strengths = self._strengths(applicant_profile)
        weak_spots = self._weaknesses(applicant_profile)

        anxiety_management = [
            "면접 30분 전에는 답변 암기보다 호흡 4-6 패턴을 5회 반복하세요.",
            "첫 답변 전 2초 멈춘 뒤 결론 한 문장을 먼저 말하세요.",
        ]
        confidence_exercises = [
            f"대표 강점 2개({', '.join(strengths[:2]) or '직무 적합성'})를 20초 자기확언으로 반복하세요.",
            "성공 경험 하나를 상황-행동-결과 3문장으로 다시 말해보세요.",
        ]
        checklist = [
            "대표 경험 3개의 수치/비교 기준 확인",
            "꼬리질문 대비 증빙 문장 1개씩 준비",
            "첫 문장 템플릿: 결론 → 행동 → 결과",
        ]
        if "low_metrics" in weak_spots:
            checklist.append("성과 숫자가 없는 경험은 사용 우선순위를 낮추기")
        if "low_contribution" in weak_spots:
            checklist.append("팀 성과와 개인 판단을 분리해서 말하기")
        return {
            "anxiety_management": anxiety_management,
            "confidence_exercises": confidence_exercises,
            "interview_day_checklist": checklist[:5],
        }

    def _strengths(self, applicant_profile: ApplicantProfile | dict[str, Any] | None) -> list[str]:
        if isinstance(applicant_profile, ApplicantProfile):
            return applicant_profile.strength_keywords
        if isinstance(applicant_profile, dict):
            return list(applicant_profile.get("signature_strengths", []) or [])
        return []

    def _weaknesses(self, applicant_profile: ApplicantProfile | dict[str, Any] | None) -> set[str]:
        if isinstance(applicant_profile, ApplicantProfile):
            return set(applicant_profile.weakness_codes)
        if isinstance(applicant_profile, dict):
            personal = applicant_profile.get("personalized_profile", {}) or {}
            return set(personal.get("weakness_codes", []) or [])
        return set()
