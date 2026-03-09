from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent

from .pipeline import (
    build_analysis_prompt,
    build_draft_prompt,
    build_interview_prompt,
    build_review_prompt,
    run_export,
    ingest_examples,
    init_workspace,
    crawl_base,
    build_coach_prompt,
    run_coach,
    run_interview,
    run_interview_with_codex,
    run_codex,
    run_gap_analysis,
    setup_workspace,
    run_writer,
    run_writer_with_codex,
)
from .workspace import Workspace


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-agent",
        description="Codex CLI workflow for application drafting.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create a new workspace.")
    p_init.add_argument("workspace")
    p_init.set_defaults(func=cmd_init)

    p_setup = sub.add_parser("setup", help="Create a workspace with state JSON files.")
    p_setup.add_argument("workspace")
    p_setup.set_defaults(func=cmd_setup)

    p_crawl = sub.add_parser("crawl-base", help="Ingest local source files into the knowledge base.")
    p_crawl.add_argument("workspace")
    p_crawl.add_argument("--path", help="Optional file or directory to ingest.")
    p_crawl.set_defaults(func=cmd_crawl_base)

    p_gaps = sub.add_parser("my-gaps", help="Run deterministic gap analysis.")
    p_gaps.add_argument("workspace")
    p_gaps.set_defaults(func=cmd_my_gaps)

    p_coach = sub.add_parser("coach", help="Run deterministic question classification and allocation.")
    p_coach.add_argument("workspace")
    p_coach.add_argument("--run-codex", action="store_true")
    p_coach.set_defaults(func=cmd_coach)

    p_writer = sub.add_parser("writer", help="Build writer prompt or run Codex.")
    p_writer.add_argument("workspace")
    p_writer.add_argument("--run-codex", action="store_true")
    p_writer.set_defaults(func=cmd_writer)

    p_interview = sub.add_parser("interview", help="Build interview prompt or run Codex.")
    p_interview.add_argument("workspace")
    p_interview.add_argument("--run-codex", action="store_true")
    p_interview.set_defaults(func=cmd_interview)

    p_export = sub.add_parser("export", help="Bundle accepted artifacts into export outputs.")
    p_export.add_argument("workspace")
    p_export.set_defaults(func=cmd_export)

    p_ingest = sub.add_parser("ingest-examples", help="Normalize raw reference samples.")
    p_ingest.add_argument("workspace")
    p_ingest.set_defaults(func=cmd_ingest)

    p_analyze = sub.add_parser("analyze", help="Build analysis prompt or run Codex.")
    p_analyze.add_argument("workspace")
    p_analyze.add_argument("--run-codex", action="store_true")
    p_analyze.set_defaults(func=cmd_analyze)

    p_draft = sub.add_parser("draft", help="Build draft prompt or run Codex.")
    p_draft.add_argument("workspace")
    p_draft.add_argument("--target", required=True, help="Path relative to workspace root.")
    p_draft.add_argument("--run-codex", action="store_true")
    p_draft.set_defaults(func=cmd_draft)

    p_review = sub.add_parser("review", help="Build review prompt or run Codex.")
    p_review.add_argument("workspace")
    p_review.add_argument("--target", default="profile/targets/example_target.md")
    p_review.add_argument("--draft", required=True, help="Path relative to workspace root.")
    p_review.add_argument("--run-codex", action="store_true")
    p_review.set_defaults(func=cmd_review)

    return parser


def cmd_init(args: argparse.Namespace) -> None:
    ws = init_workspace(Path(args.workspace))
    print(f"Initialized workspace at {ws.root}")
    print(f"Edit {ws.profile_dir / 'facts.md'} and {ws.profile_dir / 'experience_bank.md'} first.")


def cmd_setup(args: argparse.Namespace) -> None:
    ws = setup_workspace(Path(args.workspace))
    print(f"Initialized workspace at {ws.root}")
    print(f"State files created under {ws.state_dir}")
    print(f"Edit {ws.state_dir / 'project.json'} and {ws.state_dir / 'experiences.json'} before coach/writer.")


def cmd_crawl_base(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    source_path = Path(args.path) if args.path else None
    result = crawl_base(ws, source_path)
    print(f"Ingested {result['source_count']} source item(s).")
    print(f"Knowledge base now has {result['stored_count']} item(s).")
    print(f"Analysis written to {result['analysis_path']}")


def cmd_my_gaps(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = run_gap_analysis(ws)
    print(f"Gap report written to {result['path']}")
    for line in result["report"]["summary"]:
        print(f"- {line}")
    for recommendation in result["report"]["recommendations"]:
        print(f"* {recommendation}")


def cmd_coach(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = run_coach(ws)
    print(f"Coach artifact written to {result['path']}")
    print(f"Validation passed: {result['validation']['passed']}")
    print(f"Coach prompt written to {result['prompt_path']}")
    if result["validation"]["missing"]:
        print("Missing headings:")
        for heading in result["validation"]["missing"]:
            print(f"- {heading}")
    if args.run_codex:
        output_path = ws.outputs_dir / "latest_coach.md"
        exit_code = run_codex(Path(result["prompt_path"]), ws.root, output_path)
        print(f"Codex exit code: {exit_code}")
        print(f"Wrote coach Codex output to {output_path}")


def cmd_ingest(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    files = ingest_examples(ws)
    print(f"Ingested {len(files)} example file(s).")
    for path in files:
        print(path)


def cmd_analyze(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    prompt_path = build_analysis_prompt(ws)
    print(f"Prompt written to {prompt_path}")
    if args.run_codex:
        output_path = ws.analysis_dir / "structure_rules.md"
        exit_code = run_codex(prompt_path, ws.root, output_path)
        print(f"Codex exit code: {exit_code}")
        print(f"Wrote analysis output to {output_path}")
    else:
        print(next_step("Run with --run-codex after adding reference samples."))


def cmd_draft(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    target_path = ws.resolve(args.target)
    prompt_path = build_draft_prompt(ws, target_path)
    print(f"Prompt written to {prompt_path}")
    if args.run_codex:
        output_path = ws.outputs_dir / "latest_draft.md"
        exit_code = run_codex(prompt_path, ws.root, output_path)
        print(f"Codex exit code: {exit_code}")
        print(f"Wrote draft output to {output_path}")
    else:
        print(next_step("Run with --run-codex to generate a draft."))


def cmd_writer(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    if args.run_codex:
        result = run_writer_with_codex(ws)
        print(f"Prompt written to {result['prompt_path']}")
        print(f"Codex exit code: {result['exit_code']}")
        print(f"Raw writer output: {result['raw_output_path']}")
        print(f"Accepted writer artifact: {result['artifact_path']}")
        print(f"Validation passed: {result['validation']['passed']}")
        if result["validation"]["missing"]:
            print("Missing headings:")
            for heading in result["validation"]["missing"]:
                print(f"- {heading}")
    else:
        result = run_writer(ws)
        print(f"Prompt written to {result['prompt_path']}")
        print(next_step("Run with --run-codex to generate a writer artifact."))


def cmd_interview(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    if args.run_codex:
        result = run_interview_with_codex(ws)
        print(f"Prompt written to {result['prompt_path']}")
        print(f"Codex exit code: {result['exit_code']}")
        print(f"Raw interview output: {result['raw_output_path']}")
        print(f"Accepted interview artifact: {result['artifact_path']}")
        print(f"Validation passed: {result['validation']['passed']}")
        if result["validation"]["missing"]:
            print("Missing headings:")
            for heading in result["validation"]["missing"]:
                print(f"- {heading}")
    else:
        result = run_interview(ws)
        print(f"Prompt written to {result['prompt_path']}")
        print(next_step("Run with --run-codex to generate an interview artifact."))


def cmd_export(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = run_export(ws)
    print(f"Export markdown written to {result['markdown_path']}")
    print(f"Export json written to {result['json_path']}")
    print(f"Accepted artifacts bundled: {result['accepted_count']}")


def cmd_review(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    target_path = ws.resolve(args.target)
    draft_path = ws.resolve(args.draft)
    prompt_path = build_review_prompt(ws, draft_path, target_path)
    print(f"Prompt written to {prompt_path}")
    if args.run_codex:
        output_path = ws.outputs_dir / "latest_review.md"
        exit_code = run_codex(prompt_path, ws.root, output_path)
        print(f"Codex exit code: {exit_code}")
        print(f"Wrote review output to {output_path}")
    else:
        print(next_step("Run with --run-codex to critique the draft."))


def next_step(message: str) -> str:
    return dedent(
        f"""\
        Next step:
          {message}
        """
    ).rstrip()
