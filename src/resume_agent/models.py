from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, List, Optional

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
    TYPE_A = "TYPE_A"  # motivation / fit
    TYPE_B = "TYPE_B"  # core capability
    TYPE_C = "TYPE_C"  # collaboration
    TYPE_D = "TYPE_D"  # growth / learning
    TYPE_E = "TYPE_E"  # post-join contribution
    TYPE_F = "TYPE_F"  # work principles
    TYPE_G = "TYPE_G"  # failure and recovery
    TYPE_H = "TYPE_H"  # customer response
    TYPE_I = "TYPE_I"  # prioritization under pressure


class SourceType(str, Enum):
    LOCAL_MARKDOWN = "local_markdown"
    LOCAL_TEXT = "local_text"
    LOCAL_CSV_ROW = "local_csv_row"
    USER_URL_PUBLIC = "user_url_public"
    MANUAL_NOTE = "manual_note"


class ArtifactType(str, Enum):
    COACH = "COACH"
    WRITER = "WRITER"
    INTERVIEW = "INTERVIEW"
    EXPORT = "EXPORT"


class InterviewStyle(str, Enum):
    """면접 스타일"""
    FORMAL = "formal"           # 격식 있는 (대기업, 공공)
    CASUAL = "casual"           # 편안한 (스타트업)
    TECHNICAL = "technical"     # 기술 중심 (IT, 엔지니어링)
    BEHAVIORAL = "behavioral"   # 행동 중심 (영업, 마케팅)


class SuccessPattern(str, Enum):
    """합격 자소서 패턴 유형 (linkareer 데이터 기반)"""
    STAR_STRUCTURE = "star_structure"       # STAR 구조 활용
    QUANTIFIED_RESULT = "quantified_result" # 정량적 성과 강조
    PROBLEM_SOLVING = "problem_solving"     # 문제해결 서사
    COLLABORATION = "collaboration"         # 협업 경험
    GROWTH_STORY = "growth_story"           # 성장 스토리
    CUSTOMER_FOCUS = "customer_focus"       # 고객 중심 사고
    INNOVATION = "innovation"               # 혁신/개선 경험
    ETHICS = "ethics"                       # 윤리/정직 강조


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

    model_config = {
        "populate_by_name": True,
    }
