## Conflict Resolution Log

| Conflict | Resolution | Rationale |
|----------|-----------|-----------|
| 첫 milestone을 `A/B weighting`으로 둘지 `report/dashboard`로 둘지 | `report/dashboard foundation`을 M1로 채택 | user-value 분석은 이게 최소 가시 가치라고 봤고, skill hard gate도 첫 milestone을 minimum viable milestone으로 요구합니다. 리스크는 M1을 읽기 전용 집계 레이어로 제한해서 낮춥니다. |
| `report`는 M1/M2 이후에만 가능하다는 관점 vs 먼저 보여줘야 한다는 관점 | M1은 “기존 데이터 기반 report foundation”, M2/M3는 upstream 지표 강화로 분리 | CLI/pipeline 중복 없이 시작할 수 있고, 이후 새 지표가 들어와도 M1 계약을 유지한 채 확장 가능합니다. |
| `live_change_success_gap`를 `ab_tests.json`에 바로 저장할지 | 우선은 계산 계약과 출력 계약을 분리하고, derived 값은 필요 최소만 저장 | 기존 A/B 상태 스키마 호환성 리스크가 가장 큽니다. 먼저 계산/추천 규칙을 고정하는 편이 안전합니다. |
| `priority-rule coverage`를 penalty/bonus로 볼지 독립 지표로 볼지 | 정식 품질 하위 지표로 추가하고, 기존 overall score 의미는 유지 | pipeline/dashboard/test 전반에서 의미 일관성을 지키기 쉽습니다. |

## Milestone DAG

### M1: Cumulative Effect Report Foundation
- **Goal:** 기존 live-signal 학습 결과를 `status`와 별개로 보는 전용 `report/dashboard` 명령과 집계 payload를 만듭니다.
- **Success Criteria:**
  - [ ] `resume-agent report <workspace>` 또는 동등한 새 명령이 추가되고, 누적 효과 요약을 출력합니다.
  - [ ] `analysis/cumulative_effect_report.json` 또는 동등한 리포트 산출물에 최소 `live_change_effectiveness`, `live_change_action_learning`, `tracked_outcomes`가 포함됩니다.
  - [ ] `python3 -m pytest -q -s tests/test_cli_commands.py tests/test_pipeline_resume_coverage.py -k "report or cumulative"`가 통과합니다.
- **Dependencies:** None
- **Files:** `src/resume_agent/cli.py`, `src/resume_agent/pipeline.py`, `tests/test_cli_commands.py`, `tests/test_pipeline_resume_coverage.py`
- **Risk:** Medium
- **Effort:** Medium
- **User Value:** 사용자가 live-signal 학습이 실제로 누적되고 있는지 바로 확인할 수 있습니다.
- **Abort Point:** Yes

### M2: Effectiveness-Aware A/B Weighting
- **Goal:** `live_change_success_gap`를 A/B 결과 해석에 반영하는 계산 계약과 추천 로직을 추가합니다.
- **Success Criteria:**
  - [ ] `ABTest`가 live gap이 없을 때는 기존 추천과 동일하게 동작하고, gap이 있을 때는 weighted recommendation을 계산합니다.
  - [ ] `ab status` 또는 report payload에 weighted recommendation이 노출됩니다.
  - [ ] `python3 -m pytest -q -s tests/test_ab_testing.py tests/test_cli_commands.py -k "weighted or ab"`가 통과합니다.
- **Dependencies:** M1
- **Files:** `src/resume_agent/ab_testing.py`, `src/resume_agent/models.py`, `src/resume_agent/cli.py`, `tests/test_ab_testing.py`, `tests/test_cli_commands.py`
- **Risk:** High
- **Effort:** Medium
- **User Value:** 실험 추천이 단순 승률이 아니라 실제 결과 격차까지 반영하게 됩니다.
- **Abort Point:** Yes

### M3: Priority-Rule Coverage Quality Metric
- **Goal:** writer/interview 최종 품질 점수와 dashboard에 `priority-rule coverage`를 정식 지표로 편입합니다.
- **Success Criteria:**
  - [ ] writer/interview quality 결과에 `priority_rule_coverage` 또는 동등한 metric field가 저장됩니다.
  - [ ] `build_outcome_dashboard()`와 `build_kpi_dashboard()`가 해당 metric/summary를 노출합니다.
  - [ ] `python3 -m pytest -q -s tests/test_pipeline.py tests/test_pipeline_resume_coverage.py -k "priority_rule or quality metric"`가 통과합니다.
- **Dependencies:** M1
- **Files:** `src/resume_agent/pipeline.py`, `tests/test_pipeline.py`, `tests/test_pipeline_resume_coverage.py`
- **Risk:** High
- **Effort:** Medium
- **User Value:** 어떤 최신 신호를 놓쳤는지 품질 점수와 재작성 기준에서 수치로 바로 드러납니다.
- **Abort Point:** Yes

## Execution Order

```text
Phase 1: M1
Phase 2 (parallel): M2, M3
Phase 3: M_final
```

## Rejected Proposals

| Proposal | Source | Reason for rejection |
|----------|--------|---------------------|
| `A/B weighting`을 첫 milestone으로 시작 | Risk / Architecture | 리스크상 타당하지만, first milestone must be minimum viable milestone 조건을 만족시키기 어렵고 사용자 가시성이 약합니다. |
| `report/dashboard`를 마지막에만 추가 | Architecture / Dependency | 그러면 중간 산출물이 덜 demoable해지고, long-run 초반 피드백 루프가 약해집니다. |
| 세 작업을 하나의 milestone으로 묶기 | General synthesis | 파일 경계와 테스트 경계가 다르고, 실패 시 복구 비용이 너무 커집니다. |
| `live_change_success_gap`를 바로 영구 저장 스키마로 확대 | Architecture | `ab_tests.json` 호환성 리스크가 커서 계산 계약을 먼저 고정하는 편이 안전합니다. |

