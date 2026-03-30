from __future__ import annotations

import json
import re
import shutil
import time
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
from .parsing import discover_public_urls, ingest_source_file, ingest_public_url
from .classifier import classify_question, classify_question_with_confidence
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
from .state import (
    initialize_state,
    load_artifacts,
    load_experiences,
    load_knowledge_sources,
    load_profile,
    load_project,
    save_project,
    save_knowledge_sources,
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

    for path in paths:
        if (
            path.is_file()
            and source_path
            and path.resolve().parent != ws.sources_raw_dir.resolve()
        ):
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
    write_json(summary_path, [item.model_dump() for item in merged])
    return {
        "source_count": len(ingested),
        "stored_count": len(merged),
        "summary": summary,
        "analysis_path": str(summary_path),
    }


def crawl_web_sources(ws: Workspace, urls: list[str]) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    ingested: List[KnowledgeSource] = []

    for url in urls:
        for source in ingest_public_url(url):
            write_source_artifacts(ws, source)
            ingested.append(source)

    merged = merge_sources(load_knowledge_sources(ws), ingested)
    save_knowledge_sources(ws, merged)
    summary = summarize_knowledge_sources(merged)
    summary_path = ws.analysis_dir / "knowledge_hints.json"
    write_json(summary_path, [item.model_dump() for item in merged])
    return {
        "source_count": len(ingested),
        "stored_count": len(merged),
        "summary": summary,
        "analysis_path": str(summary_path),
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
    return {
        "selected_experience_ids": selected_ids,
        "question_experience_map": mappings,
    }


def build_feedback_learning_context(
    ws: Workspace,
    artifact: str,
    project: ApplicationProject | None = None,
) -> dict[str, Any]:
    ws.ensure()
    project = project or load_project(ws)
    context = {
        "artifact": artifact,
        "total_feedback": 0,
        "recent_rejection_comments": [],
        "top_patterns": [],
        "recommended_pattern": None,
        "current_pattern": _build_feedback_pattern_id(artifact, project),
        "question_experience_map": _build_feedback_selection_payload(
            read_json_if_exists(ws.analysis_dir / "question_map.json")
        ).get("question_experience_map", []),
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
        top_patterns = recommendations[:5] or [
            {
                "pattern_id": item.pattern_id,
                "success_rate": item.success_rate,
                "avg_rating": item.avg_rating,
                "total_uses": item.total_uses,
            }
            for item in learner.db.get_top_patterns(10)
            if str(item.pattern_id).startswith(f"{artifact}|")
        ][:5]
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
                "outcome_summary": learner.get_context_outcome_summary(
                    similar_context
                ),
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
    except Exception as e:
        logger.debug(f"피드백 학습 컨텍스트 생성 건너뜀: {e}")

    out_path = ws.analysis_dir / f"{artifact}_feedback_learning.json"
    write_json(out_path, context)
    return context


def build_candidate_profile(
    ws: Workspace,
    project: ApplicationProject,
    experiences: List[Experience],
) -> dict[str, Any]:
    profile = load_profile(ws)
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
        blind_spots.append("팀 성과는 보이지만 본인 판단과 책임 범위가 흐릴 수 있습니다.")
    if communication_style == "logical":
        coaching_focus.append("강한 분석형 톤은 유지하되 고객·협업 맥락을 더 드러내세요.")
    elif communication_style == "relational":
        coaching_focus.append("관계 중심 설명은 강점이지만 근거 수치와 판단 기준을 함께 제시하세요.")
    else:
        coaching_focus.append("균형형 답변이 강점이므로 핵심 메시지를 더 빠르게 압축하세요.")
    if abstraction_ratio > 0.55:
        blind_spots.append("추상 표현 비중이 높아 구체 행동과 결과가 약해질 수 있습니다.")
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
    write_json(ws.analysis_dir / "candidate_profile.json", candidate_profile)
    return candidate_profile


def build_narrative_ssot(
    ws: Workspace,
    project: ApplicationProject,
    experiences: List[Experience],
    *,
    question_map: list[dict[str, Any]] | None = None,
    company_analysis: CompanyAnalysis | None = None,
) -> dict[str, Any]:
    question_map = question_map or read_json_if_exists(ws.analysis_dir / "question_map.json")
    committee_feedback = build_committee_feedback_context(ws)
    self_intro_pack = read_json_if_exists(ws.analysis_dir / "self_intro_pack.json") or {}
    prioritized = select_primary_experiences(experiences, question_map)[:3]
    evidence_titles = [item.title for item in prioritized]
    claims = _dedupe_preserve_order(
        [
            f"{project.job_title or '지원 직무'}에 바로 투입 가능한 검증형 실무자",
            f"{project.company_name or '지원 기관'}에 맞는 근거 중심 문제해결형 지원자",
            *(self_intro_pack.get('focus_keywords', [])[:2] if isinstance(self_intro_pack, dict) else []),
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
    source_grading = source_grading or read_json_if_exists(ws.analysis_dir / "source_grading.json")
    cross_check = (source_grading or {}).get("cross_check", {}) if isinstance(source_grading, dict) else {}
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
            + (getattr(company_analysis, "taboo_phrases", [])[:3] if company_analysis else [])
        )[:5],
        "essay_usefulness_score": max(0.2, min(0.95, round(0.85 - (single_source * 0.1) - (missing_count * 0.12), 2))),
        "translation_notes": [
            "단일 출처에만 기대는 회사 정보는 자소서 주장보다 보조 근거로 사용합니다." if single_source else "핵심 회사 신호는 자소서 첫 문단과 면접 1분 답변에 공통으로 반영합니다.",
            "근거가 부족한 영역은 [NEEDS_VERIFICATION]로 분리하고 확정 표현을 피합니다." if missing_count else "교차검증된 신호를 지원동기와 직무적합성 문항에 우선 반영합니다.",
        ],
    }
    write_json(ws.analysis_dir / "research_strategy_translation.json", translation)
    return translation


def build_outcome_dashboard(
    ws: Workspace,
    project: ApplicationProject,
    artifact_type: str = "writer",
) -> dict[str, Any]:
    feedback_learning = build_feedback_learning_context(ws, artifact_type, project=project)
    strategy_summary = feedback_learning.get("strategy_outcome_summary", {})
    top_hotspots: list[dict[str, Any]] = []
    for q_type, exp_map in (strategy_summary.get("experience_stats_by_question_type", {}) or {}).items():
        for exp_id, stats in exp_map.items():
            top_hotspots.append(
                {
                    "question_type": q_type,
                    "experience_id": exp_id,
                    "weighted_net_score": int(stats.get("weighted_net_score", 0)),
                    "total_uses": int(stats.get("total_uses", 0)),
                }
            )
    top_hotspots.sort(key=lambda item: (item["weighted_net_score"], -item["total_uses"]))
    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_type": artifact_type,
        "current_pattern": feedback_learning.get("current_pattern"),
        "overall_success_rate": feedback_learning.get("overall_success_rate", 0),
        "outcome_summary": feedback_learning.get("outcome_summary", {}),
        "recommended_pattern": feedback_learning.get("recommended_pattern"),
        "high_risk_hotspots": top_hotspots[:5],
    }
    write_json(ws.analysis_dir / "outcome_dashboard.json", dashboard)
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
    if experience and expected_experience_ids and experience.id not in expected_experience_ids:
        offtrack_signals.append("공통 서사에서 우선 선정되지 않은 경험을 사용하고 있습니다.")
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
        suggestions.append("공통 서사의 핵심 주장 중 최소 1개를 문장 전면에 다시 드러내세요.")
    if offtrack_signals:
        suggestions.append("자소서·자기소개·면접의 공통 근거 경험과 답변 앵커를 더 일치시키세요.")

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
    trust = "high" if any(char.isdigit() for char in answer) or (experience and experience.evidence_text.strip()) else "medium"
    if len(simulation.get("risk_areas", [])) >= 3:
        trust = "medium" if trust == "high" else "low"
    specificity = "high" if len(answer) >= 80 and any(char.isdigit() for char in answer) else "medium"
    if len(answer) < 50:
        specificity = "low"
    next_probe = (
        simulation.get("follow_up_questions", ["왜 그렇게 판단했는지 다시 설명해주세요."])[0]
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
        "persona_panel": _dedupe_preserve_order([item for item in personas if item])[:6],
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
    write_json(ws.analysis_dir / "self_intro_pack.json", intro_pack)
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
            discovered.extend(
                discover_public_urls(query, limit=max_results_per_query)
            )
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
        "keywords": ["소통", "설명", "문서", "보고", "회의", "민원", "고객", "경청", "표현", "안내"],
        "question_types": ["TYPE_A", "TYPE_C", "TYPE_H"],
    },
    "수리능력": {
        "keywords": ["통계", "지표", "수치", "분석", "엑셀", "정산", "계산", "검증", "도표", "sql"],
        "question_types": ["TYPE_B", "TYPE_G"],
    },
    "문제해결능력": {
        "keywords": ["문제", "해결", "개선", "위기", "대응", "수습", "자동화", "대안", "조치"],
        "question_types": ["TYPE_B", "TYPE_G", "TYPE_I"],
    },
    "자기관리능력": {
        "keywords": ["학습", "성장", "개선", "적응", "피드백", "시간관리", "습관", "꾸준"],
        "question_types": ["TYPE_D", "TYPE_F"],
    },
    "자원관리능력": {
        "keywords": ["예산", "시간", "우선순위", "자원", "인력", "관리", "배분", "절감"],
        "question_types": ["TYPE_B", "TYPE_E"],
    },
    "대인관계능력": {
        "keywords": ["협업", "팀", "갈등", "설득", "조율", "협상", "고객서비스", "중재"],
        "question_types": ["TYPE_C", "TYPE_H"],
    },
    "정보능력": {
        "keywords": ["자료", "정보", "검색", "출처", "비교", "정리", "리서치", "검토"],
        "question_types": ["TYPE_B", "TYPE_D"],
    },
    "기술능력": {
        "keywords": ["시스템", "도구", "기술", "활용", "프로그램", "업무도구", "디지털"],
        "question_types": ["TYPE_B", "TYPE_E"],
    },
    "조직이해능력": {
        "keywords": ["조직", "행정", "공공", "기관", "업무이해", "규정", "절차", "정책"],
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
        question_map
        or read_json_if_exists(ws.analysis_dir / "question_map.json")
        or []
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
                for marker in ["직무기술서", "능력단위", "능력단위요소", "직업기초능력", "직업공통능력"]
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
            if any(signal in lower_keyword or lower_keyword in signal for signal in keywords):
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
        key=lambda item: (-item["score"], -len(item["matched_experience_ids"]), item["name"])
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

    q_type = question_type.value if hasattr(question_type, "value") else str(question_type)
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
        keywords = [kw.lower() for kw in NCS_COMMON_COMPETENCY_SIGNALS[competency]["keywords"]]
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
        if unit_compact in answer_compact or any(token in answer_blob for token in unit_tokens):
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
        key_questions.append("현재 자소서 문항별로 어떤 경험과 근거를 우선 연결해야 하는가?")
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
    }
    write_json(ws.analysis_dir / "research_brief.json", brief)
    return brief


def _grade_source_reliability(source: KnowledgeSource) -> tuple[str, str]:
    if source.source_type == SourceType.USER_URL_PUBLIC:
        parsed = urlparse(source.url or "")
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        if any(host.endswith(suffix) for suffix in [".go.kr", ".gov", ".ac.kr", ".edu", ".or.kr"]):
            return "B", "공공기관/교육기관/비영리 공식 도메인입니다."
        if any(token in host for token in ["reddit", "blind", "tistory", "blog", "naver", "brunch"]):
            return "E", "포럼·블로그 계열 도메인이라 참고용으로만 쓰는 편이 안전합니다."
        if any(token in path for token in ["/careers", "/jobs", "/recruit", "/about", "/company", "/news"]):
            return "B", "회사 공식 채용/소개/보도 자료 성격의 페이지일 가능성이 높습니다."
        return "C", "공개 웹 자료이지만 공식성 여부가 명확하지 않아 보조 근거로 보는 편이 안전합니다."
    if source.source_type in {
        SourceType.LOCAL_MARKDOWN,
        SourceType.LOCAL_TEXT,
        SourceType.LOCAL_CSV_ROW,
    }:
        return "C", "사용자 제공 로컬 자료로 실무 활용도는 높지만 외부 교차검증이 추가되면 더 안전합니다."
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
    company_terms = _tokenize_research_terms(
        f"{project.company_name} {project.job_title} {project.company_type}"
    )[:6]

    key_areas = [
        {
            "area": "company_fit",
            "keywords": _dedupe_preserve_order(company_terms + ["조직", "사업", "가치", "문화"]),
        },
        {
            "area": "role_requirements",
            "keywords": _dedupe_preserve_order(jd_keywords[:6] + question_terms[:3]),
        },
        {
            "area": "essay_alignment",
            "keywords": _dedupe_preserve_order(question_terms + ["지원동기", "직무역량", "입사후포부"]),
        },
        {
            "area": "interview_risks",
            "keywords": _dedupe_preserve_order(question_terms + ["꼬리질문", "방어", "경험", "근거"]),
        },
    ]

    source_tokens: dict[str, list[str]] = {}
    assessments: list[dict[str, Any]] = []
    for source in sources:
        tokens = _tokenize_research_terms(f"{source.title}\n{source.cleaned_text}")[:30]
        source_tokens[source.id] = tokens
        grade, rationale = _grade_source_reliability(source)
        supporting_areas = [
            area["area"]
            for area in key_areas
            if set(tokens) & set(area["keywords"])
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
            }
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

    if not enabled or not uncertain_questions:
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
    exit_code = run_codex(prompt_path, ws.root, output_path, tool=tool)
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
        project = classify_project_questions_with_llm_fallback(ws, project, enabled=True)
        save_project(ws, project)
        experiences = load_experiences(ws)
        progress.step("프로젝트/경험 로드", status="success")

        gap_report = analyze_gaps(project, experiences)
        feedback_learning = build_feedback_learning_context(ws, "coach", project=project)
        artifact = build_coach_artifact(
            project,
            experiences,
            gap_report,
            outcome_summary=feedback_learning.get("outcome_summary"),
            strategy_outcome_summary=feedback_learning.get("strategy_outcome_summary"),
            current_pattern=feedback_learning.get("current_pattern"),
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
        },
        status="success" if validation.passed else "failed",
        error=", ".join(validation.missing[:5]) if validation.missing else None,
    )

    return {
        "artifact": artifact,
        "validation": validation.model_dump(),
        "path": str(coach_path),
        "prompt_path": str(coach_prompt_path),
    }


def run_writer(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    prompt_path = build_draft_prompt(ws, ws.targets_dir / "example_target.md")
    return {"prompt_path": str(prompt_path)}


def run_writer_with_codex(ws: Workspace, tool: str = "codex") -> dict[str, Any]:
    with StepProgress("Writer 파이프라인") as progress:
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
                )
                logger.info(
                    f"Company analysis completed: {project.company_name} ({company_analysis.company_type})"
                )
            except Exception as e:
                logger.warning(f"Company analysis failed: {e}")
        progress.step("회사 분석", status="success")

        prompt_path = build_draft_prompt(
            ws, ws.targets_dir / "example_target.md", company_analysis=company_analysis
        )
        run_dir = ws.runs_dir / timestamp_slug()
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_output_path = run_dir / "raw_writer.md"
        progress.step("프롬프트 빌드", status="success")

        exit_code = run_codex(prompt_path, ws.root, raw_output_path, tool=tool)
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

        accepted_path = ws.artifacts_dir / "writer.md"
        writer_quality_path = ws.artifacts_dir / "writer_quality.json"

        experiences = load_experiences(ws)
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

            exit_code = run_codex(temp_prompt_path, ws.root, corrected_output_path)
            if exit_code == 0:
                normalized_text = safe_read_text(corrected_output_path)
                fact_warnings = audit_facts(normalized_text, experiences)
                logger.info("Self-correction completed.")

        quality_evaluations = []
        question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
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
        if company_analysis and normalized_text:
            try:
                quality_evaluations = build_writer_quality_evaluations(
                    project=project,
                    writer_text=normalized_text,
                    experiences=experiences,
                    question_map=question_map,
                    company_analysis=company_analysis,
                    ncs_profile=ncs_profile,
                    narrative_ssot=narrative_ssot,
                )
                for quality in quality_evaluations:
                    logger.info(
                        f"Answer quality for Q{quality['question_order']}: {quality['overall_score']:.2f}"
                    )
            except Exception as e:
                logger.warning(f"Answer quality evaluation failed: {e}")

        if exit_code == 0 and needs_writer_rewrite(validation, quality_evaluations):
            logger.warning("Writer quality below threshold. Attempting targeted rewrite.")
            rewrite_prompt = build_writer_rewrite_prompt(
                previous_output=normalized_text,
                validation=validation,
                quality_evaluations=quality_evaluations,
                feedback_learning=build_feedback_learning_context(
                    ws, "writer", project=project
                ),
                candidate_profile=build_candidate_profile(ws, project, experiences),
            )
            rewrite_dir = ws.runs_dir / f"rewrite_{timestamp_slug()}"
            rewrite_dir.mkdir(parents=True, exist_ok=True)
            rewrite_prompt_path = rewrite_dir / "rewrite_prompt.md"
            rewrite_prompt_path.write_text(rewrite_prompt, encoding="utf-8")
            rewritten_output_path = rewrite_dir / "rewritten_writer.md"
            rewrite_exit_code = run_codex(rewrite_prompt_path, ws.root, rewritten_output_path)
            if rewrite_exit_code == 0:
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
                candidate_quality = build_writer_quality_evaluations(
                    project=project,
                    writer_text=candidate_text,
                    experiences=experiences,
                    question_map=question_map,
                    company_analysis=company_analysis,
                    ncs_profile=ncs_profile,
                    narrative_ssot=narrative_ssot,
                )
                old_avg = (
                    sum(float(item.get("overall_score", 0.0)) for item in quality_evaluations)
                    / len(quality_evaluations)
                    if quality_evaluations
                    else 0.0
                )
                new_avg = (
                    sum(float(item.get("overall_score", 0.0)) for item in candidate_quality)
                    / len(candidate_quality)
                    if candidate_quality
                    else 0.0
                )
                if candidate_validation.passed and new_avg >= old_avg:
                    normalized_text = candidate_text
                    validation = candidate_validation
                    quality_evaluations = candidate_quality
                    logger.info(
                        f"Writer rewrite accepted: quality {old_avg:.2f} -> {new_avg:.2f}"
                    )

        readability = calculate_readability_score(normalized_text)
        progress.step(
            "검증/품질 평가", status="success" if validation.passed else "failed"
        )

        if fact_warnings:
            for w in fact_warnings:
                logger.warning(w)

        logger.info(f"Readability Score: {readability['score']}/100")
        for fb in readability["feedback"]:
            if readability["score"] < 100:
                logger.warning(f"Readability feedback: {fb}")

        if validation.passed:
            accepted_path.write_text(normalized_text, encoding="utf-8")
        write_json(writer_quality_path, quality_evaluations)

    snapshot = GeneratedArtifact(
        id=f"writer-{timestamp_slug()}",
        artifact_type=ArtifactType.WRITER,
        accepted=validation.passed,
        input_snapshot={
            "project": load_project(ws).model_dump(),
            "question_map_path": str(
                (ws.analysis_dir / "question_map.json").relative_to(ws.root)
            ),
            "fact_warnings": fact_warnings,
            "readability": readability,
            "company_analysis": company_analysis.model_dump()
            if company_analysis
            else None,
            "quality_evaluations": quality_evaluations,
            "writer_quality_path": str(writer_quality_path.relative_to(ws.root)),
        },
        output_path=str(accepted_path.relative_to(ws.root)),
        raw_output_path=str(raw_output_path.relative_to(ws.root)),
        validation=validation,
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)
    write_json(
        run_dir / "writer.json",
        {
            "validation": validation.model_dump(),
            "exit_code": exit_code,
            "quality_evaluations": quality_evaluations,
        },
    )

    cp_mgr = CheckpointManager(ws.root)
    cp_mgr.save_checkpoint(
        "writer",
        {
            "artifact_path": str(accepted_path.relative_to(ws.root)),
            "validation": validation.model_dump(),
            "fact_warnings": fact_warnings,
            "readability": readability,
            "quality_evaluations": quality_evaluations,
            "writer_quality_path": str(writer_quality_path.relative_to(ws.root)),
        },
        status="success" if validation.passed else "failed",
        error=", ".join(validation.missing[:5]) if validation.missing else None,
    )

    # 피드백 학습 루프: 검증 결과를 자동 피드백으로 기록
    try:
        from .feedback_learner import create_feedback_learner

        learner = create_feedback_learner(str(ws.root / "kb" / "feedback"))
        pattern = _build_feedback_pattern_id("writer", project)
        comment = None
        selection_payload = _build_feedback_selection_payload(question_map)
        low_quality = [
            item for item in quality_evaluations if float(item.get("overall_score", 0.0)) < 0.72
        ]
        if low_quality:
            weakest = low_quality[0]
            weaknesses = weakest.get("weaknesses", [])[:2]
            comment = ", ".join(weaknesses) if weaknesses else None
        learner.record_feedback(
            draft_id=f"writer-{timestamp_slug()}",
            pattern_used=pattern,
            accepted=validation.passed,
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
        )
        logger.info(f"Writer 피드백 자동 기록: {pattern}")
    except Exception as e:
        logger.debug(f"피드백 기록 건너뜀: {e}")

    return {
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "validation": validation.model_dump(),
        "exit_code": exit_code,
        "company_analysis": company_analysis.model_dump() if company_analysis else None,
        "quality_evaluations": quality_evaluations,
        "writer_quality_path": str(writer_quality_path),
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
            answer_map.get(question.id, "")
            for question in project.questions
        ]

    from .interview_engine import run_recursive_interview_chain

    deep_pack = run_recursive_interview_chain(
        ws.root, project, experiences, primary_questions, prepared_answers=prepared_answers
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
        raw_output_path=str((ws.analysis_dir / "self_intro_pack.json").relative_to(ws.root)),
        validation=ValidationResult(passed=True),
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)

    return {
        "path": str(out_path),
        "analysis_path": str(ws.analysis_dir / "self_intro_pack.json"),
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

        defense_simulations = []
        if normalized_text and project.questions:
            try:
                experiences = load_experiences(ws)
                question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
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
                    narrative_ssot=read_json_if_exists(ws.analysis_dir / "narrative_ssot.json"),
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
        progress.step("방어 시뮬레이션", status="success")

        if validation.passed:
            accepted_path.write_text(normalized_text, encoding="utf-8")
        write_json(defense_path, defense_simulations)
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
            rejection_reason=", ".join(committee_feedback.get("recurring_risks", [])[:2])
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
        outcome_dashboard = read_json_if_exists(ws.analysis_dir / "outcome_dashboard.json")

        export_md = "\n\n".join(
            [
                f"# Export Package\n\n- Company: {project.company_name}\n- Role: {project.job_title}",
                "## Narrative SSOT\n" + json.dumps(narrative_ssot or {}, ensure_ascii=False, indent=2),
                "## Outcome Dashboard\n" + json.dumps(outcome_dashboard or {}, ensure_ascii=False, indent=2),
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
    feedback_learning = build_feedback_learning_context(ws, "coach", project=project)
    artifact = coach_artifact or build_coach_artifact(
        project,
        experiences,
        gap_report or analyze_gaps(project, experiences),
        outcome_summary=feedback_learning.get("outcome_summary"),
        strategy_outcome_summary=feedback_learning.get("strategy_outcome_summary"),
        current_pattern=feedback_learning.get("current_pattern"),
    )
    company_analysis = None
    if project.company_name:
        try:
            company_analysis = analyze_company(
                company_name=project.company_name,
                job_title=project.job_title,
                company_type=project.company_type,
            )
        except Exception as e:
            logger.warning(f"Company analysis failed during coach prompt build: {e}")
    committee_feedback = build_committee_feedback_context(ws)
    self_intro_pack = build_self_intro_pack(ws, project, company_analysis=company_analysis)
    ncs_profile = build_ncs_profile(
        ws,
        project=project,
        experiences=experiences,
        company_analysis=company_analysis,
    )
    candidate_profile = build_candidate_profile(ws, project, experiences)
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

    hints = build_knowledge_hints(knowledge_sources, project)

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
                "narrative_ssot": narrative_ssot,
                "research_strategy_translation": research_strategy_translation,
                "outcome_dashboard": outcome_dashboard,
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


def build_draft_prompt(ws: Workspace, target_path: Path, company_analysis=None) -> Path:
    ws.ensure()
    project = load_project(ws)
    project = classify_project_questions_with_llm_fallback(ws, project, enabled=False)
    save_project(ws, project)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")

    hints = build_knowledge_hints(knowledge_sources, project)
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
    candidate_profile = build_candidate_profile(ws, project, experiences)
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

    extra = {
        "question_map": question_map,
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
        "narrative_ssot": narrative_ssot,
        "research_strategy_translation": research_strategy_translation,
        "outcome_dashboard": outcome_dashboard,
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
        "narrative_ssot": narrative_ssot,
        "research_strategy_translation": research_strategy_translation,
        "outcome_dashboard": outcome_dashboard,
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
        knowledge_hints=build_knowledge_hints(knowledge_sources, project),
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

    company_analysis = None
    if project.company_name:
        try:
            company_analysis = analyze_company(
                company_name=project.company_name,
                job_title=project.job_title,
                company_type=project.company_type,
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
    candidate_profile = build_candidate_profile(ws, project, experiences)
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

    data_block = build_data_block(
        project=project,
        experiences=experiences[:3],
        knowledge_hints=build_knowledge_hints(knowledge_sources, project),
        extra={
            "question_map": question_map,
            "jd_keywords": jd_keywords,
            "company_analysis": company_analysis.model_dump()
            if company_analysis
            else None,
            "research_notes": project.research_notes,
            "research_brief": brief,
            "source_grading": grading,
            "ncs_profile": ncs_profile,
            "candidate_profile": candidate_profile,
            "narrative_ssot": narrative_ssot,
            "research_strategy_translation": research_strategy_translation,
            "outcome_dashboard": outcome_dashboard,
        },
    )
    content = PROMPT_COMPANY_RESEARCH.format(data_block=data_block)
    out = ws.outputs_dir / "latest_company_research_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def run_company_research_with_codex(ws: Workspace, tool: str = "codex") -> dict[str, Any]:
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
            "corroborated_area_count": source_grading["cross_check"]["corroborated_area_count"],
            "single_source_area_count": source_grading["cross_check"]["single_source_area_count"],
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
    }


# _run_with_cli_tool, run_codex는 executor.py로 이동 (상단 import 참조)


# write_if_missing, normalize_example, relative는 utils.py로 이동 (상단 import 참조)


def collect_source_paths(ws: Workspace, source_path: Path | None) -> list[Path]:
    target = source_path or ws.sources_raw_dir
    if target.is_file():
        return [target]
    return sorted(path for path in target.iterdir() if path.is_file())


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
        chunk.strip()
        for chunk in split_pattern.split(draft_body)
        if chunk.strip()
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


def build_writer_quality_evaluations(
    project: ApplicationProject,
    writer_text: str,
    experiences: List[Experience],
    question_map: list[dict[str, Any]],
    company_analysis: CompanyAnalysis | None,
    ncs_profile: dict[str, Any] | None = None,
    narrative_ssot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not writer_text.strip() or not project.questions:
        return []

    evaluator = AnswerQualityEvaluator(company_analysis)
    simulator = DefenseSimulator(company_analysis)
    answer_map = extract_question_answer_map(writer_text, project.questions)
    experience_by_id = {item.id: item for item in experiences}
    map_by_question = {
        str(item.get("question_id")): item
        for item in question_map
        if item.get("question_id")
    }

    evaluations: list[dict[str, Any]] = []
    for question in project.questions:
        answer = answer_map.get(question.id, "")
        if not answer:
            continue
        mapped = map_by_question.get(question.id, {})
        experience = experience_by_id.get(str(mapped.get("experience_id", "")))
        quality = evaluator.evaluate(
            answer=answer,
            question=question.question_text,
            question_type=question.detected_type,
            experience=experience,
        )
        humanization = analyze_humanization(answer)
        payload = quality.model_dump()
        payload["question_order"] = question.order_no
        payload["question_text"] = question.question_text
        payload["experience_title"] = experience.title if experience else None
        payload["humanization_score"] = humanization["score"]
        payload["humanization_flags"] = humanization["flags"]
        payload["humanization_suggestions"] = humanization["suggestions"]
        ncs_alignment = evaluate_ncs_alignment(
            answer=answer,
            question_id=question.id,
            question_type=question.detected_type,
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
            question_type=question.detected_type,
            experiences=[experience] if experience else None,
        )
        payload["expected_followups"] = simulation.follow_up_questions[:3]
        payload["defense_gaps"] = simulation.risk_areas[:4]
        payload["interviewer_checklist"] = [
            "면접관이 수치와 비교 기준을 바로 물어도 30초 안에 답할 수 있는가",
            "팀 경험이라면 개인 기여와 판단 기준을 분리해 설명할 수 있는가",
            "왜 이 선택을 했는지와 그 선택이 보여주는 가치관까지 이어서 답할 수 있는가",
        ]
        evaluations.append(payload)
    return evaluations


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
    answer_map = extract_question_answer_map(writer_text, project.questions)
    experience_by_id = {item.id: item for item in experiences}
    map_by_question = {
        str(item.get("question_id")): item
        for item in question_map
        if item.get("question_id")
    }

    simulations: list[dict[str, Any]] = []
    for question in project.questions[:3]:
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
            question_type=question.detected_type,
            experiences=[experience] if experience else None,
        )
        ncs_alignment = evaluate_ncs_alignment(
            answer=answer,
            question_id=question.id,
            question_type=question.detected_type,
            ncs_profile=ncs_profile,
        )
        payload = simulation.model_dump()
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
        if question.detected_type and experience:
            historical_risk = _build_strategy_outcome_issue(
                question_order=question.order_no,
                question_type=question.detected_type.value,
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
        simulations.append(payload)
    return simulations


def needs_writer_rewrite(
    validation: ValidationResult,
    quality_evaluations: list[dict[str, Any]],
) -> bool:
    if not validation.passed:
        return True
    if not quality_evaluations:
        return False
    low_scores = [
        item for item in quality_evaluations if float(item.get("overall_score", 0.0)) < 0.72
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
    return bool(low_scores or low_humanization or low_ncs_alignment or low_ssot_alignment)


def build_writer_rewrite_prompt(
    previous_output: str,
    validation: ValidationResult,
    quality_evaluations: list[dict[str, Any]],
    feedback_learning: dict[str, Any] | None = None,
    candidate_profile: dict[str, Any] | None = None,
) -> str:
    issues: list[str] = []
    if validation.missing:
        issues.append("형식/계약 누락: " + ", ".join(validation.missing))
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
        ncs_missing = item.get("ncs_missing_competencies", [])[:3]
        ncs_suggestions = item.get("ncs_suggestions", [])[:3]
        ncs_score = float(item.get("ncs_alignment_score", 1.0))
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

    if feedback_learning:
        rejection_comments = feedback_learning.get("recent_rejection_comments", [])[:3]
        improvement_areas = feedback_learning.get("insights", {}).get(
            "improvement_areas", []
        )[:3]
        if rejection_comments:
            issues.append("최근 거절 코멘트 재발 방지: " + " / ".join(rejection_comments))
        if improvement_areas:
            issues.append("피드백 기반 개선영역: " + " / ".join(improvement_areas))
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

    return f"""
# QUALITY REWRITE TASK
이전 writer 결과를 같은 4블록 형식을 유지한 채 더 강하게 다시 작성하라.

# MUST FIX
{chr(10).join(f"- {item}" for item in issues) or "- 계약 형식과 품질 기준을 다시 점검하라."}

# HARD RULES
- 기존 DATA 범위를 벗어난 사실을 추가하지 않는다.
- 문항별 글자수 표기를 반드시 유지한다.
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
        pattern_bucket = (exp_bucket.get("pattern_breakdown", {}) or {}).get(current_pattern)
        if isinstance(pattern_bucket, dict) and int(pattern_bucket.get("total_uses", 0)) > 0:
            bucket = {**exp_bucket, **pattern_bucket}

    total_uses = int(bucket.get("total_uses", 0))
    if total_uses < 3:
        return None

    weighted_margin = int(bucket.get("weighted_net_score", 0))
    if weighted_margin >= 0:
        return None

    reasons = bucket.get("top_rejection_reasons") or exp_bucket.get("top_rejection_reasons") or []
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
