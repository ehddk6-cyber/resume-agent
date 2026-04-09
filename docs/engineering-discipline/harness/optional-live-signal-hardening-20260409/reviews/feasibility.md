**Feasibility**

이건 현재 기술 스택으로 충분히 가능합니다. 이미 `pipeline.py`가 `live_change_success_gap`, `priority-rule coverage`, `outcome_dashboard`, `kpi_dashboard`를 계산하고 있고, `ab_testing.py`와 `cli.py`도 JSON 상태 기반으로 확장 가능한 형태라서 외부 서비스나 큰 구조 변경이 필요하지 않습니다.

다만 구현 난도가 낮은 건 아닙니다. 특히 `live_change_success_gap`를 A/B 결과에 “어떻게” 반영할지, 그리고 priority-rule coverage를 최종 품질 점수에 “어느 지점에서” 편입할지가 설계 포인트입니다. 기술적으로는 가능하지만, 이 두 부분은 정책 결정이 필요해서 underestimation 위험이 있습니다.

**Suggested Milestones**

- **Name:** A/B live-signal weighting
- **Effort:** Medium
- **Feasibility risk:** Low - 현재 `live_change_effectiveness`와 `ABTest`의 결과 추천 로직이 이미 분리돼 있어서, 가중치 계산을 덧붙이는 방식으로 구현 가능합니다.
- **Key deliverable:** `live_change_success_gap`를 A/B 추천/집계에 반영하는 로직과 그에 대한 단위 테스트

- **Name:** Priority-rule quality scoring
- **Effort:** Medium
- **Feasibility risk:** Low - `recent_change_priority_rule_check`와 writer/interview 품질 산출물이 이미 존재하므로, 최종 점수 계산에 새 지표를 추가하는 형태가 자연스럽습니다.
- **Key deliverable:** writer/interview 최종 품질 점수에 priority-rule coverage를 공식 지표로 편입하고, 관련 대시보드/테스트를 갱신

- **Name:** Cumulative report command
- **Effort:** Medium
- **Feasibility risk:** Low - `status`와 `outcome_dashboard`/`kpi_dashboard` 생성 경로가 이미 있으므로, 별도 `report` 또는 `dashboard` CLI로 묶어 노출하는 건 추가 구현 범위입니다.
- **Key deliverable:** 누적 효과를 별도 명령으로 출력/저장하는 CLI와 JSON 리포트 파일, 그리고 검증 테스트

**Spike Candidates**

- `live_change_success_gap`를 A/B에서 어디까지 반영할지 정책 결정이 필요합니다. 추천 점수만 조정할지, 동률 해소용 힌트로 둘지, 아니면 통계 유의성 판단에도 개입할지 먼저 정해야 합니다.
- report/dashboard 명령의 출력 형태는 spike가 있으면 좋습니다. 콘솔 요약만 둘지, JSON 저장까지 기본으로 둘지에 따라 테스트 경계가 달라집니다.

**Underestimation Risks**

- `ab_testing.py`의 상태 직렬화 호환성입니다. `ABTestResult` 구조를 바꾸면 기존 `ab_tests.json`과의 호환을 신경 써야 합니다.
- quality scoring은 `pipeline.py`, `build_kpi_dashboard()`, `build_outcome_dashboard()`, CLI 출력이 같이 움직일 가능성이 높아서, 한 군데만 바꾸면 수치가 어긋날 수 있습니다.
- `report/dashboard`는 “보여주기만 하는 명령”처럼 보여도, 실제로는 outcome 재계산과 KPI refresh가 함께 필요할 수 있어 regression 범위가 생각보다 넓습니다.
- 기존 `status` 출력과 새 `report` 출력이 중복되거나 서로 다른 기준을 쓰면 혼란이 생기므로, 공통 요약 함수를 따로 두는 쪽이 안전합니다.

