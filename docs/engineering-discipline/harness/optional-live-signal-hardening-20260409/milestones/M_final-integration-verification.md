# Milestone: Integration Verification

**ID:** M_final
**Status:** pending
**Dependencies:** M1, M2, M3
**Risk:** Medium
**Effort:** Small

## Goal

report, weighted A/B, priority-rule quality metric이 함께 동작하는지 전체 검증합니다.

## Success Criteria

- [ ] `python3 -m pytest -q -s tests/test_ab_testing.py tests/test_pipeline.py tests/test_pipeline_resume_coverage.py tests/test_cli_commands.py`가 통과한다.
- [ ] 새 report 명령에 weighted A/B 결과와 priority-rule quality metric이 함께 나타난다.
- [ ] 기존 `status`, writer/interview, outcome dashboard 경로에 회귀가 없다.

## Files Affected

- Create: None
- Modify: None (read-only verification milestone)

## User Value

개별 개선이 아니라 전체 live-signal 루프가 안정적으로 연결되었다는 확신을 제공합니다.

## Abort Point

No — 최종 게이트입니다.

## Notes

- 실패 시 개별 milestone 성공 기준이 통합 상태에서도 유지되는지 다시 점검합니다.
- cross-milestone interface를 end-to-end로 확인합니다.

