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
    run_deep_interview,
    run_codex,
    run_gap_analysis,
    run_writer,
    run_writer_with_codex,
)
from .wizard import run_wizard
from .workspace import Workspace
from .validators import validate_experience
from .interactive import run_interactive_coach
from .progress import print_status


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n[오류 발생] {e}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-agent",
        description="Codex CLI workflow for application drafting.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create a new workspace with state JSON files.")
    p_init.add_argument("workspace")
    p_init.set_defaults(func=cmd_init)

    p_wizard = sub.add_parser("wizard", help="Interactive wizard for project setup.")
    p_wizard.add_argument("workspace")
    p_wizard.add_argument("--import-experiences", help="Path to experience file to import.")
    p_wizard.add_argument("--jd", help="Path to job description PDF.")
    p_wizard.set_defaults(func=cmd_wizard)
    
    p_mine = sub.add_parser("mine-past", help="Extract experiences from a past resume.")
    p_mine.add_argument("workspace")
    p_mine.add_argument("resume_file", help="Path to the past resume (.docx or .txt)")
    p_mine.set_defaults(func=cmd_mine_past)
    
    p_edit = sub.add_parser("edit", help="Interactive terminal editor for experiences.")
    p_edit.add_argument("workspace")
    p_edit.set_defaults(func=cmd_edit)

    p_interactive = sub.add_parser("interactive", help="Run interactive coaching session.")
    p_interactive.add_argument("workspace")
    p_interactive.set_defaults(func=cmd_interactive)

    p_validate = sub.add_parser("validate", help="Validate stored experiences.")
    p_validate.add_argument("workspace")
    p_validate.set_defaults(func=cmd_validate)
    
    p_sync = sub.add_parser("sync-vault", help="Sync experiences with Global Vault to auto-verify based on evidence.")
    p_sync.add_argument("workspace")
    p_sync.set_defaults(func=cmd_sync_vault)

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

    p_deep = sub.add_parser("deep-interview", help="Run recursive chaining for deep follow-up questions.")
    p_deep.add_argument("workspace")
    p_deep.set_defaults(func=cmd_deep_interview)

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
    # init_workspace now does both directory creation and state initialization
    ws = init_workspace(Path(args.workspace))
    print(f"Initialized workspace at {ws.root}")
    print(f"State files created under {ws.state_dir}")
    print(f"Edit {ws.profile_dir / 'facts.md'} and {ws.state_dir / 'project.json'} to start.")


def cmd_wizard(args: argparse.Namespace) -> None:
    import_path = Path(args.import_experiences) if args.import_experiences else None
    jd_path = Path(args.jd) if args.jd else None
    result = run_wizard(Path(args.workspace), import_path, jd_path)
    if result:
        print(f"\n🚀 coach를 실행하시겠습니까? (resume-agent coach {args.workspace})")

def cmd_edit(args: argparse.Namespace) -> None:
    from .editor import run_editor
    from .workspace import Workspace
    
    ws = Workspace(Path(args.workspace))
    run_editor(ws)


def cmd_interactive(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    run_interactive_coach(ws)


def cmd_validate(args: argparse.Namespace) -> None:
    from .state import load_experiences, initialize_state

    ws = Workspace(Path(args.workspace))
    ws.ensure()
    initialize_state(ws)

    experiences = load_experiences(ws)
    if not experiences:
        print_status("검증할 경험이 없습니다.", "warning")
        return

    all_passed = True
    for experience in experiences:
        result = validate_experience(experience)
        status = "success" if result.passed else "error"
        print_status(f"[{experience.title}] {result.get_summary()}", status)
        all_passed = all_passed and result.passed

    if all_passed:
        print_status("모든 경험 검증이 완료되었습니다.", "success")
    else:
        print_status("일부 경험에서 수정이 필요한 항목이 발견되었습니다.", "warning")

def cmd_sync_vault(args: argparse.Namespace) -> None:
    from .vault import VaultManager
    from .state import load_experiences, save_experiences, initialize_state
    
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    initialize_state(ws)
    
    experiences = load_experiences(ws)
    if not experiences:
        print("현재 워크스페이스에 등록된 경험이 없습니다.")
        return
        
    vault = VaultManager(Path("취업"))
    print("🔍 Global Vault (취업/자격증, 취업/경력증명서) 스캔 중...")
    verified_count = vault.verify_experiences(experiences)
    
    if verified_count > 0:
        save_experiences(ws, experiences)
        print(f"✅ {verified_count}개의 경험이 증빙 파일과 매칭되어 L3(VERIFIED)로 자동 승격되었습니다.")
    else:
        print("ℹ️ 일치하는 증빙 파일을 찾지 못했습니다.")

def cmd_mine_past(args: argparse.Namespace) -> None:
    from .miner import mine_past_resume
    from .state import load_experiences, save_experiences, initialize_state
    
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    initialize_state(ws)
    
    resume_path = Path(args.resume_file)
    if not resume_path.exists():
        print(f"파일을 찾을 수 없습니다: {resume_path}")
        return
        
    print(f"🔍 {resume_path.name} 파일에서 경험을 마이닝합니다 (Codex 실행 중...)")
    new_experiences = mine_past_resume(resume_path, ws.root)
    
    if new_experiences:
        current_experiences = load_experiences(ws)
        current_experiences.extend(new_experiences)
        save_experiences(ws, current_experiences)
        print(f"✅ {len(new_experiences)}개의 경험이 성공적으로 추출되어 워크스페이스에 저장되었습니다.")
        for exp in new_experiences:
            print(f"  - [{exp.evidence_level.value}] {exp.title}")
    else:
        print("⚠️ 경험을 추출하지 못했거나 파일 형식이 지원되지 않습니다.")


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


def cmd_deep_interview(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    print(f"🔍 {args.workspace}에 대해 심층 압박 면접 시뮬레이션을 시작합니다 (여러 번의 Codex 호출 발생)...")
    result = run_deep_interview(ws)
    print(f"✅ 심층 면접 팩 생성 완료: {result['path']}")
    print(f"📊 {result['count']}개의 질문에 대해 꼬리 질문이 생성되었습니다.")


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
