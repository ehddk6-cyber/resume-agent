"""경험 심층 분석기"""

from typing import List, Dict, Optional
from .models import (
    Experience, 
    ExperienceCoreCompetency,
    ExperienceDeepAnalysis,
    QuestionIntentAnalysis,
    Question,
    EvidenceLevel,
    VerificationStatus
)
from .semantic_engine import SemanticSearchEngine, compute_embedding_similarity
import logging

logger = logging.getLogger(__name__)

# 핵심 역량 키워드 매핑
CORE_COMPETENCY_PATTERNS = {
    "고객 중심 사고": {
        "keywords": ["고객", "이용자", "민원", "불만", "응대", "서비스", "경험"],
        "related": ["CS", "고객 만족", "서비스 품질"]
    },
    "문제 해결": {
        "keywords": ["문제", "어려움", "장애", "개선", "해결", "분석", "원인"],
        "related": ["문제해결능력", "추론력", "로직"]
    },
    "팀워크/협업": {
        "keywords": ["팀", "협업", "공동", "협력", "소통", "회의", "동료"],
        "related": ["collaboration", "stakeholder"]
    },
    "리더십": {
        "keywords": ["리드", "팀장", "책임", "결정", "안내", "방향"],
        "related": ["leader", "management"]
    },
    "데이터/분석": {
        "keywords": ["데이터", "수치", "분석", "측정", "지표", "성과", "KPI"],
        "related": ["analytics", "metric", "improvement"]
    },
    "기술 역량": {
        "keywords": ["개발", "기술", "시스템", "아키텍처", "프로그래밍", "툴"],
        "related": ["technical", "skill", "implementation"]
    },
    "커뮤니케이션": {
        "keywords": ["설명", "발표", "보고", "문서", "프리젠테이션", "자료"],
        "related": ["communication", "presentation"]
    },
    "성장 마인드셋": {
        "keywords": ["배우", "실패", "개선", "성장", "노력", "학습", "새로운"],
        "related": ["growth", "learning", "development"]
    }
}


class ExperienceDeepAnalyzer:
    
    def __init__(self, semantic_engine: Optional[SemanticSearchEngine] = None):
        self.semantic_engine = semantic_engine or SemanticSearchEngine()
    
    def analyze_core_competency(self, experience: Experience) -> List[ExperienceCoreCompetency]:
        competencies = []
        combined_text = f"{experience.title} {experience.action} {experience.result} {experience.evidence_text}"
        combined_lower = combined_text.lower()
        
        matched = {}
        for comp_name, pattern in CORE_COMPETENCY_PATTERNS.items():
            kw_score = sum(1 for kw in pattern["keywords"] if kw in combined_lower)
            sem_score = 0
            if self.semantic_engine and pattern.get("related"):
                for rel in pattern["related"]:
                    try:
                        sim = compute_embedding_similarity(combined_text[:500], rel)
                        if sim > 0:
                            sem_score += sim
                    except Exception:
                        pass
            if kw_score > 0 or sem_score > 0:
                matched[comp_name] = {"kw": kw_score, "sem": sem_score}
        
        sorted_comps = sorted(matched.items(), key=lambda x: x[1]["kw"]*2 + x[1]["sem"], reverse=True)[:5]
        
        for comp_name, data in sorted_comps:
            confidence = min((data["kw"] * 2 + data["sem"]) / 10, 1.0)
            kws = [kw for kw in CORE_COMPETENCY_PATTERNS[comp_name]["keywords"] if kw in combined_lower][:3]
            competencies.append(ExperienceCoreCompetency(
                competency=comp_name,
                confidence=round(confidence, 2),
                evidence_keywords=kws,
                interview_relevance=f"{comp_name} 역량 입증에 적합"
            ))
        return competencies
    
    def estimate_interviewer_impression(self, experience: Experience) -> Dict[str, str]:
        impressions = {"신뢰도": "중간", "차별화": "중간", "위험도": "낮음", "전체 평가": "보통"}
        
        if experience.evidence_level == EvidenceLevel.L3:
            impressions["신뢰도"] = "높음" if experience.verification_status == VerificationStatus.VERIFIED else "중간-높음"
        
        has_metrics = bool(experience.metrics and experience.metrics.strip())
        has_contrib = bool(experience.personal_contribution and experience.personal_contribution.strip())
        
        if has_metrics and has_contrib:
            impressions["차별화"] = "높음"
            if impressions["신뢰도"] == "높음":
                impressions["전체 평가"] = "긍정적"
        elif has_metrics or has_contrib:
            impressions["차별화"] = "중간"
        
        risk_count = 0
        generic = ["최선을 다했다", "많은 도움이 되었다", "성공적으로 완료"]
        if any(p in f"{experience.action} {experience.result}" for p in generic):
            risk_count += 1
        if not has_metrics:
            risk_count += 1
        if len(experience.result) < 50:
            risk_count += 1
        
        if risk_count >= 2:
            impressions["위험도"] = "높음"
            impressions["전체 평가"] = "주의 필요"
        elif risk_count == 1:
            impressions["위험도"] = "중간"
        
        return impressions
    
    def find_hidden_strengths(self, experiences: List[Experience]) -> List[str]:
        strengths = []
        all_actions = " ".join([exp.action for exp in experiences])
        
        if any(w in all_actions for w in ["프로세스", "시스템", "자동화", "효율화"]):
            strengths.append("시스템적 사고")
        if sum(1 for w in ["개발", "코드", "아키텍처"] if w in all_actions) >= 2:
            strengths.append("기술적 깊이")
        if any(w in all_actions for w in ["팀", "교육", "멘토링"]):
            strengths.append("팀 개발/리더십")
        
        return strengths
    
    def analyze_question_intent(self, question: Question) -> QuestionIntentAnalysis:
        q_lower = question.question_text.lower()
        
        intents, wanted, risks = [], [], []
        
        if any(w in q_lower for w in ["어려움", "힘들", "극복", "문제"]):
            intents.append("문제 해결 능력 및 스트레스 관리")
            wanted.extend(["문제 해결", "Resilience", "성장 마인드셋"])
            risks.append("불황 경험만 언급")
        
        if any(w in q_lower for w in ["팀", "협업", "공동", "동료"]):
            intents.append("팀워크 및 갈등 해결 능력")
            wanted.extend(["팀워크", "커뮤니케이션", "갈등 해결"])
            risks.append("팀 역할 없이 개인 성과만 강조")
        
        if any(w in q_lower for w in ["실패", "부족"]):
            intents.append("성장과 학습 마인드셋")
            wanted.extend(["성장 마인드셋", "자기 인식"])
            risks.append("실패의 책임을 남에게 전가")
        
        if not intents:
            intents = ["핵심 역량 및 업무 능력 입증"]
            wanted = ["기본 직무 역량"]
        
        return QuestionIntentAnalysis(
            question_id=question.id,
            surface_topic=question.question_text[:30],
            hidden_intent="; ".join(intents),
            core_competencies_sought=wanted[:5],
            risk_topics=risks[:3],
            recommended_approach="구체적 사실 + 개인 기여 + 측정 가능한 성과"
        )
    
    def full_analysis(self, experience: Experience) -> ExperienceDeepAnalysis:
        core = self.analyze_core_competency(experience)
        imps = self.estimate_interviewer_impression(experience)
        concerns = []
        
        if not experience.personal_contribution or len(experience.personal_contribution) < 20:
            concerns.append("개인 기여가 불분명")
        if experience.metrics and experience.verification_status != VerificationStatus.VERIFIED:
            concerns.append("수치가 검증되지 않음")
        
        framing = "일반적 STAR 구조로 작성"
        if core:
            top = core[0].competency
            framing_templates = {
                "고객 중심 사고": f"'{top}'에 초점을 맞춰 작성",
                "문제 해결": "문제 상황 → 본인만의 해결 → 측정 가능한 결과",
                "팀워크/협업": "본인 역할 명시 + 팀 내 기여도 강조",
                "성장 마인드셋": "실패/어려움 → 학습 → 현재 적용"
            }
            framing = framing_templates.get(top, f"'{top}' 역량 입증에 집중한 STAR 구조")
        
        return ExperienceDeepAnalysis(
            experience_id=experience.id,
            core_competencies=core,
            estimated_interviewer_impression=imps,
            hidden_strengths=[],
            potential_concerns=concerns,
            recommended_framing=framing
        )
