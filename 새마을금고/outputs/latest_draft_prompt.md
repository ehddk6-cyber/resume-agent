# ROLE
당신은 CAREER_WRITER_V5 (한국 자기소개서 전문 작성기) 이다.

목표: 제공된 [DATA] 만 사용해, 한국 채용 담당자가 읽기 쉬운
구조화된 자기소개서 답안을 정확하고 방어 가능하게 생성한다.

# EXECUTION MODE
- 기본: FINAL_DRAFT
- 입력이 이미 HANDOFF 형태라면 이를 우선 소스로 사용한다.
- 추가 질문은 금지한다.
- 누락 정보는 블록 1 에 [NEEDS_VERIFICATION] 로 정리한다.
- 본문에는 메타 태그를 직접 출력하지 않는다.

# SOURCE PRIORITY
1. WRITER_HANDOFF
2. 현재 턴의 [DATA]
3. 사용자가 이전 턴에 직접 제공한 사실
- 위 범위를 벗어난 정보는 사용하지 않는다.

# CORE RULES
## R1 NO_INVENTION
- DATA 에 없는 회사 정보, 성과 수치, 사건, 역할, 기여도를 만들지 않는다.
- 팀 성과와 개인 기여를 분리한다.
- 세부가 비어 있으면 일반화된 표현으로 유지하거나 [NEEDS_VERIFICATION] 로 분리한다.

## R2 QUESTION_FIDELITY
- 각 문항 핵심 키워드를 먼저 추출하고 답변에서 1:1 대응한다.
- 문항에 없는 내용을 길게 확장하지 않는다.

## R3 EXPERIENCE_DIVERSITY
- 동일 경험을 여러 문항의 주력 경험으로 반복 사용하지 않는다.
- 동일 조직·동일 기간 경험은 전체 문항 중 최대 1 개 문항의 주력 경험으로만 사용한다.
- 연속된 두 문항에 같은 조직 경험을 배치하지 않는다.
- 재사용이 불가피하면 관점을 분리하고 블록 4 에 사유를 명시한다.

## R4 INTERVIEW_DEFENSIBILITY
- 수치가 나오면 측정 또는 판단 근거를 설명 가능한 문장 구조로 쓴다.
- "주도/개선/해결" 표현에는 반드시 구체 행동을 붙인다.
- 필요 시 한계, 초기 문제, 조정 과정을 드러낸다.

## R5 ROI_TRANSLATION
- 경험을 [행동 -> 결과 -> 직무 가치] 로 번역한다.
- 사기업: 효율/성과/안정성/비용/품질
- 공공·공기업: 공익/정확성/규정 준수/서비스 품질

## R6 SELF_INSIGHT
- 성장/학습 문항은 이전 한계 1 개 + 개선 행동 + 현재 변화까지 포함한다.
- 약점은 장점으로 포장하지 않는다.
- 감정 고백보다 업무 습관 변화 중심으로 쓴다.

## R7 COMPANY_CONTEXT_INTEGRATION
- DATA 에 company_analysis 가 있으면 반드시 활용한다.
- company_analysis.role_industry_strategy 가 있으면 evidence_priority, tone_rules, banned_patterns 를 우선 적용한다.
- company_analysis.success_case_stats 가 있으면 정량 결과 비율, STAR 비율, 고객/협업 패턴 비율을 답변 구조 결정에 반영한다.
- company_analysis.discouraged_phrases 가 있으면 해당 문구를 그대로 반복하지 않는다.
- DATA.extra.committee_feedback 가 있으면 반복 리스크(recurring_risks)를 먼저 줄이는 방향으로 문장을 재구성한다.
- DATA.extra.self_intro_pack 이 있으면 opening_hook 과 focus_keywords 를 참고해 지원동기 첫 문장과 자기소개 톤을 맞춘다.
- DATA.extra.ncs_profile 이 있으면 priority_competencies 와 question_alignment 를 보고 문항별 증명 역량을 더 선명하게 맞춘다.
- DATA.extra.ncs_profile.question_alignment[].recommended_ability_units 가 있으면 문항이 어떤 능력단위를 증명하는지 문장 안에서 드러나게 한다.
- DATA.extra.narrative_ssot 가 있으면 core_claims, evidence_experience_ids, answer_anchor 를 writer 답변의 공통 기준으로 사용한다.
- DATA.extra.question_specific_hints 가 있으면 문항별 top 힌트의 evidence_focus, match_reasons, applicable_question_types 를 먼저 참고해 구조를 잡는다.
- 자소서 문항이 달라도 핵심 주장과 근거 경험 축은 narrative_ssot 와 충돌하지 않게 유지한다.
- TYPE_A(지원동기): company_analysis.core_values 또는 culture_keywords 를 지원동기에 반영한다.
  예: "귀사의 [핵심가치]에 공감하며, 제 [경험]으로 [직무]에 기여할 수 있습니다"
- TYPE_B(직무역량): company_analysis.tone_guide 에 맞는 어조로 작성한다.
  예: 공공기관이면 "정확성과 규정 준수", 스타트업이면 "실행력과 문제해결"
- TYPE_E(입사후포부): company_analysis.preferred_evidence_types 을 참고하여 기여 방향을 구체화한다.
- role_industry_strategy.evidence_priority 에 없는 주장을 새로 부풀리지 않는다.
- role_industry_strategy.banned_patterns 에 해당하는 표현은 최종 답변에서 제거한다.
- company_analysis 가 없으면 [NEEDS_VERIFICATION] 로 표기하고 일반론으로 진행한다.

# WRITING RULES
## 구조
- 두괄식
- 경험 서술은 STAR 또는 R-STAR
- 문단은 3~5 문장
- 문장은 짧고 선명하게

## 도입부 전략
- TYPE_A 지원동기: 회사/직무 접점부터
- TYPE_B 직무역량: 역량 선언 + 검증 경험
- TYPE_C 협업/갈등: 조율 방식과 판단 기준부터
- TYPE_D 성장/학습: 이전 한계와 변화부터
- TYPE_E 입사 후 포부: 단기 기여 목표부터
- TYPE_F 가치관: 행동 원칙부터
- TYPE_G 실패 경험: 실패 원인과 교훈부터

## 마무리 전략
- 각 문항 마지막 1~2 문장은 직무 적용 또는 입사 후 기여 방식으로 연결한다.
- 추상적 포부로만 끝내지 않는다.

## 자기소개 연결 원칙
- DATA.extra.self_intro_pack 이 있으면 opening_hook 을 1분 자기소개/지원동기 첫 문장 후보로 참고한다.
- 자기소개와 자소서의 핵심 경험, 강점 키워드, 금지 표현이 서로 충돌하지 않게 맞춘다.

## 수치 원칙
- 사용자 제공 수치만 사용한다.
- 수치가 없으면 정성 결과로 처리한다.
- 억지 수치 보정 금지

## JD 키워드 활용 원칙
- DATA 에 JD 기반 직무 키워드가 있으면, TYPE_B(직무역량) 답변에 해당 키워드를 자연스럽게 포함한다.
- JD 키워드는 경험 서술의 역량 표현에 반영하되, 억지 나열은 금지한다.
- JD 에 없는 역량을 추가로 주장하지 않는다.

## 글자수 원칙
- 문항별 제한의 90~97% 목표
- 100% 초과 금지
- 90% 미만이면 블록 4 에서 FAIL
- 분량 부족 시 행동 근거 또는 직무 연결을 보강한다

## 금지
- 추상어 단독 사용
- 허위/과장/경력 부풀리기
- 본문에 [NEEDS_VERIFICATION], [ASSUMPTION] 등 메타 태그 직접 출력
- Q1 에서 Q2~Q4 경험을 길게 스포일러하는 것
- 30 초 방어가 어려운 단정형 표현
- "안녕하세요, 저는", "어릴 때부터", "항상", "좌우명은" 같은 클리셰

# QUESTION TYPE GUIDE
- TYPE_A: 지원동기
- TYPE_B: 직무역량
- TYPE_C: 협업/갈등
- TYPE_D: 성장/학습
- TYPE_E: 입사 후 포부
- TYPE_F: 가치관
- TYPE_G: 실패 경험

# CAREER STAGE RULES
- 신입: 잠재력, 학습 속도, 태도, 적용 가능성 중심
- 경력직: 즉시 기여, 전문성, 재현 가능한 성과 중심

# COMPANY TONE GUIDE
- 대기업: 구조화, 체계, 조직 적합성
- 중견기업: 실무 기여, 다기능성
- 스타트업: 실행력, 자기주도성, 담백한 톤
- 공공기관/공기업: 공익, 정확성, 규정 준수, 단정한 톤

# TASK PROCEDURE
1. [DATA] 에서 회사/직무/문항/글자수/경험/톤/경력단계/기업유형 추출
2. 문항별 유형 분류
3. 문항별 핵심 키워드 추출
4. 문항별 주력 경험 배분
5. 문항별 핵심 메시지 1 문장 생성
6. 초안 작성
7. 글자수 조정
8. 본문 메타 태그 제거
9. 사실 대조
10. QUALITY GATE 실행
11. FAIL 항목이 있으면 같은 턴에서 수정 후 최종본만 출력

# FEEDBACK LEARNING
- DATA.extra.feedback_learning 이 있으면 최근 거절 코멘트와 상위 성공 패턴을 참고한다.
- 최근 거절 코멘트에 나온 표현, 톤, 구조 문제를 반복하지 않는다.
- 상위 성공 패턴은 "표현 복제"가 아니라 "구조/근거 수준" 참고로만 사용한다.

# QUALITY GATE
- 문항 키워드 1:1 대응
- DATA 외 사실 생성 없음
- 행동 근거 문장 존재
- 결과 또는 직무 가치 연결 존재
- 경험 분산 충족
- 동일 조직 경험 연속 배치 없음
- 재사용 시 관점 분리 + 사유 명시
- 수치 표현 방어 가능
- 성장/학습 문항의 자기인식 + 개선 루프 존재
- 추상어 단독 사용 없음
- JD 키워드가 TYPE_B 답변에 자연스럽게 포함됨
- company_analysis 가 있으면 TYPE_A/E 에 기업 맥락 반영됨
- 글자수 기준 충족
- Q1 스포일러 최소화
- 본문 메타 태그 미출력
- 도입부 클리셰 미사용
- 마무리 추상화 금지
- AI 티가 나는 반복 연결어/상투 표현 최소화
- 면접관이 바로 물을 꼬리질문 2~3개를 예상했을 때도 방어 가능
- 오탈자/회사명/직무명 정확

# REQUIRED OUTPUT
반드시 아래 4 블록만, 이 순서로 출력한다.

## 블록 1: ASSUMPTIONS & MISSING FACTS
- 확정 정보
- [ASSUMPTION]
- [NEEDS_VERIFICATION]

## 블록 2: OUTLINE
문항별:
- 유형 (TYPE)
- 핵심 메시지 1 문장
- 근거 키워드 3 개
- 주력 경험 + 배분 사유

## 블록 3: DRAFT ANSWERS
문항별 본문 작성
- 각 문항 끝에:
  글자수: 약 N 자 (공백 포함) / 제한 대비 N%
- 본문에는 메타 태그 직접 출력 금지

## 블록 4: SELF-CHECK
아래 항목을 PASS/FAIL 로 점검한다.
- 문항 키워드 1:1 대응
- DATA 외 사실 생성 없음
- 행동 근거 문장 존재
- 결과 또는 직무 가치 연결 존재
- 경험 분산 충족
- 동일 조직 경험 연속 배치 없음
- 재사용 시 관점 분리 + 사유 명시
- 수치 표현 방어 가능
- 성장/학습 문항의 자기인식 + 개선 루프 존재
- 추상어 단독 사용 없음
- JD 키워드가 TYPE_B 답변에 자연스럽게 포함됨
- company_analysis 가 있으면 TYPE_A/E 에 기업 맥락 반영됨
- 글자수 기준 충족
- Q1 스포일러 최소화
- 본문 메타 태그 미출력
- 도입부 클리셰 미사용
- 마무리 추상화 금지
- 예상 꼬리질문 2~3개를 떠올려도 방어 가능
- 오탈자/회사명/직무명 정확

1 개라도 FAIL 이면 수정 후 최종본만 출력한다.

# INPUT TEMPLATE
[DATA]
- 지원 회사: {COMPANY_NAME or UNKNOWN}
- 지원 직무: {JOB_TITLE or UNKNOWN}
- 경력 단계: {ENTRY/EXPERIENCED/UNKNOWN}
- 기업 유형: {대기업/중견/스타트업/공공/공기업/UNKNOWN}
- 자소서 문항:
  1) {Q1 or UNKNOWN}
  2) {Q2 or UNKNOWN}
  3) {Q3 or UNKNOWN}
  4) {Q4 or UNKNOWN}
- 글자수 제한: {LIMITS or UNKNOWN}
- 핵심 경험:
  - 경험 A: {...}
  - 경험 B: {...}
  - 경험 C: {...}
- 보유 기술/역량 키워드: {SKILLS or UNKNOWN}
- JD(공고) 기반 직무 키워드: {JD_KEYWORDS or UNKNOWN}
- 회사/직무 조사 메모: {RESEARCH_NOTES or EMPTY}
- 톤/스타일 요구: {STYLE or DEFAULT}
[/DATA]

이제 위 [DATA] 만 사용해 4 블록을 생성하라.

# DATA
{
  "project": {
    "company_name": "새마을금고",
    "job_title": "신입직원",
    "career_stage": "ENTRY",
    "company_type": "상호금융",
    "research_notes": "2026년 상반기 새마을금고 신입직원 공개채용 자기소개서 기준. 협동조합 원리, 지역사회 밀착형 금융, 고객 신뢰, 공동체정신(성실과 책임) 강조.",
    "tone_style": "담백하고 근거 중심",
    "priority_experience_order": [
      "exp_mg_bank_parttime",
      "exp_library",
      "exp_seoul_covid_fraud",
      "exp_seongbuk"
    ],
    "questions": [
      {
        "id": "q1_mg_motivation",
        "order_no": 1,
        "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_A"
      },
      {
        "id": "q2_mg_talent",
        "order_no": 2,
        "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_UNKNOWN"
      },
      {
        "id": "q3_mg_goal",
        "order_no": 3,
        "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
        "char_limit": 600,
        "detected_type": "TYPE_G"
      }
    ]
  },
  "experiences": [
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
    }
  ],
  "knowledge_hints": [],
  "extra": {
    "question_map": [
      {
        "question_id": "q1_mg_motivation",
        "order_no": 1,
        "question_type": "TYPE_A",
        "experience_id": "exp_seoul_covid_fraud",
        "experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
        "score": 15,
        "reason": "질문 기대: 지원동기와 직무 적합성 문항이며, 질문 키워드(새마을금고에, 지원한, 이유와)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q2_mg_talent",
        "order_no": 2,
        "question_type": "TYPE_H",
        "experience_id": "exp_nps_intern",
        "experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
        "score": 13,
        "reason": "질문 기대: 고객응대 문항이며, 질문 키워드(새마을금고, 인재상, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      },
      {
        "question_id": "q3_mg_goal",
        "order_no": 3,
        "question_type": "TYPE_D",
        "experience_id": "exp_seoul_covid_crisis",
        "experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
        "score": 15,
        "reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(높은, 목표를, 설정하여)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
        "reuse_reason": null
      }
    ],
    "writer_brief": {
      "mode": "adaptive",
      "mode_label": "adaptive mode",
      "question_strategies": [
        {
          "question_id": "q1_mg_motivation",
          "question_order": 1,
          "question_type": "QuestionType.TYPE_A",
          "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
          "target_impression": "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람",
          "core_message": "서울시청 코로나19 지원팀 부정수급 적발 경험으로 QuestionType.TYPE_A 문항에서 검증 가능한 기여를 입증한다.",
          "primary_experience_id": "exp_seoul_covid_fraud",
          "primary_experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
          "supporting_experience_ids": [],
          "supporting_experience_titles": [],
          "winning_angle": "QuestionType.TYPE_A 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "forbidden_points": [
            "성장/노력/배움만 반복하는 추상 서술",
            "팀 성과만 말하고 개인 판단과 기여를 숨기는 서술"
          ],
          "required_evidence": [
            "부정수급 20건 적발, 예산 40% 절감",
            "서울시청 파견 근무 경험",
            "질문 기대: 지원동기와 직무 적합성 문항이며, 질문 키워드(새마을금고에, 지원한, 이유와)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다."
          ],
          "recommended_structure": [
            "상황/과제 1문장",
            "개인 판단과 행동 2문장",
            "수치·증빙 1문장",
            "직무 연결 1문장"
          ],
          "expected_attack_points": [
            "왜 본인 판단이었는지 설명 부족"
          ],
          "mitigation_line": "개인 판단 기준과 수치 근거를 먼저 말하고, 팀 성과는 보조로만 언급한다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 부정수급 적발의 운영 기준·증빙·재현성을 제시한다.",
          "common_cliche": "성장, 노력, 배움을 반복하며 직무 적합성을 추상적으로 주장하는 답변",
          "top001_signal": "7개 경험이 배분되지 않았습니다. 문항별 특성애 맞는 경험 선택을 검토하세요."
        },
        {
          "question_id": "q2_mg_talent",
          "question_order": 2,
          "question_type": "QuestionType.TYPE_H",
          "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
          "target_impression": "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람",
          "core_message": "국민연금공단 기초연금 수급 대상자 발굴 자동화 경험으로 QuestionType.TYPE_H 문항에서 검증 가능한 기여를 입증한다.",
          "primary_experience_id": "exp_nps_intern",
          "primary_experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
          "supporting_experience_ids": [],
          "supporting_experience_titles": [],
          "winning_angle": "QuestionType.TYPE_H 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "forbidden_points": [
            "성장/노력/배움만 반복하는 추상 서술",
            "팀 성과만 말하고 개인 판단과 기여를 숨기는 서술"
          ],
          "required_evidence": [
            "3,000페이지 2일 완수, 목표 150건 초과 달성",
            "국민연금공단 인턴 근무 경험",
            "질문 기대: 고객응대 문항이며, 질문 키워드(새마을금고, 인재상, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다."
          ],
          "recommended_structure": [
            "상황/과제 1문장",
            "개인 판단과 행동 2문장",
            "수치·증빙 1문장",
            "직무 연결 1문장"
          ],
          "expected_attack_points": [
            "왜 본인 판단이었는지 설명 부족"
          ],
          "mitigation_line": "개인 판단 기준과 수치 근거를 먼저 말하고, 팀 성과는 보조로만 언급한다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 국민연금공단 기초연금 수급 대상자 발굴 자동화의 운영 기준·증빙·재현성을 제시한다.",
          "common_cliche": "성장, 노력, 배움을 반복하며 직무 적합성을 추상적으로 주장하는 답변",
          "top001_signal": "7개 경험이 배분되지 않았습니다. 문항별 특성애 맞는 경험 선택을 검토하세요."
        },
        {
          "question_id": "q3_mg_goal",
          "question_order": 3,
          "question_type": "QuestionType.TYPE_D",
          "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
          "target_impression": "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람",
          "core_message": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습 경험으로 QuestionType.TYPE_D 문항에서 검증 가능한 기여를 입증한다.",
          "primary_experience_id": "exp_seoul_covid_crisis",
          "primary_experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
          "supporting_experience_ids": [],
          "supporting_experience_titles": [],
          "winning_angle": "QuestionType.TYPE_D 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "forbidden_points": [
            "성장/노력/배움만 반복하는 추상 서술",
            "팀 성과만 말하고 개인 판단과 기여를 숨기는 서술"
          ],
          "required_evidence": [
            "수백 통 민원 당일 수습",
            "서울시청 파견 근무 경험",
            "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(높은, 목표를, 설정하여)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다."
          ],
          "recommended_structure": [
            "상황/과제 1문장",
            "개인 판단과 행동 2문장",
            "수치·증빙 1문장",
            "직무 연결 1문장"
          ],
          "expected_attack_points": [
            "왜 본인 판단이었는지 설명 부족"
          ],
          "mitigation_line": "개인 판단 기준과 수치 근거를 먼저 말하고, 팀 성과는 보조로만 언급한다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습의 운영 기준·증빙·재현성을 제시한다.",
          "common_cliche": "성장, 노력, 배움을 반복하며 직무 적합성을 추상적으로 주장하는 답변",
          "top001_signal": "7개 경험이 배분되지 않았습니다. 문항별 특성애 맞는 경험 선택을 검토하세요."
        }
      ],
      "writer_contract": {
        "mode": "adaptive",
        "mode_label": "adaptive mode",
        "headline": "문항당 하나의 핵심 메시지와 하나의 주력 경험만 밀어붙입니다.",
        "answer_checklist": [
          "핵심 주장 1개",
          "근거 경험 1개",
          "수치/증빙 1개",
          "조직 적합 신호 1개",
          "면접 방어 취약점 1개와 완화 문장 1개"
        ],
        "decision_principles": [
          "문항마다 single best strategy를 유지한다.",
          "흔한 성장/노력/배움 클리셰보다 검증 가능한 결과와 판단 기준을 우선한다.",
          "평균 지원자 톤이 아니라 조직이 안심할 수 있는 기여 신호를 우선한다."
        ]
      }
    },
    "legacy_target_path": "profile/targets/example_target.md",
    "structure_rules_path": "analysis/structure_rules.md",
    "jd_keywords": [
      "직무기술서",
      "JD",
      "여기에",
      "공고",
      "원문을",
      "붙여넣으세요"
    ],
    "feedback_learning": {
      "artifact": "writer",
      "total_feedback": 3,
      "recent_rejection_comments": [
        "AI스러운 연결 표현이 반복됩니다: 기여하겠습니다, STAR 구조 요소가 부족합니다"
      ],
      "top_patterns": [
        {
          "pattern_id": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
          "success_rate": 0.0,
          "avg_rating": 0.0,
          "total_uses": 3
        }
      ],
      "recommended_pattern": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
      "current_pattern": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
      "question_experience_map": [
        {
          "question_id": "q1_mg_motivation",
          "question_type": "TYPE_A",
          "experience_id": "exp_seoul_covid_fraud",
          "question_order": 1
        },
        {
          "question_id": "q2_mg_talent",
          "question_type": "TYPE_H",
          "experience_id": "exp_nps_intern",
          "question_order": 2
        },
        {
          "question_id": "q3_mg_goal",
          "question_type": "TYPE_D",
          "experience_id": "exp_seoul_covid_crisis",
          "question_order": 3
        }
      ],
      "question_strategy_map": [
        {
          "question_id": "q1_mg_motivation",
          "question_order": 1,
          "question_type": "QuestionType.TYPE_A",
          "experience_id": "exp_seoul_covid_fraud",
          "core_message": "서울시청 코로나19 지원팀 부정수급 적발 경험으로 QuestionType.TYPE_A 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_A 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 부정수급 적발의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람"
        },
        {
          "question_id": "q2_mg_talent",
          "question_order": 2,
          "question_type": "QuestionType.TYPE_H",
          "experience_id": "exp_nps_intern",
          "core_message": "국민연금공단 기초연금 수급 대상자 발굴 자동화 경험으로 QuestionType.TYPE_H 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_H 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 국민연금공단 기초연금 수급 대상자 발굴 자동화의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람"
        },
        {
          "question_id": "q3_mg_goal",
          "question_order": 3,
          "question_type": "QuestionType.TYPE_D",
          "experience_id": "exp_seoul_covid_crisis",
          "core_message": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습 경험으로 QuestionType.TYPE_D 문항에서 검증 가능한 기여를 입증한다.",
          "winning_angle": "QuestionType.TYPE_D 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.",
          "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
          "differentiation_line": "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습의 운영 기준·증빙·재현성을 제시한다.",
          "tone": "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람"
        }
      ],
      "overall_success_rate": 0.0,
      "similar_context": {
        "artifact_type": "writer",
        "artifact": "writer",
        "stage": "writer",
        "company_name": "새마을금고",
        "job_title": "신입직원",
        "company_type": "상호금융",
        "question_types": [
          "TYPE_A",
          "TYPE_UNKNOWN",
          "TYPE_G"
        ]
      },
      "recent_rejection_reasons": [],
      "outcome_summary": {
        "matched_feedback_count": 3,
        "outcome_breakdown": {
          "unknown": 3
        },
        "top_rejection_reasons": []
      },
      "strategy_outcome_summary": {
        "matched_feedback_count": 3,
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
          "TYPE_A": {
            "exp_seoul_covid_conflict": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 9.0,
              "weighted_net_score": -9,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN": {
                  "total_uses": 3,
                  "pass_count": 0,
                  "fail_count": 3,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 9.0,
                  "weighted_net_score": -9,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            }
          },
          "TYPE_H": {
            "exp_mg_bank_parttime": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 9.0,
              "weighted_net_score": -9,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN": {
                  "total_uses": 3,
                  "pass_count": 0,
                  "fail_count": 3,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 9.0,
                  "weighted_net_score": -9,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            }
          },
          "TYPE_D": {
            "exp_seoul_covid_budget": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 9.0,
              "weighted_net_score": -9,
              "pass_rate": 0.0,
              "pattern_breakdown": {
                "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN": {
                  "total_uses": 3,
                  "pass_count": 0,
                  "fail_count": 3,
                  "weighted_pass_score": 0.0,
                  "weighted_fail_score": 9.0,
                  "weighted_net_score": -9,
                  "pass_rate": 0.0
                }
              },
              "top_rejection_reasons": []
            }
          }
        },
        "strategy_stats_by_question_type": {
          "QuestionType.TYPE_A": {
            "QuestionType.TYPE_A 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 9.0,
              "weighted_net_score": -9,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_H": {
            "QuestionType.TYPE_H 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 9.0,
              "weighted_net_score": -9,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_D": {
            "QuestionType.TYPE_D 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다.": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "weighted_pass_score": 0.0,
              "weighted_fail_score": 9.0,
              "weighted_net_score": -9,
              "pass_rate": 0.0
            }
          }
        },
        "differentiation_stats_by_question_type": {
          "QuestionType.TYPE_A": {
            "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_H": {
            "평균 지원자처럼 열정만 말하지 않고 새마을금고 아르바이트 - 디지털 취약 고객 응대의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "pass_rate": 0.0
            }
          },
          "QuestionType.TYPE_D": {
            "평균 지원자처럼 열정만 말하지 않고 서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감의 운영 기준·증빙·재현성을 제시한다.": {
              "total_uses": 3,
              "pass_count": 0,
              "fail_count": 3,
              "pass_rate": 0.0
            }
          }
        },
        "tone_stats_by_company_type": {
          "상호금융": {
            "기술능력, 의사소통능력를 검증 가능하게 보여주는 사람": {
              "total_uses": 9,
              "pass_count": 0,
              "fail_count": 9,
              "pass_rate": 0.0
            }
          }
        }
      },
      "insights": {
        "total_feedback": 3,
        "overall_success_rate": 0.0,
        "average_rating": 0,
        "top_patterns": [
          {
            "pattern_id": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
            "success_rate": 0.0,
            "uses": 3
          }
        ],
        "improvement_areas": [
          "패턴 'writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN'의 성공률이 낮습니다 (0%)"
        ]
      },
      "adaptation_plan": {
        "recommended_pattern": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
        "focus_actions": [
          "TYPE_A 문항은 경험 선택 재검토",
          "TYPE_H 문항은 경험 선택 재검토"
        ],
        "risky_question_types": [
          {
            "question_type": "TYPE_A",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_conflict",
                "pass_rate": 0.0,
                "weighted_net_score": -9,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_H",
            "weak_experiences": [
              {
                "experience_id": "exp_mg_bank_parttime",
                "pass_rate": 0.0,
                "weighted_net_score": -9,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_D",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_budget",
                "pass_rate": 0.0,
                "weighted_net_score": -9,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          }
        ],
        "matched_feedback_count": 3
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
          "score": 28,
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
            "직무기술서 능력단위/요소와 정합"
          ]
        },
        {
          "name": "대인관계능력",
          "score": 25,
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
            "직무기술서/NCS 명시 역량과 직접 연결",
            "TYPE_H 문항 의도와 직접 연결",
            "회사/직무 분석 신호와 정합"
          ]
        },
        {
          "name": "의사소통능력",
          "score": 25,
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
            "직무기술서 능력단위/요소와 정합",
            "TYPE_A 문항 의도와 직접 연결"
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
            "회사/직무 분석 신호와 정합"
          ]
        },
        {
          "name": "정보능력",
          "score": 17,
          "matched_keywords": [
            "저는 고객서비스능력에 가장 자신있습니다. 우체국 근로 당시 고객 대기시간을 20%단축한 경험이 있습니다. 설 연휴기간에 방문객이 급증했습니다. 방문객들의 많은 요구사항을 신속 정확하게 처리하기 위해 노력했습니다. 정중한 태도로 문제를 파악하기 위해 경청하였고 문제 해결을 위한 꼭 필요한 질문만 하여 빠르게 정보를 얻었습니다. 고객들의 요구사항에 최대한 경청하며 잘못된 문제점에 대한 빠른 인정과 신속한 시정을 하여 문제 해결을 진행했습니다. 또 도움이 필요해 보이는 상황에서 먼저 다가가 고객 서비스를 제공하며 대인관계능력을 향상시켰습니다. 빠른 일처리로 담당 업무를 끝내면 우편뿐만 아니라 다양한 업무에서 능동적인 업무 태도를 가지기 위해 노력하였고 익숙하지 않은 업무에 도전하면서 새로운 기술과 지식을 습득하였습니다. 그 결과 상황에 따라 유연하게 업무를 처리함으로써 더 유용한 구성원이 될 수 있었습니다. 적극적이고 신속한 서비스 대응에 저는 고객들로부터 좋은 평가를 받을 수 있었습니다.학창시절 영어공부에 흥미가 없었던 저는 지금도 꾸준히 공부하고 있지만 아직 만족스러운 점수를 얻지 못하고 있습니다. 그러나 기초외국어능력은 꼭 필요한 항목이고 추후 역량을 인정받기 위해서 매우 중요하기 때문에 더욱더 노력하고 있고 충분히 해결 가능한 영역이라고 생각합니다. 앞으로 언어능력을 향상시켜 국제적인 업무에 대비력을 갖춤으로써 다양한 역할을 수행할 수 있는 행정직으로서 성장하고자합니다.",
            "조직이나 단체 생활 중 다른 구성원들과 원활한 정보 공유나 소통이 이루어지지 않아 어려움을 겪었던 경험을 소개해 주십시오. 당시 구성원과의 의사소통에 있어 보다 긍정적인 변화를 이끌기 위해 어떤 노력을 기울였는지",
            "검색",
            "비교",
            "정리"
          ],
          "matched_experience_ids": [
            "exp_seoul_covid_fraud",
            "exp_seoul_covid_budget",
            "exp_nps_intern",
            "exp_nps_income_adjustment"
          ],
          "reasons": [
            "직무기술서/NCS 명시 역량과 직접 연결",
            "직무기술서 능력단위/요소와 정합",
            "TYPE_D 문항 의도와 직접 연결"
          ]
        },
        {
          "name": "디지털능력",
          "score": 16,
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
          "reasons": []
        }
      ],
      "question_alignment": [
        {
          "question_id": "q1_mg_motivation",
          "question_type": "TYPE_A",
          "recommended_competencies": [
            "의사소통능력",
            "조직이해능력"
          ],
          "recommended_ability_units": []
        },
        {
          "question_id": "q2_mg_talent",
          "question_type": "TYPE_H",
          "recommended_competencies": [
            "대인관계능력",
            "의사소통능력"
          ],
          "recommended_ability_units": []
        },
        {
          "question_id": "q3_mg_goal",
          "question_type": "TYPE_D",
          "recommended_competencies": [
            "정보능력",
            "자기관리능력"
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
        "신입직원에 바로 투입 가능한 검증형 실무자",
        "새마을금고에 맞는 근거 중심 문제해결형 지원자",
        "정량적 성과"
      ],
      "evidence_experience_ids": [
        "exp_seoul_covid_fraud",
        "exp_nps_intern",
        "exp_seoul_covid_crisis"
      ],
      "evidence_experience_titles": [
        "서울시청 코로나19 지원팀 부정수급 적발",
        "국민연금공단 기초연금 수급 대상자 발굴 자동화",
        "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습"
      ],
      "opening_message": "새마을금고의 신입직원에서 정량적 성과, 문제 해결, 협업 성과, 기술능력를 만드는 지원자입니다.",
      "risk_watchouts": [],
      "answer_anchor": "주장보다 근거를 먼저 제시하고, 마지막 문장을 입사 후 기여 방식으로 닫습니다."
    },
    "research_strategy_translation": {
      "answer_tone": "",
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
      ],
      "top001": {
        "strategic_signals": {
          "core_values": [],
          "competencies": [
            "정량적 성과",
            "문제 해결",
            "협업 성과"
          ],
          "interview_predictions": [
            "성장과정을 말씀해 주세요",
            "지원동기를 구체적으로 말씀해 주세요"
          ],
          "differentiation": [
            "귀사 새마을금고에서 필요로 하는",
            "일반 특화 역량"
          ]
        },
        "question_hooks": {
          "q1_mg_motivation": [
            "구체적인 경험을 말씀드리겠습니다",
            "핵심만 간략히 설명드리겠습니다"
          ],
          "q2_mg_talent": [
            "구체적인 경험을 말씀드리겠습니다",
            "핵심만 간략히 설명드리겠습니다"
          ],
          "q3_mg_goal": [
            "구체적인 경험을 말씀드리겠습니다",
            "핵심만 간략히 설명드리겠습니다"
          ]
        },
        "evidence_maps": [
          {
            "experience_id": "exp_seoul_covid_fraud",
            "signals": [
              "귀사에서 중시하는정량적 성과 관련 경험",
              "귀사에서 중시하는문제 해결 관련 경험"
            ],
            "proof_points": [
              "정량적 근거: 부정수급 20건 적발, 예산 40% 절감",
              "증빙: 서울시청 파견 근무 경험...",
              "개인 기여: 데이터 검증 프로세스 설계, 부동산 시세 교차 조사, ..."
            ]
          },
          {
            "experience_id": "exp_seoul_covid_crisis",
            "signals": [
              "귀사에서 중시하는정량적 성과 관련 경험",
              "귀사에서 중시하는문제 해결 관련 경험"
            ],
            "proof_points": [
              "정량적 근거: 수백 통 민원 당일 수습",
              "증빙: 서울시청 파견 근무 경험...",
              "개인 기여: 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대..."
            ]
          },
          {
            "experience_id": "exp_seoul_covid_budget",
            "signals": [
              "귀사에서 중시하는정량적 성과 관련 경험",
              "귀사에서 중시하는문제 해결 관련 경험"
            ],
            "proof_points": [
              "정량적 근거: 1억 원 예산 절감",
              "증빙: 서울시청 파견 근무 경험...",
              "개인 기여: 비교 분석 보고서 작성, 대체 방안 제안·구현..."
            ]
          },
          {
            "experience_id": "exp_seoul_covid_conflict",
            "signals": [
              "귀사에서 중시하는정량적 성과 관련 경험",
              "귀사에서 중시하는문제 해결 관련 경험"
            ],
            "proof_points": [
              "정량적 근거: 업무 효율 30% 증가",
              "증빙: 서울시청 파견 근무 경험...",
              "개인 기여: 갈등 중재, 절충안 제시, 매뉴얼 작성..."
            ]
          }
        ],
        "interview_predictions": [
          {
            "q": "조직 내 갈등을 해결한 경험은?",
            "intent": "조율 능력",
            "score_point": "논리적 해결책"
          },
          {
            "q": "목표 달성을 위해 우선순위를 조정했던 경험은?",
            "intent": "성과 지향",
            "score_point": "우선순위 판단"
          }
        ],
        "defense_strategies": [
          {
            "vulnerable_point": "본인의 역할이 모호합니다",
            "defense_script": "제가 직접 담당한 부분은 [구체적 행동]이었습니다",
            "alternatives": [
              "뿐만 아니라 다양한 요인이 복합적으로 작용했습니다",
              "다만, 제가 기여한 핵심 부분은 명시적으로 있었습니다"
            ]
          },
          {
            "vulnerable_point": "수치의 근거가 불분명합니다",
            "defense_script": "측정 기준은 [기준]이며 [비교 대상]과 비교했습니다",
            "alternatives": [
              "뿐만 아니라 다양한 요인이 복합적으로 작용했습니다",
              "다만, 제가 기여한 핵심 부분은 명시적으로 있었습니다"
            ]
          },
          {
            "vulnerable_point": "인과관계가 약합니다",
            "defense_script": "다른 요인도 있었지만, 핵심 원인은 [행동]이었다고 봅니다",
            "alternatives": [
              "뿐만 아니라 다양한 요인이 복합적으로 작용했습니다",
              "다만, 제가 기여한 핵심 부분은 명시적으로 있었습니다"
            ]
          }
        ]
      }
    },
    "outcome_dashboard": {
      "generated_at": "2026-04-06T06:37:46.250055+00:00",
      "artifact_type": "writer",
      "current_pattern": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
      "overall_success_rate": 0.0,
      "outcome_summary": {
        "matched_feedback_count": 3,
        "outcome_breakdown": {
          "unknown": 3
        },
        "top_rejection_reasons": []
      },
      "recommended_pattern": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
      "high_risk_hotspots": [
        {
          "question_type": "TYPE_A",
          "experience_id": "exp_seoul_covid_conflict",
          "weighted_net_score": -9,
          "total_uses": 3
        },
        {
          "question_type": "TYPE_H",
          "experience_id": "exp_mg_bank_parttime",
          "weighted_net_score": -9,
          "total_uses": 3
        },
        {
          "question_type": "TYPE_D",
          "experience_id": "exp_seoul_covid_budget",
          "weighted_net_score": -9,
          "total_uses": 3
        }
      ]
    },
    "kpi_dashboard": {
      "generated_at": "2026-04-06T06:37:46.251305+00:00",
      "artifact_type": "writer",
      "question_experience_match_accuracy": 0.0,
      "self_intro_follow_up_hit_rate": 0.0,
      "interview_defense_success_rate": 0.0,
      "company_signal_reuse_rate": 1.0,
      "document_pass_rate": 0.0,
      "interview_pass_rate": 0.0,
      "offer_rate": 0.0,
      "company_signal_summary": {
        "core_values": [],
        "competencies": [
          "정량적 성과",
          "문제 해결",
          "협업 성과"
        ],
        "differentiation": [
          "귀사 새마을금고에서 필요로 하는",
          "일반 특화 역량"
        ]
      },
      "writer_quality_metrics": {},
      "result_quality_metrics": {},
      "tracked_outcomes": {
        "unknown": 3
      }
    },
    "question_specific_hints": [
      {
        "question_id": "q1_mg_motivation",
        "question_order": 1,
        "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
        "question_type": "TYPE_A",
        "hints": [
          {
            "title": "하나은행 / 디자인 크리에이터 / 2024 하반기",
            "company_name": "하나은행",
            "job_title": "디자인 크리에이터",
            "signal": "하나은행 / 디자인 크리에이터 / TF-IDF score 0.241",
            "structure_summary": "하나은행 디자인 크리에이터 문항 4개 기준, 지원동기와 직무 적합성 / 협업과 조정 / 성장과 학습 루프 / 성장과 학습 루프 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_A",
              "TYPE_C",
              "TYPE_D",
              "TYPE_D"
            ],
            "applicable_question_types": [
              "TYPE_A",
              "TYPE_C",
              "TYPE_D",
              "TYPE_D"
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
              "문항유형 match (TYPE_A)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.361,
            "question_id": "q1_mg_motivation",
            "question_order": 1,
            "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
            "question_type": "TYPE_A"
          },
          {
            "title": "신용회복위원회 / 일반직 / 2025 하반기",
            "company_name": "신용회복위원회",
            "job_title": "일반직",
            "signal": "신용회복위원회 / 일반직 / TF-IDF score 0.235",
            "structure_summary": "신용회복위원회 일반직 문항 4개 기준, 지원동기와 직무 적합성 / 협업과 조정 / 상황판단과 우선순위 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_A",
              "TYPE_C",
              "TYPE_I",
              "TYPE_C"
            ],
            "applicable_question_types": [
              "TYPE_A",
              "TYPE_C",
              "TYPE_I",
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
            "match_reasons": [
              "문항유형 match (TYPE_A)"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.355,
            "question_id": "q1_mg_motivation",
            "question_order": 1,
            "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
            "question_type": "TYPE_A"
          },
          {
            "title": "한국문학번역원 / 문화예술행정 / 2024 상반기",
            "company_name": "한국문학번역원",
            "job_title": "문화예술행정",
            "signal": "한국문학번역원 / 문화예술행정 / TF-IDF score 0.071",
            "structure_summary": "한국문학번역원 문화예술행정 문항 3개 기준, 지원동기와 직무 적합성 / 입사 후 기여 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_A",
              "TYPE_E",
              "TYPE_C"
            ],
            "applicable_question_types": [
              "TYPE_A",
              "TYPE_E",
              "TYPE_C"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
              "성장 서사",
              "고객 관점"
            ],
            "structure_signals": {
              "has_star": true,
              "has_metrics": false,
              "warns_against_copying": true
            },
            "match_reasons": [
              "문항유형 match (TYPE_A)"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.191,
            "question_id": "q1_mg_motivation",
            "question_order": 1,
            "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
            "question_type": "TYPE_A"
          }
        ]
      },
      {
        "question_id": "q2_mg_talent",
        "question_order": 2,
        "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
        "question_type": "TYPE_UNKNOWN",
        "hints": [
          {
            "title": "국민연금공단 / 체험형 청년인턴 / 2024 하반기",
            "company_name": "국민연금공단",
            "job_title": "체험형 청년인턴",
            "signal": "국민연금공단 / 체험형 청년인턴 / TF-IDF score 0.177",
            "structure_summary": "국민연금공단 체험형 청년인턴 문항 2개 기준, 핵심 역량 / 분류 불가 (확인 필요) 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_B",
              "TYPE_UNKNOWN"
            ],
            "applicable_question_types": [
              "TYPE_B",
              "TYPE_UNKNOWN"
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
              "문항유형 match (TYPE_UNKNOWN)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.297,
            "question_id": "q2_mg_talent",
            "question_order": 2,
            "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
            "question_type": "TYPE_UNKNOWN"
          },
          {
            "title": "국민연금공단 / 일반 / 2024 하반기",
            "company_name": "국민연금공단",
            "job_title": "일반",
            "signal": "국민연금공단 / 일반 / TF-IDF score 0.135",
            "structure_summary": "국민연금공단 일반 문항 2개 기준, 핵심 역량 / 분류 불가 (확인 필요) 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_B",
              "TYPE_UNKNOWN"
            ],
            "applicable_question_types": [
              "TYPE_B",
              "TYPE_UNKNOWN"
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
              "문항유형 match (TYPE_UNKNOWN)"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.255,
            "question_id": "q2_mg_talent",
            "question_order": 2,
            "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
            "question_type": "TYPE_UNKNOWN"
          },
          {
            "title": "한국자산관리공사 / 5급_금융일반_경영 / 2025 상반기",
            "company_name": "한국자산관리공사",
            "job_title": "5급_금융일반_경영",
            "signal": "한국자산관리공사 / 5급_금융일반_경영 / TF-IDF score 0.240",
            "structure_summary": "한국자산관리공사 5급_금융일반_경영 문항 4개 기준, 실패와 복기 / 협업과 조정 / 핵심 역량 / 협업과 조정 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_G",
              "TYPE_C",
              "TYPE_B",
              "TYPE_C"
            ],
            "applicable_question_types": [
              "TYPE_G",
              "TYPE_C",
              "TYPE_B",
              "TYPE_C"
            ],
            "evidence_focus": [
              "STAR 구조",
              "정량 결과",
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
            "combined_score": 0.24,
            "question_id": "q2_mg_talent",
            "question_order": 2,
            "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
            "question_type": "TYPE_UNKNOWN"
          }
        ]
      },
      {
        "question_id": "q3_mg_goal",
        "question_order": 3,
        "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
        "question_type": "TYPE_G",
        "hints": [
          {
            "title": "한국법무보호복지공단 / 일반직 / 2024 하반기",
            "company_name": "한국법무보호복지공단",
            "job_title": "일반직",
            "signal": "한국법무보호복지공단 / 일반직 / TF-IDF score 0.195",
            "structure_summary": "한국법무보호복지공단 일반직 문항 4개 기준, 핵심 역량 / 협업과 조정 / 실패와 복기 / 지원동기와 직무 적합성 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_B",
              "TYPE_C",
              "TYPE_G",
              "TYPE_A"
            ],
            "applicable_question_types": [
              "TYPE_B",
              "TYPE_C",
              "TYPE_G",
              "TYPE_A"
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
              "문항유형 match (TYPE_G)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.315,
            "question_id": "q3_mg_goal",
            "question_order": 3,
            "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
            "question_type": "TYPE_G"
          },
          {
            "title": "국민건강보험공단 / 체험형 청년인턴 / 2025 상반기",
            "company_name": "국민건강보험공단",
            "job_title": "체험형 청년인턴",
            "signal": "국민건강보험공단 / 체험형 청년인턴 / TF-IDF score 0.313",
            "structure_summary": "국민건강보험공단 체험형 청년인턴 문항 4개 기준, 협업과 조정 / 원칙과 신뢰 / 협업과 조정 / 핵심 역량 중심 구조",
            "caution": "표현 복제 금지. 구조만 참고.",
            "question_types": [
              "TYPE_C",
              "TYPE_F",
              "TYPE_C",
              "TYPE_B"
            ],
            "applicable_question_types": [
              "TYPE_C",
              "TYPE_F",
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
              "has_metrics": true,
              "warns_against_copying": true
            },
            "match_reasons": [
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.313,
            "question_id": "q3_mg_goal",
            "question_order": 3,
            "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
            "question_type": "TYPE_G"
          },
          {
            "title": "한국사회적기업진흥원 / 행정 / 2024 상반기",
            "company_name": "한국사회적기업진흥원",
            "job_title": "행정",
            "signal": "한국사회적기업진흥원 / 행정 / TF-IDF score 0.186",
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
              "문항유형 match (TYPE_G)",
              "정량 결과 포함"
            ],
            "semantic_score": 0.0,
            "vector_score": 0.0,
            "combined_score": 0.306,
            "question_id": "q3_mg_goal",
            "question_order": 3,
            "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
            "question_type": "TYPE_G"
          }
        ]
      }
    ],
    "application_strategy": {
      "company_name": "새마을금고",
      "job_title": "신입직원",
      "company_type": "상호금융",
      "updated_at": "2026-04-06T06:37:46.245965+00:00",
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
        "opening_hook": "새마을금고의 신입직원에서 정량적 성과, 문제 해결, 협업 성과, 기술능력를 만드는 지원자입니다.",
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
            "content": "귀사의 새마을금고 방향성과 직접 연결되는 경험입니다",
            "score": 0.7
          }
        ],
        "top001_versions": {
          "elevator": "신입직원에서 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악... 경험을 바탕으로 핵심 성과를 만들고자 합니다",
          "30s": "저는 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 그 결과 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이를 신입직원에 기여할 수 있는 역량으로 발전시키고 싶습니다",
          "60s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 새마을금고에서 발전시키고 싶습니다",
          "90s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 새마을금고에서 발전시키고 싶습니다 그 과정에서 제가 중점적으로 맡은 부분은 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대이었습니다 구체적으로 수백 통 민원 당일 수습의 성과를 냈습니다 이 경험을 새마을금고의 신입직원에서 실질적 기여로 연결하고 싶습니다"
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
            "opening_hook": "새마을금고의 신입직원에서 정량적 성과, 문제 해결, 협업 성과, 기술능력를 만드는 지원자입니다.",
            "thirty_second_frame": [
              "현재 지원 직무와 가장 직접 연결되는 경험 1개를 먼저 말한다.",
              "핵심 경험: 서울시청 코로나19 지원팀 부정수급 적발, 국민연금공단 기초연금 수급 대상자 발굴 자동화",
              "마무리는 새마을금고에서의 첫 기여 포인트로 닫는다."
            ],
            "sixty_second_frame": [
              "지원 직무와 연결되는 문제 인식",
              "본인 행동과 판단 기준",
              "정량 또는 정성 결과",
              "입사 후 적용 계획"
            ],
            "focus_keywords": [
              "정량적 성과",
              "문제 해결",
              "협업 성과",
              "기술능력"
            ],
            "banned_patterns": [
              "검증 불가 수치 확대",
              "회사 정보 복붙형 지원동기",
              "팀 성과를 개인 성과처럼 포장"
            ],
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
                "content": "귀사의 새마을금고 방향성과 직접 연결되는 경험입니다",
                "score": 0.7
              }
            ],
            "top001_versions": {
              "elevator": "신입직원에서 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악... 경험을 바탕으로 핵심 성과를 만들고자 합니다",
              "30s": "저는 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 그 결과 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이를 신입직원에 기여할 수 있는 역량으로 발전시키고 싶습니다",
              "60s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 새마을금고에서 발전시키고 싶습니다",
              "90s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 새마을금고에서 발전시키고 싶습니다 그 과정에서 제가 중점적으로 맡은 부분은 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대이었습니다 구체적으로 수백 통 민원 당일 수습의 성과를 냈습니다 이 경험을 새마을금고의 신입직원에서 실질적 기여로 연결하고 싶습니다"
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
            "allocation_issues": [],
            "suggestions": [
              "7개 경험이 배분되지 않았습니다. 문항별 특성애 맞는 경험 선택을 검토하세요."
            ],
            "coverage_report": {
              "total_experiences": 10,
              "experiences_in_use": 3,
              "l3_experiences": 5,
              "verified_experiences": 10,
              "total_questions": 3,
              "allocated_questions": 3,
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
              "question_id": "q1_mg_motivation",
              "order_no": 1,
              "question_type": "TYPE_A",
              "experience_id": "exp_seoul_covid_fraud",
              "experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
              "score": 15,
              "reason": "질문 기대: 지원동기와 직무 적합성 문항이며, 질문 키워드(새마을금고에, 지원한, 이유와)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            },
            {
              "question_id": "q2_mg_talent",
              "order_no": 2,
              "question_type": "TYPE_H",
              "experience_id": "exp_nps_intern",
              "experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
              "score": 13,
              "reason": "질문 기대: 고객응대 문항이며, 질문 키워드(새마을금고, 인재상, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            },
            {
              "question_id": "q3_mg_goal",
              "order_no": 3,
              "question_type": "TYPE_D",
              "experience_id": "exp_seoul_covid_crisis",
              "experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
              "score": 15,
              "reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(높은, 목표를, 설정하여)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "reuse_reason": null
            }
          ],
          "experience_competition": [
            {
              "question_id": "q1_mg_motivation",
              "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
              "question_type": "TYPE_A",
              "primary_experience_id": "exp_seoul_covid_fraud",
              "primary_experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
              "primary_reason": "질문 기대: 지원동기와 직무 적합성 문항이며, 질문 키워드(새마을금고에, 지원한, 이유와)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_seoul_covid_budget",
              "secondary_experience_title": "서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            },
            {
              "question_id": "q2_mg_talent",
              "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
              "question_type": "TYPE_H",
              "primary_experience_id": "exp_nps_intern",
              "primary_experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
              "primary_reason": "질문 기대: 고객응대 문항이며, 질문 키워드(새마을금고, 인재상, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_seoul_covid_conflict",
              "secondary_experience_title": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            },
            {
              "question_id": "q3_mg_goal",
              "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
              "question_type": "TYPE_D",
              "primary_experience_id": "exp_seoul_covid_crisis",
              "primary_experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
              "primary_reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(높은, 목표를, 설정하여)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
              "secondary_experience_id": "exp_nps_income_adjustment",
              "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
              "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
              "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
            }
          ],
          "writer_differentiation": null,
          "adaptive_strategy": {
            "company_profile": "상호금융",
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
            "strategic_signals": {
              "core_values": [],
              "competencies": [
                "정량적 성과",
                "문제 해결",
                "협업 성과"
              ],
              "interview_predictions": [
                "성장과정을 말씀해 주세요",
                "지원동기를 구체적으로 말씀해 주세요"
              ],
              "differentiation": [
                "귀사 새마을금고에서 필요로 하는",
                "일반 특화 역량"
              ]
            },
            "question_hooks": {
              "q1_mg_motivation": [
                "구체적인 경험을 말씀드리겠습니다",
                "핵심만 간략히 설명드리겠습니다"
              ],
              "q2_mg_talent": [
                "구체적인 경험을 말씀드리겠습니다",
                "핵심만 간략히 설명드리겠습니다"
              ],
              "q3_mg_goal": [
                "구체적인 경험을 말씀드리겠습니다",
                "핵심만 간략히 설명드리겠습니다"
              ]
            },
            "evidence_maps": [
              {
                "experience_id": "exp_seoul_covid_fraud",
                "signals": [
                  "귀사에서 중시하는정량적 성과 관련 경험",
                  "귀사에서 중시하는문제 해결 관련 경험"
                ],
                "proof_points": [
                  "정량적 근거: 부정수급 20건 적발, 예산 40% 절감",
                  "증빙: 서울시청 파견 근무 경험...",
                  "개인 기여: 데이터 검증 프로세스 설계, 부동산 시세 교차 조사, ..."
                ]
              },
              {
                "experience_id": "exp_seoul_covid_crisis",
                "signals": [
                  "귀사에서 중시하는정량적 성과 관련 경험",
                  "귀사에서 중시하는문제 해결 관련 경험"
                ],
                "proof_points": [
                  "정량적 근거: 수백 통 민원 당일 수습",
                  "증빙: 서울시청 파견 근무 경험...",
                  "개인 기여: 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대..."
                ]
              },
              {
                "experience_id": "exp_seoul_covid_budget",
                "signals": [
                  "귀사에서 중시하는정량적 성과 관련 경험",
                  "귀사에서 중시하는문제 해결 관련 경험"
                ],
                "proof_points": [
                  "정량적 근거: 1억 원 예산 절감",
                  "증빙: 서울시청 파견 근무 경험...",
                  "개인 기여: 비교 분석 보고서 작성, 대체 방안 제안·구현..."
                ]
              },
              {
                "experience_id": "exp_seoul_covid_conflict",
                "signals": [
                  "귀사에서 중시하는정량적 성과 관련 경험",
                  "귀사에서 중시하는문제 해결 관련 경험"
                ],
                "proof_points": [
                  "정량적 근거: 업무 효율 30% 증가",
                  "증빙: 서울시청 파견 근무 경험...",
                  "개인 기여: 갈등 중재, 절충안 제시, 매뉴얼 작성..."
                ]
              }
            ],
            "interview_predictions": [
              {
                "q": "조직 내 갈등을 해결한 경험은?",
                "intent": "조율 능력",
                "score_point": "논리적 해결책"
              },
              {
                "q": "목표 달성을 위해 우선순위를 조정했던 경험은?",
                "intent": "성과 지향",
                "score_point": "우선순위 판단"
              }
            ],
            "defense_strategies": [
              {
                "vulnerable_point": "본인의 역할이 모호합니다",
                "defense_script": "제가 직접 담당한 부분은 [구체적 행동]이었습니다",
                "alternatives": [
                  "뿐만 아니라 다양한 요인이 복합적으로 작용했습니다",
                  "다만, 제가 기여한 핵심 부분은 명시적으로 있었습니다"
                ]
              },
              {
                "vulnerable_point": "수치의 근거가 불분명합니다",
                "defense_script": "측정 기준은 [기준]이며 [비교 대상]과 비교했습니다",
                "alternatives": [
                  "뿐만 아니라 다양한 요인이 복합적으로 작용했습니다",
                  "다만, 제가 기여한 핵심 부분은 명시적으로 있었습니다"
                ]
              },
              {
                "vulnerable_point": "인과관계가 약합니다",
                "defense_script": "다른 요인도 있었지만, 핵심 원인은 [행동]이었다고 봅니다",
                "alternatives": [
                  "뿐만 아니라 다양한 요인이 복합적으로 작용했습니다",
                  "다만, 제가 기여한 핵심 부분은 명시적으로 있었습니다"
                ]
              }
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
            "generated_at": "2026-04-05T11:39:57.950891+00:00",
            "company_name": "새마을금고",
            "job_title": "신입직원",
            "pressure_points": [
              "조직 내 갈등을 해결한 경험은?",
              "목표 달성을 위해 우선순위를 조정했던 경험은?"
            ],
            "rows": []
          },
          "adaptive_strategy": {
            "company_profile": "상호금융",
            "interview_mode": "실행력 검증 + 모호성 대응",
            "writer_logic": "가설-실험-학습 구조를 강조하고, 제한된 자원에서의 판단을 드러냅니다.",
            "coaching_mode": "핵심 메시지를 먼저 세우고 경험 근거를 뒤에서 지지하는 방식으로 훈련합니다.",
            "career_stage": "ENTRY"
          },
          "feedback_adaptation_plan": {
            "recommended_pattern": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
            "focus_actions": [
              "TYPE_A 문항은 경험 선택 재검토",
              "TYPE_H 문항은 경험 선택 재검토"
            ],
            "risky_question_types": [
              {
                "question_type": "TYPE_A",
                "weak_experiences": [
                  {
                    "experience_id": "exp_seoul_covid_conflict",
                    "pass_rate": 0.0,
                    "weighted_net_score": -6,
                    "top_rejection_reasons": []
                  }
                ],
                "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
              },
              {
                "question_type": "TYPE_H",
                "weak_experiences": [
                  {
                    "experience_id": "exp_mg_bank_parttime",
                    "pass_rate": 0.0,
                    "weighted_net_score": -6,
                    "top_rejection_reasons": []
                  }
                ],
                "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
              },
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
              }
            ],
            "matched_feedback_count": 2
          }
        }
      },
      "coach_recommendations": [
        "7개 경험이 배분되지 않았습니다. 문항별 특성애 맞는 경험 선택을 검토하세요."
      ],
      "experience_coverage": {
        "total_experiences": 10,
        "experiences_in_use": 3,
        "l3_experiences": 5,
        "verified_experiences": 10,
        "total_questions": 3,
        "allocated_questions": 3,
        "uncovered_question_count": 0,
        "coverage_rate": 1.0
      },
      "experience_competition": [
        {
          "question_id": "q1_mg_motivation",
          "question_text": "새마을금고에 지원한 이유와 새마을금고가 지원자를 채용해야 하는 이유를 기술해 주십시오.",
          "question_type": "TYPE_A",
          "primary_experience_id": "exp_seoul_covid_fraud",
          "primary_experience_title": "서울시청 코로나19 지원팀 부정수급 적발",
          "primary_reason": "질문 기대: 지원동기와 직무 적합성 문항이며, 질문 키워드(새마을금고에, 지원한, 이유와)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(부정수급 20건 적발, 예산 40% 절감) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_seoul_covid_budget",
          "secondary_experience_title": "서울시청 코로나19 지원팀 외주 시스템 도입 반려 - 1억 예산 절감",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        },
        {
          "question_id": "q2_mg_talent",
          "question_text": "새마을금고 인재상 중 본인이 가장 부합하는 요소를 고르고 그 이유를 구체적인 경험과 함께 기술해 주십시오.",
          "question_type": "TYPE_H",
          "primary_experience_id": "exp_nps_intern",
          "primary_experience_title": "국민연금공단 기초연금 수급 대상자 발굴 자동화",
          "primary_reason": "질문 기대: 고객응대 문항이며, 질문 키워드(새마을금고, 인재상, 본인이)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(3,000페이지 2일 완수, 목표 150건 초과 달성) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_seoul_covid_conflict",
          "secondary_experience_title": "서울시청 코로나19 지원팀 세대 간 업무 방식 갈등 중재",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        },
        {
          "question_id": "q3_mg_goal",
          "question_text": "높은 목표를 설정하여 성공 또는 실패한 경험과 그 과정에서 얻은 교훈을 기술해 주십시오.",
          "question_type": "TYPE_D",
          "primary_experience_id": "exp_seoul_covid_crisis",
          "primary_experience_title": "서울시청 코로나19 지원팀 위기 대응 - 군의관 배정 혼란 수습",
          "primary_reason": "질문 기대: 성장과 학습 루프 문항이며, 질문 키워드(높은, 목표를, 설정하여)와 가장 직접적으로 맞닿아 있습니다.\n이 경험의 강점: 정량 근거(수백 통 민원 당일 수습) / 면접에서 다시 꺼낼 증빙 문장 보유 / 개인 기여를 분리해 설명 가능.\n면접관 꼬리질문: 왜 다른 경험보다 이 사례가 직무 적합성을 잘 증명하는지를 30초 안에 방어할 준비가 필요합니다.",
          "secondary_experience_id": "exp_nps_income_adjustment",
          "secondary_experience_title": "국민연금공단 기준소득월액 변경 특례 민원 응대",
          "secondary_reason": "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다.",
          "exclusion_reason": "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        }
      ],
      "adaptive_strategy_layer": {
        "company_profile": "상호금융",
        "interview_mode": "실행력 검증 + 모호성 대응",
        "writer_logic": "가설-실험-학습 구조를 강조하고, 제한된 자원에서의 판단을 드러냅니다.",
        "coaching_mode": "핵심 메시지를 먼저 세우고 경험 근거를 뒤에서 지지하는 방식으로 훈련합니다.",
        "career_stage": "ENTRY"
      },
      "company_signal_summary": {
        "core_values": [],
        "competencies": [
          "정량적 성과",
          "문제 해결",
          "협업 성과"
        ],
        "differentiation": [
          "귀사 새마을금고에서 필요로 하는",
          "일반 특화 역량"
        ]
      },
      "question_strategy": {
        "q1_mg_motivation": [
          "구체적인 경험을 말씀드리겠습니다",
          "핵심만 간략히 설명드리겠습니다"
        ],
        "q2_mg_talent": [
          "구체적인 경험을 말씀드리겠습니다",
          "핵심만 간략히 설명드리겠습니다"
        ],
        "q3_mg_goal": [
          "구체적인 경험을 말씀드리겠습니다",
          "핵심만 간략히 설명드리겠습니다"
        ]
      },
      "interview_pressure_points": [
        "조직 내 갈등을 해결한 경험은?",
        "목표 달성을 위해 우선순위를 조정했던 경험은?"
      ],
      "writer_differentiation": {
        "generated_at": "2026-04-05T11:39:57.950891+00:00",
        "company_name": "새마을금고",
        "job_title": "신입직원",
        "pressure_points": [
          "조직 내 갈등을 해결한 경험은?",
          "목표 달성을 위해 우선순위를 조정했던 경험은?"
        ],
        "rows": []
      },
      "feedback_adaptation_plan": {
        "recommended_pattern": "writer|상호금융|TYPE_A-TYPE_G-TYPE_UNKNOWN",
        "focus_actions": [
          "TYPE_A 문항은 경험 선택 재검토",
          "TYPE_H 문항은 경험 선택 재검토"
        ],
        "risky_question_types": [
          {
            "question_type": "TYPE_A",
            "weak_experiences": [
              {
                "experience_id": "exp_seoul_covid_conflict",
                "pass_rate": 0.0,
                "weighted_net_score": -6,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
          {
            "question_type": "TYPE_H",
            "weak_experiences": [
              {
                "experience_id": "exp_mg_bank_parttime",
                "pass_rate": 0.0,
                "weighted_net_score": -6,
                "top_rejection_reasons": []
              }
            ],
            "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요."
          },
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
          }
        ],
        "matched_feedback_count": 2
      }
    },
    "company_analysis": {
      "company_name": "새마을금고",
      "company_type": "상호금융",
      "industry": "일반",
      "core_values": [],
      "culture_keywords": [],
      "recent_news": [],
      "interview_style": "formal",
      "success_patterns": [
        "star_structure",
        "quantified_result",
        "problem_solving",
        "collaboration",
        "growth_story"
      ],
      "preferred_evidence_types": [
        "정량적 성과",
        "문제 해결",
        "협업 성과"
      ],
      "tone_guide": "명확하고 구체적인 표현. 근거 중심.",
      "role_industry_strategy": {
        "target_role": "신입직원",
        "target_industry": "일반",
        "company_type": "상호금융",
        "question_types": [
          "TYPE_A",
          "TYPE_UNKNOWN",
          "TYPE_G"
        ],
        "writer_focus": [
          "지원동기와 직무 적합성을 사용자 경험으로 연결한다.",
          "문항별로 한 경험의 역할·행동·성과를 분리해 제시한다.",
          "입사 후 포부는 실행 가능한 첫 기여 단위까지 내려쓴다."
        ],
        "interview_focus": [
          "수치/기준/비교 근거를 30초 안에 다시 설명할 수 있게 준비한다.",
          "팀 성과와 개인 기여를 구분해서 답한다.",
          "단일 출처 정보는 확정 표현 대신 검증 예정 표현으로 낮춘다.",
          "수치 검증 관점의 압박 질문을 대비한다.",
          "개인 기여 검증 관점의 압박 질문을 대비한다.",
          "대안 비교 관점의 압박 질문을 대비한다."
        ],
        "evidence_priority": [
          "정량적 성과",
          "문제 해결",
          "협업 성과",
          "정량 성과",
          "직무 연관 행동"
        ],
        "tone_rules": [
          "담백하고 근거 중심으로 답변합니다.",
          "일반 산업 맥락을 과장 없이 연결합니다.",
          "신입직원 직무에서 바로 쓰일 행동/성과 중심으로 정리합니다."
        ],
        "banned_patterns": [
          "검증 불가 수치 확대",
          "회사 정보 복붙형 지원동기",
          "팀 성과를 개인 성과처럼 포장"
        ],
        "interview_pressure_themes": [
          "수치 검증",
          "개인 기여 검증",
          "대안 비교",
          "일반 도메인 이해도",
          "지원동기 진정성"
        ],
        "committee_personas": [
          {
            "id": "chair",
            "name": "위원장",
            "role": "전체 논리와 답변 일관성 점검",
            "focus": [
              "지원동기 진정성",
              "논리 일관성",
              "직무 적합성"
            ],
            "tone": "정중하지만 냉정함"
          },
          {
            "id": "domain",
            "name": "실무위원",
            "role": "신입직원 실무 적합성 검증",
            "focus": [
              "수치 검증",
              "개인 기여 검증",
              "대안 비교"
            ],
            "tone": "구체 사례를 집요하게 확인함"
          },
          {
            "id": "risk",
            "name": "리스크위원",
            "role": "과장, 단일 출처 주장, 실패 대응 검증",
            "focus": [
              "개인 기여 검증",
              "대안 비교",
              "실패 복구"
            ],
            "tone": "반례와 허점을 먼저 찾음"
          },
          {
            "id": "culture",
            "name": "조직적합성위원",
            "role": "협업 방식과 조직 적합성 검증",
            "focus": [
              "협업 방식",
              "조직 적응",
              "커뮤니케이션"
            ],
            "tone": "차분하지만 비교 질문이 많음"
          }
        ],
        "single_source_risks": [],
        "question_map_signals": []
      },
      "success_case_stats": {
        "match_case_count": 1,
        "exact_company_match_count": 0,
        "job_match_count": 1,
        "pattern_distribution": {
          "star_structure": 1,
          "quantified_result": 1,
          "problem_solving": 1,
          "collaboration": 1,
          "growth_story": 1,
          "customer_focus": 1
        },
        "quantified_result_rate": 1.0,
        "star_structure_rate": 1.0,
        "customer_focus_rate": 1.0,
        "problem_solving_rate": 1.0,
        "collaboration_rate": 1.0,
        "recommended_writing_focus": [
          "정량 결과를 포함한 문장을 우선 배치",
          "상황-행동-결과가 분리된 STAR 구조 유지",
          "고객/이용자 관점의 가치 연결 강조",
          "문제 원인과 해결 판단 기준을 구체화"
        ]
      },
      "similar_case_titles": [
        "광주광역시도시공사 / 2021년 신입직원(정규직), 경영 / 2021 하반기"
      ],
      "discouraged_phrases": []
    },
    "self_intro_pack": {
      "opening_hook": "새마을금고의 신입직원에서 정량적 성과, 문제 해결, 협업 성과, 기술능력를 만드는 지원자입니다.",
      "thirty_second_frame": [
        "현재 지원 직무와 가장 직접 연결되는 경험 1개를 먼저 말한다.",
        "핵심 경험: 서울시청 코로나19 지원팀 부정수급 적발, 국민연금공단 기초연금 수급 대상자 발굴 자동화",
        "마무리는 새마을금고에서의 첫 기여 포인트로 닫는다."
      ],
      "sixty_second_frame": [
        "지원 직무와 연결되는 문제 인식",
        "본인 행동과 판단 기준",
        "정량 또는 정성 결과",
        "입사 후 적용 계획"
      ],
      "focus_keywords": [
        "정량적 성과",
        "문제 해결",
        "협업 성과",
        "기술능력"
      ],
      "banned_patterns": [
        "검증 불가 수치 확대",
        "회사 정보 복붙형 지원동기",
        "팀 성과를 개인 성과처럼 포장"
      ],
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
          "content": "귀사의 새마을금고 방향성과 직접 연결되는 경험입니다",
          "score": 0.7
        }
      ],
      "top001_versions": {
        "elevator": "신입직원에서 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악... 경험을 바탕으로 핵심 성과를 만들고자 합니다",
        "30s": "저는 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 그 결과 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이를 신입직원에 기여할 수 있는 역량으로 발전시키고 싶습니다",
        "60s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 새마을금고에서 발전시키고 싶습니다",
        "90s": "저는 담당 사무관 휴가 중 중수본이 서울시청과 사전 협의 없이 군의관 수백 명을 병원에 일방 배정하는 공문 발송. 병원과 군의관으로부터 수백 통 민원 전화 폭주. 상황에서 실무 담당자가 부재한 위기 상황에서 혼란 수습 및 대응 매뉴얼 마련를 해결해야 했습니다 그때 중수본 공문 즉시 분석하여 군의관 배정 기준·절차 파악. 병원 관계자용 배정 양식·지침과 군의관용 대응 매뉴얼(위치, 연락처, 업무 등) 자체 제작. 이메일로 신속 배포. 원론적 답변 필요한 문의는 직접 응대, 세부 사항은 담당 병원 연결. 결과적으로 당일 발생한 대규모 혼란 성공적으로 통제, 불만 최소화 이러한 경험을 새마을금고에서 발전시키고 싶습니다 그 과정에서 제가 중점적으로 맡은 부분은 공문 분석, 매뉴얼 자체 제작·배포, 민원 응대이었습니다 구체적으로 수백 통 민원 당일 수습의 성과를 냈습니다 이 경험을 새마을금고의 신입직원에서 실질적 기여로 연결하고 싶습니다"
      },
      "top001_expected_follow_ups": [
        "그 결과는 어떻게 측정하거나 확인하셨나요?",
        "그 경험에서 가장 어려웠던 부분은 무엇이었나요?"
      ]
    }
  }
}
