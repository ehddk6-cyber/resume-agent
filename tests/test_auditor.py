import pytest
from resume_agent.scoring import audit_facts
from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

def test_audit_facts_detection_rate():
    """Auditor가 허위 수치를 얼마나 잘 잡아내는지 테스트합니다."""
    # 1. 원본 경험 데이터 (진실)
    experiences = [
        Experience(
            id="exp1", title="인턴", organization="A사", period_start="",
            metrics="성과 10% 달성, 5건 계약", result="수익 2배 증가",
            evidence_level=EvidenceLevel.L3
        )
    ]
    
    # 2. 정상적인 텍스트 (Pass 해야 함)
    text_ok = "인턴 시절 10%의 성과를 냈고 5건의 계약을 성사시켰습니다."
    warnings_ok = audit_facts(text_ok, experiences)
    assert len(warnings_ok) == 0
    
    # 3. 허위 수치 텍스트 (Fail 해야 함)
    text_fake = "인턴 시절 25%의 성과를 냈고 10건의 계약을 성사시켰습니다."
    warnings_fake = audit_facts(text_fake, experiences)
    
    # "25%"와 "10건" 두 가지 모두 잡아내야 함
    assert len(warnings_fake) >= 1
    assert any("25%" in w for w in warnings_fake)
    assert any("10건" in w for w in warnings_fake)
    
    # 4. 정교한 위조 (학점 조작)
    experiences_gpa = [Experience(id="e2", title="학교", organization="U", period_start="", result="학점 3.5/4.5", metrics="3.5")]
    text_gpa_fake = "저는 성실하여 4.2/4.5의 학점을 유지했습니다."
    warnings_gpa = audit_facts(text_gpa_fake, experiences_gpa)
    assert any("4.2/4.5" in w for w in warnings_gpa)

def test_audit_facts_false_positive_risk():
    """정상적인 수치를 오탐할 위험이 있는지 확인합니다."""
    experiences = [Experience(id="e3", title="봉사", organization="B", period_start="", result="100시간 달성")]
    
    # "100시간"이 원본에 있는데 텍스트에 "100시간"이 있으면 통과해야 함
    text = "봉사활동을 100시간 했습니다."
    warnings = audit_facts(text, experiences)
    assert len(warnings) == 0
