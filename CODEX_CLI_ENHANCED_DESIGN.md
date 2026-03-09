# Codex CLI Enhanced Design

This document upgrades the initial `resume-agent` scaffold using the architecture observed in `selfintro_mvp`.

## 1. What the analyzed MVP already proves

The analyzed project is not just a prompt wrapper. It already has a concrete architecture:

- deterministic domain engines for coaching, writing, interview prep
- explicit stage commands such as `/setup`, `/crawl-base`, `/my-profile`, `/my-gaps`, `/coach`, `/writer`, `/interview`, `/export`
- structured persistence through Prisma models
- knowledge ingestion and hint ranking
- allocation logic that scores experiences by evidence level, verification status, question fit, and reuse penalty
- output contracts that validate section headings and block order
- optional LLM adapter, with a deterministic fallback as the default execution path

That means the Codex CLI version should not be designed as "LLM first". It should be designed as "pipeline first, LLM assisted".

## 2. Design direction for Codex CLI

The Codex CLI version should be a local orchestration system with three layers:

1. Deterministic core
   - question classification
   - experience scoring and allocation
   - gap analysis
   - no-invention checks
   - output contract validation

2. Artifact pipeline
   - each stage writes durable markdown/json artifacts
   - later stages read earlier artifacts instead of recomputing hidden state

3. Codex execution layer
   - `codex exec` is used only for synthesis and critique steps
   - deterministic layers constrain inputs and validate outputs before accepting them

## 3. Recommended command model

The first scaffold had `init`, `ingest-examples`, `analyze`, `draft`, `review`.

After analyzing `selfintro_mvp`, the Codex CLI should evolve toward these commands:

```text
/setup
/crawl-base
/my-profile
/my-gaps
/coach
/writer
/interview
/export
```

Recommended CLI mapping:

```text
resume-agent setup
resume-agent crawl-base
resume-agent my-profile
resume-agent my-gaps
resume-agent coach
resume-agent writer
resume-agent interview
resume-agent export
```

The original `analyze` command can remain, but it should be treated as part of `/crawl-base` or as an internal stage.

## 4. Workspace layout

The current scaffold uses a document-first workspace. Keep that, but upgrade it to support artifact persistence.

```text
workspace/
  profile/
    facts.md
    experience_bank.md
    targets/
  sources/
    raw/
    normalized/
    extracted/
  analysis/
    question_map.json
    structure_rules.md
    gap_report.md
    knowledge_hints.json
  artifacts/
    coach.md
    writer.md
    interview.md
    export.md
  runs/
    20260309_132000/
      setup.json
      crawl-base.json
      coach.json
      writer.json
      interview.json
  prompts/
    coach.md
    writer.md
    interview.md
  state/
    db.json
```

## 5. Data model

The Prisma schema in the analyzed MVP is the right conceptual model even if the Codex CLI version uses flat files first.

Recommended logical entities:

### UserProfile
- display name
- career stage
- target company types
- target roles
- style preference

### Experience
- title
- organization
- period
- situation
- task
- action
- result
- personal contribution
- metrics
- evidence text
- evidence level: `L1 | L2 | L3`
- verification status: `verified | needs_verification`
- tags

### ApplicationProject
- company name
- job title
- company type
- research notes
- tone style
- priority experience order
- questions

### KnowledgeSource
- source type
- title
- url
- raw text
- cleaned text
- extracted json

### GeneratedArtifact
- artifact type
- input snapshot
- output text
- validation result

For the Codex CLI version, start with JSON files in `state/` and keep the schema compatible with future SQLite migration.

## 6. Deterministic core to port into Codex CLI

These parts should be implemented before deeper LLM integration:

### Question classifier
Use question types like the analyzed MVP:

- `TYPE_A`: motivation / fit
- `TYPE_B`: core capability
- `TYPE_C`: collaboration
- `TYPE_D`: growth / learning
- `TYPE_E`: post-join contribution
- `TYPE_F`: work principles
- `TYPE_G`: failure and recovery
- `TYPE_H`: customer response
- `TYPE_I`: prioritization under pressure

This does not need to be ML. Start rule-based.

### Experience allocator
Score by:

- evidence level bonus
- verification status
- keyword overlap with question
- tag match by question type
- metrics presence
- user priority order
- reuse penalty
- same-organization penalty when consecutive

One important rule from the analyzed MVP should be kept:

- force at least one `L3` experience into a high-value slot when possible

### Gap analyzer
Generate these signals:

- missing metrics
- missing evidence text
- too many `needs_verification` experiences
- missing `L3` evidence
- low question-to-experience coverage
- excessive experience reuse

### Knowledge hint ranker
Do not retrieve full examples into the final draft prompt.
Instead, rank sources and surface compact hints:

- title
- source type
- matched company/job/question signal
- structure summary
- caution: "structure only, do not copy wording"

## 7. Artifact contracts

The strongest idea in the analyzed MVP is explicit output contracts.

Codex CLI version should enforce these:

### Coach contract
- current stage
- purpose
- current summary
- required inputs
- next step

### Writer contract
- assumptions and missing facts
- outline
- draft answers
- self-check

### Interview contract
- interview assumptions
- interview strategy
- expected questions map
- answer frames
- final check

If `codex exec` returns a response missing the required headings, mark the run as failed and preserve the raw output for debugging.

## 8. Role of Codex CLI in each stage

Codex should be used differently per stage:

### `/setup`
- no Codex call required
- create files and seed structures

### `/crawl-base`
- optional Codex call
- deterministic extraction first
- Codex can summarize structural patterns

### `/my-profile`
- optional Codex call
- Codex can normalize rough notes into structured experience entries

### `/my-gaps`
- no Codex call required
- deterministic rules should generate the report

### `/coach`
- deterministic allocator produces the first allocation
- Codex may explain the allocation and suggest risk-aware revisions

### `/writer`
- Codex is appropriate here
- input must include:
  - facts
  - selected experiences
  - question type
  - character limit
  - top knowledge hints
- output must be validated

### `/interview`
- Codex is appropriate here
- build follow-up defense packs from the chosen experiences

### `/export`
- no Codex call required

## 9. Prompt strategy upgrade

The initial scaffold used one prompt per stage. That is fine, but the prompt design should mirror the analyzed MVP more closely.

### Coach prompt
Ask Codex to:

- explain why each experience is assigned
- identify missing proof
- flag risky claims
- avoid changing the deterministic allocation unless it can justify the swap

### Writer prompt
Ask Codex to:

- answer each question directly
- use only facts from selected experiences
- keep structure guidance abstract
- avoid copying example wording
- preserve a markdown contract
- mark weak claims with `[NEEDS_VERIFICATION]`

### Interview prompt
Ask Codex to produce:

- 30-second answer
- full answer frame
- likely follow-up questions
- defense points
- phrases to avoid

## 10. Implementation phases

### Phase 1: Make current scaffold structurally compatible
- add project and experience JSON schemas
- add question classifier
- add allocator
- add gap analysis
- add artifact contracts

### Phase 2: Introduce persistent run artifacts
- save per-stage snapshots
- save validation reports
- save raw Codex outputs before acceptance

### Phase 3: Add knowledge ingestion
- local markdown/text ingest
- URL ingest only for user-provided public URLs
- structural pattern extraction

### Phase 4: Add interview stage
- reuse coach and writer artifacts
- generate defense packs

### Phase 5: Optional storage upgrade
- migrate from JSON workspace state to SQLite
- keep exported markdown as first-class output

## 11. Immediate changes recommended for the existing `resume-agent` scaffold

The current scaffold should be extended in this order:

1. Rename or alias commands to the stage model used above.
2. Add a `state/` folder with JSON entities for profile, experiences, project, knowledge sources, and artifacts.
3. Implement a deterministic `questionClassifier`.
4. Implement `experienceAllocator`.
5. Implement `gapAnalyzer`.
6. Split `draft` into `coach`, `writer`, and `interview`.
7. Add markdown block contract validators.
8. Store `raw_codex_output.md` whenever `codex exec` runs.
9. Add an `export` command that composes final deliverables from accepted artifacts.

## 12. Non-goals

Do not add these in the first useful Codex CLI version:

- login wall bypass
- stealth crawling
- automatic scraping of protected sites
- expression cloning from reference essays
- fabricated metrics or backfilled evidence

## 13. Final recommendation

The correct target is not "a Codex prompt that writes self-intros".

The correct target is:

"a local artifact-driven application pipeline where Codex is one stage inside a deterministic, validated system."

That is the key lesson from `selfintro_mvp`, and it is the design that should drive the next iteration of `resume-agent`.
