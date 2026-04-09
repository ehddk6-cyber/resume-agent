# M1 Cumulative Effect Report Foundation Implementation Plan

> **Worker note:** Execute this plan task-by-task using the run-plan skill or subagents. Each step uses checkbox (`- [ ]`) syntax for progress tracking.

**Goal:** 기존 live-signal 누적 학습 결과를 `status`와 분리된 `report` 명령과 JSON 산출물로 제공해, 사용자가 cumulative effect를 바로 확인할 수 있게 만든다.

**Architecture:** `pipeline.py`에 읽기 전용 집계 helper를 추가하고, `cli.py`는 그 helper가 만든 payload를 출력만 하도록 유지합니다. 기존 `status`와 `outcome/kpi dashboard` 생성 경로는 그대로 두고, 새 report는 이미 존재하는 dashboard 요약을 재사용하는 얇은 집계 레이어로 구현합니다.

**Tech Stack:** Python 3, argparse CLI, existing `pipeline.py` JSON helpers, pytest

**Work Scope:**
- **In scope:** cumulative effect report payload 생성, `resume-agent report` CLI 추가, 관련 테스트 추가
- **Out of scope:** A/B weighting 로직 변경, priority-rule quality score 산식 변경, 기존 `status` 출력 구조 개편

**Verification Strategy:**
- **Level:** test-suite
- **Command:** `python3 -m pytest -q -s tests/test_cli_commands.py tests/test_pipeline_resume_coverage.py -k "report or cumulative"`
- **What it validates:** 새 report 집계 함수와 CLI 명령이 cumulative effect 데이터를 안전하게 생성·출력하고 기존 경로와 충돌하지 않는다는 점을 검증한다.

---

## File Structure Mapping

- `src/resume_agent/pipeline.py`
  - 책임: cumulative effect report payload 생성 helper 추가
- `src/resume_agent/cli.py`
  - 책임: `report` 서브커맨드 추가 및 payload 출력
- `tests/test_pipeline_resume_coverage.py`
  - 책임: report payload 생성 검증
- `tests/test_cli_commands.py`
  - 책임: 새 CLI 명령 파서/출력 검증

## Task 1: Add cumulative effect report payload builder

**Dependencies:** None
**Files:**
- Modify: `src/resume_agent/pipeline.py`
- Test: `tests/test_pipeline_resume_coverage.py`

- [ ] **Step 1: Locate the existing dashboard builders and choose the shared fields for the report payload**

Read:
- `src/resume_agent/pipeline.py` around `build_outcome_dashboard`
- `src/resume_agent/pipeline.py` around `build_kpi_dashboard`

Decide the report payload fields and keep them read-only:
- `generated_at`
- `artifact_type`
- `outcome_dashboard` summary
- `kpi_dashboard` summary
- `live_change_effectiveness`
- `live_change_action_learning`

- [ ] **Step 2: Write a failing report payload test**

Add a test in `tests/test_pipeline_resume_coverage.py` that:
- creates a temp workspace
- seeds enough JSON/state so dashboard helpers can run
- calls the new report builder
- asserts the payload contains cumulative effect data and writes `analysis/cumulative_effect_report.json`

Run:
```bash
python3 -m pytest -q -s tests/test_pipeline_resume_coverage.py -k "report or cumulative"
```

Expected: FAIL because the report builder does not exist yet.

- [ ] **Step 3: Implement the minimal report builder**

Add a new helper in `src/resume_agent/pipeline.py` with a narrow contract, for example:
- loads/derives `outcome_dashboard`
- loads/derives `kpi_dashboard`
- composes a single read-only payload
- writes `ws.analysis_dir / "cumulative_effect_report.json"`
- returns the payload

Keep it additive only. Do not alter `build_outcome_dashboard()` or `build_kpi_dashboard()` semantics.

- [ ] **Step 4: Re-run the targeted payload test**

Run:
```bash
python3 -m pytest -q -s tests/test_pipeline_resume_coverage.py -k "report or cumulative"
```

Expected: PASS for the new report payload test.

## Task 2: Add the report CLI command

**Dependencies:** Runs after Task 1 completes
**Files:**
- Modify: `src/resume_agent/cli.py`
- Test: `tests/test_cli_commands.py`

- [ ] **Step 1: Add a failing CLI test**

Add a test in `tests/test_cli_commands.py` that:
- builds parser args for `report`
- patches the new pipeline report builder
- runs the handler
- asserts the report summary is printed

Run:
```bash
python3 -m pytest -q -s tests/test_cli_commands.py -k "report"
```

Expected: FAIL because the command and handler do not exist yet.

- [ ] **Step 2: Add the parser entry and handler**

In `src/resume_agent/cli.py`:
- import the new pipeline report builder
- add `report` subparser
- implement `cmd_report(args)`

Handler contract:
- loads workspace
- loads project if needed by the builder
- calls the report builder
- prints a compact human-readable summary

Do not modify `cmd_status()` behavior except shared helper reuse if clearly needed.

- [ ] **Step 3: Re-run the targeted CLI test**

Run:
```bash
python3 -m pytest -q -s tests/test_cli_commands.py -k "report"
```

Expected: PASS for the new CLI command test.

## Task 3: Milestone verification

**Dependencies:** Runs after Task 1 and Task 2 complete
**Files:** None (read-only verification)

- [ ] **Step 1: Run the milestone verification command**

Run:
```bash
python3 -m pytest -q -s tests/test_cli_commands.py tests/test_pipeline_resume_coverage.py -k "report or cumulative"
```

Expected: ALL PASS

- [ ] **Step 2: Verify the milestone success criteria**

Manually check:
- [ ] `resume-agent report <workspace>` 또는 동등한 새 명령이 추가되었다.
- [ ] `analysis/cumulative_effect_report.json` 또는 동등한 산출물에 최소 `live_change_effectiveness`, `live_change_action_learning`, `tracked_outcomes`가 포함된다.
- [ ] 위의 targeted pytest command가 통과한다.

- [ ] **Step 3: Run the broader regression check for touched areas**

Run:
```bash
python3 -m pytest -q -s tests/test_cli_commands.py tests/test_pipeline_resume_coverage.py
```

Expected: No regressions in the touched CLI/report coverage area.

## Self-Review

- [ ] 새 report는 읽기 전용 집계 레이어에 머무르고 기존 dashboard 의미를 바꾸지 않는다.
- [ ] `status`와 `report`의 책임이 분리되어 있다.
- [ ] 계획 안의 모든 단계는 현재 코드베이스 기준으로 바로 실행 가능하다.
