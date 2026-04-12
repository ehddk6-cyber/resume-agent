# M3 Priority-Rule Coverage Quality Metric Implementation Plan

> **Worker note:** Execute this plan task-by-task using the run-plan skill or subagents. Each step uses checkbox (`- [ ]`) syntax for progress tracking.

**Goal:** writer/interview 산출물의 `recent_change_priority_rule_check`를 정식 품질 하위 지표로 승격해, 최종 품질 결과와 outcome/KPI dashboard에서 일관되게 확인할 수 있게 만든다.

**Architecture:** `priority-rule coverage`는 기존 overall score를 덮어쓰지 않고 독립 metric으로 추가합니다. 산출물 실행 단계에서 이미 생성되는 audit payload를 재사용하고, `build_outcome_dashboard()`와 `build_kpi_dashboard()`는 이 값을 읽어 평균/최신 상태를 노출하도록 최소 변경합니다.

**Tech Stack:** Python 3, existing pipeline helpers, JSON state/artifact snapshots, pytest

**Work Scope:**
- **In scope:** priority-rule coverage metric 집계 helper, writer/interview 결과 payload 반영, outcome/KPI dashboard 노출, 관련 테스트 추가
- **Out of scope:** quality evaluator 대규모 산식 개편, A/B weighting 변경, 새로운 audit 파일 형식 도입

**Verification Strategy:**
- **Level:** test-suite
- **Command:** `python3 -m pytest -q -s tests/test_pipeline.py tests/test_pipeline_resume_coverage.py -k "priority_rule or quality metric"`
- **What it validates:** priority-rule coverage가 품질 metric과 dashboard에 정식 반영되고, 관련 집계가 회귀 없이 동작하는지 검증한다.

---

## File Structure Mapping

- `src/resume_agent/pipeline.py`
  - 책임: priority-rule coverage metric 집계 및 dashboard 노출
- `tests/test_pipeline.py`
  - 책임: writer/interview 품질 결과 및 KPI metric 검증
- `tests/test_pipeline_resume_coverage.py`
  - 책임: outcome dashboard/report 계열 집계 검증

## Task 1: Add priority-rule coverage as a formal quality metric

**Dependencies:** None
**Files:**
- Modify: `src/resume_agent/pipeline.py`
- Test: `tests/test_pipeline.py`

- [x] **Step 1: Locate the current quality result payload shape**

Read:
- `src/resume_agent/pipeline.py`

Identify:
- writer/interview run 결과에서 `recent_change_priority_rule_check`가 어디에 저장되는지
- existing `writer_quality.json` / artifact snapshot / rewrite 판단이 어떤 필드를 품질 지표로 쓰는지

- [x] **Step 2: Write failing metric tests**

Add tests in `tests/test_pipeline.py` that verify:
- priority-rule coverage가 있는 경우 정식 metric field가 계산된다
- coverage가 없을 때는 기존 흐름을 깨지 않고 안전한 기본값을 사용한다
- KPI 집계가 새 metric을 포함한다

Run:
```bash
python3 -m pytest -q -s tests/test_pipeline.py -k "priority_rule or quality metric"
```

Expected: FAIL because the formal metric is not yet exposed.

- [x] **Step 3: Implement the smallest metric integration**

In `src/resume_agent/pipeline.py`:
- audit payload에서 재사용 가능한 priority-rule coverage summary helper를 만든다
- writer/interview 결과 snapshot 또는 dashboard 집계가 읽기 쉬운 metric field를 갖게 한다
- overall score 의미는 유지하고 독립 metric으로만 추가한다

- [x] **Step 4: Re-run the targeted metric tests**

Run:
```bash
python3 -m pytest -q -s tests/test_pipeline.py -k "priority_rule or quality metric"
```

Expected: PASS for the new metric tests.

## Task 2: Expose the metric in outcome and KPI dashboards

**Dependencies:** Runs after Task 1 completes
**Files:**
- Modify: `src/resume_agent/pipeline.py`
- Test: `tests/test_pipeline_resume_coverage.py`

- [x] **Step 1: Add failing dashboard tests**

Add tests that verify:
- `build_outcome_dashboard()` exposes a compact priority-rule coverage summary
- `build_kpi_dashboard()` exposes the corresponding aggregate metric
- existing live-change effectiveness data remains intact

Run:
```bash
python3 -m pytest -q -s tests/test_pipeline_resume_coverage.py -k "priority_rule or quality metric"
```

Expected: FAIL because dashboard payloads do not yet expose the formal metric.

- [x] **Step 2: Implement dashboard exposure**

In `src/resume_agent/pipeline.py`:
- extend outcome dashboard with priority-rule coverage summary
- extend KPI dashboard with average/latest coverage fields
- keep field names explicit and backward-compatible

- [x] **Step 3: Re-run the targeted dashboard tests**

Run:
```bash
python3 -m pytest -q -s tests/test_pipeline_resume_coverage.py -k "priority_rule or quality metric"
```

Expected: PASS

## Task 3: Milestone verification

**Dependencies:** Runs after Task 1 and Task 2 complete
**Files:** None (read-only verification)

- [x] **Step 1: Run the milestone verification command**

Run:
```bash
python3 -m pytest -q -s tests/test_pipeline.py tests/test_pipeline_resume_coverage.py -k "priority_rule or quality metric"
```

Expected: ALL PASS

- [x] **Step 2: Verify the milestone success criteria**

Manually check:
- [x] writer/interview quality 결과에 `priority_rule_coverage` 또는 동등한 metric field가 저장된다.
- [x] `build_outcome_dashboard()`와 `build_kpi_dashboard()`가 해당 metric 또는 summary를 노출한다.
- [x] 위 targeted pytest command가 통과한다.

- [x] **Step 3: Run the broader touched-area regression check**

Run:
```bash
python3 -m pytest -q tests/test_pipeline.py tests/test_pipeline_resume_coverage.py
```

Expected: No regressions in the touched pipeline/dashboard surface.

## Self-Review

- [x] priority-rule coverage는 overall score와 분리된 독립 metric이다.
- [x] 기존 audit payload를 재사용해 중복 산식을 만들지 않는다.
- [x] dashboard 필드는 backward-compatible 하게 추가된다.
