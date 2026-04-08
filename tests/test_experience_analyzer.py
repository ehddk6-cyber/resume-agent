"""경험 심층 분석기 테스트"""

import pytest
from resume_agent.models import (
    Experience,
    Question,
    EvidenceLevel,
    VerificationStatus,
    QuestionType,
    ExperienceCoreCompetency,
    ExperienceDeepAnalysis,
    QuestionIntentAnalysis,
)
from resume_agent.experience_analyzer import ExperienceDeepAnalyzer, CORE_COMPETENCY_PATTERNS


@pytest.fixture
def analyzer():
    return ExperienceDeepAnalyzer()


@pytest.fixture
def sample_experience():
    return Experience(
        id="exp-001",
        title="고객 민원 처리 시스템 개발",
        organization="ABC Corp",
        period_start="2022-01",
        period_end="2022-12",
        situation="고객 민원 처리 시간이 平均 3일 소요되어 불만이 증가하고 있었습니다.",
        task="민원 처리 프로세스를 자동화하여 처리 시간을 단축해야 했습니다.",
        action="NLP 기반 민원 분류 시스템을 개발하고 기존 수동 처리 프로세스를 자동화했습니다.",
        result="민원 처리 시간을 3일에서 4시간으로 단축하고, 고객 만족도 85%로 향상시켰습니다.",
        personal_contribution="시스템 아키텍처 설계 및 핵심 NLP 모듈 개발을 담당했습니다.",
        metrics="처리 시간 90% 단축, 만족도 85%",
        evidence_text="실제 운영 데이터 기반",
        evidence_level=EvidenceLevel.L3,
        verification_status=VerificationStatus.VERIFIED,
    )


@pytest.fixture
def sample_question():
    return Question(
        id="q-001",
        order_no=1,
        question_text="가장 어려웠던 문제를 극복한 경험을 말씀해 주세요.",
        char_limit=500,
        detected_type=QuestionType.TYPE_B,
    )


class TestCoreCompetencyAnalysis:
    """핵심 역량 분석 테스트"""

    def test_analyze_core_competency_returns_list(self, analyzer, sample_experience):
        result = analyzer.analyze_core_competency(sample_experience)
        assert isinstance(result, list)

    def test_analyze_core_competency_finds_problem_solving(self, analyzer):
        exp = Experience(
            id="test-001",
            title="문제 해결 프로젝트",
            organization="Test",
            period_start="2023-01",
            action="시스템 장애 원인을 분석하고 해결책을 구현했습니다.",
            result="장애 복구",
        )
        result = analyzer.analyze_core_competency(exp)
        competencies = [c.competency for c in result]
        assert "문제 해결" in competencies

    def test_analyze_core_competency_finds_customer_focus(self, analyzer, sample_experience):
        result = analyzer.analyze_core_competency(sample_experience)
        competencies = [c.competency for c in result]
        assert "고객 중심 사고" in competencies

    def test_analyze_core_competency_finds_technical_skill(self, analyzer):
        exp = Experience(
            id="test-002",
            title="시스템 개발",
            organization="Test",
            period_start="2023-01",
            action="새로운 시스템을 개발했습니다.",
            result="성공",
        )
        result = analyzer.analyze_core_competency(exp)
        competencies = [c.competency for c in result]
        assert "기술 역량" in competencies

    def test_confidence_score_in_range(self, analyzer, sample_experience):
        result = analyzer.analyze_core_competency(sample_experience)
        for comp in result:
            assert 0.0 <= comp.confidence <= 1.0

    def test_evidence_keywords_not_empty(self, analyzer, sample_experience):
        result = analyzer.analyze_core_competency(sample_experience)
        for comp in result:
            assert isinstance(comp.evidence_keywords, list)


class TestInterviewerImpression:
    """면접관 인상 예측 테스트"""

    def test_estimate_impression_returns_dict(self, analyzer, sample_experience):
        result = analyzer.estimate_interviewer_impression(sample_experience)
        assert isinstance(result, dict)
        assert "신뢰도" in result
        assert "차별화" in result
        assert "위험도" in result
        assert "전체 평가" in result

    def test_verified_l3_high_trust(self, analyzer, sample_experience):
        result = analyzer.estimate_interviewer_impression(sample_experience)
        assert result["신뢰도"] == "높음"

    def test_generic_phrases_increase_risk(self, analyzer):
        exp = Experience(
            id="test-003",
            title="프로젝트",
            organization="Test",
            period_start="2023-01",
            action="최선을 다했습니다.",
            result="많은 도움이 되었습니다.",
        )
        result = analyzer.estimate_interviewer_impression(exp)
        assert result["위험도"] == "높음"


class TestQuestionIntentAnalysis:
    """질문 의도 분석 테스트"""

    def test_analyze_question_intent_returns_result(self, analyzer, sample_question):
        result = analyzer.analyze_question_intent(sample_question)
        assert isinstance(result, QuestionIntentAnalysis)

    def test_difficulty_keywords_detected(self, analyzer):
        q = Question(
            id="q-002",
            order_no=1,
            question_text="어려운 상황을 극복한 경험을 말씀하세요.",
        )
        result = analyzer.analyze_question_intent(q)
        assert "문제 해결" in result.hidden_intent
        assert "문제 해결" in result.core_competencies_sought

    def test_teamwork_keywords_detected(self, analyzer):
        q = Question(
            id="q-003",
            order_no=1,
            question_text="팀과 협업하여 달성한 성과가 있나요?",
        )
        result = analyzer.analyze_question_intent(q)
        assert "팀워크" in result.hidden_intent

    def test_failure_keywords_detected(self, analyzer):
        q = Question(
            id="q-004",
            order_no=1,
            question_text="실패한 경험과 그것에서 배운 점을 말씀하세요.",
        )
        result = analyzer.analyze_question_intent(q)
        assert "성장" in result.hidden_intent


class TestFullAnalysis:
    """전체 심층 분석 테스트"""

    def test_full_analysis_returns_result(self, analyzer, sample_experience):
        result = analyzer.full_analysis(sample_experience)
        assert isinstance(result, ExperienceDeepAnalysis)
        assert result.experience_id == sample_experience.id

    def test_full_analysis_includes_concerns(self, analyzer):
        exp = Experience(
            id="test-004",
            title="프로젝트",
            organization="Test",
            period_start="2023-01",
            action="작업",
            result="완료",
        )
        result = analyzer.full_analysis(exp)
        assert "개인 기여가 불분명" in result.potential_concerns


class TestHiddenStrengths:
    """숨겨진 강점 패턴 테스트"""

    def test_find_hidden_strengths_systematic(self, analyzer):
        exps = [
            Experience(
                id="exp-1",
                title="자동화",
                organization="Test",
                period_start="2023-01",
                action="프로세스 자동화 프로젝트 진행",
                result="효율성 향상",
            ),
            Experience(
                id="exp-2",
                title="시스템",
                organization="Test",
                period_start="2023-02",
                action="시스템 개선 작업",
                result="성공",
            ),
        ]
        result = analyzer.find_hidden_strengths(exps)
        assert "시스템적 사고" in result
