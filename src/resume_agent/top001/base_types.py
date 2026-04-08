"""
Top 0.01% Interview & Coaching System - Base Types

Core data models for the enhanced interview and coaching system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class AnswerStyle(Enum):
    """답변 스타일 분류"""

    EVASIVE = auto()
    OVERSTATED = auto()
    FORMULAIC = auto()
    FRAGMENTED = auto()
    BALANCED = auto()


class CoachingState(Enum):
    """코칭 상태 단계"""

    RAPPORT = auto()
    DISCOVERY = auto()
    STRATEGY = auto()
    VALIDATION = auto()
    REHEARSAL = auto()


class QuestionDepth(Enum):
    """질문 깊이"""

    DEPTH_1 = 1
    DEPTH_2 = 2
    DEPTH_3 = 3


@dataclass
class LogicalNode:
    """논리 그래프 노드"""

    id: str
    node_type: str
    content: str
    confidence: float = 1.0
    supporting_evidence: List[str] = field(default_factory=list)
    attacks: List[str] = field(default_factory=list)


@dataclass
class LogicalGraph:
    """답변의 논리 구조 그래프"""

    nodes: Dict[str, LogicalNode] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)
    root_claim: Optional[str] = None

    def get_claims(self) -> List[LogicalNode]:
        return [n for n in self.nodes.values() if n.node_type == "claim"]

    def get_evidence(self) -> List[LogicalNode]:
        return [n for n in self.nodes.values() if n.node_type == "evidence"]

    def get_conclusions(self) -> List[LogicalNode]:
        return [n for n in self.nodes.values() if n.node_type == "conclusion"]


@dataclass
class VulnerableLink:
    """취약한 논리 연결"""

    source_id: str
    target_id: str
    link_type: str
    vulnerability_type: str
    severity: str
    description: str
    attack_vectors: List[str] = field(default_factory=list)


@dataclass
class QuestionChain:
    """3-depth 꼬리질문 체인"""

    primary_question: str
    depth_1_questions: List[str] = field(default_factory=list)
    depth_2_questions: List[str] = field(default_factory=list)
    depth_3_questions: List[str] = field(default_factory=list)
    attack_vectors: List[AttackVector] = field(default_factory=list)


@dataclass
class AttackVector:
    """공격 벡터"""

    name: str
    description: str
    target_type: str
    severity: str
    example_questions: List[str] = field(default_factory=list)


@dataclass
class InterviewPersona:
    """면접관 페르소나"""

    id: str
    name: str
    role: str
    focus_areas: List[str] = field(default_factory=list)
    tone: str = ""
    aggression_level: int = 5
    attack_patterns: List[str] = field(default_factory=list)


@dataclass
class Hook:
    """자기소개 훅"""

    hook_type: str
    content: str
    impact_score: float
    supporting_evidence: Optional[str] = None


@dataclass
class Story:
    """스토리 구조"""

    situation: str
    task: str
    action: str
    result: str
    personal_contribution: str
    metrics: Optional[str] = None


@dataclass
class IntroVersions:
    """계층적 자기소개 버전"""

    elevator_pitch: str
    thirty_second: str
    sixty_second: str
    ninety_second: str
    hooks: List[Hook] = field(default_factory=list)
    core_story: Optional[Story] = None


@dataclass
class PracticeIteration:
    """연습 반복 기록"""

    timestamp: datetime
    version: str
    content: str
    feedback: str
    score: float
    improvements: List[str] = field(default_factory=list)


@dataclass
class PracticeHistory:
    """연습 히스토리"""

    iterations: List[PracticeIteration] = field(default_factory=list)
    current_version: str = ""
    best_version: Optional[str] = None
    best_score: float = 0.0


@dataclass
class StrategicSignals:
    """전략적 신호"""

    core_values_alignment: List[str] = field(default_factory=list)
    competency_matches: List[str] = field(default_factory=list)
    interview_prediction: List[str] = field(default_factory=list)
    differentiation_points: List[str] = field(default_factory=list)


@dataclass
class EvidenceMap:
    """증거 매핑"""

    experience_id: str
    question_types: List[str] = field(default_factory=list)
    strategic_signals: List[str] = field(default_factory=list)
    proof_points: List[str] = field(default_factory=list)


@dataclass
class DefenseStrategy:
    """방어 전략"""

    vulnerable_point: str
    defense_script: str
    backup_evidence: Optional[str] = None
    alternative_frames: List[str] = field(default_factory=list)


@dataclass
class CoachingFeedback:
    """코칭 피드백"""

    strength_points: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)
    specific_suggestions: List[str] = field(default_factory=list)
    next_action: str = ""


@dataclass
class SocraticQuestion:
    """소크라테스 질문"""

    question: str
    intent: str
    expected_insight: str
    follow_up_if_vague: str


@dataclass
class InterviewSimulation:
    """면접 시뮬레이션 결과"""

    question: str
    user_answer: str
    analyzed_graph: LogicalGraph
    vulnerable_links: List[VulnerableLink]
    question_chain: QuestionChain
    persona: InterviewPersona
    feedback: CoachingFeedback
    defense_strategy: DefenseStrategy
