**Value-ordered milestone sequence:**
1. `Separate cumulative effect report/dashboard command` — **Value:** `status`보다 더 깊은 누적 효과 요약을 바로 볼 수 있어서, 사용자가 live-signal 학습이 실제로 쌓이고 있다는 걸 가장 빨리 체감할 수 있습니다. `live_change_effectiveness`, `live_change_action_learning`, `top_missing_titles`를 한 화면에 모아주는 게 가장 눈에 보이는 가치입니다. — **Demo:** 새 `report` 또는 `dashboard` CLI를 실행해 요약이 출력되고, `outcome_dashboard.json`과 `kpi_dashboard.json`에 동일한 누적 효과 항목이 생성되는지 확인합니다.
2. `Priority-rule coverage in final quality scores` — **Value:** writer/interview 결과에 `priority-rule coverage`가 정식 점수로 들어가면, 사용자는 무엇이 부족했는지 숫자로 확인할 수 있고 다음 수정 기준이 훨씬 선명해집니다. 체감은 즉시적이고, 기존 품질 루프를 직접 강화합니다. — **Demo:** writer/interview 실행 후 quality 결과와 대시보드에 새 메트릭이 보이고, coverage가 낮을 때 점수 또는 rewrite 판단이 바뀌는 테스트를 확인합니다.
3. `live_change_success_gap weighting in A/B` — **Value:** 실험 추천이 단순 승률이 아니라 실제 결과 격차를 반영하게 되어, 장기적으로 더 좋은 전략 선택으로 이어집니다. 다만 사용자가 바로 보는 변화는 앞선 두 작업보다 덜 직접적입니다. — **Demo:** `ab status`/`ab end`와 단위 테스트에서 동일 샘플 조건일 때 가중치 반영 전후의 추천이나 winner 판단이 달라지는지 확인합니다.

**Minimum viable milestone:** `Separate cumulative effect report/dashboard command` 입니다. 기존 데이터만으로도 바로 사용자 가치를 만들고, live-signal 누적 루프가 실제로 보이는지 가장 빨리 증명합니다.

**Natural abort points:** `Separate cumulative effect report/dashboard command` 이후, `Priority-rule coverage in final quality scores` 이후입니다. 둘 다 중간에 멈춰도 각각 독립적으로 쓸모가 있습니다.

**Low-value milestones:** `live_change_success_gap weighting in A/B` 입니다. 중요하긴 하지만 내부 최적화 성격이 강해서, 일정이 짧으면 마지막으로 미뤄도 됩니다.

