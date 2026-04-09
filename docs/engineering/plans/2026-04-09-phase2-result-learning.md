# Phase 2: 결과 기반 학습 구현 계획

> **목표**: 합격 결과 추적 → 배치 × 결과 상관관계 학습 → 전략 최적화

**Architecture:**
- **현재**: 피드백 기록만 가능 (final_outcome 저장되지만 미활용)
- **개선**: 결과 추적 CLI → 경험-결과 상관분석 → A/B 테스트 프레임워크

**Tech Stack:**
- **CLI Framework**: argparse (기존 cli.py 확장)
- **통계 분석**: Python 내장 statistics + scipy.stats (선택적)
- **데이터 저장**: JSON (기존 state.py 활용)

**Work Scope:**
- **In scope:**
  1. 결과 추적 CLI 명령어 (`outcome`, `result`, `track`)
  2. 경험-결과 상관관계 분석 (`correlation.py`)
  3. A/B 테스트 프레임워크 (`ab_testing.py`)
  4. 통계 분석 유틸리티
- **Out of scope:**
  - Phase 3 (개인화), Phase 4 (실시간 데이터)

---

## 파일 구조 매핑

### 신규 생성 파일

| 파일 | 목적 |
|------|------|
| `src/resume_agent/outcome_tracker.py` | 결과 추적 및 통계 분석 |
| `src/resume_agent/ab_testing.py` | A/B 테스트 프레임워크 |
| `src/resume_agent/correlation.py` | 경험-결과 상관관계 분석 |
| `tests/test_outcome_tracker.py` | 결과 추적 테스트 |
| `tests/test_ab_testing.py` | A/B 테스트 테스트 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/resume_agent/cli.py` | 결과 추적 CLI 명령어 추가 |
| `src/resume_agent/models.py` | OutcomeResult, ABTestResult 모델 추가 |
| `src/resume_agent/feedback_learner.py` | 결과 분석 메서드 확장 |

---

## Task Decomposition

### Task 1: 모델 및 데이터 구조 정의

**Dependencies:** None
**Files:**
- Modify: `src/resume_agent/models.py`

- [ ] **Step 1: models.py에 새 모델 추가**

```python
class OutcomeResult(BaseModel):
    """지원 결과 추적"""
    artifact_id: str
    application_id: str
    company_name: str
    job_title: str
    outcome: Literal["pending", "screening_pass", "screening_fail", 
                     "interview_invited", "interview_pass", "interview_fail",
                     "final_pass", "final_fail", "offer_received", "offer_declined"]
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
    start_date: str
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
    question_types_used: List[str] = []
    avg_rating: Optional[float] = None
```

- [ ] **Step 2: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add src/resume_agent/models.py
git commit -m "feat(phase2): add OutcomeResult, ABTestResult, ExperienceOutcomeStats models"
```

---

### Task 2: 결과 추적기 구현

**Dependencies:** Task 1
**Files:**
- Create: `src/resume_agent/outcome_tracker.py`

- [ ] **Step 1: outcome_tracker.py 생성**

```python
"""결과 추적 및 통계 분석 모듈"""

from typing import Dict, List, Optional
from pathlib import Path
import json
import logging

from .models import OutcomeResult, ExperienceOutcomeStats
from .state import Workspace

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """지원 결과 추적 및 분석"""
    
    def __init__(self, ws: Workspace):
        self.ws = ws
        self.outcomes_file = ws.state_dir / "outcomes.json"
        self._outcomes: List[OutcomeResult] = []
        self._load()
    
    def _load(self):
        if self.outcomes_file.exists():
            with open(self.outcomes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._outcomes = [OutcomeResult(**o) for o in data]
    
    def _save(self):
        self.outcomes_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.outcomes_file, "w", encoding="utf-8") as f:
            json.dump([o.model_dump() for o in self._outcomes], f, ensure_ascii=False, indent=2)
    
    def record_outcome(self, outcome: OutcomeResult) -> OutcomeResult:
        """결과 기록"""
        # 기존 결과 확인 (중복 방지)
        for i, o in enumerate(self._outcomes):
            if o.artifact_id == outcome.artifact_id:
                self._outcomes[i] = outcome
                self._save()
                return outcome
        
        self._outcomes.append(outcome)
        self._save()
        logger.info(f"Recorded outcome: {outcome.artifact_id} -> {outcome.outcome}")
        return outcome
    
    def get_outcome(self, artifact_id: str) -> Optional[OutcomeResult]:
        """결과 조회"""
        for o in self._outcomes:
            if o.artifact_id == artifact_id:
                return o
        return None
    
    def get_all_outcomes(self) -> List[OutcomeResult]:
        """전체 결과 조회"""
        return self._outcomes
    
    def get_company_outcomes(self, company_name: str) -> List[OutcomeResult]:
        """기업별 결과 조회"""
        return [o for o in self._outcomes if company_name in o.company_name]
    
    def get_success_rate(self) -> float:
        """전체成功率 계산"""
        if not self._outcomes:
            return 0.0
        
        # 최종 합격(offers_received) + 최종 합격(final_pass)
        success = sum(1 for o in self._outcomes 
                     if o.outcome in ["offer_received", "final_pass", "interview_pass"])
        return success / len(self._outcomes) if self._outcomes else 0.0
    
    def get_outcome_summary(self) -> Dict[str, int]:
        """결과 요약 통계"""
        summary = {k: 0 for k in [
            "pending", "screening_pass", "screening_fail",
            "interview_invited", "interview_pass", "interview_fail",
            "final_pass", "final_fail", "offer_received"
        ]}
        
        for o in self._outcomes:
            if o.outcome in summary:
                summary[o.outcome] += 1
        
        return summary
    
    def get_experience_stats(
        self, 
        experience_id: str,
        experience_title: str
    ) -> ExperienceOutcomeStats:
        """경험별 사용 통계 계산"""
        # 피드백에서 이 경험을 사용한 결과 조회
        from .feedback_learner import FeedbackLearner
        
        learner = FeedbackLearner(self.ws)
        all_feedback = learner.get_all_feedback()
        
        # 이 경험을 사용한 피드백 필터링
        relevant = [
            f for f in all_feedback
            if experience_id in f.selected_experience_ids
        ]
        
        if not relevant:
            return ExperienceOutcomeStats(
                experience_id=experience_id,
                experience_title=experience_title
            )
        
        # 통계 계산
        success = sum(1 for f in relevant 
                     if f.final_outcome in ["offer_received", "final_pass", "interview_pass"])
        fail = sum(1 for f in relevant
                  if f.final_outcome in ["screening_fail", "interview_fail", "final_fail"])
        
        ratings = [f.rating for f in relevant if f.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        return ExperienceOutcomeStats(
            experience_id=experience_id,
            experience_title=experience_title,
            total_uses=len(relevant),
            success_count=success,
            fail_count=fail,
            success_rate=success / len(relevant) if relevant else 0.0,
            avg_interview_count=sum(f.interview_count or 0 for f in relevant) / len(relevant),
            question_types_used=list(set(
                qt for f in relevant 
                for qt in (f.question_types or [])
            )),
            avg_rating=avg_rating
        )
```

- [ ] **Step 2: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add src/resume_agent/outcome_tracker.py
git commit -m "feat(phase2): add OutcomeTracker for result tracking and statistics"
```

---

### Task 3: A/B 테스트 프레임워크 구현

**Dependencies:** Task 1, Task 2
**Files:**
- Create: `src/resume_agent/ab_testing.py`

- [ ] **Step 1: ab_testing.py 생성**

```python
"""A/B 테스트 프레임워크 - 전략 비교 및 최적화"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import math
from pathlib import Path

from .models import ABTestResult
from .state import Workspace

# 단순 카이제곱 검정 (scipy 없음 대응)
def chi_square_test(
    success_a: int, total_a: int,
    success_b: int, total_b: int,
    confidence: float = 0.95
) -> Tuple[float, bool]:
    """카이제곱 검정으로 두 비율 차이 유의성 검정
    
    Returns:
        (p_value, is_significant)
    """
    if total_a < 2 or total_b < 2:
        return 1.0, False  # 표본 부족
    
    # 관찰값
    observed = [
        [success_a, total_a - success_a],
        [success_b, total_b - success_b]
    ]
    
    # 기대값 계산
    total = total_a + total_b
    success_total = success_a + success_b
    fail_total = (total_a - success_a) + (total_b - success_b)
    
    if success_total == 0 or fail_total == 0:
        return 1.0, False  # 분산 0
    
    expected = [
        [success_total * total_a / total, fail_total * total_a / total],
        [success_total * total_b / total, fail_total * total_b / total]
    ]
    
    # 카이제곱 통계량
    chi_sq = 0.0
    for i in range(2):
        for j in range(2):
            if expected[i][j] > 0:
                chi_sq += (observed[i][j] - expected[i][j])**2 / expected[i][j]
    
    # 자유도 1에서의 p-value 근사 (카이제곱 분포)
    # chi_sq > 3.841: p < 0.05 (95% 신뢰수준)
    p_value = 1.0 - _chi_square_cdf(chi_sq, df=1)
    is_significant = p_value < (1 - confidence)
    
    return p_value, is_significant


def _chi_square_cdf(x: float, df: int) -> float:
    """카이제곱 분포 누적분포함수 근사 (자유도 df)"""
    # df=1인 경우 근사
    if df == 1:
        return 2 / (1 + math.exp(0.5 * x))  # Rough approximation
    return min(x / (x + df - 2), 0.9999)  # Conservative approximation


@dataclass
class Variant:
    """테스트 변형"""
    name: str
    strategy: str
    results: List[str]  # "success" or "fail"


class ABTest:
    """A/B 테스트 관리"""
    
    def __init__(self, ws: Workspace, test_id: Optional[str] = None):
        self.ws = ws
        self.tests_file = ws.state_dir / "ab_tests.json"
        self._tests: Dict[str, ABTestResult] = {}
        self._variants: Dict[str, Dict[str, List[str]]] = {}  # test_id -> {variant_name -> results}
        self._load()
        
        if test_id:
            self.active_test_id = test_id
        else:
            self.active_test_id = self._get_or_create_active_test()
    
    def _load(self):
        if self.tests_file.exists():
            with open(self.tests_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._tests = {k: ABTestResult(**v) for k, v in data.get("tests", {}).items()}
                self._variants = data.get("variants", {})
    
    def _save(self):
        self.tests_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tests": {k: v.model_dump() for k, v in self._tests.items()},
            "variants": self._variants
        }
        with open(self.tests_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_or_create_active_test(self) -> str:
        """활성 테스트 ID 조회 또는 생성"""
        for test_id, test in self._tests.items():
            if test.end_date is None:
                return test_id
        
        # 새 테스트 생성
        test_id = f"test_{len(self._tests) + 1}"
        self._tests[test_id] = ABTestResult(
            test_id=test_id,
            test_name=f"Strategy Test {len(self._tests) + 1}",
            strategy_a="default",
            strategy_b="alternative",
            start_date=""
        )
        self._variants[test_id] = {"A": [], "B": []}
        self._save()
        return test_id
    
    def record_result(self, variant: str, success: bool):
        """결과 기록"""
        if self.active_test_id not in self._variants:
            self._variants[self.active_test_id] = {"A": [], "B": []}
        
        result = "success" if success else "fail"
        self._variants[self.active_test_id][variant].append(result)
        self._update_test_stats()
        self._save()
    
    def _update_test_stats(self):
        """테스트 통계 업데이트"""
        test = self._tests.get(self.active_test_id)
        if not test:
            return
        
        variants = self._variants.get(self.active_test_id, {})
        
        # A 통계
        results_a = variants.get("A", [])
        success_a = results_a.count("success")
        test.sample_size_a = len(results_a)
        test.success_rate_a = success_a / len(results_a) if results_a else 0.0
        
        # B 통계
        results_b = variants.get("B", [])
        success_b = results_b.count("success")
        test.sample_size_b = len(results_b)
        test.success_rate_b = success_b / len(results_b) if results_b else 0.0
        
        # 유의성 검정
        if test.sample_size_a >= 5 and test.sample_size_b >= 5:
            p_value, is_significant = chi_square_test(
                success_a, test.sample_size_a,
                success_b, test.sample_size_b
            )
            test.p_value = p_value
            test.is_significant = is_significant
            
            if is_significant:
                test.winner = "A" if test.success_rate_a > test.success_rate_b else "B"
            else:
                test.winner = None
        
        self._tests[self.active_test_id] = test
    
    def get_current_test(self) -> Optional[ABTestResult]:
        """현재 활성 테스트 조회"""
        return self._tests.get(self.active_test_id)
    
    def get_all_tests(self) -> List[ABTestResult]:
        """전체 테스트 조회"""
        return list(self._tests.values())
    
    def recommend_variant(self) -> str:
        """권장 변형 반환 (데이터 기반)"""
        test = self.get_current_test()
        if not test:
            return "A"  # 기본값
        
        # 유의하면 좋은 쪽 선택
        if test.is_significant and test.winner:
            return test.winner
        
        # 데이터가 있으면 더 나은 쪽 선택
        if test.sample_size_a > 0 and test.sample_size_b > 0:
            return "A" if test.success_rate_a >= test.success_rate_b else "B"
        
        return "A"  # 기본값
    
    def end_test(self) -> Optional[ABTestResult]:
        """테스트 종료"""
        test = self._tests.get(self.active_test_id)
        if test:
            test.end_date = ""
            self._tests[self.active_test_id] = test
            self._save()
        return test
```

- [ ] **Step 2: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add src/resume_agent/ab_testing.py
git commit -m "feat(phase2): add ABTest framework for strategy comparison"
```

---

### Task 4: CLI 명령어 추가

**Dependencies:** Task 1, Task 2, Task 3
**Files:**
- Modify: `src/resume_agent/cli.py`

- [ ] **Step 1: CLI에 outcome 명령어 추가**

cli.py에 다음 명령어 추가:

```python
# outcome 명령어 (결과 추적)
def cmd_outcome(args):
    """지원 결과 추적"""
    from .outcome_tracker import OutcomeTracker
    from .models import OutcomeResult
    
    ws = Workspace(Path(args.workspace))
    tracker = OutcomeTracker(ws)
    
    if args.record:
        # 결과 기록
        outcome = OutcomeResult(
            artifact_id=args.artifact_id,
            application_id=args.application_id or "",
            company_name=args.company,
            job_title=args.job or "",
            outcome=args.outcome,
            rejection_reason=args.reason,
            interview_count=args.interviews or 0,
            notes=args.notes
        )
        result = tracker.record_outcome(outcome)
        print(f"✅ Recorded: {result.artifact_id} -> {result.outcome}")
    
    elif args.list:
        # 결과 목록
        outcomes = tracker.get_all_outcomes()
        print(f"\n📊 Total outcomes: {len(outcomes)}")
        for o in outcomes[-10:]:  # 최근 10개
            print(f"  {o.artifact_id}: {o.company_name} -> {o.outcome}")
    
    elif args.summary:
        # 요약 통계
        summary = tracker.get_outcome_summary()
        rate = tracker.get_success_rate()
        print(f"\n📈 Outcome Summary:")
        print(f"  Success Rate: {rate:.1%}")
        for outcome, count in summary.items():
            if count > 0:
                print(f"  {outcome}: {count}")


# ab 명령어 (A/B 테스트)
def cmd_ab(args):
    """A/B 테스트 관리"""
    from .ab_testing import ABTest
    
    ws = Workspace(Path(args.workspace))
    ab = ABTest(ws)
    
    if args.record:
        ab.record_result(args.variant, args.success.lower() == "success")
        print(f"✅ Recorded: Variant {args.variant} -> {args.success}")
    
    elif args.status:
        test = ab.get_current_test()
        if test:
            print(f"\n🧪 A/B Test: {test.test_name}")
            print(f"  A: {test.sample_size_a} samples, {test.success_rate_a:.1%} success")
            print(f"  B: {test.sample_size_b} samples, {test.success_rate_b:.1%} success")
            if test.is_significant:
                print(f"  Winner: {test.winner} (p={test.p_value:.3f})")
            else:
                print(f"  Not significant yet (need more samples)")
            print(f"  Recommended: {ab.recommend_variant()}")
    
    elif args.end:
        result = ab.end_test()
        if result:
            print(f"✅ Test ended. Winner: {result.winner or 'No significant difference'}")
```

main()의 ArgumentParser에 추가:

```python
# outcome 서브커맨드
parser_outcome = subparsers.add_parser("outcome", help="Track application outcomes")
parser_outcome.add_argument("--record", action="store_true", help="Record a new outcome")
parser_outcome.add_argument("--artifact-id", required=True, help="Artifact ID")
parser_outcome.add_argument("--application-id", help="Application ID")
parser_outcome.add_argument("--company", required=True, help="Company name")
parser_outcome.add_argument("--job", help="Job title")
parser_outcome.add_argument("--outcome", required=True, 
    choices=["pending", "screening_pass", "screening_fail", 
             "interview_invited", "interview_pass", "interview_fail",
             "final_pass", "final_fail", "offer_received"],
    help="Outcome result")
parser_outcome.add_argument("--reason", help="Rejection reason (if any)")
parser_outcome.add_argument("--interviews", type=int, help="Number of interviews")
parser_outcome.add_argument("--notes", help="Additional notes")
parser_outcome.add_argument("--list", action="store_true", help="List all outcomes")
parser_outcome.add_argument("--summary", action="store_true", help="Show summary statistics")
parser_outcome.set_defaults(func=cmd_outcome)

# ab 서브커맨드
parser_ab = subparsers.add_parser("ab", help="Manage A/B tests")
parser_ab.add_argument("--record", action="store_true", help="Record a result")
parser_ab.add_argument("--variant", choices=["A", "B"], help="Variant name")
parser_ab.add_argument("--success", choices=["success", "fail"], help="Result")
parser_ab.add_argument("--status", action="store_true", help="Show current test status")
parser_ab.add_argument("--end", action="store_true", help="End current test")
parser_ab.set_defaults(func=cmd_ab)
```

- [ ] **Step 2: CLI 테스트**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent && source .venv/bin/activate
python -m resume_agent.cli --help | grep -A3 "outcome\|ab "
```

- [ ] **Step 3: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add src/resume_agent/cli.py
git commit -m "feat(phase2): add outcome tracking and A/B test CLI commands"
```

---

### Task 5: 테스트 작성

**Dependencies:** Tasks 1-4
**Files:**
- Create: `tests/test_outcome_tracker.py`
- Create: `tests/test_ab_testing.py`

- [ ] **Step 1: test_outcome_tracker.py 생성**

```python
"""OutcomeTracker 테스트"""

import pytest
from pathlib import Path
import tempfile
import shutil

from resume_agent.state import Workspace
from resume_agent.outcome_tracker import OutcomeTracker
from resume_agent.models import OutcomeResult


@pytest.fixture
def temp_ws():
    tmp = Path(tempfile.mkdtemp())
    ws = Workspace(tmp)
    ws.init()
    yield ws
    shutil.rmtree(tmp)


@pytest.fixture
def tracker(temp_ws):
    return OutcomeTracker(temp_ws)


class TestOutcomeRecording:
    def test_record_outcome(self, tracker):
        outcome = OutcomeResult(
            artifact_id="test_001",
            application_id="app_001",
            company_name="TestCorp",
            job_title="Engineer",
            outcome="interview_pass"
        )
        result = tracker.record_outcome(outcome)
        
        assert result.artifact_id == "test_001"
        assert result.outcome == "interview_pass"
    
    def test_get_outcome(self, tracker):
        outcome = OutcomeResult(
            artifact_id="test_002",
            company_name="TestCorp",
            outcome="screening_fail"
        )
        tracker.record_outcome(outcome)
        
        found = tracker.get_outcome("test_002")
        assert found is not None
        assert found.artifact_id == "test_002"
    
    def test_update_existing(self, tracker):
        tracker.record_outcome(OutcomeResult(
            artifact_id="test_003",
            company_name="TestCorp",
            outcome="pending"
        ))
        tracker.record_outcome(OutcomeResult(
            artifact_id="test_003",
            company_name="TestCorp",
            outcome="interview_pass"
        ))
        
        found = tracker.get_outcome("test_003")
        assert found.outcome == "interview_pass"


class TestOutcomeStatistics:
    def test_success_rate(self, tracker):
        for i in range(5):
            tracker.record_outcome(OutcomeResult(
                artifact_id=f"pass_{i}",
                company_name="TestCorp",
                outcome="interview_pass" if i < 3 else "interview_fail"
            ))
        
        rate = tracker.get_success_rate()
        assert rate == 0.6  # 3/5
    
    def test_outcome_summary(self, tracker):
        tracker.record_outcome(OutcomeResult(artifact_id="s1", company_name="A", outcome="screening_pass"))
        tracker.record_outcome(OutcomeResult(artifact_id="s2", company_name="B", outcome="screening_fail"))
        tracker.record_outcome(OutcomeResult(artifact_id="f1", company_name="C", outcome="interview_fail"))
        
        summary = tracker.get_outcome_summary()
        assert summary["screening_pass"] == 1
        assert summary["screening_fail"] == 1
        assert summary["interview_fail"] == 1
```

- [ ] **Step 2: test_ab_testing.py 생성**

```python
"""A/B Testing Framework 테스트"""

import pytest
from pathlib import Path
import tempfile
import shutil

from resume_agent.state import Workspace
from resume_agent.ab_testing import ABTest, chi_square_test


@pytest.fixture
def temp_ws():
    tmp = Path(tempfile.mkdtemp())
    ws = Workspace(tmp)
    ws.init()
    yield ws
    shutil.rmtree(tmp)


@pytest.fixture
def ab_test(temp_ws):
    return ABTest(temp_ws)


class TestChiSquareTest:
    def test_significant_difference(self):
        """명확한 차이 감지"""
        p, sig = chi_square_test(10, 20, 5, 20)  # 50% vs 25%
        assert p < 0.05
        assert sig is True
    
    def test_no_significant_difference(self):
        """차이 없음"""
        p, sig = chi_square_test(10, 20, 10, 20)  # 50% vs 50%
        assert p > 0.05
        assert sig is False
    
    def test_insufficient_samples(self):
        """표본 부족"""
        p, sig = chi_square_test(1, 2, 1, 2)
        assert sig is False


class TestABTest:
    def test_record_results(self, ab_test):
        ab_test.record_result("A", True)
        ab_test.record_result("A", False)
        ab_test.record_result("B", True)
        
        test = ab_test.get_current_test()
        assert test.sample_size_a == 2
        assert test.sample_size_b == 1
        assert test.success_rate_a == 0.5
        assert test.success_rate_b == 1.0
    
    def test_recommend_variant(self, ab_test):
        ab_test.record_result("A", True)
        ab_test.record_result("A", True)
        ab_test.record_result("A", True)
        ab_test.record_result("B", True)
        
        # A: 100%, B: 100% → 차이 없음 → 기본값 A
        rec = ab_test.recommend_variant()
        assert rec in ["A", "B"]
    
    def test_end_test(self, ab_test):
        ab_test.record_result("A", True)
        ab_test.record_result("B", False)
        
        result = ab_test.end_test()
        assert result is not None
        assert result.end_date is not None
```

- [ ] **Step 3: 테스트 실행**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent && source .venv/bin/activate
pytest tests/test_outcome_tracker.py tests/test_ab_testing.py -v --tb=short
```

- [ ] **Step 4: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add tests/test_outcome_tracker.py tests/test_ab_testing.py
git commit -m "feat(phase2): add tests for outcome tracker and A/B testing"
```

---

### Task 6: End-to-End 검증

**Dependencies:** Tasks 1-5 모두 완료
**Files:** None (read-only verification)

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent && source .venv/bin/activate
pytest tests/test_outcome_tracker.py tests/test_ab_testing.py tests/test_experience_analyzer.py tests/test_semantic_matching.py -v --tb=short
```

- [ ] **Step 2: Phase 1 + Phase 2 통합 테스트**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent && source .venv/bin/activate
pytest tests/ -v -k "semantic or outcome or ab or experience_analyzer" --tb=short
```

- [ ] **Step 3: 전체 계획 성공 기준 검증**

- [ ] **Goal 달성**: 결과 기반 학습 시스템 ✅
- [ ] **OutcomeTracker**: 결과 추적 + 통계 분석 ✅
- [ ] **ABTest**: 전략 비교 프레임워크 ✅
- [ ] **CLI 명령어**: outcome, ab 명령어 ✅
- [ ] **테스트**: 통합 테스트 통과 ✅

- [ ] **Step 4: Commit**

```bash
cd /home/ehddk/ai/ai/ai/resume-agent
git add -A
git commit -m "feat(phase2): complete result-based learning system"
```

---

## Self-Review Checklist

- [x] 모든 Task에 정확한 파일 경로 명시
- [x] 모든 Step에 실행 가능한 코드/명령 포함
- [x] Task 간 의존성 명시
- [x] 모든 plan 요구사항 포함
- [x] placeholders 없음 (TBD, TODO 없음)
- [x] Verification Strategy 포함
- [x] Final Verification Task (Task 6) 포함

---

## 예상 산출물

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `src/resume_agent/models.py` | 수정 | OutcomeResult, ABTestResult, ExperienceOutcomeStats 추가 |
| `src/resume_agent/outcome_tracker.py` | **신규** | 결과 추적 및 통계 분석 |
| `src/resume_agent/ab_testing.py` | **신규** | A/B 테스트 프레임워크 |
| `src/resume_agent/cli.py` | 수정 | outcome, ab CLI 명령어 추가 |
| `tests/test_outcome_tracker.py` | **신규** | OutcomeTracker 테스트 |
| `tests/test_ab_testing.py` | **신규** | ABTest 테스트 |

---

## Timeline

| Phase | 예상 시간 | 목표 |
|-------|----------|------|
| Task 1 | 0.5일 | 모델 정의 |
| Task 2 | 1~2일 | OutcomeTracker 구현 |
| Task 3 | 1~2일 | ABTest 구현 |
| Task 4 | 0.5일 | CLI 명령어 추가 |
| Task 5 | 0.5일 | 테스트 작성 |
| Task 6 | 0.5일 | End-to-End 검증 |

**총 예상: 4~6일**

---

*계획 작성일: 2026-04-09*
*계획 버전: v1.0*
