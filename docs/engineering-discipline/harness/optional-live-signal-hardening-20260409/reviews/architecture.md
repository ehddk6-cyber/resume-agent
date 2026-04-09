현재 코드 경계를 기준으로 보면, 이 3개 요구는 서로 완전히 한 덩어리는 아니고 `실험 scoring`, `품질 scoring`, `리포트/CLI`의 3층으로 나누는 게 가장 안전합니다. 기존 구현은 [ab_testing.py](/home/ehddk/ai/ai/ai/resume-agent/src/resume_agent/ab_testing.py), [pipeline.py](/home/ehddk/ai/ai/ai/resume-agent/src/resume_agent/pipeline.py), [cli.py](/home/ehddk/ai/ai/ai/resume-agent/src/resume_agent/cli.py)로 이미 역할이 갈려 있어서, 그 경계를 그대로 살리는 편이 최소 변경에 맞습니다.

**M1: Effectiveness-Aware A/B Scoring**
- **Architectural rationale:** A/B 로직은 현재 샘플 집계와 추천에만 책임이 있습니다. 여기에 `live_change_success_gap`를 직접 섞기보다, 별도 scoring contract를 두어 A/B 결과 해석만 확장하는 게 인터페이스를 덜 흔듭니다.
- **Interfaces defined:** `ABTest`의 기존 집계 API는 유지하고, weighted recommendation payload 또는 pure scoring helper를 추가합니다. `ab status`는 기존 결과에 더해 live-effectiveness 가중치를 읽을 수 있어야 합니다.
- **Depends on:** None.
- **Leaves system in working state:** Yes. 가중치 입력이 없으면 기존 A/B 결과와 동일하게 동작해야 합니다.
- **Verification:** `tests/test_ab_testing.py`에서 가중치 없는 기존 동작과 weighted recommendation 케이스를 모두 통과시키고, `tests/test_cli_commands.py`의 `ab status` 경로가 새 추천 정보를 노출하는지 확인합니다.

**M2: Priority-Rule Quality Metric Formalization**
- **Architectural rationale:** `recent_change_priority_rule_check`는 이미 writer/interview 실행 경로에서 생성되고 있습니다. 이 단계는 그 결과를 최종 품질 점수의 정식 입력으로 승격시키는 경계라서, 실험 scoring과 분리하는 편이 좋습니다.
- **Interfaces defined:** writer/interview 품질 결과에 `priority_rule_coverage` 또는 동등한 정식 metric field를 추가하고, `build_kpi_dashboard()`/`build_outcome_dashboard()`가 그 값을 읽도록 안정화합니다. 기존 quality metrics schema는 유지하고 새 필드만 더합니다.
- **Depends on:** M1. 개념상 독립이지만, 최소 변경 기준으로는 공유하는 `pipeline.py`/대시보드 경로를 순서대로 편집하는 편이 안전합니다.
- **Leaves system in working state:** Yes. 새 metric은 additive여야 하고, 기존 quality score 계산은 그대로 유지되어야 합니다.
- **Verification:** `tests/test_pipeline.py`와 `tests/test_pipeline_resume_coverage.py`에서 priority-rule coverage가 quality result와 dashboard에 반영되는지 검증하고, `tests/test_cli_commands.py`의 `status`가 기존 live 지표와 충돌 없이 출력되는지 확인합니다.

**M3: Cumulative Effect Report Command**
- **Architectural rationale:** 리포트/대시보드는 앞선 두 데이터 계약을 소비만 하는 얇은 조립 레이어여야 합니다. 여기서 새로운 business logic을 만들면 중복이 생기므로, pipeline이 만든 요약을 CLI가 그대로 보여주는 구조가 맞습니다.
- **Interfaces defined:** `resume-agent report` 또는 `resume-agent dashboard` 같은 별도 서브커맨드를 추가하고, cumulative effect report JSON 또는 텍스트 패널을 생성합니다. 내용은 `live_change_success_gap`, A/B weighting 결과, priority-rule coverage, outcome/kpi 요약을 한 화면에 묶는 형태가 적절합니다.
- **Depends on:** M1, M2.
- **Leaves system in working state:** Yes. 기존 `status`는 유지하고, 새 명령은 추가 기능으로만 들어가야 합니다.
- **Verification:** `tests/test_cli_commands.py`에서 새 커맨드 파서/핸들러를 검증하고, `tests/test_pipeline_resume_coverage.py` 또는 `tests/test_pipeline.py`에서 생성된 cumulative report에 M1/M2의 핵심 필드가 함께 들어가는지 확인합니다.

**Interface risks**
- `live_change_success_gap`를 `ab_tests.json`에 저장할지, 실행 시점에 `outcome_dashboard.json`에서 읽을지 결정이 필요합니다. 저장 형식을 늘리면 장기 호환성 이슈가 생깁니다.
- `priority_rule_coverage`가 최종 quality score의 한 항목인지, 별도 penalty/bonus인지 정해야 합니다. 이걸 애매하게 두면 `writer_quality.json`과 `writer_result_quality.json`의 의미가 흔들립니다.
- 새 CLI 명령 이름이 `report`인지 `dashboard`인지, 그리고 사람이 읽는 출력과 JSON 산출물 중 어느 쪽이 기본인지 먼저 고정하는 게 좋습니다.

**Pattern conflicts**
- `ab_testing.py` 안에 리포트 포맷팅까지 넣는 건 기존 패턴과 어긋납니다. 거기는 scoring/persistence까지만 두고, 출력은 CLI나 pipeline helper가 맡는 편이 맞습니다.
- CLI에서 live-effectiveness 계산을 다시 구현하면 `pipeline.py`와 중복됩니다. 이미 있는 dashboard/report 생성 함수를 재사용하는 쪽이 맞습니다.
- `status`를 새 요구로 과도하게 비대하게 만들기보다, 별도 `report`/`dashboard` 명령을 추가하는 편이 기존 패턴과 더 잘 맞습니다.

권장 순서는 `M1 -> M2 -> M3`입니다. 이후 long-run으로 넘길 때는 마지막에 표준 `Integration Verification` 마일스톤을 붙이면 됩니다.

