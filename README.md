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

- [Enhanced Design](/home/da/resume-agent/CODEX_CLI_ENHANCED_DESIGN.md)
- [Architecture](/home/da/resume-agent/ARCHITECTURE.md)
- [Knowledge Base And State Spec](/home/da/resume-agent/KB_AND_STATE_SPEC.md)
- [Codex Usage](/home/da/resume-agent/CODEX_USAGE.md)

## Current scaffold commands

These are implemented now:

```bash
python3 -m pip install -e .

resume-agent init my_run
resume-agent ingest-examples my_run
resume-agent analyze my_run
resume-agent draft my_run --target profile/targets/example_target.md
resume-agent review my_run --draft outputs/latest_draft.md
```

The full target command model is documented as:

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
