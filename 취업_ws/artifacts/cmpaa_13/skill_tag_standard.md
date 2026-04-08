# JD 기반 스킬 태그 표준안 (CMPAA-13)

## 1) 태그 네이밍 규칙

- 형식: `domain.subdomain.skill`
- 소문자 + 점(`.`) 구분
- 최대 3단계 권장 (필요 시 4단계 허용)
- 예: `ops.document.writing`, `analytics.data.interpretation`

## 2) 태그 분류 체계

| Domain | 설명 | 예시 태그 |
|---|---|---|
| `ops` | 행정/운영 실무 수행 역량 | `ops.process.execution`, `ops.document.writing`, `ops.ms_office.excel` |
| `customer` | 민원/고객 대응 역량 | `customer.communication`, `customer.issue_resolution` |
| `analytics` | 데이터/수치 해석 및 보고 역량 | `analytics.data.interpretation`, `analytics.reporting` |
| `planning` | 기획/조정/협업 역량 | `planning.project_coordination`, `planning.stakeholder_alignment` |
| `compliance` | 규정 준수/공공성/윤리 역량 | `compliance.policy_adherence`, `compliance.public_service_mindset` |
| `digital` | 디지털 도구 활용/전환 역량 | `digital.tool_adoption`, `digital.process_improvement` |

## 3) JD 문구 -> 태그 매핑 규칙

| JD 신호 문구(예시) | 매핑 태그 |
|---|---|
| "문서 작성", "보고서", "행정 지원" | `ops.document.writing`, `ops.process.execution` |
| "민원", "고객 응대", "상담" | `customer.communication`, `customer.issue_resolution` |
| "엑셀", "통계", "데이터 분석" | `ops.ms_office.excel`, `analytics.data.interpretation` |
| "유관부서 협업", "조율", "협력" | `planning.stakeholder_alignment`, `planning.project_coordination` |
| "공공가치", "신뢰", "윤리", "규정" | `compliance.public_service_mindset`, `compliance.policy_adherence` |
| "디지털 전환", "시스템", "프로세스 개선" | `digital.process_improvement`, `digital.tool_adoption` |

## 4) 태깅 원칙

- 한 레코드당 1~5개 핵심 태그만 부여
- 명시적 요구(`explicit_requirement`) 우선 부여
- 암시적 요구는 근거 문구가 있을 때만 부여
- 조직 공통역량(예: 신뢰/소통)은 직무 맥락과 같이 등장할 때만 태깅

## 5) 품질 기준

- 태그별 근거 문구 1개 이상 필수
- `confidence < 0.65`이면 `assumptions` 필드에 이유 기록
- 월 1회 태그 드리프트 점검(신규 공고 문구 반영)
