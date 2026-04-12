# Resume Agent

Resume Agent is a Codex CLI-oriented pipeline for resume writing, self-introduction drafting, interview preparation, and outcome-driven learning.

This repository is no longer just an initial scaffold. The main pipeline is implemented and connected end-to-end.

## Implemented Capabilities

- deterministic intake and validation
- applicant profiling and coaching hints
- company research and live source refresh
- coach / writer / interview artifact generation
- outcome tracking and A/B testing
- cumulative live-signal reporting
- priority-rule coverage quality metric

## Current Status

The core project loop is complete.

Implemented phases:

- Phase 3: personalization, company analysis, interview coaching
- Phase 4: live source freshness tracking and refresh
- Phase 5: translate live changes into answer actions
- Phase 6: link live coverage to real outcomes
- Phase 7: use outcome-backed live signals in prompt priority
- Phase 8: harden rewrite, status, and report surfaces
- Optional hardening:
  - weighted A/B recommendation
  - priority-rule coverage quality metric
  - cumulative effect report

Integrated verification command:

```bash
python3 -m pytest -q -s tests/test_ab_testing.py tests/test_pipeline.py tests/test_pipeline_resume_coverage.py tests/test_cli_commands.py
```

Latest result:

- `193 passed`

## Design Docs

- [Enhanced Design](./CODEX_CLI_ENHANCED_DESIGN.md)
- [Architecture](./ARCHITECTURE.md)
- [Knowledge Base And State Spec](./KB_AND_STATE_SPEC.md)
- [Codex Usage](./CODEX_USAGE.md)
- [Engineering Discipline Reviews](./docs/engineering-discipline/reviews/)

## Quick Start

If Python is not available locally, use `uv`.

```bash
uv run --python 3.11 python -m resume_agent --help
uv run --python 3.11 python -m resume_agent init my_run
```

If Python is already installed:

```bash
python -m pip install -e .
resume-agent --help
```

## Common Commands

Core workspace flow:

```bash
resume-agent init my_run
resume-agent sync my_run
resume-agent crawl-base my_run
resume-agent company-research my_run --auto-web --refresh-live
resume-agent coach my_run
resume-agent writer my_run --target profile/targets/example_target.md
resume-agent interview my_run
resume-agent export my_run
```

Personalization and research:

```bash
resume-agent profile my_run
resume-agent company my_run --company-name "Example Corp"
resume-agent refresh-live my_run --url https://example.com/jobs
resume-agent report my_run
resume-agent status my_run
```

Learning and operations:

```bash
resume-agent outcome record my_run --artifact-id writer-001 --company "Example Corp" --outcome offer_received
resume-agent outcome summary my_run
resume-agent ab status my_run
resume-agent history my_run
```

## Workspace Layout

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
    writer_brief.json
    company_profile.json
    interview_support_pack.json
    application_strategy.json
    outcome_dashboard.json
    kpi_dashboard.json
    cumulative_effect_report.json
    live_source_updates.json
  artifacts/
    writer.md
    interview.md
    writer_quality.json
    writer_result_quality.json
    writer_change_actions.json
    writer_priority_rule_audit.json
    interview_change_actions.json
    interview_priority_rule_audit.json
  outputs/
    latest_coach_prompt.md
    latest_draft_prompt.md
    latest_interview_prompt.md
    latest_company_research_prompt.md
```

## Notes

- Use reference materials only as structure hints and strategy signals.
- The default principle is `deterministic first, Codex second`.
- Live source tracking and learning accumulate through `analysis/` and `state/` outputs.
