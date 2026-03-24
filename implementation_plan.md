# Implementation Plan

## Overview

resume-agent 프로젝트의 자기소개서(writer)와 면접(interview) 기능을 균등하게 개선하여, 더 구체적이고 창의적인 답변 생성, 면접 방어 가능성 강화, 회사/직무별 맞춤화를 구현합니다.

## 개요

현재 resume-agent는 결정론적 엔진과 Codex CLI를 조합하여 자기소개서와 면접 준비를 자동화합니다. 그러나 프롬프트가 다소 일반적이며, 회사/직무별 맞춤화가 부족하고, 면접 꼬리질문에 대한 방어 전략이 미흡합니다. 본 개선안은 이러한 한계를 극복하여 더 고품질의 결과물을 생성하는 것을 목표로 합니다.

### 개선 필요성
1. **프롬프트 일반성 문제**: 현재 프롬프트가 범용적이어서 특정 회사/직무에 최적화된 답변 생성이 어려움
2. **창의성 부족**: 클리셰 회피 규칙은 있지만, 독창적인 표현 유도 메커니즘 미흡
3. **면접 방어 취약점**: 꼬리질문 시뮬레이션은 구현되었으나, 답변의 방어 가능성 검증 로직 부족
4. **회사별 맞춤화 미흡**: 기업 유형(대기업/스타트업/공공)에 따른 톤 차별화가 단순화됨

### 개선 접근법
- 프롬프트 엔지니어링 강화 (Few-shot 예시, Chain-of-Thought 유도)
- 회사/직무 분석 자동화 (공고문 키워드 추출 → 맞춤형 답변 전략)
- 면접 방어 검증 루프 (Self-Consistency Check)
- 품질 평가 시스템 도입 (자동 점수화 및 피드백)

## Types

타입 시스템 변경 사항:

```python
# models.py에 추가할 타입들

class InterviewStyle(str, Enum):
    """면접 스타일"""
    FORMAL = "formal"           # 격식 있는 (대기업, 공공)
    CASUAL = "casual"           # 편안한 (스타트업)
    TECHNICAL = "technical"     # 기술 중심 (IT, 엔지니어링)
    BEHAVIORAL = "behavioral"   # 행동 중심 (영업, 마케팅)

class CompanyAnalysis(BaseModel):
    """회사 분석 결과"""
    company_name: str
    company_type: str  # 대기업, 중견, 스타트업, 공공, 공기업
    industry: str
    core_values: List[str] = Field(default_factory=list)
    culture_keywords: List[str] = Field(default_factory=list)
    recent_news: List[str] = Field(default_factory=list)
    interview_style: InterviewStyle = InterviewStyle.FORMAL

class QuestionAnalysis(BaseModel):
    """질문 분석 결과"""
    question_id: str
    question_text: str
    question_type: QuestionType
    keywords: List[str] = Field(default_factory=list)
    hidden_intent: str = ""  # 질문의 숨겨진 의도
    risk_level: str = "medium"  # low, medium, high
    defense_strategy: str = ""  # 방어 전략

class AnswerQuality(BaseModel):
    """답변 품질 평가"""
    question_id: str
    answer_text: str
    relevance_score: float  # 0.0 ~ 1.0
    specificity_score: float  # 0.0 ~ 1.0
    defensibility_score: float  # 0.0 ~ 1.0
    originality_score: float  # 0.0 ~ 1.0
    overall_score: float  # 0.0 ~ 1.0
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
```

## Files

파일 수정 사항:

### 새로 생성할 파일

1. **`/root/ai/resume-agent/src/resume_agent/company_analyzer.py`**
   - 회사 분석 모듈
   - 공고문 키워드 추출, 기업 문화 분석, 맞춤형 톤 결정

2. **`/root/ai/resume-agent/src/resume_agent/answer_quality.py`**
   - 답변 품질 평가 모듈
   - 관련성, 구체성, 방어 가능성, 독창성 자동 평가

3. **`/root/ai/resume-agent/src/resume_agent/defense_simulator.py`**
   - 면접 방어 시뮬레이션 모듈
   - 꼬리질문 생성, 방어 포인트 검증, 취약점 식별

4. **`/root/ai/resume-agent/prompts/writer_enhanced.md`**
   - 강화된 자기소개서 작성 프롬프트
   - Few-shot 예시, 회사별 맞춤화 지침 포함

5. **`/root/ai/resume-agent/prompts/interview_enhanced.md`**
   - 강화된 면접 준비 프롬프트
   - 방어 전략, 꼬리질문 대비 지침 포함

6. **`/root/ai/resume-agent/prompts/company_analysis.md`**
   - 회사 분석 프롬프트
   - 공고문 → 기업 문화, 핵심 가치 추출

### 수정할 파일

1. **`/root/ai/resume-agent/src/resume_agent/models.py`**
   - 위에 정의한 새 타입들 추가
   - 기존 모델에 새 필드 추가 (company_analysis, question_analyses 등)

2. **`/root/ai/resume-agent/src/resume_agent/pipeline.py`**
   - `run_writer_with_codex()` 함수에 회사 분석 로직 추가
   - `run_interview_with_codex()` 함수에 방어 시뮬레이션 로직 추가
   - 답변 품질 평가 로직 추가

3. **`/root/ai/resume-agent/src/resume_agent/classifier.py`**
   - 질문 분석 로직 강화
   - 숨겨진 의도 추출 기능 추가
   - 리스크 레벨 평가 기능 추가

4. **`/root/ai/resume-agent/src/resume_agent/interview_engine.py`**
   - `run_recursive_interview_chain()` 함수에 방어 검증 로직 추가
   - 꼬리질문 다양화 로직 추가

5. **`/root/ai/resume-agent/02_자기소개서_프롬프트..txt`**
   - Few-shot 예시 추가
   - 회사별 맞춤화 지침 강화
   - 독창성 유도 메커니즘 추가

6. **`/root/ai/resume-agent/03_면접_프롬프트..txt`**
   - 방어 전략 프레임워크 추가
   - 꼬리질문 유형별 대응법 추가
   - 회사별 면접 스타일 가이드 추가

7. **`/root/ai/resume-agent/src/resume_agent/scoring.py`**
   - 답변 품질 평가 함수 추가
   - 독창성 점수 계산 로직 추가
   - 방어 가능성 점수 계산 로직 추가

### 삭제하거나 이동할 파일

없음. 모든 새 파일은 기존 구조에 통합됩니다.

### 설정 파일 업데이트

1. **`/root/ai/resume-agent/pyproject.toml`**
   - 의존성에 추가: `sentence-transformers` (벡터 검색용, 선택적)

## Functions

함수 수정 사항:

### 새로 생성할 함수

1. **`company_analyzer.py`**
   - `analyze_company(job_description: str, company_name: str) -> CompanyAnalysis`
     - 공고문 분석 → 기업 유형, 핵심 가치, 문화 키워드 추출
   - `extract_keywords(text: str) -> List[str]`
     - 텍스트에서 핵심 키워드 추출
   - `determine_interview_style(company_analysis: CompanyAnalysis) -> InterviewStyle`
     - 기업 분석 결과 기반 면접 스타일 결정

2. **`answer_quality.py`**
   - `evaluate_answer_quality(answer: str, question: str, experience: Experience) -> AnswerQuality`
     - 답변 품질 종합 평가
   - `calculate_relevance(answer: str, question: str) -> float`
     - 질문-답변 관련성 점수
   - `calculate_specificity(answer: str) -> float`
     - 구체성 점수 (수치, 구체적 행동 포함 여부)
   - `calculate_defensibility(answer: str) -> float`
     - 방어 가능성 점수 (30초 내 방어 가능한지)
   - `calculate_originality(answer: str, reference_texts: List[str]) -> float`
     - 독창성 점수 (참고 텍스트와의 유사도)

3. **`defense_simulator.py`**
   - `simulate_interview_defense(primary_question: str, answer: str, company_analysis: CompanyAnalysis) -> DefenseSimulation`
     - 면접 방어 시뮬레이션
   - `generate_follow_up_questions(answer: str, question_type: QuestionType) -> List[str]`
     - 꼬리질문 생성
   - `identify_risk_areas(answer: str) -> List[str]`
     - 답변의 취약점 식별
   - `suggest_defense_points(answer: str, risk_areas: List[str]) -> List[str]`
     - 방어 포인트 제안

4. **`classifier.py`**에 추가
   - `extract_hidden_intent(question: str) -> str`
     - 질문의 숨겨진 의도 추출
   - `assess_risk_level(question: str, answer: str) -> str`
     - 질문-답변 조합의 리스크 레벨 평가
   - `suggest_defense_strategy(question_type: QuestionType, risk_level: str) -> str`
     - 방어 전략 제안

### 수정할 함수

1. **`pipeline.py`의 `run_writer_with_codex()`**
   - 현재: 프롬프트 생성 → Codex 실행 → 검증
   - 개선: 회사 분석 → 맞춤형 프롬프트 생성 → Codex 실행 → 품질 평가 → 검증
   - 변경 사항:
     - 회사 분석 로직 추가
     - 답변 품질 평가 로직 추가
     - 독창성 검증 로직 추가

2. **`pipeline.py`의 `run_interview_with_codex()`**
   - 현재: 프롬프트 생성 → Codex 실행 → 검증
   - 개선: 회사 분석 → 맞춤형 프롬프트 생성 → Codex 실행 → 방어 시뮬레이션 → 검증
   - 변경 사항:
     - 회사 분석 로직 추가
     - 방어 시뮬레이션 로직 추가
     - 꼬리질문 검증 로직 추가

3. **`interview_engine.py`의 `run_recursive_interview_chain()`**
   - 현재: 가상 답변 생성 → 꼬리질문 생성
   - 개선: 가상 답변 생성 → 취약점 분석 → 방어 전략 수립 → 꼬리질문 생성 → 방어 검증
   - 변경 사항:
     - 취약점 분석 로직 추가
     - 방어 전략 수립 로직 추가
     - 방어 검증 로직 추가

4. **`scoring.py`의 `score_experience()`**
   - 현재: 키워드 매칭, 증거 레벨, 태그 적합도 기반 점수
   - 개선: 위 항목 + 질문 의도 적합도 + 방어 가능성 점수 추가
   - 변경 사항:
     - 질문 의도 적합도 점수 추가
     - 방어 가능성 점수 추가

5. **`templates.py`의 프롬프트 템플릿**
   - `PROMPT_WRITER`: Few-shot 예시 추가, 회사별 맞춤화 지침 추가
   - `PROMPT_INTERVIEW`: 방어 전략 프레임워크 추가, 꼬리질문 대비 지침 추가

## Classes

클래스 수정 사항:

### 새로 생성할 클래스

1. **`CompanyAnalyzer`** (company_analyzer.py)
   - 메서드: `analyze()`, `extract_keywords()`, `determine_style()`
   - 역할: 회사/직무 분석 및 맞춤형 전략 수립

2. **`AnswerQualityEvaluator`** (answer_quality.py)
   - 메서드: `evaluate()`, `calculate_relevance()`, `calculate_specificity()`, `calculate_defensibility()`, `calculate_originality()`
   - 역할: 답변 품질 종합 평가

3. **`DefenseSimulator`** (defense_simulator.py)
   - 메서드: `simulate()`, `generate_follow_ups()`, `identify_risks()`, `suggest_defenses()`
   - 역할: 면접 방어 시뮬레이션 및 검증

### 수정할 클래스

1. **`ExperienceValidator`** (validators.py)
   - 새 메서드 추가: `validate_defensibility(experience: Experience) -> ValidationResult`
   - 역할: 경험 데이터의 방어 가능성 검증

2. **`ApplicationProject`** (models.py)
   - 새 필드 추가:
     - `company_analysis: Optional[CompanyAnalysis] = None`
     - `interview_style: InterviewStyle = InterviewStyle.FORMAL`
   - 역할: 회사 분석 결과 저장

## Dependencies

의존성 변경:

### 새로 추가할 패키지

1. **`sentence-transformers`** (선택적)
   - 용도: 벡터 임베딩 기반 유사도 계산
   - 설치: `pip install sentence-transformers`
   - 주의: 큰 패키지이므로 선택적 의존성으로 관리

### 기존 패키지 유지

- `pydantic`: 데이터 모델링
- `subprocess`: Codex CLI 실행
- `json`: 데이터 직렬화
- `pathlib`: 파일 경로 관리
- `re`: 정규 표현식 (텍스트 분석용)

## Testing

테스트 접근법:

### 새 테스트 파일

1. **`/root/ai/resume-agent/tests/test_company_analyzer.py`**
   - 회사 분석 로직 테스트
   - 다양한 기업 유형별 분석 결과 검증

2. **`/root/ai/resume-agent/tests/test_answer_quality.py`**
   - 답변 품질 평가 로직 테스트
   - 다양한 답변 패턴에 대한 점수 검증

3. **`/root/ai/resume-agent/tests/test_defense_simulator.py`**
   - 면접 방어 시뮬레이션 로직 테스트
   - 꼬리질문 생성 및 방어 전략 검증

### 기존 테스트 수정

1. **`/root/ai/resume-agent/tests/test_classifier.py`**
   - 숨겨진 의도 추출 테스트 추가
   - 리스크 레벨 평가 테스트 추가

2. **`/root/ai/resume-agent/tests/test_scoring.py`**
   - 독창성 점수 계산 테스트 추가
   - 방어 가능성 점수 계산 테스트 추가

### 검증 전략

1. **단위 테스트**: 각 모듈의 함수/클래스 개별 테스트
2. **통합 테스트**: 파이프라인 전체 흐름 테스트
3. **사용자 시나리오 테스트**: 실제 자기소개서/면접 문항으로 엔드투엔드 테스트
4. **품질 기준 테스트**: 생성된 답변의 품질이 기준 이상인지 검증

## Implementation Order

구현 순서:

1. **Phase 1: 데이터 모델 및 분석 인프라 (기반 구축)** ✅ 완료
   - models.py에 새 타입 추가 (InterviewStyle, SuccessPattern, CompanyAnalysis, QuestionAnalysis, AnswerQuality, DefenseSimulation, SuccessCase)
   - company_analyzer.py 구현 (linkareer 합격 데이터 기반 회사 분석)
   - classifier.py 강화 (숨겨진 의도 추출, 리스크 평가)

2. **Phase 2: 답변 품질 평가 시스템** ✅ 완료
   - answer_quality.py 구현 (관련성, 구체성, 방어 가능성, 독창성 평가)
   - scoring.py에 독창성/방어 가능성 점수 추가
   - linkareer 합격 패턴 기반 패턴 감지

3. **Phase 3: 면접 방어 시뮬레이션** ✅ 완료
   - defense_simulator.py 구현 (꼬리질문 생성, 방어 포인트 검증, 취약점 식별)
   - interview_engine.py 강화 (방어 검증 로직)
   - 질문 유형별/면접 스타일별 맞춤 전략

4. **Phase 4: 프롬프트 엔지니어링** ✅ 완료
   - writer_enhanced.md 프롬프트 작성 (linkareer 합격 패턴 반영)
   - interview_enhanced.md 프롬프트 작성 (방어 전략 프레임워크 포함)
   - 02_자기소개서_프롬프트..txt 업데이트 (기존 파일 유지, 새 프롬프트 별도 생성)
   - 03_면접_프롬프트..txt 업데이트 (기존 파일 유지, 새 프롬프트 별도 생성)

5. **Phase 5: 파이프라인 통합** ✅ 완료
   - pipeline.py의 run_writer_with_codex() 수정 (회사 분석, 답변 품질 평가 통합)
   - pipeline.py의 run_interview_with_codex() 수정 (회사 분석, 방어 시뮬레이션 통합)
   - 통합 테스트 작성 및 검증

6. **Phase 6: 사용자 피드백 루프 (선택적)** ⏳ 미구현
   - 피드백 수집 메커니즘 구현
   - 피드백 기반 프롬프트 자동 개선 로직
   - A/B 테스트 프레임워크
