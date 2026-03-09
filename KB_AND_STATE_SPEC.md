# Knowledge Base And State Spec

## 1. Why the knowledge base must be split

Reference essays should not be fed directly into writer prompts.

Use two stores:

### Raw sample store
- full original source
- used for traceability and offline analysis

### Pattern knowledge base
- compact extracted metadata
- used for retrieval during coach/writer/interview

This reduces:

- prompt bloat
- accidental copying
- retrieval noise

## 2. Source categories

Supported source types:

- `local_markdown`
- `local_text`
- `local_csv_row`
- `user_url_public`
- `manual_note`

Not supported:

- login-gated scraping
- stealth crawling
- anti-bot bypass

## 3. CSV ingestion policy

For datasets like `linkareer_results.csv`, the ingest pipeline should:

1. preserve the original row in raw storage
2. strip boilerplate and marketing lines
3. split the title into company, role, season if possible
4. detect question blocks
5. extract question-type candidates
6. compute pattern signals
7. emit a compact KB entry

## 4. Raw row schema

```json
{
  "id": "src_0001",
  "source_type": "local_csv_row",
  "title": "코레일네트웍스 / 청년 체험형 인턴 / 2025 하반기",
  "url": "https://linkareer.com/cover-letter/35164",
  "raw_text": "...full body...",
  "cleaned_text": "...boilerplate removed...",
  "meta": {
    "company_name": "코레일네트웍스",
    "job_title": "청년 체험형 인턴",
    "season": "2025 하반기",
    "spec_text": "...",
    "question_count": 4
  }
}
```

## 5. Pattern KB schema

```json
{
  "id": "kb_0001",
  "source_id": "src_0001",
  "title": "코레일네트웍스 / 청년 체험형 인턴 / 2025 하반기",
  "company_name": "코레일네트웍스",
  "job_title": "청년 체험형 인턴",
  "season": "2025 하반기",
  "question_types": ["TYPE_A", "TYPE_C", "TYPE_B", "TYPE_E"],
  "structure_summary": "성취/원칙/협업/직무역량 순서의 공공 인턴형 구조",
  "structure_signals": {
    "has_star": true,
    "has_metrics": true,
    "warns_against_copying": true
  },
  "spec_keywords": ["공공기관", "인턴", "고객응대", "행정"],
  "retrieval_terms": ["코레일", "철도", "청년 체험형 인턴", "공공기관", "고객응대"],
  "caution": "표현 복제 금지. 구조만 참고.",
  "source_url": "https://linkareer.com/cover-letter/35164"
}
```

## 6. State files for Codex CLI

The first implementation does not need a DB. Use JSON files.

Recommended files:

```text
state/
  profile.json
  experiences.json
  project.json
  knowledge_sources.json
  artifacts.json
```

## 7. Profile schema

```json
{
  "display_name": "",
  "career_stage": "ENTRY",
  "target_company_types": ["공공"],
  "target_roles": ["사무"],
  "style_preference": "담백하고 근거 중심"
}
```

## 8. Experience schema

```json
[
  {
    "id": "exp_001",
    "title": "통계청 인턴",
    "organization": "통계청",
    "period_start": "2024-01",
    "period_end": "2024-03",
    "situation": "",
    "task": "",
    "action": "",
    "result": "",
    "personal_contribution": "",
    "metrics": "",
    "evidence_text": "",
    "evidence_level": "L3",
    "tags": ["데이터", "문제해결"],
    "verification_status": "verified"
  }
]
```

## 9. Project schema

```json
{
  "company_name": "",
  "job_title": "",
  "career_stage": "ENTRY",
  "company_type": "공공",
  "research_notes": "",
  "tone_style": "담백하고 근거 중심",
  "priority_experience_order": [],
  "questions": [
    {
      "id": "q1",
      "order_no": 1,
      "question_text": "",
      "char_limit": 700,
      "detected_type": "TYPE_A"
    }
  ]
}
```

## 10. Artifact schema

```json
[
  {
    "id": "artifact_001",
    "artifact_type": "WRITER",
    "accepted": true,
    "input_snapshot": {},
    "output_path": "artifacts/writer.md",
    "raw_output_path": "runs/20260309_132000/raw_writer.md",
    "validation": {
      "passed": true,
      "missing": [],
      "out_of_order": []
    },
    "created_at": "2026-03-09T13:20:00Z"
  }
]
```

## 11. Retrieval policy

When the writer stage runs:

- query by company alias
- query by job alias
- query by question type
- query by extracted question keywords
- return top 3 to 5 KB entries
- pass only compact summaries into the prompt

Never pass large raw essays by default.

## 12. Cleaning rules for essay corpora

Recommended cleaning steps:

- remove platform marketing lines
- remove generic CTA blocks
- normalize repeated blank lines
- preserve question numbering
- preserve company/job naming
- mark parsing confidence when title split fails

## 13. Safety rules

- preserve source URL
- preserve raw source for auditability
- writer stage receives summaries, not raw essays
- any distinctive wording reuse should be treated as a failure risk
