import json
import subprocess
from pathlib import Path
from typing import List, dict[str, Any]

from .models import ApplicationProject, Experience
from .pipeline import build_exec_prompt, extract_last_codex_message
from .templates import PROMPT_SIMULATE_ANSWER, PROMPT_GENERATE_FOLLOW_UP
from .logger import get_logger

logger = get_logger("interview_engine")

def run_recursive_interview_chain(
    ws_root: Path, 
    project: ApplicationProject, 
    experiences: List[Experience], 
    primary_questions: List[str]
) -> List[dict[str, Any]]:
    """
    1차 질문들에 대해 가상 답변을 생성하고, 그에 따른 꼬리 질문을 연쇄적으로 생성합니다.
    """
    deep_interview_pack = []
    
    # [권고 반영] 약점 리서치 노트 가져오기
    strategy_context = project.research_notes or "일반적인 면접 원칙 준수"
    
    for i, q_text in enumerate(primary_questions[:3]):
        logger.info(f"Generating deep analysis for Question {i+1}...")
        
        # 1. 가상 답변 생성
        exp_json = json.dumps([e.model_dump() for e in experiences[:2]], ensure_ascii=False)
        sim_prompt = PROMPT_SIMULATE_ANSWER.format(question=q_text, experience_json=exp_json)
        simulated_answer = _call_codex_simple(ws_root, sim_prompt)
        
        # 2. 꼬리 질문 생성 (공격적 편향 주입)
        follow_prompt = PROMPT_GENERATE_FOLLOW_UP.format(
            company=project.company_name,
            job=project.job_title,
            simulated_answer=simulated_answer
        )
        
        # [권고 반영] 면접관에게 '비판적 시각' 강제 지시
        follow_prompt += f"\n# INTERVIEWER BIAS (STRICT MODE)\n- Focus on these strategic weaknesses: {strategy_context}\n- If the candidate sounds vague, ask for specific metrics or individual contribution.\n- Do not be impressed by achievements; find the flaw."
        
        follow_up_question = _call_codex_simple(ws_root, follow_prompt)
        
        deep_interview_pack.append({
            "primary_question": q_text,
            "simulated_answer": simulated_answer,
            "follow_up_question": follow_up_question
        })
        
    return deep_interview_pack

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
