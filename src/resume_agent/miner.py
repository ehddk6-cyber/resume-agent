import json
from pathlib import Path
from typing import List, Any
import subprocess

from .models import Experience, EvidenceLevel, VerificationStatus
from .pipeline import build_exec_prompt, extract_last_codex_message
from .pdf_utils import split_text

MINE_PROMPT_TEMPLATE = """
# ROLE
You are an expert career counselor and data extractor.
Your job is to read the following segment of a past resume/essay and extract distinct professional/academic experiences into a strict JSON list format.

# RULES
1. Identify distinct experiences (projects, internships, club activities, part-time jobs).
2. For each experience, extract information matching the STAR (Situation, Task, Action, Result) method.
3. Extract any metrics or numbers to the 'metrics' field.
4. If there is evidence text (e.g., specific reports, tools used, outcomes), put it in 'evidence_text'.
5. Infer 3-5 keywords for the 'tags' field (e.g., 협업, 문제해결, 데이터).
6. Return ONLY a valid JSON list. Do not use markdown code blocks like ```json ... ```. Just the JSON array.
7. If no clear experiences are found in this segment, return an empty list [].

# EXPECTED JSON SCHEMA
[
  {{
    "title": "string (1-line summary)",
    "organization": "string",
    "situation": "string",
    "task": "string",
    "action": "string",
    "result": "string",
    "personal_contribution": "string",
    "metrics": "string",
    "evidence_text": "string",
    "tags": ["string", "string"]
  }}
]

# TARGET DOCUMENT SEGMENT
{document_text}
"""

def mine_past_resume(file_path: Path, workspace_root: Path) -> List[Experience]:
    """과거 자소서 파일(txt, docx)을 읽어 Codex를 통해 경험 단위로 추출합니다 (청크 단위 분할 처리)."""
    # 문서 텍스트 읽기
    suffix = file_path.suffix.lower()
    full_text = ""
    if suffix == '.docx':
        try:
            from docx import Document
            doc = Document(file_path)
            full_text = "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            print("python-docx is required for docx files.")
            return []
    elif suffix == '.txt':
        full_text = file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        print(f"Unsupported file format for mining: {suffix}")
        return []

    if not full_text.strip():
        return []

    # 텍스트 분할 (청크 처리)
    chunks = split_text(full_text, chunk_size=3000)
    all_extracted_experiences: List[Experience] = []
    seen_titles = set()

    print(f"📄 문서를 {len(chunks)}개의 세그먼트로 나누어 분석을 시작합니다.")

    for i, chunk_text in enumerate(chunks):
        if len(chunks) > 1:
            print(f"  - 세그먼트 {i+1}/{len(chunks)} 처리 중...")
            
        # 프롬프트 생성
        prompt = MINE_PROMPT_TEMPLATE.format(document_text=chunk_text)
        exec_prompt = build_exec_prompt(prompt)

        # Codex 실행
        result = subprocess.run(
            [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "-C",
                str(workspace_root),
                "--color",
                "never",
                "-",
            ],
            cwd=str(workspace_root),
            input=exec_prompt,
            capture_output=True,
            text=True,
            check=False,
        )

        extracted_text = extract_last_codex_message(result.stdout or "")
        if not extracted_text:
            extracted_text = result.stdout or result.stderr

        # 마크다운 블록 제거 처리
        if "```json" in extracted_text:
            extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
        elif "```" in extracted_text:
            extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(extracted_text)
            if not isinstance(data, list):
                continue
                
            for j, item in enumerate(data):
                title = item.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                
                seen_titles.add(title)
                exp = Experience(
                    id=f"mined_{file_path.stem}_{i}_{j}",
                    title=title,
                    organization=item.get("organization", ""),
                    period_start="",
                    situation=item.get("situation", ""),
                    task=item.get("task", ""),
                    action=item.get("action", ""),
                    result=item.get("result", ""),
                    personal_contribution=item.get("personal_contribution", ""),
                    metrics=item.get("metrics", ""),
                    evidence_text=item.get("evidence_text", ""),
                    tags=item.get("tags", []),
                    evidence_level=EvidenceLevel.L2 if item.get("action") else EvidenceLevel.L1,
                    verification_status=VerificationStatus.NEEDS_VERIFICATION,
                )
                if exp.metrics or any(c in exp.result for c in ["%", "건", "명", "배"]):
                    exp.evidence_level = EvidenceLevel.L3
                all_extracted_experiences.append(exp)
        except json.JSONDecodeError:
            print(f"⚠️ 세그먼트 {i+1} 파싱 실패 (응답 포맷 오류)")
            continue

    return all_extracted_experiences
