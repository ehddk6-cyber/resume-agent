import pytest
from resume_agent.domain import (
    build_coach_artifact,
    build_knowledge_hints,
    classify_question,
    extract_question_keywords,
    score_experience,
    allocate_experiences,
    validate_company_research_contract,
    validate_interview_contract,
    validate_writer_contract,
)
from resume_agent.models import (
    ApplicationProject,
    EvidenceLevel,
    Experience,
    Question,
    QuestionType,
    VerificationStatus,
)

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


def test_score_experience_adds_semantic_match_for_related_terms():
    question = Question(
        id="q1",
        order_no=1,
        question_text="민원 처리 경험을 설명해주세요.",
        detected_type=QuestionType.TYPE_H,
    )
    semantic = Experience(
        id="exp1",
        title="고객 응대 기준 정비",
        organization="기관",
        period_start="2024-01-01",
        situation="고객 질문이 반복되었습니다.",
        task="응대 기준을 정리해야 했습니다.",
        action="응대 문안과 안내 기준을 정비했습니다.",
        result="안내 시간을 줄였습니다.",
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
    )
    unrelated = Experience(
        id="exp2",
        title="창고 정리",
        organization="기관",
        period_start="2024-01-01",
        situation="물품이 흩어져 있었습니다.",
        task="보관 위치를 정리했습니다.",
        action="품목을 분류했습니다.",
        result="정리 상태를 개선했습니다.",
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
    )

    score_semantic = score_experience(question, semantic, [], [], None)
    score_unrelated = score_experience(question, unrelated, [], [], None)

    assert score_semantic["semantic_adjustment"] > 0


def test_score_experience_applies_personalization_penalty_for_profile_weakness():
    question = Question(
        id="q-profile",
        order_no=1,
        question_text="지원 직무 적합성을 설명하세요.",
        detected_type=QuestionType.TYPE_A,
    )
    weak = Experience(
        id="exp-profile",
        title="지원 경험",
        organization="기관",
        period_start="2024-01-01",
        action="지원 자료를 정리했습니다.",
        result="업무를 마쳤습니다.",
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
    )

    baseline = score_experience(question, weak, [], [], None)
    personalized = score_experience(
        question,
        weak,
        [],
        [],
        None,
        candidate_profile={
            "personalized_profile": {
                "weakness_codes": ["low_metrics", "low_contribution"],
                "strength_keywords": [],
                "writing_style": {"dominant_tone": "logical"},
            }
        },
    )

    assert personalized["score"] < baseline["score"]
    assert personalized["personalization_adjustment"] < 0


def test_build_knowledge_hints_returns_profile_hint_without_sources():
    project = ApplicationProject(company_name="테스트기업", job_title="백엔드")

    result = build_knowledge_hints(
        [],
        project,
        applicant_profile={
            "personalized_profile": {
                "strength_keywords": ["문제 해결"],
                "weakness_codes": ["low_metrics"],
                "recommendation_summary": ["결론을 먼저 말하세요."],
                "writing_style": {"dominant_tone": "logical"},
            }
        },
    )

    assert len(result) == 1
    assert result[0]["title"] == "지원자 프로파일 힌트"


def test_build_coach_artifact_includes_risks_and_recommendations():
    project = ApplicationProject(
        company_name="테스트기업",
        job_title="백엔드",
        questions=[
            Question(
                id="q1",
                order_no=1,
                question_text="협업 경험을 설명해 주세요.",
                detected_type=QuestionType.TYPE_C,
            )
        ],
    )
    experiences = [
        Experience(
            id="exp1",
            title="프로젝트 경험",
            organization="팀",
            period_start="2024-01-01",
            evidence_level=EvidenceLevel.L2,
            verification_status=VerificationStatus.NEEDS_VERIFICATION,
            tags=["협업"],
        )
    ]
    gap_report = {
        "needs_verification": ["프로젝트 경험"],
        "question_risks": [
            {
                "question_id": "q1",
                "order_no": 1,
                "question_type": QuestionType.TYPE_C,
                "best_score": 4,
                "risk": "high",
            }
        ],
        "recommendations": ["정량 근거를 보강하세요."],
    }

    artifact = build_coach_artifact(project, experiences, gap_report)

    assert "## QUESTION RISKS" in artifact["rendered"]
    assert "## RECOMMENDATIONS" in artifact["rendered"]
    assert "best_score=4" in artifact["rendered"]
    assert "정량 근거를 보강하세요." in artifact["rendered"]


def test_build_coach_artifact_renders_question_strategies_and_writer_contract():
    project = ApplicationProject(
        company_name="테스트기업",
        job_title="백엔드",
        questions=[
            Question(
                id="q1",
                order_no=1,
                question_text="지원 동기를 설명해 주세요.",
                detected_type=QuestionType.TYPE_A,
            )
        ],
    )
    experiences = [
        Experience(
            id="exp1",
            title="민원 기준 정비",
            organization="기관",
            period_start="2024-01-01",
            tags=["직무역량"],
        )
    ]
    artifact = build_coach_artifact(
        project,
        experiences,
        {"needs_verification": [], "question_risks": [], "recommendations": []},
        question_strategies=[
            {
                "question_order": 1,
                "core_message": "운영 안정성을 입증한다.",
                "winning_angle": "열정보다 운영 기준으로 간다.",
                "losing_angle": "추상적 성장담으로 흐른다.",
                "primary_experience_title": "민원 기준 정비",
                "differentiation_line": "평균 지원자와 다르게 기준과 증빙을 말한다.",
            }
        ],
        writer_contract={
            "mode_label": "adaptive mode",
            "headline": "문항별 단일 전략을 고정한다.",
            "answer_checklist": ["핵심 주장 1개"],
        },
    )

    assert "## QUESTION STRATEGIES" in artifact["rendered"]
    assert "## WRITER CONTRACT" in artifact["rendered"]
    assert "운영 안정성을 입증한다." in artifact["rendered"]
    assert "adaptive mode" in artifact["rendered"]


def test_build_coach_artifact_renders_personalized_sections():
    project = ApplicationProject(company_name="테스트기업", job_title="백엔드")
    artifact = build_coach_artifact(
        project,
        [],
        {"needs_verification": [], "question_risks": [], "recommendations": []},
        candidate_profile={
            "profile_summary": "논리형 지원자입니다.",
            "personalized_profile": {
                "strength_keywords": ["문제 해결", "근거 중심 서술"],
                "weakness_details": ["성과 수치가 자주 빠집니다."],
                "coaching_priorities": ["결론-행동-결과 순서를 고정하세요."],
            },
        },
        company_profile={
            "mission_keywords": ["공익", "정확"],
            "value_keywords": ["책임"],
            "tailored_tips": ["공익 관점을 먼저 연결하세요."],
        },
        interview_support_pack={
            "anxiety_management": ["호흡 4-6 패턴을 5회 반복하세요."],
            "confidence_exercises": ["강점 2개를 다시 읽으세요."],
            "interview_day_checklist": ["수치 근거 3개를 확인하세요."],
        },
    )

    assert "## PERSONALIZED PROFILE" in artifact["rendered"]
    assert "## COMPANY FIT SIGNALS" in artifact["rendered"]
    assert "## INTERVIEW PSYCHOLOGY PACK" in artifact["rendered"]


def test_allocate_experiences_uses_outcome_summary_to_prefer_defensible_experience():
    question = Question(
        id="q1",
        order_no=1,
        question_text="지원 직무와 관련해 본인이 잘할 수 있는 이유를 설명하세요.",
        detected_type=QuestionType.TYPE_A,
    )
    weak = Experience(
        id="exp-weak",
        title="일반 지원 경험",
        organization="기관A",
        period_start="2024-01-01",
        situation="업무를 수행했습니다.",
        task="지원 업무를 맡았습니다.",
        action="열심히 했습니다.",
        result="문제 없이 마쳤습니다.",
        evidence_level=EvidenceLevel.L1,
        verification_status=VerificationStatus.NEEDS_VERIFICATION,
        tags=["지원"],
    )
    strong = Experience(
        id="exp-strong",
        title="민원 기준 정비",
        organization="기관B",
        period_start="2024-01-01",
        situation="반복 민원이 많았습니다.",
        task="안내 기준을 정리해야 했습니다.",
        action="기준표와 응대 문안을 재작성했습니다.",
        result="반복 문의 12건을 한 장으로 정리해 안내 시간을 줄였습니다.",
        personal_contribution="기준표 초안을 직접 만들고 수정했습니다.",
        metrics="반복 문의 12건 정리",
        evidence_text="민원 응대 메모와 처리 기록",
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
        tags=["고객응대", "의사소통", "직무역량"],
    )

    allocations = allocate_experiences(
        [question],
        [weak, strong],
        [],
        outcome_summary={
            "matched_feedback_count": 3,
            "outcome_breakdown": {"fail_interview": 2, "pass": 1},
            "top_rejection_reasons": [{"reason": "근거 부족", "count": 2}],
        },
    )

    assert allocations[0]["experience_id"] == "exp-strong"
    assert "결과 학습 반영" in allocations[0]["reason"]


def test_allocate_experiences_uses_strategy_outcome_summary_for_question_type():
    question = Question(
        id="q1",
        order_no=1,
        question_text="지원 직무와 관련해 본인이 잘할 수 있는 이유를 설명하세요.",
        detected_type=QuestionType.TYPE_A,
    )
    stable = Experience(
        id="exp-stable",
        title="안내 기준 정비",
        organization="기관A",
        period_start="2024-01-01",
        situation="반복 안내 문의가 많았습니다.",
        task="응대 기준을 정리해야 했습니다.",
        action="안내 기준표를 정리했습니다.",
        result="응대 흐름을 표준화했습니다.",
        personal_contribution="기준표 초안을 직접 작성했습니다.",
        metrics="반복 문의 12건 정리",
        evidence_text="안내 기준표 초안",
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
        tags=["직무역량", "의사소통"],
    )
    risky = Experience(
        id="exp-risky",
        title="지원 업무 참여",
        organization="기관B",
        period_start="2024-01-01",
        situation="지원 업무를 수행했습니다.",
        task="요청 사항을 처리했습니다.",
        action="안내를 도왔습니다.",
        result="업무를 마쳤습니다.",
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
        tags=["지원", "의사소통"],
    )

    allocations = allocate_experiences(
        [question],
        [stable, risky],
        [],
        strategy_outcome_summary={
            "experience_stats_by_question_type": {
                "TYPE_A": {
                    "exp-stable": {
                        "total_uses": 3,
                        "pass_count": 3,
                        "fail_count": 0,
                        "pass_rate": 1.0,
                        "pattern_breakdown": {
                            "coach|공공|TYPE_A": {
                                "total_uses": 2,
                                "pass_count": 2,
                                "fail_count": 0,
                                "pass_rate": 1.0,
                            }
                        },
                        "top_rejection_reasons": [],
                    },
                    "exp-risky": {
                        "total_uses": 2,
                        "pass_count": 0,
                        "fail_count": 2,
                        "pass_rate": 0.0,
                        "pattern_breakdown": {
                            "coach|공공|TYPE_A": {
                                "total_uses": 2,
                                "pass_count": 0,
                                "fail_count": 2,
                                "pass_rate": 0.0,
                            }
                        },
                        "top_rejection_reasons": [{"reason": "개인 기여 불명확", "count": 2}],
                    },
                }
            }
        },
        current_pattern="coach|공공|TYPE_A",
    )

    assert allocations[0]["experience_id"] == "exp-stable"
    assert "실제 결과 통계" in allocations[0]["reason"]


def test_allocate_experiences_uses_feedback_adaptation_plan():
    question = Question(
        id="q1",
        order_no=1,
        question_text="지원 동기와 적합성을 설명하세요.",
        detected_type=QuestionType.TYPE_A,
    )
    risky = Experience(
        id="exp-risky",
        title="지원 업무 참여",
        organization="기관B",
        period_start="2024-01-01",
        situation="지원 업무를 수행했습니다.",
        task="지원 동기와 적합성을 설명할 자료 정리를 맡았습니다.",
        action="지원 근거와 적합성 자료를 정리했습니다.",
        result="지원 동기 자료를 정리했습니다.",
        personal_contribution="지원 근거 문구를 직접 정리했습니다.",
        tags=["직무역량", "지원동기"],
    )
    stable = Experience(
        id="exp-stable",
        title="민원 기준 정비",
        organization="기관A",
        period_start="2024-01-01",
        situation="반복 민원이 많았습니다.",
        task="응대 기준을 정리해야 했습니다.",
        action="기준표를 만들어 안내 문구를 통일했습니다.",
        result="응대 흐름을 정리했습니다.",
        tags=["의사소통"],
    )

    baseline = allocate_experiences(
        [question],
        [risky, stable],
        [],
    )
    allocations = allocate_experiences(
        [question],
        [risky, stable],
        [],
        feedback_adaptation_plan={
            "risky_question_types": [
                {
                    "question_type": "TYPE_A",
                    "weak_experiences": [
                        {
                            "experience_id": "exp-risky",
                            "top_rejection_reasons": [{"reason": "근거 부족", "count": 2}],
                        }
                    ],
                }
            ]
        },
    )

    assert baseline[0]["experience_id"] == "exp-risky"
    assert allocations[0]["experience_id"] == "exp-stable"


def test_allocate_experiences_limits_strategy_adjustment_when_samples_are_small():
    question = Question(
        id="q1",
        order_no=1,
        question_text="지원 직무와 관련해 본인이 잘할 수 있는 이유를 설명하세요.",
        detected_type=QuestionType.TYPE_A,
    )
    experience = Experience(
        id="exp-strong",
        title="안내 기준 정비",
        organization="기관A",
        period_start="2024-01-01",
        situation="반복 안내 문의가 많았습니다.",
        task="응대 기준을 정리해야 했습니다.",
        action="안내 기준표를 정리했습니다.",
        result="응대 흐름을 표준화했습니다.",
        personal_contribution="기준표 초안을 직접 작성했습니다.",
        metrics="반복 문의 12건 정리",
        evidence_text="안내 기준표 초안",
        evidence_level=EvidenceLevel.L2,
        verification_status=VerificationStatus.VERIFIED,
        tags=["직무역량", "의사소통"],
    )

    low_sample = score_experience(
        question,
        experience,
        [],
        [],
        None,
        strategy_outcome_summary={
            "experience_stats_by_question_type": {
                "TYPE_A": {
                    "exp-strong": {
                        "total_uses": 1,
                        "pass_count": 1,
                        "fail_count": 0,
                        "weighted_pass_score": 4,
                        "weighted_fail_score": 0,
                        "weighted_net_score": 4,
                        "pattern_breakdown": {},
                    }
                }
            }
        },
    )
    enough_sample = score_experience(
        question,
        experience,
        [],
        [],
        None,
        strategy_outcome_summary={
            "experience_stats_by_question_type": {
                "TYPE_A": {
                    "exp-strong": {
                        "total_uses": 5,
                        "pass_count": 4,
                        "fail_count": 1,
                        "weighted_pass_score": 12,
                        "weighted_fail_score": 1,
                        "weighted_net_score": 11,
                        "pattern_breakdown": {},
                    }
                }
            }
        },
    )

    assert enough_sample["strategy_adjustment"] > low_sample["strategy_adjustment"]


def test_validate_writer_contract_rejects_empty_block_body():
    text = """## 블록 1: ASSUMPTIONS & MISSING FACTS

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
- 답변

## 블록 4: SELF-CHECK
- 점검
"""
    result = validate_writer_contract(text)

    assert result["passed"] is False
    assert "## 블록 1: ASSUMPTIONS & MISSING FACTS" in result["empty"]


def test_validate_writer_contract_requires_char_count_and_self_check():
    text = """## 블록 1: ASSUMPTIONS & MISSING FACTS
- 가정

## 블록 2: OUTLINE
- 개요

## 블록 3: DRAFT ANSWERS
- 답변 본문

## 블록 4: SELF-CHECK
- 점검 항목
"""
    result = validate_writer_contract(text)

    assert result["passed"] is False
    assert "문항별 글자수 표기" in result["semantic_missing"]
    assert "SELF-CHECK PASS/FAIL" in result["semantic_missing"]


def test_validate_interview_contract_accepts_filled_sections():
    text = """## 블록 1: INTERVIEW ASSUMPTIONS
- 가정

## 블록 2: INTERVIEW STRATEGY
- 전략

## 블록 3: EXPECTED QUESTIONS MAP
- 2차 꼬리질문 맵

## 블록 4: ANSWER FRAMES
- 30초 답변 프레임
"""
    result = validate_interview_contract(text)

    assert result["passed"] is True


def test_validate_interview_contract_requires_followup_and_30sec_frame():
    text = """## 블록 1: INTERVIEW ASSUMPTIONS
- 가정

## 블록 2: INTERVIEW STRATEGY
- 전략

## 블록 3: EXPECTED QUESTIONS MAP
- 질문 맵

## 블록 4: ANSWER FRAMES
- 답변 프레임
"""
    result = validate_interview_contract(text)

    assert result["passed"] is False
    assert "연쇄 꼬리질문" in result["semantic_missing"]
    assert "30초 답변 프레임" in result["semantic_missing"]


def test_validate_company_research_contract_requires_type_links_and_self_check():
    text = """## 블록 1: 확정 정보
- 회사명
- [NEEDS_VERIFICATION]

## 블록 2: 입력 기반 핵심 신호
- 신호

## 블록 3: 직무 분석
- 분석

## 블록 4: 회사/조직 적합성 해석
- 해석

## 블록 5: 자소서 연결 전략
- 지원동기 전략

## 블록 6: 면접 대비 포인트
- 면접 포인트

## 블록 7: SELF-CHECK
- 점검
"""
    result = validate_company_research_contract(text)

    assert result["passed"] is False
    assert "SELF-CHECK PASS/FAIL" in result["semantic_missing"]
    assert "자소서 유형 연결" in result["semantic_missing"]
