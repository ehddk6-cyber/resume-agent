# Milestone: Cumulative Effect Report Foundation

**ID:** M1
**Status:** executing
**Dependencies:** None
**Risk:** Medium
**Effort:** Medium

## Goal

기존 live-signal 학습 결과를 `status`와 별개로 보는 전용 `report/dashboard` 명령과 집계 payload를 만듭니다.

## Success Criteria

- [ ] `resume-agent report <workspace>` 또는 동등한 새 명령이 추가된다.
- [ ] `analysis/cumulative_effect_report.json` 또는 동등한 산출물에 최소 `live_change_effectiveness`, `live_change_action_learning`, `tracked_outcomes`가 포함된다.
- [ ] `python3 -m pytest -q -s tests/test_cli_commands.py tests/test_pipeline_resume_coverage.py -k "report or cumulative"`가 통과한다.

## Files Affected

- Create: `analysis/cumulative_effect_report.json` 또는 동등한 새 report 산출물 경로
- Modify: `src/resume_agent/cli.py`
- Modify: `src/resume_agent/pipeline.py`
- Modify: `tests/test_cli_commands.py`
- Modify: `tests/test_pipeline_resume_coverage.py`

## User Value

사용자가 live-signal 학습 효과가 실제로 누적되는지 별도 명령으로 바로 확인할 수 있습니다.

## Abort Point

Yes — 이 단계까지만 완료해도 기존 `status`보다 더 깊은 누적 효과 리포트를 사용할 수 있습니다.

## Notes

- M1은 읽기 전용 집계 레이어에 집중합니다.
- 기존 `status`를 비대하게 만들지 말고, 별도 명령으로 책임을 분리합니다.
