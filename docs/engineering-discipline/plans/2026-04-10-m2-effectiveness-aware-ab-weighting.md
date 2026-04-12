# M2 Effectiveness-Aware A/B Weighting Implementation Plan

> **Worker note:** Execute this plan task-by-task using the run-plan skill or subagents. Each step uses checkbox (`- [ ]`) syntax for progress tracking.

**Goal:** `live_change_success_gap`를 A/B 테스트 결과 해석에 반영해, 동일한 승률이라도 실제 결과 격차가 더 큰 variant를 우선 추천할 수 있게 만든다.

**Architecture:** `ab_testing.py`에는 기존 A/B 집계는 유지한 채 derived weighting helper만 추가합니다. 저장 스키마는 최소 변경으로 유지하고, CLI와 report 출력은 새 helper가 만든 weighted summary를 읽기만 하도록 분리합니다.

**Tech Stack:** Python 3, argparse CLI, existing A/B state helpers, pytest

**Work Scope:**
- **In scope:** weighted recommendation 계산 helper, `ab status` 출력 보강, report payload 연동, 관련 테스트 추가
- **Out of scope:** A/B 저장 포맷 전면 개편, 신규 실험 타입 추가, M3 priority-rule quality 산식 변경

**Verification Strategy:**
- **Level:** test-suite
- **Command:** `python3 -m pytest -q -s tests/test_ab_testing.py tests/test_cli_commands.py -k "weighted or ab"`
- **What it validates:** live gap 유무에 따라 weighted recommendation이 안전하게 계산되고, CLI/status/report가 그 값을 노출하는지 검증한다.

---

## File Structure Mapping

- `src/resume_agent/ab_testing.py`
  - 책임: weighted recommendation 계산 helper 추가
- `src/resume_agent/cli.py`
  - 책임: `ab status` 또는 관련 출력에 weighted 결과 노출
- `src/resume_agent/pipeline.py`
  - 책임: cumulative report payload에 weighted A/B summary 포함
- `tests/test_ab_testing.py`
  - 책임: weighting 계산 검증
- `tests/test_cli_commands.py`
  - 책임: CLI 출력 검증

## Task 1: Add weighted recommendation helper

**Dependencies:** None
**Files:**
- Modify: `src/resume_agent/ab_testing.py`
- Test: `tests/test_ab_testing.py`

- [x] **Step 1: Locate the current A/B result model and recommendation path**

Read:
- `src/resume_agent/ab_testing.py`
- any related models used by `ab status`

Identify:
- base success-rate recommendation rule
- where `live_change_success_gap` can be injected without breaking current callers

- [x] **Step 2: Write failing weighting tests**

Add tests in `tests/test_ab_testing.py` that verify:
- when live gap is missing, recommendation matches the current behavior
- when live gap exists, weighted recommendation prefers the variant with stronger combined signal
- weighted payload includes both raw rate and adjusted score

Run:
```bash
python3 -m pytest -q -s tests/test_ab_testing.py -k "weighted or ab"
```

Expected: FAIL because weighted helper does not exist yet.

- [x] **Step 3: Implement the minimal weighting helper**

Add a helper in `src/resume_agent/ab_testing.py` that:
- accepts existing A/B summary plus optional `live_change_success_gap`
- returns a derived weighted summary
- preserves current raw summary fields
- does not require a schema migration unless strictly necessary

- [x] **Step 4: Re-run the targeted A/B tests**

Run:
```bash
python3 -m pytest -q -s tests/test_ab_testing.py -k "weighted or ab"
```

Expected: PASS for the new weighting tests.

## Task 2: Surface weighted recommendation in CLI/report

**Dependencies:** Runs after Task 1 completes
**Files:**
- Modify: `src/resume_agent/cli.py`
- Modify: `src/resume_agent/pipeline.py`
- Test: `tests/test_cli_commands.py`

- [x] **Step 1: Add a failing CLI/report test**

Add tests that:
- patch the A/B weighting helper
- run `ab status` or the relevant CLI output path
- assert weighted recommendation and adjusted score are shown
- optionally assert `build_cumulative_effect_report()` includes weighted A/B summary

Run:
```bash
python3 -m pytest -q -s tests/test_cli_commands.py -k "weighted or ab"
```

Expected: FAIL because the output does not yet include weighted data.

- [x] **Step 2: Implement the smallest output changes**

In `src/resume_agent/cli.py` and `src/resume_agent/pipeline.py`:
- call the new weighting helper
- expose weighted recommendation in `ab status`
- include a compact weighted A/B block in cumulative report payload

Keep existing raw metrics visible so behavior is explainable.

- [x] **Step 3: Re-run the targeted CLI/report tests**

Run:
```bash
python3 -m pytest -q -s tests/test_cli_commands.py -k "weighted or ab"
```

Expected: PASS

## Task 3: Milestone verification

**Dependencies:** Runs after Task 1 and Task 2 complete
**Files:** None (read-only verification)

- [x] **Step 1: Run the milestone verification command**

Run:
```bash
python3 -m pytest -q -s tests/test_ab_testing.py tests/test_cli_commands.py -k "weighted or ab"
```

Expected: ALL PASS

- [x] **Step 2: Verify the milestone success criteria**

Manually check:
- [ ] live gap이 없을 때는 기존 추천과 동일하게 동작한다.
- [ ] live gap이 있을 때는 weighted recommendation을 계산하고 `ab status` 또는 report payload에 노출한다.
- [ ] 위 targeted pytest command가 통과한다.

- [x] **Step 3: Run the broader touched-area regression check**

Run:
```bash
python3 -m pytest -q tests/test_ab_testing.py tests/test_cli_commands.py
```

Expected: No regressions in the touched A/B and CLI surface.

## Self-Review

- [x] weighted recommendation은 raw 승률을 숨기지 않고 derived 값으로만 추가된다.
- [x] 저장 포맷 변경은 최소화되어 기존 `ab_tests.json` 호환성이 유지된다.
- [x] report/CLI 출력은 계산 helper를 재사용하고 별도 산식을 복제하지 않는다.
