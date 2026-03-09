from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .domain import (
    analyze_gaps,
    build_knowledge_hints,
    build_coach_artifact,
    ingest_source_file,
    summarize_knowledge_sources,
    validate_block_contract,
    validate_coach_contract,
)
from .state import (
    initialize_state,
    load_artifacts,
    load_experiences,
    load_knowledge_sources,
    load_project,
    save_knowledge_sources,
    upsert_artifact,
    write_json,
)
from .templates import (
    INIT_EXPERIENCE_BANK,
    INIT_FACTS,
    INIT_TARGET,
    PROMPT_COACH,
    PROMPT_ANALYZE,
    PROMPT_DRAFT,
    PROMPT_INTERVIEW,
    PROMPT_REVIEW,
    PROMPT_WRITER,
    STATE_EXPERIENCE_GUIDE,
    STATE_PROFILE_GUIDE,
)
from .workspace import Workspace


def init_workspace(root: Path) -> Workspace:
    ws = Workspace(root=root)
    ws.ensure()
    initialize_state(ws)

    write_if_missing(ws.profile_dir / "facts.md", INIT_FACTS)
    write_if_missing(ws.profile_dir / "experience_bank.md", INIT_EXPERIENCE_BANK)
    write_if_missing(ws.targets_dir / "example_target.md", INIT_TARGET)
    write_if_missing(ws.profile_dir / "state_profile_guide.md", STATE_PROFILE_GUIDE)
    write_if_missing(ws.profile_dir / "state_experience_guide.md", STATE_EXPERIENCE_GUIDE)

    write_if_missing(
        ws.prompts_dir / "analyze_template.md",
        PROMPT_ANALYZE,
    )
    write_if_missing(
        ws.prompts_dir / "draft_template.md",
        PROMPT_DRAFT,
    )
    write_if_missing(
        ws.prompts_dir / "coach_template.md",
        PROMPT_COACH,
    )
    write_if_missing(
        ws.prompts_dir / "writer_template.md",
        PROMPT_WRITER,
    )
    write_if_missing(
        ws.prompts_dir / "interview_template.md",
        PROMPT_INTERVIEW,
    )
    write_if_missing(
        ws.prompts_dir / "review_template.md",
        PROMPT_REVIEW,
    )
    return ws


def setup_workspace(root: Path) -> Workspace:
    return init_workspace(root)


def crawl_base(ws: Workspace, source_path: Path | None = None) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    paths = collect_source_paths(ws, source_path)
    ingested: list[dict[str, Any]] = []

    for path in paths:
        if path.is_file() and source_path and path.resolve().parent != ws.sources_raw_dir.resolve():
            copied = ws.sources_raw_dir / path.name
            if not copied.exists():
                shutil.copy2(path, copied)
        for source in ingest_source_file(path):
            write_source_artifacts(ws, source)
            ingested.append(source)

    merged = merge_sources(load_knowledge_sources(ws), ingested)
    save_knowledge_sources(ws, merged)
    summary = summarize_knowledge_sources(merged)
    summary_path = ws.analysis_dir / "knowledge_hints.json"
    write_json(summary_path, merged)
    return {
        "source_count": len(ingested),
        "stored_count": len(merged),
        "summary": summary,
        "analysis_path": str(summary_path),
    }


def run_gap_analysis(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    experiences = load_experiences(ws)
    report = analyze_gaps(project, experiences)
    path = ws.analysis_dir / "gap_report.json"
    write_json(path, report)
    return {"report": report, "path": str(path)}


def run_coach(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    experiences = load_experiences(ws)
    gap_report = analyze_gaps(project, experiences)
    artifact = build_coach_artifact(project, experiences, gap_report)
    validation = validate_coach_contract(artifact["rendered"])

    write_json(ws.analysis_dir / "question_map.json", artifact["allocations"])
    write_json(ws.analysis_dir / "gap_report.json", gap_report)
    coach_prompt_path = build_coach_prompt(ws, artifact, gap_report)
    coach_path = ws.artifacts_dir / "coach.md"
    coach_path.write_text(artifact["rendered"], encoding="utf-8")

    artifact_id = f"coach-{timestamp_slug()}"
    snapshot = {
        "id": artifact_id,
        "artifact_type": "COACH",
        "accepted": validation["passed"],
        "input_snapshot": {
            "project": project,
            "experience_count": len(experiences),
        },
        "output_path": str(coach_path.relative_to(ws.root)),
        "raw_output_path": str(coach_path.relative_to(ws.root)),
        "validation": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    upsert_artifact(ws, snapshot)
    run_dir = ws.runs_dir / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "coach.json", {"artifact": artifact, "validation": validation})
    return {
        "artifact": artifact,
        "validation": validation,
        "path": str(coach_path),
        "prompt_path": str(coach_prompt_path),
    }


def run_writer(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    prompt_path = build_draft_prompt(ws, ws.targets_dir / "example_target.md")
    return {"prompt_path": str(prompt_path)}


def run_writer_with_codex(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    prompt_path = build_draft_prompt(ws, ws.targets_dir / "example_target.md")
    run_dir = ws.runs_dir / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = run_dir / "raw_writer.md"
    exit_code = run_codex(prompt_path, ws.root, raw_output_path)
    headings = [
        "## ASSUMPTIONS & MISSING FACTS",
        "## OUTLINE",
        "## DRAFT ANSWERS",
        "## SELF-CHECK",
    ]
    raw_text = safe_read_text(raw_output_path)
    normalized_text = normalize_contract_output(raw_text, headings)
    validation = validate_block_contract(normalized_text, headings)
    accepted_path = ws.artifacts_dir / "writer.md"
    if validation["passed"]:
        accepted_path.write_text(normalized_text, encoding="utf-8")
    snapshot = {
        "id": f"writer-{timestamp_slug()}",
        "artifact_type": "WRITER",
        "accepted": validation["passed"],
        "input_snapshot": {
            "project": load_project(ws),
            "question_map_path": str((ws.analysis_dir / "question_map.json").relative_to(ws.root)),
        },
        "output_path": str(accepted_path.relative_to(ws.root)),
        "raw_output_path": str(raw_output_path.relative_to(ws.root)),
        "validation": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    upsert_artifact(ws, snapshot)
    write_json(run_dir / "writer.json", {"validation": validation, "exit_code": exit_code})
    return {
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "validation": validation,
        "exit_code": exit_code,
    }


def run_interview(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    prompt_path = build_interview_prompt(ws)
    return {"prompt_path": str(prompt_path)}


def run_interview_with_codex(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    prompt_path = build_interview_prompt(ws)
    run_dir = ws.runs_dir / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = run_dir / "raw_interview.md"
    exit_code = run_codex(prompt_path, ws.root, raw_output_path)
    headings = [
        "## INTERVIEW ASSUMPTIONS",
        "## INTERVIEW STRATEGY",
        "## EXPECTED QUESTIONS MAP",
        "## ANSWER FRAMES",
        "## FINAL CHECK",
    ]
    raw_text = safe_read_text(raw_output_path)
    normalized_text = normalize_contract_output(raw_text, headings)
    validation = validate_block_contract(normalized_text, headings)
    accepted_path = ws.artifacts_dir / "interview.md"
    if validation["passed"]:
        accepted_path.write_text(normalized_text, encoding="utf-8")
    snapshot = {
        "id": f"interview-{timestamp_slug()}",
        "artifact_type": "INTERVIEW",
        "accepted": validation["passed"],
        "input_snapshot": {
            "project": load_project(ws),
            "writer_artifact_exists": (ws.artifacts_dir / "writer.md").exists(),
        },
        "output_path": str(accepted_path.relative_to(ws.root)),
        "raw_output_path": str(raw_output_path.relative_to(ws.root)),
        "validation": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    upsert_artifact(ws, snapshot)
    write_json(run_dir / "interview.json", {"validation": validation, "exit_code": exit_code})
    return {
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "validation": validation,
        "exit_code": exit_code,
    }


def run_export(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    artifacts = load_artifacts(ws)
    accepted = latest_accepted_artifacts(artifacts, ["COACH", "WRITER", "INTERVIEW"])
    writer_text = safe_read_text(ws.artifacts_dir / "writer.md")
    interview_text = safe_read_text(ws.artifacts_dir / "interview.md")
    coach_text = safe_read_text(ws.artifacts_dir / "coach.md")

    export_md = "\n\n".join(
        [
            f"# Export Package\n\n- Company: {project.get('company_name', '')}\n- Role: {project.get('job_title', '')}",
            "## Coach Artifact\n" + (coach_text or "_missing_"),
            "## Writer Artifact\n" + (writer_text or "_missing_"),
            "## Interview Artifact\n" + (interview_text or "_missing_"),
        ]
    )
    export_path = ws.artifacts_dir / "export.md"
    export_path.write_text(export_md, encoding="utf-8")

    export_json = {
        "project": project,
        "accepted_artifacts": accepted,
        "paths": {
            "coach": str((ws.artifacts_dir / "coach.md").relative_to(ws.root)),
            "writer": str((ws.artifacts_dir / "writer.md").relative_to(ws.root)),
            "interview": str((ws.artifacts_dir / "interview.md").relative_to(ws.root)),
            "export": str(export_path.relative_to(ws.root)),
        },
    }
    export_json_path = ws.artifacts_dir / "export.json"
    write_json(export_json_path, export_json)
    snapshot = {
        "id": f"export-{timestamp_slug()}",
        "artifact_type": "EXPORT",
        "accepted": True,
        "input_snapshot": {"accepted_artifact_count": len(accepted)},
        "output_path": str(export_path.relative_to(ws.root)),
        "raw_output_path": str(export_json_path.relative_to(ws.root)),
        "validation": {"passed": True, "missing": []},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    upsert_artifact(ws, snapshot)
    return {
        "markdown_path": str(export_path),
        "json_path": str(export_json_path),
        "accepted_count": len(accepted),
    }


def build_coach_prompt(ws: Workspace, coach_artifact: dict[str, Any] | None = None, gap_report: dict[str, Any] | None = None) -> Path:
    ws.ensure()
    project = load_project(ws)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    artifact = coach_artifact or build_coach_artifact(project, experiences, gap_report or analyze_gaps(project, experiences))
    data_block = build_data_block(
        project=project,
        experiences=experiences,
        knowledge_hints=build_knowledge_hints(knowledge_sources, project),
        extra={
            "gap_report": gap_report or analyze_gaps(project, experiences),
            "coach_allocations": artifact.get("allocations", []),
        },
    )
    content = PROMPT_COACH.format(data_block=data_block)
    out = ws.outputs_dir / "latest_coach_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def ingest_examples(ws: Workspace) -> list[Path]:
    ws.ensure()
    ingested: list[Path] = []
    for src in sorted(ws.sources_raw_dir.iterdir()):
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        dst = ws.sources_normalized_dir / f"{src.stem}.md"
        normalized = normalize_example(src.name, text)
        dst.write_text(normalized, encoding="utf-8")
        ingested.append(dst)
    return ingested


def build_analysis_prompt(ws: Workspace) -> Path:
    ws.ensure()
    content = PROMPT_ANALYZE.format(
        facts_path=relative(ws.root, ws.profile_dir / "facts.md"),
        experience_path=relative(ws.root, ws.profile_dir / "experience_bank.md"),
        examples_dir=relative(ws.root, ws.sources_normalized_dir),
    )
    out = ws.outputs_dir / "analysis_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def build_draft_prompt(ws: Workspace, target_path: Path) -> Path:
    ws.ensure()
    project = load_project(ws)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    data_block = build_data_block(
        project=project,
        experiences=select_primary_experiences(experiences, question_map),
        knowledge_hints=build_knowledge_hints(knowledge_sources, project),
        extra={
            "question_map": question_map,
            "legacy_target_path": relative(ws.root, target_path),
            "structure_rules_path": relative(ws.root, ws.analysis_dir / "structure_rules.md"),
        },
    )
    content = PROMPT_WRITER.format(data_block=data_block)
    out = ws.outputs_dir / "latest_draft_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def build_interview_prompt(ws: Workspace) -> Path:
    ws.ensure()
    project = load_project(ws)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    writer_artifact = safe_read_text(ws.artifacts_dir / "writer.md")
    data_block = build_data_block(
        project=project,
        experiences=select_primary_experiences(experiences, question_map),
        knowledge_hints=build_knowledge_hints(knowledge_sources, project),
        extra={
            "question_map": question_map,
            "writer_artifact": writer_artifact,
        },
    )
    content = PROMPT_INTERVIEW.format(data_block=data_block)
    out = ws.outputs_dir / "latest_interview_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def build_review_prompt(ws: Workspace, draft_path: Path, target_path: Path) -> Path:
    ws.ensure()
    content = PROMPT_REVIEW.format(
        draft_path=relative(ws.root, draft_path),
        facts_path=relative(ws.root, ws.profile_dir / "facts.md"),
        experience_path=relative(ws.root, ws.profile_dir / "experience_bank.md"),
        target_path=relative(ws.root, target_path),
    )
    out = ws.outputs_dir / "latest_review_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def run_codex(prompt_path: Path, cwd: Path, output_path: Path) -> int:
    if shutil.which("codex") is None:
        raise RuntimeError("`codex` is not available on PATH.")

    prompt = build_exec_prompt(prompt_path.read_text(encoding="utf-8"))
    result = subprocess.run(
        [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(cwd),
            "--color",
            "never",
            "-o",
            str(output_path),
            "-",
        ],
        cwd=str(cwd),
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    if (not output_path.exists()) or not output_path.read_text(encoding="utf-8", errors="ignore").strip():
        extracted = extract_last_codex_message(result.stdout or "")
        output_path.write_text(
            extracted or ((result.stdout or "") + ("\n" + result.stderr if result.stderr else "")),
            encoding="utf-8",
        )
    return result.returncode


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def normalize_example(name: str, body: str) -> str:
    return f"# Source: {name}\n\n{body.strip()}\n"


def relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def collect_source_paths(ws: Workspace, source_path: Path | None) -> list[Path]:
    target = source_path or ws.sources_raw_dir
    if target.is_file():
        return [target]
    return sorted(path for path in target.iterdir() if path.is_file())


def write_source_artifacts(ws: Workspace, source: dict[str, Any]) -> None:
    name = f"{source['id']}-{slugify(source['title'])}"
    normalized_path = ws.sources_normalized_dir / f"{name}.md"
    extracted_path = ws.sources_extracted_dir / f"{name}.json"
    normalized_path.write_text(
        f"# {source['title']}\n\n{source['cleaned_text']}\n",
        encoding="utf-8",
    )
    write_json(extracted_path, source)


def merge_sources(existing: list[dict[str, Any]], new_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {source["id"]: source for source in existing}
    for source in new_sources:
        by_id[source["id"]] = source
    return list(by_id.values())


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)
    return slug[:80] or "source"


def latest_accepted_artifacts(
    artifacts: list[dict[str, Any]],
    artifact_types: list[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for artifact_type in artifact_types:
        candidates = [
            item
            for item in artifacts
            if item.get("artifact_type") == artifact_type and item.get("accepted")
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda item: str(item.get("created_at", "")))
        selected.append(candidates[-1])
    return selected


def normalize_contract_output(text: str, headings: list[str]) -> str:
    if not text:
        return ""
    primary_heading = headings[0] if headings else ""
    if primary_heading and primary_heading in text:
        return text[text.rfind(primary_heading) :].strip()
    start_positions = [text.rfind(heading) for heading in headings if heading in text]
    if not start_positions:
        return text.strip()
    start = min(start_positions)
    return text[start:].strip()


def build_exec_prompt(prompt: str) -> str:
    return (
        "This is a pure text-generation task.\n"
        "Do not inspect files, do not run shell commands, do not plan aloud, and do not acknowledge the request.\n"
        "Return only the final answer that satisfies the requested output contract.\n\n"
        f"{prompt}"
    )


def extract_last_codex_message(stdout: str) -> str:
    marker = "\ncodex\n"
    if marker in stdout:
        return stdout.rsplit(marker, 1)[-1].strip()
    return stdout.strip()


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def build_data_block(
    *,
    project: dict[str, Any],
    experiences: list[dict[str, Any]],
    knowledge_hints: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> str:
    payload = {
        "project": project,
        "experiences": experiences,
        "knowledge_hints": knowledge_hints,
        "extra": extra or {},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def read_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def select_primary_experiences(
    experiences: list[dict[str, Any]],
    question_map: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not question_map:
        return experiences[:3]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in question_map:
        experience_id = str(item.get("experience_id", ""))
        if experience_id in seen:
            continue
        for experience in experiences:
            if str(experience.get("id")) == experience_id:
                selected.append(experience)
                seen.add(experience_id)
                break
    return selected or experiences[:3]
