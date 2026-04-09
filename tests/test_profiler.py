from pathlib import Path

from resume_agent.models import Experience
from resume_agent.profiler import ApplicantProfiler, build_candidate_profile_payload


def _experience(
    experience_id: str,
    *,
    action: str,
    result: str,
    personal_contribution: str = "",
    metrics: str = "",
    evidence_text: str = "",
    title: str = "프로젝트 경험",
) -> Experience:
    return Experience(
        id=experience_id,
        title=title,
        organization="테스트기관",
        period_start="2024-01-01",
        action=action,
        result=result,
        personal_contribution=personal_contribution,
        metrics=metrics,
        evidence_text=evidence_text,
    )


def test_build_profile_extracts_strengths_and_recommendations():
    profiler = ApplicantProfiler()
    profile = profiler.build_profile(
        [
            _experience(
                "exp-1",
                action="고객 문의 유형을 분석하고 안내 기준을 정리했습니다.",
                result="반복 문의 12건을 한 장으로 정리했습니다.",
                personal_contribution="기준표 초안을 직접 작성했습니다.",
                metrics="12건 정리",
                evidence_text="민원 응대 메모",
                title="민원 기준 정비",
            )
        ]
    )

    assert profile.source_count == 1
    assert profile.strength_keywords
    assert profile.recommendation_summary
    assert profile.writing_style.expression_patterns


def test_build_profile_marks_metric_weakness_when_evidence_is_sparse():
    profiler = ApplicantProfiler()
    profile = profiler.build_profile(
        [
            _experience(
                "exp-1",
                action="열심히 대응했습니다.",
                result="성공적으로 마무리했습니다.",
            )
        ]
    )

    assert "low_metrics" in profile.weakness_codes
    assert any("수치" in item for item in profile.weakness_details)


def test_build_candidate_profile_payload_contains_personalized_snapshot():
    profiler = ApplicantProfiler()
    profile = profiler.build_profile(
        [
            _experience(
                "exp-1",
                action="기준을 분석하고 개선했습니다.",
                result="처리 시간을 30% 줄였습니다.",
                metrics="30% 감소",
            )
        ]
    )

    payload = build_candidate_profile_payload(profile)

    assert "personalized_profile" in payload
    assert payload["signature_strengths"]
    assert payload["writing_style"]["evidence_density"] >= 0
