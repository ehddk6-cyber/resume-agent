# Analyze Reference Examples

You are extracting structure rules from reference application samples.

## Inputs
- Candidate facts: `{facts_path}`
- Experience bank: `{experience_path}`
- Normalized examples directory: `{examples_dir}`

## Task
Read the examples and produce:

1. A reusable structure guide for high-quality applications.
2. A list of common section patterns, opening moves, evidence patterns, and transitions.
3. A list of things to avoid.
4. A warning section describing plagiarism risks and how to avoid them.

## Rules
- Extract structure, logic, and rhetorical patterns only.
- Do not copy distinctive phrasing from the examples.
- Prefer compact, reusable rules.
- If the examples are weak or inconsistent, say so explicitly.

Write the result to markdown with these sections:
- Overview
- Structural patterns
- Evidence patterns
- Tone patterns
- Anti-patterns
- Safe-use rules
