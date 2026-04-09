from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse

from .logger import get_logger
from .config import get_config_value
from .checkpoint import CheckpointManager
from .progress import StepProgress
from .utils import (
    slugify,
    timestamp_slug,
    safe_read_text,
    read_json_if_exists,
    relative,
    write_if_missing,
    normalize_example,
    normalize_contract_output,
)
from .executor import (
    build_exec_prompt,
    extract_last_codex_message,
    run_codex,
)

logger = get_logger("pipeline")

from .domain import (
    analyze_gaps,
    auto_classify_project_questions,
    build_knowledge_hints,
    build_question_specific_knowledge_hints,
    build_coach_artifact,
    summarize_knowledge_sources,
    validate_block_contract,
    validate_coach_contract,
    validate_company_research_contract,
    validate_writer_contract,
    validate_interview_contract,
    calculate_readability_score,
    audit_facts,
)
from .parsing import (
    discover_public_urls,
    fetch_public_url_snapshot,
    ingest_source_file,
    ingest_public_url,
)
from .classifier import (
    classify_question,
    classify_question_regex_only,
    classify_question_with_confidence,
)
from .models import (
    ApplicationProject,
    ArtifactType,
    Experience,
    GeneratedArtifact,
    KnowledgeSource,
    SourceType,
    QuestionType,
    ValidationResult,
    CompanyAnalysis,
    SuccessCase,
)
from .company_analyzer import (
    analyze_company,
    CompanyAnalyzer,
    build_role_industry_strategy_from_project,
)
from .answer_quality import (
    evaluate_answer_quality,
    AnswerQualityEvaluator,
    analyze_humanization,
)
from .defense_simulator import simulate_interview_defense, DefenseSimulator
from .company_profiler import CompanyProfiler
from .interview_coach import InterviewCoach
from .profiler import ApplicantProfiler, build_candidate_profile_payload
from .state import (
    initialize_state,
    load_artifacts,
    load_experiences,
    load_live_source_cache,
    load_knowledge_sources,
    load_profile,
    load_project,
    load_success_cases,
    save_live_source_cache,
    save_project,
    save_knowledge_sources,
    save_success_cases,
    upsert_profile_snapshot,
    upsert_artifact,
    write_json,
)
from .templates import (
    INIT_EXPERIENCE_BANK,
    INIT_FACTS,
    INIT_SECRETS,
    INIT_TARGET,
    PROMPT_COACH,
    PROMPT_ANALYZE,
    PROMPT_COMPANY_RESEARCH,
    PROMPT_DRAFT,
    PROMPT_INTERVIEW,
    PROMPT_REVIEW,
    PROMPT_WRITER,
    STATE_EXPERIENCE_GUIDE,
    STATE_PROFILE_GUIDE,
)
from .workspace import Workspace
from .quality_evaluator import evaluate_draft_quality


def _get_success_cases_for_analysis(ws: Workspace) -> Optional[List[SuccessCase]]:
    """워크스페이스에서 success_cases를 로드하여 분석용으로 반환. 없으면 None."""
    try:
        cases = load_success_cases(ws)
        return cases if cases else None
    except Exception:
        return None


def _resolve_writer_target_path(ws: Workspace, target_path: Path | None) -> Path:
    return (target_path or (ws.targets_dir / "example_target.md")).resolve()


def _validate_writer_preconditions(
    ws: Workspace,
    *,
    target_path: Path,
    tool: str | None = None,
) -> tuple[ApplicationProject, list[dict[str, Any]]]:
    from .cli_tool_manager import get_available_tools

    project = load_project(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")

    if not target_path.exists():
        raise RuntimeError(
            "writer target 파일이 없습니다.\n"
            f"- 확인 경로: {target_path}\n"
            f"- 다음 액션: `resume-agent writer {ws.root} --target <상대경로>`로 올바른 파일을 지정하세요."
        )

    if not project.questions:
        raise RuntimeError(
            "writer를 실행할 질문이 없습니다.\n"
            f"- 확인 파일: {ws.state_dir / 'project.json'}\n"
            "- 다음 액션: `project.json`에 questions를 채운 뒤 다시 실행하세요."
        )

    if not question_map:
        raise RuntimeError(
            "writer 선행조건이 충족되지 않았습니다. question_map.json이 없습니다.\n"
            f"- 확인 경로: {ws.analysis_dir / 'question_map.json'}\n"
            f"- 다음 액션: `resume-agent coach {ws.root}`를 먼저 실행하세요."
        )

    if tool:
        available_tools = get_available_tools()
        if tool not in available_tools:
            available_display = ", ".join(available_tools) if available_tools else "없음"
            raise RuntimeError(
                f"선택한 CLI 도구를 찾을 수 없습니다: {tool}\n"
                f"- 사용 가능 도구: {available_display}\n"
                f"- 다음 액션: 다른 `--tool`을 선택하거나 {tool} CLI를 설치하세요."
            )

    writer_brief = read_json_if_exists(ws.analysis_dir / "writer_brief.json")
    if not writer_brief:
        raise RuntimeError(
            "writer 선행조건이 충족되지 않았습니다. writer_brief.json이 없습니다.\n"
            f"- 확인 경로: {ws.analysis_dir / 'writer_brief.json'}\n"
            f"- 다음 액션: `resume-agent coach {ws.root}`를 다시 실행해 문항 전략 시트를 생성하세요."
        )

    return project, question_map


def _build_writer_prompt_context(
    ws: Workspace,
    *,
    target_path: Path,
    company_analysis: CompanyAnalysis | None = None,
) -> dict[str, Any]:
    prompt_path = build_draft_prompt(ws, target_path, company_analysis=company_analysis)
    run_dir = ws.runs_dir / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = run_dir / "raw_writer.md"
    return {
        "prompt_path": prompt_path,
        "run_dir": run_dir,
        "raw_output_path": raw_output_path,
    }


def _run_writer_llm(
    prompt_path: Path,
    ws: Workspace,
    output_path: Path,
    *,
    tool: str,
) -> int:
    return run_codex(prompt_path, ws.root, output_path, tool=tool)


def _read_llm_run_meta(output_path: Path) -> dict[str, Any]:
    meta = read_json_if_exists(output_path.with_suffix(".meta.json"))
    return meta if isinstance(meta, dict) else {}


def _summarize_llm_run_metas(run_metas: list[dict[str, Any]]) -> dict[str, Any]:
    attempted_tools: list[str] = []
    selected_tool: str | None = None
    fallback_reason: str | None = None

    for meta in run_metas:
        if not isinstance(meta, dict):
            continue
        for tool_name in meta.get("attempted_tools", []):
            if tool_name not in attempted_tools:
                attempted_tools.append(str(tool_name))
        if meta.get("selected_tool"):
            selected_tool = str(meta["selected_tool"])
        if not fallback_reason and meta.get("fallback_reason"):
            fallback_reason = str(meta["fallback_reason"])

    return {
        "attempted_tools": attempted_tools,
        "selected_tool": selected_tool,
        "fallback_reason": fallback_reason,
    }


def _build_writer_quality_status(
    evaluations: list[dict[str, Any]] | None = None,
    *,
    status: str = "ok",
    error_reason: str | None = None,
) -> list[dict[str, Any]]:
    if evaluations:
        return evaluations
    if status == "ok":
        return []
    payload: dict[str, Any] = {"status": status}
    if error_reason:
        payload["error_reason"] = error_reason
    return [payload]


def init_workspace(root: Path) -> Workspace:
    ws = Workspace(root=root)
    ws.ensure()
    initialize_state(ws)

    write_if_missing(ws.profile_dir / "facts.md", INIT_FACTS)
    write_if_missing(ws.profile_dir / "experience_bank.md", INIT_EXPERIENCE_BANK)
    write_if_missing(
        ws.profile_dir / "jd.md",
        "# 직무기술서 (JD)\n\n여기에 공고 원문을 붙여넣으세요.\n",
    )
    write_if_missing(ws.targets_dir / "example_target.md", INIT_TARGET)
    write_if_missing(ws.profile_dir / "state_profile_guide.md", STATE_PROFILE_GUIDE)
    write_if_missing(
        ws.profile_dir / "state_experience_guide.md", STATE_EXPERIENCE_GUIDE
    )

    secrets_path = ws.root / ".secrets.json"
    if not secrets_path.exists():
        secrets_path.write_text(INIT_SECRETS, encoding="utf-8")

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


def crawl_base(ws: Workspace, source_path: Path | None = None) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    paths = collect_source_paths(ws, source_path)
    ingested: List[KnowledgeSource] = []
    all_success_cases: List[SuccessCase] = []

    for path in paths:
        raw_path = materialize_source_file(ws, path, source_root=source_path)
        if raw_path is None:
            continue
        sources, cases = ingest_source_file(raw_path)
        for source in sources:
            write_source_artifacts(ws, source)
            ingested.append(source)
        all_success_cases.extend(cases)

    merged = merge_sources(load_knowledge_sources(ws), ingested)
    save_knowledge_sources(ws, merged)

    # success_cases 병합 및 저장
    existing_cases = load_success_cases(ws)
    merged_cases = _merge_success_cases(existing_cases, all_success_cases)
    save_success_cases(ws, merged_cases)

    summary = summarize_knowledge_sources(merged)
    summary_path = ws.analysis_dir / "knowledge_hints.json"
    write_json(summary_path, [item.model_dump() for item in merged])
    return {
        "source_count": len(ingested),
        "stored_count": len(merged),
        "success_case_count": len(all_success_cases),
        "total_success_cases": len(merged_cases),
        "summary": summary,
        "analysis_path": str(summary_path),
    }


def crawl_web_sources(ws: Workspace, urls: list[str]) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    cache = load_live_source_cache(ws)
    ingested: List[KnowledgeSource] = []
    updates: List[dict[str, Any]] = []

    for url in urls:
        snapshot = fetch_public_url_snapshot(url)
        previous = cache.get(url) if isinstance(cache.get(url), dict) else None
        change_status = "new"
        change_summary = "신규 추적 시작"
        if previous:
            change_status = (
                "unchanged"
                if str(previous.get("content_hash") or "") == snapshot["content_hash"]
                else "changed"
            )
            change_summary = _summarize_live_source_change(previous, snapshot, change_status)
        cache[url] = {
            "url": url,
            "title": snapshot["title"],
            "content_hash": snapshot["content_hash"],
            "fetched_at": snapshot["fetched_at"],
            "status_code": snapshot["status_code"],
            "change_status": change_status,
            "change_summary": change_summary,
            "cleaned_excerpt": str(snapshot.get("cleaned_text") or "")[:280],
            "keywords": _tokenize_research_terms(
                str(snapshot.get("cleaned_text") or "")
            )[:12],
        }
        updates.append(cache[url])

        for source in ingest_public_url(url, snapshot=snapshot):
            write_source_artifacts(ws, source)
            ingested.append(source)

    merged = merge_sources(load_knowledge_sources(ws), ingested)
    save_knowledge_sources(ws, merged)
    save_live_source_cache(ws, cache)
    summary = summarize_knowledge_sources(merged)
    summary_path = ws.analysis_dir / "knowledge_hints.json"
    write_json(summary_path, [item.model_dump() for item in merged])
    updates_path = ws.analysis_dir / "live_source_updates.json"
    write_json(
        updates_path,
        {
            "tracked_url_count": len(cache),
            "checked_url_count": len(urls),
            "updates": updates,
        },
    )
    return {
        "source_count": len(ingested),
        "stored_count": len(merged),
        "summary": summary,
        "analysis_path": str(summary_path),
        "live_updates_path": str(updates_path),
        "new_url_count": sum(
            1 for item in updates if item.get("change_status") == "new"
        ),
        "changed_url_count": sum(
            1 for item in updates if item.get("change_status") == "changed"
        ),
        "unchanged_url_count": sum(
            1 for item in updates if item.get("change_status") == "unchanged"
        ),
    }


def build_live_source_update_summary(
    ws: Workspace, urls: list[str] | None = None
) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    cache = load_live_source_cache(ws)
    records = [
        value
        for key, value in cache.items()
        if isinstance(value, dict) and (not urls or key in urls)
    ]
    records.sort(key=lambda item: str(item.get("fetched_at") or ""), reverse=True)
    priority_updates = [
        item for item in records if item.get("change_status") in {"changed", "new"}
    ]
    return {
        "tracked_url_count": len(records),
        "new_url_count": sum(
            1 for item in records if item.get("change_status") == "new"
        ),
        "changed_url_count": sum(
            1 for item in records if item.get("change_status") == "changed"
        ),
        "unchanged_url_count": sum(
            1 for item in records if item.get("change_status") == "unchanged"
        ),
        "priority_update_count": len(priority_updates),
        "priority_live_updates": priority_updates[:5],
        "latest_updates": records[:5],
    }


def refresh_live_web_sources(ws: Workspace, urls: list[str]) -> dict[str, Any]:
    return crawl_web_sources(ws, urls)


def build_live_priority_by_url(ws: Workspace) -> dict[str, str]:
    ws.ensure()
    initialize_state(ws)
    cache = load_live_source_cache(ws)
    return {
        str(url): str(payload.get("change_status") or "")
        for url, payload in cache.items()
        if isinstance(payload, dict) and str(url).strip()
    }


def _summarize_live_source_change(
    previous: dict[str, Any],
    snapshot: dict[str, Any],
    change_status: str,
) -> str:
    if change_status == "unchanged":
        return "변경 없음"
    if change_status == "new":
        return "신규 추적 시작"

    previous_terms = _tokenize_research_terms(str(previous.get("cleaned_excerpt") or ""))
    current_terms = _tokenize_research_terms(str(snapshot.get("cleaned_text") or ""))
    added = [term for term in current_terms if term not in previous_terms][:3]
    removed = [term for term in previous_terms if term not in current_terms][:3]

    parts: list[str] = []
    if added:
        parts.append(f"추가 신호: {', '.join(added)}")
    if removed:
        parts.append(f"약화 신호: {', '.join(removed)}")
    return " / ".join(parts) if parts else "본문 변경 감지"


def refresh_existing_public_sources(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    knowledge_sources = load_knowledge_sources(ws)
    urls = _dedupe_preserve_order(
        [
            str(source.url or "").strip()
            for source in knowledge_sources
            if source.source_type == SourceType.USER_URL_PUBLIC and source.url
        ]
    )
    if not urls:
        return {
            "tracked_url_count": 0,
            "source_count": 0,
            "stored_count": len(knowledge_sources),
            "new_url_count": 0,
            "changed_url_count": 0,
            "unchanged_url_count": 0,
            "live_updates_path": str(ws.analysis_dir / "live_source_updates.json"),
        }
    result = refresh_live_web_sources(ws, urls)
    return {
        "tracked_url_count": len(urls),
        **result,
    }


def _build_feedback_pattern_id(stage: str, project: ApplicationProject) -> str:
    question_types = sorted(
        {
            question.detected_type.value
            for question in project.questions
            if getattr(question, "detected_type", None)
        }
    )
    type_key = "-".join(question_types[:4]) if question_types else "NONE"
    company_type = project.company_type or "UNKNOWN"
    return f"{stage}|{company_type}|{type_key}"


def _build_feedback_selection_payload(
    question_map: list[dict[str, Any]] | None,
    writer_brief: dict[str, Any] | None = None,
) -> dict[str, list[Any]]:
    selected_ids: list[str] = []
    mappings: list[dict[str, str]] = []
    for item in question_map or []:
        experience_id = str(item.get("experience_id") or "").strip()
        if not experience_id:
            continue
        if experience_id not in selected_ids:
            selected_ids.append(experience_id)
        mappings.append(
            {
                "question_id": str(item.get("question_id") or ""),
                "question_type": str(item.get("question_type") or ""),
                "experience_id": experience_id,
                "question_order": int(
                    item.get("question_order")
                    or item.get("order_no")
                    or item.get("order")
                    or 0
                ),
            }
        )
    question_strategy_map: list[dict[str, Any]] = []
    strategy_by_question = {
        str(item.get("question_id") or ""): item
        for item in (writer_brief or {}).get("question_strategies", [])
        if isinstance(item, dict) and item.get("question_id")
    }
    for item in mappings:
        strategy = strategy_by_question.get(str(item.get("question_id") or ""))
        if not strategy:
            continue
        question_strategy_map.append(
            {
                "question_id": str(strategy.get("question_id") or item.get("question_id") or ""),
                "question_order": int(strategy.get("question_order") or item.get("question_order") or 0),
                "question_type": str(
                    strategy.get("question_type") or item.get("question_type") or ""
                ),
                "experience_id": str(
                    strategy.get("primary_experience_id") or item.get("experience_id") or ""
                ),
                "core_message": str(strategy.get("core_message") or "").strip(),
                "winning_angle": str(strategy.get("winning_angle") or "").strip(),
                "losing_angle": str(strategy.get("losing_angle") or "").strip(),
                "differentiation_line": str(
                    strategy.get("differentiation_line") or ""
                ).strip(),
                "tone": str(strategy.get("target_impression") or "").strip(),
            }
        )
    return {
        "selected_experience_ids": selected_ids,
        "question_experience_map": mappings,
        "question_strategy_map": question_strategy_map,
    }


def build_feedback_learning_context(
    ws: Workspace,
    artifact: str,
    project: ApplicationProject | None = None,
) -> dict[str, Any]:
    ws.ensure()
    project = project or load_project(ws)
    selection_payload = _build_feedback_selection_payload(
        read_json_if_exists(ws.analysis_dir / "question_map.json"),
        writer_brief=read_json_if_exists(ws.analysis_dir / "writer_brief.json"),
    )
    context = {
        "artifact": artifact,
        "total_feedback": 0,
        "recent_rejection_comments": [],
        "top_patterns": [],
        "recommended_pattern": None,
        "current_pattern": _build_feedback_pattern_id(artifact, project),
        "question_experience_map": selection_payload.get("question_experience_map", []),
        "question_strategy_map": selection_payload.get("question_strategy_map", []),
    }
    try:
        from .feedback_learner import create_feedback_learner

        learner = create_feedback_learner(str(ws.root / "kb" / "feedback"))
        insights = learner.get_insights()
        question_types = [
            question.detected_type.value
            for question in project.questions
            if getattr(question, "detected_type", None)
        ]
        similar_context = {
            "artifact_type": artifact,
            "artifact": artifact,
            "stage": artifact,
            "company_name": project.company_name,
            "job_title": project.job_title,
            "company_type": project.company_type,
            "question_types": question_types,
        }
        recommendations = learner.get_recommendation(similar_context)
        history = learner.db.get_feedback_history(limit=30)
        artifact_history = [
            item
            for item in history
            if item.artifact_type == artifact
            or str(item.pattern_used).startswith(f"{artifact}|")
        ]
        top_patterns = (
            recommendations[:5]
            or [
                {
                    "pattern_id": item.pattern_id,
                    "success_rate": item.success_rate,
                    "avg_rating": item.avg_rating,
                    "total_uses": item.total_uses,
                }
                for item in learner.db.get_top_patterns(10)
                if str(item.pattern_id).startswith(f"{artifact}|")
            ][:5]
        )
        context.update(
            {
                "total_feedback": insights.get("total_feedback", 0),
                "overall_success_rate": insights.get("overall_success_rate", 0),
                "similar_context": similar_context,
                "recent_rejection_comments": [
                    item.comment
                    for item in artifact_history
                    if not item.accepted and item.comment
                ][:5],
                "recent_rejection_reasons": [
                    item.rejection_reason
                    for item in artifact_history
                    if not item.accepted and item.rejection_reason
                ][:5],
                "outcome_summary": learner.get_context_outcome_summary(similar_context),
                "strategy_outcome_summary": learner.get_strategy_outcome_summary(
                    similar_context
                ),
                "top_patterns": top_patterns,
                "insights": insights,
                "recommended_pattern": top_patterns[0]["pattern_id"]
                if top_patterns
                else context["current_pattern"],
            }
        )
        context["adaptation_plan"] = build_feedback_adaptation_plan(
            project,
            context,
        )
    except Exception as e:
        logger.debug(f"피드백 학습 컨텍스트 생성 건너뜀: {e}")

    out_path = ws.analysis_dir / f"{artifact}_feedback_learning.json"
    write_json(out_path, context)
    return context


def _safe_top_rejection_reason(stats: dict[str, Any] | None) -> str:
    if not isinstance(stats, dict):
        return ""
    top_reasons = stats.get("top_rejection_reasons", []) or []
    if not top_reasons:
        return ""
    top_reason = top_reasons[0]
    if isinstance(top_reason, dict):
        return str(top_reason.get("reason") or "").strip()
    return str(top_reason).strip()


def _build_writer_contract(
    feedback_learning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    matched_feedback = int((feedback_learning or {}).get("total_feedback") or 0)
    mode = "adaptive" if matched_feedback > 0 else "heuristic"
    mode_label = "adaptive mode" if mode == "adaptive" else "heuristic mode"
    return {
        "mode": mode,
        "mode_label": mode_label,
        "headline": "문항당 하나의 핵심 메시지와 하나의 주력 경험만 밀어붙입니다.",
        "answer_checklist": [
            "핵심 주장 1개",
            "근거 경험 1개",
            "수치/증빙 1개",
            "조직 적합 신호 1개",
            "면접 방어 취약점 1개와 완화 문장 1개",
        ],
        "decision_principles": [
            "문항마다 single best strategy를 유지한다.",
            "흔한 성장/노력/배움 클리셰보다 검증 가능한 결과와 판단 기준을 우선한다.",
            "평균 지원자 톤이 아니라 조직이 안심할 수 있는 기여 신호를 우선한다.",
        ],
    }


def build_writer_brief(
    ws: Workspace,
    *,
    project: ApplicationProject,
    experiences: list[Experience],
    allocations: list[dict[str, Any]],
    feedback_learning: dict[str, Any] | None = None,
    experience_competition: dict[str, Any] | None = None,
    top001_coach_analysis: dict[str, Any] | None = None,
    committee_feedback: dict[str, Any] | None = None,
    self_intro_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    experience_by_id = {item.id: item for item in experiences}
    competition_entries = []
    if isinstance(experience_competition, dict):
        competition_entries = experience_competition.get("questions", []) or []
    elif isinstance(experience_competition, list):
        competition_entries = experience_competition
    competition_rows = {
        str(item.get("question_id") or ""): item
        for item in competition_entries
        if isinstance(item, dict) and item.get("question_id")
    }
    risky_map: dict[str, dict[str, Any]] = {}
    strategy_summary = (feedback_learning or {}).get("strategy_outcome_summary", {})
    for question_type, rows in (
        strategy_summary.get("experience_stats_by_question_type", {}) or {}
    ).items():
        if not isinstance(rows, dict):
            continue
        risky_map[str(question_type)] = rows

    question_text_by_id = {
        question.id: question.question_text for question in project.questions
    }
    question_strategies: list[dict[str, Any]] = []
    recurring_risks = (committee_feedback or {}).get("recurring_risks", [])[:3]
    focus_keywords = (self_intro_pack or {}).get("focus_keywords", [])[:2]
    top001_suggestions = (top001_coach_analysis or {}).get("suggestions", [])[:3]

    for allocation in allocations:
        question_id = str(allocation.get("question_id") or "").strip()
        question_type = str(allocation.get("question_type") or "").strip()
        experience_id = str(allocation.get("experience_id") or "").strip()
        experience = experience_by_id.get(experience_id)
        competition = competition_rows.get(question_id, {})
        ranked = competition.get("ranked_experiences", []) if isinstance(competition, dict) else []
        supporting_titles = [
            str(item.get("experience_title") or "").strip()
            for item in ranked[1:2]
            if isinstance(item, dict) and str(item.get("experience_title") or "").strip()
        ]
        supporting_ids = [
            str(item.get("experience_id") or "").strip()
            for item in ranked[1:2]
            if isinstance(item, dict) and str(item.get("experience_id") or "").strip()
        ]
        risky_reason = _safe_top_rejection_reason(
            ((risky_map.get(question_type) or {}).get(experience_id) or {})
        )
        evidence_bits = _dedupe_preserve_order(
            [
                getattr(experience, "metrics", "") if experience else "",
                getattr(experience, "evidence_text", "") if experience else "",
                allocation.get("reason", ""),
            ]
        )[:3]
        forbidden_points = _dedupe_preserve_order(
            [
                "성장/노력/배움만 반복하는 추상 서술",
                f"{risky_reason}처럼 들리는 표현" if risky_reason else "",
                "팀 성과만 말하고 개인 판단과 기여를 숨기는 서술",
            ]
        )[:3]
        target_impression = "운영 안정성과 책임감을 주는 사람"
        if focus_keywords:
            target_impression = f"{', '.join(focus_keywords)}를 검증 가능하게 보여주는 사람"
        question_strategies.append(
            {
                "question_id": question_id,
                "question_order": int(allocation.get("order_no") or allocation.get("question_order") or 0),
                "question_type": question_type,
                "question_text": question_text_by_id.get(question_id, ""),
                "target_impression": target_impression,
                "core_message": (
                    f"{experience.title} 경험으로 {question_type} 문항에서 검증 가능한 기여를 입증한다."
                    if experience
                    else f"{question_type} 문항에서 검증 가능한 기여를 입증한다."
                ),
                "primary_experience_id": experience_id,
                "primary_experience_title": experience.title if experience else allocation.get("experience_title", ""),
                "supporting_experience_ids": supporting_ids,
                "supporting_experience_titles": supporting_titles,
                "winning_angle": (
                    f"{question_type} 문항은 성실/열정보다 운영 안정성·판단 기준·재현 가능한 성과로 밀어붙인다."
                ),
                "losing_angle": "의지만 강조하거나 추상적 성장담으로 흐르면 약해진다.",
                "forbidden_points": forbidden_points,
                "required_evidence": evidence_bits,
                "recommended_structure": [
                    "상황/과제 1문장",
                    "개인 판단과 행동 2문장",
                    "수치·증빙 1문장",
                    "직무 연결 1문장",
                ],
                "expected_attack_points": _dedupe_preserve_order(
                    recurring_risks
                    + ([risky_reason] if risky_reason else [])
                    + ["왜 본인 판단이었는지 설명 부족"]
                )[:4],
                "mitigation_line": "개인 판단 기준과 수치 근거를 먼저 말하고, 팀 성과는 보조로만 언급한다.",
                "differentiation_line": (
                    f"평균 지원자처럼 열정만 말하지 않고 {experience.title if experience else '핵심 경험'}의 운영 기준·증빙·재현성을 제시한다."
                ),
                "common_cliche": "성장, 노력, 배움을 반복하며 직무 적합성을 추상적으로 주장하는 답변",
                "top001_signal": top001_suggestions[0] if top001_suggestions else "",
            }
        )

    writer_contract = _build_writer_contract(feedback_learning)
    brief = {
        "mode": writer_contract["mode"],
        "mode_label": writer_contract["mode_label"],
        "question_strategies": question_strategies,
        "writer_contract": writer_contract,
    }
    write_json(ws.analysis_dir / "writer_brief.json", brief)
    lines = [
        "# Writer Brief",
        "",
        f"- Mode: {writer_contract['mode_label']}",
        f"- Headline: {writer_contract['headline']}",
        "",
    ]
    for strategy in question_strategies:
        lines.extend(
            [
                f"## Q{strategy['question_order']}",
                f"- 목표 인상: {strategy['target_impression']}",
                f"- 핵심 메시지: {strategy['core_message']}",
                f"- Winning angle: {strategy['winning_angle']}",
                f"- Losing angle: {strategy['losing_angle']}",
                f"- 금지 메시지: {', '.join(strategy['forbidden_points'])}",
                f"- 필수 근거: {', '.join(strategy['required_evidence']) or '없음'}",
                f"- 추천 구조: {', '.join(strategy['recommended_structure'])}",
                f"- 예상 공격 포인트: {', '.join(strategy['expected_attack_points']) or '없음'}",
                f"- 차별화 문장: {strategy['differentiation_line']}",
                "",
            ]
        )
    (ws.artifacts_dir / "writer_brief.md").write_text("\n".join(lines), encoding="utf-8")
    return brief


def build_feedback_adaptation_plan(
    project: ApplicationProject,
    feedback_learning: dict[str, Any] | None,
) -> dict[str, Any]:
    feedback_learning = feedback_learning or {}
    strategy_summary = feedback_learning.get("strategy_outcome_summary", {}) or {}
    outcome_summary = feedback_learning.get("outcome_summary", {}) or {}
    top_patterns = feedback_learning.get("top_patterns", []) or []

    risky_question_types: list[dict[str, Any]] = []
    experience_stats = strategy_summary.get("experience_stats_by_question_type", {}) or {}
    for question_type, exp_map in experience_stats.items():
        weak_experiences = []
        for experience_id, stats in (exp_map or {}).items():
            pass_rate = float(stats.get("pass_rate", 0.0))
            weighted_net = int(stats.get("weighted_net_score", 0))
            if pass_rate < 0.5 or weighted_net < 0:
                weak_experiences.append(
                    {
                        "experience_id": experience_id,
                        "pass_rate": round(pass_rate, 3),
                        "weighted_net_score": weighted_net,
                        "top_rejection_reasons": stats.get("top_rejection_reasons", [])[:2],
                    }
                )
        if weak_experiences:
            risky_question_types.append(
                {
                    "question_type": question_type,
                    "weak_experiences": weak_experiences[:3],
                    "recommended_action": "해당 문항 유형은 경험 교체 또는 근거 보강을 우선 검토하세요.",
                }
            )

    focus_actions: list[str] = []
    for item in outcome_summary.get("top_rejection_reasons", [])[:3]:
        reason = str(item.get("reason", "")).strip()
        if reason:
            focus_actions.append(f"반복 탈락 사유 '{reason}' 보강")
    for item in risky_question_types[:2]:
        focus_actions.append(
            f"{item['question_type']} 문항은 경험 선택 재검토"
        )
    recommended_pattern = (
        top_patterns[0]["pattern_id"]
        if top_patterns and isinstance(top_patterns[0], dict)
        else feedback_learning.get("recommended_pattern")
    )

    return {
        "recommended_pattern": recommended_pattern,
        "focus_actions": _dedupe_preserve_order(focus_actions)[:5],
        "risky_question_types": risky_question_types[:4],
        "matched_feedback_count": strategy_summary.get(
            "matched_feedback_count",
            outcome_summary.get("matched_feedback_count", 0),
        ),
    }


def build_candidate_profile(
    ws: Workspace,
    project: ApplicationProject,
    experiences: List[Experience],
) -> dict[str, Any]:
    profile = load_profile(ws)
    personalized = ApplicantProfiler().build_profile(experiences, profile_id="default")
    upsert_profile_snapshot(ws, personalized)
    total = len(experiences) or 1
    metric_count = sum(1 for item in experiences if item.metrics.strip())
    contribution_count = sum(
        1 for item in experiences if item.personal_contribution.strip()
    )
    collaboration_count = sum(
        1
        for item in experiences
        if any(tag in {"협업", "소통", "조율", "고객응대"} for tag in item.tags)
    )
    abstract_tokens = ("항상", "최선", "성장", "가치", "역량", "기여")
    concrete_tokens = ("건", "%", "명", "원", "일", "표", "기준", "안내")
    logical_tokens = ("분석", "검토", "정리", "기준", "데이터", "보고", "개선")
    relational_tokens = ("협업", "소통", "고객", "민원", "지원", "조율", "안내")
    logical_hits = 0
    relational_hits = 0
    abstract_hits = 0
    concrete_hits = 0
    tag_frequency: dict[str, int] = {}
    for experience in experiences:
        bag = " ".join(
            [
                experience.title,
                experience.situation,
                experience.task,
                experience.action,
                experience.result,
                " ".join(experience.tags),
            ]
        )
        logical_hits += sum(bag.count(token) for token in logical_tokens)
        relational_hits += sum(bag.count(token) for token in relational_tokens)
        abstract_hits += sum(bag.count(token) for token in abstract_tokens)
        concrete_hits += sum(bag.count(token) for token in concrete_tokens)
        for tag in experience.tags:
            if tag.strip():
                tag_frequency[tag] = tag_frequency.get(tag, 0) + 1

    communication_style = "balanced"
    if logical_hits >= relational_hits + 2:
        communication_style = "logical"
    elif relational_hits >= logical_hits + 2:
        communication_style = "relational"

    signature_strengths = [
        tag
        for tag, _ in sorted(
            tag_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        )[:4]
    ]
    if not signature_strengths:
        signature_strengths = [project.job_title or "직무 적합성"]

    abstraction_ratio = round(abstract_hits / max(1, abstract_hits + concrete_hits), 2)
    confidence_style = "balanced"
    if contribution_count / total >= 0.7 and metric_count / total >= 0.5:
        confidence_style = "assertive"
    elif contribution_count / total < 0.4:
        confidence_style = "reserved"

    blind_spots: list[str] = []
    coaching_focus: list[str] = []
    if metric_count / total < 0.5:
        coaching_focus.append("수치·비교 기준을 먼저 보강하세요.")
        blind_spots.append("성과를 설명할 때 비교 기준과 수치가 빠지기 쉽습니다.")
    if contribution_count / total < 0.5:
        coaching_focus.append("개인 기여와 판단 기준을 더 선명하게 분리하세요.")
        blind_spots.append(
            "팀 성과는 보이지만 본인 판단과 책임 범위가 흐릴 수 있습니다."
        )
    if communication_style == "logical":
        coaching_focus.append(
            "강한 분석형 톤은 유지하되 고객·협업 맥락을 더 드러내세요."
        )
    elif communication_style == "relational":
        coaching_focus.append(
            "관계 중심 설명은 강점이지만 근거 수치와 판단 기준을 함께 제시하세요."
        )
    else:
        coaching_focus.append(
            "균형형 답변이 강점이므로 핵심 메시지를 더 빠르게 압축하세요."
        )
    if abstraction_ratio > 0.55:
        blind_spots.append(
            "추상 표현 비중이 높아 구체 행동과 결과가 약해질 수 있습니다."
        )
    if collaboration_count / total < 0.3:
        blind_spots.append("협업 맥락보다 개인 수행 중심으로 들릴 수 있습니다.")

    interview_strategy = {
        "opening": "핵심 결론을 먼저 말하고, 곧바로 행동 근거와 결과를 붙입니다.",
        "pressure_response": "즉답이 어려우면 기준→행동→결과 순서로 짧게 재정리합니다.",
        "tone": "담백하고 근거 중심을 유지하되 질문 의도에 맞는 감정 온도를 한 문장 추가합니다.",
    }

    candidate_profile = {
        "style_preference": profile.style_preference,
        "communication_style": communication_style,
        "metric_coverage_ratio": round(metric_count / total, 2),
        "personal_contribution_ratio": round(contribution_count / total, 2),
        "collaboration_ratio": round(collaboration_count / total, 2),
        "abstraction_ratio": abstraction_ratio,
        "confidence_style": confidence_style,
        "signature_strengths": signature_strengths,
        "blind_spots": blind_spots[:3],
        "coaching_focus": coaching_focus[:3],
        "interview_strategy": interview_strategy,
        "profile_summary": (
            f"{profile.style_preference} 톤을 선호하는 "
            f"{communication_style}형 지원자입니다. "
            f"주요 강점은 {', '.join(signature_strengths[:3])}입니다."
        ),
    }
    candidate_profile.update(build_candidate_profile_payload(personalized))
    candidate_profile["style_preference"] = profile.style_preference
    write_json(ws.analysis_dir / "candidate_profile.json", candidate_profile)
    return candidate_profile


def build_company_profile(
    ws: Workspace,
    project: ApplicationProject,
    candidate_profile: dict[str, Any] | None,
    *,
    job_description: str = "",
) -> dict[str, Any]:
    company_profile = CompanyProfiler(
        ws,
        _get_success_cases_for_analysis(ws) or [],
    ).profile_company(
        project,
        job_description=job_description,
        applicant_profile=candidate_profile,
    )
    write_json(ws.analysis_dir / "company_profile.json", company_profile)
    return company_profile


def build_interview_support_pack(
    ws: Workspace,
    candidate_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    support_pack = InterviewCoach().build_support_pack(candidate_profile)
    write_json(ws.analysis_dir / "interview_support_pack.json", support_pack)
    return support_pack


def build_narrative_ssot(
    ws: Workspace,
    project: ApplicationProject,
    experiences: List[Experience],
    *,
    question_map: list[dict[str, Any]] | None = None,
    company_analysis: CompanyAnalysis | None = None,
) -> dict[str, Any]:
    question_map = question_map or read_json_if_exists(
        ws.analysis_dir / "question_map.json"
    )
    committee_feedback = build_committee_feedback_context(ws)
    self_intro_pack = (
        read_json_if_exists(ws.analysis_dir / "self_intro_pack.json") or {}
    )
    prioritized = select_primary_experiences(experiences, question_map)[:3]
    evidence_titles = [item.title for item in prioritized]
    claims = _dedupe_preserve_order(
        [
            f"{project.job_title or '지원 직무'}에 바로 투입 가능한 검증형 실무자",
            f"{project.company_name or '지원 기관'}에 맞는 근거 중심 문제해결형 지원자",
            *(
                self_intro_pack.get("focus_keywords", [])[:2]
                if isinstance(self_intro_pack, dict)
                else []
            ),
        ]
    )[:3]
    ssot = {
        "core_claims": claims,
        "evidence_experience_ids": [item.id for item in prioritized],
        "evidence_experience_titles": evidence_titles,
        "opening_message": self_intro_pack.get("opening_hook", ""),
        "risk_watchouts": committee_feedback.get("recurring_risks", [])[:4],
        "answer_anchor": (
            company_analysis.answer_tone_hint
            if company_analysis and getattr(company_analysis, "answer_tone_hint", "")
            else "주장보다 근거를 먼저 제시하고, 마지막 문장을 입사 후 기여 방식으로 닫습니다."
        ),
    }
    write_json(ws.analysis_dir / "narrative_ssot.json", ssot)
    return ssot


def build_research_strategy_translation(
    ws: Workspace,
    project: ApplicationProject,
    *,
    company_analysis: CompanyAnalysis | None = None,
    source_grading: dict[str, Any] | None = None,
) -> dict[str, Any]:
    experiences = load_experiences(ws)
    source_grading = source_grading or read_json_if_exists(
        ws.analysis_dir / "source_grading.json"
    )
    live_source_updates = build_live_source_update_summary(ws)
    cross_check = (
        (source_grading or {}).get("cross_check", {})
        if isinstance(source_grading, dict)
        else {}
    )
    single_source = int(cross_check.get("single_source_area_count", 0))
    missing_count = int(cross_check.get("missing_area_count", 0))
    translation = {
        "answer_tone": (
            getattr(company_analysis, "answer_tone_hint", "")
            if company_analysis
            else "차분하고 근거 중심으로 답하되 공공기관은 책임감과 고객 관점을 함께 드러냅니다."
        ),
        "preferred_evidence_style": "행동 기준 + 수치/기록 + 개인 기여를 함께 제시",
        "disliked_expressions": _dedupe_preserve_order(
            ["항상", "최선을 다했습니다", "기여하고자 합니다"]
            + (
                getattr(company_analysis, "taboo_phrases", [])[:3]
                if company_analysis
                else []
            )
        )[:5],
        "essay_usefulness_score": max(
            0.2,
            min(0.95, round(0.85 - (single_source * 0.1) - (missing_count * 0.12), 2)),
        ),
        "translation_notes": [
            "단일 출처에만 기대는 회사 정보는 자소서 주장보다 보조 근거로 사용합니다."
            if single_source
            else "핵심 회사 신호는 자소서 첫 문단과 면접 1분 답변에 공통으로 반영합니다.",
            "근거가 부족한 영역은 [NEEDS_VERIFICATION]로 분리하고 확정 표현을 피합니다."
            if missing_count
            else "교차검증된 신호를 지원동기와 직무적합성 문항에 우선 반영합니다.",
        ],
        "recent_change_actions": _build_recent_change_actions(
            live_source_updates.get("priority_live_updates", []),
            project=project,
        ),
    }

    top001_translation: dict[str, Any] = {}
    if company_analysis:
        try:
            from .top001.integrator import Top001ResearchTranslator

            top001_translation = Top001ResearchTranslator().translate_research_to_strategy(
                company_analysis,
                experiences,
                project.questions,
            )
        except Exception as e:
            logger.warning(f"Top001 research translation failed: {e}")

    if top001_translation:
        translation["top001"] = top001_translation
        write_json(
            ws.analysis_dir / "research_strategy_translation_top001.json",
            _normalize_strategy_payload(top001_translation),
        )

    write_json(ws.analysis_dir / "research_strategy_translation.json", translation)
    update_application_strategy(
        ws,
        project=project,
        stage="research",
        experiences=experiences,
        research_strategy=top001_translation or translation,
    )
    return translation


def _build_recent_change_actions(
    priority_live_updates: list[dict[str, Any]],
    *,
    project: ApplicationProject,
) -> list[str]:
    actions: list[str] = []
    for item in priority_live_updates[:3]:
        title = str(item.get("title") or item.get("url") or "공개 소스").strip()
        summary = str(item.get("change_summary") or "").strip()
        status = str(item.get("change_status") or "").strip()
        keywords = [str(keyword) for keyword in item.get("keywords", [])[:3]]

        if status == "changed":
            if summary:
                actions.append(
                    f"{title} 변화에 맞춰 지원동기와 직무적합성 문장에서 '{summary}'를 반영해 최신 우선순위를 설명합니다."
                )
            elif keywords:
                actions.append(
                    f"{title}에서 다시 강조된 {', '.join(keywords)} 신호를 답변 첫 문단 근거로 앞세웁니다."
                )
        elif status == "new":
            actions.append(
                f"{title} 신규 공개 신호를 기존 경험과 연결해 {project.job_title or '지원 직무'} 적합성 근거를 보강합니다."
            )

    if not actions:
        actions.append(
            "최근 변경된 공개 신호가 없으면 기존 교차검증 결과를 유지하고 과도한 주장 확장은 피합니다."
        )
    return _dedupe_preserve_order(actions)[:3]


def _assess_recent_change_action_coverage(
    text: str,
    priority_live_updates: list[dict[str, Any]],
) -> dict[str, Any]:
    lowered = (text or "").lower()
    checks: list[dict[str, Any]] = []
    for item in priority_live_updates[:3]:
        keywords = [
            str(keyword).strip()
            for keyword in item.get("keywords", [])[:3]
            if str(keyword).strip()
        ]
        covered_keywords = [
            keyword for keyword in keywords if keyword.lower() in lowered
        ]
        checks.append(
            {
                "title": str(item.get("title") or item.get("url") or "공개 소스"),
                "change_status": str(item.get("change_status") or ""),
                "change_summary": str(item.get("change_summary") or ""),
                "keywords": keywords,
                "covered_keywords": covered_keywords,
                "covered": bool(covered_keywords),
            }
        )

    covered_count = sum(1 for item in checks if item["covered"])
    return {
        "checked_count": len(checks),
        "covered_count": covered_count,
        "missing_count": max(len(checks) - covered_count, 0),
        "coverage_rate": round(covered_count / len(checks), 2) if checks else 0.0,
        "items": checks,
    }


def _summarize_recent_change_action_check(report: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {}

    items = report.get("items", [])
    if not isinstance(items, list):
        items = []

    missing_titles = [
        str(item.get("title") or "").strip()
        for item in items
        if isinstance(item, dict)
        and not item.get("covered")
        and str(item.get("title") or "").strip()
    ]
    covered_titles = [
        str(item.get("title") or "").strip()
        for item in items
        if isinstance(item, dict)
        and item.get("covered")
        and str(item.get("title") or "").strip()
    ]
    return {
        "checked_count": int(report.get("checked_count", 0) or 0),
        "covered_count": int(report.get("covered_count", 0) or 0),
        "missing_count": int(report.get("missing_count", 0) or 0),
        "coverage_rate": float(report.get("coverage_rate", 0.0) or 0.0),
        "missing_titles": missing_titles[:5],
        "covered_titles": covered_titles[:5],
    }


_POSITIVE_TRACKED_OUTCOMES = {
    "screening_pass",
    "interview_invited",
    "interview_pass",
    "final_pass",
    "offer_received",
}

_NEGATIVE_TRACKED_OUTCOMES = {
    "screening_fail",
    "interview_fail",
    "final_fail",
    "offer_declined",
}


def build_live_change_effectiveness_summary(
    ws: Workspace,
    artifact_type: str | None = None,
) -> dict[str, Any]:
    from .outcome_tracker import OutcomeTracker

    artifacts = load_artifacts(ws)
    outcomes = OutcomeTracker(ws).get_all_outcomes()
    outcomes_by_id = {item.artifact_id: item for item in outcomes if item.artifact_id}

    tracked_artifact_count = 0
    linked_outcome_count = 0
    success_count = 0
    fail_count = 0
    pending_count = 0
    missing_title_counts: dict[str, int] = {}
    coverage_bands: dict[str, dict[str, Any]] = {
        "high": {"count": 0, "success_count": 0, "success_rate": 0.0},
        "medium": {"count": 0, "success_count": 0, "success_rate": 0.0},
        "low": {"count": 0, "success_count": 0, "success_rate": 0.0},
    }

    for artifact in artifacts:
        current_type = (
            artifact.artifact_type.value
            if hasattr(artifact.artifact_type, "value")
            else str(artifact.artifact_type)
        )
        current_type = current_type.strip().lower()
        if artifact_type and current_type != str(artifact_type).strip().lower():
            continue
        input_snapshot = artifact.input_snapshot or {}
        if not isinstance(input_snapshot, dict):
            continue
        report = input_snapshot.get("recent_change_action_check")
        if not isinstance(report, dict):
            continue

        tracked_artifact_count += 1
        outcome = outcomes_by_id.get(artifact.id)
        if outcome is None:
            continue

        linked_outcome_count += 1
        outcome_key = str(outcome.outcome or "pending").strip().lower()
        coverage_rate = float(report.get("coverage_rate", 0.0) or 0.0)
        if coverage_rate >= 0.67:
            band = "high"
        elif coverage_rate >= 0.34:
            band = "medium"
        else:
            band = "low"
        coverage_bands[band]["count"] += 1

        if outcome_key in _POSITIVE_TRACKED_OUTCOMES:
            success_count += 1
            coverage_bands[band]["success_count"] += 1
        elif outcome_key in _NEGATIVE_TRACKED_OUTCOMES:
            fail_count += 1
            for item in report.get("items", []) or []:
                if not isinstance(item, dict) or item.get("covered"):
                    continue
                title = str(item.get("title") or "").strip()
                if title:
                    missing_title_counts[title] = missing_title_counts.get(title, 0) + 1
        else:
            pending_count += 1

    for stats in coverage_bands.values():
        count = int(stats.get("count", 0) or 0)
        successes = int(stats.get("success_count", 0) or 0)
        stats["success_rate"] = round(successes / count, 2) if count else 0.0

    top_missing_titles = [
        {"title": title, "count": count}
        for title, count in sorted(
            missing_title_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
    ]

    high_success_rate = float(coverage_bands["high"]["success_rate"])
    low_success_rate = float(coverage_bands["low"]["success_rate"])
    return {
        "tracked_artifact_count": tracked_artifact_count,
        "linked_outcome_count": linked_outcome_count,
        "success_count": success_count,
        "fail_count": fail_count,
        "pending_count": pending_count,
        "coverage_bands": coverage_bands,
        "high_vs_low_success_gap": round(high_success_rate - low_success_rate, 2),
        "top_missing_titles": top_missing_titles,
    }


def _normalize_strategy_payload(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat") and callable(value.isoformat):
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if is_dataclass(value):
        return _normalize_strategy_payload(asdict(value))
    if isinstance(value, dict):
        return {
            str(key): _normalize_strategy_payload(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_strategy_payload(item) for item in value]
    if hasattr(value, "model_dump"):
        return _normalize_strategy_payload(value.model_dump())
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _normalize_strategy_payload(value.to_dict())
    if hasattr(value, "__dict__"):
        return _normalize_strategy_payload(
            {
                key: item
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        )
    return str(value)


def _read_application_strategy(ws: Workspace) -> dict[str, Any]:
    existing = read_json_if_exists(ws.analysis_dir / "application_strategy.json")
    return existing if isinstance(existing, dict) else {}


def _build_experience_priority_summary(
    experiences: list[Experience],
    allocations: list[dict[str, Any]] | None = None,
    coach_analysis: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    prioritized: list[dict[str, Any]] = []
    if allocations:
        for item in allocations:
            if not isinstance(item, dict):
                continue
            exp_id = str(item.get("experience_id", "")).strip()
            if not exp_id:
                continue
            prioritized.append(
                {
                    "experience_id": exp_id,
                    "question_id": str(item.get("question_id", "")).strip(),
                    "question_type": str(item.get("question_type", "")).strip(),
                    "reason": str(item.get("reason", "")).strip(),
                }
            )
    if prioritized:
        return prioritized

    coverage = (coach_analysis or {}).get("coverage_report", {})
    ranked = coverage.get("top_experience_ids", []) if isinstance(coverage, dict) else []
    by_id = {exp.id: exp for exp in experiences}
    summary: list[dict[str, Any]] = []
    for exp_id in ranked:
        exp = by_id.get(str(exp_id))
        if not exp:
            continue
        summary.append(
            {
                "experience_id": exp.id,
                "title": exp.title,
                "reason": "질문 커버리지와 증빙 수준 기준 상위 경험",
            }
        )
    if summary:
        return summary
    return [
        {
            "experience_id": exp.id,
            "title": exp.title,
            "reason": "기본 우선 경험",
        }
        for exp in experiences[:3]
    ]


def build_adaptive_strategy_layer(
    project: ApplicationProject,
    *,
    candidate_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    company_type = (project.company_type or "일반").strip()
    if company_type in {"공공", "공기업"}:
        interview_mode = "구조화 질문 + 공익성/책임감 검증"
        writer_logic = "정책·서비스 맥락을 먼저 두고, 개인 판단 기준과 증빙을 뒤에 붙입니다."
    elif company_type in {"대기업", "중견"}:
        interview_mode = "압박형 검증 + 협업/우선순위 판단 확인"
        writer_logic = "문제-행동-성과를 빠르게 제시하고 조직 적합성으로 마무리합니다."
    else:
        interview_mode = "실행력 검증 + 모호성 대응"
        writer_logic = "가설-실험-학습 구조를 강조하고, 제한된 자원에서의 판단을 드러냅니다."

    confidence_style = (candidate_profile or {}).get("confidence_style", "balanced")
    if confidence_style == "logical":
        coaching_mode = "수치와 비교 기준을 먼저 묻고, 결론을 짧게 압축합니다."
    elif confidence_style == "relational":
        coaching_mode = "협업 맥락은 유지하되 개인 기여와 판단 근거를 더 선명하게 끌어냅니다."
    else:
        coaching_mode = "핵심 메시지를 먼저 세우고 경험 근거를 뒤에서 지지하는 방식으로 훈련합니다."

    return {
        "company_profile": company_type,
        "interview_mode": interview_mode,
        "writer_logic": writer_logic,
        "coaching_mode": coaching_mode,
        "career_stage": project.career_stage.value,
    }


def build_experience_competition_report(
    project: ApplicationProject,
    experiences: list[Experience],
    allocations: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not project.questions:
        return []

    experience_by_id = {exp.id: exp for exp in experiences}
    selected_ids = [
        str(item.get("experience_id", "")).strip()
        for item in allocations or []
        if isinstance(item, dict) and str(item.get("experience_id", "")).strip()
    ]
    selected_set = set(selected_ids)

    rows: list[dict[str, Any]] = []
    for question in project.questions:
        mapped = next(
            (
                item
                for item in allocations or []
                if isinstance(item, dict)
                and str(item.get("question_id", "")).strip() == question.id
            ),
            {},
        )
        primary_id = str(mapped.get("experience_id", "")).strip()
        primary = experience_by_id.get(primary_id)
        question_keywords = set(
            re.findall(r"[A-Za-z0-9가-힣]{2,}", (question.question_text or "").lower())
        )

        secondary_candidates: list[tuple[int, Experience]] = []
        for exp in experiences:
            if exp.id == primary_id:
                continue
            blob = " ".join(
                [
                    exp.title,
                    exp.situation,
                    exp.task,
                    exp.action,
                    exp.result,
                    " ".join(exp.tags),
                ]
            ).lower()
            score = sum(1 for keyword in question_keywords if keyword and keyword in blob)
            if exp.metrics:
                score += 1
            if exp.id not in selected_set:
                score += 1
            secondary_candidates.append((score, exp))
        secondary_candidates.sort(key=lambda item: item[0], reverse=True)
        secondary = secondary_candidates[0][1] if secondary_candidates else None

        exclusion_reason = (
            "주요 경험이 이미 다른 문항에서 반복 사용되어 차별화가 약해질 수 있습니다."
            if secondary and secondary.id in selected_set
            else "정량 근거나 직무 연결성이 더 높은 경험을 우선 배치했습니다."
        )
        rows.append(
            {
                "question_id": question.id,
                "question_text": question.question_text,
                "question_type": _resolve_question_type(question).value,
                "primary_experience_id": primary.id if primary else "",
                "primary_experience_title": primary.title if primary else "",
                "primary_reason": str(mapped.get("reason", "")).strip()
                or "질문 의도와 가장 직접 연결되는 경험입니다.",
                "secondary_experience_id": secondary.id if secondary else "",
                "secondary_experience_title": secondary.title if secondary else "",
                "secondary_reason": (
                    "대체 카드로 활용 가능하지만, 현재 1순위 경험보다 직결성이 약합니다."
                    if secondary
                    else "대체 경험 후보가 아직 충분하지 않습니다."
                ),
                "exclusion_reason": exclusion_reason,
            }
        )
    return rows


def build_writer_differentiation_report(
    project: ApplicationProject,
    quality_evaluations: list[dict[str, Any]],
    *,
    research_strategy_translation: dict[str, Any] | None = None,
    application_strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question_strategy = (
        application_strategy.get("question_strategy", {})
        if isinstance(application_strategy, dict)
        else {}
    )
    interview_pressure_points = (
        application_strategy.get("interview_pressure_points", [])
        if isinstance(application_strategy, dict)
        else []
    )
    top001_strategy = (
        research_strategy_translation.get("top001", {})
        if isinstance(research_strategy_translation, dict)
        else {}
    )
    differentiation_signals = (
        top001_strategy.get("strategic_signals", {}).get("differentiation", [])
        if isinstance(top001_strategy, dict)
        else []
    )

    rows: list[dict[str, Any]] = []
    for item in quality_evaluations:
        question_id = str(item.get("question_id", "")).strip()
        weaknesses = item.get("weaknesses", [])[:2]
        suggestions = item.get("suggestions", [])[:2]
        rows.append(
            {
                "question_order": item.get("question_order"),
                "question_id": question_id,
                "question_text": item.get("question_text", ""),
                "current_score": float(item.get("overall_score", 0.0)),
                "ordinary_pattern": (
                    "지원동기/역량을 일반론으로 설명하고, 개인 기여보다 포부 문장으로 마무리하는 패턴"
                ),
                "current_answer_risk": weaknesses or item.get("defense_gaps", [])[:2],
                "top001_strategy": question_strategy.get(question_id, [])[:2]
                or differentiation_signals[:2]
                or ["회사 신호와 경험 연결고리를 문장 첫머리에 배치"],
                "rewrite_focus": suggestions
                or ["질문 의도에 맞는 경험 근거를 한 문장 더 앞당겨 배치"],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company_name": project.company_name,
        "job_title": project.job_title,
        "pressure_points": interview_pressure_points[:5],
        "rows": rows,
    }


def update_application_strategy(
    ws: Workspace,
    *,
    project: ApplicationProject,
    stage: str,
    experiences: list[Experience] | None = None,
    allocations: list[dict[str, Any]] | None = None,
    coach_analysis: dict[str, Any] | None = None,
    self_intro_pack: dict[str, Any] | None = None,
    research_strategy: dict[str, Any] | None = None,
    interview_top001: list[dict[str, Any]] | None = None,
    experience_competition: list[dict[str, Any]] | None = None,
    writer_differentiation: dict[str, Any] | None = None,
    adaptive_strategy: dict[str, Any] | None = None,
    feedback_adaptation_plan: dict[str, Any] | None = None,
    recent_change_action_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    strategy = _read_application_strategy(ws)
    strategy.update(
        {
            "company_name": project.company_name,
            "job_title": project.job_title,
            "company_type": project.company_type,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    if research_strategy:
        signals = research_strategy.get("strategic_signals", {})
        strategy["company_signal_summary"] = {
            "core_values": signals.get("core_values", []),
            "competencies": signals.get("competencies", []),
            "differentiation": signals.get("differentiation", []),
        }
        strategy["question_strategy"] = research_strategy.get("question_hooks", {})
        strategy["interview_pressure_points"] = [
            item.get("q", str(item))
            for item in research_strategy.get("interview_predictions", [])[:5]
            if item
        ]

    if experiences:
        strategy["experience_priority"] = _build_experience_priority_summary(
            experiences, allocations=allocations, coach_analysis=coach_analysis
        )

    if coach_analysis:
        strategy["coach_recommendations"] = coach_analysis.get("suggestions", [])
        strategy["experience_coverage"] = coach_analysis.get("coverage_report", {})
    if experience_competition:
        strategy["experience_competition"] = experience_competition

    if self_intro_pack:
        strategy["self_intro_candidates"] = {
            "opening_hook": self_intro_pack.get("opening_hook", ""),
            "top001_hooks": self_intro_pack.get("top001_hooks", []),
            "top001_versions": self_intro_pack.get("top001_versions", {}),
            "expected_follow_ups": self_intro_pack.get(
                "top001_expected_follow_ups", []
            ),
        }

    if interview_top001:
        pressure_points = strategy.get("interview_pressure_points", [])
        for item in interview_top001:
            for vulnerability in item.get("vulnerabilities", [])[:2]:
                if vulnerability and vulnerability not in pressure_points:
                    pressure_points.append(vulnerability)
        strategy["interview_pressure_points"] = pressure_points[:8]
        strategy["interview_strategy"] = {
            "weak_response_count": sum(
                1 for item in interview_top001 if item.get("weak_response")
            ),
            "top_recommendations": _dedupe_preserve_order(
                recommendation
                for item in interview_top001
                for recommendation in item.get("recommendations", [])
            )[:6],
        }
    if writer_differentiation:
        strategy["writer_differentiation"] = writer_differentiation
    if adaptive_strategy:
        strategy["adaptive_strategy_layer"] = adaptive_strategy
    if feedback_adaptation_plan:
        strategy["feedback_adaptation_plan"] = feedback_adaptation_plan
    if recent_change_action_check:
        live_change_action_learning = strategy.get("live_change_action_learning", {})
        if not isinstance(live_change_action_learning, dict):
            live_change_action_learning = {}
        stage_reports = live_change_action_learning.get("stage_reports", {})
        if not isinstance(stage_reports, dict):
            stage_reports = {}
        stage_reports[stage] = _summarize_recent_change_action_check(
            recent_change_action_check
        )
        valid_reports = [
            report
            for report in stage_reports.values()
            if isinstance(report, dict) and report.get("checked_count", 0)
        ]
        average_coverage_rate = (
            round(
                sum(float(report.get("coverage_rate", 0.0)) for report in valid_reports)
                / len(valid_reports),
                2,
            )
            if valid_reports
            else 0.0
        )
        live_change_action_learning = {
            "latest_stage": stage,
            "average_coverage_rate": average_coverage_rate,
            "stage_reports": stage_reports,
            "focus_titles": stage_reports[stage].get("missing_titles", []),
        }
        strategy["live_change_action_learning"] = live_change_action_learning

    stage_payloads = strategy.get("stage_payloads", {})
    if not isinstance(stage_payloads, dict):
        stage_payloads = {}
    stage_payloads[stage] = _normalize_strategy_payload(
        {
            "coach_analysis": coach_analysis,
            "self_intro_pack": self_intro_pack,
            "research_strategy": research_strategy,
            "interview_top001": interview_top001,
            "allocations": allocations,
            "experience_competition": experience_competition,
            "writer_differentiation": writer_differentiation,
            "adaptive_strategy": adaptive_strategy,
            "feedback_adaptation_plan": feedback_adaptation_plan,
            "recent_change_action_check": recent_change_action_check,
        }
    )
    strategy["stage_payloads"] = stage_payloads

    write_json(ws.analysis_dir / "application_strategy.json", strategy)
    return strategy


def build_outcome_dashboard(
    ws: Workspace,
    project: ApplicationProject,
    artifact_type: str = "writer",
) -> dict[str, Any]:
    feedback_learning = build_feedback_learning_context(
        ws, artifact_type, project=project
    )
    strategy_summary = feedback_learning.get("strategy_outcome_summary", {})
    top_hotspots: list[dict[str, Any]] = []
    for q_type, exp_map in (
        strategy_summary.get("experience_stats_by_question_type", {}) or {}
    ).items():
        for exp_id, stats in exp_map.items():
            top_hotspots.append(
                {
                    "question_type": q_type,
                    "experience_id": exp_id,
                    "weighted_net_score": int(stats.get("weighted_net_score", 0)),
                    "total_uses": int(stats.get("total_uses", 0)),
                }
            )
    top_hotspots.sort(
        key=lambda item: (item["weighted_net_score"], -item["total_uses"])
    )
    application_strategy = read_json_if_exists(ws.analysis_dir / "application_strategy.json")
    live_change_action_learning = (
        application_strategy.get("live_change_action_learning", {})
        if isinstance(application_strategy, dict)
        else {}
    )
    live_change_effectiveness = build_live_change_effectiveness_summary(
        ws, artifact_type=artifact_type
    )
    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_type": artifact_type,
        "current_pattern": feedback_learning.get("current_pattern"),
        "overall_success_rate": feedback_learning.get("overall_success_rate", 0),
        "outcome_summary": feedback_learning.get("outcome_summary", {}),
        "recommended_pattern": feedback_learning.get("recommended_pattern"),
        "high_risk_hotspots": top_hotspots[:5],
        "live_change_action_learning": live_change_action_learning,
        "live_change_effectiveness": live_change_effectiveness,
    }
    write_json(ws.analysis_dir / "outcome_dashboard.json", dashboard)
    return dashboard


def build_kpi_dashboard(
    ws: Workspace,
    project: ApplicationProject,
    artifact_type: str = "writer",
) -> dict[str, Any]:
    feedback_learning = build_feedback_learning_context(
        ws, artifact_type, project=project
    )
    strategy_summary = feedback_learning.get("strategy_outcome_summary", {}) or {}
    outcome_summary = feedback_learning.get("outcome_summary", {}) or {}
    application_strategy = read_json_if_exists(ws.analysis_dir / "application_strategy.json")
    self_intro_drills = read_json_if_exists(ws.state_dir / "self_intro_drills.json") or []
    interview_sessions = read_json_if_exists(ws.state_dir / "interview_sessions.json") or []
    writer_quality = read_json_if_exists(ws.artifacts_dir / "writer_quality.json") or []
    writer_result_quality = (
        read_json_if_exists(ws.artifacts_dir / "writer_result_quality.json") or []
    )

    experience_stats = strategy_summary.get("experience_stats_by_question_type", {}) or {}
    pass_rates: list[float] = []
    for type_bucket in experience_stats.values():
        for exp_bucket in type_bucket.values():
            try:
                pass_rates.append(float(exp_bucket.get("pass_rate", 0.0)))
            except (TypeError, ValueError):
                continue

    question_experience_match_accuracy = (
        round(sum(pass_rates) / len(pass_rates), 3) if pass_rates else 0.0
    )

    outcome_breakdown = outcome_summary.get("outcome_breakdown", {}) or {}
    total_outcomes = sum(int(value) for value in outcome_breakdown.values()) or 0
    interview_pass_rate = round(
        (
            int(outcome_breakdown.get("interview_pass", 0))
            + int(outcome_breakdown.get("pass", 0))
            + int(outcome_breakdown.get("offer", 0))
        )
        / total_outcomes,
        3,
    ) if total_outcomes else 0.0
    document_pass_rate = round(
        (
            int(outcome_breakdown.get("document_pass", 0))
            + int(outcome_breakdown.get("pass", 0))
            + int(outcome_breakdown.get("offer", 0))
        )
        / total_outcomes,
        3,
    ) if total_outcomes else 0.0
    offer_rate = round(
        int(outcome_breakdown.get("offer", 0)) / total_outcomes,
        3,
    ) if total_outcomes else 0.0

    drill_scores = [
        float(item.get("score", 0.0))
        for item in self_intro_drills
        if isinstance(item, dict) and item.get("score") is not None
    ]
    self_intro_follow_up_hit_rate = (
        round(sum(drill_scores) / len(drill_scores), 3) if drill_scores else 0.0
    )

    session_risk_counts = [
        sum(
            len(turn.get("risk_areas", [])) + len(turn.get("follow_up_risk_areas", []))
            for turn in session.get("turns", [])
            if isinstance(turn, dict)
        )
        for session in interview_sessions
        if isinstance(session, dict)
    ]
    interview_defense_success_rate = (
        round(
            sum(1 for count in session_risk_counts if count <= 2)
            / len(session_risk_counts),
            3,
        )
        if session_risk_counts
        else 0.0
    )

    question_strategy = (
        application_strategy.get("question_strategy", {})
        if isinstance(application_strategy, dict)
        else {}
    )
    company_signal_summary = (
        application_strategy.get("company_signal_summary", {})
        if isinstance(application_strategy, dict)
        else {}
    )
    live_change_effectiveness = build_live_change_effectiveness_summary(
        ws, artifact_type=artifact_type
    )
    company_signal_reuse_rate = round(
        (
            len([value for value in question_strategy.values() if value])
            / max(1, len(project.questions))
        ),
        3,
    ) if project.questions else 0.0

    writer_quality_metrics: dict[str, float] = {}
    if isinstance(writer_quality, list):
        metric_keys = [
            "overall_score",
            "defensibility_score",
            "ncs_alignment_score",
            "ssot_alignment_score",
            "humanization_score",
        ]
        for metric_key in metric_keys:
            values: list[float] = []
            for item in writer_quality:
                if not isinstance(item, dict):
                    continue
                try:
                    value = float(item.get(metric_key, 0.0))
                except (TypeError, ValueError):
                    continue
                values.append(value)
            if values:
                writer_quality_metrics[metric_key] = round(
                    sum(values) / len(values), 3
                )

    result_quality_metrics: dict[str, float] = {}
    if isinstance(writer_result_quality, list):
        overall_values = []
        dimension_values: dict[str, list[float]] = {}
        for item in writer_result_quality:
            if not isinstance(item, dict):
                continue
            try:
                overall_values.append(float(item.get("overall", 0.0)))
            except (TypeError, ValueError):
                pass
            details = item.get("details", {})
            if isinstance(details, dict):
                for key, raw_value in details.items():
                    try:
                        dimension_values.setdefault(key, []).append(float(raw_value))
                    except (TypeError, ValueError):
                        continue
        if overall_values:
            result_quality_metrics["overall"] = round(
                sum(overall_values) / len(overall_values), 3
            )
        for key, values in dimension_values.items():
            if values:
                result_quality_metrics[key] = round(sum(values) / len(values), 3)

    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_type": artifact_type,
        "question_experience_match_accuracy": question_experience_match_accuracy,
        "self_intro_follow_up_hit_rate": self_intro_follow_up_hit_rate,
        "interview_defense_success_rate": interview_defense_success_rate,
        "company_signal_reuse_rate": company_signal_reuse_rate,
        "document_pass_rate": document_pass_rate,
        "interview_pass_rate": interview_pass_rate,
        "offer_rate": offer_rate,
        "company_signal_summary": company_signal_summary,
        "writer_quality_metrics": writer_quality_metrics,
        "result_quality_metrics": result_quality_metrics,
        "tracked_outcomes": outcome_breakdown,
        "live_change_linked_outcomes": live_change_effectiveness.get(
            "linked_outcome_count", 0
        ),
        "live_change_high_coverage_success_rate": (
            live_change_effectiveness.get("coverage_bands", {})
            .get("high", {})
            .get("success_rate", 0.0)
        ),
        "live_change_low_coverage_success_rate": (
            live_change_effectiveness.get("coverage_bands", {})
            .get("low", {})
            .get("success_rate", 0.0)
        ),
        "live_change_success_gap": live_change_effectiveness.get(
            "high_vs_low_success_gap", 0.0
        ),
        "live_change_top_missing_titles": live_change_effectiveness.get(
            "top_missing_titles", []
        ),
    }
    write_json(ws.analysis_dir / "kpi_dashboard.json", dashboard)
    return dashboard


def build_blind_benchmark_frame(
    ws: Workspace,
    *,
    project: ApplicationProject | None = None,
) -> dict[str, Any]:
    project = project or load_project(ws)
    frame = {
        "company_name": project.company_name,
        "job_title": project.job_title,
        "candidate_count": 3,
        "candidates": [
            {"id": "human_expert", "label": "인간 전문가 버전", "blind_code": "A"},
            {"id": "resume_agent", "label": "resume-agent 버전", "blind_code": "B"},
            {"id": "hybrid", "label": "혼합 버전", "blind_code": "C"},
        ],
        "questions": [
            {
                "question_id": question.id,
                "order_no": question.order_no,
                "question_text": question.question_text,
                "question_type": (
                    question.detected_type.value
                    if getattr(question, "detected_type", None)
                    else QuestionType.TYPE_UNKNOWN.value
                ),
            }
            for question in project.questions
        ],
        "rubric": [
            "질문 적합성",
            "구체성",
            "개인 기여 명확성",
            "면접 방어 가능성",
            "조직 적합성",
            "문장 자연스러움",
        ],
        "outcome_metrics": [
            "document_pass_rate",
            "interview_pass_rate",
            "final_pass_rate",
            "offer_rate",
        ],
        "instructions": [
            "평가자는 작성 주체를 모르는 상태에서 각 버전을 비교합니다.",
            "문항별 점수와 최종 선호 버전을 함께 기록합니다.",
            "가능하면 실제 서류·면접 결과와 연결해 후속 분석합니다.",
        ],
    }
    write_json(ws.analysis_dir / "blind_benchmark_frame.json", frame)
    return frame


def evaluate_narrative_ssot_alignment(
    answer: str,
    *,
    experience: Experience | None,
    narrative_ssot: dict[str, Any] | None,
) -> dict[str, Any]:
    if not answer.strip() or not isinstance(narrative_ssot, dict):
        return {
            "score": 1.0,
            "expected_claims": [],
            "matched_claims": [],
            "missing_claims": [],
            "offtrack_signals": [],
            "suggestions": [],
        }

    core_claims = [
        str(item).strip()
        for item in narrative_ssot.get("core_claims", [])
        if str(item).strip()
    ]
    expected_experience_ids = {
        str(item).strip()
        for item in (narrative_ssot.get("evidence_experience_ids", []) or [])
        if str(item).strip()
    }
    anchor = str(narrative_ssot.get("answer_anchor") or "").strip()
    answer_tokens = set(re.findall(r"[A-Za-z0-9가-힣]{2,}", answer.lower()))

    matched_claims: list[str] = []
    missing_claims: list[str] = []
    for claim in core_claims[:3]:
        claim_tokens = {
            token for token in re.findall(r"[A-Za-z0-9가-힣]{2,}", claim.lower())
        }
        if claim_tokens and claim_tokens & answer_tokens:
            matched_claims.append(claim)
        else:
            missing_claims.append(claim)

    offtrack_signals: list[str] = []
    if (
        experience
        and expected_experience_ids
        and experience.id not in expected_experience_ids
    ):
        offtrack_signals.append(
            "공통 서사에서 우선 선정되지 않은 경험을 사용하고 있습니다."
        )
    if anchor:
        anchor_tokens = {
            token for token in re.findall(r"[A-Za-z0-9가-힣]{2,}", anchor.lower())
        }
        if anchor_tokens and not (anchor_tokens & answer_tokens):
            offtrack_signals.append("공통 답변 앵커와 어조가 약하게 연결됩니다.")

    denominator = max(1, len(core_claims) + len(offtrack_signals))
    score = max(
        0.0,
        min(
            1.0,
            round(
                (len(matched_claims) + (1 if not offtrack_signals else 0))
                / denominator,
                2,
            ),
        ),
    )
    suggestions: list[str] = []
    if missing_claims:
        suggestions.append(
            "공통 서사의 핵심 주장 중 최소 1개를 문장 전면에 다시 드러내세요."
        )
    if offtrack_signals:
        suggestions.append(
            "자소서·자기소개·면접의 공통 근거 경험과 답변 앵커를 더 일치시키세요."
        )

    return {
        "score": score,
        "expected_claims": core_claims,
        "matched_claims": matched_claims,
        "missing_claims": missing_claims,
        "offtrack_signals": offtrack_signals,
        "suggestions": suggestions,
    }


def _simulate_interviewer_reaction(
    answer: str,
    simulation: dict[str, Any],
    experience: Experience | None = None,
) -> dict[str, Any]:
    answer = answer or ""
    trust = (
        "high"
        if any(char.isdigit() for char in answer)
        or (experience and experience.evidence_text.strip())
        else "medium"
    )
    if len(simulation.get("risk_areas", [])) >= 3:
        trust = "medium" if trust == "high" else "low"
    specificity = (
        "high"
        if len(answer) >= 80 and any(char.isdigit() for char in answer)
        else "medium"
    )
    if len(answer) < 50:
        specificity = "low"
    next_probe = (
        simulation.get(
            "follow_up_questions", ["왜 그렇게 판단했는지 다시 설명해주세요."]
        )[0]
        if simulation.get("follow_up_questions")
        else "그 판단의 근거를 다시 설명해주세요."
    )
    return {
        "trust_signal": trust,
        "specificity_signal": specificity,
        "impression": "근거는 있으나 더 선명한 개인 기여 설명이 필요합니다."
        if simulation.get("risk_areas")
        else "구조와 근거가 비교적 안정적으로 들립니다.",
        "next_probe": next_probe,
    }


def _build_interviewer_reaction_chain(
    answer: str,
    simulation: dict[str, Any],
    *,
    experience: Experience | None = None,
) -> list[dict[str, Any]]:
    base = _simulate_interviewer_reaction(answer, simulation, experience=experience)
    risk_areas = simulation.get("risk_areas", [])
    follow_ups = simulation.get("follow_up_questions", [])
    return [
        {
            "turn": 1,
            "stage": "first_impression",
            "reaction": base["impression"],
            "signal": base["trust_signal"],
        },
        {
            "turn": 2,
            "stage": "probe",
            "reaction": base["next_probe"],
            "signal": (
                risk_areas[0]
                if risk_areas
                else "핵심 근거를 더 구체적으로 확인하고 싶습니다."
            ),
        },
        {
            "turn": 3,
            "stage": "verdict_shift",
            "reaction": (
                "답변 보강 시 설득력이 올라갈 수 있습니다."
                if risk_areas or follow_ups
                else "현재 답변만으로도 비교적 안정적으로 들립니다."
            ),
            "signal": (
                follow_ups[0]
                if follow_ups
                else "추가 질문 없이도 핵심 메시지가 유지됩니다."
            ),
        },
    ]


def build_committee_feedback_context(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    sessions = read_json_if_exists(ws.state_dir / "interview_sessions.json") or []
    latest_session = sessions[-1] if sessions else {}
    turns = latest_session.get("turns", [])
    recurring_risks: list[str] = []
    personas: list[str] = []
    verdicts: list[str] = []

    for turn in turns:
        recurring_risks.extend(turn.get("risk_areas", []))
        recurring_risks.extend(turn.get("follow_up_risk_areas", []))
        personas.append(turn.get("interviewer_persona", ""))
        for round_item in turn.get("committee_rounds", []):
            recurring_risks.extend(round_item.get("risk_areas", []))
            personas.append(round_item.get("persona", ""))
        summary = turn.get("committee_summary", {})
        if isinstance(summary, dict) and summary.get("verdict"):
            verdicts.append(summary["verdict"])

    return {
        "session_count": len(sessions),
        "latest_session_mode": latest_session.get("mode", ""),
        "latest_turn_count": len(turns),
        "latest_committee_verdict": verdicts[-1] if verdicts else "",
        "recurring_risks": _dedupe_preserve_order(
            [item for item in recurring_risks if item]
        )[:6],
        "persona_panel": _dedupe_preserve_order([item for item in personas if item])[
            :6
        ],
    }


def build_self_intro_pack(
    ws: Workspace,
    project: ApplicationProject,
    company_analysis: CompanyAnalysis | None = None,
) -> dict[str, Any]:
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    committee_feedback = build_committee_feedback_context(ws)
    experiences = load_experiences(ws)
    source_grading = read_json_if_exists(ws.analysis_dir / "source_grading.json")

    strategy_pack: dict[str, Any] = {}
    if company_analysis:
        strategy_pack = build_role_industry_strategy_from_project(
            project,
            company_analysis,
            question_map=question_map,
            source_grading=source_grading,
        )
    ncs_profile = build_ncs_profile(
        ws,
        project=project,
        experiences=experiences,
        question_map=question_map,
        company_analysis=company_analysis,
    )

    prioritized = select_primary_experiences(experiences, question_map)[:2]
    top_experience_titles = [exp.title for exp in prioritized]
    focus_keywords = _dedupe_preserve_order(
        strategy_pack.get("evidence_priority", [])[:3]
        + ncs_profile.get("priority_competencies", [])[:2]
    )[:4]
    banned_patterns = strategy_pack.get("banned_patterns", [])[:3]
    recurring_risks = committee_feedback.get("recurring_risks", [])[:3]

    opening = (
        f"{project.company_name or '지원 기관'}의 {project.job_title or '직무'}에서 "
        f"{', '.join(focus_keywords) if focus_keywords else '검증 가능한 성과'}를 만드는 지원자입니다."
    )
    intro_pack = {
        "opening_hook": opening,
        "thirty_second_frame": [
            "현재 지원 직무와 가장 직접 연결되는 경험 1개를 먼저 말한다.",
            f"핵심 경험: {', '.join(top_experience_titles) if top_experience_titles else '주요 경험 정리 필요'}",
            f"마무리는 {project.company_name or '해당 조직'}에서의 첫 기여 포인트로 닫는다.",
        ],
        "sixty_second_frame": [
            "지원 직무와 연결되는 문제 인식",
            "본인 행동과 판단 기준",
            "정량 또는 정성 결과",
            "입사 후 적용 계획",
        ],
        "focus_keywords": focus_keywords,
        "banned_patterns": banned_patterns,
        "committee_watchouts": recurring_risks,
        "ncs_priority_competencies": ncs_profile.get("priority_competencies", [])[:3],
    }

    top001_pack: dict[str, Any] = {}
    try:
        from .top001.integrator import Top001CoachEngine

        top001_pack = Top001CoachEngine().generate_self_intro_pack(
            experiences,
            project.company_name or "지원 기관",
            project.job_title or "지원 직무",
        )
    except Exception as e:
        logger.warning(f"Top001 self intro build failed: {e}")

    if top001_pack and isinstance(top001_pack, dict):
        intro_pack["top001_hooks"] = top001_pack.get("hooks", [])
        intro_pack["top001_versions"] = top001_pack.get("versions", {})
        intro_pack["top001_expected_follow_ups"] = top001_pack.get(
            "expected_follow_ups", []
        )
        write_json(
            ws.analysis_dir / "self_intro_top001.json",
            _normalize_strategy_payload(top001_pack),
        )

    write_json(ws.analysis_dir / "self_intro_pack.json", intro_pack)
    update_application_strategy(
        ws,
        project=project,
        stage="self_intro",
        experiences=experiences,
        self_intro_pack=intro_pack,
    )
    return intro_pack


def discover_company_public_urls(
    ws: Workspace,
    max_results_per_query: int = 3,
) -> dict[str, Any]:
    ws.ensure()
    project = load_project(ws)
    brief = build_research_brief(ws)
    queries = _dedupe_preserve_order(
        [
            f"{project.company_name} {project.job_title} 채용",
            f"{project.company_name} {project.job_title} 직무",
            f"{project.company_name} 기업문화 인재상",
            *brief.get("key_questions", [])[:2],
        ]
    )
    discovered: list[dict[str, str]] = []
    for query in queries:
        if not query.strip():
            continue
        try:
            discovered.extend(discover_public_urls(query, limit=max_results_per_query))
        except Exception as e:
            logger.warning(f"웹 검색 실패 ({query}): {e}")

    deduped: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in discovered:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)

    payload = {"queries": queries, "results": deduped}
    write_json(ws.analysis_dir / "web_discovery.json", payload)
    return payload


def crawl_web_sources_auto(
    ws: Workspace,
    max_results_per_query: int = 3,
    max_urls: int = 8,
) -> dict[str, Any]:
    ws.ensure()
    discovery = discover_company_public_urls(
        ws,
        max_results_per_query=max_results_per_query,
    )
    urls = [item["url"] for item in discovery["results"][:max_urls]]
    crawl_result = (
        crawl_web_sources(ws, urls)
        if urls
        else {"source_count": 0, "stored_count": len(load_knowledge_sources(ws))}
    )
    result = {
        "query_count": len(discovery["queries"]),
        "discovered_url_count": len(discovery["results"]),
        "ingested_url_count": len(urls),
        "discovery_path": str(ws.analysis_dir / "web_discovery.json"),
        **crawl_result,
    }
    return result


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


NCS_COMMON_COMPETENCY_SIGNALS: dict[str, dict[str, Any]] = {
    "의사소통능력": {
        "keywords": [
            "소통",
            "설명",
            "문서",
            "보고",
            "회의",
            "민원",
            "고객",
            "경청",
            "표현",
            "안내",
        ],
        "question_types": ["TYPE_A", "TYPE_C", "TYPE_H"],
    },
    "수리능력": {
        "keywords": [
            "통계",
            "지표",
            "수치",
            "분석",
            "엑셀",
            "정산",
            "계산",
            "검증",
            "도표",
            "sql",
        ],
        "question_types": ["TYPE_B", "TYPE_G"],
    },
    "문제해결능력": {
        "keywords": [
            "문제",
            "해결",
            "개선",
            "위기",
            "대응",
            "수습",
            "자동화",
            "대안",
            "조치",
        ],
        "question_types": ["TYPE_B", "TYPE_G", "TYPE_I"],
    },
    "자기관리능력": {
        "keywords": [
            "학습",
            "성장",
            "개선",
            "적응",
            "피드백",
            "시간관리",
            "습관",
            "꾸준",
        ],
        "question_types": ["TYPE_D", "TYPE_F"],
    },
    "자원관리능력": {
        "keywords": [
            "예산",
            "시간",
            "우선순위",
            "자원",
            "인력",
            "관리",
            "배분",
            "절감",
        ],
        "question_types": ["TYPE_B", "TYPE_E"],
    },
    "대인관계능력": {
        "keywords": [
            "협업",
            "팀",
            "갈등",
            "설득",
            "조율",
            "협상",
            "고객서비스",
            "중재",
        ],
        "question_types": ["TYPE_C", "TYPE_H"],
    },
    "정보능력": {
        "keywords": ["자료", "정보", "검색", "출처", "비교", "정리", "리서치", "검토"],
        "question_types": ["TYPE_B", "TYPE_D"],
    },
    "기술능력": {
        "keywords": [
            "시스템",
            "도구",
            "기술",
            "활용",
            "프로그램",
            "업무도구",
            "디지털",
        ],
        "question_types": ["TYPE_B", "TYPE_E"],
    },
    "조직이해능력": {
        "keywords": [
            "조직",
            "행정",
            "공공",
            "기관",
            "업무이해",
            "규정",
            "절차",
            "정책",
        ],
        "question_types": ["TYPE_A", "TYPE_E", "TYPE_F"],
    },
    "직업윤리": {
        "keywords": ["윤리", "청렴", "공정", "원칙", "준수", "책임", "정확", "신뢰"],
        "question_types": ["TYPE_F", "TYPE_G", "TYPE_I"],
    },
    "디지털능력": {
        "keywords": ["디지털", "ai", "자동화", "데이터", "엑셀", "시스템", "온라인"],
        "question_types": ["TYPE_B", "TYPE_E"],
    },
}

NCS_PUBLIC_COMPANY_PRIORITIES = [
    "의사소통능력",
    "문제해결능력",
    "대인관계능력",
    "직업윤리",
    "조직이해능력",
]


def build_ncs_profile(
    ws: Workspace,
    project: ApplicationProject | None = None,
    experiences: list[Experience] | None = None,
    question_map: list[dict[str, Any]] | None = None,
    jd_keywords: list[str] | None = None,
    company_analysis: CompanyAnalysis | None = None,
) -> dict[str, Any]:
    """NCS 직업공통능력 관점에서 경험/JD/문항을 재해석한 프로필을 생성합니다."""
    ws.ensure()
    project = project or load_project(ws)
    experiences = experiences or load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = (
        question_map or read_json_if_exists(ws.analysis_dir / "question_map.json") or []
    )
    jd_keywords = jd_keywords or _extract_jd_keywords_for_research(ws)
    try:
        from .pdf_utils import extract_ncs_job_spec
    except Exception as e:
        logger.warning(f"NCS job spec extraction unavailable: {e}")
        extract_ncs_job_spec = None

    jd_text = safe_read_text(ws.profile_dir / "jd.md")
    job_spec_sources: list[dict[str, Any]] = []
    if extract_ncs_job_spec and jd_text.strip():
        parsed = extract_ncs_job_spec(jd_text)
        if any(parsed.values()):
            job_spec_sources.append(
                {
                    "title": "profile/jd.md",
                    "source_type": "profile_jd",
                    **parsed,
                }
            )
    if extract_ncs_job_spec:
        for source in knowledge_sources:
            source_blob = "\n".join(
                [
                    source.title,
                    source.cleaned_text or source.raw_text,
                ]
            )
            if not any(
                marker in source_blob
                for marker in [
                    "직무기술서",
                    "능력단위",
                    "능력단위요소",
                    "직업기초능력",
                    "직업공통능력",
                ]
            ):
                continue
            parsed = extract_ncs_job_spec(source.cleaned_text or source.raw_text)
            if any(parsed.values()):
                job_spec_sources.append(
                    {
                        "title": source.title,
                        "source_type": source.source_type.value,
                        **parsed,
                    }
                )

    ability_units = _dedupe_preserve_order(
        [
            item
            for source in job_spec_sources
            for item in source.get("ability_units", [])
        ]
    )[:12]
    ability_unit_elements = _dedupe_preserve_order(
        [
            item
            for source in job_spec_sources
            for item in source.get("ability_unit_elements", [])
        ]
    )[:20]
    job_spec_competencies = _dedupe_preserve_order(
        [
            item
            for source in job_spec_sources
            for item in source.get("ncs_competencies", [])
        ]
    )[:12]

    competency_rows: list[dict[str, Any]] = []
    public_priority_set = set(NCS_PUBLIC_COMPANY_PRIORITIES)
    question_type_lookup = {
        item.get("question_id") or item.get("id") or f"q{idx + 1}": (
            item.get("question_type")
            or item.get("detected_type")
            or item.get("type")
            or ""
        )
        for idx, item in enumerate(question_map)
    }

    for competency, config in NCS_COMMON_COMPETENCY_SIGNALS.items():
        score = 0
        matched_keywords: list[str] = []
        matched_experience_ids: list[str] = []
        reasons: list[str] = []
        keywords = [kw.lower() for kw in config["keywords"]]

        if (
            project.company_type in {"공공", "공기업"}
            and competency in public_priority_set
        ):
            score += 2
            reasons.append("공공·공기업 지원에서 자주 요구되는 기본 역량")

        for keyword in jd_keywords:
            lower_keyword = keyword.lower()
            if any(
                signal in lower_keyword or lower_keyword in signal
                for signal in keywords
            ):
                score += 2
                matched_keywords.append(keyword)

        for job_competency in job_spec_competencies:
            lower_competency = job_competency.lower()
            if competency == job_competency or any(
                signal in lower_competency or lower_competency in signal
                for signal in keywords
            ):
                score += 3
                matched_keywords.append(job_competency)
                reasons.append("직무기술서/NCS 명시 역량과 직접 연결")

        for unit in ability_units + ability_unit_elements:
            lower_unit = unit.lower()
            if any(signal in lower_unit or lower_unit in signal for signal in keywords):
                score += 1
                matched_keywords.append(unit)
                reasons.append("직무기술서 능력단위/요소와 정합")

        for item in question_map:
            q_type = (
                item.get("question_type")
                or item.get("detected_type")
                or item.get("type")
                or ""
            )
            if q_type in config["question_types"]:
                score += 1
                reasons.append(f"{q_type} 문항 의도와 직접 연결")
                focus = item.get("recommended_focus")
                if focus and any(signal in str(focus).lower() for signal in keywords):
                    score += 1

        for exp in experiences:
            blob = " ".join(
                [
                    exp.title,
                    exp.organization,
                    exp.situation,
                    exp.task,
                    exp.action,
                    exp.result,
                    exp.personal_contribution,
                    exp.metrics,
                    " ".join(exp.tags),
                ]
            ).lower()
            if any(signal in blob for signal in keywords):
                score += 2
                matched_experience_ids.append(exp.id)
                for signal in keywords:
                    if signal in blob:
                        matched_keywords.append(signal)

        if company_analysis:
            analysis_blob = " ".join(
                company_analysis.core_values
                + company_analysis.culture_keywords
                + company_analysis.preferred_evidence_types
            ).lower()
            if any(signal in analysis_blob for signal in keywords):
                score += 1
                reasons.append("회사/직무 분석 신호와 정합")

        matched_keywords = _dedupe_preserve_order(matched_keywords)[:5]
        matched_experience_ids = _dedupe_preserve_order(matched_experience_ids)[:4]
        reasons = _dedupe_preserve_order(reasons)[:3]

        if score > 0:
            competency_rows.append(
                {
                    "name": competency,
                    "score": score,
                    "matched_keywords": matched_keywords,
                    "matched_experience_ids": matched_experience_ids,
                    "reasons": reasons,
                }
            )

    competency_rows.sort(
        key=lambda item: (
            -item["score"],
            -len(item["matched_experience_ids"]),
            item["name"],
        )
    )
    priority_order = [item["name"] for item in competency_rows[:5]]

    ability_unit_map: list[dict[str, Any]] = []
    for unit in ability_units:
        lower_unit = unit.lower()
        matched_competencies = [
            row["name"]
            for row in competency_rows
            if any(
                signal in lower_unit or lower_unit in signal
                for signal in NCS_COMMON_COMPETENCY_SIGNALS[row["name"]]["keywords"]
            )
            or row["name"].lower() in lower_unit
        ]
        if matched_competencies:
            ability_unit_map.append(
                {
                    "unit": unit,
                    "matched_competencies": matched_competencies[:3],
                }
            )

    question_alignment: list[dict[str, Any]] = []
    for question_id, q_type in question_type_lookup.items():
        matched = [
            item["name"]
            for item in competency_rows
            if q_type in NCS_COMMON_COMPETENCY_SIGNALS[item["name"]]["question_types"]
        ][:3]
        if matched:
            related_units = [
                item["unit"]
                for item in ability_unit_map
                if any(name in item["matched_competencies"] for name in matched)
            ][:3]
            question_alignment.append(
                {
                    "question_id": question_id,
                    "question_type": q_type,
                    "recommended_competencies": matched,
                    "recommended_ability_units": related_units,
                }
            )

    coaching_focus = [
        f"{name}을(를) 증명할 수 있는 경험·행동·결과를 한 문항에 하나씩 고정"
        for name in priority_order[:3]
    ]
    interview_watchouts = [
        f"{name} 관련 답변은 수치·판단기준·개인기여를 30초 안에 다시 설명할 수 있어야 함"
        for name in priority_order[:3]
    ]

    ncs_profile = {
        "framework_name": "NCS 직업공통능력",
        "reference_date": "2026-03-30",
        "reference_source": "https://www.ncs.go.kr/web/job/contents/1.%20%EC%A7%81%EC%97%85%EA%B3%B5%ED%86%B5%EB%8A%A5%EB%A0%A5_%EC%9D%98%EC%82%AC%EC%86%8C%ED%86%B5%EB%8A%A5%EB%A0%A5.pdf",
        "priority_competencies": priority_order,
        "job_spec_source_titles": [item["title"] for item in job_spec_sources[:5]],
        "ability_units": ability_units,
        "ability_unit_elements": ability_unit_elements,
        "job_spec_competencies": job_spec_competencies,
        "ability_unit_map": ability_unit_map[:8],
        "competency_evidence_map": competency_rows[:7],
        "question_alignment": question_alignment,
        "coaching_focus": coaching_focus,
        "interview_watchouts": interview_watchouts,
    }
    write_json(
        ws.analysis_dir / "ncs_job_spec.json",
        {
            "reference_date": "2026-03-30",
            "job_spec_source_titles": [item["title"] for item in job_spec_sources[:10]],
            "ability_units": ability_units,
            "ability_unit_elements": ability_unit_elements,
            "job_spec_competencies": job_spec_competencies,
            "ability_unit_map": ability_unit_map[:12],
        },
    )
    write_json(ws.analysis_dir / "ncs_profile.json", ncs_profile)
    return ncs_profile


def _expected_ncs_competencies(
    question_id: str,
    question_type: QuestionType,
    ncs_profile: dict[str, Any] | None,
) -> list[str]:
    if not ncs_profile:
        return []

    for item in ncs_profile.get("question_alignment", []) or []:
        if item.get("question_id") == question_id:
            return item.get("recommended_competencies", [])[:3]

    q_type = (
        question_type.value if hasattr(question_type, "value") else str(question_type)
    )
    return [
        name
        for name, config in NCS_COMMON_COMPETENCY_SIGNALS.items()
        if q_type in config["question_types"]
    ][:3]


def evaluate_ncs_alignment(
    answer: str,
    question_id: str,
    question_type: QuestionType,
    ncs_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    expected = _expected_ncs_competencies(question_id, question_type, ncs_profile)
    question_alignment = next(
        (
            item
            for item in (ncs_profile or {}).get("question_alignment", []) or []
            if item.get("question_id") == question_id
        ),
        {},
    )
    expected_units = question_alignment.get("recommended_ability_units", [])[:3]
    if not expected:
        return {
            "score": 1.0,
            "expected_competencies": [],
            "matched_competencies": [],
            "missing_competencies": [],
            "expected_ability_units": expected_units,
            "matched_ability_units": [],
            "missing_ability_units": expected_units,
            "suggestions": [],
        }

    answer_blob = answer.lower()
    answer_compact = re.sub(r"\s+", "", answer_blob)
    matched: list[str] = []
    for competency in expected:
        keywords = [
            kw.lower() for kw in NCS_COMMON_COMPETENCY_SIGNALS[competency]["keywords"]
        ]
        if any(keyword in answer_blob for keyword in keywords):
            matched.append(competency)

    matched_units: list[str] = []
    for unit in expected_units:
        unit_tokens = [
            token
            for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", unit.lower())
            if len(token) >= 2
        ]
        unit_compact = re.sub(r"\s+", "", unit.lower())
        if unit_compact in answer_compact or any(
            token in answer_blob for token in unit_tokens
        ):
            matched_units.append(unit)

    component_scores = [len(matched) / max(len(expected), 1)]
    if expected_units:
        component_scores.append(len(matched_units) / max(len(expected_units), 1))
    score = round(sum(component_scores) / len(component_scores), 2)
    missing = [item for item in expected if item not in matched]
    missing_units = [item for item in expected_units if item not in matched_units]
    suggestions = [
        f"{item}을(를) 보여주는 행동/근거 문장을 한 줄 더 보강하세요."
        for item in missing[:2]
    ] + [
        f"답변에서 '{item}' 능력단위가 드러나도록 업무행동 또는 처리단계를 더 구체화하세요."
        for item in missing_units[:2]
    ]
    return {
        "score": score,
        "expected_competencies": expected,
        "matched_competencies": matched,
        "missing_competencies": missing,
        "expected_ability_units": expected_units,
        "matched_ability_units": matched_units,
        "missing_ability_units": missing_units,
        "suggestions": suggestions,
    }


def _tokenize_research_terms(text: str) -> list[str]:
    stopwords = {
        "그리고",
        "또한",
        "대한",
        "관련",
        "직무",
        "회사",
        "지원",
        "경험",
        "역량",
        "능력",
        "자기소개서",
        "면접",
        "채용",
        "공고",
        "수행",
        "요구",
        "우대",
        "기반",
        "활용",
        "하는",
        "합니다",
        "입니다",
    }
    tokens = re.findall(r"[A-Za-z0-9가-힣+#]{2,}", text.lower())
    filtered = [
        token
        for token in tokens
        if token not in stopwords and not token.isdigit() and len(token) >= 2
    ]
    return _dedupe_preserve_order(filtered)


def _extract_jd_keywords_for_research(ws: Workspace) -> list[str]:
    jd_text = safe_read_text(ws.profile_dir / "jd.md")
    if not jd_text:
        return []
    try:
        from .pdf_utils import extract_jd_keywords

        return extract_jd_keywords(jd_text)
    except Exception as e:
        logger.warning(f"JD keyword extraction failed during research build: {e}")
        return _tokenize_research_terms(jd_text)[:8]


def build_research_brief(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    project = load_project(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    knowledge_sources = load_knowledge_sources(ws)
    live_source_updates = build_live_source_update_summary(ws)
    jd_keywords = _extract_jd_keywords_for_research(ws)
    key_questions: list[str] = []

    if project.company_name or project.job_title:
        key_questions.append(
            f"{project.company_name or '지원 회사'}의 {project.job_title or '지원 직무'}에서 실제로 요구하는 핵심 과업은 무엇인가?"
        )
    if jd_keywords:
        key_questions.append(
            f"JD 키워드({', '.join(jd_keywords[:4])})가 실제로 의미하는 역량과 증명 방식은 무엇인가?"
        )
    if question_map:
        key_questions.append(
            "현재 자소서 문항별로 어떤 경험과 근거를 우선 연결해야 하는가?"
        )
    key_questions.extend(
        [
            "왜 이 회사/직무인지에 대한 논리를 과장 없이 어떻게 방어할 것인가?",
            "면접에서 꼬리질문이 들어오기 쉬운 취약 지점은 무엇인가?",
        ]
    )

    brief = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "objective": "회사/직무 조사 결과를 자소서(TYPE_A/TYPE_B/TYPE_E)와 면접 방어에 바로 연결 가능한 형태로 정리한다.",
        "scope": {
            "local_documents": [
                "profile/facts.md",
                "profile/experience_bank.md",
                "profile/jd.md",
            ],
            "knowledge_source_count": len(knowledge_sources),
            "public_web_ingested": any(
                source.source_type.value == "user_url_public"
                for source in knowledge_sources
            ),
            "live_source_tracked_count": live_source_updates["tracked_url_count"],
            "recent_live_change_count": live_source_updates["changed_url_count"],
            "priority_live_update_count": live_source_updates["priority_update_count"],
        },
        "assumptions": [
            "외부 공개 웹 자료는 사용자가 수집하거나 crawl-web으로 ingest한 범위만 사용한다.",
            "미확인 회사 사실은 확정 정보가 아니라 검증 필요 신호로 남긴다.",
        ],
        "risks": [
            "단일 출처에만 의존한 신호는 자소서/면접에서 방어력이 낮을 수 있다.",
            "JD 표현을 그대로 반복하면 회사 적합성 해석이 얕아질 수 있다.",
            "사용자 경험과 연결되지 않는 조사 포인트는 실전 활용도가 떨어진다.",
        ],
        "completion_criteria": [
            "핵심 질문마다 최소 1개 이상의 근거 소스가 연결된다.",
            "중요 주장에는 2개 이상 소스 교차검증 여부가 표시된다.",
            "TYPE_A / TYPE_B / TYPE_E 및 면접 대비 포인트로 연결된다.",
            "미확인 정보는 [NEEDS_VERIFICATION]로 분리된다.",
        ],
        "key_questions": _dedupe_preserve_order(key_questions)[:5],
        "freshness_target": f"{datetime.now().date().isoformat()} 기준 최신 제공 자료",
        "live_source_updates": live_source_updates,
        "priority_live_updates": live_source_updates["priority_live_updates"],
    }
    write_json(ws.analysis_dir / "research_brief.json", brief)
    return brief


def _grade_source_reliability(source: KnowledgeSource) -> tuple[str, str]:
    if source.source_type == SourceType.USER_URL_PUBLIC:
        parsed = urlparse(source.url or "")
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        if any(
            host.endswith(suffix)
            for suffix in [".go.kr", ".gov", ".ac.kr", ".edu", ".or.kr"]
        ):
            return "B", "공공기관/교육기관/비영리 공식 도메인입니다."
        if any(
            token in host
            for token in ["reddit", "blind", "tistory", "blog", "naver", "brunch"]
        ):
            return "E", "포럼·블로그 계열 도메인이라 참고용으로만 쓰는 편이 안전합니다."
        if any(
            token in path
            for token in [
                "/careers",
                "/jobs",
                "/recruit",
                "/about",
                "/company",
                "/news",
            ]
        ):
            return (
                "B",
                "회사 공식 채용/소개/보도 자료 성격의 페이지일 가능성이 높습니다.",
            )
        return (
            "C",
            "공개 웹 자료이지만 공식성 여부가 명확하지 않아 보조 근거로 보는 편이 안전합니다.",
        )
    if source.source_type in {
        SourceType.LOCAL_MARKDOWN,
        SourceType.LOCAL_TEXT,
        SourceType.LOCAL_CSV_ROW,
    }:
        return (
            "C",
            "사용자 제공 로컬 자료로 실무 활용도는 높지만 외부 교차검증이 추가되면 더 안전합니다.",
        )
    if source.source_type == SourceType.MANUAL_NOTE:
        return "D", "수기 메모 성격이라 단독 확정 근거로 쓰기 어렵습니다."
    return "D", "출처 성격이 명확하지 않아 보조 참고 수준으로 보는 편이 안전합니다."


def _detect_source_conflicts(sources: list[KnowledgeSource]) -> list[dict[str, Any]]:
    conflict_pairs = [
        ("정규직", "계약직", "고용 형태"),
        ("신입", "경력", "채용 대상"),
        ("원격", "상주", "근무 방식"),
        ("재택", "출근", "근무 방식"),
    ]
    conflicts: list[dict[str, Any]] = []
    for idx, left in enumerate(sources):
        left_text = f"{left.title} {left.cleaned_text}"
        for right in sources[idx + 1 :]:
            right_text = f"{right.title} {right.cleaned_text}"
            for a_token, b_token, topic in conflict_pairs:
                left_has_a = a_token in left_text
                left_has_b = b_token in left_text
                right_has_a = a_token in right_text
                right_has_b = b_token in right_text
                if (left_has_a and right_has_b) or (left_has_b and right_has_a):
                    conflicts.append(
                        {
                            "topic": topic,
                            "tokens": [a_token, b_token],
                            "sources": [left.title, right.title],
                        }
                    )
                    break
    return conflicts


def _run_semantic_source_review(
    ws: Workspace,
    brief: dict[str, Any],
    assessments: list[dict[str, Any]],
    area_results: list[dict[str, Any]],
    *,
    tool: str = "codex",
) -> dict[str, Any]:
    prompt_lines = [
        "# SOURCE CROSS-CHECK TASK",
        "아래 출처 평가를 바탕으로 자기소개서/면접 준비용 의미적 교차검증 결과를 JSON 객체 하나로 요약하라.",
        "반드시 JSON 객체만 출력한다.",
        '형식: {"summary":"...", "agreements":["..."], "conflicts":["..."], "essay_implications":["..."]}',
        "",
        "# RESEARCH OBJECTIVE",
        brief.get("objective", ""),
        "",
        "# KEY QUESTIONS",
        json.dumps(brief.get("key_questions", []), ensure_ascii=False, indent=2),
        "",
        "# SOURCE ASSESSMENTS",
        json.dumps(assessments, ensure_ascii=False, indent=2),
        "",
        "# CROSS CHECK AREAS",
        json.dumps(area_results, ensure_ascii=False, indent=2),
    ]
    prompt_path = ws.outputs_dir / "latest_source_semantic_review_prompt.md"
    prompt_path.write_text("\n".join(prompt_lines), encoding="utf-8")
    output_path = ws.analysis_dir / "source_semantic_review.json"
    exit_code = run_codex(prompt_path, ws.root, output_path, tool=tool)
    if exit_code != 0:
        return {
            "summary": "자동 의미 검증에 실패해 규칙 기반 교차검증 결과를 우선 사용합니다.",
            "agreements": [],
            "conflicts": [],
            "essay_implications": [],
        }
    try:
        payload = _extract_json_fragment(safe_read_text(output_path))
    except ValueError:
        return {
            "summary": "의미 검증 결과를 파싱하지 못해 규칙 기반 교차검증 결과를 우선 사용합니다.",
            "agreements": [],
            "conflicts": [],
            "essay_implications": [],
        }
    if not isinstance(payload, dict):
        return {
            "summary": "의미 검증 형식이 올바르지 않아 규칙 기반 교차검증 결과를 우선 사용합니다.",
            "agreements": [],
            "conflicts": [],
            "essay_implications": [],
        }
    return {
        "summary": str(payload.get("summary", "")).strip(),
        "agreements": [str(item) for item in payload.get("agreements", [])[:5]],
        "conflicts": [str(item) for item in payload.get("conflicts", [])[:5]],
        "essay_implications": [
            str(item) for item in payload.get("essay_implications", [])[:5]
        ],
    }


def build_source_grading(
    ws: Workspace,
    research_brief: dict[str, Any] | None = None,
    *,
    use_semantic_review: bool = False,
    tool: str = "codex",
) -> dict[str, Any]:
    ws.ensure()
    project = load_project(ws)
    sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    brief = research_brief or build_research_brief(ws)
    jd_keywords = _extract_jd_keywords_for_research(ws)
    question_terms = _tokenize_research_terms(
        " ".join(question.question_text for question in project.questions)
    )[:6]
    live_priority_by_url = build_live_priority_by_url(ws)
    company_terms = _tokenize_research_terms(
        f"{project.company_name} {project.job_title} {project.company_type}"
    )[:6]

    key_areas = [
        {
            "area": "company_fit",
            "keywords": _dedupe_preserve_order(
                company_terms + ["조직", "사업", "가치", "문화"]
            ),
        },
        {
            "area": "role_requirements",
            "keywords": _dedupe_preserve_order(jd_keywords[:6] + question_terms[:3]),
        },
        {
            "area": "essay_alignment",
            "keywords": _dedupe_preserve_order(
                question_terms + ["지원동기", "직무역량", "입사후포부"]
            ),
        },
        {
            "area": "interview_risks",
            "keywords": _dedupe_preserve_order(
                question_terms + ["꼬리질문", "방어", "경험", "근거"]
            ),
        },
    ]

    source_tokens: dict[str, list[str]] = {}
    assessments: list[dict[str, Any]] = []
    for source in sources:
        tokens = _tokenize_research_terms(f"{source.title}\n{source.cleaned_text}")[:30]
        source_tokens[source.id] = tokens
        grade, rationale = _grade_source_reliability(source)
        freshness_status = (
            str(live_priority_by_url.get(str(source.url or "")) or "")
            if source.url
            else ""
        )
        supporting_areas = [
            area["area"] for area in key_areas if set(tokens) & set(area["keywords"])
        ]
        assessments.append(
            {
                "source_id": source.id,
                "title": source.title,
                "url": source.url,
                "source_type": source.source_type.value,
                "grade": grade,
                "rationale": rationale,
                "supporting_areas": supporting_areas,
                "keywords": tokens[:12],
                "freshness_status": freshness_status,
                "freshness_priority": 2
                if freshness_status == "changed"
                else 1
                if freshness_status == "new"
                else 0,
            }
        )
    assessments.sort(
        key=lambda item: (
            int(item.get("freshness_priority", 0)),
            len(item.get("supporting_areas", [])),
            str(item.get("title") or ""),
        ),
        reverse=True,
    )

    area_results: list[dict[str, Any]] = []
    for area in key_areas:
        supporting = [
            source.title
            for source in sources
            if set(source_tokens.get(source.id, [])) & set(area["keywords"])
        ]
        status = "missing"
        if len(supporting) >= 2:
            status = "corroborated"
        elif len(supporting) == 1:
            status = "single_source"
        area_results.append(
            {
                "area": area["area"],
                "keywords": area["keywords"][:8],
                "supporting_sources": supporting,
                "support_count": len(supporting),
                "status": status,
            }
        )

    grading = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_objective": brief.get("objective", ""),
        "key_questions": brief.get("key_questions", []),
        "question_map_count": len(question_map),
        "assessments": assessments,
        "cross_check": {
            "key_areas": area_results,
            "corroborated_area_count": sum(
                1 for item in area_results if item["status"] == "corroborated"
            ),
            "single_source_area_count": sum(
                1 for item in area_results if item["status"] == "single_source"
            ),
            "missing_area_count": sum(
                1 for item in area_results if item["status"] == "missing"
            ),
            "conflicts": _detect_source_conflicts(sources),
        },
    }
    if use_semantic_review and assessments:
        grading["semantic_review"] = _run_semantic_source_review(
            ws,
            brief,
            assessments,
            area_results,
            tool=tool,
        )
    write_json(ws.analysis_dir / "source_grading.json", grading)
    return grading


def build_humanization_guard() -> dict[str, Any]:
    return {
        "avoid_openers": [
            "안녕하세요, 저는",
            "어릴 때부터",
            "항상",
            "저의 강점은",
        ],
        "avoid_fillers": [
            "기여하고자 합니다",
            "역량을 발휘하겠습니다",
            "성장할 수 있었습니다",
        ],
        "preferred_moves": [
            "직무 접점 또는 문제 상황으로 시작",
            "행동과 판단 기준을 먼저 제시",
            "마지막 문장은 기여 방식으로 구체화",
        ],
    }


def load_feedback_context(ws: Workspace, artifact_type: str) -> dict[str, Any]:
    try:
        from .feedback_learner import create_feedback_learner

        learner = create_feedback_learner(str(ws.root / "kb" / "feedback"))
        project = load_project(ws)
        context = {
            "artifact_type": artifact_type,
            "company_name": project.company_name,
            "job_title": project.job_title,
            "question_count": len(project.questions),
        }
        recommendations = learner.get_recommendation(context)
        insights = learner.get_insights()
        recent_comments = [
            item.comment
            for item in learner.db.get_feedback_history(limit=10)
            if item.comment
        ][:5]
        return {
            "recommendations": recommendations[:5],
            "insights": insights,
            "recent_comments": recent_comments,
        }
    except Exception as e:
        logger.warning(f"Feedback context load failed: {e}")
        return {
            "recommendations": [],
            "insights": {"total_feedback": 0, "improvement_areas": []},
            "recent_comments": [],
        }


def _extract_json_fragment(text: str) -> Any:
    candidates: list[str] = []
    stripped = text.strip()
    if stripped:
        candidates.append(stripped)
    first_object = text.find("{")
    first_array = text.find("[")
    starts = [idx for idx in [first_object, first_array] if idx != -1]
    if starts:
        start = min(starts)
        candidates.append(text[start:].strip())
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("JSON payload not found")


def classify_project_questions_with_llm_fallback(
    ws: Workspace,
    project: ApplicationProject,
    *,
    tool: str = "codex",
    confidence_threshold: float = 0.34,
    enabled: bool = True,
) -> ApplicationProject:
    if not enabled:
        for question in project.questions:
            question.detected_type = classify_question_regex_only(
                question.question_text
            )
        return project

    uncertain_questions: list[QuestionType | Any] = []
    for question in project.questions:
        detected_type, confidence = classify_question_with_confidence(
            question.question_text
        )
        question.detected_type = detected_type
        if (
            detected_type == QuestionType.TYPE_UNKNOWN
            or confidence < confidence_threshold
        ):
            uncertain_questions.append(question)

    if not uncertain_questions:
        return project

    prompt_lines = [
        "# QUESTION TYPE FALLBACK TASK",
        "아래 자기소개서 문항을 TYPE_A~TYPE_I 중 하나로 재분류하라.",
        "반드시 JSON 배열만 출력한다.",
        '형식: [{"question_id":"q1","question_type":"TYPE_A","reason":"짧은 근거"}]',
        "",
        "# TYPE GUIDE",
        "- TYPE_A: 지원동기/직무 적합성",
        "- TYPE_B: 직무역량/강점",
        "- TYPE_C: 협업/갈등/조정",
        "- TYPE_D: 성장/학습/개선",
        "- TYPE_E: 입사 후 포부/기여",
        "- TYPE_F: 원칙/가치관/신뢰",
        "- TYPE_G: 실패/위기/복기",
        "- TYPE_H: 고객/민원/서비스",
        "- TYPE_I: 우선순위/판단/압박 상황",
        "",
        "# QUESTIONS",
    ]
    for question in uncertain_questions:
        prompt_lines.append(f"- {question.id}: {question.question_text}")

    prompt_path = ws.outputs_dir / "latest_question_type_fallback_prompt.md"
    prompt_path.write_text("\n".join(prompt_lines), encoding="utf-8")
    output_path = ws.analysis_dir / "question_type_fallback.json"
    try:
        exit_code = run_codex(prompt_path, ws.root, output_path, tool=tool)
    except Exception as e:
        logger.warning(f"Question type fallback failed, using regex-only result: {e}")
        return project
    if exit_code != 0:
        return project

    try:
        payload = _extract_json_fragment(safe_read_text(output_path))
    except ValueError:
        return project
    if not isinstance(payload, list):
        return project

    by_id = {question.id: question for question in project.questions}
    for item in payload:
        if not isinstance(item, dict):
            continue
        question = by_id.get(str(item.get("question_id", "")))
        if not question:
            continue
        raw_type = str(item.get("question_type", "")).strip()
        try:
            question.detected_type = QuestionType(raw_type)
        except ValueError:
            continue
    return project


def run_gap_analysis(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    project = classify_project_questions_with_llm_fallback(ws, project, enabled=True)
    save_project(ws, project)
    experiences = load_experiences(ws)
    report = analyze_gaps(project, experiences)
    path = ws.analysis_dir / "gap_report.json"
    write_json(path, report)
    return {"report": report, "path": str(path)}


def run_coach(ws: Workspace) -> dict[str, Any]:
    with StepProgress("Coach 파이프라인") as progress:
        ws.ensure()
        initialize_state(ws)
        progress.step("워크스페이스 초기화", status="success")

        project = load_project(ws)
        project = classify_project_questions_with_llm_fallback(
            ws, project, enabled=True
        )
        save_project(ws, project)
        experiences = load_experiences(ws)
        candidate_profile = build_candidate_profile(ws, project, experiences)
        company_profile = build_company_profile(ws, project, candidate_profile)
        interview_support_pack = build_interview_support_pack(ws, candidate_profile)
        progress.step("프로젝트/경험 로드", status="success")

        gap_report = analyze_gaps(project, experiences)
        feedback_learning = build_feedback_learning_context(
            ws, "coach", project=project
        )
        artifact = build_coach_artifact(
            project,
            experiences,
            gap_report,
            outcome_summary=feedback_learning.get("outcome_summary"),
            strategy_outcome_summary=feedback_learning.get("strategy_outcome_summary"),
            current_pattern=feedback_learning.get("current_pattern"),
            feedback_adaptation_plan=feedback_learning.get("adaptation_plan"),
            candidate_profile=candidate_profile,
            company_profile=company_profile,
            interview_support_pack=interview_support_pack,
        )
        progress.step("갭 분석 및 코칭 아티팩트 생성", status="success")

        validation_dict = validate_coach_contract(artifact["rendered"])
        validation = ValidationResult(
            passed=validation_dict["passed"], missing=validation_dict["missing"]
        )
        progress.step(
            f"검증 {'통과' if validation.passed else '실패'}",
            status="success" if validation.passed else "failed",
        )

    write_json(ws.analysis_dir / "question_map.json", artifact["allocations"])
    write_json(ws.analysis_dir / "gap_report.json", gap_report)
    top001_coach_analysis: dict[str, Any] = {}
    try:
        from .top001.integrator import Top001CoachEngine

        top001_coach_analysis = Top001CoachEngine().analyze_experiences(
            experiences,
            project.questions,
            artifact.get("allocations", []),
        )
    except Exception as e:
        logger.warning(f"Top001 coach analysis failed: {e}")
    if top001_coach_analysis:
        write_json(
            ws.analysis_dir / "top001_coach_analysis.json",
            _normalize_strategy_payload(top001_coach_analysis),
        )
    experience_competition = build_experience_competition_report(
        project,
        experiences,
        artifact.get("allocations", []),
    )
    write_json(ws.analysis_dir / "experience_competition.json", experience_competition)
    if isinstance(gap_report, dict):
        gap_report["experience_competition"] = experience_competition
        write_json(ws.analysis_dir / "gap_report.json", gap_report)
    committee_feedback = build_committee_feedback_context(ws)
    self_intro_pack = build_self_intro_pack(ws, project)
    writer_brief = build_writer_brief(
        ws,
        project=project,
        experiences=experiences,
        allocations=artifact.get("allocations", []),
        feedback_learning=feedback_learning,
        experience_competition=experience_competition,
        top001_coach_analysis=top001_coach_analysis,
        committee_feedback=committee_feedback,
        self_intro_pack=self_intro_pack,
    )
    artifact = build_coach_artifact(
        project,
        experiences,
        gap_report,
        outcome_summary=feedback_learning.get("outcome_summary"),
        strategy_outcome_summary=feedback_learning.get("strategy_outcome_summary"),
        current_pattern=feedback_learning.get("current_pattern"),
        feedback_adaptation_plan=feedback_learning.get("adaptation_plan"),
        question_strategies=writer_brief.get("question_strategies"),
        writer_contract=writer_brief.get("writer_contract"),
        candidate_profile=candidate_profile,
        company_profile=company_profile,
        interview_support_pack=interview_support_pack,
    )
    validation_dict = validate_coach_contract(artifact["rendered"])
    validation = ValidationResult(
        passed=validation_dict["passed"], missing=validation_dict["missing"]
    )
    strategy_path = ws.analysis_dir / "application_strategy.json"
    adaptive_strategy = build_adaptive_strategy_layer(
        project,
        candidate_profile=build_candidate_profile(ws, project, experiences),
    )
    update_application_strategy(
        ws,
        project=project,
        stage="coach",
        experiences=experiences,
        allocations=artifact.get("allocations", []),
        coach_analysis=top001_coach_analysis,
        experience_competition=experience_competition,
        adaptive_strategy=adaptive_strategy,
    )
    coach_prompt_path = build_coach_prompt(ws, artifact, gap_report)
    coach_path = ws.artifacts_dir / "coach.md"
    coach_path.write_text(artifact["rendered"], encoding="utf-8")

    artifact_id = f"coach-{timestamp_slug()}"
    snapshot = GeneratedArtifact(
        id=artifact_id,
        artifact_type=ArtifactType.COACH,
        accepted=validation.passed,
        input_snapshot={
            "project": project.model_dump(),
            "experience_count": len(experiences),
        },
        output_path=str(coach_path.relative_to(ws.root)),
        raw_output_path=str(coach_path.relative_to(ws.root)),
        validation=validation,
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)
    run_dir = ws.runs_dir / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / "coach.json",
        {"artifact": artifact, "validation": validation.model_dump()},
    )

    cp_mgr = CheckpointManager(ws.root)
    cp_mgr.save_checkpoint(
        "coach",
        {
            "question_map_path": str(
                (ws.analysis_dir / "question_map.json").relative_to(ws.root)
            ),
            "gap_report_path": str(
                (ws.analysis_dir / "gap_report.json").relative_to(ws.root)
            ),
            "coach_path": str(coach_path.relative_to(ws.root)),
            "artifact_id": artifact_id,
            "application_strategy_path": str(strategy_path.relative_to(ws.root)),
            "writer_brief_path": str(
                (ws.analysis_dir / "writer_brief.json").relative_to(ws.root)
            ),
        },
        status="success" if validation.passed else "failed",
        error=", ".join(validation.missing[:5]) if validation.missing else None,
    )

    return {
        "artifact": artifact,
        "validation": validation.model_dump(),
        "path": str(coach_path),
        "prompt_path": str(coach_prompt_path),
        "top001_analysis_path": str(ws.analysis_dir / "top001_coach_analysis.json"),
        "application_strategy_path": str(strategy_path),
        "writer_brief_path": str(ws.analysis_dir / "writer_brief.json"),
    }


def run_writer(ws: Workspace, target_path: Path | None = None) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    resolved_target_path = _resolve_writer_target_path(ws, target_path)
    _validate_writer_preconditions(ws, target_path=resolved_target_path)
    prompt_path = build_draft_prompt(ws, resolved_target_path)
    return {
        "prompt_path": str(prompt_path),
        "target_path": str(resolved_target_path),
    }


def run_writer_with_codex(
    ws: Workspace,
    target_path: Path | None = None,
    tool: str = "codex",
    patina: bool = False,
    patina_mode: str = "audit",
    patina_profile: str = "resume",
    patina_max: bool = False,
    patina_max_models: str | None = None,
    patina_max_dispatch: str | None = None,
) -> dict[str, Any]:
    with StepProgress("Writer 파이프라인") as progress:
        ws.ensure()
        initialize_state(ws)
        progress.step("워크스페이스 초기화", status="success")

        resolved_target_path = _resolve_writer_target_path(ws, target_path)
        project, question_map = _validate_writer_preconditions(
            ws,
            target_path=resolved_target_path,
            tool=tool,
        )
        progress.step("선행조건 검사", status="success")

        company_analysis = None
        if project.company_name:
            try:
                company_analysis = analyze_company(
                    company_name=project.company_name,
                    job_title=project.job_title,
                    company_type=project.company_type,
                    success_cases=_get_success_cases_for_analysis(ws),
                )
                logger.info(
                    f"Company analysis completed: {project.company_name} ({company_analysis.company_type})"
                )
            except Exception as e:
                logger.warning(f"Company analysis failed: {e}")
        progress.step("회사 분석", status="success")

        prompt_context = _build_writer_prompt_context(
            ws,
            target_path=resolved_target_path,
            company_analysis=company_analysis,
        )
        prompt_path = prompt_context["prompt_path"]
        run_dir = prompt_context["run_dir"]
        raw_output_path = prompt_context["raw_output_path"]
        llm_run_metas: list[dict[str, Any]] = []
        progress.step("프롬프트 빌드", status="success")

        exit_code = _run_writer_llm(prompt_path, ws, raw_output_path, tool=tool)
        llm_run_metas.append(_read_llm_run_meta(raw_output_path))
        if exit_code != 0:
            progress.step("Codex 실행 실패", status="failed")
        else:
            progress.step("Codex 실행 완료", status="success")

        headings = [
            "## 블록 1: ASSUMPTIONS & MISSING FACTS",
            "## 블록 2: OUTLINE",
            "## 블록 3: DRAFT ANSWERS",
            "## 블록 4: SELF-CHECK",
        ]
        raw_text = safe_read_text(raw_output_path)
        normalized_text = normalize_contract_output(raw_text, headings)
        validation_dict = validate_writer_contract(normalized_text)
        validation_missing = list(validation_dict["missing"])
        validation_missing.extend(validation_dict.get("semantic_missing", []))
        validation = ValidationResult(
            passed=validation_dict["passed"], missing=validation_missing
        )
        char_limit_report = build_writer_char_limit_report(project, normalized_text)
        validation = merge_writer_validation_with_char_report(
            validation, char_limit_report
        )

        accepted_path = ws.artifacts_dir / "writer.md"
        draft_path = ws.artifacts_dir / "writer_draft.md"
        error_output_path = ws.artifacts_dir / "writer_error.md"
        writer_quality_path = ws.artifacts_dir / "writer_quality.json"
        writer_result_quality_path = ws.artifacts_dir / "writer_result_quality.json"
        writer_differentiation_path = ws.artifacts_dir / "writer_differentiation.json"
        writer_defensibility_path = ws.artifacts_dir / "writer_defensibility.json"
        writer_message_discipline_path = (
            ws.artifacts_dir / "writer_message_discipline.json"
        )
        writer_committee_reaction_path = (
            ws.artifacts_dir / "writer_committee_reaction.json"
        )
        writer_change_action_path = ws.artifacts_dir / "writer_change_actions.json"
        rewrite_report_md_path = ws.analysis_dir / "writer_rewrite_quality_report.md"
        rewrite_report_json_path = (
            ws.analysis_dir / "writer_rewrite_quality_report.json"
        )
        rewrite_quality_report: dict[str, Any] | None = None
        rewrite_attempt_count = 0
        char_loop_changed = False
        patina_result: dict[str, Any] | None = None
        patina_max_result: dict[str, Any] | None = None

        experiences = load_experiences(ws)
        writer_brief = read_json_if_exists(ws.analysis_dir / "writer_brief.json")
        fact_warnings = audit_facts(normalized_text, experiences)

        if fact_warnings and exit_code == 0:
            logger.warning(
                f"Fact audit failed. Attempting self-correction for: {fact_warnings}"
            )
            correction_prompt = f"""
            # ERROR FOUND IN PREVIOUS OUTPUT
            The following factual inconsistencies were found based on the source data:
            {chr(10).join(fact_warnings)}

            # TASK
            Rewrite the answers to ensure ALL metrics and facts strictly match the source data.
            Maintain the same format and character limits.

            # PREVIOUS OUTPUT
            {normalized_text}
            """
            run_dir = ws.runs_dir / f"correction_{timestamp_slug()}"
            run_dir.mkdir(parents=True, exist_ok=True)
            corrected_output_path = run_dir / "corrected_writer.md"

            temp_prompt_path = run_dir / "correction_prompt.md"
            temp_prompt_path.write_text(correction_prompt, encoding="utf-8")

            rewrite_attempt_count += 1
            exit_code = _run_writer_llm(
                temp_prompt_path,
                ws,
                corrected_output_path,
                tool=tool,
            )
            llm_run_metas.append(_read_llm_run_meta(corrected_output_path))
            if exit_code == 0:
                normalized_text = safe_read_text(corrected_output_path)
                fact_warnings = audit_facts(normalized_text, experiences)
                logger.info("Self-correction completed.")

        quality_evaluations: list[dict[str, Any]] = []
        result_quality_evaluations: list[dict[str, Any]] = []
        quality_evaluation_error: str | None = None
        result_quality_evaluation_error: str | None = None
        ncs_profile = read_json_if_exists(ws.analysis_dir / "ncs_profile.json")
        narrative_ssot = read_json_if_exists(ws.analysis_dir / "narrative_ssot.json")
        if not ncs_profile:
            ncs_profile = build_ncs_profile(
                ws,
                project=project,
                experiences=experiences,
                question_map=question_map,
                company_analysis=company_analysis,
            )
        if normalized_text:
            try:
                quality_evaluations = build_writer_quality_evaluations(
                    project=project,
                    writer_text=normalized_text,
                    experiences=experiences,
                    question_map=question_map,
                    company_analysis=company_analysis,
                    ncs_profile=ncs_profile,
                    narrative_ssot=narrative_ssot,
                    writer_brief=writer_brief,
                )
                for quality in quality_evaluations:
                    logger.info(
                        f"Answer quality for Q{quality['question_order']}: {quality['overall_score']:.2f}"
                    )
            except Exception as e:
                quality_evaluation_error = str(e)
                logger.warning(f"Answer quality evaluation failed: {e}")
        if normalized_text:
            try:
                result_quality_evaluations = build_writer_result_quality_evaluations(
                    project=project,
                    writer_text=normalized_text,
                    experiences=experiences,
                    question_map=question_map,
                )
            except Exception as e:
                result_quality_evaluation_error = str(e)
                logger.warning(f"Result-focused quality evaluation failed: {e}")

        def _rewrite_with_constraints(
            previous_output: str,
            current_validation: ValidationResult,
            current_quality: list[dict[str, Any]],
            current_result_quality: list[dict[str, Any]],
            current_char_report: dict[str, Any],
            suffix: str,
            focus_mode: str = "full",
        ) -> tuple[
            int,
            str,
            ValidationResult,
            list[dict[str, Any]],
            list[dict[str, Any]],
            dict[str, Any],
        ]:
            nonlocal rewrite_attempt_count
            rewrite_dir = ws.runs_dir / f"{suffix}_{timestamp_slug()}"
            rewrite_dir.mkdir(parents=True, exist_ok=True)
            rewrite_prompt = build_writer_rewrite_prompt(
                previous_output=previous_output,
                validation=current_validation,
                quality_evaluations=current_quality,
                result_quality_evaluations=current_result_quality,
                char_limit_report=current_char_report,
                feedback_learning=build_feedback_learning_context(
                    ws, "writer", project=project
                ),
                candidate_profile=build_candidate_profile(ws, project, experiences),
                writer_brief=writer_brief,
                focus_mode=focus_mode,
            )
            rewrite_prompt_path = rewrite_dir / "rewrite_prompt.md"
            rewrite_prompt_path.write_text(rewrite_prompt, encoding="utf-8")
            rewritten_output_path = rewrite_dir / "rewritten_writer.md"
            rewrite_attempt_count += 1
            rewrite_exit_code = _run_writer_llm(
                rewrite_prompt_path,
                ws,
                rewritten_output_path,
                tool=tool,
            )
            llm_run_metas.append(_read_llm_run_meta(rewritten_output_path))
            if rewrite_exit_code != 0:
                return (
                    rewrite_exit_code,
                    previous_output,
                    current_validation,
                    current_quality,
                    current_result_quality,
                    current_char_report,
                )

            candidate_text = normalize_contract_output(
                safe_read_text(rewritten_output_path),
                headings,
            )
            candidate_validation_dict = validate_writer_contract(candidate_text)
            candidate_missing = list(candidate_validation_dict["missing"])
            candidate_missing.extend(
                candidate_validation_dict.get("semantic_missing", [])
            )
            candidate_validation = ValidationResult(
                passed=candidate_validation_dict["passed"],
                missing=candidate_missing,
            )
            candidate_char_report = build_writer_char_limit_report(
                project, candidate_text
            )
            candidate_validation = merge_writer_validation_with_char_report(
                candidate_validation, candidate_char_report
            )
            candidate_quality = build_writer_quality_evaluations(
                project=project,
                writer_text=candidate_text,
                experiences=experiences,
                question_map=question_map,
                company_analysis=company_analysis,
                ncs_profile=ncs_profile,
                narrative_ssot=narrative_ssot,
                writer_brief=writer_brief,
            )
            candidate_result_quality = build_writer_result_quality_evaluations(
                project=project,
                writer_text=candidate_text,
                experiences=experiences,
                question_map=question_map,
            )
            return (
                rewrite_exit_code,
                candidate_text,
                candidate_validation,
                candidate_quality,
                candidate_result_quality,
                candidate_char_report,
            )

        if exit_code == 0 and needs_writer_rewrite(
            validation,
            quality_evaluations,
            result_quality_evaluations,
        ):
            logger.warning(
                "Writer quality below threshold. Attempting targeted rewrite."
            )
            (
                rewrite_exit_code,
                candidate_text,
                candidate_validation,
                candidate_quality,
                candidate_result_quality,
                candidate_char_report,
            ) = _rewrite_with_constraints(
                normalized_text,
                validation,
                quality_evaluations,
                result_quality_evaluations,
                char_limit_report,
                "rewrite",
                "full",
            )
            if rewrite_exit_code == 0:
                rewrite_quality_report = build_writer_rewrite_quality_report(
                    quality_evaluations,
                    candidate_quality,
                    before_result_quality_evaluations=result_quality_evaluations,
                    after_result_quality_evaluations=candidate_result_quality,
                )
                rewrite_report_md_path.write_text(
                    rewrite_quality_report["markdown"], encoding="utf-8"
                )
                write_json(rewrite_report_json_path, rewrite_quality_report)
                old_avg = (
                    sum(
                        float(item.get("overall_score", 0.0))
                        for item in quality_evaluations
                    )
                    / len(quality_evaluations)
                    if quality_evaluations
                    else 0.0
                )
                new_avg = (
                    sum(
                        float(item.get("overall_score", 0.0))
                        for item in candidate_quality
                    )
                    / len(candidate_quality)
                    if candidate_quality
                    else 0.0
                )
                old_result_avg = _average_result_quality_score(
                    result_quality_evaluations
                )
                new_result_avg = _average_result_quality_score(
                    candidate_result_quality
                )
                if should_accept_writer_rewrite(
                    candidate_validation,
                    quality_evaluations,
                    candidate_quality,
                    result_quality_evaluations,
                    candidate_result_quality,
                ):
                    normalized_text = candidate_text
                    validation = candidate_validation
                    quality_evaluations = candidate_quality
                    result_quality_evaluations = candidate_result_quality
                    char_limit_report = candidate_char_report
                    logger.info(
                        "Writer rewrite accepted: "
                        f"quality {old_avg:.2f} -> {new_avg:.2f}, "
                        f"result_quality {old_result_avg:.2f} -> {new_result_avg:.2f}"
                    )

        if exit_code == 0:
            normalized_text, char_limit_report, char_loop_changed = (
                enforce_writer_char_limits(
                    project,
                    normalized_text,
                    rewrite_func=lambda previous_output, report, attempt: (
                        _rewrite_with_constraints(
                            previous_output,
                            merge_writer_validation_with_char_report(
                                validation, report
                            ),
                            quality_evaluations,
                            result_quality_evaluations,
                            report,
                            f"length_fix_{attempt}",
                            "char_limit",
                        )[1]
                    ),
                    max_attempts=3,
                )
            )
            if char_loop_changed:
                validation_dict = validate_writer_contract(normalized_text)
                validation = ValidationResult(
                    passed=validation_dict["passed"],
                    missing=list(validation_dict["missing"])
                    + list(validation_dict.get("semantic_missing", [])),
                )
                validation = merge_writer_validation_with_char_report(
                    validation, char_limit_report
                )
                if normalized_text:
                    try:
                        quality_evaluations = build_writer_quality_evaluations(
                            project=project,
                            writer_text=normalized_text,
                            experiences=experiences,
                            question_map=question_map,
                            company_analysis=company_analysis,
                            ncs_profile=ncs_profile,
                            narrative_ssot=narrative_ssot,
                            writer_brief=writer_brief,
                        )
                        quality_evaluation_error = None
                    except Exception as e:
                        quality_evaluations = []
                        quality_evaluation_error = str(e)
                        logger.warning(
                            f"Answer quality evaluation failed after char rewrite: {e}"
                        )
                if normalized_text:
                    try:
                        result_quality_evaluations = (
                            build_writer_result_quality_evaluations(
                                project=project,
                                writer_text=normalized_text,
                                experiences=experiences,
                                question_map=question_map,
                            )
                        )
                        result_quality_evaluation_error = None
                    except Exception as e:
                        result_quality_evaluations = []
                        result_quality_evaluation_error = str(e)
                        logger.warning(
                            f"Result-focused quality evaluation failed after char rewrite: {e}"
                        )

        llm_execution = _summarize_llm_run_metas(llm_run_metas)
        approval_passed = validation.passed and not fact_warnings

        readability = calculate_readability_score(normalized_text)
        progress.step(
            "검증/품질 평가", status="success" if approval_passed else "failed"
        )

        if fact_warnings:
            for w in fact_warnings:
                logger.warning(w)

        logger.info(f"Readability Score: {readability['score']}/100")
        for fb in readability["feedback"]:
            if readability["score"] < 100:
                logger.warning(f"Readability feedback: {fb}")

        quality_status = (
            "error"
            if quality_evaluation_error
            else "skipped"
            if not normalized_text.strip()
            else "ok"
        )
        recent_change_action_check = _assess_recent_change_action_coverage(
            normalized_text,
            build_live_source_update_summary(ws).get("priority_live_updates", []),
        )
        result_quality_status = (
            "error"
            if result_quality_evaluation_error
            else "skipped"
            if not normalized_text.strip()
            else "ok"
        )

        has_contract_output = all(heading in normalized_text for heading in headings)
        if approval_passed:
            accepted_path.write_text(normalized_text, encoding="utf-8")
        elif accepted_path.exists():
            accepted_path.unlink()
        if has_contract_output:
            draft_path.write_text(normalized_text, encoding="utf-8")
            if error_output_path.exists():
                error_output_path.unlink()
        else:
            error_output_path.write_text(normalized_text, encoding="utf-8")
        write_json(
            writer_quality_path,
            _build_writer_quality_status(
                quality_evaluations,
                status=quality_status,
                error_reason=quality_evaluation_error,
            ),
        )
        write_json(
            writer_result_quality_path,
            _build_writer_quality_status(
                result_quality_evaluations,
                status=result_quality_status,
                error_reason=result_quality_evaluation_error,
            ),
        )
        write_json(
            writer_defensibility_path,
            _build_writer_quality_status(
                [
                    {
                        "question_id": item.get("question_id"),
                        "question_order": item.get("question_order"),
                        "committee_reaction_score": item.get("committee_reaction_score"),
                        "committee_attack_points": item.get("committee_attack_points", []),
                        "committee_mitigation_priority": item.get("committee_mitigation_priority"),
                        "committee_reaction_summary": item.get("committee_reaction_summary"),
                    }
                    for item in quality_evaluations
                ],
                status=quality_status,
                error_reason=quality_evaluation_error,
            ),
        )
        write_json(
            writer_message_discipline_path,
            _build_writer_quality_status(
                [
                    {
                        "question_id": item.get("question_id"),
                        "question_order": item.get("question_order"),
                        "message_discipline_score": item.get("message_discipline_score"),
                        "message_primary": item.get("message_primary"),
                        "message_competing_points": item.get("message_competing_points", []),
                        "cliche_score": item.get("cliche_score"),
                        "cliche_flags": item.get("cliche_flags", []),
                    }
                    for item in quality_evaluations
                ],
                status=quality_status,
                error_reason=quality_evaluation_error,
            ),
        )
        write_json(
            writer_committee_reaction_path,
            _build_writer_quality_status(
                [
                    {
                        "question_id": item.get("question_id"),
                        "question_order": item.get("question_order"),
                        "committee_reaction_score": item.get("committee_reaction_score"),
                        "committee_attack_points": item.get("committee_attack_points", []),
                        "committee_reaction_summary": item.get("committee_reaction_summary"),
                    }
                    for item in quality_evaluations
                ],
                status=quality_status,
                error_reason=quality_evaluation_error,
            ),
        )
        write_json(writer_change_action_path, recent_change_action_check)
        writer_feedback_learning = build_feedback_learning_context(
            ws, "writer", project=project
        )
        application_strategy = read_json_if_exists(
            ws.analysis_dir / "application_strategy.json"
        )
        writer_differentiation = build_writer_differentiation_report(
            project,
            quality_evaluations,
            research_strategy_translation=read_json_if_exists(
                ws.analysis_dir / "research_strategy_translation.json"
            ),
            application_strategy=application_strategy
            if isinstance(application_strategy, dict)
            else None,
        )
        write_json(writer_differentiation_path, writer_differentiation)
        update_application_strategy(
            ws,
            project=project,
            stage="writer",
            experiences=experiences,
            writer_differentiation=writer_differentiation,
            adaptive_strategy=build_adaptive_strategy_layer(
                project,
                candidate_profile=build_candidate_profile(ws, project, experiences),
            ),
            feedback_adaptation_plan=writer_feedback_learning.get("adaptation_plan"),
            recent_change_action_check=recent_change_action_check,
        )

    snapshot = GeneratedArtifact(
        id=f"writer-{timestamp_slug()}",
        artifact_type=ArtifactType.WRITER,
        accepted=approval_passed,
        input_snapshot={
            "project": load_project(ws).model_dump(),
            "target_path": relative(ws.root, resolved_target_path),
            "tool": tool,
            "selected_tool": llm_execution["selected_tool"] or tool,
            "attempted_tools": llm_execution["attempted_tools"] or [tool],
            "fallback_reason": llm_execution["fallback_reason"],
            "question_map_path": relative(ws.root, ws.analysis_dir / "question_map.json"),
            "fact_warnings": fact_warnings,
            "readability": readability,
            "company_analysis": company_analysis.model_dump()
            if company_analysis
            else None,
            "quality_evaluations": quality_evaluations,
            "result_quality_evaluations": result_quality_evaluations,
            "writer_run_meta": {
                "target_path": relative(ws.root, resolved_target_path),
                "tool": tool,
                "selected_tool": llm_execution["selected_tool"] or tool,
                "attempted_tools": llm_execution["attempted_tools"] or [tool],
                "fallback_reason": llm_execution["fallback_reason"],
                "rewrite_count": rewrite_attempt_count,
                "char_limit_adjusted": bool(char_loop_changed),
                "quality_evaluation_status": quality_status,
                "quality_evaluation_error": quality_evaluation_error,
                "result_quality_evaluation_status": result_quality_status,
                "result_quality_evaluation_error": result_quality_evaluation_error,
                "approved": approval_passed,
                "writer_brief_path": relative(
                    ws.root, ws.analysis_dir / "writer_brief.json"
                ),
            },
            "rewrite_quality_report_path": relative(ws.root, rewrite_report_json_path)
            if rewrite_quality_report
            else None,
            "writer_quality_path": relative(ws.root, writer_quality_path),
            "writer_result_quality_path": relative(ws.root, writer_result_quality_path),
            "writer_differentiation_path": relative(
                ws.root, writer_differentiation_path
            ),
            "writer_defensibility_path": relative(ws.root, writer_defensibility_path),
            "writer_message_discipline_path": relative(
                ws.root, writer_message_discipline_path
            ),
            "writer_committee_reaction_path": relative(
                ws.root, writer_committee_reaction_path
            ),
            "writer_change_action_path": relative(ws.root, writer_change_action_path),
            "recent_change_action_check": recent_change_action_check,
            "patina_max_result_path": relative(
                ws.root, ws.analysis_dir / "patina_max_report.json"
            )
            if patina_max_result
            else None,
        },
        output_path=relative(ws.root, accepted_path),
        raw_output_path=relative(ws.root, raw_output_path),
        validation=validation,
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)
    write_json(
        run_dir / "writer.json",
        {
            "validation": validation.model_dump(),
            "approved": approval_passed,
            "exit_code": exit_code,
            "target_path": relative(ws.root, resolved_target_path),
            "tool": tool,
            "selected_tool": llm_execution["selected_tool"] or tool,
            "attempted_tools": llm_execution["attempted_tools"] or [tool],
            "fallback_reason": llm_execution["fallback_reason"],
            "rewrite_count": rewrite_attempt_count,
            "char_limit_adjusted": bool(char_loop_changed),
            "quality_evaluation_status": quality_status,
            "quality_evaluation_error": quality_evaluation_error,
            "result_quality_evaluation_status": result_quality_status,
            "result_quality_evaluation_error": result_quality_evaluation_error,
            "quality_evaluations": quality_evaluations,
            "artifact_path": relative(ws.root, accepted_path)
            if approval_passed and accepted_path.exists()
            else None,
            "draft_path": relative(ws.root, draft_path) if draft_path.exists() else None,
            "error_output_path": relative(ws.root, error_output_path)
            if error_output_path.exists()
            else None,
            "writer_brief_path": relative(ws.root, ws.analysis_dir / "writer_brief.json"),
            "rewrite_quality_report_path": relative(ws.root, rewrite_report_json_path)
            if rewrite_quality_report
            else None,
            "writer_differentiation_path": relative(
                ws.root, writer_differentiation_path
            ),
            "writer_defensibility_path": relative(ws.root, writer_defensibility_path),
            "writer_message_discipline_path": relative(
                ws.root, writer_message_discipline_path
            ),
            "writer_committee_reaction_path": relative(
                ws.root, writer_committee_reaction_path
            ),
            "patina_max_result_path": relative(
                ws.root, ws.analysis_dir / "patina_max_report.json"
            )
            if patina_max_result
            else None,
        },
    )

    cp_mgr = CheckpointManager(ws.root)
    cp_mgr.save_checkpoint(
        "writer",
        {
            "artifact_path": relative(ws.root, accepted_path),
            "draft_path": relative(ws.root, draft_path) if draft_path.exists() else None,
            "error_output_path": relative(ws.root, error_output_path)
            if error_output_path.exists()
            else None,
            "validation": validation.model_dump(),
            "approved": approval_passed,
            "target_path": relative(ws.root, resolved_target_path),
            "tool": tool,
            "selected_tool": llm_execution["selected_tool"] or tool,
            "attempted_tools": llm_execution["attempted_tools"] or [tool],
            "fallback_reason": llm_execution["fallback_reason"],
            "rewrite_count": rewrite_attempt_count,
            "char_limit_adjusted": bool(char_loop_changed),
            "fact_warnings": fact_warnings,
            "readability": readability,
            "quality_evaluations": quality_evaluations,
            "result_quality_evaluations": result_quality_evaluations,
            "quality_evaluation_status": quality_status,
            "quality_evaluation_error": quality_evaluation_error,
            "result_quality_evaluation_status": result_quality_status,
            "result_quality_evaluation_error": result_quality_evaluation_error,
            "writer_quality_path": relative(ws.root, writer_quality_path),
            "writer_result_quality_path": relative(ws.root, writer_result_quality_path),
            "writer_differentiation_path": relative(
                ws.root, writer_differentiation_path
            ),
            "writer_defensibility_path": relative(ws.root, writer_defensibility_path),
            "writer_message_discipline_path": relative(
                ws.root, writer_message_discipline_path
            ),
            "writer_committee_reaction_path": relative(
                ws.root, writer_committee_reaction_path
            ),
            "writer_brief_path": relative(
                ws.root, ws.analysis_dir / "writer_brief.json"
            ),
            "rewrite_report_md_path": relative(ws.root, rewrite_report_md_path)
            if rewrite_quality_report
            else None,
            "rewrite_report_json_path": relative(ws.root, rewrite_report_json_path)
            if rewrite_quality_report
            else None,
            "patina_max_result_path": relative(
                ws.root, ws.analysis_dir / "patina_max_report.json"
            )
            if patina_max_result
            else None,
        },
        status="success" if approval_passed else "failed",
        error=", ".join((fact_warnings or validation.missing)[:5])
        if fact_warnings or validation.missing
        else None,
    )

    # 피드백 학습 루프: 검증 결과를 자동 피드백으로 기록
    try:
        from .feedback_learner import create_feedback_learner

        learner = create_feedback_learner(str(ws.root / "kb" / "feedback"))
        pattern = _build_feedback_pattern_id("writer", project)
        comment = None
        selection_payload = _build_feedback_selection_payload(
            question_map,
            writer_brief=writer_brief,
        )
        low_quality = [
            item
            for item in quality_evaluations
            if float(item.get("overall_score", 0.0)) < 0.72
        ]
        if low_quality:
            weakest = low_quality[0]
            weaknesses = weakest.get("weaknesses", [])[:2]
            comment = ", ".join(weaknesses) if weaknesses else None
        learner.record_feedback(
            draft_id=f"writer-{timestamp_slug()}",
            pattern_used=pattern,
            accepted=approval_passed,
            comment=comment,
            artifact_type="writer",
            company_name=project.company_name,
            job_title=project.job_title,
            company_type=project.company_type,
            question_types=[
                question.detected_type.value
                for question in project.questions
                if getattr(question, "detected_type", None)
            ],
            stage="writer",
            selected_experience_ids=selection_payload["selected_experience_ids"],
            question_experience_map=selection_payload["question_experience_map"],
            question_strategy_map=selection_payload["question_strategy_map"],
        )
        logger.info(f"Writer 피드백 자동 기록: {pattern}")
    except Exception as e:
        logger.debug(f"피드백 기록 건너뜀: {e}")

    # ── patina AI 패턴 제거 파이프라인 ──────────────────────────────
    if patina_max and approval_passed:
        try:
            from .patina_max_bridge import run_patina_max

            logger.info(
                "patina-max 실행: "
                f"models={patina_max_models or 'config/default'}, "
                f"dispatch={patina_max_dispatch or 'config/default'}"
            )
            progress.step("patina-max 실행", status="running")

            patina_max_result = run_patina_max(
                writer_text=normalized_text,
                workspace_root=ws.root,
                project=project,
                models=patina_max_models,
                dispatch=patina_max_dispatch,
                profile_name=patina_profile,
            )

            if patina_max_result.get("reassembled_text"):
                patina_max_result = enforce_patina_char_limits(
                    project,
                    patina_max_result,
                    rewrite_func=lambda previous_output, report, attempt: (
                        _rewrite_with_constraints(
                            previous_output,
                            merge_writer_validation_with_char_report(
                                ValidationResult(passed=True, missing=[]), report
                            ),
                            build_writer_quality_evaluations(
                                project=project,
                                writer_text=previous_output,
                                experiences=experiences,
                                question_map=question_map,
                                company_analysis=company_analysis,
                                ncs_profile=ncs_profile,
                                narrative_ssot=narrative_ssot,
                                writer_brief=writer_brief,
                            )
                            if previous_output
                            else [],
                            build_writer_result_quality_evaluations(
                                project=project,
                                writer_text=previous_output,
                                experiences=experiences,
                                question_map=question_map,
                            )
                            if previous_output
                            else [],
                            report,
                            f"patina_max_length_fix_{attempt}",
                        )[1]
                    ),
                    max_attempts=2,
                )

            if patina_max_result.get("reassembled_text"):
                patina_max_path = ws.artifacts_dir / "writer_draft_patina_max.md"
                patina_max_path.write_text(
                    patina_max_result["reassembled_text"], encoding="utf-8"
                )
                patina_max_result["result_path"] = str(patina_max_path)
                logger.info(f"patina-max 교정 결과 저장: {patina_max_path}")

            patina_max_report_path = ws.analysis_dir / "patina_max_report.json"
            write_json(patina_max_report_path, patina_max_result)
            progress.step("patina-max 완료", status="success")
        except Exception as e:
            logger.warning(f"patina-max 실행 실패: {e}")
            patina_max_result = {
                "mode": "max",
                "models": [],
                "dispatch": "direct",
                "selected_model": None,
                "selected_text": "",
                "outputs_by_model": {},
                "warnings": [f"patina-max 실행 실패: {e}"],
                "reassembled_text": normalized_text,
                "selection_report": {"reason": "exception"},
                "run_meta": {
                    "requested_dispatch": patina_max_dispatch,
                    "effective_dispatch": "direct",
                    "selected_model": None,
                },
            }
            progress.step("patina-max 실패", status="failed")
    elif patina_max and not approval_passed:
        logger.warning(
            "patina-max 건너뜀: writer 검증 통과하지 못함 (--patina-max는 검증 통과 후에만 실행)"
        )
    elif patina and approval_passed:
        try:
            from .patina_bridge import run_patina

            logger.info(
                f"patina 실행: mode={patina_mode}, profile={patina_profile}, tool={tool}"
            )
            progress.step(f"patina {patina_mode} 실행", status="running")

            patina_result = run_patina(
                writer_text=normalized_text,
                tool=tool,
                mode=patina_mode,
                profile_name=patina_profile,
            )

            if patina_mode in ("rewrite", "ouroboros") and patina_result.get(
                "reassembled_text"
            ):
                patina_result = enforce_patina_char_limits(
                    project,
                    patina_result,
                    rewrite_func=lambda previous_output, report, attempt: (
                        _rewrite_with_constraints(
                            previous_output,
                            merge_writer_validation_with_char_report(
                                ValidationResult(passed=True, missing=[]), report
                            ),
                            build_writer_quality_evaluations(
                                project=project,
                                writer_text=previous_output,
                                experiences=experiences,
                                question_map=question_map,
                                company_analysis=company_analysis,
                                ncs_profile=ncs_profile,
                                narrative_ssot=narrative_ssot,
                                writer_brief=writer_brief,
                            )
                            if previous_output
                            else [],
                            build_writer_result_quality_evaluations(
                                project=project,
                                writer_text=previous_output,
                                experiences=experiences,
                                question_map=question_map,
                            )
                            if previous_output
                            else [],
                            report,
                            f"patina_length_fix_{attempt}",
                        )[1]
                    ),
                    max_attempts=2,
                )

            # rewrite/ouroboros 모드: 교정 결과를 writer_draft.md에 반영
            if patina_mode in ("rewrite", "ouroboros") and patina_result.get(
                "reassembled_text"
            ):
                patina_draft_path = ws.artifacts_dir / "writer_draft_patina.md"
                patina_draft_path.write_text(
                    patina_result["reassembled_text"], encoding="utf-8"
                )
                logger.info(f"patina 교정 결과 저장: {patina_draft_path}")

            # 글자수 변동 경고 로깅
            for w in patina_result.get("warnings", []):
                logger.warning(f"patina: {w}")

            progress.step(f"patina {patina_mode} 완료", status="success")
        except Exception as e:
            logger.warning(f"patina 실행 실패: {e}")
            patina_result = {
                "mode": patina_mode,
                "tool": tool,
                "raw_output": "",
                "answers": {},
                "processed": {},
                "char_deltas": {},
                "warnings": [f"patina 실행 실패: {e}"],
                "reassembled_text": normalized_text,
            }
            progress.step(f"patina {patina_mode} 실패", status="failed")
    elif patina and not approval_passed:
        logger.warning(
            "patina 건너뜀: writer 검증 통과하지 못함 (--patina는 검증 통과 후에만 실행)"
        )

    if patina_max_result:
        patina_max_report_rel = relative(ws.root, ws.analysis_dir / "patina_max_report.json")
        snapshot.input_snapshot["patina_max_result_path"] = patina_max_report_rel
        upsert_artifact(ws, snapshot)
        writer_run_payload = read_json_if_exists(run_dir / "writer.json") or {}
        if isinstance(writer_run_payload, dict):
            writer_run_payload["patina_max_result_path"] = patina_max_report_rel
            writer_run_payload["patina_max_selected_model"] = patina_max_result.get(
                "selected_model"
            )
            write_json(run_dir / "writer.json", writer_run_payload)

    return {
        "prompt_path": str(prompt_path),
        "target_path": str(resolved_target_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "draft_path": str(draft_path),
        "error_output_path": str(error_output_path),
        "validation": validation.model_dump(),
        "approved": approval_passed,
        "exit_code": exit_code,
        "tool": tool,
        "selected_tool": llm_execution["selected_tool"] or tool,
        "attempted_tools": llm_execution["attempted_tools"] or [tool],
        "fallback_reason": llm_execution["fallback_reason"],
        "writer_brief_path": str(ws.analysis_dir / "writer_brief.json"),
        "company_analysis": company_analysis.model_dump() if company_analysis else None,
        "quality_evaluations": quality_evaluations,
        "result_quality_evaluations": result_quality_evaluations,
        "writer_quality_path": str(writer_quality_path),
        "writer_result_quality_path": str(writer_result_quality_path),
        "writer_differentiation_path": str(writer_differentiation_path),
        "writer_defensibility_path": str(writer_defensibility_path),
        "writer_message_discipline_path": str(writer_message_discipline_path),
        "writer_committee_reaction_path": str(writer_committee_reaction_path),
        "writer_change_action_path": str(writer_change_action_path),
        "recent_change_action_check": recent_change_action_check,
        "rewrite_quality_report_path": str(rewrite_report_json_path)
        if rewrite_quality_report
        else None,
        "patina_result": patina_result,
        "patina_max_result": patina_max_result,
        "patina_max_result_path": str(ws.analysis_dir / "patina_max_report.json")
        if patina_max_result
        else None,
        "application_strategy_path": str(ws.analysis_dir / "application_strategy.json"),
    }


def run_deep_interview(ws: Workspace) -> dict[str, Any]:
    """재귀적 체이닝을 통해 심층 면접 꼬리 질문을 생성합니다."""
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    experiences = load_experiences(ws)
    writer_text = safe_read_text(ws.artifacts_dir / "writer.md")

    # 상위 질문 추출
    primary_questions = [q.question_text for q in project.questions]
    prepared_answers = []
    if writer_text:
        answer_map = extract_question_answer_map(writer_text, project.questions)
        prepared_answers = [
            answer_map.get(question.id, "") for question in project.questions
        ]

    from .interview_engine import run_recursive_interview_chain

    deep_pack = run_recursive_interview_chain(
        ws.root,
        project,
        experiences,
        primary_questions,
        prepared_answers=prepared_answers,
    )

    # 아티팩트 저장
    out_path = ws.artifacts_dir / "deep_interview.md"
    content = "# Deep Interview Defense Pack\n\n"
    content += "> 이 문서는 AI 시뮬레이션을 통해 답변의 허점을 파고드는 꼬리 질문을 생성한 결과입니다.\n\n"
    for item in deep_pack:
        content += f"### 메인 질문: {item['primary_question']}\n"
        content += f"- **시뮬레이션 답변**: {item['simulated_answer']}\n"
        content += f"- **대표 위원**: {item.get('interviewer_persona', '면접위원')}\n"
        content += f"- **🔥 날카로운 꼬리 질문**: {item['follow_up_question']}\n"
        committee_rounds = item.get("committee_rounds", [])
        if committee_rounds:
            content += "- **위원회 라운드**:\n"
            for round_item in committee_rounds:
                focus = ", ".join(round_item.get("focus", [])[:2])
                content += (
                    f"  - {round_item.get('persona', '면접위원')} / {round_item.get('stance', '검증')}: "
                    f"{round_item.get('question', '')}"
                )
                if focus:
                    content += f" ({focus})"
                content += "\n"
        content += "\n"

    out_path.write_text(content, encoding="utf-8")
    logger.info(f"Deep interview pack written to {out_path}")

    return {"path": str(out_path), "count": len(deep_pack)}


def run_self_intro(ws: Workspace) -> dict[str, Any]:
    """30초/60초 자기소개 아티팩트를 생성합니다."""
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)

    company_analysis = None
    if project.company_name:
        try:
            company_analysis = analyze_company(
                company_name=project.company_name,
                job_title=project.job_title,
                company_type=project.company_type,
                success_cases=_get_success_cases_for_analysis(ws),
            )
        except Exception as e:
            logger.warning(f"Company analysis failed during self intro build: {e}")

    intro_pack = build_self_intro_pack(ws, project, company_analysis=company_analysis)
    committee_feedback = build_committee_feedback_context(ws)

    out_path = ws.artifacts_dir / "self_intro.md"
    content = "# Self Introduction Pack\n\n"
    content += f"- 회사: {project.company_name or '미지정'}\n"
    content += f"- 직무: {project.job_title or '미지정'}\n\n"
    content += "## 30초 자기소개 오프닝\n"
    content += f"{intro_pack.get('opening_hook', '')}\n\n"
    content += "## 30초 답변 프레임\n"
    for item in intro_pack.get("thirty_second_frame", []):
        content += f"- {item}\n"
    content += "\n## 60초 답변 프레임\n"
    for item in intro_pack.get("sixty_second_frame", []):
        content += f"- {item}\n"
    content += "\n## 강조 키워드\n"
    for item in intro_pack.get("focus_keywords", []):
        content += f"- {item}\n"
    content += "\n## 피해야 할 표현\n"
    for item in intro_pack.get("banned_patterns", []):
        content += f"- {item}\n"
    content += "\n## 위원회 경계 포인트\n"
    for item in committee_feedback.get("recurring_risks", []) or intro_pack.get(
        "committee_watchouts", []
    ):
        content += f"- {item}\n"
    if intro_pack.get("top001_hooks"):
        content += "\n## Top001 훅 후보\n"
        for item in intro_pack.get("top001_hooks", []):
            if isinstance(item, dict):
                content += f"- {item.get('content', '')}\n"
    if intro_pack.get("top001_versions"):
        content += "\n## Top001 버전 초안\n"
        for version_name, version_text in intro_pack.get("top001_versions", {}).items():
            content += f"- {version_name}: {version_text}\n"
    if intro_pack.get("top001_expected_follow_ups"):
        content += "\n## 예상 꼬리 질문\n"
        for item in intro_pack.get("top001_expected_follow_ups", []):
            content += f"- {item}\n"

    out_path.write_text(content, encoding="utf-8")

    snapshot = GeneratedArtifact(
        id=f"self-intro-{timestamp_slug()}",
        artifact_type=ArtifactType.SELF_INTRO,
        accepted=True,
        input_snapshot={
            "project": project.model_dump(),
            "committee_feedback": committee_feedback,
            "self_intro_pack": intro_pack,
        },
        output_path=str(out_path.relative_to(ws.root)),
        raw_output_path=str(
            (ws.analysis_dir / "self_intro_pack.json").relative_to(ws.root)
        ),
        validation=ValidationResult(passed=True),
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)

    return {
        "path": str(out_path),
        "analysis_path": str(ws.analysis_dir / "self_intro_pack.json"),
        "application_strategy_path": str(ws.analysis_dir / "application_strategy.json"),
    }


def run_interview(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    prompt_path = build_interview_prompt(ws)
    return {"prompt_path": str(prompt_path)}


def run_interview_with_codex(ws: Workspace, tool: str = "codex") -> dict[str, Any]:
    with StepProgress("Interview 파이프라인") as progress:
        ws.ensure()
        initialize_state(ws)
        progress.step("워크스페이스 초기화", status="success")

        project = load_project(ws)
        company_analysis = None
        if project.company_name:
            try:
                company_analysis = analyze_company(
                    company_name=project.company_name,
                    job_title=project.job_title,
                    company_type=project.company_type,
                    success_cases=_get_success_cases_for_analysis(ws),
                )
                logger.info(
                    f"Company analysis for interview: {project.company_name} (style: {company_analysis.interview_style})"
                )
            except Exception as e:
                logger.warning(f"Company analysis failed: {e}")
        progress.step("회사 분석", status="success")

        prompt_path = build_interview_prompt(ws, company_analysis=company_analysis)
        run_dir = ws.runs_dir / timestamp_slug()
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_output_path = run_dir / "raw_interview.md"
        progress.step("프롬프트 빌드", status="success")

        exit_code = run_codex(prompt_path, ws.root, raw_output_path, tool=tool)
        if exit_code != 0:
            progress.step("Codex 실행 실패", status="failed")
        else:
            progress.step("Codex 실행 완료", status="success")

        headings = [
            "## 블록 1: INTERVIEW ASSUMPTIONS",
            "## 블록 2: INTERVIEW STRATEGY",
            "## 블록 3: EXPECTED QUESTIONS MAP",
            "## 블록 4: ANSWER FRAMES",
        ]
        raw_text = safe_read_text(raw_output_path)
        normalized_text = normalize_contract_output(raw_text, headings)
        validation_dict = validate_interview_contract(normalized_text)
        validation_missing = list(validation_dict["missing"])
        validation_missing.extend(validation_dict.get("semantic_missing", []))
        validation = ValidationResult(
            passed=validation_dict["passed"], missing=validation_missing
        )

        accepted_path = ws.artifacts_dir / "interview.md"
        defense_path = ws.artifacts_dir / "interview_defense.json"
        top001_defense_path = ws.artifacts_dir / "interview_top001.json"
        interview_change_action_path = ws.artifacts_dir / "interview_change_actions.json"

        defense_simulations = []
        top001_interview_simulations: list[dict[str, Any]] = []
        if normalized_text and project.questions:
            try:
                experiences = load_experiences(ws)
                question_map = read_json_if_exists(
                    ws.analysis_dir / "question_map.json"
                )
                interview_feedback = build_feedback_learning_context(
                    ws, "interview", project=project
                )
                ncs_profile = read_json_if_exists(ws.analysis_dir / "ncs_profile.json")
                if not ncs_profile:
                    ncs_profile = build_ncs_profile(
                        ws,
                        project=project,
                        experiences=experiences,
                        question_map=question_map,
                        company_analysis=company_analysis,
                    )
                writer_text = safe_read_text(ws.artifacts_dir / "writer.md")
                defense_simulations = build_interview_defense_simulations(
                    project=project,
                    writer_text=writer_text,
                    experiences=experiences,
                    question_map=question_map,
                    company_analysis=company_analysis,
                    ncs_profile=ncs_profile,
                    narrative_ssot=read_json_if_exists(
                        ws.analysis_dir / "narrative_ssot.json"
                    ),
                    strategy_outcome_summary=interview_feedback.get(
                        "strategy_outcome_summary"
                    ),
                    current_pattern=interview_feedback.get("current_pattern"),
                )
                for simulation in defense_simulations:
                    logger.info(
                        f"Defense simulation for Q{simulation['question_order']}: {len(simulation['follow_up_questions'])} follow-ups generated"
                    )
            except Exception as e:
                logger.warning(f"Defense simulation failed: {e}")
            try:
                from .top001.integrator import Top001InterviewEngine

                question_map = question_map or read_json_if_exists(
                    ws.analysis_dir / "question_map.json"
                )
                answer_map = extract_question_answer_map(
                    safe_read_text(ws.artifacts_dir / "writer.md"),
                    project.questions,
                )
                exp_by_id = {exp.id: exp for exp in experiences}
                default_exp = experiences[0] if experiences else None
                engine = Top001InterviewEngine()
                for question in project.questions:
                    answer = answer_map.get(question.id, "").strip()
                    if not answer:
                        continue
                    mapped_exp = default_exp
                    for item in question_map or []:
                        if (
                            isinstance(item, dict)
                            and str(item.get("question_id", "")).strip() == question.id
                        ):
                            candidate = exp_by_id.get(
                                str(item.get("experience_id", "")).strip()
                            )
                            if candidate:
                                mapped_exp = candidate
                                break
                    simulation = engine.simulate_interview(
                        question.question_text,
                        answer,
                        mapped_exp,
                        company_analysis,
                    )
                    top001_interview_simulations.append(
                        {
                            "question_id": question.id,
                            "question_text": question.question_text,
                            "experience_id": getattr(mapped_exp, "id", ""),
                            **_normalize_strategy_payload(simulation),
                        }
                    )
            except Exception as e:
                logger.warning(f"Top001 interview simulation failed: {e}")
        progress.step("방어 시뮬레이션", status="success")

        if validation.passed:
            accepted_path.write_text(normalized_text, encoding="utf-8")
        write_json(defense_path, defense_simulations)
        write_json(top001_defense_path, top001_interview_simulations)
        recent_change_action_check = _assess_recent_change_action_coverage(
            normalized_text,
            build_live_source_update_summary(ws).get("priority_live_updates", []),
        )
        write_json(interview_change_action_path, recent_change_action_check)
        interview_feedback_learning = build_feedback_learning_context(
            ws, "interview", project=project
        )
        update_application_strategy(
            ws,
            project=project,
            experiences=experiences if "experiences" in locals() else None,
            stage="interview",
            interview_top001=top001_interview_simulations,
            adaptive_strategy=build_adaptive_strategy_layer(
                project,
                candidate_profile=build_candidate_profile(
                    ws,
                    project,
                    experiences if "experiences" in locals() else [],
                ),
            ),
            feedback_adaptation_plan=interview_feedback_learning.get("adaptation_plan"),
            recent_change_action_check=recent_change_action_check,
        )
        progress.step(
            f"검증 {'통과' if validation.passed else '실패'}",
            status="success" if validation.passed else "failed",
        )

    snapshot = GeneratedArtifact(
        id=f"interview-{timestamp_slug()}",
        artifact_type=ArtifactType.INTERVIEW,
        accepted=validation.passed,
        input_snapshot={
            "project": load_project(ws).model_dump(),
            "writer_artifact_exists": (ws.artifacts_dir / "writer.md").exists(),
            "company_analysis": company_analysis.model_dump()
            if company_analysis
            else None,
            "defense_simulations": defense_simulations,
            "top001_interview_simulations": top001_interview_simulations,
            "interview_change_action_path": str(
                interview_change_action_path.relative_to(ws.root)
            ),
            "recent_change_action_check": recent_change_action_check,
        },
        output_path=str(accepted_path.relative_to(ws.root)),
        raw_output_path=str(raw_output_path.relative_to(ws.root)),
        validation=validation,
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)
    write_json(
        run_dir / "interview.json",
        {
            "validation": validation.model_dump(),
            "exit_code": exit_code,
            "defense_simulations": defense_simulations,
            "top001_interview_simulations": top001_interview_simulations,
        },
    )

    cp_mgr = CheckpointManager(ws.root)
    cp_mgr.save_checkpoint(
        "interview",
        {
            "artifact_path": str(accepted_path.relative_to(ws.root)),
            "validation": validation.model_dump(),
            "defense_simulations": defense_simulations,
            "defense_path": str(defense_path.relative_to(ws.root)),
            "top001_defense_path": str(top001_defense_path.relative_to(ws.root)),
        },
        status="success" if validation.passed else "failed",
        error=", ".join(validation.missing[:5]) if validation.missing else None,
    )

    # 피드백 학습 루프: 검증 결과를 자동 피드백으로 기록
    try:
        from .feedback_learner import create_feedback_learner

        learner = create_feedback_learner(str(ws.root / "kb" / "feedback"))
        pattern = _build_feedback_pattern_id("interview", project)
        comment = ", ".join(validation.missing[:3]) if validation.missing else None
        committee_feedback = build_committee_feedback_context(ws)
        selection_payload = _build_feedback_selection_payload(
            read_json_if_exists(ws.analysis_dir / "question_map.json")
        )
        learner.record_feedback(
            draft_id=f"interview-{timestamp_slug()}",
            pattern_used=pattern,
            accepted=validation.passed,
            comment=comment,
            artifact_type="interview",
            company_name=project.company_name,
            job_title=project.job_title,
            company_type=project.company_type,
            question_types=[
                question.detected_type.value
                for question in project.questions
                if getattr(question, "detected_type", None)
            ],
            stage="interview",
            final_outcome=committee_feedback.get("latest_committee_verdict"),
            rejection_reason=", ".join(
                committee_feedback.get("recurring_risks", [])[:2]
            )
            if not validation.passed
            else None,
            selected_experience_ids=selection_payload["selected_experience_ids"],
            question_experience_map=selection_payload["question_experience_map"],
        )
        logger.info(f"Interview 피드백 자동 기록: {pattern}")
    except Exception as e:
        logger.debug(f"피드백 기록 건너뜀: {e}")

    return {
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "validation": validation.model_dump(),
        "exit_code": exit_code,
        "company_analysis": company_analysis.model_dump() if company_analysis else None,
        "defense_simulations": defense_simulations,
        "defense_path": str(defense_path),
        "top001_defense_path": str(top001_defense_path),
        "interview_change_action_path": str(interview_change_action_path),
        "recent_change_action_check": recent_change_action_check,
        "application_strategy_path": str(ws.analysis_dir / "application_strategy.json"),
    }


def run_deep_interview(ws: Workspace) -> dict[str, Any]:
    """재귀적 체이닝을 통해 심층 면접 꼬리 질문을 생성합니다."""
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    experiences = load_experiences(ws)

    # 상위 질문 추출
    primary_questions = [q.question_text for q in project.questions]

    from .interview_engine import run_recursive_interview_chain

    deep_pack = run_recursive_interview_chain(
        ws.root, project, experiences, primary_questions
    )

    # 아티팩트 저장
    out_path = ws.artifacts_dir / "deep_interview.md"
    content = "# Deep Interview Defense Pack\n\n"
    content += "> 이 문서는 AI 시뮬레이션을 통해 답변의 허점을 파고드는 꼬리 질문을 생성한 결과입니다.\n\n"
    for item in deep_pack:
        content += f"### 메인 질문: {item['primary_question']}\n"
        content += f"- **시뮬레이션 답변**: {item['simulated_answer']}\n"
        content += f"- **대표 위원**: {item.get('interviewer_persona', '면접위원')}\n"
        content += f"- **🔥 날카로운 꼬리 질문**: {item['follow_up_question']}\n"
        committee_rounds = item.get("committee_rounds", [])
        if committee_rounds:
            content += "- **위원회 라운드**:\n"
            for round_item in committee_rounds:
                focus = ", ".join(round_item.get("focus", [])[:2])
                content += (
                    f"  - {round_item.get('persona', '면접위원')} / {round_item.get('stance', '검증')}: "
                    f"{round_item.get('question', '')}"
                )
                if focus:
                    content += f" ({focus})"
                content += "\n"
        content += "\n"

    out_path.write_text(content, encoding="utf-8")
    logger.info(f"Deep interview pack written to {out_path}")

    return {"path": str(out_path), "count": len(deep_pack)}


def run_export(ws: Workspace) -> dict[str, Any]:
    with StepProgress("Export 파이프라인") as progress:
        ws.ensure()
        initialize_state(ws)
        project = load_project(ws)
        artifacts = load_artifacts(ws)
        accepted = latest_accepted_artifacts(
            artifacts,
            [
                ArtifactType.COACH,
                ArtifactType.SELF_INTRO,
                ArtifactType.WRITER,
                ArtifactType.INTERVIEW,
            ],
        )
        progress.step("아티팩트 로드", status="success")

        writer_text = safe_read_text(ws.artifacts_dir / "writer.md")
        interview_text = safe_read_text(ws.artifacts_dir / "interview.md")
        coach_text = safe_read_text(ws.artifacts_dir / "coach.md")
        self_intro_text = safe_read_text(ws.artifacts_dir / "self_intro.md")
        narrative_ssot = read_json_if_exists(ws.analysis_dir / "narrative_ssot.json")
        outcome_dashboard = read_json_if_exists(
            ws.analysis_dir / "outcome_dashboard.json"
        )

        export_md = "\n\n".join(
            [
                f"# Export Package\n\n- Company: {project.company_name}\n- Role: {project.job_title}",
                "## Narrative SSOT\n"
                + json.dumps(narrative_ssot or {}, ensure_ascii=False, indent=2),
                "## Outcome Dashboard\n"
                + json.dumps(outcome_dashboard or {}, ensure_ascii=False, indent=2),
                "## Coach Artifact\n" + (coach_text or "_missing_"),
                "## Self Intro Artifact\n" + (self_intro_text or "_missing_"),
                "## Writer Artifact\n" + (writer_text or "_missing_"),
                "## Interview Artifact\n" + (interview_text or "_missing_"),
            ]
        )
        export_path = ws.artifacts_dir / "export.md"
        export_path.write_text(export_md, encoding="utf-8")
        progress.step("Markdown 내보내기", status="success")

        export_json = {
            "project": project.model_dump(),
            "accepted_artifacts": [item.model_dump() for item in accepted],
            "paths": {
                "coach": str((ws.artifacts_dir / "coach.md").relative_to(ws.root)),
                "self_intro": str(
                    (ws.artifacts_dir / "self_intro.md").relative_to(ws.root)
                ),
                "writer": str((ws.artifacts_dir / "writer.md").relative_to(ws.root)),
                "interview": str(
                    (ws.artifacts_dir / "interview.md").relative_to(ws.root)
                ),
                "narrative_ssot": str(
                    (ws.analysis_dir / "narrative_ssot.json").relative_to(ws.root)
                ),
                "outcome_dashboard": str(
                    (ws.analysis_dir / "outcome_dashboard.json").relative_to(ws.root)
                ),
                "export": str(export_path.relative_to(ws.root)),
            },
        }
        export_json_path = ws.artifacts_dir / "export.json"
        write_json(export_json_path, export_json)
        progress.step("JSON 내보내기", status="success")

        docx_path = None
        try:
            from .docx_export import export_artifacts_to_docx, is_docx_available

            if is_docx_available():
                docx_output = ws.artifacts_dir / "export.docx"
                project_info = {
                    "company_name": project.company_name,
                    "job_title": project.job_title,
                }
                docx_path = export_artifacts_to_docx(
                    coach_path=ws.artifacts_dir / "coach.md",
                    writer_path=ws.artifacts_dir / "writer.md",
                    interview_path=ws.artifacts_dir / "interview.md",
                    output_path=docx_output,
                    project_info=project_info,
                )
                progress.step("DOCX 내보내기", status="success")
            else:
                progress.step("DOCX 내보내기 (건너뜀)", status="skipped")
        except Exception as e:
            logger.warning(f"DOCX 내보내기 실패: {e}")
            progress.step("DOCX 내보내기 실패", status="failed")

    snapshot = GeneratedArtifact(
        id=f"export-{timestamp_slug()}",
        artifact_type=ArtifactType.EXPORT,
        accepted=True,
        input_snapshot={"accepted_artifact_count": len(accepted)},
        output_path=str(export_path.relative_to(ws.root)),
        raw_output_path=str(export_json_path.relative_to(ws.root)),
        validation=ValidationResult(passed=True),
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)

    cp_mgr = CheckpointManager(ws.root)
    cp_mgr.save_checkpoint(
        "export",
        {
            "export_md_path": str(export_path.relative_to(ws.root)),
            "export_json_path": str(export_json_path.relative_to(ws.root)),
            "export_docx_path": str(docx_path.relative_to(ws.root))
            if docx_path
            else None,
        },
        status="success",
    )

    return {
        "markdown_path": str(export_path),
        "json_path": str(export_json_path),
        "docx_path": str(docx_path) if docx_path else None,
        "accepted_count": len(accepted),
    }


from .estimator import (
    estimate_cost_and_log,
    count_tokens,
    is_over_limit,
    WARNING_THRESHOLD_TOKENS,
)


def build_coach_prompt(
    ws: Workspace,
    coach_artifact: dict[str, Any] | None = None,
    gap_report: dict[str, Any] | None = None,
) -> Path:
    ws.ensure()
    project = load_project(ws)
    project = classify_project_questions_with_llm_fallback(ws, project, enabled=False)
    save_project(ws, project)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    candidate_profile = build_candidate_profile(ws, project, experiences)
    company_profile = build_company_profile(ws, project, candidate_profile)
    interview_support_pack = build_interview_support_pack(ws, candidate_profile)
    feedback_learning = build_feedback_learning_context(ws, "coach", project=project)
    artifact = coach_artifact or build_coach_artifact(
        project,
        experiences,
        gap_report or analyze_gaps(project, experiences),
        outcome_summary=feedback_learning.get("outcome_summary"),
        strategy_outcome_summary=feedback_learning.get("strategy_outcome_summary"),
        current_pattern=feedback_learning.get("current_pattern"),
        candidate_profile=candidate_profile,
        company_profile=company_profile,
        interview_support_pack=interview_support_pack,
    )
    company_analysis = None
    if project.company_name:
        try:
            company_analysis = analyze_company(
                company_name=project.company_name,
                job_title=project.job_title,
                company_type=project.company_type,
                success_cases=_get_success_cases_for_analysis(ws),
            )
        except Exception as e:
            logger.warning(f"Company analysis failed during coach prompt build: {e}")
    committee_feedback = build_committee_feedback_context(ws)
    self_intro_pack = build_self_intro_pack(
        ws, project, company_analysis=company_analysis
    )
    ncs_profile = build_ncs_profile(
        ws,
        project=project,
        experiences=experiences,
        company_analysis=company_analysis,
    )
    narrative_ssot = build_narrative_ssot(
        ws,
        project,
        experiences,
        question_map=read_json_if_exists(ws.analysis_dir / "question_map.json"),
        company_analysis=company_analysis,
    )
    research_strategy_translation = build_research_strategy_translation(
        ws,
        project,
        company_analysis=company_analysis,
    )
    outcome_dashboard = build_outcome_dashboard(ws, project, "coach")
    kpi_dashboard = build_kpi_dashboard(ws, project, "coach")

    hints = build_knowledge_hints(
        knowledge_sources, project, applicant_profile=candidate_profile
    )
    question_specific_hints = build_question_specific_knowledge_hints(
        knowledge_sources, project
    )

    # [토큰 압축 로직] 한도 초과 시 힌트 개수를 줄여가며 재시도
    while len(hints) >= 0:
        data_block = build_data_block(
            project=project,
            experiences=experiences,
            knowledge_hints=hints,
            extra={
                "gap_report": gap_report or analyze_gaps(project, experiences),
                "coach_allocations": artifact.get("allocations", []),
                "feedback_learning": feedback_learning,
                "committee_feedback": committee_feedback,
                "self_intro_pack": self_intro_pack,
                "ncs_profile": ncs_profile,
                "candidate_profile": candidate_profile,
                "company_profile": company_profile,
                "interview_support_pack": interview_support_pack,
                "narrative_ssot": narrative_ssot,
                "research_strategy_translation": research_strategy_translation,
                "outcome_dashboard": outcome_dashboard,
                "kpi_dashboard": kpi_dashboard,
                "question_specific_hints": question_specific_hints,
                "company_analysis": company_analysis.model_dump()
                if company_analysis
                else None,
            },
        )
        content = PROMPT_COACH.format(data_block=data_block)
        if not is_over_limit(count_tokens(content)) or not hints:
            break
        hints.pop()  # 가장 점수가 낮은 힌트부터 제거
        logger.info(f"Compressing context: Reduced knowledge hints to {len(hints)}")

    out = ws.outputs_dir / "latest_coach_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def ingest_examples(ws: Workspace) -> list[Path]:
    ws.ensure()
    ingested: list[Path] = []
    for src in sorted(
        path
        for path in ws.sources_raw_dir.rglob("*")
        if path.is_file() and not path.name.endswith((".meta.json", ".zone.identifier"))
    ):
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        rel_name = src.relative_to(ws.sources_raw_dir).with_suffix("")
        dst_name = "__".join(rel_name.parts) + ".md"
        dst = ws.sources_normalized_dir / dst_name
        normalized = normalize_example(str(rel_name), text)
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


def build_draft_prompt(ws: Workspace, target_path: Path, company_analysis=None) -> Path:
    ws.ensure()
    project = load_project(ws)
    project = classify_project_questions_with_llm_fallback(ws, project, enabled=False)
    save_project(ws, project)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    candidate_profile = build_candidate_profile(ws, project, experiences)
    company_profile = build_company_profile(ws, project, candidate_profile)

    hints = build_knowledge_hints(
        knowledge_sources, project, applicant_profile=candidate_profile
    )
    question_specific_hints = build_question_specific_knowledge_hints(
        knowledge_sources, project
    )
    selected_exps = select_primary_experiences(experiences, question_map)

    # JD 키워드 추출
    jd_keywords = []
    jd_text = safe_read_text(ws.profile_dir / "jd.md")
    if jd_text:
        from .pdf_utils import extract_jd_keywords

        jd_keywords = extract_jd_keywords(jd_text)
        logger.info(f"JD 키워드 추출: {jd_keywords[:5]}")
    ncs_profile = build_ncs_profile(
        ws,
        project=project,
        experiences=experiences,
        question_map=question_map,
        jd_keywords=jd_keywords,
        company_analysis=company_analysis,
    )
    narrative_ssot = build_narrative_ssot(
        ws,
        project,
        experiences,
        question_map=question_map,
        company_analysis=company_analysis,
    )
    research_strategy_translation = build_research_strategy_translation(
        ws,
        project,
        company_analysis=company_analysis,
    )
    outcome_dashboard = build_outcome_dashboard(ws, project, "writer")
    kpi_dashboard = build_kpi_dashboard(ws, project, "writer")

    extra = {
        "question_map": question_map,
        "writer_brief": read_json_if_exists(ws.analysis_dir / "writer_brief.json"),
        "legacy_target_path": relative(ws.root, target_path),
        "structure_rules_path": relative(
            ws.root, ws.analysis_dir / "structure_rules.md"
        ),
        "jd_keywords": jd_keywords,
        "feedback_learning": build_feedback_learning_context(
            ws, "writer", project=project
        ),
        "committee_feedback": build_committee_feedback_context(ws),
        "ncs_profile": ncs_profile,
        "candidate_profile": candidate_profile,
        "company_profile": company_profile,
        "narrative_ssot": narrative_ssot,
        "research_strategy_translation": research_strategy_translation,
        "outcome_dashboard": outcome_dashboard,
        "kpi_dashboard": kpi_dashboard,
        "question_specific_hints": question_specific_hints,
        "application_strategy": read_json_if_exists(
            ws.analysis_dir / "application_strategy.json"
        ),
    }
    if company_analysis:
        source_grading = read_json_if_exists(ws.analysis_dir / "source_grading.json")
        strategy_pack = build_role_industry_strategy_from_project(
            project,
            company_analysis,
            question_map=question_map,
            source_grading=source_grading,
        )
        company_analysis.role_industry_strategy = strategy_pack
        if hasattr(company_analysis, "model_dump"):
            extra["company_analysis"] = company_analysis.model_dump()
        else:
            extra["company_analysis"] = company_analysis
    extra["self_intro_pack"] = build_self_intro_pack(
        ws, project, company_analysis=company_analysis
    )

    # [토큰 압축 로직]
    while len(hints) >= 0:
        data_block = build_data_block(
            project=project,
            experiences=selected_exps,
            knowledge_hints=hints,
            extra=extra,
        )
        content = PROMPT_WRITER.format(data_block=data_block)
        if not is_over_limit(count_tokens(content)) or not hints:
            break
        hints.pop()
        logger.info(
            f"Compressing context (Writer): Reduced knowledge hints to {len(hints)}"
        )

    out = ws.outputs_dir / "latest_draft_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def build_interview_prompt(ws: Workspace, company_analysis=None) -> Path:
    ws.ensure()
    project = load_project(ws)
    project = classify_project_questions_with_llm_fallback(ws, project, enabled=False)
    save_project(ws, project)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    writer_artifact = safe_read_text(ws.artifacts_dir / "writer.md")
    writer_quality = read_json_if_exists(ws.artifacts_dir / "writer_quality.json")
    interview_defense = read_json_if_exists(ws.artifacts_dir / "interview_defense.json")
    jd_keywords = _extract_jd_keywords_for_research(ws)
    ncs_profile = build_ncs_profile(
        ws,
        project=project,
        experiences=experiences,
        question_map=question_map,
        jd_keywords=jd_keywords,
        company_analysis=company_analysis,
    )
    candidate_profile = build_candidate_profile(ws, project, experiences)
    company_profile = build_company_profile(ws, project, candidate_profile)
    interview_support_pack = build_interview_support_pack(ws, candidate_profile)
    narrative_ssot = build_narrative_ssot(
        ws,
        project,
        experiences,
        question_map=question_map,
        company_analysis=company_analysis,
    )
    research_strategy_translation = build_research_strategy_translation(
        ws,
        project,
        company_analysis=company_analysis,
    )
    outcome_dashboard = build_outcome_dashboard(ws, project, "interview")
    kpi_dashboard = build_kpi_dashboard(ws, project, "interview")

    extra = {
        "question_map": question_map,
        "writer_artifact": writer_artifact,
        "writer_quality": writer_quality,
        "interview_defense": interview_defense,
        "feedback_learning": build_feedback_learning_context(
            ws, "interview", project=project
        ),
        "committee_feedback": build_committee_feedback_context(ws),
        "ncs_profile": ncs_profile,
        "candidate_profile": candidate_profile,
        "company_profile": company_profile,
        "interview_support_pack": interview_support_pack,
        "narrative_ssot": narrative_ssot,
        "research_strategy_translation": research_strategy_translation,
        "outcome_dashboard": outcome_dashboard,
        "kpi_dashboard": kpi_dashboard,
        "question_specific_hints": build_question_specific_knowledge_hints(
            knowledge_sources, project
        ),
        "application_strategy": read_json_if_exists(
            ws.analysis_dir / "application_strategy.json"
        ),
    }
    if company_analysis:
        source_grading = read_json_if_exists(ws.analysis_dir / "source_grading.json")
        strategy_pack = build_role_industry_strategy_from_project(
            project,
            company_analysis,
            question_map=question_map,
            source_grading=source_grading,
        )
        company_analysis.role_industry_strategy = strategy_pack
        if hasattr(company_analysis, "model_dump"):
            extra["company_analysis"] = company_analysis.model_dump()
        else:
            extra["company_analysis"] = company_analysis
    extra["self_intro_pack"] = build_self_intro_pack(
        ws, project, company_analysis=company_analysis
    )

    data_block = build_data_block(
        project=project,
        experiences=select_primary_experiences(experiences, question_map),
        knowledge_hints=build_knowledge_hints(
            knowledge_sources, project, applicant_profile=candidate_profile
        ),
        extra=extra,
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


def build_company_research_prompt(
    ws: Workspace,
    research_brief: dict[str, Any] | None = None,
    source_grading: dict[str, Any] | None = None,
) -> Path:
    """기업·직무 조사 프롬프트를 빌드합니다."""
    ws.ensure()
    project = load_project(ws)
    project = classify_project_questions_with_llm_fallback(ws, project, enabled=False)
    save_project(ws, project)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    candidate_profile = build_candidate_profile(ws, project, experiences)
    jd_text = safe_read_text(ws.profile_dir / "jd.md")
    company_profile = build_company_profile(
        ws,
        project,
        candidate_profile,
        job_description=jd_text,
    )
    live_source_updates = build_live_source_update_summary(ws)
    live_priority_by_url = build_live_priority_by_url(ws)

    company_analysis = None
    if project.company_name:
        try:
            company_analysis = analyze_company(
                company_name=project.company_name,
                job_title=project.job_title,
                company_type=project.company_type,
                success_cases=_get_success_cases_for_analysis(ws),
            )
        except Exception as e:
            logger.warning(f"Company analysis failed during research prompt build: {e}")

    jd_keywords = _extract_jd_keywords_for_research(ws)
    brief = research_brief or build_research_brief(ws)
    grading = source_grading or build_source_grading(ws, research_brief=brief)
    ncs_profile = build_ncs_profile(
        ws,
        project=project,
        experiences=experiences,
        question_map=question_map,
        jd_keywords=jd_keywords,
        company_analysis=company_analysis,
    )
    narrative_ssot = build_narrative_ssot(
        ws,
        project,
        experiences,
        question_map=question_map,
        company_analysis=company_analysis,
    )
    research_strategy_translation = build_research_strategy_translation(
        ws,
        project,
        company_analysis=company_analysis,
        source_grading=grading,
    )
    outcome_dashboard = build_outcome_dashboard(ws, project, "company_research")
    kpi_dashboard = build_kpi_dashboard(ws, project, "company_research")

    data_block = build_data_block(
        project=project,
        experiences=experiences[:3],
        knowledge_hints=build_knowledge_hints(
            knowledge_sources,
            project,
            applicant_profile=candidate_profile,
            live_priority_by_url=live_priority_by_url,
        ),
        extra={
            "question_map": question_map,
            "jd_keywords": jd_keywords,
            "company_analysis": company_analysis.model_dump()
            if company_analysis
            else None,
            "question_specific_hints": build_question_specific_knowledge_hints(
                knowledge_sources,
                project,
                live_priority_by_url=live_priority_by_url,
            ),
            "research_notes": project.research_notes,
            "research_brief": brief,
            "source_grading": grading,
            "ncs_profile": ncs_profile,
            "candidate_profile": candidate_profile,
            "company_profile": company_profile,
            "live_source_updates": live_source_updates,
            "priority_live_updates": live_source_updates["priority_live_updates"],
            "narrative_ssot": narrative_ssot,
            "research_strategy_translation": research_strategy_translation,
            "outcome_dashboard": outcome_dashboard,
            "kpi_dashboard": kpi_dashboard,
            "application_strategy": read_json_if_exists(
                ws.analysis_dir / "application_strategy.json"
            ),
        },
    )
    content = PROMPT_COMPANY_RESEARCH.format(data_block=data_block)
    out = ws.outputs_dir / "latest_company_research_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def run_company_research_with_codex(
    ws: Workspace, tool: str = "codex"
) -> dict[str, Any]:
    with StepProgress("Company Research 파이프라인") as progress:
        ws.ensure()
        initialize_state(ws)
        progress.step("워크스페이스 초기화", status="success")

        research_brief = build_research_brief(ws)
        source_grading = build_source_grading(
            ws,
            research_brief=research_brief,
            use_semantic_review=True,
            tool=tool,
        )
        prompt_path = build_company_research_prompt(
            ws,
            research_brief=research_brief,
            source_grading=source_grading,
        )
        run_dir = ws.runs_dir / timestamp_slug()
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_output_path = run_dir / "raw_company_research.md"
        progress.step("프롬프트 빌드", status="success")

        exit_code = run_codex(prompt_path, ws.root, raw_output_path, tool=tool)
        if exit_code != 0:
            progress.step("Codex 실행 실패", status="failed")
        else:
            progress.step("Codex 실행 완료", status="success")

        headings = [
            "## 블록 1: 확정 정보",
            "## 블록 2: 입력 기반 핵심 신호",
            "## 블록 3: 직무 분석",
            "## 블록 4: 회사/조직 적합성 해석",
            "## 블록 5: 자소서 연결 전략",
            "## 블록 6: 면접 대비 포인트",
            "## 블록 7: SELF-CHECK",
        ]
        raw_text = safe_read_text(raw_output_path)
        normalized_text = normalize_contract_output(raw_text, headings)
        validation_dict = validate_company_research_contract(normalized_text)
        validation_missing = list(validation_dict["missing"])
        validation_missing.extend(validation_dict.get("semantic_missing", []))
        validation = ValidationResult(
            passed=validation_dict["passed"],
            missing=validation_missing,
        )

        accepted_path = ws.analysis_dir / "company_research.md"
        source_trace_path = ws.analysis_dir / "company_research_sources.json"
        research_brief_path = ws.analysis_dir / "research_brief.json"
        source_grading_path = ws.analysis_dir / "source_grading.json"
        project = load_project(ws)
        knowledge_sources = load_knowledge_sources(ws)
        question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
        source_trace = {
            "project": {
                "company_name": project.company_name,
                "job_title": project.job_title,
                "company_type": project.company_type,
            },
            "question_count": len(project.questions),
            "knowledge_source_titles": [item.title for item in knowledge_sources[:10]],
            "question_map_count": len(question_map),
            "jd_exists": (ws.profile_dir / "jd.md").exists(),
            "research_notes_present": bool(project.research_notes.strip()),
            "research_brief_path": str(research_brief_path.relative_to(ws.root)),
            "source_grading_path": str(source_grading_path.relative_to(ws.root)),
            "corroborated_area_count": source_grading["cross_check"][
                "corroborated_area_count"
            ],
            "single_source_area_count": source_grading["cross_check"][
                "single_source_area_count"
            ],
            "source_conflict_count": len(source_grading["cross_check"]["conflicts"]),
        }

        if validation.passed:
            accepted_path.write_text(normalized_text, encoding="utf-8")
        write_json(source_trace_path, source_trace)
        progress.step(
            f"검증 {'통과' if validation.passed else '실패'}",
            status="success" if validation.passed else "failed",
        )

    snapshot = GeneratedArtifact(
        id=f"research-{timestamp_slug()}",
        artifact_type=ArtifactType.RESEARCH,
        accepted=validation.passed,
        input_snapshot=source_trace,
        output_path=str(accepted_path.relative_to(ws.root)),
        raw_output_path=str(raw_output_path.relative_to(ws.root)),
        validation=validation,
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)
    write_json(
        run_dir / "company_research.json",
        {
            "validation": validation.model_dump(),
            "exit_code": exit_code,
            "source_trace_path": str(source_trace_path.relative_to(ws.root)),
            "research_brief_path": str(research_brief_path.relative_to(ws.root)),
            "source_grading_path": str(source_grading_path.relative_to(ws.root)),
        },
    )

    cp_mgr = CheckpointManager(ws.root)
    cp_mgr.save_checkpoint(
        "company_research",
        {
            "artifact_path": str(accepted_path.relative_to(ws.root)),
            "validation": validation.model_dump(),
            "source_trace_path": str(source_trace_path.relative_to(ws.root)),
            "research_brief_path": str(research_brief_path.relative_to(ws.root)),
            "source_grading_path": str(source_grading_path.relative_to(ws.root)),
        },
        status="success" if validation.passed else "failed",
        error=", ".join(validation.missing[:5]) if validation.missing else None,
    )

    return {
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "validation": validation.model_dump(),
        "exit_code": exit_code,
        "source_trace_path": str(source_trace_path),
        "research_brief_path": str(research_brief_path),
        "source_grading_path": str(source_grading_path),
        "top001_strategy_path": str(
            ws.analysis_dir / "research_strategy_translation_top001.json"
        ),
        "application_strategy_path": str(ws.analysis_dir / "application_strategy.json"),
    }


# _run_with_cli_tool, run_codex는 executor.py로 이동 (상단 import 참조)


# write_if_missing, normalize_example, relative는 utils.py로 이동 (상단 import 참조)


def collect_source_paths(ws: Workspace, source_path: Path | None) -> list[Path]:
    target = source_path or ws.sources_raw_dir
    paths: list[Path] = []
    if target.is_file():
        paths.append(target)
    else:
        paths.extend(
            sorted(
                path
                for path in target.rglob("*")
                if path.is_file() and not _is_metadata_sidecar(path)
            )
        )

    # config에서 linkareer CSV 경로 읽어 추가
    linkareer_rel = get_config_value("linkareer.source_path", "")
    if linkareer_rel:
        # resume-agent 프로젝트 루트 기준으로 상대 경로 해석
        project_root = Path(__file__).parent.parent.parent
        linkareer_path = (project_root / linkareer_rel).resolve()
        if linkareer_path.is_file() and linkareer_path not in paths:
            paths.append(linkareer_path)

    return paths


def _is_metadata_sidecar(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(":zone.identifier") or name.endswith(".zone.identifier")


def materialize_source_file(
    ws: Workspace,
    path: Path,
    *,
    source_root: Path | None = None,
) -> Path | None:
    """외부 원본 파일을 sources/raw 아래의 텍스트 자산으로 변환합니다."""
    if not path.exists() or not path.is_file():
        return None

    source_root = source_root.resolve() if source_root else None
    path = path.resolve()

    if source_root and source_root.is_dir() and path.is_relative_to(source_root):
        relative_path = path.relative_to(source_root)
    else:
        relative_path = Path(path.name)

    raw_target = ws.sources_raw_dir / relative_path
    suffix = path.suffix.lower()

    if suffix in {".pdf", ".docx"}:
        from .pdf_utils import extract_text_from_docx, extract_text_from_pdf

        extractor = (
            extract_text_from_pdf if suffix == ".pdf" else extract_text_from_docx
        )
        text = extractor(path)
        if not text.strip():
            logger.warning(f"No text extracted from {path}")
            return None
        raw_target = raw_target.with_suffix(".txt")
        raw_target.parent.mkdir(parents=True, exist_ok=True)
        raw_target.write_text(text, encoding="utf-8")
        return raw_target

    raw_target.parent.mkdir(parents=True, exist_ok=True)
    if path != raw_target:
        shutil.copy2(path, raw_target)
    return raw_target


def write_source_artifacts(ws: Workspace, source: KnowledgeSource) -> None:
    name = f"{source.id}-{slugify(source.title)}"
    normalized_path = ws.sources_normalized_dir / f"{name}.md"
    extracted_path = ws.sources_extracted_dir / f"{name}.json"
    normalized_path.write_text(
        f"# {source.title}\n\n{source.cleaned_text}\n",
        encoding="utf-8",
    )
    write_json(extracted_path, source.model_dump())


def merge_sources(
    existing: List[KnowledgeSource], new_sources: List[KnowledgeSource]
) -> List[KnowledgeSource]:
    by_id = {source.id: source for source in existing}
    for source in new_sources:
        by_id[source.id] = source
    return list(by_id.values())


def _merge_success_cases(
    existing: List[SuccessCase], new_cases: List[SuccessCase]
) -> List[SuccessCase]:
    """기존 success_cases와 새로 파싱된 cases를 병합. (title+company_name 기준 중복 제거)"""
    seen: dict[str, SuccessCase] = {}
    for case in existing:
        key = f"{case.title}|{case.company_name}"
        seen[key] = case
    for case in new_cases:
        key = f"{case.title}|{case.company_name}"
        seen[key] = case  # 새로 파싱된 데이터로 갱신
    return list(seen.values())


# slugify는 utils.py로 이동 (상단 import 참조)


def latest_accepted_artifacts(
    artifacts: List[GeneratedArtifact],
    artifact_types: List[ArtifactType],
) -> List[GeneratedArtifact]:
    selected: List[GeneratedArtifact] = []
    for artifact_type in artifact_types:
        candidates = [
            item
            for item in artifacts
            if item.artifact_type == artifact_type and item.accepted
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda item: item.created_at)
        selected.append(candidates[-1])
    return selected


# normalize_contract_output는 utils.py로 이동 (상단 import 참조)


# build_exec_prompt, extract_last_codex_message는 executor.py로 이동 (상단 import 참조)


# timestamp_slug는 utils.py로 이동 (상단 import 참조)


def build_data_block(
    *,
    project: ApplicationProject,
    experiences: List[Experience],
    knowledge_hints: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> str:
    payload = {
        "project": project.model_dump(),
        "experiences": [item.model_dump() for item in experiences],
        "knowledge_hints": knowledge_hints,
        "extra": extra or {},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


# read_json_if_exists, safe_read_text는 utils.py로 이동 (상단 import 참조)


def select_primary_experiences(
    experiences: List[Experience],
    question_map: list[dict[str, Any]],
) -> List[Experience]:
    if not question_map:
        return experiences[:3]
    selected: List[Experience] = []
    seen: set[str] = set()
    for item in question_map:
        experience_id = str(item.get("experience_id", ""))
        if experience_id in seen:
            continue
        for experience in experiences:
            if experience.id == experience_id:
                selected.append(experience)
                seen.add(experience_id)
                break
    return selected or experiences[:3]


def extract_markdown_section(text: str, heading: str, stop_headings: list[str]) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    start += len(heading)
    end = len(text)
    for stop in stop_headings:
        idx = text.find(stop, start)
        if idx != -1 and idx < end:
            end = idx
    return text[start:end].strip()


def extract_question_answer_map(
    writer_text: str,
    questions: List[Any],
) -> dict[str, str]:
    headings = [
        "## 블록 1: ASSUMPTIONS & MISSING FACTS",
        "## 블록 2: OUTLINE",
        "## 블록 3: DRAFT ANSWERS",
        "## 블록 4: SELF-CHECK",
    ]
    draft_body = extract_markdown_section(
        writer_text,
        "## 블록 3: DRAFT ANSWERS",
        [item for item in headings if item != "## 블록 3: DRAFT ANSWERS"],
    )
    if not draft_body.strip() or not questions:
        return {}

    split_pattern = re.compile(r"(?:^|\n)(?:Q\s*\d+[:.)]?|문항\s*\d+[:.)]?|\d+\)\s+)")
    chunks = [
        chunk.strip() for chunk in split_pattern.split(draft_body) if chunk.strip()
    ]
    if len(chunks) < len(questions):
        chunks = [
            chunk.strip()
            for chunk in re.split(r"\n\s*\n+", draft_body)
            if chunk.strip()
        ]

    result: dict[str, str] = {}
    for question, chunk in zip(questions, chunks):
        cleaned = re.sub(r"글자수:\s*약\s*\d+\s*자.*", "", chunk).strip()
        if cleaned:
            result[question.id] = cleaned
    return result


def extract_question_answer_details(
    writer_text: str,
    questions: List[Any],
) -> dict[str, dict[str, Any]]:
    answer_map = extract_question_answer_map(writer_text, questions)
    details: dict[str, dict[str, Any]] = {}
    for question in questions:
        answer = answer_map.get(question.id, "")
        details[question.id] = {
            "answer": answer,
            "char_count": len(answer),
            "has_answer": bool(answer.strip()),
            "char_limit": getattr(question, "char_limit", None),
            "question_order": getattr(question, "order_no", None),
        }
    return details


def build_writer_char_limit_report(
    project: ApplicationProject,
    writer_text: str,
    ratio_min: float | None = None,
    ratio_max: float | None = None,
) -> dict[str, Any]:
    ratio_min = (
        float(ratio_min)
        if ratio_min is not None
        else float(get_config_value("export.char_limit_ratio_min", 0.90))
    )
    ratio_max = (
        float(ratio_max)
        if ratio_max is not None
        else float(get_config_value("export.char_limit_ratio_max", 0.97))
    )

    details = extract_question_answer_details(writer_text, project.questions)
    question_reports: list[dict[str, Any]] = []
    issues: list[str] = []

    for question in project.questions:
        detail = details.get(question.id, {})
        answer = str(detail.get("answer") or "")
        char_count = int(detail.get("char_count") or 0)
        char_limit = getattr(question, "char_limit", None)
        ratio = round(char_count / char_limit, 3) if char_limit else None

        status = "within_target"
        if not answer.strip():
            status = "missing_answer"
        elif not char_limit:
            status = "no_limit"
        elif char_count > char_limit:
            status = "over_limit"
        elif ratio is not None and ratio < ratio_min:
            status = "under_target"
        elif ratio is not None and ratio > ratio_max:
            status = "over_target"

        report_item = {
            "question_id": question.id,
            "question_order": question.order_no,
            "question_text": question.question_text,
            "char_count": char_count,
            "char_limit": char_limit,
            "ratio": ratio,
            "target_min": ratio_min,
            "target_max": ratio_max,
            "status": status,
        }
        question_reports.append(report_item)

        if status == "missing_answer":
            issues.append(f"Q{question.order_no} 답변 본문이 비어 있습니다")
        elif status == "over_limit":
            issues.append(
                f"Q{question.order_no} 글자수 초과: {char_count}자 / 제한 {char_limit}자 (공백 포함)"
            )
        elif status == "under_target":
            issues.append(
                f"Q{question.order_no} 분량 부족: {char_count}자 / 제한 {char_limit}자 / 목표 {int(ratio_min * 100)}% 이상"
            )
        elif status == "over_target":
            issues.append(
                f"Q{question.order_no} 목표 범위 초과: {char_count}자 / 제한 {char_limit}자 / 목표 {int(ratio_max * 100)}% 이하"
            )

    return {
        "passed": not issues,
        "issues": issues,
        "question_reports": question_reports,
        "ratio_min": ratio_min,
        "ratio_max": ratio_max,
    }


def enforce_writer_char_limits(
    project: ApplicationProject,
    writer_text: str,
    rewrite_func,
    max_attempts: int = 2,
) -> tuple[str, dict[str, Any], bool]:
    current_text = writer_text
    report = build_writer_char_limit_report(project, current_text)
    changed = False

    if report["passed"]:
        return current_text, report, changed

    for attempt in range(1, max_attempts + 1):
        rewritten = rewrite_func(current_text, report, attempt)
        if not rewritten or not str(rewritten).strip():
            break
        current_text = str(rewritten)
        changed = True
        report = build_writer_char_limit_report(project, current_text)
        if report["passed"]:
            break

    return current_text, report, changed


def enforce_patina_char_limits(
    project: ApplicationProject,
    patina_result: dict[str, Any] | None,
    rewrite_func,
    max_attempts: int = 2,
) -> dict[str, Any] | None:
    if not patina_result:
        return patina_result
    reassembled_text = str(patina_result.get("reassembled_text") or "")
    if not reassembled_text.strip():
        patina_result["char_limit_report"] = {
            "passed": True,
            "issues": [],
            "question_reports": [],
        }
        patina_result["char_limit_adjusted"] = False
        return patina_result

    final_text, report, changed = enforce_writer_char_limits(
        project,
        reassembled_text,
        rewrite_func=rewrite_func,
        max_attempts=max_attempts,
    )
    patina_result["reassembled_text"] = final_text
    patina_result["char_limit_report"] = report
    patina_result["char_limit_adjusted"] = changed
    if not report.get("passed", True):
        warnings = list(patina_result.get("warnings", []))
        warnings.extend(report.get("issues", []))
        patina_result["warnings"] = list(dict.fromkeys(warnings))
    return patina_result


def merge_writer_validation_with_char_report(
    validation: ValidationResult,
    char_limit_report: dict[str, Any],
) -> ValidationResult:
    if char_limit_report.get("passed", True):
        return validation

    merged_missing = list(validation.missing)
    merged_missing.extend(char_limit_report.get("issues", []))
    return ValidationResult(
        passed=False,
        missing=list(dict.fromkeys(merged_missing)),
    )


def build_writer_quality_evaluations(
    project: ApplicationProject,
    writer_text: str,
    experiences: List[Experience],
    question_map: list[dict[str, Any]],
    company_analysis: CompanyAnalysis | None,
    ncs_profile: dict[str, Any] | None = None,
    narrative_ssot: dict[str, Any] | None = None,
    writer_brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not writer_text.strip() or not project.questions:
        return []

    evaluator = AnswerQualityEvaluator(company_analysis)
    simulator = DefenseSimulator(company_analysis)
    answer_map = extract_question_answer_map(writer_text, project.questions)
    answer_details = extract_question_answer_details(writer_text, project.questions)
    experience_by_id = {item.id: item for item in experiences}
    map_by_question = {
        str(item.get("question_id")): item
        for item in question_map
        if item.get("question_id")
    }
    writer_brief_by_question = {
        str(item.get("question_id") or ""): item
        for item in (writer_brief or {}).get("question_strategies", [])
        if isinstance(item, dict) and item.get("question_id")
    }

    evaluations: list[dict[str, Any]] = []
    for question in project.questions:
        resolved_question_type = _resolve_question_type(question)
        answer = answer_map.get(question.id, "")
        if not answer:
            continue
        mapped = map_by_question.get(question.id, {})
        experience = experience_by_id.get(str(mapped.get("experience_id", "")))
        strategy_brief = writer_brief_by_question.get(question.id, {})
        quality = evaluator.evaluate(
            answer=answer,
            question=question.question_text,
            question_type=resolved_question_type,
            experience=experience,
        )
        humanization = analyze_humanization(answer)
        payload = quality.model_dump()
        payload["resolved_question_type"] = resolved_question_type.value
        payload["question_order"] = question.order_no
        payload["question_text"] = question.question_text
        payload["char_count"] = answer_details.get(question.id, {}).get("char_count", 0)
        payload["char_limit"] = question.char_limit
        payload["char_ratio"] = (
            round(payload["char_count"] / question.char_limit, 3)
            if question.char_limit
            else None
        )
        payload["experience_title"] = experience.title if experience else None
        payload["humanization_score"] = humanization["score"]
        payload["humanization_flags"] = humanization["flags"]
        payload["humanization_suggestions"] = humanization["suggestions"]
        message_discipline = evaluate_writer_message_discipline(
            answer,
            strategy_brief=strategy_brief,
        )
        cliche_block = evaluate_writer_cliche_blocking(
            answer,
            discouraged_phrases=(
                company_analysis.discouraged_phrases if company_analysis else None
            ),
        )
        differentiation = evaluate_writer_answer_differentiation(
            answer,
            experience=experience,
            strategy_brief=strategy_brief,
        )
        ncs_alignment = evaluate_ncs_alignment(
            answer=answer,
            question_id=question.id,
            question_type=resolved_question_type,
            ncs_profile=ncs_profile,
        )
        payload["ncs_alignment_score"] = ncs_alignment["score"]
        payload["ncs_expected_competencies"] = ncs_alignment["expected_competencies"]
        payload["ncs_matched_competencies"] = ncs_alignment["matched_competencies"]
        payload["ncs_missing_competencies"] = ncs_alignment["missing_competencies"]
        payload["ncs_expected_ability_units"] = ncs_alignment["expected_ability_units"]
        payload["ncs_matched_ability_units"] = ncs_alignment["matched_ability_units"]
        payload["ncs_missing_ability_units"] = ncs_alignment["missing_ability_units"]
        payload["ncs_suggestions"] = ncs_alignment["suggestions"]
        ssot_alignment = evaluate_narrative_ssot_alignment(
            answer,
            experience=experience,
            narrative_ssot=narrative_ssot,
        )
        payload["ssot_alignment_score"] = ssot_alignment["score"]
        payload["ssot_expected_claims"] = ssot_alignment["expected_claims"]
        payload["ssot_matched_claims"] = ssot_alignment["matched_claims"]
        payload["ssot_missing_claims"] = ssot_alignment["missing_claims"]
        payload["ssot_offtrack_signals"] = ssot_alignment["offtrack_signals"]
        payload["ssot_suggestions"] = ssot_alignment["suggestions"]
        simulation = simulator.simulate(
            primary_question=question.question_text,
            answer=answer,
            question_type=resolved_question_type,
            experiences=[experience] if experience else None,
        )
        payload["expected_followups"] = simulation.follow_up_questions[:3]
        payload["defense_gaps"] = simulation.risk_areas[:4]
        committee_reaction = evaluate_writer_committee_reaction(
            answer,
            simulation=simulation.model_dump(),
            strategy_brief=strategy_brief,
        )
        payload["message_discipline_score"] = message_discipline["score"]
        payload["message_primary"] = message_discipline["primary_message"]
        payload["message_competing_points"] = message_discipline["competing_messages"]
        payload["message_discipline_suggestions"] = message_discipline["suggestions"]
        payload["cliche_score"] = cliche_block["score"]
        payload["cliche_flags"] = cliche_block["flags"]
        payload["cliche_suggestions"] = cliche_block["suggestions"]
        payload["differentiation_score"] = differentiation["score"]
        payload["differentiation_line"] = differentiation["line"]
        payload["differentiation_gaps"] = differentiation["gaps"]
        payload["differentiation_suggestions"] = differentiation["suggestions"]
        payload["committee_reaction_score"] = committee_reaction["score"]
        payload["committee_attack_points"] = committee_reaction["attack_points"]
        payload["committee_reaction_summary"] = committee_reaction["summary"]
        payload["committee_mitigation_priority"] = committee_reaction[
            "mitigation_priority"
        ]
        payload["writer_checklist_status"] = {
            "core_message": strategy_brief.get("core_message", ""),
            "required_evidence": strategy_brief.get("required_evidence", [])[:3],
            "target_impression": strategy_brief.get("target_impression", ""),
        }
        payload["interviewer_checklist"] = [
            "면접관이 수치와 비교 기준을 바로 물어도 30초 안에 답할 수 있는가",
            "팀 경험이라면 개인 기여와 판단 기준을 분리해 설명할 수 있는가",
            "왜 이 선택을 했는지와 그 선택이 보여주는 가치관까지 이어서 답할 수 있는가",
        ]
        payload["evaluation_rubric"] = {
            "strong_points": payload.get("strengths", [])[:3],
            "risk_points": list(
                dict.fromkeys(
                    [
                        *payload.get("weaknesses", []),
                        *payload.get("defense_gaps", []),
                    ]
                )
            )[:4],
            "improvement_points": list(
                dict.fromkeys(
                    [
                        *payload.get("suggestions", []),
                        *payload.get("humanization_suggestions", []),
                        *payload.get("message_discipline_suggestions", []),
                        *payload.get("cliche_suggestions", []),
                        *payload.get("differentiation_suggestions", []),
                        *payload.get("ncs_suggestions", []),
                        *payload.get("ssot_suggestions", []),
                    ]
                )
            )[:4],
        }
        evaluations.append(payload)
    return evaluations


def build_writer_result_quality_evaluations(
    project: ApplicationProject,
    writer_text: str,
    experiences: List[Experience],
    question_map: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not writer_text.strip() or not project.questions:
        return []

    answer_map = extract_question_answer_map(writer_text, project.questions)
    experience_by_id = {item.id: item for item in experiences}
    map_by_question = {
        str(item.get("question_id")): item
        for item in question_map
        if isinstance(item, dict) and item.get("question_id")
    }

    evaluations: list[dict[str, Any]] = []
    for question in project.questions:
        answer = answer_map.get(question.id, "")
        if not answer:
            continue
        mapped = map_by_question.get(question.id, {})
        experience = experience_by_id.get(str(mapped.get("experience_id", "")))
        context_parts = []
        if experience:
            context_parts = [
                experience.situation,
                experience.task,
                experience.action,
                experience.result,
            ]
        quality = evaluate_draft_quality(
            answer,
            question.question_text,
            "\n".join(part for part in context_parts if part),
        )
        evaluations.append(
            {
                "question_id": question.id,
                "question_order": question.order_no,
                "question_text": question.question_text,
                "overall": round(float(quality.overall) / 100.0, 3),
                "details": {
                    key: round(float(value) / 100.0, 3)
                    for key, value in quality.details.items()
                },
                "feedback": quality.feedback[:4],
                "suggestions": quality.suggestions[:4],
            }
        )
    return evaluations


def evaluate_writer_message_discipline(
    answer: str,
    *,
    strategy_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    compact_answer = re.sub(r"\s+", " ", answer).strip()
    clauses = [
        item.strip()
        for item in re.split(r"[.!?\n]|하지만|또한|그리고|반면", compact_answer)
        if item.strip()
    ]
    primary_message = str((strategy_brief or {}).get("core_message") or "").strip()
    competing_messages = [
        clause[:80]
        for clause in clauses[1:]
        if len(clause) >= 18
    ][:3]
    score = 1.0
    if len(competing_messages) >= 2:
        score -= 0.25
    if not primary_message:
        primary_message = clauses[0][:80] if clauses else ""
    elif primary_message and primary_message not in compact_answer:
        score -= 0.1
    suggestions = []
    if len(competing_messages) >= 2:
        suggestions.append("문항당 주장 축을 하나로 줄이고 보조 메시지는 삭제하거나 축소하세요.")
    if primary_message and primary_message not in compact_answer:
        suggestions.append("writer_brief의 핵심 메시지를 첫 2문장 안에 더 직접적으로 드러내세요.")
    return {
        "score": round(max(0.0, score), 3),
        "primary_message": primary_message,
        "competing_messages": competing_messages,
        "suggestions": suggestions,
    }


def evaluate_writer_cliche_blocking(
    answer: str,
    *,
    discouraged_phrases: list[str] | None = None,
) -> dict[str, Any]:
    cliche_patterns = [
        "성장",
        "노력",
        "배움",
        "열정",
        "역량을 키웠",
        "깨달았",
        "최선을 다",
    ]
    flags = [pattern for pattern in cliche_patterns if pattern in answer]
    discouraged_hits = [
        phrase for phrase in (discouraged_phrases or []) if phrase and phrase in answer
    ]
    score = max(0.0, 1.0 - (0.08 * len(flags)) - (0.06 * len(discouraged_hits)))
    suggestions = []
    if flags:
        suggestions.append("추상어 대신 당시 판단 기준, 수치, 증빙 문장으로 바꾸세요.")
    if len(flags) >= 2:
        suggestions.append("성장/노력/배움 서술을 줄이고 결과와 조직 적합 신호를 앞에 배치하세요.")
    if discouraged_hits:
        suggestions.append(
            "유사 합격사례에서 반복된 표현 대신 본인 경험의 상황·판단·근거 문장으로 다시 쓰세요."
        )
    return {
        "score": round(score, 3),
        "flags": [*flags[:4], *discouraged_hits[:2]],
        "suggestions": suggestions,
    }


def evaluate_writer_answer_differentiation(
    answer: str,
    *,
    experience: Experience | None = None,
    strategy_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    differentiation_line = str(
        (strategy_brief or {}).get("differentiation_line") or ""
    ).strip()
    score = 0.6
    gaps: list[str] = []
    if re.search(r"\d", answer):
        score += 0.15
    else:
        gaps.append("수치·비교 기준이 부족합니다.")
    if experience and experience.title and experience.title in answer:
        score += 0.1
    else:
        gaps.append("주력 경험명이 답변에 직접 드러나지 않습니다.")
    if differentiation_line and differentiation_line.split(" ")[0] not in answer:
        gaps.append("writer_brief의 차별화 문장이 직접적으로 반영되지 않았습니다.")
    suggestions = []
    if gaps:
        suggestions.append("평균 지원자가 쓸 수 없는 판단 기준·증빙·운영 맥락을 한 문장으로 명시하세요.")
    return {
        "score": round(min(1.0, score), 3),
        "line": differentiation_line,
        "gaps": gaps[:3],
        "suggestions": suggestions,
    }


def evaluate_writer_committee_reaction(
    answer: str,
    *,
    simulation: dict[str, Any],
    strategy_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attack_points = _dedupe_preserve_order(
        list((simulation or {}).get("risk_areas", []))
        + list((simulation or {}).get("follow_up_questions", []))
        + list((strategy_brief or {}).get("expected_attack_points", []))
    )[:4]
    score = max(0.0, 1.0 - (0.1 * len(attack_points)))
    mitigation_priority = attack_points[0] if attack_points else ""
    summary = (
        "면접관이 바로 파고들 만한 지점이 남아 있습니다."
        if attack_points
        else "현재 답변은 비교적 안정적으로 방어 가능합니다."
    )
    return {
        "score": round(score, 3),
        "attack_points": attack_points,
        "summary": summary,
        "mitigation_priority": mitigation_priority,
    }


def build_interview_defense_simulations(
    project: ApplicationProject,
    writer_text: str,
    experiences: List[Experience],
    question_map: list[dict[str, Any]],
    company_analysis: CompanyAnalysis | None,
    ncs_profile: dict[str, Any] | None = None,
    narrative_ssot: dict[str, Any] | None = None,
    strategy_outcome_summary: dict[str, Any] | None = None,
    current_pattern: str | None = None,
) -> list[dict[str, Any]]:
    if not project.questions:
        return []

    simulator = DefenseSimulator(company_analysis)
    top001_engine = None
    try:
        from .top001.integrator import Top001InterviewEngine

        top001_engine = Top001InterviewEngine()
    except Exception as e:
        logger.debug(f"Top001 interview engine unavailable in defense simulation: {e}")
    answer_map = extract_question_answer_map(writer_text, project.questions)
    experience_by_id = {item.id: item for item in experiences}
    map_by_question = {
        str(item.get("question_id")): item
        for item in question_map
        if item.get("question_id")
    }

    simulations: list[dict[str, Any]] = []
    for question in project.questions[:3]:
        resolved_question_type = _resolve_question_type(question)
        mapped = map_by_question.get(question.id, {})
        experience = experience_by_id.get(str(mapped.get("experience_id", "")))
        answer = answer_map.get(question.id)
        if not answer and experience:
            answer = " ".join(
                part.strip()
                for part in [
                    experience.situation,
                    experience.task,
                    experience.action,
                    experience.result,
                ]
                if part.strip()
            )
        if not answer:
            answer = f"{question.question_text}에 대한 답변 초안이 아직 없습니다."

        simulation = simulator.simulate(
            primary_question=question.question_text,
            answer=answer,
            question_type=resolved_question_type,
            experiences=[experience] if experience else None,
        )
        ncs_alignment = evaluate_ncs_alignment(
            answer=answer,
            question_id=question.id,
            question_type=resolved_question_type,
            ncs_profile=ncs_profile,
        )
        payload = simulation.model_dump()
        payload["resolved_question_type"] = resolved_question_type.value
        payload["question_order"] = question.order_no
        payload["experience_title"] = experience.title if experience else None
        payload["ncs_alignment_score"] = ncs_alignment["score"]
        payload["ncs_priority_competencies"] = ncs_alignment["expected_competencies"]
        payload["ncs_missing_competencies"] = ncs_alignment["missing_competencies"]
        payload["ncs_priority_ability_units"] = ncs_alignment["expected_ability_units"]
        payload["ncs_missing_ability_units"] = ncs_alignment["missing_ability_units"]
        payload["interviewer_reaction"] = _simulate_interviewer_reaction(
            answer,
            payload,
            experience=experience,
        )
        payload["interviewer_reaction_chain"] = _build_interviewer_reaction_chain(
            answer,
            payload,
            experience=experience,
        )
        ssot_alignment = evaluate_narrative_ssot_alignment(
            answer,
            experience=experience,
            narrative_ssot=narrative_ssot,
        )
        payload["ssot_alignment_score"] = ssot_alignment["score"]
        payload["ssot_missing_claims"] = ssot_alignment["missing_claims"]
        payload["ssot_offtrack_signals"] = ssot_alignment["offtrack_signals"]
        if resolved_question_type != QuestionType.TYPE_UNKNOWN and experience:
            historical_risk = _build_strategy_outcome_issue(
                question_order=question.order_no,
                question_type=resolved_question_type.value,
                experience_id=experience.id,
                strategy_outcome_summary=strategy_outcome_summary,
                current_pattern=current_pattern,
            )
            if historical_risk:
                payload["historical_outcome_signal"] = historical_risk
        payload["improvement_suggestions"] = list(
            dict.fromkeys(
                [
                    *payload.get("improvement_suggestions", []),
                    *ncs_alignment["suggestions"],
                    *ssot_alignment["suggestions"],
                    *(
                        [payload["historical_outcome_signal"]]
                        if payload.get("historical_outcome_signal")
                        else []
                    ),
                ]
            )
        )
        if top001_engine:
            try:
                top001_result = top001_engine.simulate_interview(
                    question.question_text,
                    answer,
                    experience,
                    company_analysis,
                )
                payload["logical_vulnerabilities"] = top001_result.get(
                    "vulnerabilities", []
                )
                payload["logical_follow_up_chain"] = [
                    {
                        "primary_question": chain.get("primary_question", ""),
                        "depth_1_questions": chain.get("depth_1_questions", [])[:2],
                    }
                    for chain in top001_result.get("question_chains", [])[:2]
                    if isinstance(chain, dict)
                ]
                payload["logical_pressure_level"] = top001_result.get(
                    "pressure_level", ""
                )
                payload["improvement_suggestions"] = list(
                    dict.fromkeys(
                        payload["improvement_suggestions"]
                        + top001_result.get("recommendations", [])
                    )
                )
                for vulnerability in payload["logical_vulnerabilities"][:2]:
                    if vulnerability and vulnerability not in payload["risk_areas"]:
                        payload["risk_areas"].append(vulnerability)
            except Exception as e:
                logger.debug(f"Top001 simulation merge skipped: {e}")
        payload["interview_rubric"] = {
            "strong_points": payload.get("defense_points", [])[:3],
            "risk_points": payload.get("risk_areas", [])[:4],
            "improvement_points": payload.get("improvement_suggestions", [])[:4],
        }
        simulations.append(payload)
    return simulations


def _resolve_question_type(question: Any) -> QuestionType:
    detected = getattr(question, "detected_type", None)
    if isinstance(detected, str):
        try:
            detected = QuestionType(detected)
        except ValueError:
            detected = QuestionType.TYPE_UNKNOWN
    if isinstance(detected, QuestionType) and detected != QuestionType.TYPE_UNKNOWN:
        return detected
    inferred = classify_question(getattr(question, "question_text", "") or "")
    return (
        inferred if inferred != QuestionType.TYPE_UNKNOWN else QuestionType.TYPE_UNKNOWN
    )


def needs_writer_rewrite(
    validation: ValidationResult,
    quality_evaluations: list[dict[str, Any]],
    result_quality_evaluations: list[dict[str, Any]] | None = None,
) -> bool:
    if not validation.passed:
        return True
    if not quality_evaluations:
        return False
    low_scores = [
        item
        for item in quality_evaluations
        if float(item.get("overall_score", 0.0)) < 0.72
    ]
    low_humanization = [
        item
        for item in quality_evaluations
        if float(item.get("humanization_score", 1.0)) <= 0.78
        or len(item.get("humanization_flags", [])) >= 2
    ]
    low_ncs_alignment = [
        item
        for item in quality_evaluations
        if item.get("ncs_expected_competencies")
        and float(item.get("ncs_alignment_score", 1.0)) < 0.6
    ]
    low_ssot_alignment = [
        item
        for item in quality_evaluations
        if item.get("ssot_expected_claims")
        and float(item.get("ssot_alignment_score", 1.0)) < 0.55
    ]
    low_differentiation = [
        item
        for item in quality_evaluations
        if float(item.get("differentiation_score", 1.0)) < 0.62
    ]
    low_committee_defense = [
        item
        for item in quality_evaluations
        if float(item.get("committee_reaction_score", 1.0)) < 0.62
        or len(item.get("committee_attack_points", [])) >= 3
    ]
    low_message_discipline = [
        item
        for item in quality_evaluations
        if float(item.get("message_discipline_score", 1.0)) < 0.72
    ]
    low_cliche_blocking = [
        item
        for item in quality_evaluations
        if float(item.get("cliche_score", 1.0)) < 0.76
        or len(item.get("cliche_flags", [])) >= 3
    ]
    low_result_quality = [
        item
        for item in (result_quality_evaluations or [])
        if float(item.get("overall", 1.0)) < 0.72
    ]
    return bool(
        low_scores
        or low_humanization
        or low_ncs_alignment
        or low_ssot_alignment
        or low_differentiation
        or low_committee_defense
        or low_message_discipline
        or low_cliche_blocking
        or low_result_quality
    )


def build_writer_rewrite_quality_report(
    before_evaluations: list[dict[str, Any]],
    after_evaluations: list[dict[str, Any]],
    minimum_samples: int = 3,
    before_result_quality_evaluations: list[dict[str, Any]] | None = None,
    after_result_quality_evaluations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _fmt(values: list[str]) -> str:
        cleaned = [
            item.strip() for item in values if isinstance(item, str) and item.strip()
        ]
        return ", ".join(cleaned) if cleaned else "없음"

    before_by_order = {
        int(item.get("question_order")): item
        for item in before_evaluations
        if item.get("question_order") is not None
    }
    after_by_order = {
        int(item.get("question_order")): item
        for item in after_evaluations
        if item.get("question_order") is not None
    }
    before_result_by_order = {
        int(item.get("question_order")): item
        for item in before_result_quality_evaluations or []
        if item.get("question_order") is not None
    }
    after_result_by_order = {
        int(item.get("question_order")): item
        for item in after_result_quality_evaluations or []
        if item.get("question_order") is not None
    }

    orders = sorted(set(before_by_order.keys()) & set(after_by_order.keys()))
    rows: list[dict[str, Any]] = []
    for order in orders:
        before = before_by_order[order]
        after = after_by_order[order]
        row = {
            "question_order": order,
            "overall_before": _to_float(before.get("overall_score", 0.0)),
            "overall_after": _to_float(after.get("overall_score", 0.0)),
            "humanization_before": _to_float(before.get("humanization_score", 0.0)),
            "humanization_after": _to_float(after.get("humanization_score", 0.0)),
            "ncs_before": _to_float(before.get("ncs_alignment_score", 0.0)),
            "ncs_after": _to_float(after.get("ncs_alignment_score", 0.0)),
            "ssot_before": _to_float(before.get("ssot_alignment_score", 0.0)),
            "ssot_after": _to_float(after.get("ssot_alignment_score", 0.0)),
            "ncs_expected_competencies": after.get("ncs_expected_competencies", [])
            or before.get("ncs_expected_competencies", []),
            "ncs_matched_competencies": after.get("ncs_matched_competencies", []),
            "ncs_missing_competencies": after.get("ncs_missing_competencies", []),
        }
        row["overall_delta"] = round(row["overall_after"] - row["overall_before"], 3)
        row["humanization_delta"] = round(
            row["humanization_after"] - row["humanization_before"], 3
        )
        row["ncs_delta"] = round(row["ncs_after"] - row["ncs_before"], 3)
        row["ssot_delta"] = round(row["ssot_after"] - row["ssot_before"], 3)
        before_result = before_result_by_order.get(order, {})
        after_result = after_result_by_order.get(order, {})
        row["result_quality_before"] = _to_float(before_result.get("overall", 0.0))
        row["result_quality_after"] = _to_float(after_result.get("overall", 0.0))
        row["result_quality_delta"] = round(
            row["result_quality_after"] - row["result_quality_before"], 3
        )
        rows.append(row)

    sample_count = len(rows)
    minimum_sample_met = sample_count >= minimum_samples

    if rows:
        avg_overall_delta = round(
            sum(item["overall_delta"] for item in rows) / sample_count, 3
        )
        avg_humanization_delta = round(
            sum(item["humanization_delta"] for item in rows) / sample_count, 3
        )
        avg_ncs_delta = round(sum(item["ncs_delta"] for item in rows) / sample_count, 3)
        avg_ssot_delta = round(
            sum(item["ssot_delta"] for item in rows) / sample_count, 3
        )
        avg_result_quality_delta = round(
            sum(item["result_quality_delta"] for item in rows) / sample_count, 3
        )
    else:
        avg_overall_delta = 0.0
        avg_humanization_delta = 0.0
        avg_ncs_delta = 0.0
        avg_ssot_delta = 0.0
        avg_result_quality_delta = 0.0

    lines = [
        "# Writer Rewrite Quality Comparison",
        "",
        f"- 샘플 수: {sample_count}",
        f"- 최소 샘플 기준(>= {minimum_samples}): {'충족' if minimum_sample_met else '미충족'}",
        f"- 평균 overall 변화: {avg_overall_delta:+.3f}",
        f"- 평균 humanization 변화: {avg_humanization_delta:+.3f}",
        f"- 평균 JD/NCS 변화: {avg_ncs_delta:+.3f}",
        f"- 평균 SSOT 변화: {avg_ssot_delta:+.3f}",
        f"- 평균 result quality 변화: {avg_result_quality_delta:+.3f}",
        "",
        "| 문항 | Overall (전→후) | Human (전→후) | JD/NCS (전→후) | SSOT (전→후) | JD/NCS 근거 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        evidence = (
            f"기대={_fmt(row['ncs_expected_competencies'])}; "
            f"매칭={_fmt(row['ncs_matched_competencies'])}; "
            f"미충족={_fmt(row['ncs_missing_competencies'])}"
        )
        lines.append(
            "| Q{order} | {ob:.2f}→{oa:.2f} ({od:+.2f}) | {hb:.2f}→{ha:.2f} ({hd:+.2f}) | "
            "{nb:.2f}→{na:.2f} ({nd:+.2f}) | {sb:.2f}→{sa:.2f} ({sd:+.2f}) | {evidence} |".format(
                order=row["question_order"],
                ob=row["overall_before"],
                oa=row["overall_after"],
                od=row["overall_delta"],
                hb=row["humanization_before"],
                ha=row["humanization_after"],
                hd=row["humanization_delta"],
                nb=row["ncs_before"],
                na=row["ncs_after"],
                nd=row["ncs_delta"],
                sb=row["ssot_before"],
                sa=row["ssot_after"],
                sd=row["ssot_delta"],
                evidence=evidence,
            )
        )

    return {
        "minimum_samples": minimum_samples,
        "sample_count": sample_count,
        "minimum_sample_met": minimum_sample_met,
        "average_overall_delta": avg_overall_delta,
        "average_humanization_delta": avg_humanization_delta,
        "average_ncs_delta": avg_ncs_delta,
        "average_ssot_delta": avg_ssot_delta,
        "average_result_quality_delta": avg_result_quality_delta,
        "rows": rows,
        "markdown": "\n".join(lines),
    }


def _average_result_quality_score(
    result_quality_evaluations: list[dict[str, Any]] | None,
) -> float:
    if not result_quality_evaluations:
        return 0.0
    values: list[float] = []
    for item in result_quality_evaluations:
        try:
            values.append(float(item.get("overall", 0.0)))
        except (TypeError, ValueError, AttributeError):
            continue
    return sum(values) / len(values) if values else 0.0


def should_accept_writer_rewrite(
    candidate_validation: ValidationResult,
    current_quality_evaluations: list[dict[str, Any]],
    candidate_quality_evaluations: list[dict[str, Any]],
    current_result_quality_evaluations: list[dict[str, Any]] | None = None,
    candidate_result_quality_evaluations: list[dict[str, Any]] | None = None,
) -> bool:
    if not candidate_validation.passed:
        return False

    old_avg = (
        sum(
            float(item.get("overall_score", 0.0))
            for item in current_quality_evaluations
        )
        / len(current_quality_evaluations)
        if current_quality_evaluations
        else 0.0
    )
    new_avg = (
        sum(
            float(item.get("overall_score", 0.0))
            for item in candidate_quality_evaluations
        )
        / len(candidate_quality_evaluations)
        if candidate_quality_evaluations
        else 0.0
    )
    old_result_avg = _average_result_quality_score(current_result_quality_evaluations)
    new_result_avg = _average_result_quality_score(candidate_result_quality_evaluations)

    if new_avg > old_avg:
        return True
    if new_avg == old_avg and new_result_avg >= old_result_avg:
        return True
    if new_avg >= old_avg and new_result_avg > old_result_avg:
        return True
    return False


def build_writer_rewrite_prompt(
    previous_output: str,
    validation: ValidationResult,
    quality_evaluations: list[dict[str, Any]],
    result_quality_evaluations: list[dict[str, Any]] | None = None,
    char_limit_report: dict[str, Any] | None = None,
    feedback_learning: dict[str, Any] | None = None,
    candidate_profile: dict[str, Any] | None = None,
    writer_brief: dict[str, Any] | None = None,
    focus_mode: str = "full",
) -> str:
    issues: list[str] = []
    char_only_mode = focus_mode == "char_limit"
    length_first_section = ""
    if char_only_mode:
        length_first_section = (
            "# LENGTH-FIRST MODE\n"
            "- 이번 재작성의 1순위는 각 문항 본문을 제한 대비 90~97% 범위로 맞추는 것이다.\n"
            "- 분량이 부족한 문항은 새 사실을 만들지 말고 기존 행동, 판단 기준, 개인 기여, 결과 연결을 더 구체적으로 풀어 써라.\n"
            "- 다른 품질 축보다 글자수 강제조건을 우선 충족하라.\n"
        )
    if validation.missing:
        issues.append("형식/계약 누락: " + ", ".join(validation.missing))
    if not char_only_mode:
        for item in quality_evaluations:
            overall = float(item.get("overall_score", 0.0))
            humanization_flags = item.get("humanization_flags", [])[:3]
            humanization_suggestions = item.get("humanization_suggestions", [])[:3]

            if overall < 0.72 or humanization_flags:
                weaknesses = item.get("weaknesses", [])[:3]
                suggestions = item.get("suggestions", [])[:3]
                issues.append(
                    f"Q{item.get('question_order', '?')} 품질점수 {overall:.2f} / 약점: "
                    + ", ".join(weaknesses or ["불명확"])
                )
                if suggestions:
                    issues.append(
                        f"Q{item.get('question_order', '?')} 개선지시: "
                        + ", ".join(suggestions)
                    )
            if humanization_flags:
                issues.append(
                    f"Q{item.get('question_order', '?')} 인간화 이슈: "
                    + ", ".join(humanization_flags)
                )
            if humanization_suggestions:
                issues.append(
                    f"Q{item.get('question_order', '?')} 자연화 지시: "
                    + ", ".join(humanization_suggestions)
                )
            interviewer_checklist = item.get("interviewer_checklist", [])[:3]
            if interviewer_checklist:
                issues.append(
                    f"Q{item.get('question_order', '?')} 면접관 체크: "
                    + " / ".join(interviewer_checklist)
                )
            expected_followups = item.get("expected_followups", [])[:3]
            if expected_followups:
                issues.append(
                    f"Q{item.get('question_order', '?')} 예상 꼬리질문: "
                    + " / ".join(expected_followups)
                )
            defense_gaps = item.get("defense_gaps", [])[:3]
            if defense_gaps:
                issues.append(
                    f"Q{item.get('question_order', '?')} 방어 취약점: "
                    + " / ".join(defense_gaps)
                )
            committee_attack_points = item.get("committee_attack_points", [])[:3]
            if committee_attack_points:
                issues.append(
                    f"Q{item.get('question_order', '?')} 위원회 예상 공격: "
                    + " / ".join(committee_attack_points)
                )
            message_discipline_score = float(item.get("message_discipline_score", 1.0))
            if message_discipline_score < 0.72:
                issues.append(
                    f"Q{item.get('question_order', '?')} 메시지 축 흔들림({message_discipline_score:.2f}): "
                    + " / ".join(item.get("message_competing_points", [])[:3])
                )
            cliche_flags = item.get("cliche_flags", [])[:3]
            if cliche_flags:
                issues.append(
                    f"Q{item.get('question_order', '?')} 클리셰 차단 필요: "
                    + ", ".join(cliche_flags)
                )
            differentiation_score = float(item.get("differentiation_score", 1.0))
            if differentiation_score < 0.62:
                issues.append(
                    f"Q{item.get('question_order', '?')} 차별화 부족({differentiation_score:.2f}): "
                    + ", ".join(item.get("differentiation_gaps", [])[:3] or ["차별화 문장이 약합니다."])
                )
            ncs_missing = item.get("ncs_missing_competencies", [])[:3]
            ncs_expected = item.get("ncs_expected_competencies", [])[:3]
            ncs_matched = item.get("ncs_matched_competencies", [])[:3]
            ncs_suggestions = item.get("ncs_suggestions", [])[:3]
            ncs_score = float(item.get("ncs_alignment_score", 1.0))
            if ncs_expected:
                issues.append(
                    f"Q{item.get('question_order', '?')} JD/NCS 매칭 근거: "
                    f"기대역량={', '.join(ncs_expected)} / "
                    f"현재매칭={', '.join(ncs_matched) if ncs_matched else '없음'} / "
                    f"미충족={', '.join(ncs_missing) if ncs_missing else '없음'}"
                )
            if ncs_missing and ncs_score < 0.6:
                issues.append(
                    f"Q{item.get('question_order', '?')} NCS 정합성 부족({ncs_score:.2f}): "
                    + ", ".join(ncs_missing)
                )
            if ncs_suggestions:
                issues.append(
                    f"Q{item.get('question_order', '?')} NCS 보강지시: "
                    + ", ".join(ncs_suggestions)
                )
            ncs_missing_units = item.get("ncs_missing_ability_units", [])[:3]
            if ncs_missing_units:
                issues.append(
                    f"Q{item.get('question_order', '?')} 능력단위 보강: "
                    + ", ".join(ncs_missing_units)
                )
    if not char_only_mode:
        for item in result_quality_evaluations or []:
            overall = float(item.get("overall", 1.0))
            details = item.get("details", {})
            low_dimensions = [
                f"{key}={float(value):.2f}"
                for key, value in details.items()
                if float(value) < 0.7
            ]
            if overall < 0.72 or low_dimensions:
                issues.append(
                    f"Q{item.get('question_order', '?')} 결과중심 품질 {overall:.2f}"
                )
            if low_dimensions:
                issues.append(
                    f"Q{item.get('question_order', '?')} 결과중심 보강축: "
                    + ", ".join(low_dimensions[:4])
                )
            suggestions = item.get("suggestions", [])[:3]
            if suggestions:
                issues.append(
                    f"Q{item.get('question_order', '?')} 결과중심 개선지시: "
                    + ", ".join(suggestions)
                )
            ssot_missing = item.get("ssot_missing_claims", [])[:3]
            ssot_offtrack = item.get("ssot_offtrack_signals", [])[:3]
            ssot_suggestions = item.get("ssot_suggestions", [])[:3]
            ssot_score = float(item.get("ssot_alignment_score", 1.0))
            if ssot_missing and ssot_score < 0.55:
                issues.append(
                    f"Q{item.get('question_order', '?')} 공통 서사 정합성 부족({ssot_score:.2f}): "
                    + ", ".join(ssot_missing)
                )
            if ssot_offtrack:
                issues.append(
                    f"Q{item.get('question_order', '?')} 서사 이탈 신호: "
                    + " / ".join(ssot_offtrack)
                )
            if ssot_suggestions:
                issues.append(
                    f"Q{item.get('question_order', '?')} 서사 보강지시: "
                    + " / ".join(ssot_suggestions)
                )

    if char_limit_report:
        for item in char_limit_report.get("question_reports", []):
            status = item.get("status")
            if status in {
                "over_limit",
                "under_target",
                "over_target",
                "missing_answer",
            }:
                issues.append(
                    f"Q{item.get('question_order', '?')} 글자수 강제조건: "
                    f"현재 {item.get('char_count', 0)}자 / 제한 {item.get('char_limit', 'N/A')}자 / "
                    f"목표 {int(float(item.get('target_min', 0.9)) * 100)}~{int(float(item.get('target_max', 0.97)) * 100)}% / 상태 {status}"
                )

    if feedback_learning and not char_only_mode:
        rejection_comments = feedback_learning.get("recent_rejection_comments", [])[:3]
        improvement_areas = feedback_learning.get("insights", {}).get(
            "improvement_areas", []
        )[:3]
        adaptation_actions = (
            feedback_learning.get("adaptation_plan", {}).get("focus_actions", [])[:3]
        )
        if rejection_comments:
            issues.append(
                "최근 거절 코멘트 재발 방지: " + " / ".join(rejection_comments)
            )
        if improvement_areas:
            issues.append("피드백 기반 개선영역: " + " / ".join(improvement_areas))
        if adaptation_actions:
            issues.append("학습 루프 우선 과제: " + " / ".join(adaptation_actions))
        strategy_outcome_summary = feedback_learning.get("strategy_outcome_summary")
        question_experience_map = feedback_learning.get("question_experience_map", [])
        current_pattern = feedback_learning.get("current_pattern")
        strategy_issues: list[str] = []
        for item in question_experience_map:
            strategy_issue = _build_strategy_outcome_issue(
                question_order=item.get("question_order") or "?",
                question_type=str(item.get("question_type") or ""),
                experience_id=str(item.get("experience_id") or ""),
                strategy_outcome_summary=strategy_outcome_summary,
                current_pattern=current_pattern,
            )
            if strategy_issue:
                strategy_issues.append(strategy_issue)
        if strategy_issues:
            issues.extend(strategy_issues[:4])
    if candidate_profile:
        summary = candidate_profile.get("profile_summary", "")
        focus = candidate_profile.get("coaching_focus", [])[:3]
        if summary:
            issues.append("지원자 프로필 요약: " + summary)
        if focus:
            issues.append("지원자 맞춤 코칭 포인트: " + " / ".join(focus))
    if writer_brief:
        for item in writer_brief.get("question_strategies", [])[:4]:
            issues.append(
                f"Q{item.get('question_order', '?')} writer contract: "
                f"핵심메시지={item.get('core_message', '')} / "
                f"winning={item.get('winning_angle', '')} / "
                f"금지={', '.join(item.get('forbidden_points', [])[:2])}"
            )

    return f"""
# QUALITY REWRITE TASK
이전 writer 결과를 같은 4블록 형식을 유지한 채 더 강하게 다시 작성하라.

{length_first_section}

# MUST FIX
{chr(10).join(f"- {item}" for item in issues) or "- 계약 형식과 품질 기준을 다시 점검하라."}

# HARD RULES
- 기존 DATA 범위를 벗어난 사실을 추가하지 않는다.
- 문항별 글자수 표기를 반드시 유지한다.
- 각 문항 답변 본문은 공백 포함 실제 글자수 기준으로 제한을 절대 초과하지 않는다.
- 각 문항 답변 본문은 가능하면 제한 대비 90~97% 범위에 맞춘다.
- SELF-CHECK는 PASS/FAIL로 명시한다.
- 각 문항은 질문 의도에 직접 답해야 한다.
- 추상어 대신 행동, 수치, 개인 기여를 우선한다.
- 기계적인 도입부/상투 표현/관성적 마무리를 제거한다.
- 지원자 고유의 설명 습관과 강점을 유지하되 약한 부분만 보강한다.

# PREVIOUS OUTPUT
{previous_output}
""".strip()


def _build_strategy_outcome_issue(
    question_order: Any,
    question_type: str,
    experience_id: str,
    strategy_outcome_summary: dict[str, Any] | None,
    current_pattern: str | None = None,
) -> str | None:
    if not strategy_outcome_summary or not question_type or not experience_id:
        return None

    type_bucket = (
        strategy_outcome_summary.get("experience_stats_by_question_type", {}) or {}
    ).get(question_type, {})
    exp_bucket = type_bucket.get(experience_id)
    if not isinstance(exp_bucket, dict):
        return None

    bucket = exp_bucket
    if current_pattern:
        pattern_bucket = (exp_bucket.get("pattern_breakdown", {}) or {}).get(
            current_pattern
        )
        if (
            isinstance(pattern_bucket, dict)
            and int(pattern_bucket.get("total_uses", 0)) > 0
        ):
            bucket = {**exp_bucket, **pattern_bucket}

    total_uses = int(bucket.get("total_uses", 0))
    if total_uses < 3:
        return None

    weighted_margin = int(bucket.get("weighted_net_score", 0))
    if weighted_margin >= 0:
        return None

    reasons = (
        bucket.get("top_rejection_reasons")
        or exp_bucket.get("top_rejection_reasons")
        or []
    )
    reason_hint = ""
    if reasons and isinstance(reasons[0], dict):
        reason_hint = reasons[0].get("reason", "")
    detail = (
        f"실제 결과 통계 경고: Q{question_order}에 현재 경험은 {question_type} 문항에서 "
        f"실패 비중이 높습니다"
    )
    if reason_hint:
        detail += f" (주요 사유: {reason_hint})"
    return detail
