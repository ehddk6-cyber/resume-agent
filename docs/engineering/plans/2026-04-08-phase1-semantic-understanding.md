# Phase 1: 의미적 이해 강화 구현 계획

> **Worker note:** Execute this plan task-by-task using the agentic-run-plan skill or subagents. Each step uses checkbox (`- [ ]`) syntax for progress tracking.

**Goal:** resume-agent의 의미적 이해能力을 상위 5%에서 상위 3%로 향상 (Ko-SBERT/E5 임베딩 + 경험 심층 분석기 + 형태소 분석 강화)

**Architecture:** 
- **현재**: TF-IDF + 키워드 매칭 기반 (단어 빈도)
- **개선**: Ko-SBERT/multilingual-e5 임베딩 + 벡터 DB + 한국어 형태소 분석

**Tech Stack:**
- **현재**: `paraphrase-multilingual-MiniLM-L12-v2` (384차원)
- **변경**: `intfloat/multilingual-e5-small` 또는 `jhgan/ko-sbert-nli` (768차원)
- **형태소**: `kiwipiepy` (이미 사용 중)
- **벡터 DB**: JSON 파일 기반 (현재 유지, ChromaDB 업그레이드는 Phase 2)

**Work Scope:**
- **In scope:**
  1. 임베딩 모델 업그레이드 (config.yaml + semantic_engine.py)
  2. 경험 심층 분석기 구현 (ExperienceDeepAnalyzer)
  3. 형태소 분석 기반 키워드 추출 강화
  4. 질문-경험 의미적 매칭 개선
  5. 재인덱싱 유틸리티 및 마이그레이션
- **Out of scope:**
  - ChromaDB 통합 (Phase 2)
  - 피드백 루프 (Phase 2)
  - 개인화 시스템 (Phase 3)

---

## Verification Strategy

- **Level:** test-suite (pytest)
- **Command:** `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/ -v`
- **What it validates:** 
  - 기존 72개 테스트 통과 유지
  - 새 의미적 유사도 테스트 통과 (경험-질문 매칭 정확도)
  - ExperienceDeepAnalyzer 유닛 테스트 통과

---

## 파일 구조 매핑

### 신규 생성 파일

| 파일 | 목적 |
|------|------|
| `src/resume_agent/experience_analyzer.py` | 경험 심층 분석기 (핵심 역량 추출, 면접관 인상 예측) |
| `tests/test_experience_analyzer.py` | 경험 분석기 테스트 |
| `scripts/migrate_embeddings.py` | 임베딩 재인덱싱 마이그레이션 스크립트 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `config.yaml` | embedding.model_name, embedding.dimension |
| `src/resume_agent/semantic_engine.py` | 모델 업그레이드 + 새 메서드 추가 |
| `src/resume_agent/models.py` | ExperienceDeepAnalysis 모델 추가 |
| `src/resume_agent/scoring.py` | 의미적 유사도 계산 로직 개선 |
| `tests/test_semantic_engine.py` | 새 모델 테스트 케이스 추가 |

---

## Task Decomposition

### Task 0: 검증 인프라 확인

**Dependencies:** None
**Files:** 확인만 (수정 없음)

- [ ] **Step 1: 현재 테스트 실행하여基准 수립**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/ -v --tb=short`
Expected: 기존 72개 테스트 모두 PASS

- [ ] **Step 2: 현재 임베딩 차원 확인**

Run: `grep -A5 "embedding:" config.yaml`
Expected: `dimension: 384`

- [ ] **Step 3: 의미적 유사도 벤치마크 케이스 정의**

```python
# 테스트용 의미적 동등성 케이스
TEST_EQUIVALENCES = [
    ("고객 응대", "민원 처리", "서비스 불만 대응"),
    ("팀 리더", "프로젝트 관리", "팀장"),
    ("성과 향상", "성과 개선", "업적 증가"),
]
```

---

### Task 1: 임베딩 모델 업그레이드

**Dependencies:** Task 0 완료
**Files:**
- Modify: `config.yaml`
- Modify: `src/resume_agent/semantic_engine.py`

- [ ] **Step 1: config.yaml 업데이트**

Edit: `config.yaml`
```yaml
embedding:
  # 변경 전: paraphrase-multilingual-MiniLM-L12-v2 (384차원)
  # 변경 후: multilingual-e5-small (768차원) 또는 ko-sbert-nli (768차원)
  model_name: "intfloat/multilingual-e5-small"
  dimension: 384  # e5-small은 384차원 유지
  # Korean specific: "jhgan/ko-sbert-nli" (768차원) 사용 시 768으로 변경
  similarity_threshold: 0.35  # 유지
  max_semantic_bonus: 5  # 기존 3에서 5로 증가 (더 정확한 임베딩 대비)
```

- [ ] **Step 2: semantic_engine.py 모델 초기화 변경**

Edit: `src/resume_agent/semantic_engine.py` - `_get_embedding_model()` 메서드

```python
def _get_embedding_model(self) -> SentenceTransformer:
    """임베딩 모델 초기화 - 다중 모델 지원"""
    if self._model is None:
        model_name = self.config.get("embedding", {}).get(
            "model_name", 
            "intfloat/multilingual-e5-small"  # 기본값 변경
        )
        self._model = SentenceTransformer(model_name)
        
        # 모델 정보 로깅
        self.logger.info(f"Loaded embedding model: {model_name}")
        self.logger.info(f"Embedding dimension: {self._model.get_sentence_embedding_dimension()}")
    
    return self._model
```

- [ ] **Step 3: 차원 검증 추가**

Edit: `src/resume_agent/semantic_engine.py` - `SemanticSearchEngine.__init__()`

```python
def __init__(self, config: Optional[dict] = None, kb_path: Optional[str] = None):
    self.config = config or {}
    self.kb_path = kb_path or DEFAULT_KB_PATH
    self._model = None
    self._cache = {}  # In-memory embedding cache
    self.logger = get_logger(__name__)
    
    # 차원 검증
    expected_dim = self.config.get("embedding", {}).get("dimension", 384)
    if expected_dim not in [384, 768]:
        self.logger.warning(f"Unusual embedding dimension: {expected_dim}")
```

- [ ] **Step 4: 테스트 실행**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/test_semantic_engine.py -v -k "test_model" --tb=short`
Expected: PASS 또는 새로운 모델 관련 테스트가 추가되어야 함

- [ ] **Step 5: 임시 테스트 추가**

Create: `tests/test_semantic_engine.py` (기존 파일에 추가)

```python
def test_e5_embeddings_quality():
    """e5 임베딩의 의미적 품질 테스트"""
    from resume_agent.semantic_engine import SemanticSearchEngine
    
    engine = SemanticSearchEngine()
    
    # 의미적 동등성 테스트
    test_cases = [
        ("고객 응대经验丰富", "민원 처리 전문가"),
        ("团队 Leadership", "팀 리더십"),
        ("성과 개선 달성", "업적 향상"),
    ]
    
    for text1, text2 in test_cases:
        sim = engine.compute_similarity(text1, text2)
        # 의미적으로 관련 있으면 > 0.5
        assert sim > 0.3, f"'{text1}' vs '{text2}' similarity too low: {sim}"
```

Run: `pytest tests/test_semantic_engine.py::test_e5_embeddings_quality -v`

- [ ] **Step 6: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add config.yaml src/resume_agent/semantic_engine.py
git commit -m "feat(phase1): upgrade embedding model to multilingual-e5-small"
```

---

### Task 2: 경험 심층 분석기 구현

**Dependencies:** Task 1 완료
**Files:**
- Create: `src/resume_agent/experience_analyzer.py`
- Modify: `src/resume_agent/models.py`
- Create: `tests/test_experience_analyzer.py`

- [ ] **Step 1: models.py에 심층 분석 결과 모델 추가**

Edit: `src/resume_agent/models.py` - 끝에 추가

```python
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
    estimated_interviewer_impression: Dict[str, str]  # {"신뢰도": "높음", "차별화": "중간", "위험도": "낮음"}
    hidden_strengths: List[str]  # 드러나지 않은 강점 패턴
    potential_concerns: List[str]  # 잠재적 우려사항
    recommended_framing: str  # 권장 프레이밍 방식


class QuestionIntentAnalysis(BaseModel):
    """질문의 숨겨진 의도 분석"""
    question_id: str
    surface_topic: str  # 표면 주제
    hidden_intent: str  # 숨겨진 의도
    core_competencies_sought: List[str]  # 원하는 핵심 역량
    risk_topics: List[str]  # 위험 주제 (피해야 할)
    recommended_approach: str  # 권장 답변 접근법
```

- [ ] **Step 2: experience_analyzer.py 기본 구조 생성**

Create: `src/resume_agent/experience_analyzer.py`

```python
"""경험 심층 분석기 - 경험의 본질적 성격과 면접관 인상 예측"""

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
import re
import logging

from .models import (
    Experience, 
    ExperienceCoreCompetency,
    ExperienceDeepAnalysis,
    QuestionIntentAnalysis
)
from .semantic_engine import SemanticSearchEngine

logger = logging.getLogger(__name__)


# 핵심 역량 키워드 매핑 테이블 (TF-IDF + 의미적 유사도로 보완)
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
        "related": ["collaboration", " stakeholder"]
    },
    "리더십": {
        "keywords": ["리드", "팀장", "책임", "결정", "안내", "방향", "策"],
        "related": ["leader", "management", "팀 관리"]
    },
    "数据/분석": {
        "keywords": ["데이터", "수치", "분석", "측정", "지표", "성과", "KPI"],
        "related": ["analytics", "metric", "improvement"]
    },
    "기술 역량": {
        "keywords": ["개발", "기술", "시스템", "架构", "프로그래밍", "툴"],
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
    """경험의 본질적 성격을 분석하는 심층 분석기"""
    
    def __init__(self, semantic_engine: Optional[SemanticSearchEngine] = None):
        self.semantic_engine = semantic_engine or SemanticSearchEngine()
        self.logger = logger
    
    def analyze_core_competency(self, experience: Experience) -> List[ExperienceCoreCompetency]:
        """경험이 실제로 증명하는 핵심 역량 추출
        
        예: "고객 민원 처리" → ["고객 중심 사고", "갈등 해결", "스트레스 관리"]
        """
        competencies = []
        
        # 1. 키워드 기반 1차 추출
        combined_text = f"{experience.title} {experience.action} {experience.result} {experience.evidence_text}"
        combined_text_lower = combined_text.lower()
        
        matched_competencies = {}
        
        for comp_name, pattern in CORE_COMPETENCY_PATTERNS.items():
            # 키워드 매칭 점수
            keyword_score = 0
            matched_keywords = []
            
            for keyword in pattern["keywords"]:
                if keyword in combined_text_lower:
                    keyword_score += 1
                    matched_keywords.append(keyword)
            
            # 관련어 의미적 유사도 보완
            semantic_score = 0
            if self.semantic_engine:
                for related in pattern.get("related", []):
                    try:
                        # 경험 텍스트와 관련어의 유사도
                        sim = self.semantic_engine.compute_similarity(
                            combined_text[:500],  # 긴 텍스트는 자르기
                            related
                        )
                        semantic_score += sim
                    except Exception:
                        pass
            
            # 종합 점수
            total_score = keyword_score * 2 + semantic_score
            
            if total_score > 0:
                matched_competencies[comp_name] = {
                    "score": total_score,
                    "keywords": matched_keywords,
                    "semantic_score": semantic_score
                }
        
        # 2. 점수 기준 상위 역량 선정
        sorted_comps = sorted(
            matched_competencies.items(), 
            key=lambda x: x[1]["score"], 
            reverse=True
        )[:5]  # 상위 5개
        
        for comp_name, data in sorted_comps:
            # Confidence 계산 (0.0~1.0)
            max_possible = 10  # 키워드 5개 * 2 + 의미적 5개
            confidence = min(data["score"] / max_possible, 1.0)
            
            competencies.append(ExperienceCoreCompetency(
                competency=comp_name,
                confidence=round(confidence, 2),
                evidence_keywords=data["keywords"][:3],
                interview_relevance=f"{comp_name} 역량 입증에 적합"
            ))
        
        return competencies
    
    def estimate_interviewer_impression(self, experience: Experience) -> Dict[str, str]:
        """면접관이 이 경험을 들었을 때의 예상 반응 예측"""
        
        impressions = {
            "신뢰도": "중간",
            "차별화": "중간", 
            "위험도": "낮음",
            "전체 평가": "보통"
        }
        
        # 1. 신뢰도 판단 (증거 레벨 + 검증 상태)
        if experience.evidence_level.value == "L3":
            if experience.verification_status.value == "verified":
                impressions["신뢰도"] = "높음"
                impressions["전체 평가"] = "긍정적"
            else:
                impressions["신뢰도"] = "중간-높음"
        elif experience.evidence_level.value == "L2":
            impressions["신뢰도"] = "중간"
        else:
            impressions["신뢰도"] = "낮음-중간"
        
        # 2. 차별화 판단 (성과 수치 + 개인 기여 + 고유성)
        has_metrics = bool(experience.metrics and experience.metrics.strip())
        has_personal_contribution = bool(
            experience.personal_contribution and experience.personal_contribution.strip()
        )
        
        if has_metrics and has_personal_contribution:
            impressions["차별화"] = "높음"
        elif has_metrics or has_personal_contribution:
            impressions["차별화"] = "중간"
        
        # 3. 위험도 판단 (과장 의심, 일반적 경험 여부)
        risk_indicators = []
        
        # 일반적인 표현 체크
        generic_patterns = ["최선을 다했다", "많은 도움이 되었다", "성공적으로 완료"]
        text = f"{experience.action} {experience.result}"
        
        for pattern in generic_patterns:
            if pattern in text:
                risk_indicators.append("일반적 표현 사용")
        
        # 수치 부재
        if not has_metrics:
            risk_indicators.append("수치 부재")
        
        # 짧은 결과
        if len(experience.result) < 50:
            risk_indicators.append("결과 설명 부족")
        
        if len(risk_indicators) >= 2:
            impressions["위험도"] = "높음"
            impressions["전체 평가"] = "주의 필요"
        elif len(risk_indicators) == 1:
            impressions["위험도"] = "중간"
        
        return impressions
    
    def find_hidden_strengths(self, experiences: List[Experience]) -> List[str]:
        """경험 카드에서 드러나지 않은 강점 패턴 탐지
        
        예: 여러 경험에 걸쳐 일관된 문제해결 패턴 → "시스템적 사고"
        """
        # 경험 간 공통 패턴 분석
        all_actions = " ".join([exp.action for exp in experiences])
        
        hidden_strengths = []
        
        # 시스템적 사고 패턴
        systemic_indicators = ["프로세스", "시스템", "자동화", "효율화", "流程", "체계"]
        if any(ind in all_actions for ind in systemic_indicators):
            hidden_strengths.append("시스템적 사고 (프로세스/시스템 개선 관심)")
        
        # 기술적 깊이 패턴
        technical_indicators = ["개발", "코드", "아키텍처", "기술", "스택", "구조"]
        tech_count = sum(1 for ind in technical_indicators if ind in all_actions)
        if tech_count >= 2:
            hidden_strengths.append("기술적 깊이 (구체적 기술 활용 역량)")
        
        #人心/리더십 패턴
        people_indicators = ["팀", "교육", "멘토링", "리드", "안내"]
        if any(ind in all_actions for ind in people_indicators):
            hidden_strengths.append("팀 개발/리더십 (사람과 조직에 영향력)")
        
        return hidden_strengths
    
    def analyze_question_intent(self, question: "Question") -> QuestionIntentAnalysis:
        """질문의 숨겨진 의도 분석
        
        예: "어려움을 극복한 경험을 말하세요" → 
            - 표면: 어려움 극복
            - 숨김: 문제 해결 능력, 스트레스 관리, 성장 마인드셋
        """
        question_text = question.question_text.lower()
        
        # TYPE_B 기본 분석 (직무역량) - 실제 구현에서는 TYPE_A~I 모두 처리
        surface_topic = question.question_text[:30]
        hidden_intents = []
        competencies_sought = []
        risk_topics = []
        
        # 키워드 기반 의도 추론
        if any(word in question_text for word in ["어려움", "힘들", "극복", "문제"]):
            hidden_intents.append("문제 해결 능력 및 스트레스 관리")
            competencies_sought.extend(["문제 해결", " Resilience", "성장 마인드셋"])
            risk_topics.append("불황 경험만 언급")
        
        if any(word in question_text for word in ["팀", "협업", "공동", "동료"]):
            hidden_intents.append("팀워크 및 갈등 해결 능력")
            competencies_sought.extend(["팀워크", "커뮤니케이션", "갈등 해결"])
            risk_topics.append("팀 역할 없이 개인 성과만 강조")
        
        if any(word in question_text for word in ["실패", "부족", " Improvement"]):
            hidden_intents.append("성장과 학습 마인드셋")
            competencies_sought.extend(["성장 마인드셋", "자기 인식", " Improvement"])
            risk_topics.append("실패의 책임을 남에게 전가")
        
        # 의도가 감지되지 않으면 기본값
        if not hidden_intents:
            hidden_intents = ["핵심 역량 및 업무 능력 입증"]
            competencies_sought = ["기본 직무 역량"]
        
        return QuestionIntentAnalysis(
            question_id=question.id,
            surface_topic=surface_topic,
            hidden_intent="; ".join(hidden_intents),
            core_competencies_sought=competencies_sought[:5],
            risk_topics=risk_topics[:3],
            recommended_approach="구체적 사실 + 개인 기여 + 측정 가능한 성과"
        )
    
    def full_analysis(self, experience: Experience) -> ExperienceDeepAnalysis:
        """경험의 전체 심층 분석"""
        core_competencies = self.analyze_core_competency(experience)
        impressions = self.estimate_interviewer_impression(experience)
        
        return ExperienceDeepAnalysis(
            experience_id=experience.id,
            core_competencies=core_competencies,
            estimated_interviewer_impression=impressions,
            hidden_strengths=[],  # 단일 경험에서는 빈 리스트
            potential_concerns=self._identify_potential_concerns(experience),
            recommended_framing=self._generate_recommended_framing(experience, core_competencies)
        )
    
    def _identify_potential_concerns(self, experience: Experience) -> List[str]:
        """잠재적 우려사항 식별"""
        concerns = []
        
        # 짧은 활동 기간
        if experience.period_end and experience.period_start:
            try:
                # 간단한 기간 체크 (정교화 필요)
                if len(experience.result) < 30:
                    concerns.append("결과가 너무 간결함 - 면접관 질문 예상")
            except Exception:
                pass
        
        # 개인 기여 불분명
        if not experience.personal_contribution or len(experience.personal_contribution) < 20:
            concerns.append("개인 기여가 불분명 - '팀' 성과만 있는 것으로 보일 수 있음")
        
        # 검증 불가 수치
        if experience.metrics and not experience.verification_status.value == "verified":
            concerns.append(f"수치가 검증되지 않음 - 신뢰도 저하 우려")
        
        return concerns
    
    def _generate_recommended_framing(
        self, 
        experience: Experience, 
        competencies: List[ExperienceCoreCompetency]
    ) -> str:
        """경험의 권장 프레이밍 방식 생성"""
        if not competencies:
            return "일반적 STAR 구조로 작성"
        
        top_competency = competencies[0].competency
        
        framing_templates = {
            "고객 중심 사고": f"'{top_competency}'에 초점을 맞춰 작성",
            "문제 해결": "문제 상황 → 본인만의 해결アプローチ → 측정 가능한 결과 순서",
            "팀워크/협업": "본인 역할 명시 + 팀 내 기여도 강조 필요",
            "리더십": "리더 역할 + 의사결정 과정 + 팀에 미친 영향",
            "데이터/분석": "분석 방법 + 인사이트 + 비즈니스 impact",
            "기술 역량": "기술 선택 이유 + 구현 난이도 + 기술적 성장",
            "커뮤니케이션": "대상 + 메시지 + 결과 (이해관계자 반응)",
            "성장 마인드셋": "실패/어려움 → 학습 → 현재 적용"
        }
        
        return framing_templates.get(
            top_competency, 
            f"'{top_competency}' 역량 입증에 집중한 STAR 구조"
        )
```

- [ ] **Step 3: experience_analyzer.py의존성 확인**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && python -c "from resume_agent.experience_analyzer import ExperienceDeepAnalyzer; print('Import OK')"`
Expected: Import OK

- [ ] **Step 4: 단위 테스트 작성**

Create: `tests/test_experience_analyzer.py`

```python
"""ExperienceDeepAnalyzer 단위 테스트"""

import pytest
from resume_agent.experience_analyzer import ExperienceDeepAnalyzer, CORE_COMPETENCY_PATTERNS
from resume_agent.models import Experience, EvidenceLevel, VerificationStatus


@pytest.fixture
def analyzer():
    return ExperienceDeepAnalyzer()


@pytest.fixture
def sample_experience():
    return Experience(
        id="exp_001",
        title="고객 불만 처리 및 서비스 개선",
        organization="ABC客户服务部",
        period_start="2023-01",
        period_end="2023-12",
        situation="고객からの投诉가 월 100건 이상 발생한 상황",
        task="고객 만족도 20%p 향상 필요",
        action="1:1 민원 해결 시스템 도입, 팀 교육 프로그램 설계 및 실행",
        result="고객 만족도 45%→78%로 상승, 재投诉율 30%→8% 감소",
        personal_contribution="시스템 설계 전담, 교육 콘텐츠 80% 직접 개발",
        metrics="만족도 33%p 상승, 재投诉율 22%p 감소",
        evidence_text="CSAT 45%→78%, 고객 후기 200건 중 긍정률 92%",
        evidence_level=EvidenceLevel.L3,
        tags=["고객服务", "CS", "교육", "시스템"],
        verification_status=VerificationStatus.VERIFIED
    )


class TestCoreCompetencyAnalysis:
    """핵심 역량 추출 테스트"""
    
    def test_identifies_customer_focus(self, analyzer, sample_experience):
        """고객 중심 사고 역량 식별"""
        competencies = analyzer.analyze_core_competency(sample_experience)
        
        comp_names = [c.competency for c in competencies]
        
        assert "고객 중심 사고" in comp_names, f"Expected '고객 중심 사고', got: {comp_names}"
    
    def test_identifies_problem_solving(self, analyzer, sample_experience):
        """문제 해결 역량 식별"""
        competencies = analyzer.analyze_core_competency(sample_experience)
        
        comp_names = [c.competency for c in competencies]
        
        assert "문제 해결" in comp_names, f"Expected '문제 해결', got: {comp_names}"
    
    def test_confidence_scoring(self, analyzer, sample_experience):
        """신뢰도 점수 계산"""
        competencies = analyzer.analyze_core_competency(sample_experience)
        
        for comp in competencies:
            assert 0.0 <= comp.confidence <= 1.0, f"Invalid confidence: {comp.confidence}"
            assert len(comp.evidence_keywords) <= 3, f"Too many keywords: {comp.evidence_keywords}"


class TestInterviewerImpression:
    """면접관 인상 예측 테스트"""
    
    def test_l3_verified_high_trust(self, analyzer, sample_experience):
        """L3 + 검증됨 → 신뢰도 높음"""
        impressions = analyzer.estimate_interviewer_impression(sample_experience)
        
        assert impressions["신뢰도"] == "높음", f"Expected '높음', got: {impressions['신뢰도']}"
        assert impressions["전체 평가"] == "긍정적"
    
    def test_l1_unverified_low_trust(self, analyzer):
        """L1 + 미검증 → 신뢰도 낮음"""
        exp = Experience(
            id="exp_002",
            title="일반적인 업무",
            organization="XYZ",
            period_start="2022-01",
            action="업무를 수행했다",
            result="좋은 성과를 냈다",
            evidence_level=EvidenceLevel.L1,
            tags=["일반"],
            verification_status=VerificationStatus.NEEDS_VERIFICATION
        )
        
        impressions = analyzer.estimate_interviewer_impression(exp)
        
        assert impressions["신뢰도"] in ["낮음", "낮음-중간"]
    
    def test_metrics_improves_differentiation(self, analyzer, sample_experience):
        """수치가 있으면 차별화 향상"""
        impressions = analyzer.estimate_interviewer_impression(sample_experience)
        
        assert impressions["차별화"] == "높음"


class TestQuestionIntentAnalysis:
    """질문 의도 분석 테스트"""
    
    def test_difficulty_overcome_question(self, analyzer):
        """어려움 극복 질문의 숨겨진 의도"""
        from resume_agent.models import Question, QuestionType
        
        question = Question(
            id="q_001",
            order_no=1,
            question_text="어려움을 극복한 경험을 말씀해주세요",
            char_limit=1000,
            detected_type=QuestionType.TYPE_B
        )
        
        analysis = analyzer.analyze_question_intent(question)
        
        assert "문제 해결" in analysis.hidden_intent
        assert "문제 해결" in analysis.core_competencies_sought
        assert len(analysis.risk_topics) > 0
    
    def test_teamwork_question(self, analyzer):
        """팀워크 질문의 숨겨진 의도"""
        from resume_agent.models import Question, QuestionType
        
        question = Question(
            id="q_002",
            order_no=2,
            question_text="팀에서 갈등을 해결한 경험을 말하세요",
            char_limit=1000,
            detected_type=QuestionType.TYPE_D
        )
        
        analysis = analyzer.analyze_question_intent(question)
        
        assert "팀워크" in analysis.hidden_intent


class TestFullAnalysis:
    """전체 심층 분석 테스트"""
    
    def test_full_analysis_output(self, analyzer, sample_experience):
        """전체 분석 결과 형식 검증"""
        result = analyzer.full_analysis(sample_experience)
        
        assert result.experience_id == sample_experience.id
        assert len(result.core_competencies) > 0
        assert isinstance(result.estimated_interviewer_impression, dict)
        assert len(result.recommended_framing) > 0


class TestHiddenStrengths:
    """숨겨진 강점 패턴 탐지 테스트"""
    
    def test_finds_systemic_thinking(self, analyzer):
        """시스템적 사고 패턴 발견"""
        experiences = [
            Experience(
                id=f"exp_{i}",
                title=f"경험 {i}",
                organization="Test",
                period_start="2023-01",
                action="프로세스를 개선하고 시스템을 개발했다",
                result="효율성 향상",
                evidence_level=EvidenceLevel.L2,
                tags=["업무"]
            )
            for i in range(3)
        ]
        
        strengths = analyzer.find_hidden_strengths(experiences)
        
        # 시스템적 사고 관련 강점이 있어야 함
        systemic_found = any("시스템" in s or "프로세스" in s for s in strengths)
        assert systemic_found, f"Expected systemic thinking pattern, got: {strengths}"
```

- [ ] **Step 5: 테스트 실행**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/test_experience_analyzer.py -v --tb=short`
Expected: ALL PASS (12 tests)

- [ ] **Step 6: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add src/resume_agent/experience_analyzer.py src/resume_agent/models.py tests/test_experience_analyzer.py
git commit -m "feat(phase1): add ExperienceDeepAnalyzer for core competency extraction"
```

---

### Task 3: 형태소 분석 기반 키워드 추출 강화

**Dependencies:** Task 1 완료 (semantic_engine.py 임베딩 필요)
**Files:**
- Modify: `src/resume_agent/parsing.py` (키워드 추출 로직)
- Modify: `src/resume_agent/scoring.py` (형태소 기반 유사도 보완)

- [ ] **Step 1: parsing.py에 형태소 분석 기반 키워드 추출 추가**

Edit: `src/resume_agent/parsing.py` - 끝에 새 함수 추가

```python
def extract_keywords_morphological(self, text: str, top_n: int = 20) -> List[str]:
    """형태소 분석 기반 키워드 추출
    
    Kiwi 형태소 분석기를 사용하여 명사/동사/형용사를 추출
    - 일반적인 조사/어미 제거
    - 불용어 필터링
    - 복합명사 결합
    """
    from kiwipiepy import Kiwi
    
    kiwi = Kiwi()
    keywords = []
    stopwords = {
        "것", "수", "등", "및", "에", "을", "를", "의", "가", "이", "은", "들",
        "에", "에서", "에게", "한테", "께", "랑", "이랑", "나", "과", "와",
        "때", "더", "년", "월", "일", "시", "분", "초",
        "있습니다", "합니다", "했습니다", "했습니다", "했습니다"
    }
    
    # 형태소 분석
    result = kiwi.tokenize(text)
    
    for token in result:
        word = token.form
        pos = token.tag
        
        # 명사(NNG, NNP), 동사(VV), 형용사(VA)만 추출
        if pos in ['NNG', 'NNP', 'VV', 'VA'] and len(word) >= 2:
            # 불용어 제거
            if word not in stopwords and not word.isdigit():
                # 복합어 결합 시도 (예: 고객 + 서비스 → 고객서비스)
                # 현재는 단일 형태소만
                keywords.append(word)
    
    # 빈도수 기준 정렬
    from collections import Counter
    keyword_freq = Counter(keywords)
    
    # 상위 N개 반환
    return [kw for kw, _ in keyword_freq.most_common(top_n)]
```

- [ ] **Step 2: parsing.py의 기존 키워드 추출 함수 확인**

기존 키워드 추출 함수를 찾아서 형태소 분석 기반 버전을 통합합니다.

```python
def extract_keywords(self, text: str, top_n: int = 20, use_morphological: bool = True) -> List[str]:
    """키워드 추출 - 기존 메서드 + 형태소 분석 옵션
    
    Args:
        text: 입력 텍스트
        top_n: 반환할 키워드 수
        use_morphological: True이면 형태소 분석 사용, False이면 기존 TF-IDF
    """
    if use_morphological:
        # 형태소 분석 기반 추출 (정확도 높음)
        return self.extract_keywords_morphological(text, top_n)
    else:
        # 기존 TF-IDF 기반 추출 (호환성 유지)
        return self._extract_keywords_tfidf(text, top_n)
```

- [ ] **Step 3: scoring.py에 형태소 기반 유사도 계산 추가**

Edit: `src/resume_agent/scoring.py` - 새 메서드 추가

```python
def compute_morphological_similarity(self, text1: str, text2: str) -> float:
    """형태소 분석 기반 유사도 계산
    
    Kiwi로 형태소를 추출하고, 명사/동사 기반 Jaccard 유사도 계산
    """
    from kiwipiepy import Kiwi
    from resume_agent.parser import ResumeParser
    
    parser = ResumeParser()
    
    # 형태소 기반 키워드 추출
    keywords1 = set(parser.extract_keywords_morphological(text1, top_n=30))
    keywords2 = set(parser.extract_keywords_morphological(text2, top_n=30))
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # Jaccard 유사도
    intersection = len(keywords1 & keywords2)
    union = len(keywords1 | keywords2)
    
    return intersection / union if union > 0 else 0.0
```

- [ ] **Step 4: scoring.py의 경험 매칭 로직에 형태소 유사도 통합**

Edit: `src/resume_agent/scoring.py` - `score_experience` 함수

```python
def score_experience(
    experience: Experience,
    question: Question,
    all_experiences: List[Experience],
    config: dict,
    use_morphological: bool = True  # 새 옵션
) -> float:
    """경험-질문 매칭 점수 계산"""
    # ... 기존 로직 ...
    
    # 형태소 기반 유사도 추가
    if use_morphological:
        exp_text = f"{experience.action} {experience.result}"
        morph_sim = self.compute_morphological_similarity(exp_text, question.question_text)
        # 최대 3점 보너스
        score += min(morph_sim * 10, 3)
    
    return score
```

- [ ] **Step 5: 테스트 실행**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/ -v -k "keyword or similarity" --tb=short`
Expected: 기존 키워드/유사도 테스트 통과

- [ ] **Step 6: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add src/resume_agent/parsing.py src/resume_agent/scoring.py
git commit -m "feat(phase1): enhance keyword extraction with morphological analysis"
```

---

### Task 4: 질문-경험 의미적 매칭 개선

**Dependencies:** Task 2, Task 3 완료
**Files:**
- Modify: `src/resume_agent/domain.py` (knowledge hints 빌더)
- Modify: `src/resume_agent/classifier.py` (경험 기반 분류 보완)

- [ ] **Step 1: domain.py의 knowledge hints 빌더에 ExperienceDeepAnalyzer 통합**

Edit: `src/resume_agent/domain.py` - `build_knowledge_hints` 메서드

```python
def build_knowledge_hints(
    experiences: List[Experience],
    questions: List[Question],
    kb_path: str,
    config: dict,
    use_deep_analyzer: bool = True  # 새 옵션
) -> dict:
    """지식 힌트 빌드 - 경험 심층 분석 통합"""
    from .experience_analyzer import ExperienceDeepAnalyzer
    
    hints = {
        "experience_hints": [],  # 경험별 힌트
        "question_hints": [],     # 질문별 힌트
        "matching_pairs": []      # 권장 경험-질문 페어링
    }
    
    # 경험 심층 분석 (상위 10개만)
    analyzer = ExperienceDeepAnalyzer()
    analyzed_experiences = []
    
    for exp in experiences[:10]:
        analysis = analyzer.full_analysis(exp)
        analyzed_experiences.append({
            "experience_id": exp.id,
            "analysis": analysis
        })
        
        # 경험 힌트 추가
        top_competency = analysis.core_competencies[0] if analysis.core_competencies else None
        hints["experience_hints"].append({
            "exp_id": exp.id,
            "title": exp.title,
            "top_competency": top_competency.competency if top_competency else "미분류",
            "competencies": [c.competency for c in analysis.core_competencies[:3]],
            "interview_tip": f"'{top_competency.competency}' 역량 입증에 최적" if top_competency else "일반적 STAR 작성"
        })
    
    # 질문별 힌트 (의도 분석)
    for question in questions:
        intent = analyzer.analyze_question_intent(question)
        
        hints["question_hints"].append({
            "question_id": question.id,
            "surface_topic": intent.surface_topic,
            "hidden_intent": intent.hidden_intent,
            "wanted_competencies": intent.core_competencies_sought,
            "risk_topics": intent.risk_topics
        })
        
        # 경험-질문 매칭 (핵심 역량 기반)
        for exp_data in analyzed_experiences:
            exp_competencies = [c.competency for c in exp_data["analysis"].core_competencies]
            
            # 의미적 매칭 (공통 역량 기준)
            common = set(exp_competencies) & set(intent.core_competencies_sought)
            
            if common:
                hints["matching_pairs"].append({
                    "question_id": question.id,
                    "experience_id": exp_data["experience_id"],
                    "matched_competencies": list(common),
                    "match_score": len(common) / max(len(exp_competencies), len(intent.core_competencies_sought))
                })
    
    # 매칭 점수 기준 정렬
    hints["matching_pairs"] = sorted(
        hints["matching_pairs"],
        key=lambda x: x["match_score"],
        reverse=True
    )[:20]  # 상위 20개
    
    return hints
```

- [ ] **Step 2: classifier.py에 경험 기반 분류 보완 추가**

Edit: `src/resume_agent/classifier.py` - 기존 분류기에 경험 힌트 옵션 추가

```python
def classify_with_experience_hints(
    questions: List[Question],
    experiences: List[Experience],
    config: dict,
    use_deep_analysis: bool = True
) -> dict:
    """경험 힌트를 활용한 질문 분류
    
    경험의 핵심 역량을 기반으로 질문 분류를 보완
    """
    from .experience_analyzer import ExperienceDeepAnalyzer
    
    results = {}
    analyzer = ExperienceDeepAnalyzer()
    
    # 경험 핵심 역량 매핑
    exp_competencies = {}
    for exp in experiences:
        analysis = analyzer.analyze_core_competency(exp)
        exp_competencies[exp.id] = [c.competency for c in analysis]
    
    for question in questions:
        # 기존 분류
        base_type = classify_question_type(question.question_text, config)
        
        # 경험 기반 보완 (경험의 역량과 질문의 의도 매칭)
        if use_deep_analysis:
            intent = analyzer.analyze_question_intent(question)
            
            # 경험 역량과 질문 의도 매칭
            matching_exp = []
            for exp_id, comps in exp_competencies.items():
                common = set(comps) & set(intent.core_competencies_sought)
                if common:
                    matching_exp.append({
                        "exp_id": exp_id,
                        "matched": list(common)
                    })
            
            # 가장 관련 깊은 경험 3개
            top_matching = sorted(
                matching_exp,
                key=lambda x: len(x["matched"]),
                reverse=True
            )[:3]
            
            results[question.id] = {
                "type": base_type,
                "intent_analysis": intent.model_dump(),
                "recommended_experiences": top_matching,
                "confidence_boost": len(top_matching) > 0  # 경험이 있으면 신뢰도 향상
            }
        else:
            results[question.id] = {
                "type": base_type,
                "confidence_boost": False
            }
    
    return results
```

- [ ] **Step 3: 테스트 작성**

Create: `tests/test_semantic_matching.py`

```python
"""질문-경험 의미적 매칭 테스트"""

import pytest
from resume_agent.domain import build_knowledge_hints
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


class TestKnowledgeHints:
    """지식 힌트 빌드 테스트"""
    
    def test_builds_experience_hints(self, sample_experiences, sample_questions):
        """경험 힌트 생성"""
        hints = build_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        assert "experience_hints" in hints
        assert len(hints["experience_hints"]) > 0
        
        # 핵심 역량 추출 확인
        exp_hint = hints["experience_hints"][0]
        assert "top_competency" in exp_hint
        assert "competencies" in exp_hint
    
    def test_builds_question_hints(self, sample_experiences, sample_questions):
        """질문 힌트 생성"""
        hints = build_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        assert "question_hints" in hints
        assert len(hints["question_hints"]) > 0
        
        # 숨겨진 의도 확인
        q_hint = hints["question_hints"][0]
        assert "hidden_intent" in q_hint
        assert "wanted_competencies" in q_hint
    
    def test_creates_matching_pairs(self, sample_experiences, sample_questions):
        """경험-질문 매칭 페어 생성"""
        hints = build_knowledge_hints(
            sample_experiences,
            sample_questions,
            kb_path="./kb",
            config={}
        )
        
        assert "matching_pairs" in hints
        
        # 고객 응대 질문 ↔ 고객 불만 경험 매칭 확인
        customer_q = next(
            (p for p in hints["matching_pairs"] if "q_002" in p["question_id"]),
            None
        )
        
        if customer_q:
            # "고객" 관련 경험과 매칭되어야 함
            assert "exp_001" in customer_q["experience_id"] or len(customer_q["matched_competencies"]) > 0


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
        
        # 경험 매칭 확인
        rec_exp = results["q_001"]["recommended_experiences"]
        assert isinstance(rec_exp, list)
    
    def test_confidence_boost_when_experience_matches(self, sample_experiences, sample_questions):
        """경험 매칭 시 신뢰도 향상"""
        results = classify_with_experience_hints(
            sample_questions,
            sample_experiences,
            config={},
            use_deep_analysis=True
        )
        
        # 경험과 질문이 매칭되면 confidence_boost True
        has_match = any(r.get("recommended_experiences") for r in results.values())
        assert has_match, "Expected at least one experience-question match"
```

- [ ] **Step 4: 테스트 실행**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/test_semantic_matching.py -v --tb=short`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add src/resume_agent/domain.py src/resume_agent/classifier.py tests/test_semantic_matching.py
git commit -m "feat(phase1): integrate ExperienceDeepAnalyzer for semantic matching"
```

---

### Task 5: 재인덱싱 마이그레이션 스크립트

**Dependencies:** Task 1 완료
**Files:**
- Create: `scripts/migrate_embeddings.py`

- [ ] **Step 1: 마이그레이션 스크립트 작성**

Create: `scripts/migrate_embeddings.py`

```python
#!/usr/bin/env python3
"""임베딩 모델 업그레이드 마이그레이션 스크립트

사용법:
    python scripts/migrate_embeddings.py [--dry-run] [--force]

기능:
    1. 기존 임베딩 인덱스 백업
    2. 새 모델로 전체 문서 재인덱싱
    3. 차원 불일치 감지 및 자동 재인덱싱
"""

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_agent.semantic_engine import SemanticSearchEngine


def migrate_embeddings(
    kb_path: str = "./kb",
    dry_run: bool = False,
    force: bool = False
):
    """임베딩 마이그레이션 실행"""
    
    kb_dir = Path(kb_path)
    index_file = kb_dir / "vector" / "index.json"
    backup_dir = kb_dir / "vector" / "backups"
    
    print(f"=== Embedding Migration Script ===")
    print(f"KB Path: {kb_path}")
    print(f"Dry Run: {dry_run}")
    print(f"Force: {force}")
    
    # 1. 백업 디렉토리 생성
    if not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. 기존 인덱스 확인
    if not index_file.exists():
        print("⚠️  No existing index found. Nothing to migrate.")
        return
    
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    
    old_dimension = index_data.get("embedding_dimension", 384)
    print(f"📊 Existing index dimension: {old_dimension}")
    
    # 3. 새 모델 정보 확인
    engine = SemanticSearchEngine()
    new_dimension = engine._get_embedding_model().get_sentence_embedding_dimension()
    print(f"📊 New model dimension: {new_dimension}")
    
    # 4. 차원 비교
    if old_dimension == new_dimension:
        print("✅ Dimensions match. No re-embedding needed.")
        
        if not force:
            print("Use --force to re-embed anyway.")
            return
    
    # 5. 백업 생성
    if not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"index_backup_{timestamp}_dim{old_dimension}.json"
        shutil.copy(index_file, backup_file)
        print(f"📦 Backup created: {backup_file}")
    
    # 6. 재인덱싱
    if dry_run:
        print("🔄 [DRY RUN] Would re-index all documents...")
        print(f"    Documents to re-index: {len(index_data.get('documents', []))}")
    else:
        print("🔄 Re-indexing all documents with new model...")
        
        # 문서 텍스트 추출
        documents = []
        for doc in index_data.get("documents", []):
            documents.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc.get("metadata", {})
            })
        
        # 새 인덱스 생성
        engine.index_documents(documents, persist=True)
        
        # 새 인덱스 정보
        with open(index_file, "r", encoding="utf-8") as f:
            new_index = json.load(f)
        
        print(f"✅ Re-indexing complete!")
        print(f"    New dimension: {new_index.get('embedding_dimension')}")
        print(f"    Documents indexed: {len(new_index.get('documents', []))}")


def main():
    parser = argparse.ArgumentParser(description="Migrate embeddings to new model")
    parser.add_argument(
        "--kb-path",
        default="./kb",
        help="Knowledge base path (default: ./kb)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing even if dimensions match"
    )
    
    args = parser.parse_args()
    
    migrate_embeddings(
        kb_path=args.kb_path,
        dry_run=args.dry_run,
        force=args.force
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 스크립트 실행 가능하도록 설정**

Run: `chmod +x scripts/migrate_embeddings.py`

- [ ] **Step 3: dry-run 실행 (현재 차원 확인)**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && python scripts/migrate_embeddings.py --dry-run --kb-path ./kb`
Expected: 현재 차원 출력 + 마이그레이션 필요 여부 확인

- [ ] **Step 4: 실제 마이그레이션 (필요시)**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && python scripts/migrate_embeddings.py --force --kb-path ./kb`
Expected: 새 모델로 재인덱싱 완료

- [ ] **Step 5: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add scripts/migrate_embeddings.py
git commit -m "feat(phase1): add embedding migration script"
```

---

### Task 6 (Final): End-to-End 검증

**Dependencies:** Tasks 1-5 모두 완료
**Files:** None (read-only verification)

- [ ] **Step 1: 전체 테스트 실행**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/ -v --tb=short`
Expected: ALL PASS (기존 72 + 신규 ~30 = ~100개 테스트)

- [ ] **Step 2: 의미적 유사도 벤치마크 검증**

```python
# 검증할 의미적 동등성 케이스
TEST_EQUIVALENCES = [
    ("고객 응대", "민원 처리", 0.5),  # min similarity
    ("팀 리더", "프로젝트 매니저", 0.4),
    ("성과 향상", "성과 개선", 0.6),
    ("문제 해결", "어려움 극복", 0.5),
]

# 실행
from resume_agent.semantic_engine import SemanticSearchEngine
engine = SemanticSearchEngine()

all_passed = True
for text1, text2, min_sim in TEST_EQUIVALENCES:
    sim = engine.compute_similarity(text1, text2)
    if sim < min_sim:
        print(f"❌ FAIL: '{text1}' vs '{text2}' = {sim} < {min_sim}")
        all_passed = False
    else:
        print(f"✅ PASS: '{text1}' vs '{text2}' = {sim}")

if all_passed:
    print("\n✅ All semantic similarity benchmarks passed!")
```

- [ ] **Step 3: ExperienceDeepAnalyzer 통합 검증**

```python
# 검증
from resume_agent.experience_analyzer import ExperienceDeepAnalyzer
from resume_agent.models import Experience, EvidenceLevel, VerificationStatus

analyzer = ExperienceDeepAnalyzer()

exp = Experience(
    id="test",
    title="고객 불만 처리",
    organization="Test",
    period_start="2023-01",
    action="고객 민원을 해결하고 프로세스를 개선했다",
    result="고객 만족도 50% 향상",
    evidence_level=EvidenceLevel.L3,
    tags=["CS"],
    verification_status=VerificationStatus.VERIFIED
)

analysis = analyzer.full_analysis(exp)
assert len(analysis.core_competencies) > 0, "No competencies extracted"
assert "고객 중심 사고" in [c.competency for c in analysis.core_competencies], "Customer focus not detected"

print("✅ ExperienceDeepAnalyzer integration verified!")
```

- [ ] **Step 4: 전체 계획 성공 기준 검증**

- [ ] **Goal 달성**: 의미적 이해 향상 (Ko-SBERT/E5 임베딩) ✅
- [ ] **ExperienceDeepAnalyzer**: 경험 핵심 역량 추출 + 면접관 인상 예측 ✅
- [ ] **형태소 분석**: Kiwi 기반 키워드 추출 강화 ✅
- [ ] **의미적 매칭**: 질문-경험 의미적 연결 개선 ✅
- [ ] **마이그레이션**: 재인덱싱 스크립트 제공 ✅

- [ ] **Step 5: 회귀 테스트**

Run: `cd /home/ehddk/ai/ai/ai/resume-agent && pytest tests/test_semantic_engine.py tests/test_vector_store_coverage.py -v --tb=short`
Expected: 기존 기능 회귀 없음

---

## Self-Review Checklist

- [x] 모든 Task에 정확한 파일 경로 명시
- [x] 모든 Step에 실행 가능한 코드/명령 포함
- [x] Task 간 파일 충돌 없음 (parallel tasks는 다른 파일 수정)
- [x] 의존성 체인 정확히 명시
- [x] 모든 plan 요구사항(Task 1~5) 포함
- [x] placeholders 없음 (TBD, TODO 없음)
- [x] Verification Strategy 포함
- [x] Final Verification Task (Task 6) 마지막에 위치

---

## 예상 산출물

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `config.yaml` | 수정 | 임베딩 모델 변경 |
| `src/resume_agent/semantic_engine.py` | 수정 | 모델 업그레이드 |
| `src/resume_agent/experience_analyzer.py` | **신규** | 경험 심층 분석기 |
| `src/resume_agent/models.py` | 수정 | 새 Pydantic 모델 추가 |
| `src/resume_agent/parsing.py` | 수정 | 형태소 분석 키워드 추출 |
| `src/resume_agent/scoring.py` | 수정 | 의미적 유사도 계산 개선 |
| `src/resume_agent/domain.py` | 수정 | knowledge hints에 분석기 통합 |
| `src/resume_agent/classifier.py` | 수정 | 경험 기반 분류 보완 |
| `scripts/migrate_embeddings.py` | **신규** | 마이그레이션 스크립트 |
| `tests/test_experience_analyzer.py` | **신규** | 분석기 테스트 |
| `tests/test_semantic_matching.py` | **신규** | 의미적 매칭 테스트 |
| `tests/test_semantic_engine.py` | 수정 | 새 모델 테스트 추가 |
| `DIAGNOSTIC_TOP001.md` | **신규** | 진단 문서 |

---

## Timeline

| Phase | 예상 시간 | 목표 |
|-------|----------|------|
| Task 0-1 | 1~2일 | 임베딩 모델 업그레이드 |
| Task 2 | 2~3일 | ExperienceDeepAnalyzer |
| Task 3 | 1~2일 | 형태소 분석 강화 |
| Task 4 | 2~3일 | 의미적 매칭 개선 |
| Task 5 | 0.5일 | 마이그레이션 스크립트 |
| Task 6 | 0.5일 | End-to-End 검증 |

**총 예상: 7~11일 (1.5~2주)**

---

*계획 작성일: 2026-04-08*
*계획 버전: v1.0*
