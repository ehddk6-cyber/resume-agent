from __future__ import annotations

import argparse
import traceback
import time
from pathlib import Path
from textwrap import dedent

from .pipeline import (
    build_analysis_prompt,
    build_draft_prompt,
    build_interview_prompt,
    build_review_prompt,
    build_company_research_prompt,
    build_outcome_dashboard,
    build_kpi_dashboard,
    run_company_research_with_codex,
    run_export,
    ingest_examples,
    init_workspace,
    crawl_base,
    crawl_web_sources,
    crawl_web_sources_auto,
    refresh_live_web_sources,
    refresh_existing_public_sources,
    build_coach_prompt,
    run_coach,
    run_interview,
    run_interview_with_codex,
    run_deep_interview,
    run_self_intro,
    run_codex,
    run_gap_analysis,
    run_writer,
    run_writer_with_codex,
    build_blind_benchmark_frame,
)
from .wizard import run_wizard
from .workspace import Workspace
from .validators import validate_experience
from .interactive import run_interactive_coach
from .progress import print_status
from .state import load_artifacts, load_project


def main() -> int:
    parser = build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1

    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
        return 130
    except Exception as e:
        print(f"\n[오류 발생] {e}")
        if getattr(args, "debug", False):
            traceback.print_exc()
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume-agent",
        description="Codex CLI workflow for application drafting.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print traceback details on command failure.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init",
        help="Create a new workspace, initialize state, and auto-sync linkareer data.",
    )
    p_init.add_argument("workspace")
    p_init.set_defaults(func=cmd_init)

    p_wizard = sub.add_parser(
        "wizard",
        help="Interactive wizard for project setup and automatic linkareer sync.",
    )
    p_wizard.add_argument("workspace")
    p_wizard.add_argument(
        "--import-experiences", help="Path to experience file to import."
    )
    p_wizard.add_argument("--jd", help="Path to job description PDF.")
    p_wizard.set_defaults(func=cmd_wizard)

    p_mine = sub.add_parser("mine-past", help="Extract experiences from a past resume.")
    p_mine.add_argument("workspace")
    p_mine.add_argument("resume_file", help="Path to the past resume (.docx or .txt)")
    p_mine.set_defaults(func=cmd_mine_past)

    p_edit = sub.add_parser("edit", help="Interactive terminal editor for experiences.")
    p_edit.add_argument("workspace")
    p_edit.set_defaults(func=cmd_edit)

    p_interactive = sub.add_parser(
        "interactive", help="Run interactive coaching session."
    )
    p_interactive.add_argument("workspace")
    p_interactive.set_defaults(func=cmd_interactive)

    p_validate = sub.add_parser("validate", help="Validate stored experiences.")
    p_validate.add_argument("workspace")
    p_validate.set_defaults(func=cmd_validate)

    p_sync = sub.add_parser(
        "sync-vault",
        help="Sync experiences with Global Vault to auto-verify based on evidence.",
    )
    p_sync.add_argument("workspace")
    p_sync.set_defaults(func=cmd_sync_vault)

    p_sync_base = sub.add_parser(
        "sync",
        help="Refresh the workspace knowledge base from the latest linkareer.csv and local raw sources.",
    )
    p_sync_base.add_argument("workspace")
    p_sync_base.add_argument(
        "--path",
        help="Optional file or directory to ingest. If omitted, syncs the workspace defaults.",
    )
    p_sync_base.set_defaults(func=cmd_sync_base)

    p_crawl = sub.add_parser(
        "crawl-base",
        help="Ingest local source files into the knowledge base (extracts docx/pdf to sources/raw).",
    )
    p_crawl.add_argument("workspace")
    p_crawl.add_argument(
        "--path",
        help="Optional file or directory to ingest. docx/pdf are extracted into sources/raw.",
    )
    p_crawl.set_defaults(func=cmd_crawl_base)

    p_crawl_web = sub.add_parser(
        "crawl-web", help="Ingest public web URLs into the knowledge base."
    )
    p_crawl_web.add_argument("workspace")
    p_crawl_web.add_argument(
        "--url",
        action="append",
        required=True,
        help="Public URL to ingest. Repeatable.",
    )
    p_crawl_web.set_defaults(func=cmd_crawl_web)

    p_crawl_web_auto = sub.add_parser(
        "crawl-web-auto",
        help="Discover and ingest public web URLs from search queries automatically.",
    )
    p_crawl_web_auto.add_argument("workspace")
    p_crawl_web_auto.add_argument(
        "--max-results-per-query",
        type=int,
        default=3,
        help="Maximum discovered URLs per query.",
    )
    p_crawl_web_auto.add_argument(
        "--max-urls",
        type=int,
        default=8,
        help="Maximum URLs to ingest after discovery.",
    )
    p_crawl_web_auto.set_defaults(func=cmd_crawl_web_auto)

    p_refresh_live = sub.add_parser(
        "refresh-live",
        help="공개 URL의 최신 스냅샷을 다시 수집하고 변경 여부를 기록합니다.",
    )
    p_refresh_live.add_argument("workspace")
    p_refresh_live.add_argument(
        "--url",
        action="append",
        required=True,
        help="최신성 추적할 공개 URL. 반복 가능.",
    )
    p_refresh_live.set_defaults(func=cmd_refresh_live)

    p_gaps = sub.add_parser("my-gaps", help="Run deterministic gap analysis.")
    p_gaps.add_argument("workspace")
    p_gaps.set_defaults(func=cmd_my_gaps)

    p_coach = sub.add_parser(
        "coach", help="Run deterministic question classification and allocation."
    )
    p_coach.add_argument("workspace")
    p_coach.add_argument("--run-codex", action="store_true")
    p_coach.add_argument(
        "--tool",
        default="codex",
        choices=["codex", "claude", "gemini", "kilo", "cline", "opencode"],
        help="CLI tool to use for LLM execution (default: codex).",
    )
    p_coach.add_argument(
        "--psychology-pack",
        action="store_true",
        help="지원자 프로파일 기반 면접 심리 코칭 팩을 함께 출력합니다.",
    )
    p_coach.set_defaults(func=cmd_coach)

    p_profile = sub.add_parser(
        "profile",
        help="지원자 글쓰기 스타일과 강약점을 분석해 프로파일을 저장합니다.",
    )
    p_profile.add_argument("workspace")
    p_profile.add_argument(
        "--answer",
        action="append",
        default=[],
        help="추가로 분석할 과거 답변 텍스트. 반복 가능.",
    )
    p_profile.set_defaults(func=cmd_profile)

    p_writer = sub.add_parser("writer", help="Build writer prompt or run Codex.")
    p_writer.add_argument("workspace")
    p_writer.add_argument(
        "--target",
        default="profile/targets/example_target.md",
        help="Path relative to workspace root.",
    )
    p_writer.add_argument("--run-codex", action="store_true")
    p_writer.add_argument(
        "--tool",
        default="codex",
        choices=["codex", "claude", "gemini", "kilo", "cline", "opencode"],
        help="CLI tool to use for LLM execution (default: codex).",
    )
    p_writer.add_argument(
        "--patina",
        action="store_true",
        help="Writer 실행 후 patina AI 패턴 제거를 자동 실행합니다.",
    )
    p_writer.add_argument(
        "--patina-mode",
        default="audit",
        choices=["audit", "rewrite", "score", "ouroboros"],
        help="patina 실행 모드 (default: audit).",
    )
    p_writer.add_argument(
        "--patina-profile",
        default="resume",
        help="patina 프로필 이름 (default: resume).",
    )
    p_writer.add_argument(
        "--patina-max",
        action="store_true",
        help="Writer 실행 후 patina-max 멀티모델 후처리를 실행합니다.",
    )
    p_writer.add_argument(
        "--patina-max-models",
        default=None,
        help="patina-max 모델 목록 (쉼표 구분). 예: claude,codex,opencode,gemini",
    )
    p_writer.add_argument(
        "--patina-max-dispatch",
        default=None,
        choices=["direct", "omc"],
        help="patina-max 디스패치 모드 (v1에서는 omc를 받아도 direct로 강등).",
    )
    p_writer.set_defaults(func=cmd_writer)

    p_interview = sub.add_parser(
        "interview", help="Build interview prompt or run Codex."
    )
    p_interview.add_argument("workspace")
    p_interview.add_argument("--run-codex", action="store_true")
    p_interview.add_argument(
        "--tool",
        default="codex",
        choices=["codex", "claude", "gemini", "kilo", "cline", "opencode"],
        help="CLI tool to use for LLM execution (default: codex).",
    )
    p_interview.set_defaults(func=cmd_interview)

    p_deep = sub.add_parser(
        "deep-interview", help="Run recursive chaining for deep follow-up questions."
    )
    p_deep.add_argument("workspace")
    p_deep.set_defaults(func=cmd_deep_interview)

    p_self_intro = sub.add_parser(
        "self-intro", help="Build a 30s/60s self introduction artifact."
    )
    p_self_intro.add_argument("workspace")
    p_self_intro.set_defaults(func=cmd_self_intro)

    p_export = sub.add_parser(
        "export", help="Bundle accepted artifacts into export outputs."
    )
    p_export.add_argument("workspace")
    p_export.set_defaults(func=cmd_export)

    p_ingest = sub.add_parser(
        "ingest-examples", help="Normalize raw reference samples."
    )
    p_ingest.add_argument("workspace")
    p_ingest.set_defaults(func=cmd_ingest)

    p_analyze = sub.add_parser("analyze", help="Build analysis prompt or run Codex.")
    p_analyze.add_argument("workspace")
    p_analyze.add_argument("--run-codex", action="store_true")
    p_analyze.add_argument(
        "--tool",
        default="codex",
        choices=["codex", "claude", "gemini", "kilo", "cline", "opencode"],
        help="CLI tool to use for LLM execution (default: codex).",
    )
    p_analyze.set_defaults(func=cmd_analyze)

    p_draft = sub.add_parser("draft", help="Build draft prompt or run Codex.")
    p_draft.add_argument("workspace")
    p_draft.add_argument(
        "--target", required=True, help="Path relative to workspace root."
    )
    p_draft.add_argument("--run-codex", action="store_true")
    p_draft.add_argument(
        "--tool",
        default="codex",
        choices=["codex", "claude", "gemini", "kilo", "cline", "opencode"],
        help="CLI tool to use for LLM execution (default: codex).",
    )
    p_draft.set_defaults(func=cmd_draft)

    p_review = sub.add_parser("review", help="Build review prompt or run Codex.")
    p_review.add_argument("workspace")
    p_review.add_argument("--target", default="profile/targets/example_target.md")
    p_review.add_argument(
        "--draft", required=True, help="Path relative to workspace root."
    )
    p_review.add_argument("--run-codex", action="store_true")
    p_review.add_argument(
        "--tool",
        default="codex",
        choices=["codex", "claude", "gemini", "kilo", "cline", "opencode"],
        help="CLI tool to use for LLM execution (default: codex).",
    )
    p_review.set_defaults(func=cmd_review)

    p_company = sub.add_parser(
        "company-research", help="Build company research prompt or run Codex."
    )
    p_company.add_argument("workspace")
    p_company.add_argument("--run-codex", action="store_true")
    p_company.add_argument(
        "--tool",
        default="codex",
        choices=["codex", "claude", "gemini", "kilo", "cline", "opencode"],
        help="CLI tool to use for LLM execution (default: codex).",
    )
    p_company.add_argument(
        "--auto-web",
        action="store_true",
        help="회사/직무 검색어를 자동 생성해 공개 웹 자료를 먼저 수집합니다.",
    )
    p_company.add_argument(
        "--max-results-per-query",
        type=int,
        default=3,
        help="자동 웹 조사 시 검색어당 수집할 후보 URL 수 (default: 3).",
    )
    p_company.add_argument(
        "--max-urls",
        type=int,
        default=8,
        help="자동 웹 조사 시 실제 ingest 할 최대 URL 수 (default: 8).",
    )
    p_company.add_argument(
        "--refresh-live",
        action="store_true",
        help="이미 수집한 공개 URL을 프롬프트 생성 전에 다시 확인합니다.",
    )
    p_company.set_defaults(func=cmd_company_research)

    p_company_profile = sub.add_parser(
        "company",
        help="기업별 미션/가치와 합격 패턴을 요약합니다.",
    )
    p_company_profile.add_argument("workspace")
    p_company_profile.add_argument("--company-name")
    p_company_profile.add_argument("--job-title")
    p_company_profile.add_argument("--company-type")
    p_company_profile.add_argument(
        "--job-description-file",
        help="미션/가치 파싱에 반영할 JD 또는 메모 파일 경로.",
    )
    p_company_profile.set_defaults(func=cmd_company)

    p_resume = sub.add_parser("resume", help="Resume pipeline from last checkpoint.")
    p_resume.add_argument("workspace")
    p_resume.set_defaults(func=cmd_resume)

    p_mock = sub.add_parser("mock-interview", help="Run conversational mock interview.")
    p_mock.add_argument("workspace")
    p_mock.add_argument(
        "--mode",
        choices=["hard", "normal", "coach"],
        default="normal",
        help="Interview mode: hard (aggressive), normal, coach (real-time feedback)",
    )
    p_mock.set_defaults(func=cmd_mock_interview)

    p_feedback = sub.add_parser(
        "feedback", help="Record feedback on generated artifacts."
    )
    p_feedback.add_argument("workspace")
    p_feedback.add_argument(
        "--artifact",
        choices=["writer", "interview", "coach"],
        required=True,
        help="Artifact type to give feedback on.",
    )
    p_feedback.add_argument(
        "--accepted",
        action="store_true",
        default=True,
        help="Mark artifact as accepted (default).",
    )
    p_feedback.add_argument(
        "--rejected", action="store_true", help="Mark artifact as rejected."
    )
    p_feedback.add_argument(
        "--rating", type=int, choices=[1, 2, 3, 4, 5], help="Rating 1-5 (optional)."
    )
    p_feedback.add_argument("--comment", type=str, help="Feedback comment (optional).")
    p_feedback.add_argument(
        "--final-outcome",
        choices=[
            "document_pass",
            "document_fail",
            "interview_pass",
            "interview_fail",
            "offer",
            "hold",
        ],
        help="Optional outcome after using the artifact.",
    )
    p_feedback.add_argument(
        "--rejection-reason",
        type=str,
        help="Optional rejection or weakness note for later learning.",
    )
    p_feedback.set_defaults(func=cmd_feedback)

    p_benchmark = sub.add_parser(
        "benchmark-blind", help="Generate a blind benchmark evaluation frame."
    )
    p_benchmark.add_argument("workspace")
    p_benchmark.set_defaults(func=cmd_benchmark_blind)

    p_status = sub.add_parser("status", help="Show current pipeline status dashboard.")
    p_status.add_argument("workspace")
    p_status.set_defaults(func=cmd_status)

    p_history = sub.add_parser("history", help="Show artifact generation history.")
    p_history.add_argument("workspace")
    p_history.set_defaults(func=cmd_history)

    # outcome command
    p_outcome = sub.add_parser("outcome", help="Record/list/summary application outcomes.")
    p_outcome.add_argument("workspace")
    outcome_sub = p_outcome.add_subparsers(dest="outcome_action", required=True)
    
    p_outcome_record = outcome_sub.add_parser("record", help="Record an application outcome.")
    p_outcome_record.add_argument("--artifact-id", required=True, help="Artifact ID to record outcome for.")
    p_outcome_record.add_argument("--company", required=True, help="Company name.")
    p_outcome_record.add_argument("--job-title", default="", help="Job title.")
    p_outcome_record.add_argument("--application-id", default="", help="Application ID.")
    p_outcome_record.add_argument("--outcome", required=True, choices=["pending", "screening_pass", "screening_fail", "interview_invited", "interview_pass", "interview_fail", "final_pass", "final_fail", "offer_received", "offer_declined"], help="Outcome result.")
    p_outcome_record.set_defaults(func=cmd_outcome_record)
    
    p_outcome_list = outcome_sub.add_parser("list", help="List all recorded outcomes.")
    p_outcome_list.add_argument("workspace")
    p_outcome_list.add_argument("--company", help="Filter by company name.")
    p_outcome_list.set_defaults(func=cmd_outcome_list)
    
    p_outcome_summary = outcome_sub.add_parser("summary", help="Show outcome summary statistics.")
    p_outcome_summary.add_argument("workspace")
    p_outcome_summary.set_defaults(func=cmd_outcome_summary)

    # ab command
    p_ab = sub.add_parser("ab", help="Record/status/end A/B tests.")
    p_ab.add_argument("workspace")
    ab_sub = p_ab.add_subparsers(dest="ab_action", required=True)
    
    p_ab_record = ab_sub.add_parser("record", help="Record a test result.")
    p_ab_record.add_argument("--variant", required=True, choices=["A", "B"], help="Test variant.")
    p_ab_record.add_argument("--success", action="store_true", help="Mark as success.")
    p_ab_record.add_argument("--fail", action="store_true", help="Mark as failure.")
    p_ab_record.set_defaults(func=cmd_ab_record)
    
    p_ab_status = ab_sub.add_parser("status", help="Show current A/B test status.")
    p_ab_status.set_defaults(func=cmd_ab_status)
    
    p_ab_end = ab_sub.add_parser("end", help="End the current A/B test.")
    p_ab_end.set_defaults(func=cmd_ab_end)

    return parser


def cmd_init(args: argparse.Namespace) -> None:
    # init_workspace handles directory creation and state initialization
    ws = init_workspace(Path(args.workspace))
    print(f"Initialized workspace at {ws.root}")
    print(f"State files created under {ws.state_dir}")
    result = crawl_base(ws)
    print(f"Ingested {result['source_count']} source item(s).")
    print(f"Knowledge base now has {result['stored_count']} item(s).")
    print(f"Analysis written to {result['analysis_path']}")
    print(
        f"Edit {ws.profile_dir / 'facts.md'} and {ws.state_dir / 'project.json'} to start."
    )


def cmd_wizard(args: argparse.Namespace) -> None:
    import_path = Path(args.import_experiences) if args.import_experiences else None
    jd_path = Path(args.jd) if args.jd else None
    result = run_wizard(Path(args.workspace), import_path, jd_path)
    sync_result = crawl_base(result["workspace"])
    print(f"Ingested {sync_result['source_count']} source item(s).")
    print(f"Knowledge base now has {sync_result['stored_count']} item(s).")
    print(f"Analysis written to {sync_result['analysis_path']}")
    if result:
        print(f"\ncoach를 실행하시겠습니까? (resume-agent coach {args.workspace})")


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
    print("Global Vault 스캔 중...")
    verified_count = vault.verify_experiences(experiences)

    if verified_count > 0:
        save_experiences(ws, experiences)
        print(
            f"{verified_count}개의 경험이 증빙 파일과 매칭되어 자동 승격되었습니다."
        )
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

    print(f"{resume_path.name} 파일에서 경험을 마이닝합니다...")
    new_experiences = mine_past_resume(resume_path, ws.root)

    if new_experiences:
        current_experiences = load_experiences(ws)
        current_experiences.extend(new_experiences)
        save_experiences(ws, current_experiences)
        print(
            f"{len(new_experiences)}개의 경험이 성공적으로 추출되어 저장되었습니다."
        )
        for exp in new_experiences:
            print(f"  - [{exp.evidence_level.value}] {exp.title}")
    else:
        print("경험을 추출하지 못했거나 파일 형식이 지원되지 않습니다.")


def cmd_crawl_base(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    source_path = Path(args.path) if args.path else None
    result = crawl_base(ws, source_path)
    print(f"Ingested {result['source_count']} source item(s).")
    print(f"Knowledge base now has {result['stored_count']} item(s).")
    print(f"Analysis written to {result['analysis_path']}")


def cmd_sync_base(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    source_path = Path(args.path) if args.path else None
    result = crawl_base(ws, source_path)
    print(f"Ingested {result['source_count']} source item(s).")
    print(f"Knowledge base now has {result['stored_count']} item(s).")
    print(f"Analysis written to {result['analysis_path']}")


def cmd_crawl_web(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = crawl_web_sources(ws, args.url)
    print(f"Ingested {result['source_count']} web source item(s).")
    print(f"Knowledge base now has {result['stored_count']} item(s).")
    print(f"Analysis written to {result['analysis_path']}")


def cmd_crawl_web_auto(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = crawl_web_sources_auto(
        ws,
        max_results_per_query=args.max_results_per_query,
        max_urls=args.max_urls,
    )
    print(f"Discovered {result['discovered_url_count']} candidate URL(s).")
    print(f"Ingested {result['ingested_url_count']} URL(s).")
    print(f"Knowledge base now has {result['stored_count']} item(s).")
    print(f"Discovery written to {result['discovery_path']}")


def cmd_refresh_live(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = refresh_live_web_sources(ws, args.url)
    print(f"Refreshed {len(args.url)} live URL(s).")
    print(
        "Change summary: "
        f"new={result['new_url_count']}, "
        f"changed={result['changed_url_count']}, "
        f"unchanged={result['unchanged_url_count']}"
    )
    print(f"Knowledge base now has {result['stored_count']} item(s).")
    print(f"Live updates written to {result['live_updates_path']}")


def cmd_my_gaps(args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    ws = Workspace(Path(args.workspace))
    result = run_gap_analysis(ws)
    report = result["report"]

    # 1. 요약 패널
    summary_text = "\n".join(f"  {line}" for line in report["summary"])
    console.print(
        Panel(
            summary_text,
            title="갭 분석 요약",
            border_style="cyan",
        )
    )

    # 2. 문항별 리스크 테이블
    question_risks = report.get("question_risks", [])
    if question_risks:
        risk_table = Table(show_header=True, header_style="bold magenta")
        risk_table.add_column("문항", width=6)
        risk_table.add_column("유형", width=12)
        risk_table.add_column("최고점", width=8)
        risk_table.add_column("리스크", width=8)

        for qr in question_risks:
            risk = qr.get("risk", "unknown")
            risk_style = {"low": "green", "medium": "yellow", "high": "red"}.get(
                risk, "dim"
            )
            risk_label = {"low": "낮음", "medium": "보통", "high": "높음"}.get(
                risk, risk
            )
            risk_table.add_row(
                f"Q{qr.get('order_no', '?')}",
                qr.get("question_type", "?"),
                str(qr.get("best_score", 0)),
                f"[{risk_style}]{risk_label}[/{risk_style}]",
            )
        console.print(risk_table)

    # 3. 경험별 결함 표시
    missing_metrics = report.get("missing_metrics", [])
    missing_evidence = report.get("missing_evidence", [])
    needs_verification = report.get("needs_verification", [])

    if missing_metrics or missing_evidence or needs_verification:
        gap_items = []
        if missing_metrics:
            gap_items.append(("[yellow]정량 수치 부족[/yellow]", missing_metrics))
        if missing_evidence:
            gap_items.append(("[yellow]증빙 텍스트 부족[/yellow]", missing_evidence))
        if needs_verification:
            gap_items.append(("[red]검증 필요[/red]", needs_verification))

        for label, items in gap_items:
            console.print(f"\n  {label}:")
            for item in items:
                console.print(f"    - {item}")

    # 4. 권고사항
    recommendations = report.get("recommendations", [])
    if recommendations:
        console.print(
            Panel(
                "\n".join(f"  {r}" for r in recommendations),
                title="권고사항",
                border_style="green",
            )
        )

    console.print(f"\n[dim]상세 리포트: {result['path']}[/dim]")


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
        exit_code = run_codex(
            Path(result["prompt_path"]), ws.root, output_path, tool=args.tool
        )
        print(f"Codex exit code: {exit_code}")
        print(f"Wrote coach Codex output to {output_path}")
    if getattr(args, "psychology_pack", False):
        from .interview_coach import InterviewCoach
        from .profiler import ApplicantProfiler
        from .state import load_experiences

        experiences = load_experiences(ws)
        profile = ApplicantProfiler().build_profile(experiences, profile_id="default")
        support_pack = InterviewCoach().build_support_pack(profile)
        print("\n[Psychology Pack]")
        for key, items in support_pack.items():
            print(f"{key}:")
            for item in items:
                print(f"- {item}")


def cmd_profile(args: argparse.Namespace) -> None:
    from .profiler import ApplicantProfiler
    from .state import load_experiences, upsert_profile_snapshot

    ws = Workspace(Path(args.workspace))
    ws.ensure()
    experiences = load_experiences(ws)
    profiler = ApplicantProfiler()
    profile = profiler.build_profile(
        experiences,
        past_answers=list(args.answer or []),
        profile_id="default",
    )
    upsert_profile_snapshot(ws, profile)

    print("Applicant profile updated.")
    print(f"- source_count: {profile.source_count}")
    print(f"- dominant_tone: {profile.writing_style.dominant_tone}")
    print(f"- strengths: {', '.join(profile.strength_keywords[:4])}")
    if profile.weakness_details:
        print(f"- weaknesses: {', '.join(profile.weakness_details[:3])}")
    if profile.coaching_priorities:
        print(f"- coaching: {', '.join(profile.coaching_priorities[:2])}")


def cmd_company(args: argparse.Namespace) -> None:
    from .company_profiler import CompanyProfiler
    from .state import load_experiences, load_project, load_success_cases
    from .profiler import ApplicantProfiler

    ws = Workspace(Path(args.workspace))
    ws.ensure()
    project = load_project(ws)
    if args.company_name:
        project.company_name = args.company_name
    if args.job_title:
        project.job_title = args.job_title
    if args.company_type:
        project.company_type = args.company_type

    jd_text = ""
    if getattr(args, "job_description_file", None):
        jd_text = Path(args.job_description_file).read_text(encoding="utf-8")

    experiences = load_experiences(ws)
    applicant_profile = ApplicantProfiler().build_profile(experiences, profile_id="default")
    result = CompanyProfiler(ws, load_success_cases(ws)).profile_company(
        project,
        job_description=jd_text,
        applicant_profile=applicant_profile,
    )

    print("Company profile updated.")
    print(f"- company: {result['company_name']}")
    print(f"- mission_keywords: {', '.join(result['mission_keywords']) or '-'}")
    print(f"- value_keywords: {', '.join(result['value_keywords']) or '-'}")
    print(f"- tailored_tips: {' / '.join(result['tailored_tips'])}")


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
        exit_code = run_codex(prompt_path, ws.root, output_path, tool=args.tool)
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
        exit_code = run_codex(prompt_path, ws.root, output_path, tool=args.tool)
        print(f"Codex exit code: {exit_code}")
        print(f"Wrote draft output to {output_path}")
    else:
        print(next_step("Run with --run-codex to generate a draft."))


def cmd_writer(args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()
    ws = Workspace(Path(args.workspace))

    patina_enabled = getattr(args, "patina", False)
    patina_mode = getattr(args, "patina_mode", "audit")
    patina_profile = getattr(args, "patina_profile", "resume")
    patina_max_enabled = getattr(args, "patina_max", False)
    patina_max_models = getattr(args, "patina_max_models", None)
    patina_max_dispatch = getattr(args, "patina_max_dispatch", None)

    if args.run_codex:
        result = run_writer_with_codex(
            ws,
            target_path=ws.resolve(args.target),
            tool=args.tool,
            patina=patina_enabled,
            patina_mode=patina_mode,
            patina_profile=patina_profile,
            patina_max=patina_max_enabled,
            patina_max_models=patina_max_models,
            patina_max_dispatch=patina_max_dispatch,
        )
        validation = result["validation"]
        approved = bool(result.get("approved"))

        # 1. 검증 결과 요약 패널
        if approved:
            console.print(
                Panel.fit(
                    "[bold green]Writer 검증 통과[/bold green]",
                    title="검증 결과",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel.fit(
                    "[bold red]❌ Writer 검증 실패[/bold red]",
                    title="검증 결과",
                    border_style="red",
                )
            )
            if validation["missing"]:
                missing_text = Text()
                for heading in validation["missing"]:
                    missing_text.append(f"  - {heading}\n", style="red")
                console.print(
                    Panel(
                        missing_text,
                        title="누락된 블록",
                        border_style="red",
                    )
                )

        # 2. 팩트 오딧 결과
        input_snapshot = {}
        try:
            from .state import load_artifacts

            artifacts = load_artifacts(ws)
            for art in reversed(artifacts):
                artifact_type = getattr(art, "artifact_type", None)
                if artifact_type and getattr(artifact_type, "name", "") == "WRITER":
                    input_snapshot = art.input_snapshot or {}
                    break
        except Exception:
            pass

        fact_warnings = input_snapshot.get("fact_warnings", [])
        if fact_warnings:
            fact_text = Text()
            for w in fact_warnings:
                fact_text.append(f"  {w}\n", style="yellow")
            console.print(
                Panel(
                    fact_text,
                    title="팩트 오딧 경고",
                    border_style="yellow",
                )
            )
            console.print(
                "[dim]수정 방법: experiences.json에 실제 수치를 추가하거나, 정성 표현으로 변경하세요.[/dim]"
            )
        else:
            console.print("[green]팩트 오딧: 경고 없음[/green]")

        # 3. 가독성 점수
        readability = input_snapshot.get("readability", {})
        if readability:
            score = readability.get("score", 0)
            feedback_list = readability.get("feedback", [])
            score_style = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            console.print(
                f"\n[{score_style}]가독성 점수: {score}/100[/{score_style}]"
            )
            if feedback_list and score < 100:
                for fb in feedback_list:
                    console.print(f"  [dim]- {fb}[/dim]")

        # 4. 답변 품질 평가
        quality_evals = input_snapshot.get("quality_evaluations", [])
        if quality_evals:
            console.print("\n[bold]답변 품질 평가[/bold]")
            q_table = Table(show_header=True, header_style="bold cyan")
            q_table.add_column("문항", width=4)
            q_table.add_column("관련성", width=8)
            q_table.add_column("구체성", width=8)
            q_table.add_column("방어력", width=8)
            q_table.add_column("독창성", width=8)
            q_table.add_column("종합", width=8)

            for qe in quality_evals:
                overall = qe.get("overall_score", 0)
                overall_style = (
                    "green" if overall >= 0.7 else "yellow" if overall >= 0.5 else "red"
                )
                q_table.add_row(
                    qe.get("question_id", "?"),
                    f"{qe.get('relevance_score', 0):.0%}",
                    f"{qe.get('specificity_score', 0):.0%}",
                    f"{qe.get('defensibility_score', 0):.0%}",
                    f"{qe.get('originality_score', 0):.0%}",
                    f"[{overall_style}]{overall:.0%}[/{overall_style}]",
                )
            console.print(q_table)

            # 개선 제안
            for qe in quality_evals:
                suggestions = qe.get("suggestions", [])
                if suggestions:
                    console.print(
                        f"\n  [cyan]{qe.get('question_id', '?')} 개선 제안:[/cyan]"
                    )
                    for s in suggestions[:2]:
                        console.print(f"    - {s}")

        # 5. 최종 결과 요약
        artifact_path = Path(result["artifact_path"])
        draft_path = Path(result.get("draft_path") or "")
        error_output_path = Path(result.get("error_output_path") or "")
        raw_output_path = Path(result["raw_output_path"])
        selected_tool = result.get("selected_tool") or input_snapshot.get(
            "selected_tool", args.tool
        )
        attempted_tools = result.get("attempted_tools") or input_snapshot.get(
            "attempted_tools", []
        )
        fallback_reason = result.get("fallback_reason") or input_snapshot.get(
            "fallback_reason"
        )
        if approved and artifact_path.exists():
            console.print(f"\n[dim]출력 파일: {artifact_path}[/dim]")
        else:
            console.print("\n[dim]출력 파일: 승인 산출물 미생성[/dim]")
            if str(draft_path) and draft_path.exists():
                console.print(f"[dim]최종 초안: {draft_path}[/dim]")
            elif str(error_output_path) and error_output_path.exists():
                console.print(f"[dim]실행 오류 기록: {error_output_path}[/dim]")
        console.print(f"[dim]Raw 출력: {raw_output_path}[/dim]")
        console.print(f"[dim]최종 모델: {selected_tool or args.tool}[/dim]")
        if attempted_tools:
            console.print(f"[dim]시도한 모델: {', '.join(attempted_tools)}[/dim]")
        console.print(
            f"[dim]폴백 발생: {'예' if fallback_reason else '아니오'}[/dim]"
        )
        if fallback_reason:
            console.print(f"[dim]폴백 사유: {fallback_reason}[/dim]")
        console.print(f"[dim]승인본 생성: {'예' if approved else '아니오'}[/dim]")

        # 6. patina 결과 표시
        patina_result = result.get("patina_result")
        if patina_result:
            console.print("\n[bold magenta]━━━ patina AI 패턴 분석 ━━━[/bold magenta]")

            p_mode = patina_result.get("mode", "audit")
            p_tool = patina_result.get("tool", "?")

            if p_mode == "audit":
                console.print(f"[dim]모드: audit | 도구: {p_tool}[/dim]")
                raw = patina_result.get("raw_output", "")
                if raw:
                    console.print(
                        Panel(
                            raw[:3000],
                            title="patina 감지 결과",
                            border_style="magenta",
                        )
                    )
                else:
                    console.print("[yellow]감지 결과가 없습니다.[/yellow]")

            elif p_mode == "score":
                console.print(f"[dim]모드: score | 도구: {p_tool}[/dim]")
                raw = patina_result.get("raw_output", "")
                if raw:
                    console.print(
                        Panel(
                            raw[:3000],
                            title="patina AI 유사도 점수",
                            border_style="magenta",
                        )
                    )

            elif p_mode in ("rewrite", "ouroboros"):
                console.print(f"[dim]모드: {p_mode} | 도구: {p_tool}[/dim]")
                char_deltas = patina_result.get("char_deltas", {})
                if char_deltas:
                    d_table = Table(show_header=True, header_style="bold magenta")
                    d_table.add_column("문항", width=4)
                    d_table.add_column("원본", width=8)
                    d_table.add_column("교정 후", width=8)
                    d_table.add_column("변동", width=10)

                    for q_id, delta in sorted(char_deltas.items()):
                        d_style = "red" if abs(delta["delta_pct"]) > 5 else "green"
                        d_table.add_row(
                            q_id,
                            f"{delta['original_chars']}자",
                            f"{delta['new_chars']}자",
                            f"[{d_style}]{delta['delta_pct']:+.1f}%[/]",
                        )
                    console.print(d_table)

                reassembled = patina_result.get("reassembled_text")
                if reassembled:
                    patina_out = ws.artifacts_dir / "writer_draft_patina.md"
                    patina_out.write_text(reassembled, encoding="utf-8")
                    console.print(f"[dim]patina 교정 결과: {patina_out}[/dim]")

            # 경고 표시
            warnings = patina_result.get("warnings", [])
            for w in warnings:
                console.print(f"  [yellow]⚠️ {w}[/yellow]")

        patina_max_result = result.get("patina_max_result")
        if patina_max_result:
            console.print("\n[bold magenta]━━━ patina-max 멀티모델 분석 ━━━[/bold magenta]")
            models = patina_max_result.get("models", [])
            selected_model = patina_max_result.get("selected_model")
            dispatch = patina_max_result.get("dispatch", "direct")
            if models:
                console.print(f"[dim]사용 모델: {', '.join(models)}[/dim]")
            console.print(f"[dim]디스패치: {dispatch}[/dim]")
            console.print(
                f"[dim]선택 모델: {selected_model or '선택 실패 (writer 원문 유지)'}[/dim]"
            )

            outputs_by_model = patina_max_result.get("outputs_by_model", {})
            if outputs_by_model:
                m_table = Table(show_header=True, header_style="bold magenta")
                m_table.add_column("모델", width=12)
                m_table.add_column("상태", width=10)
                m_table.add_column("문항보존", width=8)
                m_table.add_column("제한이슈", width=10)
                m_table.add_column("변동합", width=10)
                for model_name, meta in outputs_by_model.items():
                    success = bool(meta.get("success"))
                    processed_count = int(meta.get("processed_count", 0))
                    issue_count = len(
                        (meta.get("char_limit_report") or {}).get("issues", [])
                    )
                    total_abs_delta = int(meta.get("total_abs_delta", 0))
                    status_text = "[green]성공[/green]" if success else "[red]실패[/red]"
                    m_table.add_row(
                        model_name,
                        status_text,
                        str(processed_count),
                        str(issue_count),
                        str(total_abs_delta),
                    )
                console.print(m_table)

            reassembled = patina_max_result.get("reassembled_text")
            if reassembled:
                patina_max_out = ws.artifacts_dir / "writer_draft_patina_max.md"
                patina_max_out.write_text(reassembled, encoding="utf-8")
                console.print(f"[dim]patina-max 교정 결과: {patina_max_out}[/dim]")

            warnings = patina_max_result.get("warnings", [])
            for w in warnings:
                console.print(f"  [yellow]⚠️ {w}[/yellow]")

    else:
        result = run_writer(ws, ws.resolve(args.target))
        print(f"Prompt written to {result['prompt_path']}")
        print(next_step("Run with --run-codex to generate a writer artifact."))


def cmd_interview(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    if args.run_codex:
        result = run_interview_with_codex(ws, tool=args.tool)
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
    print(
        f"{args.workspace}에 대해 심층 압박 면접 시뮬레이션을 시작합니다..."
    )
    result = run_deep_interview(ws)
    print(f"심층 면접 팩 생성 완료: {result['path']}")
    print(f"{result['count']}개의 질문에 대해 꼬리 질문이 생성되었습니다.")


def cmd_self_intro(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = run_self_intro(ws)
    print(f"자기소개 팩 생성 완료: {result['path']}")
    print(f"📦 분석 데이터: {result['analysis_path']}")


def cmd_export(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    result = run_export(ws)
    print(f"Export markdown written to {result['markdown_path']}")
    print(f"Export json written to {result['json_path']}")
    if result.get("docx_path"):
        print(f"Export docx written to {result['docx_path']}")
    print(f"Accepted artifacts bundled: {result['accepted_count']}")


def cmd_review(args: argparse.Namespace) -> None:
    ws = Workspace(Path(args.workspace))
    target_path = ws.resolve(args.target)
    draft_path = ws.resolve(args.draft)
    prompt_path = build_review_prompt(ws, draft_path, target_path)
    print(f"Prompt written to {prompt_path}")
    if args.run_codex:
        output_path = ws.outputs_dir / "latest_review.md"
        exit_code = run_codex(prompt_path, ws.root, output_path, tool=args.tool)
        print(f"Codex exit code: {exit_code}")
        print(f"Wrote review output to {output_path}")
    else:
        print(next_step("Run with --run-codex to critique the draft."))


def cmd_company_research(args: argparse.Namespace) -> None:
    """기업·직무 조사 프롬프트 빌드 또는 Codex 실행"""
    ws = Workspace(Path(args.workspace))
    if args.auto_web:
        auto_result = crawl_web_sources_auto(
            ws,
            max_results_per_query=args.max_results_per_query,
            max_urls=args.max_urls,
        )
        print(
            "Auto web research: "
            f"{auto_result['discovered_url_count']}개 후보 URL, "
            f"{auto_result['ingested_url_count']}개 ingest"
        )
    if getattr(args, "refresh_live", False):
        refresh_result = refresh_existing_public_sources(ws)
        print(
            "Live refresh: "
            f"{refresh_result['tracked_url_count']}개 추적 URL, "
            f"changed={refresh_result['changed_url_count']}, "
            f"unchanged={refresh_result['unchanged_url_count']}"
        )
    prompt_path = build_company_research_prompt(ws)
    if args.run_codex:
        result = run_company_research_with_codex(ws, tool=args.tool)
        print(f"Codex exit code: {result['exit_code']}")
        print(f"Wrote company research output to {result['artifact_path']}")
        print(f"Source trace written to {result['source_trace_path']}")
    else:
        print(f"Company research prompt written to {prompt_path}")
        print(next_step("Run with --run-codex to generate the research."))


def next_step(message: str) -> str:
    return dedent(
        f"""\
        Next step:
          {message}
        """
    ).rstrip()


def cmd_resume(args: argparse.Namespace) -> None:
    """체크포인트 기반 파이프라인 재시작"""
    from .checkpoint import CheckpointManager
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    ws = Workspace(Path(args.workspace))
    ws.ensure()

    cp_mgr = CheckpointManager(ws.root)
    resume_point = cp_mgr.get_resume_point()

    if resume_point is None:
        console.print(
            Panel.fit(
                "[yellow]재시작할 체크포인트가 없습니다.[/yellow]\n"
                "먼저 다음 명령어로 파이프라인을 실행하세요:\n"
                "  resume-agent coach <workspace>",
                title="체크포인트 없음",
                border_style="yellow",
            )
        )
        return

    pipeline_order = ["coach", "writer", "interview", "export"]
    completed_steps = set(cp_mgr.list_checkpoints())
    remaining_steps = []
    start_index = (
        pipeline_order.index(resume_point) + 1 if resume_point in pipeline_order else 0
    )

    for step in pipeline_order[start_index:]:
        if step not in completed_steps:
            remaining_steps.append(step)

    if not remaining_steps:
        console.print(
            Panel.fit(
                "[green]모든 파이프라인 단계가 완료되었습니다.[/green]",
                title="파이프라인 완료",
                border_style="green",
            )
        )
        return

    next_step_name = remaining_steps[0]
    console.print(
        Panel.fit(
            f"[cyan]마지막 완료 단계: {resume_point}[/cyan]\n"
            f"[bold]다음 단계: {next_step_name}[/bold]\n"
            f"남은 단계: {', '.join(remaining_steps)}",
            title="파이프라인 재시작",
            border_style="cyan",
        )
    )

    # 다음 단계 실행
    if next_step_name == "coach":
        result = run_coach(ws)
        console.print(f"[green]coach 완료[/green]")
    elif next_step_name == "writer":
        result = run_writer_with_codex(ws)
        console.print(f"[green]writer 완료[/green]")
    elif next_step_name == "interview":
        result = run_interview_with_codex(ws)
        console.print(f"[green]interview 완료[/green]")
    elif next_step_name == "export":
        result = run_export(ws)
        console.print(f"[green]export 완료[/green]")
    else:
        console.print(f"[red]알 수 없는 단계: {next_step_name}[/red]")
        return

    console.print(f"\n[dim]다음 단계를 계속하려면: resume-agent resume {ws.root}[/dim]")


def cmd_mock_interview(args: argparse.Namespace) -> None:
    """대화형 모의면접 실행"""
    from .interactive import run_mock_interview

    ws = Workspace(Path(args.workspace))
    ws.ensure()

    print(f"모의면접 모드: {args.mode}")
    run_mock_interview(ws, args.mode)


def cmd_feedback(args: argparse.Namespace) -> None:
    """아티팩트에 대한 사용자 피드백 기록"""
    from .feedback_learner import create_feedback_learner
    from .pipeline import _build_feedback_pattern_id, _build_feedback_selection_payload
    from .state import load_project
    from .utils import read_json_if_exists

    ws = Workspace(Path(args.workspace))
    ws.ensure()

    accepted = not args.rejected
    learner = create_feedback_learner(str(ws.root / "kb" / "feedback"))
    project = load_project(ws)

    artifact_id = f"{args.artifact}-manual-{int(time.time())}"
    pattern = _build_feedback_pattern_id(args.artifact, project)
    question_types = [
        question.detected_type.value
        for question in project.questions
        if getattr(question, "detected_type", None)
    ]
    selection_payload = _build_feedback_selection_payload(
        read_json_if_exists(ws.analysis_dir / "question_map.json"),
        writer_brief=read_json_if_exists(ws.analysis_dir / "writer_brief.json"),
    )

    learner.record_feedback(
        draft_id=artifact_id,
        pattern_used=pattern,
        accepted=accepted,
        rating=args.rating,
        comment=args.comment,
        artifact_type=args.artifact,
        company_name=project.company_name,
        job_title=project.job_title,
        company_type=project.company_type,
        question_types=question_types,
        stage=args.artifact,
        final_outcome=args.final_outcome,
        rejection_reason=args.rejection_reason,
        selected_experience_ids=selection_payload["selected_experience_ids"],
        question_experience_map=selection_payload["question_experience_map"],
        question_strategy_map=selection_payload.get("question_strategy_map", {}),
    )

    status = "수락" if accepted else "거부"
    rating_str = f", 평점: {args.rating}/5" if args.rating else ""
    comment_str = f", 코멘트: {args.comment}" if args.comment else ""
    outcome_str = f", 결과: {args.final_outcome}" if args.final_outcome else ""
    reason_str = f", 사유: {args.rejection_reason}" if args.rejection_reason else ""
    print(
        f"피드백 기록 완료: {args.artifact} - {status}{rating_str}{comment_str}{outcome_str}{reason_str}"
    )
    if not args.final_outcome:
        print("다음 단계 결과 기록 예시:")
        print(
            f"  python -m resume_agent.cli feedback {args.workspace} --artifact {args.artifact} "
            "--accepted --final-outcome document_pass"
        )
        print(
            f"  python -m resume_agent.cli feedback {args.workspace} --artifact {args.artifact} "
            '--rejected --final-outcome interview_fail --rejection-reason "근거 부족"'
        )

    # 인사이트 출력
    insights = learner.get_insights()
    if insights["total_feedback"] > 0:
        print(f"\n전체 통계:")
        print(f"  - 총 피드백: {insights['total_feedback']}건")
        print(f"  - 전체 성공률: {insights['overall_success_rate']:.0%}")
        print(f"  - 평균 평점: {insights['average_rating']:.1f}/5")


def cmd_benchmark_blind(args: argparse.Namespace) -> None:
    """블라인드 벤치마크 프레임 생성"""
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    project = load_project(ws)
    frame = build_blind_benchmark_frame(ws, project=project)
    path = ws.analysis_dir / "blind_benchmark_frame.json"
    print(f"블라인드 벤치마크 프레임 생성 완료: {path}")
    print(f"  - 비교 후보 수: {frame['candidate_count']}")
    print(f"  - 평가 문항 수: {len(frame['questions'])}")


def cmd_status(args: argparse.Namespace) -> None:
    """파이프라인 현재 상태 대시보드 출력"""
    from .checkpoint import CheckpointManager
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    ws = Workspace(Path(args.workspace))
    ws.ensure()

    # 체크포인트 상태
    cp_mgr = CheckpointManager(ws.root)
    checkpoints = cp_mgr.list_checkpoints()
    pipeline_steps = ["coach", "writer", "interview", "export"]

    # 파이프라인 진행 상태 테이블
    table = Table(show_header=True, header_style="bold cyan", title="파이프라인 상태")
    table.add_column("단계", width=12)
    table.add_column("상태", width=10)
    table.add_column("체크포인트", width=20)

    for step in pipeline_steps:
        if step in checkpoints:
            info = cp_mgr.get_checkpoint_info(step)
            ts = info["timestamp"][:19] if info else "?"
            table.add_row(step.upper(), "[green]완료[/green]", ts)
        else:
            table.add_row(step.upper(), "[dim]대기[/dim]", "-")

    console.print(table)

    # 아티팩트 상태
    try:
        artifacts = load_artifacts(ws)
        if artifacts:
            art_table = Table(
                show_header=True, header_style="bold magenta", title="아티팩트 상태"
            )
            art_table.add_column("타입", width=12)
            art_table.add_column("상태", width=8)
            art_table.add_column("생성 시각", width=20)

            latest = {}
            for a in sorted(artifacts, key=lambda x: x.created_at):
                latest[a.artifact_type.value] = a

            for atype, artifact in latest.items():
                status = (
                    "[green]수락[/green]" if artifact.accepted else "[red]거부[/red]"
                )
                ts = str(artifact.created_at)[:19]
                art_table.add_row(atype.upper(), status, ts)

            console.print(art_table)
    except Exception:
        pass

    try:
        dashboard = read_json_if_exists(ws.analysis_dir / "outcome_dashboard.json")
        if dashboard:
            console.print(
                Panel(
                    f"아티팩트: {dashboard.get('artifact_type', '-')}\n"
                    f"권장 패턴: {dashboard.get('recommended_pattern', '-')}\n"
                    f"성공률: {dashboard.get('overall_success_rate', 0)}\n"
                    f"고위험 패턴 수: {len(dashboard.get('high_risk_hotspots', []))}",
                    title="Outcome Dashboard",
                    border_style="magenta",
                )
            )
    except Exception:
        pass

    # 프로젝트 정보
    try:
        project = load_project(ws)
        if project.company_name or project.job_title:
            console.print(
                Panel(
                    f"회사: {project.company_name or '-'}\n"
                    f"직무: {project.job_title or '-'}\n"
                    f"경력단계: {project.career_stage or '-'}",
                    title="프로젝트 정보",
                    border_style="blue",
                )
            )
    except Exception:
        pass


def cmd_history(args: argparse.Namespace) -> None:
    """아티팩트 생성 히스토리 출력"""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    ws = Workspace(Path(args.workspace))
    ws.ensure()

    try:
        artifacts = load_artifacts(ws)
    except Exception:
        artifacts = []

    if not artifacts:
        console.print("[yellow]생성된 아티팩트가 없습니다.[/yellow]")
        return

    # 실행 히스토리
    runs_dir = ws.runs_dir
    if runs_dir.exists():
        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], reverse=True)
        if run_dirs:
            console.print("[bold]실행 히스토리 (최근 10개):[/bold]")
            for rd in run_dirs[:10]:
                files = list(rd.glob("*.json"))
                file_names = ", ".join(f.stem for f in files)
                console.print(f"  {rd.name}: {file_names}")
            console.print()

    # 아티팩트 테이블
    table = Table(show_header=True, header_style="bold cyan", title="아티팩트 히스토리")
    table.add_column("ID", width=25)
    table.add_column("타입", width=12)
    table.add_column("상태", width=8)
    table.add_column("생성 시각", width=20)

    for artifact in sorted(artifacts, key=lambda x: x.created_at, reverse=True)[:20]:
        status = "[green]수락[/green]" if artifact.accepted else "[red]거부[/red]"
        ts = str(artifact.created_at)[:19]
        table.add_row(artifact.id, artifact.artifact_type.value.upper(), status, ts)

    console.print(table)


def cmd_outcome_record(args: argparse.Namespace) -> None:
    """지원 결과 기록"""
    from .outcome_tracker import OutcomeTracker
    from .models import OutcomeResult
    
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    
    tracker = OutcomeTracker(ws)
    outcome = OutcomeResult(
        artifact_id=args.artifact_id,
        application_id=args.application_id,
        company_name=args.company,
        job_title=args.job_title,
        outcome=args.outcome
    )
    result = tracker.record_outcome(outcome)
    print(f"결과 기록 완료: {result.artifact_id} -> {result.outcome}")
    print(f"   회사: {result.company_name}, 직무: {result.job_title}")

    artifact_prefix = str(result.artifact_id).split("-", 1)[0].strip().lower()
    artifact_type = {
        "writer": "writer",
        "interview": "interview",
        "coach": "coach",
        "company_research": "company_research",
    }.get(artifact_prefix)
    if artifact_type:
        project = load_project(ws)
        build_outcome_dashboard(ws, project, artifact_type)
        build_kpi_dashboard(ws, project, artifact_type)


def cmd_outcome_list(args: argparse.Namespace) -> None:
    """지원 결과 목록 조회"""
    from rich.console import Console
    from rich.table import Table
    from .outcome_tracker import OutcomeTracker
    
    console = Console()
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    
    tracker = OutcomeTracker(ws)
    outcomes = tracker.get_all_outcomes()
    
    if args.company:
        outcomes = [o for o in outcomes if args.company.lower() in o.company_name.lower()]
    
    if not outcomes:
        console.print("[yellow]기록된 결과가 없습니다.[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold cyan", title="지원 결과 목록")
    table.add_column("아티팩트 ID", width=30)
    table.add_column("회사", width=20)
    table.add_column("직무", width=15)
    table.add_column("결과", width=15)
    
    outcome_labels = {
        "pending": "대기",
        "screening_pass": "서류 통과",
        "screening_fail": "서류 탈락",
        "interview_invited": "면접 초대",
        "interview_pass": "면접 통과",
        "interview_fail": "면접 탈락",
        "final_pass": "최종 합격",
        "final_fail": "최종 탈락",
        "offer_received": "합격",
        "offer_declined": "사직",
    }
    
    for o in sorted(outcomes, key=lambda x: x.artifact_id, reverse=True):
        outcome_text = outcome_labels.get(o.outcome, o.outcome)
        outcome_style = "green" if o.outcome in ["offer_received", "final_pass", "interview_pass", "screening_pass"] else "red" if o.outcome in ["screening_fail", "interview_fail", "final_fail"] else "yellow"
        table.add_row(
            o.artifact_id,
            o.company_name,
            o.job_title,
            f"[{outcome_style}]{outcome_text}[/{outcome_style}]"
        )
    
    console.print(table)


def cmd_outcome_summary(args: argparse.Namespace) -> None:
    """지원 결과 요약 통계"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from .outcome_tracker import OutcomeTracker
    
    console = Console()
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    
    tracker = OutcomeTracker(ws)
    summary = tracker.get_outcome_summary()
    total = sum(summary.values())
    success_rate = tracker.get_success_rate()
    
    outcome_labels = {
        "pending": "대기",
        "screening_pass": "서류 통과",
        "screening_fail": "서류 탈락",
        "interview_invited": "면접 초대",
        "interview_pass": "면접 통과",
        "interview_fail": "면접 탈락",
        "final_pass": "최종 합격",
        "final_fail": "최종 탈락",
        "offer_received": "합격",
    }
    
    table = Table(show_header=True, header_style="bold cyan", title="결과 요약")
    table.add_column("구분", width=15)
    table.add_column("건수", width=8)
    table.add_column("비율", width=10)
    
    for key, label in outcome_labels.items():
        count = summary.get(key, 0)
        pct = (count / total * 100) if total > 0 else 0
        table.add_row(label, str(count), f"{pct:.1f}%")
    
    console.print(table)
    console.print(f"\n[bold]전체 성공률:[/bold] {success_rate:.1%}")
    console.print(f"[bold]총 지원 수:[/bold] {total}건")


def cmd_ab_record(args: argparse.Namespace) -> None:
    """A/B 테스트 결과 기록"""
    from .ab_testing import ABTest
    
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    
    ab_test = ABTest(ws)
    success = args.success and not args.fail
    ab_test.record_result(args.variant, success)
    
    print(f"기록 완료: Variant {args.variant} -> {'성공' if success else '실패'}")
    
    test = ab_test.get_current_test()
    if test:
        print(f"\n현재 테스트 상태:")
        print(f"  Variant A: {test.sample_size_a}개 ({test.success_rate_a:.1%})")
        print(f"  Variant B: {test.sample_size_b}개 ({test.success_rate_b:.1%})")
        if test.is_significant:
            print(f"  → 통계적으로 유의미한 결과! Winner: {test.winner}")


def cmd_ab_status(args: argparse.Namespace) -> None:
    """A/B 테스트 상태 조회"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from .ab_testing import ABTest
    
    console = Console()
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    
    ab_test = ABTest(ws)
    test = ab_test.get_current_test()
    
    if not test:
        console.print("[yellow]진행 중인 테스트가 없습니다.[/yellow]")
        return
    
    status_text = "[green]진행 중[/green]" if test.end_date is None else "[red]종료됨[/red]"
    recommend = ab_test.recommend_variant()
    
    console.print(
        Panel(
            f"테스트 ID: {test.test_id}\n"
            f"테스트 이름: {test.test_name}\n"
            f"상태: {status_text}\n"
            f"권장 Variant: {recommend}",
            title=f"A/B 테스트: {test.test_name}",
            border_style="cyan",
        )
    )
    
    table = Table(show_header=True, header_style="bold magenta", title="Variant 통계")
    table.add_column("Variant", width=10)
    table.add_column("전략", width=15)
    table.add_column("샘플 수", width=10)
    table.add_column("성공률", width=10)
    table.add_column("p-value", width=10)
    table.add_column("유의미", width=10)
    
    winner_style_a = "bold green" if test.winner == "A" else None
    winner_style_b = "bold green" if test.winner == "B" else None
    
    sig_a = "✓" if test.is_significant and test.winner == "A" else ""
    sig_b = "✓" if test.is_significant and test.winner == "B" else ""
    
    cell_a = f"[bold green]A[/]" if winner_style_a else "A"
    cell_b = f"[bold green]B[/]" if winner_style_b else "B"
    
    table.add_row(
        cell_a,
        test.strategy_a,
        str(test.sample_size_a),
        f"{test.success_rate_a:.1%}",
        f"{test.p_value:.3f}" if test.p_value else "-",
        sig_a
    )
    table.add_row(
        cell_b,
        test.strategy_b,
        str(test.sample_size_b),
        f"{test.success_rate_b:.1%}",
        f"{test.p_value:.3f}" if test.p_value else "-",
        sig_b
    )
    
    console.print(table)


def cmd_ab_end(args: argparse.Namespace) -> None:
    """A/B 테스트 종료"""
    from rich.console import Console
    from rich.panel import Panel
    from .ab_testing import ABTest
    
    console = Console()
    ws = Workspace(Path(args.workspace))
    ws.ensure()
    
    ab_test = ABTest(ws)
    test = ab_test.end_test()
    
    if not test:
        console.print("[yellow]종료할 테스트가 없습니다.[/yellow]")
        return
    
    winner = test.winner or "결정되지 않음"
    winner_strategy = test.strategy_a if winner == "A" else test.strategy_b if winner == "B" else "-"
    
    console.print(
        Panel(
            f"테스트 ID: {test.test_id}\n"
            f"최종 Winner: {winner}\n"
            f"Winner 전략: {winner_strategy}\n"
            f"Variant A 성공률: {test.success_rate_a:.1%} ({test.sample_size_a}개)\n"
            f"Variant B 성공률: {test.success_rate_b:.1%} ({test.sample_size_b}개)",
            title="A/B 테스트 종료",
            border_style="green",
        )
    )
    
    if test.is_significant:
        console.print(f"\n[green]통계적으로 유의미한 결과입니다![/green]")
        console.print(f"   {winner_strategy} 전략을 기본으로 채택하세요.")
    else:
        console.print(f"\n[yellow]통계적으로 유의미한 차이가 없습니다.[/yellow]")
        console.print(f"   더 많은 샘플이 필요합니다.")
