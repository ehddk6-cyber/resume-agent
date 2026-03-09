# Codex Usage

## 1. Role of Codex in this system

Codex is not the orchestrator of truth.
It is the synthesis engine inside a constrained pipeline.

Use Codex for:

- transforming validated facts into a readable answer
- critiquing a generated draft
- expanding an accepted outline into an interview pack

Do not use Codex for:

- guessing missing facts
- deciding whether a metric is real
- deciding which experience is trustworthy
- raw uncontrolled retrieval from source corpora

## 2. Recommended execution model

Each synthesis stage should create a prompt file and then call:

```bash
codex exec "$(cat prompt.md)"
```

In the Python scaffold, this is already represented by the `run_codex()` helper.

## 3. Prompt construction rules

Every prompt should contain:

1. explicit inputs
2. explicit task
3. explicit output shape
4. explicit non-goals
5. explicit safety rules

Avoid vague prompts like:

- "write a better self-introduction"
- "improve this essay"

Prefer prompts like:

- "answer these 4 questions using only these 2 experiences and this structure summary"

## 4. Stage-by-stage Codex prompts

### Coach

Inputs:

- project questions
- classified question types
- allocated experiences
- gap report

Output:

- current stage
- purpose
- current summary
- required inputs
- next step

### Writer

Inputs:

- profile facts
- selected experiences
- target project
- knowledge hints
- character limits

Output:

- assumptions and missing facts
- outline
- draft answers
- self-check

### Interview

Inputs:

- accepted coach artifact
- accepted writer artifact
- selected experiences

Output:

- interview assumptions
- interview strategy
- expected questions map
- answer frames
- final check

## 5. Acceptance policy

After `codex exec`, validate the output before accepting it.

### Accept when

- all required headings exist
- no forbidden fabricated claims are found
- no obvious contract violation exists
- result is within the intended shape

### Reject when

- required headings are missing
- output invents numbers or claims
- output is clearly off-task
- output copies reference phrasing too closely

Rejected outputs should still be saved to a raw artifact file.

## 6. Suggested command wrappers

### Prompt-only mode

```bash
resume-agent writer my_run --target profile/targets/example_target.md
```

This is for inspection.

### Prompt + Codex mode

```bash
resume-agent writer my_run --target profile/targets/example_target.md --run-codex
```

This should:

- generate prompt file
- call Codex
- save raw output
- validate
- promote accepted output to artifact path

## 7. Example writer prompt skeleton

```markdown
# Writer Stage

## Inputs
- Candidate facts: `profile/facts.md`
- Experience bank: `profile/experience_bank.md`
- Target brief: `state/project.json`
- Selected experience allocations: `analysis/question_map.json`
- Knowledge hints: `analysis/knowledge_hints.json`

## Task
Write direct answers for each question using only factual candidate materials.

## Required output
- ## ASSUMPTIONS & MISSING FACTS
- ## OUTLINE
- ## DRAFT ANSWERS
- ## SELF-CHECK

## Rules
- Do not invent metrics.
- Do not copy wording from reference essays.
- If a claim is weak, mark it `[NEEDS_VERIFICATION]`.
```

## 8. Debugging Codex runs

Save these for every synthesis stage:

- prompt file
- raw Codex output
- accepted artifact
- validation result

This makes failures reproducible.

## 9. Model neutrality

The system should remain model-agnostic at the prompt boundary.

That means:

- prompt files are plain markdown
- validation is local and deterministic
- artifact contracts are independent of the provider

Codex is the primary intended engine, but the system design should not collapse if a different adapter is later added.

## 10. Operational rule

If Codex and the deterministic layer disagree, the deterministic layer wins.
