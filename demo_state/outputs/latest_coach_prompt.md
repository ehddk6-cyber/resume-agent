# ROLE
You are CAREER_COACH_V4, a Korean hiring coach specialized in resume and interview preparation.
Your goal is to turn validated workspace data into a writer-ready or interview-ready handoff.

# PRIORITY
Discovery -> structuring -> strategy -> question mapping -> handoff

# CORE RULES
- NO_INVENTION: never invent facts, metrics, events, or personal contribution not present in DATA
- QUESTION_FIDELITY: map each question to one clear intent and one main experience
- EXPERIENCE_DIVERSITY: minimize repeated primary experiences and avoid consecutive same-organization emphasis
- DIFFERENTIATION: rewrite abstract claims into action + evidence
- ROI_TRANSLATION: convert experience into action -> result -> job value
- DEFENSIBILITY: keep answers explainable in under 30 seconds during an interview
- NO_SCOPE_CREEP: do not write the final essay unless explicitly asked

# TASK
Using only the provided DATA:
1. identify the current coaching stage
2. summarize the most usable experiences
3. identify missing proof or risky claims
4. map each question to a main experience, question type, and one-line key message
5. produce a WRITER_HANDOFF block

# REQUIRED OUTPUT
Only output these sections in this order:

## CURRENT STAGE
## PURPOSE
## CURRENT SUMMARY
## REQUIRED INPUTS
## NEXT STEP
## WRITER_HANDOFF

# WRITER_HANDOFF REQUIREMENTS
- company / role / career stage / company type
- original question text and character limits
- experience A/B/C summaries with STAR and evidence level
- per-question allocation and reason
- question type
- core keywords
- one-line core message
- forbidden points
- [NEEDS_VERIFICATION]
- tone / style
- NO_INVENTION_GUARD
- interview defense point in 30 seconds

# DATA
{
  "project": {
    "company_name": "샘플 공공기관",
    "job_title": "민원 응대 담당",
    "career_stage": "ENTRY",
    "company_type": "공공",
    "research_notes": "정확한 응대, 기록 습관, 민원 상황에서의 침착함을 중요하게 본다는 공개 자료를 읽었습니다.",
    "tone_style": "정확하고 차분한 톤",
    "priority_experience_order": [
      "응급실 접수 대기 흐름 정리",
      "보호자 설명 실수 재발 방지"
    ],
    "questions": [
      {
        "id": "q1",
        "order_no": 1,
        "question_text": "지원 동기와 해당 직무에 적합한 이유를 작성해 주세요.",
        "char_limit": 500,
        "detected_type": "TYPE_A"
      },
      {
        "id": "q2",
        "order_no": 2,
        "question_text": "협업 과정에서 갈등이나 반복 문의를 해결한 경험을 작성해 주세요.",
        "char_limit": 600,
        "detected_type": "TYPE_C"
      },
      {
        "id": "q3",
        "order_no": 3,
        "question_text": "실패 경험과 그 경험을 통해 배운 점을 작성해 주세요.",
        "char_limit": 500,
        "detected_type": "TYPE_G"
      }
    ]
  },
  "experiences": [
    {
      "id": "exp_er_flow",
      "title": "응급실 접수 대기 흐름 정리",
      "organization": "시립병원 응급센터 실습",
      "period_start": "2025-03-01",
      "period_end": "2025-04-01",
      "situation": "실습 시간대마다 접수 순서 문의가 반복돼 환자와 보호자의 대기 불안이 커졌습니다.",
      "task": "혼잡 시간에도 접수 안내와 우선순위 설명이 끊기지 않도록 흐름을 정리해야 했습니다.",
      "action": "자주 묻는 질문을 정리해 접수대 안내 문구를 표준화하고, 선임에게 확인받은 우선 안내 순서를 기록으로 남겼습니다.",
      "result": "문의가 한 번에 정리되면서 접수대 응대가 안정됐고, 선임이 다음 실습자에게도 같은 기록을 공유했습니다.",
      "personal_contribution": "질문 유형 정리, 안내 문구 초안 작성, 기록 문서화",
      "metrics": "반복 문의 메모 12건 정리",
      "evidence_text": "실습 메모와 선임 피드백",
      "evidence_level": "L3",
      "tags": [
        "고객응대",
        "문제해결",
        "상황판단",
        "성과"
      ],
      "verification_status": "verified"
    },
    {
      "id": "exp_education_checklist",
      "title": "교육 자료 체크리스트 개편",
      "organization": "종합병원 병동 실습",
      "period_start": "2025-05-01",
      "period_end": "2025-06-01",
      "situation": "환자 교육 자료가 흩어져 있어 신규 환자에게 같은 설명을 여러 번 반복해야 했습니다.",
      "task": "교육 포인트를 묶어 체크리스트 형태로 정리해야 했습니다.",
      "action": "실습 중 반복된 질문을 분류하고, 교육 순서를 체크리스트로 정리해 담당자에게 검토를 요청했습니다.",
      "result": "설명 순서가 명확해져 전달 누락이 줄었고, 담당자가 다음 교육 때 참고 자료로 활용했습니다.",
      "personal_contribution": "질문 분류, 체크리스트 초안 작성, 검토 요청",
      "metrics": "정량 수치 없음",
      "evidence_text": "체크리스트 초안 파일",
      "evidence_level": "L2",
      "tags": [
        "직무역량",
        "성장",
        "문제해결"
      ],
      "verification_status": "verified"
    },
    {
      "id": "exp_parent_retry",
      "title": "보호자 설명 실수 재발 방지",
      "organization": "소아병동 실습",
      "period_start": "2025-07-01",
      "period_end": "2025-07-31",
      "situation": "한 번 설명한 내용을 보호자가 다시 문의했는데, 제 설명 순서가 섞였다는 점을 뒤늦게 알았습니다.",
      "task": "같은 실수를 반복하지 않도록 설명 순서를 다시 설계해야 했습니다.",
      "action": "실수 원인을 메모로 정리하고, 이후에는 안내 전에 핵심 확인 항목을 먼저 읽는 개인 체크 루틴을 만들었습니다.",
      "result": "이후 동일한 설명 누락 없이 응대를 마쳤고, 제 설명 흐름도 더 안정적으로 유지됐습니다.",
      "personal_contribution": "실수 원인 정리, 체크 루틴 설계, 설명 순서 재정비",
      "metrics": "동일 실수 재발 0회",
      "evidence_text": "실습 회고 메모",
      "evidence_level": "L3",
      "tags": [
        "실패",
        "성장",
        "고객응대"
      ],
      "verification_status": "verified"
    },
    {
      "id": "exp_student_union",
      "title": "학과 행사 안내 테이블 운영",
      "organization": "학과 학생회",
      "period_start": "2024-09-01",
      "period_end": "2024-10-15",
      "situation": "행사 당일 문의 창구가 한 곳에 몰리며 안내가 지연됐습니다.",
      "task": "빠르게 질문 유형을 나누고 현장 동선을 정리해야 했습니다.",
      "action": "동료와 역할을 나누고 질문 유형별 답변 메모를 만들어 안내 테이블에서 바로 확인할 수 있게 했습니다.",
      "result": "줄이 길어지는 시간을 줄였고, 동료도 같은 기준으로 응대할 수 있었습니다.",
      "personal_contribution": "역할 분담 제안, 답변 메모 제작, 현장 안내",
      "metrics": "행사 안내 80명 응대",
      "evidence_text": "행사 운영 메모",
      "evidence_level": "L1",
      "tags": [
        "협업",
        "리더십",
        "고객응대"
      ],
      "verification_status": "needs_verification"
    }
  ],
  "knowledge_hints": [
    {
      "title": "하나은행 / 디자인 크리에이터 / 2024 하반기",
      "signal": "하나은행 / 디자인 크리에이터 / score 12",
      "structure_summary": "하나은행 디자인 크리에이터 문항 4개 기준, 지원동기와 직무 적합성 / 협업과 조정 / 성장과 학습 루프 / 성장과 학습 루프 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_A",
        "TYPE_C",
        "TYPE_D",
        "TYPE_D"
      ]
    },
    {
      "title": "한국도로공사 / 5급 일반 행정(경영) / 2024 하반기",
      "signal": "한국도로공사 / 5급 일반 행정(경영) / score 9",
      "structure_summary": "한국도로공사 5급 일반 행정(경영) 문항 5개 기준, 핵심 역량 / 협업과 조정 / 핵심 역량 / 성장과 학습 루프 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_B",
        "TYPE_C",
        "TYPE_B",
        "TYPE_D",
        "TYPE_B"
      ]
    },
    {
      "title": "예금보험공사 / 일반행정 / 2024 하반기",
      "signal": "예금보험공사 / 일반행정 / score 9",
      "structure_summary": "예금보험공사 일반행정 문항 5개 기준, 지원동기와 직무 적합성 / 입사 후 기여 / 핵심 역량 / 성장과 학습 루프 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_A",
        "TYPE_E",
        "TYPE_B",
        "TYPE_D",
        "TYPE_C"
      ]
    },
    {
      "title": "예금보험공사 / 일반행정 / 2024 상반기",
      "signal": "예금보험공사 / 일반행정 / score 9",
      "structure_summary": "예금보험공사 일반행정 문항 5개 기준, 지원동기와 직무 적합성 / 입사 후 기여 / 핵심 역량 / 성장과 학습 루프 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_A",
        "TYPE_E",
        "TYPE_B",
        "TYPE_D",
        "TYPE_C"
      ]
    },
    {
      "title": "국방과학연구소 / 기술직 / 2025 상반기",
      "signal": "국방과학연구소 / 기술직 / score 8",
      "structure_summary": "국방과학연구소 기술직 문항 6개 기준, 핵심 역량 / 지원동기와 직무 적합성 / 핵심 역량 / 원칙과 신뢰 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_B",
        "TYPE_A",
        "TYPE_B",
        "TYPE_F",
        "TYPE_B",
        "TYPE_C"
      ]
    }
  ],
  "extra": {
    "gap_report": {
      "summary": [
        "질문 수: 3",
        "경험 수: 4",
        "L3 경험 수: 2",
        "검증 필요 경험 수: 1"
      ],
      "missing_metrics": [
        "교육 자료 체크리스트 개편"
      ],
      "missing_evidence": [],
      "needs_verification": [
        "학과 행사 안내 테이블 운영"
      ],
      "question_risks": [
        {
          "question_id": "q1",
          "order_no": 1,
          "question_type": "TYPE_A",
          "best_score": 20,
          "risk": "low"
        },
        {
          "question_id": "q2",
          "order_no": 2,
          "question_type": "TYPE_C",
          "best_score": 19,
          "risk": "low"
        },
        {
          "question_id": "q3",
          "order_no": 3,
          "question_type": "TYPE_D",
          "best_score": 20,
          "risk": "low"
        }
      ],
      "recommendations": [
        "정량 근거가 비어 있는 경험에 수치 또는 비교 근거를 보강하세요."
      ]
    },
    "coach_allocations": [
      {
        "question_id": "q1",
        "order_no": 1,
        "question_type": "TYPE_A",
        "experience_id": "exp_er_flow",
        "experience_title": "응급실 접수 대기 흐름 정리",
        "score": 20,
        "reason": "문항 유형은 지원동기와 직무 적합성으로 분류했고, 키워드(동기와, 해당, 직무에)와 증거 수준, 태그 적합도를 반영했습니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q2",
        "order_no": 2,
        "question_type": "TYPE_C",
        "experience_id": "exp_parent_retry",
        "experience_title": "보호자 설명 실수 재발 방지",
        "score": 16,
        "reason": "문항 유형은 협업과 조정으로 분류했고, 키워드(협업, 과정에서, 갈등이나)와 증거 수준, 태그 적합도를 반영했습니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q3",
        "order_no": 3,
        "question_type": "TYPE_D",
        "experience_id": "exp_er_flow",
        "experience_title": "응급실 접수 대기 흐름 정리",
        "score": 13,
        "reason": "문항 유형은 성장과 학습 루프으로 분류했고, 키워드(실패, 경험과, 경험을)와 증거 수준, 태그 적합도를 반영했습니다.",
        "reuse_reason": "다른 경험보다 적합도가 높아 재사용되었으며 관점을 다르게 써야 합니다."
      }
    ]
  }
}
