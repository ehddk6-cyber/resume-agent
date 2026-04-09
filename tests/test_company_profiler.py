from pathlib import Path

from resume_agent.company_profiler import CompanyProfiler
from resume_agent.models import ApplicationProject, SuccessCase
from resume_agent.profiler import ApplicantProfiler
from resume_agent.state import initialize_state, load_company_patterns
from resume_agent.workspace import Workspace


def test_company_profiler_saves_company_pattern(tmp_path: Path):
    ws = Workspace(tmp_path)
    initialize_state(ws)
    experiences = []
    applicant_profile = ApplicantProfiler().build_profile(experiences)
    profiler = CompanyProfiler(
        ws,
        [
            SuccessCase(
                title="합격 사례",
                company_name="테스트기업",
                job_title="백엔드",
                key_phrases=["문제 해결", "운영 기준"],
            )
        ],
    )

    result = profiler.profile_company(
        ApplicationProject(
            company_name="테스트기업",
            job_title="백엔드",
            research_notes="고객 신뢰와 정확성을 강조합니다.",
        ),
        applicant_profile=applicant_profile,
    )

    assert result["company_name"] == "테스트기업"
    assert load_company_patterns(ws)["테스트기업"]["tailored_tips"]
