# Milestone: Effectiveness-Aware A/B Weighting

**ID:** M2
**Status:** pending
**Dependencies:** M1
**Risk:** High
**Effort:** Medium

## Goal

`live_change_success_gap`를 A/B 결과 해석에 반영하는 계산 계약과 추천 로직을 추가합니다.

## Success Criteria

- [ ] live gap이 없을 때는 기존 추천과 동일하게 동작한다.
- [ ] live gap이 있을 때는 weighted recommendation을 계산하고 `ab status` 또는 report payload에 노출한다.
- [ ] `python3 -m pytest -q -s tests/test_ab_testing.py tests/test_cli_commands.py -k "weighted or ab"`가 통과한다.

## Files Affected

- Modify: `src/resume_agent/ab_testing.py`
- Modify: `src/resume_agent/models.py`
- Modify: `src/resume_agent/cli.py`
- Modify: `tests/test_ab_testing.py`
- Modify: `tests/test_cli_commands.py`

## User Value

실험 추천이 단순 승률이 아니라 실제 결과 격차를 반영하게 됩니다.

## Abort Point

Yes — 이 단계까지만 완료해도 더 나은 variant 추천 근거를 실험 루프에 반영할 수 있습니다.

## Notes

- `ab_tests.json` 호환성 리스크가 크므로 저장 스키마 확대는 최소화합니다.
- 계산 계약과 출력 계약을 먼저 분리하고, derived 값은 필요 최소만 저장합니다.

