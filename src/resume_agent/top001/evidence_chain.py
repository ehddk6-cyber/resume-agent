from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base_types import (
    EvidenceMap,
)

if TYPE_CHECKING:
    from ..models import Experience, Question


class Inconsistency:
    def __init__(
        self,
        inconsistency_type: str,
        severity: str,
        description: str,
        related_experiences: List[str],
    ):
        self.inconsistency_type = inconsistency_type
        self.severity = severity
        self.description = description
        self.related_experiences = related_experiences

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.inconsistency_type,
            "severity": self.severity,
            "description": self.description,
            "experiences": self.related_experiences,
        }


class EvidenceChainValidator:
    def validate_temporal_consistency(
        self, experiences: List[Experience]
    ) -> List[Inconsistency]:
        inconsistencies = []
        if not experiences or len(experiences) < 2:
            return inconsistencies

        exp_list = [
            (
                e.id,
                getattr(e, "start_date", ""),
                getattr(e, "end_date", ""),
                getattr(e, "organization", ""),
                getattr(e, "title", ""),
            )
            for e in experiences
        ]

        for i in range(len(exp_list)):
            for j in range(i + 1, len(exp_list)):
                id1, start1, end1, org1, title1 = exp_list[i]
                id2, start2, end2, org2, title2 = exp_list[j]

                if not start1 or not start2:
                    continue

                if start1 == start2 and org1 == org2 and title1 != title2:
                    inconsistencies.append(
                        Inconsistency(
                            inconsistency_type="overlapping_roles",
                            severity="high",
                            description=f"동일 조직({org1})에서 동시에 다른 역할({title1} vs {title2})을 수행한 것으로 파악됩니다",
                            related_experiences=[id1, id2],
                        )
                    )

                if end1 and start2:
                    if end1 > start2:
                        date_format = r"\d{4}-\d{2}"
                        if re.match(date_format, start1) and re.match(
                            date_format, end1
                        ):
                            inconsistencies.append(
                                Inconsistency(
                                    inconsistency_type="timeline_overlap",
                                    severity="medium",
                                    description=f"경험 기간이 겹칩니다: {title1}({start1}~{end1}) vs {title2}({start2}~)",
                                    related_experiences=[id1, id2],
                                )
                            )

        return inconsistencies

    def validate_role_consistency(
        self, experiences: List[Experience]
    ) -> List[Inconsistency]:
        inconsistencies = []
        if not experiences:
            return inconsistencies

        for exp in experiences:
            action = getattr(exp, "action", "") or ""
            personal = getattr(exp, "personal_contribution", "") or ""
            result = getattr(exp, "result", "") or ""

            if ("주도" in action or "负责" in action) and not personal:
                inconsistencies.append(
                    Inconsistency(
                        inconsistency_type="vague_personal_contribution",
                        severity="medium",
                        description=f"'{getattr(exp, 'title', '경험')}'에서 '주도' 표현 사용 but personal contribution 없음",
                        related_experiences=[exp.id],
                    )
                )

            vague_actions = ["함께", "协作", "共同"]
            if any(va in action for va in vague_actions):
                if personal and any(
                    word in personal for word in ["전체", "모든", "팀"]
                ):
                    inconsistencies.append(
                        Inconsistency(
                            inconsistency_type="team_vs_personal",
                            severity="high",
                            description=f"'{getattr(exp, 'title', '경험')}'에서 팀 활동과 개인 기여가模糊합니다",
                            related_experiences=[exp.id],
                        )
                    )

        return inconsistencies

    def validate_cross_question_allocation(
        self,
        allocations: List[Dict[str, Any]],
        experiences: List[Experience],
    ) -> List[Dict[str, Any]]:
        issues = []
        if not allocations:
            return issues

        exp_usage_count: Dict[str, int] = {}
        org_usage_by_position: Dict[str, Dict[int, str]] = {}

        for i, alloc in enumerate(allocations):
            exp_id = alloc.get("experience_id", "")
            org = ""
            for exp in experiences:
                if exp.id == exp_id:
                    org = getattr(exp, "organization", "") or ""
                    break

            exp_usage_count[exp_id] = exp_usage_count.get(exp_id, 0) + 1

            if org:
                if org not in org_usage_by_position:
                    org_usage_by_position[org] = {}
                org_usage_by_position[org][i] = exp_id

        for exp_id, count in exp_usage_count.items():
            if count > 1:
                issues.append(
                    {
                        "type": "overused_experience",
                        "severity": "high" if count > 2 else "medium",
                        "experience_id": exp_id,
                        "reuse_count": count,
                        "message": f"경험이 {count}개 문항에 재사용되었습니다. 다양성 확보를 위해 다른 경험을 고려하세요.",
                    }
                )

        for org, positions in org_usage_by_position.items():
            positions_list = sorted(positions.keys())
            for i in range(len(positions_list) - 1):
                if positions_list[i + 1] - positions_list[i] == 1:
                    issues.append(
                        {
                            "type": "consecutive_same_org",
                            "severity": "medium",
                            "organization": org,
                            "positions": [positions_list[i], positions_list[i + 1]],
                            "message": f"동일 조직({org}) 경험이 연속 문항에 배치되었습니다. 다른 관점이나 기간의 경험으로 분리하세요.",
                        }
                    )

        return issues

    def suggest_experience_additions(
        self,
        experiences: List[Experience],
        questions: List[Question],
        allocations: List[Dict[str, Any]],
    ) -> List[str]:
        suggestions = []
        if not experiences:
            return ["경험 카드가 비어 있습니다. 최소 3개 이상의 경험을 추가하세요."]

        exp_ids_in_use = {a.get("experience_id") for a in allocations}
        unused_experiences = [e for e in experiences if e.id not in exp_ids_in_use]

        if len(experiences) < len(questions):
            suggestions.append(
                f"문항 수({len(questions)}) 대비 경험 수({len(experiences)})가 부족합니다. "
                f"최소 {len(questions)}개의 다양한 경험을 준비하세요."
            )

        if len(unused_experiences) > len(experiences) * 0.5:
            suggestions.append(
                f"{len(unused_experiences)}개 경험이 배분되지 않았습니다. "
                f"문항별 특성애 맞는 경험 선택을 검토하세요."
            )

        action_texts = [getattr(e, "action", "") or "" for e in experiences]
        has_quantified = any(
            re.search(r"\d+(?:\.\d+)?%|\d+배|\d+건", getattr(e, "metrics", "") or "")
            for e in experiences
        )
        if not has_quantified:
            suggestions.append(
                "정량적 근거가 있는 경험이 부족합니다. "
                "수치나 비교 데이터가 포함된 경험을 추가하면 설득력이 높아집니다."
            )

        l3_count = sum(
            1
            for e in experiences
            if getattr(e, "evidence_level", None)
            and "L3" in str(getattr(e, "evidence_level", ""))
        )
        if l3_count == 0:
            suggestions.append(
                "L3 증거 수준(정량적 결과+증빙)이 있는 경험이 없습니다. "
                "면접에서 방어 가능한 검증된 경험을 추가하세요."
            )

        return suggestions

    def get_coverage_report(
        self,
        experiences: List[Experience],
        questions: List[Question],
        allocations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        exp_ids = {a.get("experience_id") for a in allocations}
        l3_count = sum(
            1
            for e in experiences
            if getattr(e, "evidence_level", None)
            and "L3" in str(getattr(e, "evidence_level", ""))
        )
        verified_count = sum(
            1
            for e in experiences
            if getattr(e, "verification_status", None)
            and "VERIFIED" in str(getattr(e, "verification_status", ""))
        )

        return {
            "total_experiences": len(experiences),
            "experiences_in_use": len(exp_ids),
            "l3_experiences": l3_count,
            "verified_experiences": verified_count,
            "total_questions": len(questions),
            "allocated_questions": len(allocations),
            "uncovered_question_count": len(questions) - len(allocations),
            "coverage_rate": round(len(allocations) / max(len(questions), 1), 2),
        }
