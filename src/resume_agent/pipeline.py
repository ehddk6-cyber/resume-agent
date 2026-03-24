from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from .logger import get_logger
logger = get_logger("pipeline")

from .domain import (
    analyze_gaps,
    auto_classify_project_questions,
    build_knowledge_hints,
    build_coach_artifact,
    ingest_source_file,
    summarize_knowledge_sources,
    validate_block_contract,
    validate_coach_contract,
    validate_writer_contract,
    validate_interview_contract,
    calculate_readability_score,
    audit_facts,
)
from .models import (
    ApplicationProject,
    ArtifactType,
    Experience,
    GeneratedArtifact,
    KnowledgeSource,
    QuestionType,
    ValidationResult,
    CompanyAnalysis,
    SuccessCase,
)
from .company_analyzer import analyze_company, CompanyAnalyzer
from .answer_quality import evaluate_answer_quality, AnswerQualityEvaluator
from .defense_simulator import simulate_interview_defense, DefenseSimulator
from .state import (
    initialize_state,
    load_artifacts,
    load_experiences,
    load_knowledge_sources,
    load_project,
    save_project,
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


def crawl_base(ws: Workspace, source_path: Path | None = None) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    paths = collect_source_paths(ws, source_path)
    ingested: List[KnowledgeSource] = []

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
    write_json(summary_path, [item.model_dump() for item in merged])
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
    auto_classify_project_questions(project)
    save_project(ws, project)
    experiences = load_experiences(ws)
    report = analyze_gaps(project, experiences)
    path = ws.analysis_dir / "gap_report.json"
    write_json(path, report)
    return {"report": report, "path": str(path)}


def run_coach(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    auto_classify_project_questions(project)
    save_project(ws, project)
    experiences = load_experiences(ws)
    gap_report = analyze_gaps(project, experiences)
    artifact = build_coach_artifact(project, experiences, gap_report)
    validation_dict = validate_coach_contract(artifact["rendered"])
    validation = ValidationResult(passed=validation_dict["passed"], missing=validation_dict["missing"])

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
    write_json(run_dir / "coach.json", {"artifact": artifact, "validation": validation.model_dump()})
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


def run_writer_with_codex(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    
    # [linkareer 개선] 회사 분석 수행
    project = load_project(ws)
    company_analysis = None
    if project.company_name:
        try:
            company_analysis = analyze_company(
                company_name=project.company_name,
                job_title=project.job_title,
                company_type=project.company_type,
            )
            logger.info(f"Company analysis completed: {project.company_name} ({company_analysis.company_type})")
        except Exception as e:
            logger.warning(f"Company analysis failed: {e}")
    
    prompt_path = build_draft_prompt(ws, ws.targets_dir / "example_target.md")
    run_dir = ws.runs_dir / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = run_dir / "raw_writer.md"
    exit_code = run_codex(prompt_path, ws.root, raw_output_path)
    headings = [
        "## 블록 1: ASSUMPTIONS & MISSING FACTS",
        "## 블록 2: OUTLINE",
        "## 블록 3: DRAFT ANSWERS",
        "## 블록 4: SELF-CHECK",
    ]
    raw_text = safe_read_text(raw_output_path)
    normalized_text = normalize_contract_output(raw_text, headings)
    validation_dict = validate_writer_contract(normalized_text)
    validation = ValidationResult(passed=validation_dict["passed"], missing=validation_dict["missing"])

    accepted_path = ws.artifacts_dir / "writer.md"
    
    # 추가 검증: 가독성 및 팩트 오딧
    experiences = load_experiences(ws)
    fact_warnings = audit_facts(normalized_text, experiences)
    
    # [linkareer 개선] 답변 품질 평가 수행
    quality_evaluations = []
    if company_analysis and normalized_text:
        try:
            evaluator = AnswerQualityEvaluator(company_analysis)
            # 블록 3에서 답변 추출 시도
            answer_section = ""
            if "## 블록 3: DRAFT ANSWERS" in normalized_text:
                parts = normalized_text.split("## 블록 3: DRAFT ANSWERS")
                if len(parts) > 1:
                    answer_section = parts[1].split("## 블록 4:")[0] if "## 블록 4:" in parts[1] else parts[1]
            
            if answer_section and project.questions:
                for q in project.questions[:3]:  # 최대 3개 질문만 평가
                    quality = evaluator.evaluate(
                        answer=answer_section[:500],  # 샘플링
                        question=q.question_text,
                        question_type=q.detected_type,
                    )
                    quality_evaluations.append(quality.model_dump())
                    logger.info(f"Answer quality for Q{q.order_no}: {quality.overall_score:.2f}")
        except Exception as e:
            logger.warning(f"Answer quality evaluation failed: {e}")
    
    # [권고 반영: Self-Correction 루프]
    if fact_warnings and exit_code == 0:
        logger.warning(f"Fact audit failed. Attempting self-correction for: {fact_warnings}")
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
        # 재시도 (1회 한정)
        run_dir = ws.runs_dir / f"correction_{timestamp_slug()}"
        run_dir.mkdir(parents=True, exist_ok=True)
        corrected_output_path = run_dir / "corrected_writer.md"
        
        # 임시 프롬프트 파일 생성
        temp_prompt_path = run_dir / "correction_prompt.md"
        temp_prompt_path.write_text(correction_prompt, encoding="utf-8")
        
        exit_code = run_codex(temp_prompt_path, ws.root, corrected_output_path)
        if exit_code == 0:
            normalized_text = safe_read_text(corrected_output_path)
            fact_warnings = audit_facts(normalized_text, experiences) # 재검증
            logger.info("Self-correction completed.")
    
    readability = calculate_readability_score(normalized_text)
    
    if fact_warnings:
        for w in fact_warnings:
            logger.warning(w)
    
    logger.info(f"Readability Score: {readability['score']}/100")
    for fb in readability['feedback']:
        if readability['score'] < 100:
            logger.warning(f"Readability feedback: {fb}")

    if validation.passed:
        accepted_path.write_text(normalized_text, encoding="utf-8")
    
    snapshot = GeneratedArtifact(
        id=f"writer-{timestamp_slug()}",
        artifact_type=ArtifactType.WRITER,
        accepted=validation.passed,
        input_snapshot={
            "project": load_project(ws).model_dump(),
            "question_map_path": str((ws.analysis_dir / "question_map.json").relative_to(ws.root)),
            "fact_warnings": fact_warnings,
            "readability": readability,
            "company_analysis": company_analysis.model_dump() if company_analysis else None,
            "quality_evaluations": quality_evaluations,
        },
        output_path=str(accepted_path.relative_to(ws.root)),
        raw_output_path=str(raw_output_path.relative_to(ws.root)),
        validation=validation,
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)
    write_json(run_dir / "writer.json", {"validation": validation.model_dump(), "exit_code": exit_code})
    return {
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "validation": validation.model_dump(),
        "exit_code": exit_code,
        "company_analysis": company_analysis.model_dump() if company_analysis else None,
        "quality_evaluations": quality_evaluations,
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
    deep_pack = run_recursive_interview_chain(ws.root, project, experiences, primary_questions)
    
    # 아티팩트 저장
    out_path = ws.artifacts_dir / "deep_interview.md"
    content = "# Deep Interview Defense Pack\n\n"
    content += "> 이 문서는 AI 시뮬레이션을 통해 답변의 허점을 파고드는 꼬리 질문을 생성한 결과입니다.\n\n"
    for item in deep_pack:
        content += f"### 메인 질문: {item['primary_question']}\n"
        content += f"- **시뮬레이션 답변**: {item['simulated_answer']}\n"
        content += f"- **🔥 날카로운 꼬리 질문**: {item['follow_up_question']}\n\n"
        
    out_path.write_text(content, encoding="utf-8")
    logger.info(f"Deep interview pack written to {out_path}")
    
    return {"path": str(out_path), "count": len(deep_pack)}


def run_interview(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    prompt_path = build_interview_prompt(ws)
    return {"prompt_path": str(prompt_path)}


def run_interview_with_codex(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    
    # [linkareer 개선] 회사 분석 수행
    project = load_project(ws)
    company_analysis = None
    if project.company_name:
        try:
            company_analysis = analyze_company(
                company_name=project.company_name,
                job_title=project.job_title,
                company_type=project.company_type,
            )
            logger.info(f"Company analysis for interview: {project.company_name} (style: {company_analysis.interview_style})")
        except Exception as e:
            logger.warning(f"Company analysis failed: {e}")
    
    prompt_path = build_interview_prompt(ws)
    run_dir = ws.runs_dir / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = run_dir / "raw_interview.md"
    exit_code = run_codex(prompt_path, ws.root, raw_output_path)
    headings = [
        "## 블록 1: INTERVIEW ASSUMPTIONS",
        "## 블록 2: INTERVIEW STRATEGY",
        "## 블록 3: EXPECTED QUESTIONS MAP",
        "## 블록 4: ANSWER FRAMES",
    ]
    raw_text = safe_read_text(raw_output_path)
    normalized_text = normalize_contract_output(raw_text, headings)
    validation_dict = validate_interview_contract(normalized_text)
    validation = ValidationResult(passed=validation_dict["passed"], missing=validation_dict["missing"])

    accepted_path = ws.artifacts_dir / "interview.md"
    
    # [linkareer 개선] 방어 시뮬레이션 수행
    defense_simulations = []
    if company_analysis and normalized_text and project.questions:
        try:
            simulator = DefenseSimulator(company_analysis)
            for q in project.questions[:3]:  # 최대 3개 질문만 시뮬레이션
                # 답변 프레임에서 60초 답변 추출 시도
                sample_answer = f"{q.question_text}에 대한 답변 준비 중"
                simulation = simulator.simulate(
                    primary_question=q.question_text,
                    answer=sample_answer,
                    question_type=q.detected_type,
                )
                defense_simulations.append(simulation.model_dump())
                logger.info(f"Defense simulation for Q{q.order_no}: {len(simulation.follow_up_questions)} follow-ups generated")
        except Exception as e:
            logger.warning(f"Defense simulation failed: {e}")
    
    if validation.passed:
        accepted_path.write_text(normalized_text, encoding="utf-8")
    
    snapshot = GeneratedArtifact(
        id=f"interview-{timestamp_slug()}",
        artifact_type=ArtifactType.INTERVIEW,
        accepted=validation.passed,
        input_snapshot={
            "project": load_project(ws).model_dump(),
            "writer_artifact_exists": (ws.artifacts_dir / "writer.md").exists(),
            "company_analysis": company_analysis.model_dump() if company_analysis else None,
            "defense_simulations": defense_simulations,
        },
        output_path=str(accepted_path.relative_to(ws.root)),
        raw_output_path=str(raw_output_path.relative_to(ws.root)),
        validation=validation,
        created_at=datetime.now(timezone.utc),
    )
    upsert_artifact(ws, snapshot)
    write_json(run_dir / "interview.json", {"validation": validation.model_dump(), "exit_code": exit_code})
    return {
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_output_path),
        "artifact_path": str(accepted_path),
        "validation": validation.model_dump(),
        "exit_code": exit_code,
        "company_analysis": company_analysis.model_dump() if company_analysis else None,
        "defense_simulations": defense_simulations,
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
    deep_pack = run_recursive_interview_chain(ws.root, project, experiences, primary_questions)
    
    # 아티팩트 저장
    out_path = ws.artifacts_dir / "deep_interview.md"
    content = "# Deep Interview Defense Pack\n\n"
    content += "> 이 문서는 AI 시뮬레이션을 통해 답변의 허점을 파고드는 꼬리 질문을 생성한 결과입니다.\n\n"
    for item in deep_pack:
        content += f"### 메인 질문: {item['primary_question']}\n"
        content += f"- **시뮬레이션 답변**: {item['simulated_answer']}\n"
        content += f"- **🔥 날카로운 꼬리 질문**: {item['follow_up_question']}\n\n"
        
    out_path.write_text(content, encoding="utf-8")
    logger.info(f"Deep interview pack written to {out_path}")
    
    return {"path": str(out_path), "count": len(deep_pack)}


def run_export(ws: Workspace) -> dict[str, Any]:
    ws.ensure()
    initialize_state(ws)
    project = load_project(ws)
    artifacts = load_artifacts(ws)
    accepted = latest_accepted_artifacts(artifacts, [ArtifactType.COACH, ArtifactType.WRITER, ArtifactType.INTERVIEW])
    writer_text = safe_read_text(ws.artifacts_dir / "writer.md")
    interview_text = safe_read_text(ws.artifacts_dir / "interview.md")
    coach_text = safe_read_text(ws.artifacts_dir / "coach.md")

    export_md = "\n\n".join(
        [
            f"# Export Package\n\n- Company: {project.company_name}\n- Role: {project.job_title}",
            "## Coach Artifact\n" + (coach_text or "_missing_"),
            "## Writer Artifact\n" + (writer_text or "_missing_"),
            "## Interview Artifact\n" + (interview_text or "_missing_"),
        ]
    )
    export_path = ws.artifacts_dir / "export.md"
    export_path.write_text(export_md, encoding="utf-8")

    export_json = {
        "project": project.model_dump(),
        "accepted_artifacts": [item.model_dump() for item in accepted],
        "paths": {
            "coach": str((ws.artifacts_dir / "coach.md").relative_to(ws.root)),
            "writer": str((ws.artifacts_dir / "writer.md").relative_to(ws.root)),
            "interview": str((ws.artifacts_dir / "interview.md").relative_to(ws.root)),
            "export": str(export_path.relative_to(ws.root)),
        },
    }
    export_json_path = ws.artifacts_dir / "export.json"
    write_json(export_json_path, export_json)
    
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
    return {
        "markdown_path": str(export_path),
        "json_path": str(export_json_path),
        "accepted_count": len(accepted),
    }


from .estimator import estimate_cost_and_log, count_tokens, is_over_limit, WARNING_THRESHOLD_TOKENS

def build_coach_prompt(ws: Workspace, coach_artifact: dict[str, Any] | None = None, gap_report: dict[str, Any] | None = None) -> Path:
    ws.ensure()
    project = load_project(ws)
    auto_classify_project_questions(project)
    save_project(ws, project)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    artifact = coach_artifact or build_coach_artifact(project, experiences, gap_report or analyze_gaps(project, experiences))
    
    hints = build_knowledge_hints(knowledge_sources, project)
    
    # [토큰 압축 로직] 한도 초과 시 힌트 개수를 줄여가며 재시도
    while len(hints) > 0:
        data_block = build_data_block(
            project=project,
            experiences=experiences,
            knowledge_hints=hints,
            extra={
                "gap_report": gap_report or analyze_gaps(project, experiences),
                "coach_allocations": artifact.get("allocations", []),
            },
        )
        content = PROMPT_COACH.format(data_block=data_block)
        if not is_over_limit(count_tokens(content)):
            break
        hints.pop() # 가장 점수가 낮은 힌트부터 제거
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


def build_draft_prompt(ws: Workspace, target_path: Path) -> Path:
    ws.ensure()
    project = load_project(ws)
    auto_classify_project_questions(project)
    save_project(ws, project)
    experiences = load_experiences(ws)
    knowledge_sources = load_knowledge_sources(ws)
    question_map = read_json_if_exists(ws.analysis_dir / "question_map.json")
    
    hints = build_knowledge_hints(knowledge_sources, project)
    selected_exps = select_primary_experiences(experiences, question_map)
    
    # [토큰 압축 로직]
    while len(hints) >= 0:
        data_block = build_data_block(
            project=project,
            experiences=selected_exps,
            knowledge_hints=hints,
            extra={
                "question_map": question_map,
                "legacy_target_path": relative(ws.root, target_path),
                "structure_rules_path": relative(ws.root, ws.analysis_dir / "structure_rules.md"),
            },
        )
        content = PROMPT_WRITER.format(data_block=data_block)
        if not is_over_limit(count_tokens(content)) or not hints:
            break
        hints.pop()
        logger.info(f"Compressing context (Writer): Reduced knowledge hints to {len(hints)}")

    out = ws.outputs_dir / "latest_draft_prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def build_interview_prompt(ws: Workspace) -> Path:
    ws.ensure()
    project = load_project(ws)
    auto_classify_project_questions(project)
    save_project(ws, project)
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


from .estimator import estimate_cost_and_log

def run_codex(prompt_path: Path, cwd: Path, output_path: Path) -> int:
    if shutil.which("codex") is None:
        logger.error("`codex` is not available on PATH.")
        raise RuntimeError("`codex` is not available on PATH.")

    prompt_text = prompt_path.read_text(encoding="utf-8")
    estimate_cost_and_log(prompt_text, context_name=output_path.name)
    
    prompt = build_exec_prompt(prompt_text)
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        logger.info(f"Running codex for {output_path.name} (Attempt {attempt + 1}/{max_retries})")
        try:
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
            
            if result.returncode == 0:
                logger.info(f"Codex execution successful for {output_path.name}")
                if (not output_path.exists()) or not output_path.read_text(encoding="utf-8", errors="ignore").strip():
                    extracted = extract_last_codex_message(result.stdout or "")
                    output_path.write_text(
                        extracted or ((result.stdout or "") + ("\n" + result.stderr if result.stderr else "")),
                        encoding="utf-8",
                    )
                return 0
            else:
                logger.warning(f"Codex execution failed with code {result.returncode}. Stderr: {result.stderr.strip()[:200]}")
                
        except Exception as e:
            logger.error(f"Error during codex execution: {e}")
            
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
            
    logger.error(f"Failed to execute codex after {max_retries} attempts.")
    return 1


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


def write_source_artifacts(ws: Workspace, source: KnowledgeSource) -> None:
    name = f"{source.id}-{slugify(source.title)}"
    normalized_path = ws.sources_normalized_dir / f"{name}.md"
    extracted_path = ws.sources_extracted_dir / f"{name}.json"
    normalized_path.write_text(
        f"# {source.title}\n\n{source.cleaned_text}\n",
        encoding="utf-8",
    )
    write_json(extracted_path, source.model_dump())


def merge_sources(existing: List[KnowledgeSource], new_sources: List[KnowledgeSource]) -> List[KnowledgeSource]:
    by_id = {source.id: source for source in existing}
    for source in new_sources:
        by_id[source.id] = source
    return list(by_id.values())


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)
    return slug[:80] or "source"


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
