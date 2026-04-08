# Resume Agent

Codex CLI-oriented resume and self-introduction pipeline.

The current repository contains:

- a minimal working Python scaffold
- the completed design for the full Codex-native pipeline
- the contract and state model needed to implement it without drifting into prompt spaghetti

## What this project is aiming for

The target system is not "one big prompt that writes a self-introduction".

It is:

1. deterministic intake and validation
2. knowledge-base extraction from reference materials
3. question classification and experience allocation
4. Codex-assisted synthesis only where synthesis is actually needed
5. artifact contracts and post-generation validation

## Design docs

- [Enhanced Design](./CODEX_CLI_ENHANCED_DESIGN.md)
- [Architecture](./ARCHITECTURE.md)
- [Knowledge Base And State Spec](./KB_AND_STATE_SPEC.md)
- [Codex Usage](./CODEX_USAGE.md)

## Quick start

If `python` or `pip` is not installed on your machine, use `uv`.
It can provision Python automatically for this project.

```bash
uv run --python 3.11 python -m resume_agent --help
uv run --python 3.11 python -m resume_agent setup my_run
```

## Current scaffold commands

These are implemented now:

```bash
uv run --python 3.11 python -m resume_agent init my_run
uv run --python 3.11 python -m resume_agent sync my_run

uv run --python 3.11 python -m resume_agent ingest-examples my_run
uv run --python 3.11 python -m resume_agent analyze my_run
uv run --python 3.11 python -m resume_agent draft my_run --target profile/targets/example_target.md
uv run --python 3.11 python -m resume_agent review my_run --draft outputs/latest_draft.md
```

`init` and `wizard` automatically run `crawl-base` once after the workspace is created or saved, so the latest `linkareer.csv` is reflected immediately. Use `sync` later whenever you want to refresh an existing workspace without recreating it.

If you already have Python available, the editable install flow still works:

```bash
python -m pip install -e .
resume-agent --help
```

The full target command model is documented as:

```text
resume-agent setup
resume-agent crawl-base
resume-agent sync
resume-agent my-profile
resume-agent my-gaps
resume-agent coach
resume-agent writer
resume-agent interview
resume-agent export
```

## Current workspace layout

```text
my_run/
  profile/
    facts.md
    experience_bank.md
    targets/
  sources/
    raw/
    normalized/
  analysis/
    structure_rules.md
    gap_report.md
  outputs/
    latest_draft_prompt.md
    latest_draft.md
    latest_review_prompt.md
    latest_coach_prompt.md
    latest_interview_prompt.md
    latest_company_research_prompt.md
  prompts/
```

## Direction

The next implementation step should follow the design docs in this order:

1. add state JSON schemas
2. add deterministic question classification
3. add experience allocation and gap analysis
4. add artifact contracts
5. split draft/review into coach/writer/interview/export
6. wire `codex exec` into validated synthesis stages

## Notes

- Use legally obtained reference materials only.
- Reference essays must be converted into structure hints, not copied text.
- The system should prefer "deterministic first, Codex second".
