from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CareerStage(str, Enum):
    ENTRY = "ENTRY"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"


class EvidenceLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_VERIFICATION = "needs_verification"


class QuestionType(str, Enum):
    TYPE_A = "TYPE_A"
    TYPE_B = "TYPE_B"
    TYPE_C = "TYPE_C"
    TYPE_D = "TYPE_D"
    TYPE_E = "TYPE_E"
    TYPE_F = "TYPE_F"
    TYPE_G = "TYPE_G"
    TYPE_H = "TYPE_H"
    TYPE_I = "TYPE_I"
    TYPE_UNKNOWN = "TYPE_UNKNOWN"


class SourceType(str, Enum):
    LOCAL_MARKDOWN = "local_markdown"
    LOCAL_TEXT = "local_text"
    LOCAL_CSV_ROW = "local_csv_row"
    USER_URL_PUBLIC = "user_url_public"
    MANUAL_NOTE = "manual_note"


class ArtifactType(str, Enum):
    COACH = "COACH"
    RESEARCH = "RESEARCH"
    SELF_INTRO = "SELF_INTRO"
    WRITER = "WRITER"
    INTERVIEW = "INTERVIEW"
    EXPORT = "EXPORT"


class InterviewStyle(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"


class SuccessPattern(str, Enum):
    """합격 자소서 패턴 유형 (linkareer 데이터 기반)"""

    STAR_STRUCTURE = "star_structure"  # STAR 구조 활용
    QUANTIFIED_RESULT = "quantified_result"  # 정량적 성과 강조
    PROBLEM_SOLVING = "problem_solving"  # 문제해결 서사
    COLLABORATION = "collaboration"  # 협업 경험
    GROWTH_STORY = "growth_story"  # 성장 스토리
    CUSTOMER_FOCUS = "customer_focus"  # 고객 중심 사고
    INNOVATION = "innovation"  # 혁신/개선 경험
    ETHICS = "ethics"  # 윤리/정직 강조


class UserProfile(BaseModel):
    display_name: str = ""
    career_stage: CareerStage = CareerStage.ENTRY
    target_company_types: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    style_preference: str = "담백하고 근거 중심"


class Experience(BaseModel):
    id: str
    title: str
    organization: str
    period_start: str
    period_end: Optional[str] = None
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    personal_contribution: str = ""
    metrics: str = ""
    evidence_text: str = ""
    evidence_level: EvidenceLevel = EvidenceLevel.L1
    tags: List[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.NEEDS_VERIFICATION
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class Question(BaseModel):
    id: str
    order_no: int
    question_text: str
    char_limit: Optional[int] = None
    detected_type: QuestionType = QuestionType.TYPE_B


class ApplicationProject(BaseModel):
    company_name: str = ""
    job_title: str = ""
    career_stage: CareerStage = CareerStage.ENTRY
    company_type: str = "공공"
    research_notes: str = ""
    tone_style: str = "담백하고 근거 중심"
    priority_experience_order: List[str] = Field(default_factory=list)
    questions: List[Question] = Field(default_factory=list)


class KnowledgeSourceMeta(BaseModel):
    company_name: str = ""
    job_title: str = ""
    season: str = ""
    spec_text: str = ""
    question_count: int = 0


class StructureSignals(BaseModel):
    has_star: bool = False
    has_metrics: bool = False
    warns_against_copying: bool = True


class PatternKB(BaseModel):
    company_name: str = ""
    job_title: str = ""
    season: str = ""
    question_types: List[QuestionType] = Field(default_factory=list)
    structure_summary: str = ""
    structure_signals: StructureSignals = Field(default_factory=StructureSignals)
    spec_keywords: List[str] = Field(default_factory=list)
    retrieval_terms: List[str] = Field(default_factory=list)
    caution: str = "표현 복제 금지. 구조만 참고."
    source_url: Optional[str] = None


class KnowledgeSource(BaseModel):
    id: str
    source_type: SourceType = SourceType.LOCAL_TEXT
    title: str
    url: Optional[str] = None
    raw_text: str = ""
    cleaned_text: str = ""
    meta: KnowledgeSourceMeta = Field(default_factory=KnowledgeSourceMeta)
    pattern: Optional[PatternKB] = None


class ValidationResult(BaseModel):
    passed: bool = False
    missing: List[str] = Field(default_factory=list)
    out_of_order: List[str] = Field(default_factory=list)


class CompanyAnalysis(BaseModel):
    """회사 분석 결과 (linkareer 데이터 기반 패턴 포함)"""

    company_name: str
    company_type: str = "공공"  # 대기업, 중견, 스타트업, 공공, 공기업
    industry: str = ""
    core_values: List[str] = Field(default_factory=list)
    culture_keywords: List[str] = Field(default_factory=list)
    recent_news: List[str] = Field(default_factory=list)
    interview_style: InterviewStyle = InterviewStyle.FORMAL
    success_patterns: List[SuccessPattern] = Field(default_factory=list)
    preferred_evidence_types: List[str] = Field(default_factory=list)
    tone_guide: str = ""
    role_industry_strategy: dict[str, Any] = Field(default_factory=dict)
    success_case_stats: dict[str, Any] = Field(default_factory=dict)
    similar_case_titles: List[str] = Field(default_factory=list)
    discouraged_phrases: List[str] = Field(default_factory=list)


class WritingStyleAnalysis(BaseModel):
    avg_sentence_words: float = 0.0
    avg_sentence_chars: float = 0.0
    dominant_tone: str = "balanced"
    formality_level: str = "balanced"
    sentence_style: str = "balanced"
    evidence_density: float = 0.0
    confidence_tendency: str = "balanced"
    expression_patterns: List[str] = Field(default_factory=list)
    keyword_frequency: Dict[str, int] = Field(default_factory=dict)


class ApplicantProfile(BaseModel):
    profile_id: str = "default"
    source_count: int = 0
    analyzed_text_count: int = 0
    writing_style: WritingStyleAnalysis = Field(default_factory=WritingStyleAnalysis)
    strength_keywords: List[str] = Field(default_factory=list)
    weakness_codes: List[str] = Field(default_factory=list)
    weakness_details: List[str] = Field(default_factory=list)
    recommendation_summary: List[str] = Field(default_factory=list)
    answer_style_preferences: List[str] = Field(default_factory=list)
    coaching_priorities: List[str] = Field(default_factory=list)
    generated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class QuestionAnalysis(BaseModel):
    """질문 분석 결과"""

    question_id: str
    question_text: str
    question_type: QuestionType
    keywords: List[str] = Field(default_factory=list)
    hidden_intent: str = ""  # 질문의 숨겨진 의도
    risk_level: str = "medium"  # low, medium, high
    defense_strategy: str = ""  # 방어 전략
    recommended_patterns: List[SuccessPattern] = Field(default_factory=list)


class AnswerQuality(BaseModel):
    """답변 품질 평가"""

    question_id: str
    answer_text: str
    relevance_score: float = 0.0  # 0.0 ~ 1.0
    specificity_score: float = 0.0  # 0.0 ~ 1.0
    defensibility_score: float = 0.0  # 0.0 ~ 1.0
    originality_score: float = 0.0  # 0.0 ~ 1.0
    overall_score: float = 0.0  # 0.0 ~ 1.0
    detected_patterns: List[SuccessPattern] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class DefenseSimulation(BaseModel):
    """면접 방어 시뮬레이션 결과"""

    primary_question: str
    simulated_answer: str
    follow_up_questions: List[str] = Field(default_factory=list)
    defense_points: List[str] = Field(default_factory=list)
    risk_areas: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)


class SuccessCase(BaseModel):
    """합격 사례 (linkareer_results.csv 기반)"""

    title: str
    company_name: str = ""
    job_title: str = ""
    spec_summary: str = ""
    answer_text: str = ""
    source_url: Optional[str] = None
    detected_patterns: List[SuccessPattern] = Field(default_factory=list)
    question_type: Optional[QuestionType] = None
    key_phrases: List[str] = Field(default_factory=list)

    @classmethod
    def from_csv_row(
        cls,
        title: str,
        company_name: str = "",
        job_title: str = "",
        spec_summary: str = "",
        answer_text: str = "",
        source_url: Optional[str] = None,
        detected_patterns: Optional[List[SuccessPattern]] = None,
    ) -> "SuccessCase":
        """CSV 행에서 SuccessCase 생성. detected_patterns는 외부에서 주입."""
        return cls(
            title=title,
            company_name=company_name,
            job_title=job_title,
            spec_summary=spec_summary,
            answer_text=answer_text,
            source_url=source_url,
            detected_patterns=detected_patterns or [],
        )


class GeneratedArtifact(BaseModel):
    id: str
    artifact_type: ArtifactType
    accepted: bool = False
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_path: Optional[str] = None
    raw_output_path: Optional[str] = None
    validation: ValidationResult = Field(default_factory=ValidationResult)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class OutcomeResult(BaseModel):
    """지원 결과 추적"""
    artifact_id: str
    application_id: str = ""
    company_name: str
    job_title: str = ""
    outcome: Literal[
        "pending", "screening_pass", "screening_fail",
        "interview_invited", "interview_pass", "interview_fail",
        "final_pass", "final_fail", "offer_received", "offer_declined"
    ] = "pending"
    outcome_date: Optional[str] = None
    rejection_reason: Optional[str] = None
    interview_count: int = 0
    notes: Optional[str] = None


class ABTestResult(BaseModel):
    """A/B 테스트 결과"""
    test_id: str
    test_name: str
    strategy_a: str
    strategy_b: str
    sample_size_a: int = 0
    sample_size_b: int = 0
    success_rate_a: float = 0.0
    success_rate_b: float = 0.0
    p_value: Optional[float] = None
    confidence_level: float = 0.95
    winner: Optional[str] = None
    is_significant: bool = False
    start_date: str = ""
    end_date: Optional[str] = None


class ExperienceOutcomeStats(BaseModel):
    """경험-결과 통계"""
    experience_id: str
    experience_title: str
    total_uses: int = 0
    success_count: int = 0
    fail_count: int = 0
    success_rate: float = 0.0
    avg_interview_count: float = 0.0
    question_types_used: List[str] = Field(default_factory=list)
    avg_rating: Optional[float] = None
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_path: Optional[str] = None
    raw_output_path: Optional[str] = None
    validation: ValidationResult = Field(default_factory=ValidationResult)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    model_config = {
        "populate_by_name": True,
    }


class ExperienceCoreCompetency(BaseModel):
    """경험의 핵심 역량 분석 결과"""
    competency: str  # 역량명 (예: "고객 중심 사고")
    confidence: float  # 확신도 0.0~1.0
    evidence_keywords: List[str]  # 근거 키워드
    interview_relevance: str  # 면접관 기대값


class ExperienceDeepAnalysis(BaseModel):
    """경험 심층 분석 결과"""
    experience_id: str
    core_competencies: List[ExperienceCoreCompetency]
    estimated_interviewer_impression: Dict[str, str]
    hidden_strengths: List[str]
    potential_concerns: List[str]
    recommended_framing: str


class QuestionIntentAnalysis(BaseModel):
    """질문의 숨겨진 의도 분석"""
    question_id: str
    surface_topic: str
    hidden_intent: str
    core_competencies_sought: List[str]
    risk_topics: List[str]
    recommended_approach: str
