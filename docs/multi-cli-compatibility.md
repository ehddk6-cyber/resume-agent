# Multi-CLI Compatibility (Codex / Claude / Gemini / Kilo)

## Runtime checklist (2026-03-31)

| Runtime | Binary on PATH | `--help` smoke | `resume-agent writer --tool <runtime>` parse |
|---|---|---|---|
| codex | PASS | PASS | PASS |
| claude | PASS | PASS | PASS |
| gemini | PASS | PASS | PASS |
| kilo | PASS | PASS | PASS |

## Differences and handling

- Prompt flag mapping:
  - codex: `-p`
  - claude: `-p`
  - gemini: `--prompt`
  - kilo: `run`
- Availability check:
  - Runtime execution is gated by `shutil.which(...)` in `CLIToolManager`.
  - If a selected tool is unavailable, the executor writes a fallback artifact with remediation guidance.

## Common execution contract (minimum)

1. Input: plain text prompt (wrapped by `build_exec_prompt(...)`).
2. Invocation: CLI called through `CLIToolManager.execute(prompt, timeout=300)`.
3. Output: stdout captured and written to output artifact.
4. Error contract:
   - Non-zero exit -> fallback artifact with error details.
   - Missing binary -> fallback artifact with install guidance.
   - Timeout -> raised and surfaced as tool execution failure.

## Applied changes

- Added `kilo` as a first-class tool in:
  - `src/resume_agent/cli_tool_manager.py`
  - `src/resume_agent/cli.py` (`--tool` choices)
  - `src/resume_agent/executor.py` (tool docs/fallback guidance)
- Added regression tests:
  - `tests/test_cli_tool_manager.py`
  - `tests/test_executor_cli.py::test_writer_accepts_kilo_tool_option`
