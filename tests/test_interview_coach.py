from resume_agent.interview_coach import InterviewCoach
from resume_agent.models import ApplicantProfile


def test_interview_coach_adds_checklist_for_metric_gap():
    coach = InterviewCoach()
    pack = coach.build_support_pack(
        ApplicantProfile(
            strength_keywords=["문제 해결"],
            weakness_codes=["low_metrics"],
        )
    )

    assert pack["anxiety_management"]
    assert any("성과 숫자" in item for item in pack["interview_day_checklist"])
