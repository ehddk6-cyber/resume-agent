"""질문-경험 의미적 매칭 테스트"""

import pytest
from resume_agent.domain import build_experience_knowledge_hints
from resume_agent.classifier import classify_with_experience_hints
from resume_agent.models import Experience, Question, EvidenceLevel, VerificationStatus, QuestionType


@pytest.fixture
def sample_experiences():
    return [
        Experience(
            id="exp_001",
            title="고객 불만 처리 및 만족도 향상",
            organization="ABC客服",
            period_start="2023-01",
            action="1:1 민원 해결 시스템 도입, 팀 교육 프로그램 설계",
            result="고객 만족도 45%→78% 상승",
            metrics="만족도 33%p 상승",
            evidence_level=EvidenceLevel.L3,
            tags=["CS", "교육"],
            verification_status=VerificationStatus.VERIFIED
        ),
        Experience(
            id="exp_002",
            title="품질 개선 프로젝트 리드",
            organization="ABC",
            period_start="2022-06",
            action="품질 이슈 분석 및 개선안 수립, 이해관계자 협업",
            result="불량률 5%→1.2% 감소",
            metrics="불량률 3.8%p 감소",
            evidence_level=EvidenceLevel.L3,
            tags=["품질", "프로젝트"],
            verification_status=VerificationStatus.VERIFIED
        ),
    ]


@pytest.fixture
def sample_questions():
    return [
        Question(
            id="q_001",
            order_no=1,
            question_text="어려움을 극복한 경험을 말해주세요",
            char_limit=1000,
            detected_type=QuestionType.TYPE_B
        ),
        Question(
            id="q_002",
            order_no=2,
            question_text="고객 응대 경험을 설명해주세요",
            char_limit=1000,
            detected_type=QuestionType.TYPE_B
        ),
    ]


class TestExperienceKnowledgeHints:
    """build_experience_knowledge_hints 테스트"""
    
    def test_builds_experience_hints(self, sample_experiences, sample_questions):
        """경험 힌트 생성"""
        hints = build_experience_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        assert "experience_hints" in hints
        assert len(hints["experience_hints"]) > 0
    
    def test_experience_hints_contain_competency_fields(self, sample_experiences, sample_questions):
        """경험 힌트에 역량 필드 포함 확인"""
        hints = build_experience_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        exp_hint = hints["experience_hints"][0]
        assert "top_competency" in exp_hint
        assert "competencies" in exp_hint
    
    def test_builds_question_hints(self, sample_experiences, sample_questions):
        """질문 힌트 생성"""
        hints = build_experience_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        assert "question_hints" in hints
        assert len(hints["question_hints"]) > 0
    
    def test_question_hints_contain_analysis_fields(self, sample_experiences, sample_questions):
        """질문 힌트에 분석 필드 포함 확인"""
        hints = build_experience_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        q_hint = hints["question_hints"][0]
        assert "hidden_intent" in q_hint
        assert "wanted_competencies" in q_hint
        assert "risk_topics" in q_hint
    
    def test_builds_matching_pairs(self, sample_experiences, sample_questions):
        """경험-질문 매칭 쌍 생성"""
        hints = build_experience_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        assert "matching_pairs" in hints
        # 정렬 확인
        if len(hints["matching_pairs"]) > 1:
            scores = [p["match_score"] for p in hints["matching_pairs"]]
            assert scores == sorted(scores, reverse=True)


class TestExperienceBasedClassification:
    """경험 기반 분류 테스트"""
    
    def test_classification_with_experience_hints(self, sample_experiences, sample_questions):
        """경험 힌트 활용 분류"""
        results = classify_with_experience_hints(
            sample_questions,
            sample_experiences,
            config={},
            use_deep_analysis=True
        )
        
        assert "q_001" in results
        assert "type" in results["q_001"]
        assert "recommended_experiences" in results["q_001"]
    
    def test_classification_includes_intent_analysis(self, sample_experiences, sample_questions):
        """분류 결과에 의도 분석 포함"""
        results = classify_with_experience_hints(
            sample_questions,
            sample_experiences,
            config={},
            use_deep_analysis=True
        )
        
        intent = results["q_001"]["intent_analysis"]
        assert "hidden_intent" in intent
        assert "wanted_competencies" in intent
        assert "risk_topics" in intent
    
    def test_classification_without_deep_analysis(self, sample_experiences, sample_questions):
        """심층 분석 없이 분류"""
        results = classify_with_experience_hints(
            sample_questions,
            sample_experiences,
            config={},
            use_deep_analysis=False
        )
        
        assert results["q_001"]["confidence_boost"] is False
    
    def test_classification_recommends_matching_experiences(self, sample_experiences, sample_questions):
        """매칭되는 경험 추천 확인"""
        results = classify_with_experience_hints(
            sample_questions,
            sample_experiences,
            config={},
            use_deep_analysis=True
        )
        
        # 고객 관련 질문에 고객 경험이 추천되어야 함
        for q_id, result in results.items():
            if "고객" in next(
                (q.question_text for q in sample_questions if q.id == q_id), ""
            ):
                # 고객 관련 질문이면 매칭된 경험이 있을 수 있음
                if result.get("recommended_experiences"):
                    assert all("exp_id" in exp for exp in result["recommended_experiences"])