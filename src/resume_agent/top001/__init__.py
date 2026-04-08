"""
Top 0.01% Interview & Coaching System
"""

from .base_types import (
    LogicalNode,
    LogicalGraph,
    VulnerableLink,
    QuestionChain,
    AttackVector,
    AnswerStyle,
    InterviewPersona,
    CoachingState,
    Hook,
    Story,
    IntroVersions,
    PracticeHistory,
    StrategicSignals,
    EvidenceMap,
    DefenseStrategy,
    CoachingFeedback,
    SocraticQuestion,
    InterviewSimulation,
    PracticeIteration,
    QuestionDepth,
)

from .logical_analyzer import LogicalStructureAnalyzer
from .deep_interrogator import DeepInterrogator
from .adaptive_persona import AdaptivePersonaEngine
from .adaptive_coach import AdaptiveCoachEngine
from .self_intro_mastery import SelfIntroMastery
from .strategic_research import StrategicResearchTranslator
from .evidence_chain import EvidenceChainValidator, Inconsistency
from .integrator import (
    Top001InterviewEngine,
    Top001CoachEngine,
    Top001ResearchTranslator,
)

__version__ = "0.1.0"
__all__ = [
    "LogicalNode",
    "LogicalGraph",
    "VulnerableLink",
    "QuestionChain",
    "AttackVector",
    "AnswerStyle",
    "InterviewPersona",
    "CoachingState",
    "Hook",
    "Story",
    "IntroVersions",
    "PracticeHistory",
    "StrategicSignals",
    "EvidenceMap",
    "DefenseStrategy",
    "CoachingFeedback",
    "SocraticQuestion",
    "InterviewSimulation",
    "PracticeIteration",
    "QuestionDepth",
    "LogicalStructureAnalyzer",
    "DeepInterrogator",
    "AdaptivePersonaEngine",
    "AdaptiveCoachEngine",
    "SelfIntroMastery",
    "StrategicResearchTranslator",
    "EvidenceChainValidator",
    "Inconsistency",
    "Top001InterviewEngine",
    "Top001CoachEngine",
    "Top001ResearchTranslator",
]
