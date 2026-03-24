import pytest
from resume_agent.domain import classify_question, score_experience, extract_question_keywords
from resume_agent.models import Question, QuestionType, Experience, EvidenceLevel, VerificationStatus

def test_classify_question():
    """질문 유형 분류가 정상적으로 작동하는지 확인합니다."""
    text1 = "당사에 지원하게 된 동기와 직무에 적합한 이유를 서술해 주십시오."
    assert classify_question(text1) == QuestionType.TYPE_A
    
    text2 = "본인이 겪었던 가장 큰 실패와 이를 극복한 경험을 적어주세요."
    assert classify_question(text2) == QuestionType.TYPE_G
    
    text3 = "팀원들과 협업하여 문제를 해결한 경험에 대해 설명하시오."
    assert classify_question(text3) == QuestionType.TYPE_C

def test_extract_question_keywords():
    """질문에서 불용어를 제외한 핵심 키워드 추출을 확인합니다."""
    text = "본인이 지원한 직무와 관련하여 가장 큰 성과를 낸 경험을 기술해 주십시오."
    keywords = extract_question_keywords(text)
    
    # '본인', '지원', '직무', '관련', '경험', '기술', '주십시오'는 불용어
    assert "성과를" in keywords or "성과" in [k.replace("를", "") for k in keywords]
    assert "가장" in keywords

def test_score_experience_priority():
    """우선순위, 증거 수준, 검증 상태에 따른 경험 점수 가중치를 테스트합니다."""
    question = Question(id="q1", order_no=1, question_text="협업 경험", detected_type=QuestionType.TYPE_C)
    
    # 훌륭한 경험 (L3, 검증됨)
    exp_good = Experience(
        id="exp1", title="도서관 프로젝트", organization="도서관", period_start="",
        evidence_level=EvidenceLevel.L3, verification_status=VerificationStatus.VERIFIED,
        metrics="10% 증가", tags=["협업", "소통"]
    )
    
    # 부족한 경험 (L1, 미검증)
    exp_bad = Experience(
        id="exp2", title="단순 아르바이트", organization="편의점", period_start="",
        evidence_level=EvidenceLevel.L1, verification_status=VerificationStatus.NEEDS_VERIFICATION,
        metrics="", tags=["책임감"]
    )
    
    score_good = score_experience(question, exp_good, [], [], None)
    score_bad = score_experience(question, exp_bad, [], [], None)
    
    assert score_good["score"] > score_bad["score"]

def test_score_experience_penalty_for_reuse():
    """이미 사용된 경험에 대한 재사용 페널티가 제대로 적용되는지 확인합니다."""
    question = Question(id="q1", order_no=1, question_text="성장 경험", detected_type=QuestionType.TYPE_D)
    exp = Experience(
        id="exp1", title="동아리장 경험", organization="학교", period_start="",
        evidence_level=EvidenceLevel.L2, verification_status=VerificationStatus.VERIFIED,
        metrics="5명 증가", tags=["성장"]
    )
    
    score_first = score_experience(question, exp, [], [], None)
    score_reused = score_experience(question, exp, [], ["exp1"], None)
    
    assert score_first["score"] > score_reused["score"]
    assert score_first["score"] - score_reused["score"] == 7  # domain.py에 7점 페널티 적용됨
