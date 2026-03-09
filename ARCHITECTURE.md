# Architecture

## Goal

Build a Codex-native local application pipeline for:

- self-introduction letters
- essay questions
- support documents
- interview defense packs

The system must remain useful even when no remote LLM is configured.

## System shape

The architecture has five layers.

### 1. Input layer

Human-entered data:

- user profile
- experience cards
- application project
- essay questions
- optional reference samples

This layer must be editable without touching prompts.

### 2. Knowledge layer

Reference materials are ingested and normalized into two stores:

- raw store
- pattern knowledge base

Raw store keeps traceability.
Pattern KB keeps only structure signals and retrieval metadata.

### 3. Deterministic domain layer

This is the center of the system.

Core components:

- `questionClassifier`
- `experienceAllocator`
- `gapAnalyzer`
- `validators`
- `knowledgeHintRanker`

These components make the high-risk decisions before Codex writes anything.

### 4. Synthesis layer

Codex is used only for stages that benefit from language synthesis:

- coach explanation
- writer output
- interview output

The synthesis layer never receives unbounded context.
It receives validated snapshots and compact hints.

### 5. Artifact layer

Every stage writes outputs as durable artifacts:

- markdown for humans
- json snapshots for machines
- validation results for debugging

No stage should depend on hidden in-memory state.

## Runtime flow

```text
setup
  -> initialize workspace state

crawl-base
  -> ingest local files / approved URLs
  -> normalize
  -> extract pattern KB entries

my-profile
  -> create / update profile and experience cards

my-gaps
  -> deterministic risk and missing-data report

coach
  -> classify questions
  -> allocate experiences
  -> produce coaching artifact

writer
  -> retrieve top knowledge hints
  -> build writer prompt
  -> run codex exec
  -> validate writer contract

interview
  -> reuse accepted coach + writer artifacts
  -> run codex exec
  -> validate interview contract

export
  -> compose final markdown/json package
```

## Command responsibilities

### `setup`
- initialize workspace
- create seed files
- create state files
- create prompt templates

### `crawl-base`
- ingest CSV / markdown / txt / approved URLs
- clean boilerplate
- extract company/job/question signals
- write normalized sources
- write pattern KB

### `my-profile`
- edit profile fields
- edit experiences
- mark evidence level and verification status

### `my-gaps`
- detect missing metrics
- detect weak evidence
- detect over-reused experiences
- detect missing L3 evidence

### `coach`
- classify questions
- allocate experiences
- emit assumptions, required inputs, and next-step guidance

### `writer`
- create per-question structure plans
- generate answers using Codex
- validate block headings and content safety

### `interview`
- derive expected follow-ups
- build 30-second and full answer frames
- build defense notes and banned phrases

### `export`
- save clean deliverables
- keep source snapshots for auditability

## Design rules

### Rule 1: deterministic first

If a decision can be expressed as a rule, it should not depend on the LLM.

### Rule 2: structure, not copying

Reference samples are only for:

- rhetorical structure
- evidence patterns
- answer ordering
- question-to-experience fit signals

They are not for phrase reuse.

### Rule 3: write artifacts at every stage

Every stage must leave behind:

- inputs used
- output generated
- validation result

### Rule 4: fail closed

If a writer or interview contract fails validation:

- preserve raw output
- mark the run failed
- do not auto-promote the artifact to accepted

### Rule 5: defensibility over polish

If there is a tradeoff between a smoother sentence and a claim the user can defend, choose defensibility.

## Minimum implementation order

1. state JSON schema
2. question classifier
3. experience allocator
4. gap analyzer
5. artifact contracts
6. KB ingest and pattern extraction
7. writer and interview Codex integration
