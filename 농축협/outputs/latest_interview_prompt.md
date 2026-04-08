# ROLE
당신은 CAREER_INTERVIEWER_V3 (한국 취업 면접 준비 및 압박 면접 시뮬레이션 전문 모델) 이다.

목표: 제공된 [DATA] 만 사용해, 지원자의 자소서와 경험을 철저히 검증하고
예상질문, 답변 프레임, 그리고 "2~3단계 깊이의 연쇄 꼬리 질문(Recursive Follow-ups)"을 구조화한다.

# CORE RULES
## R1 DEFENSE FIRST & RECURSIVE FOLLOW-UPS
- 단순 1차 질문에서 멈추지 않는다. 지원자가 대답할 만한 내용을 예상하고, 그 논리적 허점이나 수치를 파고드는 2차, 3차 꼬리질문을 반드시 생성한다.
- 꼬리 질문은 수치 검증, 역할 비중 검증, 실패 시 대안 검증 등 다각도로 접근한다.

## R2 NO_INVENTION
- DATA 외 회사 정보, 실적, 수치, 사건, 대화, 감정 반응을 만들지 않는다.
- 모르는 정보나 수치가 비어있다면 [NEEDS_VERIFICATION] 로 날카롭게 지적한다.

## R3 30_SECOND_RULE
- 모든 답변 프레임은 30초 내외(약 150~200자)로 말할 수 있도록 간결하게 작성한다.

## R3-1 PRESSURE MODE
- DATA.extra.feedback_learning 이 있으면 최근 거절 코멘트와 취약 패턴을 우선적으로 압박 포인트에 반영한다.
- 메인 질문마다 최소 1개는 "수치 검증", 1개는 "개인 기여 검증", 1개는 "대안/반례 검증" 성격의 질문을 포함한다.

## R4 COMPANY_CONTEXT_INTEGRATION
- DATA 에 company_analysis 가 있으면 반드시 활용한다.
- interview_style (formal/casual/technical/behavioral) 에 따라 답변 톤을 조정한다.
  예: formal → 정중하고 구조화된 답변, casual → 담백하고 실행 중심 답변
- core_values 를 면접 질문의 예상 의도에 반영한다.
  예: "고객 중심" 가치를 가진 회사면 고객 관련 경험을 강조하라는 전략 제시
- company_type (대기업/중견/스타트업/공공/공기업) 에 따라 면접 스타일을 추정하고 그에 맞는 대비를 한다.
  예: 공공기관 → 공익/규정 준수/민원 대응 질문 비중 높음
- company_analysis.role_industry_strategy 가 있으면 interview_pressure_themes, banned_patterns, evidence_priority 를 우선 압박 포인트와 답변 프레임에 반영한다.
- DATA.extra.ncs_profile 이 있으면 priority_competencies 와 interview_watchouts 를 압박 포인트 설계에 반영한다.
- DATA.extra.ncs_profile.ability_units / question_alignment[].recommended_ability_units 가 있으면 능력단위 기준의 꼬리질문도 포함한다.
- DATA.extra.narrative_ssot 가 있으면 core_claims 와 answer_anchor 를 기준으로 자소서-자기소개-면접 답변의 공통 축을 유지한다.
- 면접 답변 프레임은 narrative_ssot.evidence_experience_ids 에 포함된 경험과 충돌하지 않게 설계한다.
- company_analysis.role_industry_strategy.committee_personas 가 있으면 단일 면접관이 아니라 위원회형 면접으로 간주한다.
  각 메인 질문은 서로 다른 위원이 맡는 것처럼 의도와 압박 포인트를 분리한다.
- 최소 3명의 위원을 가정한다: 위원장(논리/일관성), 실무위원(직무 적합성), 리스크위원(과장/허점 검증).
- single_source_risks 가 있으면 해당 영역은 확정 표현 대신 검증 보완 문장으로 낮춘다.
- company_analysis 가 없으면 일반적인 면접 원칙으로 진행한다.

# REQUIRED OUTPUT
오직 아래 4개의 마크다운 블록과 FINAL CHECK만 출력하라.

## 블록 1: INTERVIEW ASSUMPTIONS
- 지원자의 경험 데이터(DATA)와 작성된 자소서에서 발견된 논리적 허점, 과장된 표현, 수치 부족 등 방어해야 할 약점 3가지를 정리한다.

## 블록 2: INTERVIEW STRATEGY
- 블록 1의 약점을 방어하기 위한 핵심 전략과 절대로 면접장에서 해서는 안 될 Banned Phrases를 정의한다.

## 블록 3: EXPECTED QUESTIONS MAP
- 각 자소서 문항별로 1개의 메인 질문을 뽑고, 이에 대한 2~3단계 꼬리질문 트리(Tree)를 작성한다.
  - 각 메인 질문 앞에 담당 위원 페르소나를 명시한다.
  - 예상 질문 1: ...
    - 꼬리 질문 1-1 (검증): ...
    - 꼬리 질문 1-2 (압박): ... (1-1의 답변을 가정하고 더 깊게 파고듦)

## 블록 4: ANSWER FRAMES
각 메인 질문에 대해 두 가지 답변 프레임을 작성한다.

### 30초 답변 (핵심 요약)
- 두괄식, STAR 압축
- 핵심 주장 + 핵심 근거 1개 + 결론
- 약 150~200자

### 60~90초 답변 (확장 답변)
- 30초 답변의 핵심을 유지하되, STAR 전개를 완성
- 상황(10초) → 과제/행동(30초) → 결과/근거(20초) → 직무 연결(15초)
- 예상 반론에 대한 사전 대비 1개 포함
- 꼬리질문 후 답변 요청 시 사용
- 약 400~600자

각 답변 끝에 방어 포인트를 명시:
- "면접관이 이 부분을 추궁할 경우: [반론 대비 문장]"

## FINAL CHECK
- [ ] 꼬리 질문이 2단계 이상 깊이 있게 작성되었는가?
- [ ] 없는 사실을 지어내지 않았는가?
- [ ] 30초 답변과 60~90초 답변의 사실축이 일치하는가?
- [ ] 60~90초 답변이 꼬리질문 후에도 방어 가능한가?

# DATA
{
  "project": {
    "company_name": "농·축협",
    "job_title": "신규직원",
    "career_stage": "ENTRY",
    "company_type": "협동조합",
    "research_notes": "2026년 상반기 농·축협 신규직원 채용 자기소개서 기준. 교육지원·경제·금융의 복합 구조, 조합원 신뢰, 현장 밀착 서비스, 정직과 도덕성, 실무 개선 역량 강조.",
    "tone_style": "담백하고 근거 중심",
    "priority_experience_order": [
      "exp_nps_intern",
      "exp_seoul_covid_fraud",
      "exp_seoul_covid_conflict",
      "exp_mg_bank_parttime"
    ],
    "questions": [
      {
        "id": "q1_nh_growth",
        "order_no": 1,
        "question_text": "본인의 발전을 위해 노력했던 경험 중 성장 가능성을 가장 잘 보여주는 사례와 그것을 농협 업무에 어떻게 활용할 수 있는지 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_D"
      },
      {
        "id": "q2_nh_decision",
        "order_no": 2,
        "question_text": "판단이 쉽지 않은 상황에서 의사결정을 내렸던 경험을 구체적으로 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_I"
      },
      {
        "id": "q3_nh_trust",
        "order_no": 3,
        "question_text": "조직이나 팀에서 맡은 역할을 수행하며 동료나 구성원의 신뢰를 얻게 되었던 경험을 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_F"
      },
      {
        "id": "q4_nh_value",
        "order_no": 4,
        "question_text": "농협의 구성원으로서 본인이 중요하게 생각하는 가치나 원칙과 농협에서 수행하고 싶은 역할을 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_F"
      },
      {
        "id": "q5_nh_structure",
        "order_no": 5,
        "question_text": "농협이 교육지원·경제·금융 사업을 동시에 수행하는 구조가 가지는 경쟁력과 본인이 기여할 수 있는 부분을 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_E"
      }
    ]
  },
  "experiences": [
    {
      "id": "exp_seoul_covid_conflict",
      "title": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
      "organization": "서울시청 시민건강국 코로나19지원팀",
      "period_start": "2021-07-01",
      "period_end": "2021-12-31",
      "situation": "중수본 숙박비 지침 변경으로 급여 엑셀 수식 재설정 필요. 젊은 직원의 자동화 수식과 50대 공무원의 수동 방식 간 심각한 언쟁 발생.",
      "task": "세대 간·직무 숙련도 차이로 인한 갈등 해결 및 업무 정상화",
      "action": "기존 직원의 경험을 존중하며 새 수식의 장점과 사용법을 다회차에 걸쳐 설명. 젊은 직원에게는 공무원의 입장을 이해해달라며 양보 유도. 절충안(병행) 마련.",
      "result": "상호 사과와 함께 새 수식 도입, 업무 효율 30% 증가",
      "personal_contribution": "갈등 중재, 절충안 제시, 매뉴얼 작성",
      "metrics": "업무 효율 30% 증가",
      "evidence_text": "서울시청 파견 근무 경험",
      "evidence_level": "L3",
      "tags": [
        "갈등중재",
        "협업",
        "설득"
      ],
      "verification_status": "verified",
      "updated_at": "2026-03-27 10:00:00+09:00"
    },
    {
      "id": "exp_nps_intern",
      "title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
      "organization": "국민연금공단 강남역삼지사 연금지급부",
      "period_start": "2024-10-04",
      "period_end": "2024-12-31",
      "situation": "기초연금 수급 대상자 발굴 시 연금액 기준 단순 필터링 후 무작위 전화 방식(자산/소득 미반영). 3,000페이지 분량의 지급 결정서·추납·분납 서류를 2일 내 처리 필요.",
      "task": "방대한 서류 체계적 분류 및 실질적 수급 대상자 정확한 선별",
      "action": "서류를 카테고리별(색상 폴더)로 구분하고 시급성에 따라 우선순위 설정. VLOOKUP, TEXT, CONCATENATE 함수로 연금액·부동산 공시지가·소득을 동시에 반영하는 엑셀 자동 필터링 시스템 구축. 연락처 데이터 표준화.",
      "result": "2일 만에 3,000페이지 정리 완수. 불필요한 전화 업무 대폭 축소. 업무 속도 1주일 단축. 발굴 목표(150건) 초과 달성.",
      "personal_contribution": "엑셀 자동 필터링 시스템 설계·구축, 서류 분류 체계 수립",
      "metrics": "3,000페이지 2일 완수, 목표 150건 초과 달성",
      "evidence_text": "국민연금공단 인턴 근무 경험",
      "evidence_level": "L3",
      "tags": [
        "데이터분석",
        "엑셀자동화",
        "프로세스개선"
      ],
      "verification_status": "verified",
      "updated_at": "2026-03-27 10:00:00+09:00"
    },
    {
      "id": "exp_seoul_covid_fraud",
      "title": "서울시청 코로나19 지원팀 부정수급 적발",
      "organization": "서울시청 시민건강국 코로나19지원팀",
      "period_start": "2021-07-01",
      "period_end": "2021-12-31",
      "situation": "파견 의료인력 1,000명 급여 산정 업무 지원 중, 고시원 영수증에 한 달 숙박비를 10만원으로 계약했다는 허위 증빙 발견. 실제 시세와 290만원 차이 발생 의심.",
      "task": "숙박비 청구 건의 신뢰성을 검증하고 공적 예산 누수 방지",
      "action": "부동산 앱 검색 및 공인중개사 전화 조사로 해당 지역 고시원 시세 40~50만원 파악. 임대업자에게 직접 세입자로 위장하여 연락, 실제 시세 확인 및 허위 거래 입증. 팀장 보고 후 의료진에게 숙박비 미지급 통보.",
      "result": "부정수급 20건 적발, 관련 예산 최소 40% 절감",
      "personal_contribution": "데이터 검증 프로세스 설계, 부동산 시세 교차 조사, 허위 거래 입증",
      "metrics": "부정수급 20건 적발, 예산 40% 절감",
      "evidence_text": "서울시청 파견 근무 경험",
      "evidence_level": "L3",
      "tags": [
        "데이터검증",
        "청렴성",
        "예산절감"
      ],
      "verification_status": "verified",
      "updated_at": "2026-03-27 10:00:00+09:00"
    },
    {
      "id": "exp_seoul_covid_crisis",
      "title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
      "organization": "서울시청 시민건강국 코로나19지원팀",
      "period_start": "2021-07-01",
      "period_end": "2021-12-31",
      "situation": "담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주.",
      "task": "실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련",
      "action": "중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결.",
      "result": "당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화",
      "personal_contribution": "공문 분석, 매뉴얼 자체 제작·배포, 민원 응대",
      "metrics": "수백 통 민원 당일 수습",
      "evidence_text": "서울시청 파견 근무 경험",
      "evidence_level": "L3",
      "tags": [
        "위기대응",
        "책임감",
        "매뉴얼제작",
        "순발력"
      ],
      "verification_status": "verified",
      "updated_at": "2026-03-27 10:00:00+09:00"
    },
    {
      "id": "exp_mg_bank_parttime",
      "title": "새마을금고 아르바이트 - 디지털 취약 고객 응대",
      "organization": "새마을금고",
      "period_start": "2023-01-01",
      "period_end": "2023-12-31",
      "situation": "90세 시각·청각 장애 고객이 디지털 태블릿 서명 절차에 어려움과 불안감을 느끼는 상황이 발생함.",
      "task": "디지털 취약 계층 고객이 불편 없이 서명을 완료하도록 돕고 금융기관에 대한 불안을 낮추기",
      "action": "스몰토크로 긴장을 완화하고, 큰 목소리와 또박또박한 발음으로 설명하며, 직접 행동을 유도해 절차를 눈높이에 맞춰 안내함.",
      "result": "고객이 불안감 없이 서명을 완료했고, 디지털 취약 계층을 응대하는 실무 노하우를 축적함.",
      "personal_contribution": "고객 상황에 맞춘 설명 방식 조정, 접근성 중심 응대, 절차 완료 지원",
      "metrics": "디지털 취약 계층 응대 성공",
      "evidence_text": "새마을금고 아르바이트 경험",
      "evidence_level": "L2",
      "tags": [
        "고객응대",
        "접근성",
        "소통",
        "신뢰형성"
      ],
      "verification_status": "verified",
      "updated_at": "2026-04-05 16:00:00+09:00"
    }
  ],
  "knowledge_hints": [
    {
      "title": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / 2024 하반기",
      "company_name": "한국보훈복지의료공단",
      "job_title": "[5급] 경영,경제,회계",
      "signal": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / TF-IDF score 0.273",
      "structure_summary": "한국보훈복지의료공단 [5급] 경영,경제,회계 문항 5개 기준, 협업과 조정 / 상황판단과 우선순위 / 협업과 조정 / 핵심 역량 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_C",
        "TYPE_I",
        "TYPE_C",
        "TYPE_B",
        "TYPE_I"
      ],
      "applicable_question_types": [
        "TYPE_C",
        "TYPE_I",
        "TYPE_C",
        "TYPE_B",
        "TYPE_I"
      ],
      "evidence_focus": [
        "STAR 구조",
        "정량 결과",
        "문제 해결",
        "협업"
      ],
      "structure_signals": {
        "has_star": true,
        "has_metrics": true,
        "warns_against_copying": true
      },
      "match_reasons": [
        "정량 결과 포함"
      ],
      "semantic_score": 0.0,
      "vector_score": 0.0,
      "combined_score": 0.273
    },
    {
      "title": "한국신용정보원 / 일반 / 2025 상반기",
      "company_name": "한국신용정보원",
      "job_title": "일반",
      "signal": "한국신용정보원 / 일반 / TF-IDF score 0.215",
      "structure_summary": "한국신용정보원 일반 문항 9개 기준, 입사 후 기여 / 고객응대 / 고객응대 / 원칙과 신뢰 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_E",
        "TYPE_H",
        "TYPE_H",
        "TYPE_F",
        "TYPE_H",
        "TYPE_B"
      ],
      "applicable_question_types": [
        "TYPE_E",
        "TYPE_H",
        "TYPE_H",
        "TYPE_F",
        "TYPE_H",
        "TYPE_B"
      ],
      "evidence_focus": [
        "STAR 구조",
        "정량 결과",
        "문제 해결",
        "협업"
      ],
      "structure_signals": {
        "has_star": true,
        "has_metrics": true,
        "warns_against_copying": true
      },
      "match_reasons": [
        "정량 결과 포함"
      ],
      "semantic_score": 0.0,
      "vector_score": 0.0,
      "combined_score": 0.215
    },
    {
      "title": "한국산업단지공단 / 경영·경제(일반_4급) / 2024 하반기",
      "company_name": "한국산업단지공단",
      "job_title": "경영·경제(일반_4급)",
      "signal": "한국산업단지공단 / 경영·경제(일반_4급) / TF-IDF score 0.186",
      "structure_summary": "한국산업단지공단 경영·경제(일반_4급) 문항 6개 기준, 핵심 역량 / 협업과 조정 / 핵심 역량 / 핵심 역량 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_B",
        "TYPE_C",
        "TYPE_B",
        "TYPE_B",
        "TYPE_E",
        "TYPE_C"
      ],
      "applicable_question_types": [
        "TYPE_B",
        "TYPE_C",
        "TYPE_B",
        "TYPE_B",
        "TYPE_E",
        "TYPE_C"
      ],
      "evidence_focus": [
        "STAR 구조",
        "정량 결과",
        "문제 해결",
        "협업"
      ],
      "structure_signals": {
        "has_star": true,
        "has_metrics": true,
        "warns_against_copying": true
      },
      "match_reasons": [
        "정량 결과 포함"
      ],
      "semantic_score": 0.0,
      "vector_score": 0.0,
      "combined_score": 0.186
    },
    {
      "title": "대한적십자사 / 일반사무 / 2025 상반기",
      "company_name": "대한적십자사",
      "job_title": "일반사무",
      "signal": "대한적십자사 / 일반사무 / TF-IDF score 0.183",
      "structure_summary": "대한적십자사 일반사무 문항 4개 기준, 입사 후 기여 / 핵심 역량 / 성장과 학습 루프 / 원칙과 신뢰 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_E",
        "TYPE_B",
        "TYPE_D",
        "TYPE_F"
      ],
      "applicable_question_types": [
        "TYPE_E",
        "TYPE_B",
        "TYPE_D",
        "TYPE_F"
      ],
      "evidence_focus": [
        "STAR 구조",
        "정량 결과",
        "문제 해결",
        "협업"
      ],
      "structure_signals": {
        "has_star": true,
        "has_metrics": true,
        "warns_against_copying": true
      },
      "match_reasons": [
        "정량 결과 포함"
      ],
      "semantic_score": 0.0,
      "vector_score": 0.0,
      "combined_score": 0.183
    },
    {
      "title": "경기도의료원 / 행정직 / 2024 하반기",
      "company_name": "경기도의료원",
      "job_title": "행정직",
      "signal": "경기도의료원 / 행정직 / TF-IDF score 0.126",
      "structure_summary": "경기도의료원 행정직 문항 6개 기준, 핵심 역량 / 원칙과 신뢰 / 실패와 복기 / 협업과 조정 중심 구조",
      "caution": "표현 복제 금지. 구조만 참고.",
      "question_types": [
        "TYPE_B",
        "TYPE_F",
        "TYPE_G",
        "TYPE_C",
        "TYPE_F",
        "TYPE_I"
      ],
      "applicable_question_types": [
        "TYPE_B",
        "TYPE_F",
        "TYPE_G",
        "TYPE_C",
        "TYPE_F",
        "TYPE_I"
      ],
      "evidence_focus": [
        "STAR 구조",
        "정량 결과",
        "문제 해결",
        "성장 서사"
      ],
      "structure_signals": {
        "has_star": true,
        "has_metrics": false,
        "warns_against_copying": true
      },
      "match_reasons": [],
      "semantic_score": 0.0,
      "vector_score": 0.0,
      "combined_score": 0.126
    }
  ],
  "extra": {
    "question_map": [
      {
        "question_id": "q1_nh_growth",
        "order_no": 1,
        "question_type": "TYPE_D",
        "experience_id": "exp_seoul_covid_conflict",
        "experience_title": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
        "score": 15,
        "reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(본인의, 발전을, 위해)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(업무 효율 30% 증가) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q2_nh_decision",
        "order_no": 2,
        "question_type": "TYPE_I",
        "experience_id": "exp_nps_intern",
        "experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
        "score": 13,
        "reason": "질문 기대: 상황판단과 우선순위 문항이며, 질문 키워드(판단이, 쉽지, 않은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q3_nh_trust",
        "order_no": 3,
        "question_type": "TYPE_F",
        "experience_id": "exp_seoul_covid_fraud",
        "experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
        "score": 13,
        "reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(조직이나, 팀에서, 맡은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q4_nh_value",
        "order_no": 4,
        "question_type": "TYPE_F",
        "experience_id": "exp_seoul_covid_crisis",
        "experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
        "score": 9,
        "reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(농협의, 구성원으로서, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q5_nh_structure",
        "order_no": 5,
        "question_type": "TYPE_E",
        "experience_id": "exp_mg_bank_parttime",
        "experience_title": "새마을금고 아르바이트 - 디지털 취약 고객 응대",
        "score": 11,
        "reason": "질문 기대: 입사 후 기여 문항이며, 질문 키워드(농협이, 교육지원, 경제)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(디지털 취약 계층 응대 성공) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      }
    ],
    "writer_artifact": "",
    "writer_quality": [],
    "interview_defense": [],
    "feedback_learning": {
      "artifact": "interview",
      "total_feedback": 2,
      "recent_rejection_comments": [],
      "top_patterns": [],
      "recommended_pattern": "interview|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
      "current_pattern": "interview|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
      "question_experience_map": [
        {
          "question_id": "q1_nh_growth",
          "question_type": "TYPE_D",
          "experience_id": "exp_seoul_covid_conflict",
          "question_order": 1
        },
        {
          "question_id": "q2_nh_decision",
          "question_type": "TYPE_I",
          "experience_id": "exp_nps_intern",
          "question_order": 2
        },
        {
          "question_id": "q3_nh_trust",
          "question_type": "TYPE_F",
          "experience_id": "exp_seoul_covid_fraud",
          "question_order": 3
        },
        {
          "question_id": "q4_nh_value",
          "question_type": "TYPE_F",
          "experience_id": "exp_seoul_covid_crisis",
          "question_order": 4
        },
        {
          "question_id": "q5_nh_structure",
          "question_type": "TYPE_E",
          "experience_id": "exp_mg_bank_parttime",
          "question_order": 5
        }
      ],
      "question_strategy_map": [
        {
          "question_id": "q1_nh_growth",
          "question_order": 1,
          "question_type": "QuestionType.TYPE_D",
          "experience_id": "exp_seoul_covid_conflict",
          "core_message": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재 경험으로 QuestionType.TYPE_D 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_D 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 대인관계능력를 검증 가능하게 보여주는 사람"
        },
        {
          "question_id": "q2_nh_decision",
          "question_order": 2,
          "question_type": "QuestionType.TYPE_I",
          "experience_id": "exp_nps_intern",
          "core_message": "국민연금공단 기초연금 수급 대상자 발굴 자동화 경험으로 QuestionType.TYPE_I 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_I 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 국민연금공단 기초연금 수급 대상자 발굴 자동화의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 대인관계능력를 검증 가능하게 보여주는 사람"
        },
        {
          "question_id": "q3_nh_trust",
          "question_order": 3,
          "question_type": "QuestionType.TYPE_F",
          "experience_id": "exp_seoul_covid_fraud",
          "core_message": "서울시청 코로나19 지원팀 부정수급 적발 경험으로 QuestionType.TYPE_F 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_F 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 부정수급 적발의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 대인관계능력를 검증 가능하게 보여주는 사람"
        },
        {
          "question_id": "q4_nh_value",
          "question_order": 4,
          "question_type": "QuestionType.TYPE_F",
          "experience_id": "exp_seoul_covid_crisis",
          "core_message": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습 경험으로 QuestionType.TYPE_F 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_F 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 대인관계능력를 검증 가능하게 보여주는 사람"
        },
        {
          "question_id": "q5_nh_structure",
          "question_order": 5,
          "question_type": "QuestionType.TYPE_E",
          "experience_id": "exp_mg_bank_parttime",
          "core_message": "새마을금고 아르바이트 - 디지털 취약 고객 응대 경험으로 QuestionType.TYPE_E 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_E 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 새마을금고 아르바이트 - 디지털 취약 고객 응대의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 대인관계능력를 검증 가능하게 보여주는 사람"
        }
      ],
      "overall_success_rate": 0.0,
      "similar_context": {
        "artifact_type": "interview",
        "artifact": "interview",
        "stage": "interview",
        "company_name": "농·축협",
        "job_title": "신규직원",
        "company_type": "협동조합",
        "question_types": [
          "TYPE_D",
          "TYPE_I",
          "TYPE_F",
          "TYPE_F",
          "TYPE_E"
        ]
      },
      "recent_rejection_reasons": [],
      "outcome_summary": {
        "matched_feedback_count": 2,
        "outcome_breakdown": {
          "unknown": 2
        },
        "top_rejection_reasons": []
      },
      "strategy_outcome_summary": {
        "matched_feedback_count": 2,
        "learned_outcome_weights": {
          "offer": 4.0,
          "final_pass": 3.0,
          "pass": 3.0,
          "interview_pass": 2.0,
          "document_pass": 2.0,
          "fail_interview": 3.0,
          "interview_fail": 3.0,
          "document_fail": 1.0,
          "reject": 2.0,
          "rejected": 3.0
        },
        "experience_stats_by_question_type": {
          "TYPE_D": {
            "exp_seoul_covid_budget": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I": {
                  "total_uses": 2,
                  "pass_count": 0,
                  "fail_count": 2,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 6.0,
                  "weighted_net_score": -6,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            }
          },
          "TYPE_I": {
            "exp_nps_income_adjustment": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I": {
                  "total_uses": 2,
                  "pass_count": 0,
                  "fail_count": 2,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 6.0,
                  "weighted_net_score": -6,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            }
          },
          "TYPE_F": {
            "exp_seoul_covid_conflict": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I": {
                  "total_uses": 2,
                  "pass_count": 0,
                  "fail_count": 2,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 6.0,
                  "weighted_net_score": -6,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            },
            "exp_nps_intern": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I": {
                  "total_uses": 2,
                  "pass_count": 0,
                  "fail_count": 2,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 6.0,
                  "weighted_net_score": -6,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            }
          },
          "TYPE_E": {
            "exp_seoul_covid_fraud": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I": {
                  "total_uses": 2,
                  "pass_count": 0,
                  "fail_count": 2,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 6.0,
                  "weighted_net_score": -6,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            }
          }
        },
        "strategy_stats_by_question_type": {
          "QuestionType.TYPE_D": {
            "QuestionType.TYPE_D 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_I": {
            "QuestionType.TYPE_I 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_F": {
            "QuestionType.TYPE_F 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.": {
              "total_uses": 4,
              "pass_count": 0,
              "fail_count": 4,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 12.0,
              "weighted_net_score": -12,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_E": {
            "QuestionType.TYPE_E 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 6.0,
              "weighted_net_score": -6,
              "pass_rate": 0.0
            }
          }
        },
        "differentiation_stats_by_question_type": {
          "QuestionType.TYPE_D": {
            "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_I": {
            "평균 지원자처럼 열정만 말하지 않고 국민연금공단 기준소득월액 변경 특례 민원 응대의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_F": {
            "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "pass_rate": 0.0
            },
            "평균 지원자처럼 열정만 말하지 않고 국민연금공단 기초연금 수급 대상자 발굴 자동화의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_E": {
            "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 부정수급 적발의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 2,
              "pass_count": 0,
              "fail_count": 2,
              "pass_rate": 0.0
            }
          }
        },
        "tone_stats_by_company_type": {
          "협동조합": {
            "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람": {
              "total_uses": 10,
              "pass_count": 0,
              "fail_count": 10,
              "pass_rate": 0.0
            }
          }
        }
      },
      "insights": {
        "total_feedback": 2,
        "overall_success_rate": 0.0,
        "average_rating": 0,
        "top_patterns": [
          {
            "pattern_id": "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
            "success_rate": 0.0,
            "uses": 2
          }
        ],
        "improvement_areas": []
      },
      "adaptation_plan": {
        "recommended_pattern": "interview|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
        "focus_actions": [
          "TYPE_D 문항은 경험 선택 재검토",
          "TYPE_I 문항은 경험 선택 재검토"
        ],
        "risky_question_types": [
          {
            "question_type": "TYPE_D",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_budget",
                "pass_rate": 0.0,
                "weighted_net_score": -6,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_I",
            "weak_experiences": [
              {
                "experience_id": "exp_nps_income_adjustment",
                "pass_rate": 0.0,
                "weighted_net_score": -6,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_F",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_conflict",
                "pass_rate": 0.0,
                "weighted_net_score": -6,
                "top_rejection_reasons": []
              },
              {
                "experience_id": "exp_nps_intern",
                "pass_rate": 0.0,
                "weighted_net_score": -6,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_E",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_fraud",
                "pass_rate": 0.0,
                "weighted_net_score": -6,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          }
        ],
        "matched_feedback_count": 2
      }
    },
    "committee_feedback": {
      "session_count": 0,
      "latest_session_mode": "",
      "latest_turn_count": 0,
      "latest_committee_verdict": "",
      "recurring_risks": [],
      "persona_panel": []
    },
    "ncs_profile": {
      "framework_name": "NCS 직업공통능력",
      "reference_date": "2026-03-30",
      "reference_source": "https://www.ncs.go.kr/web/job/contents/1.%20%EC%A7%81%EC%97%85%EA%B3%B5%ED%86%B5%EB%8A%A5%EB%A0%A5_%EC%9D%98%EC%82%AC%EC%86%8C%ED%86%B5%EB%8A%A5%EB%A0%A5.pdf",
      "priority_competencies": [
        "기술능력",
        "대인관계능력",
        "의사소통능력",
        "수리능력",
        "문제해결능력"
      ],
      "job_spec_source_titles": [
        "부산교통공사 / 일반직9급_운영직(행정학)_장애인 / 2024 상반기",
        "한국토지주택공사 / (사무)_일반 / 2024 상반기",
        "한국건강증진개발원 / 청년인턴 (건강증진사업 &행정 업무지원) / 2023 하반기",
        "한국토지주택공사 / 기술직 / 2023 상반기",
        "한국토지주택공사 / 인천권(사무)일반 / 2023 상반기"
      ],
      "ability_units": [],
      "ability_unit_elements": [
        "조직이나 단체 생활 중 다른 구성원들과 원활한 정보 공유나 소통이 이루어지지 않아 어려움을 겪었던 경험을 소개해 주십시오. 당시 구성원과의 의사소통에 있어 보다 긍정적인 변화를 이끌기 위해 어떤 노력을 기울였는지",
        "그리고 그 결과는 어땠는지 기술해 주십시오.",
        "활동 혹은 업무 수행 중 예상치 못한 문제나 어려움에 직면하였으나",
        "이를 슬기롭게 극복했던 경험을 소개해 주십시오. 당시 상황은 어땠으며",
        "문제 상황을 해결하기 위해 귀하가 취한 행동과 그렇게 행동한 이유"
      ],
      "job_spec_competencies": [
        "중 자신있는 능력(영역)과 자신없는 능력(영역)을 선정하고 각 해당 능력에 대한 경험을 작성해주세요. (700자)",
        "저는 고객서비스능력에 가장 자신있습니다. 우체국 근로 당시 고객 대기시간을 20%단축한 경험이 있습니다. 설 연휴기간에 방문객이 급증했습니다. 방문객들의 많은 요구사항을 신속 정확하게 처리하기 위해 노력했습니다. 정중한 태도로 문제를 파악하기 위해 경청하였고 문제 해결을 위한 꼭 필요한 질문만 하여 빠르게 정보를 얻었습니다. 고객들의 요구사항에 최대한 경청하며 잘못된 문제점에 대한 빠른 인정과 신속한 시정을 하여 문제 해결을 진행했습니다. 또 도움이 필요해 보이는 상황에서 먼저 다가가 고객 서비스를 제공하며 대인관계능력을 향상시켰습니다. 빠른 일처리로 담당 업무를 끝내면 우편뿐만 아니라 다양한 업무에서 능동적인 업무 태도를 가지기 위해 노력하였고 익숙하지 않은 업무에 도전하면서 새로운 기술과 지식을 습득하였습니다. 그 결과 상황에 따라 유연하게 업무를 처리함으로써 더 유용한 구성원이 될 수 있었습니다. 적극적이고 신속한 서비스 대응에 저는 고객들로부터 좋은 평가를 받을 수 있었습니다.학창시절 영어공부에 흥미가 없었던 저는 지금도 꾸준히 공부하고 있지만 아직 만족스러운 점수를 얻지 못하고 있습니다. 그러나 기초외국어능력은 꼭 필요한 항목이고 추후 역량을 인정받기 위해서 매우 중요하기 때문에 더욱더 노력하고 있고 충분히 해결 가능한 영역이라고 생각합니다. 앞으로 언어능력을 향상시켜 국제적인 업무에 대비력을 갖춤으로써 다양한 역할을 수행할 수 있는 행정직으로서 성장하고자합니다.",
        "의사소통) 과업 중 상대방의 의견과 다른 의견을 제시해야 했던 경험을 아래의 순서에 따라 기술해 주십시오.",
        "① 당시 상황 기술(과업 상황",
        "상대방의 의견",
        "본인의 의견)",
        "② 본인의 의견을 전달하기 전에 확인하거나 준비한 부분 기술",
        "③ 본인의 의견을 전달한 방법과 그 방법을 사용한 이유 기술",
        "학과 동아리 조장 역할을 맡았을 당시",
        "부조장과 계획 진행에 있어 추구하는 방향이 달라 갈등이 있었습니다. 이에 저는 감정적인 상황에서 벗어나",
        "상황을 객관적으로 분석했습니다. 당시 저는 팀원 전체의 단체활동을 추구했고",
        "부조장은 그러면 인원 통제가 힘들다는 의견을 가지고 있었습니다."
      ],
      "ability_unit_map": [],
      "competency_evidence_map": [
        {
          "name": "기술능력",
          "score": 29,
          "matched_keywords": [
            "직무기술서",
            "저는 고객서비스능력에 가장 자신있습니다. 우체국 근로 당시 고객 대기시간을 20%단축한 경험이 있습니다. 설 연휴기간에 방문객이 급증했습니다. 방문객들의 많은 요구사항을 신속 정확하게 처리하기 위해 노력했습니다. 정중한 태도로 문제를 파악하기 위해 경청하였고 문제 해결을 위한 꼭 필요한 질문만 하여 빠르게 정보를 얻었습니다. 고객들의 요구사항에 최대한 경청하며 잘못된 문제점에 대한 빠른 인정과 신속한 시정을 하여 문제 해결을 진행했습니다. 또 도움이 필요해 보이는 상황에서 먼저 다가가 고객 서비스를 제공하며 대인관계능력을 향상시켰습니다. 빠른 일처리로 담당 업무를 끝내면 우편뿐만 아니라 다양한 업무에서 능동적인 업무 태도를 가지기 위해 노력하였고 익숙하지 않은 업무에 도전하면서 새로운 기술과 지식을 습득하였습니다. 그 결과 상황에 따라 유연하게 업무를 처리함으로써 더 유용한 구성원이 될 수 있었습니다. 적극적이고 신속한 서비스 대응에 저는 고객들로부터 좋은 평가를 받을 수 있었습니다.학창시절 영어공부에 흥미가 없었던 저는 지금도 꾸준히 공부하고 있지만 아직 만족스러운 점수를 얻지 못하고 있습니다. 그러나 기초외국어능력은 꼭 필요한 항목이고 추후 역량을 인정받기 위해서 매우 중요하기 때문에 더욱더 노력하고 있고 충분히 해결 가능한 영역이라고 생각합니다. 앞으로 언어능력을 향상시켜 국제적인 업무에 대비력을 갖춤으로써 다양한 역할을 수행할 수 있는 행정직으로서 성장하고자합니다.",
            "의사소통) 과업 중 상대방의 의견과 다른 의견을 제시해야 했던 경험을 아래의 순서에 따라 기술해 주십시오.",
            "① 당시 상황 기술(과업 상황",
            "② 본인의 의견을 전달하기 전에 확인하거나 준비한 부분 기술"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_budget",
            "exp_nps_intern",
            "exp_library",
            "exp_banpo_event"
          ],
          "reasons": [
            "직무기술서/NCS 명시 역량과 직접 연결",
            "직무기술서 능력단위/요소와 정합",
            "TYPE_E 문항 의도와 직접 연결"
          ]
        },
        {
          "name": "대인관계능력",
          "score": 23,
          "matched_keywords": [
            "저는 고객서비스능력에 가장 자신있습니다. 우체국 근로 당시 고객 대기시간을 20%단축한 경험이 있습니다. 설 연휴기간에 방문객이 급증했습니다. 방문객들의 많은 요구사항을 신속 정확하게 처리하기 위해 노력했습니다. 정중한 태도로 문제를 파악하기 위해 경청하였고 문제 해결을 위한 꼭 필요한 질문만 하여 빠르게 정보를 얻었습니다. 고객들의 요구사항에 최대한 경청하며 잘못된 문제점에 대한 빠른 인정과 신속한 시정을 하여 문제 해결을 진행했습니다. 또 도움이 필요해 보이는 상황에서 먼저 다가가 고객 서비스를 제공하며 대인관계능력을 향상시켰습니다. 빠른 일처리로 담당 업무를 끝내면 우편뿐만 아니라 다양한 업무에서 능동적인 업무 태도를 가지기 위해 노력하였고 익숙하지 않은 업무에 도전하면서 새로운 기술과 지식을 습득하였습니다. 그 결과 상황에 따라 유연하게 업무를 처리함으로써 더 유용한 구성원이 될 수 있었습니다. 적극적이고 신속한 서비스 대응에 저는 고객들로부터 좋은 평가를 받을 수 있었습니다.학창시절 영어공부에 흥미가 없었던 저는 지금도 꾸준히 공부하고 있지만 아직 만족스러운 점수를 얻지 못하고 있습니다. 그러나 기초외국어능력은 꼭 필요한 항목이고 추후 역량을 인정받기 위해서 매우 중요하기 때문에 더욱더 노력하고 있고 충분히 해결 가능한 영역이라고 생각합니다. 앞으로 언어능력을 향상시켜 국제적인 업무에 대비력을 갖춤으로써 다양한 역할을 수행할 수 있는 행정직으로서 성장하고자합니다.",
            "부조장과 계획 진행에 있어 추구하는 방향이 달라 갈등이 있었습니다. 이에 저는 감정적인 상황에서 벗어나",
            "상황을 객관적으로 분석했습니다. 당시 저는 팀원 전체의 단체활동을 추구했고",
            "팀",
            "설득"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_fraud",
            "exp_seoul_covid_crisis",
            "exp_seoul_covid_budget",
            "exp_seoul_covid_conflict"
          ],
          "reasons": [
            "직무기술서/NCS 명시 역량과 직접 연결"
          ]
        },
        {
          "name": "의사소통능력",
          "score": 23,
          "matched_keywords": [
            "저는 고객서비스능력에 가장 자신있습니다. 우체국 근로 당시 고객 대기시간을 20%단축한 경험이 있습니다. 설 연휴기간에 방문객이 급증했습니다. 방문객들의 많은 요구사항을 신속 정확하게 처리하기 위해 노력했습니다. 정중한 태도로 문제를 파악하기 위해 경청하였고 문제 해결을 위한 꼭 필요한 질문만 하여 빠르게 정보를 얻었습니다. 고객들의 요구사항에 최대한 경청하며 잘못된 문제점에 대한 빠른 인정과 신속한 시정을 하여 문제 해결을 진행했습니다. 또 도움이 필요해 보이는 상황에서 먼저 다가가 고객 서비스를 제공하며 대인관계능력을 향상시켰습니다. 빠른 일처리로 담당 업무를 끝내면 우편뿐만 아니라 다양한 업무에서 능동적인 업무 태도를 가지기 위해 노력하였고 익숙하지 않은 업무에 도전하면서 새로운 기술과 지식을 습득하였습니다. 그 결과 상황에 따라 유연하게 업무를 처리함으로써 더 유용한 구성원이 될 수 있었습니다. 적극적이고 신속한 서비스 대응에 저는 고객들로부터 좋은 평가를 받을 수 있었습니다.학창시절 영어공부에 흥미가 없었던 저는 지금도 꾸준히 공부하고 있지만 아직 만족스러운 점수를 얻지 못하고 있습니다. 그러나 기초외국어능력은 꼭 필요한 항목이고 추후 역량을 인정받기 위해서 매우 중요하기 때문에 더욱더 노력하고 있고 충분히 해결 가능한 영역이라고 생각합니다. 앞으로 언어능력을 향상시켜 국제적인 업무에 대비력을 갖춤으로써 다양한 역할을 수행할 수 있는 행정직으로서 성장하고자합니다.",
            "의사소통) 과업 중 상대방의 의견과 다른 의견을 제시해야 했던 경험을 아래의 순서에 따라 기술해 주십시오.",
            "조직이나 단체 생활 중 다른 구성원들과 원활한 정보 공유나 소통이 이루어지지 않아 어려움을 겪었던 경험을 소개해 주십시오. 당시 구성원과의 의사소통에 있어 보다 긍정적인 변화를 이끌기 위해 어떤 노력을 기울였는지",
            "보고",
            "민원"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_fraud",
            "exp_seoul_covid_crisis",
            "exp_seoul_covid_budget",
            "exp_seoul_covid_conflict"
          ],
          "reasons": [
            "직무기술서/NCS 명시 역량과 직접 연결",
            "직무기술서 능력단위/요소와 정합"
          ]
        },
        {
          "name": "수리능력",
          "score": 19,
          "matched_keywords": [
            "상황을 객관적으로 분석했습니다. 당시 저는 팀원 전체의 단체활동을 추구했고",
            "검증",
            "분석",
            "엑셀",
            "정산"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_fraud",
            "exp_seoul_covid_crisis",
            "exp_seoul_covid_budget",
            "exp_seoul_covid_conflict"
          ],
          "reasons": [
            "직무기술서/NCS 명시 역량과 직접 연결"
          ]
        },
        {
          "name": "문제해결능력",
          "score": 18,
          "matched_keywords": [
            "저는 고객서비스능력에 가장 자신있습니다. 우체국 근로 당시 고객 대기시간을 20%단축한 경험이 있습니다. 설 연휴기간에 방문객이 급증했습니다. 방문객들의 많은 요구사항을 신속 정확하게 처리하기 위해 노력했습니다. 정중한 태도로 문제를 파악하기 위해 경청하였고 문제 해결을 위한 꼭 필요한 질문만 하여 빠르게 정보를 얻었습니다. 고객들의 요구사항에 최대한 경청하며 잘못된 문제점에 대한 빠른 인정과 신속한 시정을 하여 문제 해결을 진행했습니다. 또 도움이 필요해 보이는 상황에서 먼저 다가가 고객 서비스를 제공하며 대인관계능력을 향상시켰습니다. 빠른 일처리로 담당 업무를 끝내면 우편뿐만 아니라 다양한 업무에서 능동적인 업무 태도를 가지기 위해 노력하였고 익숙하지 않은 업무에 도전하면서 새로운 기술과 지식을 습득하였습니다. 그 결과 상황에 따라 유연하게 업무를 처리함으로써 더 유용한 구성원이 될 수 있었습니다. 적극적이고 신속한 서비스 대응에 저는 고객들로부터 좋은 평가를 받을 수 있었습니다.학창시절 영어공부에 흥미가 없었던 저는 지금도 꾸준히 공부하고 있지만 아직 만족스러운 점수를 얻지 못하고 있습니다. 그러나 기초외국어능력은 꼭 필요한 항목이고 추후 역량을 인정받기 위해서 매우 중요하기 때문에 더욱더 노력하고 있고 충분히 해결 가능한 영역이라고 생각합니다. 앞으로 언어능력을 향상시켜 국제적인 업무에 대비력을 갖춤으로써 다양한 역할을 수행할 수 있는 행정직으로서 성장하고자합니다.",
            "활동 혹은 업무 수행 중 예상치 못한 문제나 어려움에 직면하였으나",
            "문제 상황을 해결하기 위해 귀하가 취한 행동과 그렇게 행동한 이유",
            "위기",
            "대응"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_crisis",
            "exp_seoul_covid_budget",
            "exp_seoul_covid_conflict",
            "exp_nps_intern"
          ],
          "reasons": [
            "직무기술서/NCS 명시 역량과 직접 연결",
            "직무기술서 능력단위/요소와 정합",
            "TYPE_I 문항 의도와 직접 연결"
          ]
        },
        {
          "name": "직업윤리",
          "score": 18,
          "matched_keywords": [
            "저는 고객서비스능력에 가장 자신있습니다. 우체국 근로 당시 고객 대기시간을 20%단축한 경험이 있습니다. 설 연휴기간에 방문객이 급증했습니다. 방문객들의 많은 요구사항을 신속 정확하게 처리하기 위해 노력했습니다. 정중한 태도로 문제를 파악하기 위해 경청하였고 문제 해결을 위한 꼭 필요한 질문만 하여 빠르게 정보를 얻었습니다. 고객들의 요구사항에 최대한 경청하며 잘못된 문제점에 대한 빠른 인정과 신속한 시정을 하여 문제 해결을 진행했습니다. 또 도움이 필요해 보이는 상황에서 먼저 다가가 고객 서비스를 제공하며 대인관계능력을 향상시켰습니다. 빠른 일처리로 담당 업무를 끝내면 우편뿐만 아니라 다양한 업무에서 능동적인 업무 태도를 가지기 위해 노력하였고 익숙하지 않은 업무에 도전하면서 새로운 기술과 지식을 습득하였습니다. 그 결과 상황에 따라 유연하게 업무를 처리함으로써 더 유용한 구성원이 될 수 있었습니다. 적극적이고 신속한 서비스 대응에 저는 고객들로부터 좋은 평가를 받을 수 있었습니다.학창시절 영어공부에 흥미가 없었던 저는 지금도 꾸준히 공부하고 있지만 아직 만족스러운 점수를 얻지 못하고 있습니다. 그러나 기초외국어능력은 꼭 필요한 항목이고 추후 역량을 인정받기 위해서 매우 중요하기 때문에 더욱더 노력하고 있고 충분히 해결 가능한 영역이라고 생각합니다. 앞으로 언어능력을 향상시켜 국제적인 업무에 대비력을 갖춤으로써 다양한 역할을 수행할 수 있는 행정직으로서 성장하고자합니다.",
            "청렴",
            "신뢰",
            "책임",
            "정확"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_fraud",
            "exp_seoul_covid_crisis",
            "exp_nps_intern",
            "exp_nps_income_adjustment"
          ],
          "reasons": [
            "직무기술서/NCS 명시 역량과 직접 연결",
            "TYPE_I 문항 의도와 직접 연결",
            "TYPE_F 문항 의도와 직접 연결"
          ]
        },
        {
          "name": "디지털능력",
          "score": 17,
          "matched_keywords": [
            "데이터",
            "엑셀",
            "시스템",
            "자동화",
            "디지털"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_fraud",
            "exp_seoul_covid_budget",
            "exp_seoul_covid_conflict",
            "exp_nps_intern"
          ],
          "reasons": [
            "TYPE_E 문항 의도와 직접 연결"
          ]
        }
      ],
      "question_alignment": [
        {
          "question_id": "q1_nh_growth",
          "question_type": "TYPE_D",
          "recommended_competencies": [
            "정보능력",
            "자기관리능력"
          ],
          "recommended_ability_units": []
        },
        {
          "question_id": "q2_nh_decision",
          "question_type": "TYPE_I",
          "recommended_competencies": [
            "문제해결능력",
            "직업윤리"
          ],
          "recommended_ability_units": []
        },
        {
          "question_id": "q3_nh_trust",
          "question_type": "TYPE_F",
          "recommended_competencies": [
            "직업윤리",
            "조직이해능력",
            "자기관리능력"
          ],
          "recommended_ability_units": []
        },
        {
          "question_id": "q4_nh_value",
          "question_type": "TYPE_F",
          "recommended_competencies": [
            "직업윤리",
            "조직이해능력",
            "자기관리능력"
          ],
          "recommended_ability_units": []
        },
        {
          "question_id": "q5_nh_structure",
          "question_type": "TYPE_E",
          "recommended_competencies": [
            "기술능력",
            "디지털능력",
            "조직이해능력"
          ],
          "recommended_ability_units": []
        }
      ],
      "coaching_focus": [
        "기술능력을(를) 증명할 수 있는 경험·행동·결과를 한 문항에 하나씩 고정",
        "대인관계능력을(를) 증명할 수 있는 경험·행동·결과를 한 문항에 하나씩 고정",
        "의사소통능력을(를) 증명할 수 있는 경험·행동·결과를 한 문항에 하나씩 고정"
      ],
      "interview_watchouts": [
        "기술능력 관련 답변은 수치·판단기준·개인기여를 30초 안에 다시 설명할 수 있어야 함",
        "대인관계능력 관련 답변은 수치·판단기준·개인기여를 30초 안에 다시 설명할 수 있어야 함",
        "의사소통능력 관련 답변은 수치·판단기준·개인기여를 30초 안에 다시 설명할 수 있어야 함"
      ]
    },
    "candidate_profile": {
      "style_preference": "담백하고 근거 중심",
      "communication_style": "logical",
      "metric_coverage_ratio": 1.0,
      "personal_contribution_ratio": 1.0,
      "collaboration_ratio": 0.3,
      "abstraction_ratio": 0.0,
      "confidence_style": "assertive",
      "signature_strengths": [
        "설득",
        "프로세스개선",
        "갈등중재",
        "데이터분석"
      ],
      "blind_spots": [],
      "coaching_focus": [
        "강한 분석형 톤은 유지하되 고객·협업 맥락을 더 드러내세요."
      ],
      "interview_strategy": {
        "opening": "핵심 결론을 먼저 말하고, 곧바로 행동 근거와 결과를 붙입니다.",
        "pressure_response": "즉답이 어려우면 기준→행동→결과 순서로 짧게 재정리합니다.",
        "tone": "담백하고 근거 중심을 유지하되 질문 의도에 맞는 감정 온도를 한 문장 추가합니다."
      },
      "profile_summary": "담백하고 근거 중심 톤을 선호하는 logical형 지원자입니다. 주요 강점은 설득, 프로세스개선, 갈등중재입니다."
    },
    "narrative_ssot": {
      "core_claims": [
        "신규직원에 바로 투입 가능한 검증형 실무자",
        "농·축협에 맞는 근거 중심 문제해결형 지원자",
        "기술능력"
      ],
      "evidence_experience_ids": [
        "exp_seoul_covid_conflict",
        "exp_nps_intern",
        "exp_seoul_covid_fraud"
      ],
      "evidence_experience_titles": [
        "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
        "국민연금공단 기초연금 수급 대상자 발굴 자동화",
        "서울시청 코로나19 지원팀 부정수급 적발"
      ],
      "opening_message": "농·축협의 신규직원에서 기술능력, 대인관계능력를 만드는 지원자입니다.",
      "risk_watchouts": [],
      "answer_anchor": "주장보다 근거를 먼저 제시하고, 마지막 문장을 입사 후 기여 방식으로 닫습니다."
    },
    "research_strategy_translation": {
      "answer_tone": "차분하고 근거 중심으로 답하되 공공기관은 책임감과 고객 관점을 함께 드러냅니다.",
      "preferred_evidence_style": "행동 기준 + 수치/기록 + 개인 기여를 함께 제시",
      "disliked_expressions": [
        "항상",
        "최선을 다했습니다",
        "기여하고자 합니다"
      ],
      "essay_usefulness_score": 0.85,
      "translation_notes": [
        "핵심 회사 신호는 자소서 첫 문단과 면접 1분 답변에 공통으로 반영합니다.",
        "교차검증된 신호를 지원동기와 직무적합성 문항에 우선 반영합니다."
      ]
    },
    "outcome_dashboard": {
      "generated_at": "2026-04-06T06:38:44.620642+00:00",
      "artifact_type": "interview",
      "current_pattern": "interview|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
      "overall_success_rate": 0.0,
      "outcome_summary": {
        "matched_feedback_count": 2,
        "outcome_breakdown": {
          "unknown": 2
        },
        "top_rejection_reasons": []
      },
      "recommended_pattern": "interview|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
      "high_risk_hotspots": [
        {
          "question_type": "TYPE_D",
          "experience_id": "exp_seoul_covid_budget",
          "weighted_net_score": -6,
          "total_uses": 2
        },
        {
          "question_type": "TYPE_I",
          "experience_id": "exp_nps_income_adjustment",
          "weighted_net_score": -6,
          "total_uses": 2
        },
        {
          "question_type": "TYPE_F",
          "experience_id": "exp_seoul_covid_conflict",
          "weighted_net_score": -6,
          "total_uses": 2
        },
        {
          "question_type": "TYPE_F",
          "experience_id": "exp_nps_intern",
          "weighted_net_score": -6,
          "total_uses": 2
        },
        {
          "question_type": "TYPE_E",
          "experience_id": "exp_seoul_covid_fraud",
          "weighted_net_score": -6,
          "total_uses": 2
        }
      ]
    },
    "kpi_dashboard": {
      "generated_at": "2026-04-06T06:38:44.622119+00:00",
      "artifact_type": "interview",
      "question_experience_match_accuracy": 0.0,
      "self_intro_follow_up_hit_rate": 0.0,
      "interview_defense_success_rate": 0.0,
      "company_signal_reuse_rate": 0.0,
      "document_pass_rate": 0.0,
      "interview_pass_rate": 0.0,
      "offer_rate": 0.0,
      "company_signal_summary": {
        "core_values": [],
        "competencies": [],
        "differentiation": []
      },
      "writer_quality_metrics": {},
      "result_quality_metrics": {},
      "tracked_outcomes": {
        "unknown": 2
      }
    },
    "question_specific_hints": [
      {
        "question_id": "q1_nh_growth",
        "question_order": 1,
        "question_text": "본인의 발전을 위해 노력했던 경험 중 성장 가능성을 가장 잘 보여주는 사례와 그것을 농협 업무에 어떻게 활용할 수 있는지 기술해 주십시오.",
        "question_type": "TYPE_D",
        "hints": [
          {
            "title": "서울시설공단 / 사무 / 2024 하반기",
            "company_name": "서울시설공단",
            "job_title": "사무",
            "signal": "서울시설공단 / 사무 / TF-IDF score 0.140",
            "structure_summary": "서울시설공단 사무 문항 5개 기준, 핵심 역량 / 성장과 학습 루프 / 상황판단과 우선순위 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_B",
              "TYPE_D",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B"
            ],
            "applicable_question_types": [
              "TYPE_B",
              "TYPE_D",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": false,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_D)"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.26,
            "question_id": "q1_nh_growth",
            "question_order": 1,
            "question_text": "본인의 발전을 위해 노력했던 경험 중 성장 가능성을 가장 잘 보여주는 사례와 그것을 농협 업무에 어떻게 활용할 수 있는지 기술해 주십시오.",
            "question_type": "TYPE_D"
          },
          {
            "title": "한국전력거래소 / 사무 / 2025 상반기",
            "company_name": "한국전력거래소",
            "job_title": "사무",
            "signal": "한국전력거래소 / 사무 / TF-IDF score 0.144",
            "structure_summary": "한국전력거래소 사무 문항 3개 기준, 고객응대 / 협업과 조정 / 원칙과 신뢰 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_H",
              "TYPE_C",
              "TYPE_F"
            ],
            "applicable_question_types": [
              "TYPE_H",
              "TYPE_C",
              "TYPE_F"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "협업",
              "성장 서사"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": false,
              "warns_against_copying": true
            },
            "match_reasons": [],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.144,
            "question_id": "q1_nh_growth",
            "question_order": 1,
            "question_text": "본인의 발전을 위해 노력했던 경험 중 성장 가능성을 가장 잘 보여주는 사례와 그것을 농협 업무에 어떻게 활용할 수 있는지 기술해 주십시오.",
            "question_type": "TYPE_D"
          },
          {
            "title": "한국고용정보원 / 사업지원 / 2024 상반기",
            "company_name": "한국고용정보원",
            "job_title": "사업지원",
            "signal": "한국고용정보원 / 사업지원 / TF-IDF score 0.128",
            "structure_summary": "한국고용정보원 사업지원 문항 4개 기준, 입사 후 기여 / 핵심 역량 / 실패와 복기 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_E",
              "TYPE_B",
              "TYPE_G",
              "TYPE_C"
            ],
            "applicable_question_types": [
              "TYPE_E",
              "TYPE_B",
              "TYPE_G",
              "TYPE_C"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": false,
              "warns_against_copying": true
            },
            "match_reasons": [],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.128,
            "question_id": "q1_nh_growth",
            "question_order": 1,
            "question_text": "본인의 발전을 위해 노력했던 경험 중 성장 가능성을 가장 잘 보여주는 사례와 그것을 농협 업무에 어떻게 활용할 수 있는지 기술해 주십시오.",
            "question_type": "TYPE_D"
          }
        ]
      },
      {
        "question_id": "q2_nh_decision",
        "question_order": 2,
        "question_text": "판단이 쉽지 않은 상황에서 의사결정을 내렸던 경험을 구체적으로 기술해 주십시오.",
        "question_type": "TYPE_I",
        "hints": [
          {
            "title": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / 2024 하반기",
            "company_name": "한국보훈복지의료공단",
            "job_title": "[5급] 경영,경제,회계",
            "signal": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / TF-IDF score 0.260",
            "structure_summary": "한국보훈복지의료공단 [5급] 경영,경제,회계 문항 5개 기준, 협업과 조정 / 상황판단과 우선순위 / 협업과 조정 / 핵심 역량 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_C",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B",
              "TYPE_I"
            ],
            "applicable_question_types": [
              "TYPE_C",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B",
              "TYPE_I"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_I)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.38,
            "question_id": "q2_nh_decision",
            "question_order": 2,
            "question_text": "판단이 쉽지 않은 상황에서 의사결정을 내렸던 경험을 구체적으로 기술해 주십시오.",
            "question_type": "TYPE_I"
          },
          {
            "title": "한국기술교육대학교 / 일반행정_공무직 / 2024 하반기",
            "company_name": "한국기술교육대학교",
            "job_title": "일반행정_공무직",
            "signal": "한국기술교육대학교 / 일반행정_공무직 / TF-IDF score 0.251",
            "structure_summary": "한국기술교육대학교 일반행정_공무직 문항 6개 기준, 상황판단과 우선순위 / 협업과 조정 / 실패와 복기 / 상황판단과 우선순위 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_I",
              "TYPE_C",
              "TYPE_G",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B"
            ],
            "applicable_question_types": [
              "TYPE_I",
              "TYPE_C",
              "TYPE_G",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "성장 서사"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": false,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_I)"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.371,
            "question_id": "q2_nh_decision",
            "question_order": 2,
            "question_text": "판단이 쉽지 않은 상황에서 의사결정을 내렸던 경험을 구체적으로 기술해 주십시오.",
            "question_type": "TYPE_I"
          },
          {
            "title": "서울교통공사 / 사무 / 2025 상반기",
            "company_name": "서울교통공사",
            "job_title": "사무",
            "signal": "서울교통공사 / 사무 / TF-IDF score 0.199",
            "structure_summary": "서울교통공사 사무 문항 5개 기준, 지원동기와 직무 적합성 / 핵심 역량 / 상황판단과 우선순위 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_A",
              "TYPE_B",
              "TYPE_I",
              "TYPE_C",
              "TYPE_E"
            ],
            "applicable_question_types": [
              "TYPE_A",
              "TYPE_B",
              "TYPE_I",
              "TYPE_C",
              "TYPE_E"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_I)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.319,
            "question_id": "q2_nh_decision",
            "question_order": 2,
            "question_text": "판단이 쉽지 않은 상황에서 의사결정을 내렸던 경험을 구체적으로 기술해 주십시오.",
            "question_type": "TYPE_I"
          }
        ]
      },
      {
        "question_id": "q3_nh_trust",
        "question_order": 3,
        "question_text": "조직이나 팀에서 맡은 역할을 수행하며 동료나 구성원의 신뢰를 얻게 되었던 경험을 기술해 주십시오.",
        "question_type": "TYPE_F",
        "hints": [
          {
            "title": "한국보훈복지의료공단 / 사무 / 2025 하반기",
            "company_name": "한국보훈복지의료공단",
            "job_title": "사무",
            "signal": "한국보훈복지의료공단 / 사무 / TF-IDF score 0.109",
            "structure_summary": "한국보훈복지의료공단 사무 문항 5개 기준, 핵심 역량 / 원칙과 신뢰 / 성장과 학습 루프 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_B",
              "TYPE_F",
              "TYPE_D",
              "TYPE_C",
              "TYPE_F"
            ],
            "applicable_question_types": [
              "TYPE_B",
              "TYPE_F",
              "TYPE_D",
              "TYPE_C",
              "TYPE_F"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_F)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.229,
            "question_id": "q3_nh_trust",
            "question_order": 3,
            "question_text": "조직이나 팀에서 맡은 역할을 수행하며 동료나 구성원의 신뢰를 얻게 되었던 경험을 기술해 주십시오.",
            "question_type": "TYPE_F"
          },
          {
            "title": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / 2024 하반기",
            "company_name": "한국보훈복지의료공단",
            "job_title": "[5급] 경영,경제,회계",
            "signal": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / TF-IDF score 0.191",
            "structure_summary": "한국보훈복지의료공단 [5급] 경영,경제,회계 문항 5개 기준, 협업과 조정 / 상황판단과 우선순위 / 협업과 조정 / 핵심 역량 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_C",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B",
              "TYPE_I"
            ],
            "applicable_question_types": [
              "TYPE_C",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B",
              "TYPE_I"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.191,
            "question_id": "q3_nh_trust",
            "question_order": 3,
            "question_text": "조직이나 팀에서 맡은 역할을 수행하며 동료나 구성원의 신뢰를 얻게 되었던 경험을 기술해 주십시오.",
            "question_type": "TYPE_F"
          },
          {
            "title": "한국철도공사 / 사무영업(일반)_수도권 / 2024 하반기",
            "company_name": "한국철도공사",
            "job_title": "사무영업(일반)_수도권",
            "signal": "한국철도공사 / 사무영업(일반)_수도권 / TF-IDF score 0.150",
            "structure_summary": "한국철도공사 사무영업(일반)_수도권 문항 4개 기준, 협업과 조정 / 협업과 조정 / 협업과 조정 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_C",
              "TYPE_C",
              "TYPE_C",
              "TYPE_C"
            ],
            "applicable_question_types": [
              "TYPE_C",
              "TYPE_C",
              "TYPE_C",
              "TYPE_C"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": false,
              "warns_against_copying": true
            },
            "match_reasons": [],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.15,
            "question_id": "q3_nh_trust",
            "question_order": 3,
            "question_text": "조직이나 팀에서 맡은 역할을 수행하며 동료나 구성원의 신뢰를 얻게 되었던 경험을 기술해 주십시오.",
            "question_type": "TYPE_F"
          }
        ]
      },
      {
        "question_id": "q4_nh_value",
        "question_order": 4,
        "question_text": "농협의 구성원으로서 본인이 중요하게 생각하는 가치나 원칙과 농협에서 수행하고 싶은 역할을 기술해 주십시오.",
        "question_type": "TYPE_F",
        "hints": [
          {
            "title": "한국신용정보원 / 일반 / 2025 상반기",
            "company_name": "한국신용정보원",
            "job_title": "일반",
            "signal": "한국신용정보원 / 일반 / TF-IDF score 0.356",
            "structure_summary": "한국신용정보원 일반 문항 9개 기준, 입사 후 기여 / 고객응대 / 고객응대 / 원칙과 신뢰 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_E",
              "TYPE_H",
              "TYPE_H",
              "TYPE_F",
              "TYPE_H",
              "TYPE_B"
            ],
            "applicable_question_types": [
              "TYPE_E",
              "TYPE_H",
              "TYPE_H",
              "TYPE_F",
              "TYPE_H",
              "TYPE_B"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_F)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.476,
            "question_id": "q4_nh_value",
            "question_order": 4,
            "question_text": "농협의 구성원으로서 본인이 중요하게 생각하는 가치나 원칙과 농협에서 수행하고 싶은 역할을 기술해 주십시오.",
            "question_type": "TYPE_F"
          },
          {
            "title": "한국사회적기업진흥원 / 행정 / 2024 상반기",
            "company_name": "한국사회적기업진흥원",
            "job_title": "행정",
            "signal": "한국사회적기업진흥원 / 행정 / TF-IDF score 0.175",
            "structure_summary": "한국사회적기업진흥원 행정 문항 4개 기준, 핵심 역량 / 협업과 조정 / 원칙과 신뢰 / 실패와 복기 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_B",
              "TYPE_C",
              "TYPE_F",
              "TYPE_G"
            ],
            "applicable_question_types": [
              "TYPE_B",
              "TYPE_C",
              "TYPE_F",
              "TYPE_G"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_F)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.295,
            "question_id": "q4_nh_value",
            "question_order": 4,
            "question_text": "농협의 구성원으로서 본인이 중요하게 생각하는 가치나 원칙과 농협에서 수행하고 싶은 역할을 기술해 주십시오.",
            "question_type": "TYPE_F"
          },
          {
            "title": "중소벤처기업진흥공단 / 행정_기업평가 / 2025 하반기",
            "company_name": "중소벤처기업진흥공단",
            "job_title": "행정_기업평가",
            "signal": "중소벤처기업진흥공단 / 행정_기업평가 / TF-IDF score 0.159",
            "structure_summary": "중소벤처기업진흥공단 행정_기업평가 문항 4개 기준, 원칙과 신뢰 / 실패와 복기 / 핵심 역량 / 핵심 역량 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_F",
              "TYPE_G",
              "TYPE_B",
              "TYPE_B"
            ],
            "applicable_question_types": [
              "TYPE_F",
              "TYPE_G",
              "TYPE_B",
              "TYPE_B"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_F)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.279,
            "question_id": "q4_nh_value",
            "question_order": 4,
            "question_text": "농협의 구성원으로서 본인이 중요하게 생각하는 가치나 원칙과 농협에서 수행하고 싶은 역할을 기술해 주십시오.",
            "question_type": "TYPE_F"
          }
        ]
      },
      {
        "question_id": "q5_nh_structure",
        "question_order": 5,
        "question_text": "농협이 교육지원·경제·금융 사업을 동시에 수행하는 구조가 가지는 경쟁력과 본인이 기여할 수 있는 부분을 기술해 주십시오.",
        "question_type": "TYPE_E",
        "hints": [
          {
            "title": "한국산업단지공단 / 경영·경제(일반_4급) / 2024 하반기",
            "company_name": "한국산업단지공단",
            "job_title": "경영·경제(일반_4급)",
            "signal": "한국산업단지공단 / 경영·경제(일반_4급) / TF-IDF score 0.351",
            "structure_summary": "한국산업단지공단 경영·경제(일반_4급) 문항 6개 기준, 핵심 역량 / 협업과 조정 / 핵심 역량 / 핵심 역량 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_B",
              "TYPE_C",
              "TYPE_B",
              "TYPE_B",
              "TYPE_E",
              "TYPE_C"
            ],
            "applicable_question_types": [
              "TYPE_B",
              "TYPE_C",
              "TYPE_B",
              "TYPE_B",
              "TYPE_E",
              "TYPE_C"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_E)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.471,
            "question_id": "q5_nh_structure",
            "question_order": 5,
            "question_text": "농협이 교육지원·경제·금융 사업을 동시에 수행하는 구조가 가지는 경쟁력과 본인이 기여할 수 있는 부분을 기술해 주십시오.",
            "question_type": "TYPE_E"
          },
          {
            "title": "대한적십자사 / 일반사무 / 2025 상반기",
            "company_name": "대한적십자사",
            "job_title": "일반사무",
            "signal": "대한적십자사 / 일반사무 / TF-IDF score 0.220",
            "structure_summary": "대한적십자사 일반사무 문항 4개 기준, 입사 후 기여 / 핵심 역량 / 성장과 학습 루프 / 원칙과 신뢰 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_E",
              "TYPE_B",
              "TYPE_D",
              "TYPE_F"
            ],
            "applicable_question_types": [
              "TYPE_E",
              "TYPE_B",
              "TYPE_D",
              "TYPE_F"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_E)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.34,
            "question_id": "q5_nh_structure",
            "question_order": 5,
            "question_text": "농협이 교육지원·경제·금융 사업을 동시에 수행하는 구조가 가지는 경쟁력과 본인이 기여할 수 있는 부분을 기술해 주십시오.",
            "question_type": "TYPE_E"
          },
          {
            "title": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / 2024 하반기",
            "company_name": "한국보훈복지의료공단",
            "job_title": "[5급] 경영,경제,회계",
            "signal": "한국보훈복지의료공단 / [5급] 경영,경제,회계 / TF-IDF score 0.295",
            "structure_summary": "한국보훈복지의료공단 [5급] 경영,경제,회계 문항 5개 기준, 협업과 조정 / 상황판단과 우선순위 / 협업과 조정 / 핵심 역량 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_C",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B",
              "TYPE_I"
            ],
            "applicable_question_types": [
              "TYPE_C",
              "TYPE_I",
              "TYPE_C",
              "TYPE_B",
              "TYPE_I"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "문제 해결",
              "협업"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.295,
            "question_id": "q5_nh_structure",
            "question_order": 5,
            "question_text": "농협이 교육지원·경제·금융 사업을 동시에 수행하는 구조가 가지는 경쟁력과 본인이 기여할 수 있는 부분을 기술해 주십시오.",
            "question_type": "TYPE_E"
          }
        ]
      }
    ],
    "application_strategy": {
      "company_name": "농·축협",
      "job_title": "신규직원",
      "company_type": "협동조합",
      "updated_at": "2026-04-06T06:38:44.615796+00:00",
      "experience_priority": [
        {
          "experience_id": "exp_seoul_covid_fraud",
          "title": "서울시청 코로나19 지원팀 부정수급 적발",
          "reason": "기본 우선 경험"
        },
        {
          "experience_id": "exp_seoul_covid_crisis",
          "title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
          "reason": "기본 우선 경험"
        },
        {
          "experience_id": "exp_seoul_covid_budget",
          "title": "서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감",
          "reason": "기본 우선 경험"
        }
      ],
      "self_intro_candidates": {
        "opening_hook": "농·축협의 신규직원에서 기술능력, 대인관계능력를 만드는 지원자입니다.",
        "top001_hooks": [
          {
            "type": "result_hook",
            "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 부정수급 20건 적발, 예산 40% 절감",
            "score": 0.95
          },
          {
            "type": "result_hook",
            "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 수백 통 민원 당일 수습",
            "score": 0.95
          },
          {
            "type": "result_hook",
            "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 1억 원 예산 절감",
            "score": 0.95
          },
          {
            "type": "connection_hook",
            "content": "귀사의 농·축협 방향성과 직접 연결되는 경험입니다",
            "score": 0.7
          }
        ],
        "top001_versions": {
          "elevator": "신규직원에서 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악... 경험을 바탕으로 핵심 성과를 만들고자 합니다",
          "30s": "저는 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 그 결과 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이를 신규직원에 기여할 수 있는 역량으로 발전시키고 싶습니다",
          "60s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 농·축협에서 발전시키고 싶습니다",
          "90s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 농·축협에서 발전시키고 싶습니다 그 과정에서 제가 중점적으로 맡은 부분은 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대이었습니다 구체적으로 수백 통 민원 당일 수습의 성과를 냈습니다 이 경험을 농·축협의 신규직원에서 실질적 기여로 연결하고 싶습니다"
        },
        "expected_follow_ups": [
          "그 결과는 어떻게 측정하거나 확인하셨나요?",
          "그 경험에서 가장 어려웠던 부분은 무엇이었나요?"
        ]
      },
      "stage_payloads": {
        "self_intro": {
          "coach_analysis": null,
          "self_intro_pack": {
            "opening_hook": "농·축협의 신규직원에서 기술능력, 대인관계능력를 만드는 지원자입니다.",
            "thirty_second_frame": [
              "현재 지원 직무와 가장 직접 연결되는 경험 1개를 먼저 말한다.",
              "핵심 경험: 서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재, 국민연금공단 기초연금 수급 대상자 발굴 자동화",
              "마무리는 농·축협에서의 첫 기여 포인트로 닫는다."
            ],
            "sixty_second_frame": [
              "지원 직무와 연결되는 문제 인식",
              "본인 행동과 판단 기준",
              "정량 또는 정성 결과",
              "입사 후 적용 계획"
            ],
            "focus_keywords": [
              "기술능력",
              "대인관계능력"
            ],
            "banned_patterns": [],
            "committee_watchouts": [],
            "ncs_priority_competencies": [
              "기술능력",
              "대인관계능력",
              "의사소통능력"
            ],
            "top001_hooks": [
              {
                "type": "result_hook",
                "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 부정수급 20건 적발, 예산 40% 절감",
                "score": 0.95
              },
              {
                "type": "result_hook",
                "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 수백 통 민원 당일 수습",
                "score": 0.95
              },
              {
                "type": "result_hook",
                "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 1억 원 예산 절감",
                "score": 0.95
              },
              {
                "type": "connection_hook",
                "content": "귀사의 농·축협 방향성과 직접 연결되는 경험입니다",
                "score": 0.7
              }
            ],
            "top001_versions": {
              "elevator": "신규직원에서 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악... 경험을 바탕으로 핵심 성과를 만들고자 합니다",
              "30s": "저는 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 그 결과 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이를 신규직원에 기여할 수 있는 역량으로 발전시키고 싶습니다",
              "60s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 농·축협에서 발전시키고 싶습니다",
              "90s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 농·축협에서 발전시키고 싶습니다 그 과정에서 제가 중점적으로 맡은 부분은 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대이었습니다 구체적으로 수백 통 민원 당일 수습의 성과를 냈습니다 이 경험을 농·축협의 신규직원에서 실질적 기여로 연결하고 싶습니다"
            },
            "top001_expected_follow_ups": [
              "그 결과는 어떻게 측정하거나 확인하셨나요?",
              "그 경험에서 가장 어려웠던 부분은 무엇이었나요?"
            ]
          },
          "research_strategy": null,
          "interview_top001": null,
          "allocations": null,
          "experience_competition": null,
          "writer_differentiation": null,
          "adaptive_strategy": null,
          "feedback_adaptation_plan": null
        },
        "coach": {
          "coach_analysis": {
            "coaching_state": 2,
            "temporal_inconsistencies": [],
            "role_inconsistencies": [],
            "allocation_issues": [
              {
                "type": "consecutive_same_org",
                "severity": "medium",
                "organization": "서울시청 시민건강국 코로나19지원팀",
                "positions": [
                  2,
                  3
                ],
                "message": "동일 조직(서울시청 시민건강국 코로나19지원팀) 경험이 연속 문항에 배치되었습니다. 다른 관점이나 기간의 경험으로 분리하세요."
              }
            ],
            "suggestions": [],
            "coverage_report": {
              "total_experiences": 10,
              "experiences_in_use": 5,
              "l3_experiences": 5,
              "verified_experiences": 10,
              "total_questions": 5,
              "allocated_questions": 5,
              "uncovered_question_count": 0,
              "coverage_rate": 1.0
            },
            "progressive_plan": [
              {
                "session": 1,
                "state": 2,
                "focus": "핵심 경험 3개 발굴 + STAR 구조화",
                "activities": [
                  "가장 설득력 있는 경험 선택",
                  "각 경험의 상황-행동-결과 정리",
                  "면접에서 다시 꺼낼 증빙 문장 만들기"
                ],
                "output": "경험 카드 3개 완성"
              },
              {
                "session": 2,
                "state": 3,
                "focus": "문항별 경험 매핑 + 차별화 포인트",
                "activities": [
                  "문항 유형별 핵심 메시지 설정",
                  "경험-문항 최적 배분",
                  "회사와 직무 접점 찾기"
                ],
                "output": "경험 배분표 + 차별화 전략"
              },
              {
                "session": 3,
                "state": 4,
                "focus": "근거 검증 및 보강",
                "activities": [
                  "L3 증거 수준 확인",
                  "수치와 측정 기준 검증",
                  "증빙 자료 준비"
                ],
                "output": "검증 완료 경험列表"
              },
              {
                "session": 4,
                "state": 5,
                "focus": "면접 예상 질문 + 방어 연습",
                "activities": [
                  "3-depth 꼬리질문 시뮬레이션",
                  "30초 스피치 연습",
                  "취약점 방어 연습"
                ],
                "output": "완성된 답변 프레임워크"
              }
            ]
          },
          "self_intro_pack": null,
          "research_strategy": null,
          "interview_top001": null,
          "allocations": [
            {
              "question_id": "q1_nh_growth",
              "order_no": 1,
              "question_type": "TYPE_D",
              "experience_id": "exp_seoul_covid_conflict",
              "experience_title": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
              "score": 15,
              "reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(본인의, 발전을, 위해)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(업무 효율 30% 증가) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            },
            {
              "question_id": "q2_nh_decision",
              "order_no": 2,
              "question_type": "TYPE_I",
              "experience_id": "exp_nps_intern",
              "experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
              "score": 13,
              "reason": "질문 기대: 상황판단과 우선순위 문항이며, 질문 키워드(판단이, 쉽지, 않은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            },
            {
              "question_id": "q3_nh_trust",
              "order_no": 3,
              "question_type": "TYPE_F",
              "experience_id": "exp_seoul_covid_fraud",
              "experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
              "score": 13,
              "reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(조직이나, 팀에서, 맡은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            },
            {
              "question_id": "q4_nh_value",
              "order_no": 4,
              "question_type": "TYPE_F",
              "experience_id": "exp_seoul_covid_crisis",
              "experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
              "score": 9,
              "reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(농협의, 구성원으로서, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            },
            {
              "question_id": "q5_nh_structure",
              "order_no": 5,
              "question_type": "TYPE_E",
              "experience_id": "exp_mg_bank_parttime",
              "experience_title": "새마을금고 아르바이트 - 디지털 취약 고객 응대",
              "score": 11,
              "reason": "질문 기대: 입사 후 기여 문항이며, 질문 키워드(농협이, 교육지원, 경제)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(디지털 취약 계층 응대 성공) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            }
          ],
          "experience_competition": [
            {
              "question_id": "q1_nh_growth",
              "question_text": "본인의 발전을 위해 노력했던 경험 중 성장 가능성을 가장 잘 보여주는 사례와 그것을 농협 업무에 어떻게 활용할 수 있는지 기술해 주십시오.",
              "question_type": "TYPE_D",
              "primary_experience_id": "exp_seoul_covid_conflict",
              "primary_experience_title": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
              "primary_reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(본인의, 발전을, 위해)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(업무 효율 30% 증가) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_nps_income_adjustment",
              "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            },
            {
              "question_id": "q2_nh_decision",
              "question_text": "판단이 쉽지 않은 상황에서 의사결정을 내렸던 경험을 구체적으로 기술해 주십시오.",
              "question_type": "TYPE_I",
              "primary_experience_id": "exp_nps_intern",
              "primary_experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
              "primary_reason": "질문 기대: 상황판단과 우선순위 문항이며, 질문 키워드(판단이, 쉽지, 않은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_nps_income_adjustment",
              "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            },
            {
              "question_id": "q3_nh_trust",
              "question_text": "조직이나 팀에서 맡은 역할을 수행하며 동료나 구성원의 신뢰를 얻게 되었던 경험을 기술해 주십시오.",
              "question_type": "TYPE_F",
              "primary_experience_id": "exp_seoul_covid_fraud",
              "primary_experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
              "primary_reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(조직이나, 팀에서, 맡은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_nps_income_adjustment",
              "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            },
            {
              "question_id": "q4_nh_value",
              "question_text": "농협의 구성원으로서 본인이 중요하게 생각하는 가치나 원칙과 농협에서 수행하고 싶은 역할을 기술해 주십시오.",
              "question_type": "TYPE_F",
              "primary_experience_id": "exp_seoul_covid_crisis",
              "primary_experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
              "primary_reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(농협의, 구성원으로서, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_seoul_covid_budget",
              "secondary_experience_title": "서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            },
            {
              "question_id": "q5_nh_structure",
              "question_text": "농협이 교육지원·경제·금융 사업을 동시에 수행하는 구조가 가지는 경쟁력과 본인이 기여할 수 있는 부분을 기술해 주십시오.",
              "question_type": "TYPE_E",
              "primary_experience_id": "exp_mg_bank_parttime",
              "primary_experience_title": "새마을금고 아르바이트 - 디지털 취약 고객 응대",
              "primary_reason": "질문 기대: 입사 후 기여 문항이며, 질문 키워드(농협이, 교육지원, 경제)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(디지털 취약 계층 응대 성공) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_seoul_covid_budget",
              "secondary_experience_title": "서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            }
          ],
          "writer_differentiation": null,
          "adaptive_strategy": {
            "company_profile": "협동조합",
            "interview_mode": "실행력 검증 + 모호성 대응",
            "writer_logic": "가설-실험-학습 구조를 강조하고, 제한된 자원에서의 판단을 드러냅니다.",
            "coaching_mode": "핵심 메시지를 먼저 세우고 경험 근거를 뒤에서 지지하는 방식으로 훈련합니다.",
            "career_stage": "ENTRY"
          },
          "feedback_adaptation_plan": null
        },
        "research": {
          "coach_analysis": null,
          "self_intro_pack": null,
          "research_strategy": {
            "answer_tone": "차분하고 근거 중심으로 답하되 공공기관은 책임감과 고객 관점을 함께 드러냅니다.",
            "preferred_evidence_style": "행동 기준 + 수치/기록 + 개인 기여를 함께 제시",
            "disliked_expressions": [
              "항상",
              "최선을 다했습니다",
              "기여하고자 합니다"
            ],
            "essay_usefulness_score": 0.85,
            "translation_notes": [
              "핵심 회사 신호는 자소서 첫 문단과 면접 1분 답변에 공통으로 반영합니다.",
              "교차검증된 신호를 지원동기와 직무적합성 문항에 우선 반영합니다."
            ]
          },
          "interview_top001": null,
          "allocations": null,
          "experience_competition": null,
          "writer_differentiation": null,
          "adaptive_strategy": null,
          "feedback_adaptation_plan": null
        },
        "writer": {
          "coach_analysis": null,
          "self_intro_pack": null,
          "research_strategy": null,
          "interview_top001": null,
          "allocations": null,
          "experience_competition": null,
          "writer_differentiation": {
            "generated_at": "2026-04-05T11:38:58.950478+00:00",
            "company_name": "농·축협",
            "job_title": "신규직원",
            "pressure_points": [
              "조직 내 갈등을 해결한 경험은?",
              "목표 달성을 위해 우선순위를 조정했던 경험은?"
            ],
            "rows": []
          },
          "adaptive_strategy": {
            "company_profile": "협동조합",
            "interview_mode": "실행력 검증 + 모호성 대응",
            "writer_logic": "가설-실험-학습 구조를 강조하고, 제한된 자원에서의 판단을 드러냅니다.",
            "coaching_mode": "핵심 메시지를 먼저 세우고 경험 근거를 뒤에서 지지하는 방식으로 훈련합니다.",
            "career_stage": "ENTRY"
          },
          "feedback_adaptation_plan": {
            "recommended_pattern": "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
            "focus_actions": [
              "TYPE_D 문항은 경험 선택 재검토",
              "TYPE_I 문항은 경험 선택 재검토"
            ],
            "risky_question_types": [
              {
                "question_type": "TYPE_D",
                "weak_experiences": [
                  {
                    "experience_id": "exp_seoul_covid_budget",
                    "pass_rate": 0.0,
                    "weighted_net_score": -3,
                    "top_rejection_reasons": []
                  }
                ],
                "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
              },
              {
                "question_type": "TYPE_I",
                "weak_experiences": [
                  {
                    "experience_id": "exp_nps_income_adjustment",
                    "pass_rate": 0.0,
                    "weighted_net_score": -3,
                    "top_rejection_reasons": []
                  }
                ],
                "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
              },
              {
                "question_type": "TYPE_F",
                "weak_experiences": [
                  {
                    "experience_id": "exp_seoul_covid_conflict",
                    "pass_rate": 0.0,
                    "weighted_net_score": -3,
                    "top_rejection_reasons": []
                  },
                  {
                    "experience_id": "exp_nps_intern",
                    "pass_rate": 0.0,
                    "weighted_net_score": -3,
                    "top_rejection_reasons": []
                  }
                ],
                "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
              },
              {
                "question_type": "TYPE_E",
                "weak_experiences": [
                  {
                    "experience_id": "exp_seoul_covid_fraud",
                    "pass_rate": 0.0,
                    "weighted_net_score": -3,
                    "top_rejection_reasons": []
                  }
                ],
                "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
              }
            ],
            "matched_feedback_count": 1
          }
        }
      },
      "coach_recommendations": [],
      "experience_coverage": {
        "total_experiences": 10,
        "experiences_in_use": 5,
        "l3_experiences": 5,
        "verified_experiences": 10,
        "total_questions": 5,
        "allocated_questions": 5,
        "uncovered_question_count": 0,
        "coverage_rate": 1.0
      },
      "experience_competition": [
        {
          "question_id": "q1_nh_growth",
          "question_text": "본인의 발전을 위해 노력했던 경험 중 성장 가능성을 가장 잘 보여주는 사례와 그것을 농협 업무에 어떻게 활용할 수 있는지 기술해 주십시오.",
          "question_type": "TYPE_D",
          "primary_experience_id": "exp_seoul_covid_conflict",
          "primary_experience_title": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
          "primary_reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(본인의, 발전을, 위해)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(업무 효율 30% 증가) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_nps_income_adjustment",
          "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        },
        {
          "question_id": "q2_nh_decision",
          "question_text": "판단이 쉽지 않은 상황에서 의사결정을 내렸던 경험을 구체적으로 기술해 주십시오.",
          "question_type": "TYPE_I",
          "primary_experience_id": "exp_nps_intern",
          "primary_experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
          "primary_reason": "질문 기대: 상황판단과 우선순위 문항이며, 질문 키워드(판단이, 쉽지, 않은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_nps_income_adjustment",
          "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        },
        {
          "question_id": "q3_nh_trust",
          "question_text": "조직이나 팀에서 맡은 역할을 수행하며 동료나 구성원의 신뢰를 얻게 되었던 경험을 기술해 주십시오.",
          "question_type": "TYPE_F",
          "primary_experience_id": "exp_seoul_covid_fraud",
          "primary_experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
          "primary_reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(조직이나, 팀에서, 맡은)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_nps_income_adjustment",
          "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        },
        {
          "question_id": "q4_nh_value",
          "question_text": "농협의 구성원으로서 본인이 중요하게 생각하는 가치나 원칙과 농협에서 수행하고 싶은 역할을 기술해 주십시오.",
          "question_type": "TYPE_F",
          "primary_experience_id": "exp_seoul_covid_crisis",
          "primary_experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
          "primary_reason": "질문 기대: 원칙과 신뢰 문항이며, 질문 키워드(농협의, 구성원으로서, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_seoul_covid_budget",
          "secondary_experience_title": "서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        },
        {
          "question_id": "q5_nh_structure",
          "question_text": "농협이 교육지원·경제·금융 사업을 동시에 수행하는 구조가 가지는 경쟁력과 본인이 기여할 수 있는 부분을 기술해 주십시오.",
          "question_type": "TYPE_E",
          "primary_experience_id": "exp_mg_bank_parttime",
          "primary_experience_title": "새마을금고 아르바이트 - 디지털 취약 고객 응대",
          "primary_reason": "질문 기대: 입사 후 기여 문항이며, 질문 키워드(농협이, 교육지원, 경제)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(디지털 취약 계층 응대 성공) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_seoul_covid_budget",
          "secondary_experience_title": "서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        }
      ],
      "adaptive_strategy_layer": {
        "company_profile": "협동조합",
        "interview_mode": "실행력 검증 + 모호성 대응",
        "writer_logic": "가설-실험-학습 구조를 강조하고, 제한된 자원에서의 판단을 드러냅니다.",
        "coaching_mode": "핵심 메시지를 먼저 세우고 경험 근거를 뒤에서 지지하는 방식으로 훈련합니다.",
        "career_stage": "ENTRY"
      },
      "company_signal_summary": {
        "core_values": [],
        "competencies": [],
        "differentiation": []
      },
      "question_strategy": {},
      "interview_pressure_points": [],
      "writer_differentiation": {
        "generated_at": "2026-04-05T11:38:58.950478+00:00",
        "company_name": "농·축협",
        "job_title": "신규직원",
        "pressure_points": [
          "조직 내 갈등을 해결한 경험은?",
          "목표 달성을 위해 우선순위를 조정했던 경험은?"
        ],
        "rows": []
      },
      "feedback_adaptation_plan": {
        "recommended_pattern": "writer|협동조합|TYPE_D-TYPE_E-TYPE_F-TYPE_I",
        "focus_actions": [
          "TYPE_D 문항은 경험 선택 재검토",
          "TYPE_I 문항은 경험 선택 재검토"
        ],
        "risky_question_types": [
          {
            "question_type": "TYPE_D",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_budget",
                "pass_rate": 0.0,
                "weighted_net_score": -3,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_I",
            "weak_experiences": [
              {
                "experience_id": "exp_nps_income_adjustment",
                "pass_rate": 0.0,
                "weighted_net_score": -3,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_F",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_conflict",
                "pass_rate": 0.0,
                "weighted_net_score": -3,
                "top_rejection_reasons": []
              },
              {
                "experience_id": "exp_nps_intern",
                "pass_rate": 0.0,
                "weighted_net_score": -3,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_E",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_fraud",
                "pass_rate": 0.0,
                "weighted_net_score": -3,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          }
        ],
        "matched_feedback_count": 1
      }
    },
    "self_intro_pack": {
      "opening_hook": "농·축협의 신규직원에서 기술능력, 대인관계능력를 만드는 지원자입니다.",
      "thirty_second_frame": [
        "현재 지원 직무와 가장 직접 연결되는 경험 1개를 먼저 말한다.",
        "핵심 경험: 서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재, 국민연금공단 기초연금 수급 대상자 발굴 자동화",
        "마무리는 농·축협에서의 첫 기여 포인트로 닫는다."
      ],
      "sixty_second_frame": [
        "지원 직무와 연결되는 문제 인식",
        "본인 행동과 판단 기준",
        "정량 또는 정성 결과",
        "입사 후 적용 계획"
      ],
      "focus_keywords": [
        "기술능력",
        "대인관계능력"
      ],
      "banned_patterns": [],
      "committee_watchouts": [],
      "ncs_priority_competencies": [
        "기술능력",
        "대인관계능력",
        "의사소통능력"
      ],
      "top001_hooks": [
        {
          "type": "result_hook",
          "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 부정수급 20건 적발, 예산 40% 절감",
          "score": 0.95
        },
        {
          "type": "result_hook",
          "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 수백 통 민원 당일 수습",
          "score": 0.95
        },
        {
          "type": "result_hook",
          "content": "정량적 성과를 증명한 구체적 경험이 있습니다: 1억 원 예산 절감",
          "score": 0.95
        },
        {
          "type": "connection_hook",
          "content": "귀사의 농·축협 방향성과 직접 연결되는 경험입니다",
          "score": 0.7
        }
      ],
      "top001_versions": {
        "elevator": "신규직원에서 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악... 경험을 바탕으로 핵심 성과를 만들고자 합니다",
        "30s": "저는 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 그 결과 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이를 신규직원에 기여할 수 있는 역량으로 발전시키고 싶습니다",
        "60s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 농·축협에서 발전시키고 싶습니다",
        "90s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 농·축협에서 발전시키고 싶습니다 그 과정에서 제가 중점적으로 맡은 부분은 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대이었습니다 구체적으로 수백 통 민원 당일 수습의 성과를 냈습니다 이 경험을 농·축협의 신규직원에서 실질적 기여로 연결하고 싶습니다"
      },
      "top001_expected_follow_ups": [
        "그 결과는 어떻게 측정하거나 확인하셨나요?",
        "그 경험에서 가장 어려웠던 부분은 무엇이었나요?"
      ]
    }
  }
}
