import json
import subprocess
from pathlib import Path
from typing import List, Any

from .models import ApplicationProject, Experience
from .company_analyzer import analyze_company, build_role_industry_strategy_from_project
from .executor import build_exec_prompt, extract_last_codex_message
from .templates import PROMPT_SIMULATE_ANSWER, PROMPT_GENERATE_FOLLOW_UP
from .logger import get_logger

logger = get_logger("interview_engine")


def run_recursive_interview_chain(
    ws_root: Path,
    project: ApplicationProject,
    experiences: List[Experience],
    primary_questions: List[str],
    prepared_answers: List[str] | None = None,
) -> List[dict[str, Any]]:
    """
    1차 질문들에 대해 가상 답변을 생성하고, 그에 따른 꼬리 질문을 연쇄적으로 생성합니다.
    """
    deep_interview_pack = []

    # [권고 반영] 약점 리서치 노트 가져오기
    strategy_context = project.research_notes or "일반적인 면접 원칙 준수"
    committee_personas: List[dict[str, Any]] = []
    try:
        company_analysis = analyze_company(
            company_name=project.company_name,
            job_title=project.job_title,
            company_type=project.company_type,
        )
        strategy_pack = build_role_industry_strategy_from_project(
            project,
            company_analysis,
        )
        committee_personas = strategy_pack.get("committee_personas", [])
    except Exception:
        committee_personas = []

    for i, q_text in enumerate(primary_questions[:3]):
        logger.info(f"Generating deep analysis for Question {i + 1}...")

        # 1. 답변 확보: 실제 작성 답변이 있으면 우선 사용하고, 없으면 시뮬레이션 생성
        simulated_answer = ""
        if prepared_answers and i < len(prepared_answers):
            simulated_answer = (prepared_answers[i] or "").strip()

        if not simulated_answer:
            exp_json = json.dumps(
                [e.model_dump() for e in experiences[:2]], ensure_ascii=False
            )
            sim_prompt = PROMPT_SIMULATE_ANSWER.format(
                question=q_text, experience_json=exp_json
            )
            simulated_answer = _call_codex_simple(ws_root, sim_prompt)

        # 2. 꼬리 질문 생성 (공격적 편향 주입)
        persona = committee_personas[i % len(committee_personas)] if committee_personas else {}
        follow_prompt = PROMPT_GENERATE_FOLLOW_UP.format(
            company=project.company_name,
            job=project.job_title,
            simulated_answer=simulated_answer,
            interviewer_name=persona.get("name", "면접위원"),
            interviewer_role=persona.get("role", "논리적 허점을 검증하는 위원"),
            interviewer_focus=", ".join(persona.get("focus", [])[:3]) or "수치, 개인 기여, 대안 비교",
        )

        # [권고 반영] 면접관에게 '비판적 시각' 강제 지시
        follow_prompt += f"\n# INTERVIEWER BIAS (STRICT MODE)\n- Focus on these strategic weaknesses: {strategy_context}\n- If the candidate sounds vague, ask for specific metrics or individual contribution.\n- Do not be impressed by achievements; find the flaw."

        follow_up_question = _call_codex_simple(ws_root, follow_prompt)

        deep_interview_pack.append(
            {
                "primary_question": q_text,
                "simulated_answer": simulated_answer,
                "follow_up_question": follow_up_question,
                "interviewer_persona": persona.get("name", "면접위원"),
                "committee_rounds": _build_committee_rounds(
                    committee_personas, i, follow_up_question
                ),
            }
        )

    return deep_interview_pack


def _build_committee_rounds(
    committee_personas: List[dict[str, Any]],
    primary_index: int,
    follow_up_question: str,
) -> List[dict[str, Any]]:
    if not committee_personas:
        return []

    rounds: List[dict[str, Any]] = []
    for offset, persona in enumerate(committee_personas[:3]):
        stance = "주질문 검증"
        if offset == 1:
            stance = "실무 적합성 검증"
        elif offset == 2:
            stance = "리스크 및 반례 검증"
        rounds.append(
            {
                "persona": persona.get("name", "면접위원"),
                "role": persona.get("role", ""),
                "focus": persona.get("focus", []),
                "stance": stance,
                "question": follow_up_question if offset == 0 else _persona_reframe_question(
                    follow_up_question, persona
                ),
            }
        )
    return rounds


def _persona_reframe_question(question: str, persona: dict[str, Any]) -> str:
    focus = ", ".join(persona.get("focus", [])[:2])
    if not focus:
        return question
    return f"{question} 특히 {focus} 관점에서 다시 설명해주세요."


def _call_codex_simple(cwd: Path, prompt_text: str) -> str:
    """단일 텍스트 생성을 위해 Codex를 호출하는 헬퍼 함수"""
    exec_prompt = build_exec_prompt(prompt_text)

    result = subprocess.run(
        [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(cwd),
            "--color",
            "never",
            "-",
        ],
        cwd=str(cwd),
        input=exec_prompt,
        capture_output=True,
        text=True,
        check=False,
    )

    output = extract_last_codex_message(result.stdout or "")
    return output.strip() or "Error generating response"
