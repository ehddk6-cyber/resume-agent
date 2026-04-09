"""기업별 심층 분석 보조 모듈."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Optional

from .company_analyzer import analyze_company
from .models import ApplicantProfile, ApplicationProject, SuccessCase
from .state import load_company_patterns, save_company_patterns
from .workspace import Workspace


class CompanyProfiler:
    def __init__(self, ws: Workspace, success_cases: Optional[list[SuccessCase]] = None):
        self.ws = ws
        self.success_cases = success_cases or []

    def profile_company(
        self,
        project: ApplicationProject,
        job_description: str = "",
        applicant_profile: ApplicantProfile | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        analysis = analyze_company(
            company_name=project.company_name,
            job_title=project.job_title,
            job_description=job_description,
            company_type=project.company_type,
            success_cases=self.success_cases,
        )
        mission_values = self._parse_mission_values(
            "\n".join(
                [
                    project.company_name,
                    project.research_notes,
                    job_description,
                ]
            )
        )
        success_patterns = self._build_success_pattern_stats(
            project.company_name,
            project.job_title,
        )
        profile = {
            "company_name": project.company_name,
            "job_title": project.job_title,
            "mission_keywords": mission_values["mission_keywords"],
            "value_keywords": mission_values["value_keywords"],
            "success_pattern_stats": success_patterns,
            "tailored_tips": self._build_tailored_tips(
                analysis.core_values + analysis.culture_keywords,
                applicant_profile,
            ),
        }
        patterns = load_company_patterns(self.ws)
        patterns[project.company_name or "default"] = profile
        save_company_patterns(self.ws, patterns)
        return profile

    def _parse_mission_values(self, text: str) -> dict[str, list[str]]:
        mission_terms = re.findall(
            r"(고객|공익|혁신|신뢰|정확|협업|성장|책임|도전|문제해결)",
            text,
        )
        counter = Counter(mission_terms)
        keywords = [item for item, _ in counter.most_common(6)]
        return {
            "mission_keywords": keywords[:3],
            "value_keywords": keywords[3:6] if len(keywords) > 3 else keywords[:3],
        }

    def _build_success_pattern_stats(
        self,
        company_name: str,
        job_title: str,
    ) -> dict[str, Any]:
        relevant = [
            case
            for case in self.success_cases
            if (
                (not company_name or company_name in case.company_name)
                and (not job_title or job_title in case.job_title or not case.job_title)
            )
        ]
        phrase_counter: Counter[str] = Counter()
        question_counter: Counter[str] = Counter()
        for case in relevant:
            if case.question_type:
                question_counter[case.question_type.value] += 1
            phrase_counter.update(case.key_phrases[:5])
        return {
            "sample_count": len(relevant),
            "question_type_counts": dict(question_counter),
            "top_phrases": [item for item, _ in phrase_counter.most_common(5)],
        }

    def _build_tailored_tips(
        self,
        values: list[str],
        applicant_profile: ApplicantProfile | dict[str, Any] | None,
    ) -> list[str]:
        tips: list[str] = []
        if values:
            tips.append(f"답변에서 {', '.join(values[:3])} 키워드를 직접 연결하세요.")
        strengths: list[str] = []
        if isinstance(applicant_profile, ApplicantProfile):
            strengths = applicant_profile.strength_keywords
        elif isinstance(applicant_profile, dict):
            strengths = list(applicant_profile.get("signature_strengths", []) or [])
        if strengths:
            tips.append(f"강점은 {', '.join(strengths[:2])} 중심으로 재배치하는 편이 좋습니다.")
        if not tips:
            tips.append("기업 미션과 직무 요구를 한 문장으로 연결하는 연습이 필요합니다.")
        return tips[:3]
