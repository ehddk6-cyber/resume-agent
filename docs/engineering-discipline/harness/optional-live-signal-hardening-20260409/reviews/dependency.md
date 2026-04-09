**Dependency DAG:**
```text
M1 (no deps) ─┬─→ M3 (depends on M1, M2) ─→ M_final
M2 (no deps) ─┘
```

**M1: A/B live-gap weighting core**
- Goal: `live_change_success_gap`를 A/B 실험 모델에 반영할 수 있는 핵심 계약을 만든다.
- Success criteria:
  - `ABTestResult`가 가중치 관련 필드를 안전하게 직렬화/역직렬화한다.
  - `ABTest`가 가중치가 있는 경우와 없는 경우를 모두 처리한다.
  - `tests/test_ab_testing.py`가 통과하고 기존 A/B 동작이 깨지지 않는다.
- Files: `src/resume_agent/ab_testing.py`, `src/resume_agent/models.py`, `tests/test_ab_testing.py`
- Depends on: None
- Leaves system in working state: Yes

**M2: Priority-rule coverage quality metric**
- Goal: writer/interview 최종 품질 점수에 `priority-rule coverage`를 정식 지표로 편입한다.
- Success criteria:
  - writer/interview 결과에 priority-rule coverage가 저장된다.
  - `build_outcome_dashboard()` / `build_kpi_dashboard()`가 새 지표를 노출한다.
  - `tests/test_pipeline.py`와 `tests/test_pipeline_resume_coverage.py`가 통과한다.
- Files: `src/resume_agent/pipeline.py`, `tests/test_pipeline.py`, `tests/test_pipeline_resume_coverage.py`
- Depends on: None
- Leaves system in working state: Yes

**M3: Cumulative report/dashboard command**
- Goal: `status`와 별개로 누적 효과를 보는 CLI 명령을 추가한다.
- Success criteria:
  - 새 CLI 명령이 A/B 가중치 결과, priority-rule coverage, live-change 효과를 한 번에 보여준다.
  - 기존 `status` 출력은 유지된다.
  - `tests/test_cli_commands.py`가 통과한다.
- Files: `src/resume_agent/cli.py`, `tests/test_cli_commands.py`
- Depends on: M1, M2
- Leaves system in working state: Yes

**M_final: Integration Verification**
- Goal: 세 변경이 함께 돌아가는지 전체 검증한다.
- Success criteria:
  - `python3 -m pytest -q -s tests/test_ab_testing.py tests/test_pipeline.py tests/test_pipeline_resume_coverage.py tests/test_cli_commands.py` 통과
  - A/B, 품질 지표, CLI 보고가 서로 충돌하지 않는다.
- Files: None
- Depends on: M1, M2, M3
- Leaves system in working state: Yes

**File conflict matrix:**
| File | Milestones | Ordering constraint |
|------|-----------|-------------------|
| `src/resume_agent/ab_testing.py` | M1 | 없음 |
| `src/resume_agent/models.py` | M1 | M1에서 계약 고정 후 사용 |
| `src/resume_agent/pipeline.py` | M2 | M2 먼저, 이후 M3가 읽기만 하도록 유지 |
| `src/resume_agent/cli.py` | M3 | M1, M2 완료 후 |
| `tests/test_ab_testing.py` | M1 | 없음 |
| `tests/test_pipeline.py` | M2 | 없음 |
| `tests/test_pipeline_resume_coverage.py` | M2 | 없음 |
| `tests/test_cli_commands.py` | M3 | M1, M2 완료 후 |

**Parallelizable groups:**
- Group A: [M1, M2] — 서로 다른 핵심 파일을 건드리고 인터페이스 의존도도 없음
- Group B: [M3] — M1/M2의 산출물을 소비
- Group C: [M_final] — 전체 통합 검증

**External dependencies:**
- `pytest`: required by M1, M2, M3, M_final, setup needed: no
- 로컬 파일 시스템(`state/`, `analysis/` JSON): required by M1, M2, M3, setup needed: no
- 외부 API/서비스: none

**Shared state:**
- `state/ab_tests.json`: M1이 쓰는 A/B 실험 상태
- `analysis/outcome_dashboard.json`, `analysis/kpi_dashboard.json`: M2가 쓰고 M3가 읽는 상태
- 새 누적 리포트 파일을 만든다면 `analysis/cumulative_effect_report.json` 같은 별도 경로로 두는 게 안전합니다

