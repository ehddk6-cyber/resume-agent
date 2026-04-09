# Milestone: Priority-Rule Coverage Quality Metric

**ID:** M3
**Status:** pending
**Dependencies:** M1
**Risk:** High
**Effort:** Medium

## Goal

writer/interview 최종 품질 점수와 dashboard에 `priority-rule coverage`를 정식 지표로 편입합니다.

## Success Criteria

- [ ] writer/interview quality 결과에 `priority_rule_coverage` 또는 동등한 metric field가 저장된다.
- [ ] `build_outcome_dashboard()`와 `build_kpi_dashboard()`가 해당 metric 또는 summary를 노출한다.
- [ ] `python3 -m pytest -q -s tests/test_pipeline.py tests/test_pipeline_resume_coverage.py -k "priority_rule or quality metric"`가 통과한다.

## Files Affected

- Modify: `src/resume_agent/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_resume_coverage.py`

## User Value

놓친 최신 신호가 품질 점수와 재작성 기준에서 수치로 드러나서 수정 우선순위를 바로 알 수 있습니다.

## Abort Point

Yes — 이 단계까지만 완료해도 writer/interview 품질 루프가 더 명확한 지표를 갖게 됩니다.

## Notes

- `priority-rule coverage`는 독립 품질 하위 지표로 추가합니다.
- 기존 overall score 의미를 유지하고, dashboard 및 tests 전반의 의미 일관성을 우선합니다.

