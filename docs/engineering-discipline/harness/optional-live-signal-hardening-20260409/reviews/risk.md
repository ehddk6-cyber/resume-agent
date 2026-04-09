- Risk: `live_change_success_gap`를 A/B 결과에 반영하는 순간, `ABTest.recommend_variant()`와 기존 성공률/유의성 로직의 의미가 바뀔 수 있습니다.
- Severity: High
- Affected milestone(s): M1 `Weighted A/B decision contract`
- Mitigation: `src/resume_agent/ab_testing.py` 안에서 먼저 순수 함수/계산 계약을 고정하고, 기존 A/B 결과와 새 가중치 결과를 병행 노출한 뒤 교체합니다. `tests/test_ab_testing.py`로 기본 추천, 가중 추천, 경계값을 먼저 잠그면 이후 `pipeline.py`와 `cli.py` 연결 리스크가 줄어듭니다.

- Risk: `priority-rule coverage`를 “정식 품질 지표”로 올리는 기준이 애매하면, writer/interview 품질 점수와 재작성 조건, 대시보드 수치가 서로 다른 해석을 가지게 됩니다.
- Severity: High
- Affected milestone(s): M2 `Priority-rule coverage scoring`
- Mitigation: 커버리지 정의를 한 군데에서만 계산하고, writer/interview 결과 요약과 `kpi_dashboard.json`은 그 값을 재사용하게 만듭니다. `pipeline.py`의 audit 출력과 `tests/test_pipeline.py`, `tests/test_pipeline_resume_coverage.py`를 함께 묶어, 점수 산식이 흔들려도 바로 검출되게 해야 합니다.

- Risk: 별도 `report/dashboard` CLI는 겉보기엔 단순하지만, 실제로는 `outcome_dashboard.json`, `kpi_dashboard.json`, live-change effectiveness 요약, A/B 결과를 한 화면에 묶는 인터페이스 계약이 필요합니다.
- Severity: Medium
- Affected milestone(s): M3 `Cumulative effect report CLI`
- Mitigation: 새 명령은 처음부터 “읽기 전용 집계”로 제한하고, 기존 `status`와 출력 책임을 분리합니다. `cli.py`와 `tests/test_cli_commands.py`에서 JSON 파일 읽기와 콘솔 렌더링을 분리해 두면 회귀 범위가 작아집니다.

- Risk: 외부 API나 새 서비스 의존성은 없지만, 여러 기능이 `state/*.json`과 `analysis/*.json`의 기존 스키마에 강하게 의존합니다. 스냅샷 형식이 조금만 달라도 downstream이 깨질 수 있습니다.
- Severity: Low
- Affected milestone(s): M1, M2, M3
- Mitigation: 새 필드는 전부 선택적으로 추가하고, 누락 시 0값이나 빈 배열로 안전하게 처리합니다. temp workspace 기반 테스트로 파일 부재, 빈 파일, 과거 스키마를 모두 한 번씩 확인하면 됩니다.

Overall risk-ordered milestone sequence:
1. `M1 Weighted A/B decision contract` — 가장 높은 통합 리스크와 의미 변경 리스크가 있어서 먼저 잠가야 합니다. 여기서 가중치 계약이 안정되면 뒤의 품질 점수와 리포트가 같은 기준을 공유할 수 있습니다.
2. `M2 Priority-rule coverage scoring` — 내부 데이터 흐름이 가장 넓게 퍼지지만, M1 이후면 live-change 데이터 계약이 안정되어 있어 추적이 쉬워집니다. writer/interview 품질과 대시보드가 같이 맞물리므로 그다음이 적절합니다.
3. `M3 Cumulative effect report CLI` — 사용자 가시성이 높고 검증은 쉽지만, 앞선 두 milestone의 산출물을 소비하는 단계라 마지막이 안전합니다. 실패해도 되돌림 비용이 가장 낮습니다.

