"""
patina ↔ resume-agent 브릿지 모듈

patina의 SKILL.md, 패턴 파일, 프로필을 로드하여 LLM 프롬프트를 구성하고,
writer_draft.md의 답변을 추출/재조합하여 patina 파이프라인을 실행한다.

patina는 Python 패키지가 아닌 Claude Code 스킬(마크다운 파일)이므로,
subprocess 호출 대신 파일을 직접 읽어 LLM 프롬프트에 주입한다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger(__name__)

# patina 스킬 디렉토리 기본 경로
_PATINA_SKILL_DIR = Path.home() / ".codex" / "skills" / "patina"

# 지원 모드
VALID_MODES = ("audit", "rewrite", "score", "ouroboros")


def get_patina_skill_dir() -> Path:
    """patina 스킬 디렉토리 경로 반환. 없으면 FileNotFoundError."""
    if _PATINA_SKILL_DIR.is_dir():
        return _PATINA_SKILL_DIR
    # 대체 경로 탐색
    for alt in [
        Path.home() / ".claude" / "skills" / "patina",
        Path.home() / ".kilocode" / "skills" / "patina",
        Path.home() / "patina",
    ]:
        if alt.is_dir():
            return alt
    raise FileNotFoundError(
        f"patina 스킬 디렉토리를 찾을 수 없습니다. 기대 경로: {_PATINA_SKILL_DIR}"
    )


def load_patina_skill_md() -> str:
    """patina/SKILL.md 전체 텍스트 로드."""
    skill_dir = get_patina_skill_dir()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_md}")
    return skill_md.read_text(encoding="utf-8")


def load_patina_patterns(lang: str = "ko") -> str:
    """
    patina 패턴 팩 파일들을 로드하여 하나의 문자열로 결합.

    Args:
        lang: 언어 코드 (기본: "ko")

    Returns:
        결합된 패턴 팩 텍스트
    """
    skill_dir = get_patina_skill_dir()
    patterns_dir = skill_dir / "patterns"
    if not patterns_dir.is_dir():
        raise FileNotFoundError(f"patterns 디렉토리를 찾을 수 없습니다: {patterns_dir}")

    pattern_files = sorted(patterns_dir.glob(f"{lang}-*.md"))
    if not pattern_files:
        raise FileNotFoundError(
            f"{lang} 언어의 패턴 파일을 찾을 수 없습니다: {patterns_dir}/{lang}-*.md"
        )

    parts = []
    for pf in pattern_files:
        header = f"\n\n---\n## 패턴 팩: {pf.name}\n---\n\n"
        parts.append(header + pf.read_text(encoding="utf-8"))

    return "\n".join(parts)


def load_patina_scoring() -> str:
    """patina/core/scoring.md 로드."""
    skill_dir = get_patina_skill_dir()
    scoring_md = skill_dir / "core" / "scoring.md"
    if not scoring_md.exists():
        raise FileNotFoundError(f"scoring.md not found: {scoring_md}")
    return scoring_md.read_text(encoding="utf-8")


def load_patina_voice() -> str:
    """patina/core/voice.md 로드."""
    skill_dir = get_patina_skill_dir()
    voice_md = skill_dir / "core" / "voice.md"
    if not voice_md.exists():
        raise FileNotFoundError(f"voice.md not found: {voice_md}")
    return voice_md.read_text(encoding="utf-8")


def load_patina_profile(profile_name: str = "resume") -> str:
    """
    patina 프로필 파일 로드. 사용자 커스텀 프로필 우선.

    Args:
        profile_name: 프로필 이름 (기본: "resume")
    """
    skill_dir = get_patina_skill_dir()

    # 커스텀 프로필 우선
    custom = skill_dir / "custom" / "profiles" / f"{profile_name}.md"
    if custom.exists():
        return custom.read_text(encoding="utf-8")

    # 기본 프로필
    default = skill_dir / "profiles" / f"{profile_name}.md"
    if default.exists():
        return default.read_text(encoding="utf-8")

    # 폴백: default 프로필
    fallback = skill_dir / "profiles" / "default.md"
    if fallback.exists():
        logger.warning(
            f"프로필 '{profile_name}'을 찾을 수 없어 default 프로필을 사용합니다."
        )
        return fallback.read_text(encoding="utf-8")

    raise FileNotFoundError(f"프로필 파일을 찾을 수 없습니다: {profile_name}")


def load_patina_config() -> str:
    """patina/.patina.default.yaml 로드."""
    skill_dir = get_patina_skill_dir()
    config = skill_dir / ".patina.default.yaml"
    if not config.exists():
        raise FileNotFoundError(f".patina.default.yaml not found: {config}")
    return config.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# writer_draft.md 파싱: 답변 추출 및 재조합
# ---------------------------------------------------------------------------

# writer_draft.md에서 답변 블록 추출용 정규식
# "### Q숫자." 헤더부터 "글자수:" 라인 직전까지의 본문 추출
_RE_ANSWER_HEADER = re.compile(
    r"(###\s+Q(\d+)\..*?\n)"  # Q 헤더 (그룹 1 전체, 그룹 2 번호)
    r"([\s\S]*?)"  # 본문 (그룹 3)
    r"(?=글자수:|$)",  # 글자수 라인 직전까지
    re.MULTILINE,
)

# 소제목 라인 추출: "**[소제목] ...**"
_RE_SUBTITLE = re.compile(r"\*\*\[소제목\].*?\*\*\n*")

# 글자수 메타데이터 블록 추출
_RE_CHARCOUNT = re.compile(r"글자수:.*?(?=\n---|\n\n##|\Z)", re.DOTALL)


def extract_answers(writer_text: str) -> dict[str, dict[str, str]]:
    """
    writer_draft.md 텍스트에서 Q1~Q4 답변 본문을 추출한다.

    Returns:
        {
            "Q1": {"header": "### Q1. ...", "subtitle": "**[소제목] ...**", "body": "...", "charcount": "글자수: ..."},
            "Q2": {...},
            ...
        }
    """
    answers: dict[str, dict[str, str]] = {}

    # "---" 구분자로 섹션 분리
    sections = re.split(r"\n---\n", writer_text)

    for section in sections:
        # "### Q숫자." 헤더 매칭
        header_match = re.search(r"^(###\s+Q(\d+)\..*?)$", section, re.MULTILINE)
        if not header_match:
            continue

        q_id = f"Q{header_match.group(2)}"
        header = header_match.group(1)

        # 소제목 추출
        subtitle_match = _RE_SUBTITLE.search(section)
        subtitle = subtitle_match.group(0).strip() if subtitle_match else ""

        # 글자수 메타데이터 추출
        charcount_match = _RE_CHARCOUNT.search(section)
        charcount = charcount_match.group(0).strip() if charcount_match else ""

        # 본문: 헤더 뒤부터 글자수 직전까지
        # 헤더 위치 찾기
        body_start = header_match.end()
        if charcount_match:
            body_end = charcount_match.start()
        else:
            body_end = len(section)

        body = section[body_start:body_end].strip()
        # 소제목이 본문 앞에 있으면 제거
        if subtitle:
            body = body.replace(subtitle, "").strip()

        answers[q_id] = {
            "header": header,
            "subtitle": subtitle,
            "body": body,
            "charcount": charcount,
        }

    return answers


def reassemble_answers(
    original_text: str,
    processed: dict[str, str],
) -> str:
    """
    처리된 답변 본문을 원본 writer_draft.md 구조에 재삽입한다.

    Args:
        original_text: 원본 writer_draft.md 텍스트
        processed: {"Q1": "처리된 본문", "Q2": "...", ...}

    Returns:
        재조합된 writer_draft.md 텍스트
    """
    result = original_text

    for q_id, new_body in processed.items():
        # "### Q숫자." 헤더 찾기
        q_num = q_id[1:]  # "1", "2", ...
        header_pattern = re.compile(
            rf"(###\s+Q{q_num}\..*?\n)"  # 헤더
            rf"(\*\*\[소제목\].*?\*\*\n*)?"  # 소제목 (선택)
            rf"([\s\S]*?)"  # 기존 본문
            rf"(글자수:.*?(?=\n---|\n\n##|\Z))",  # 글자수 메타
            re.DOTALL,
        )

        def _replace(match: re.Match, body: str = new_body) -> str:
            header = match.group(1)
            subtitle = match.group(2) or ""
            charcount = match.group(4)
            return f"{header}{subtitle}\n{body}\n\n{charcount}"

        result = header_pattern.sub(_replace, result)

    return result


def measure_char_delta(original_body: str, new_body: str) -> dict[str, Any]:
    """
    글자수 변동을 측정한다. (워드 기준 공백 포함)

    Returns:
        {"original_chars": int, "new_chars": int, "delta": int, "delta_pct": float}
    """
    orig_len = len(original_body)
    new_len = len(new_body)
    delta = new_len - orig_len
    delta_pct = (delta / orig_len * 100) if orig_len > 0 else 0.0
    return {
        "original_chars": orig_len,
        "new_chars": new_len,
        "delta": delta,
        "delta_pct": round(delta_pct, 1),
    }


# ---------------------------------------------------------------------------
# patina 프롬프트 빌더
# ---------------------------------------------------------------------------


def build_patina_prompt(
    text: str,
    mode: str = "audit",
    profile_name: str = "resume",
    lang: str = "ko",
) -> str:
    """
    patina 스킬 파일들을 조합하여 LLM 프롬프트를 생성한다.

    Args:
        text: 처리할 텍스트 (답변 본문)
        mode: 실행 모드 (audit, rewrite, score, ouroboros)
        profile_name: 프로필 이름
        lang: 언어 코드

    Returns:
        완성된 LLM 프롬프트
    """
    skill_md = load_patina_skill_md()
    patterns = load_patina_patterns(lang)
    profile = load_patina_profile(profile_name)
    voice = load_patina_voice()
    config = load_patina_config()

    # score/ouroboros 모드에서는 scoring.md 추가
    scoring = ""
    if mode in ("score", "ouroboros"):
        scoring = load_patina_scoring()

    prompt = f"""# Task: AI 글쓰기 패턴 제거 (patina)

당신은 AI가 생성한 텍스트에서 AI 특유의 패턴을 찾아 제거하는 편집자입니다.
아래 지침을 따라 텍스트를 처리하세요.

## 실행 모드: {mode}

{"- **audit 모드**: 감지만 하고 수정하지 않는다. 패턴별 발견 위치와 심각도를 테이블로 출력한다." if mode == "audit" else ""}
{"- **rewrite 모드**: AI 패턴을 찾아 자연스러운 대안으로 교체한다. 의미를 보존한다." if mode == "rewrite" else ""}
{"- **score 모드**: AI 유사도 점수를 0-100 척도로 산출한다." if mode == "score" else ""}
{"- **ouroboros 모드**: rewrite + score를 결합하여 점수가 30 이하가 될 때까지 반복 교정한다." if mode == "ouroboros" else ""}

---

## 0단계: 설정

```yaml
{config}
```

---

## 1단계: 프로필

{profile}

---

## 2단계: 패턴 팩

{patterns}

---

## 3단계: 목소리 지침

{voice}

---

## 4단계: 스코어링 알고리즘

{scoring if scoring else "(이 모드에서는 스코어링을 사용하지 않습니다.)"}

---

## 5단계: 오케스트레이션 지침

{skill_md}

---

## 6단계: 처리할 텍스트

아래 텍스트를 patina 파이프라인에 따라 처리하세요.

**중요 제약:**
- `### Q숫자.` 헤더와 `글자수:` 메타데이터 라인은 절대 변경하지 마세요.
- 소제목(`**[소제목] ...**`)은 변경하지 마세요.
- 답변 본문(소제목 다음부터 글자수 직전까지만)을 처리하세요.
- 구체적 수치("20건", "40%", "3,000페이지", "150건")와 고유명사("VLOOKUP", "AICC", "PWM")는 절대 변경하지 마세요.

---

### 처리할 텍스트

{text}

---

## 출력 형식

{"### 감지 결과 (audit 테이블)" if mode == "audit" else ""}
{"각 답변(Q1~Q4)별로 감지된 패턴을 아래 형식으로 나열하세요:" if mode == "audit" else ""}
{"" if mode == "audit" else ""}
{"| 문항 | 패턴 # | 패턴명 | 심각도 | 발견 위치 | 설명 |" if mode == "audit" else ""}
{"|------|--------|--------|--------|-----------|------|" if mode == "audit" else ""}
{'| Q1 | #7 | AI 특유 어휘 남발 | Medium | 2번째 문장 | "혁신적인" 사용 |' if mode == "audit" else ""}
{"" if mode == "audit" else ""}
{"감지하지 못한 경우 빈 테이블을 반환하세요." if mode == "audit" else ""}

{"### 교정 결과 (rewrite)" if mode == "rewrite" else ""}
{"각 답변(Q1~Q4)별로 교정된 전체 본문을 제공하세요. 원본 형식을 유지하세요." if mode == "rewrite" else ""}

{"### AI 유사도 점수 (score)" if mode == "score" else ""}
{"scoring.md 알고리즘에 따라 점수를 산출하세요." if mode == "score" else ""}

{"### Ouroboros 교정 결과 (ouroboros)" if mode == "ouroboros" else ""}
{"반복 로그와 최종 교정된 전체 텍스트를 제공하세요." if mode == "ouroboros" else ""}
"""

    return prompt


def build_patina_audit_report_prompt(
    text: str,
    profile_name: str = "resume",
    lang: str = "ko",
) -> str:
    """
    audit 모드 전용 간소화 프롬프트. 감지만 수행하고 보고서를 생성한다.
    """
    return build_patina_prompt(text, mode="audit", profile_name=profile_name, lang=lang)


def build_patina_rewrite_prompt(
    text: str,
    profile_name: str = "resume",
    lang: str = "ko",
) -> str:
    """
    rewrite 모드 전용 프롬프트. 패턴 제거 후 재작성한다.
    """
    return build_patina_prompt(
        text, mode="rewrite", profile_name=profile_name, lang=lang
    )


def build_patina_score_prompt(
    text: str,
    profile_name: str = "resume",
    lang: str = "ko",
) -> str:
    """
    score 모드 전용 프롬프트. AI 유사도 점수를 산출한다.
    """
    return build_patina_prompt(text, mode="score", profile_name=profile_name, lang=lang)


def build_patina_ouroboros_prompt(
    text: str,
    profile_name: str = "resume",
    lang: str = "ko",
) -> str:
    """
    ouroboros 모드 전용 프롬프트. 반복 교정 + 점수 수렴.
    """
    return build_patina_prompt(
        text, mode="ouroboros", profile_name=profile_name, lang=lang
    )


# ---------------------------------------------------------------------------
# 메인 실행 엔트리포인트
# ---------------------------------------------------------------------------


def run_patina(
    writer_text: str,
    tool: str = "codex",
    mode: str = "audit",
    profile_name: str = "resume",
    lang: str = "ko",
) -> dict[str, Any]:
    """
    writer_draft.md 텍스트에 patina 파이프라인을 실행한다.

    Args:
        writer_text: writer_draft.md 전체 텍스트
        tool: 사용할 CLI 도구 (codex, claude, gemini, kilo, cline)
        mode: 실행 모드 (audit, rewrite, score, ouroboros)
        profile_name: 프로필 이름
        lang: 언어 코드

    Returns:
        {
            "mode": str,
            "tool": str,
            "raw_output": str,
            "answers": dict,           # 추출된 답변 {"Q1": {...}, ...}
            "processed": dict,         # 처리된 답변 {"Q1": "새 본문", ...}
            "char_deltas": dict,       # 글자수 변동 {"Q1": {...}, ...}
            "warnings": list,          # 경고 메시지
            "reassembled_text": str,   # 재조합된 전체 텍스트 (rewrite/ouroboros만)
        }
    """
    from .cli_tool_manager import CLIToolManager, get_available_tools
    from .executor import build_exec_prompt

    if mode not in VALID_MODES:
        raise ValueError(f"지원하지 않는 모드: {mode}. 지원 모드: {VALID_MODES}")

    # 1. 답변 추출
    answers = extract_answers(writer_text)
    if not answers:
        logger.warning("writer_draft.md에서 답변 블록을 추출하지 못했습니다.")
        return {
            "mode": mode,
            "tool": tool,
            "raw_output": "",
            "answers": {},
            "processed": {},
            "char_deltas": {},
            "warnings": ["답변 블록을 추출하지 못했습니다."],
            "reassembled_text": writer_text,
        }

    # 2. 본문만 결합 (헤더/글자수 제외)
    combined_body = ""
    for q_id in sorted(answers.keys()):
        ans = answers[q_id]
        combined_body += f"\n\n### {q_id} 답변 본문\n\n{ans['body']}"

    combined_body = combined_body.strip()

    # 3. 프롬프트 생성
    prompt = build_patina_prompt(
        combined_body,
        mode=mode,
        profile_name=profile_name,
        lang=lang,
    )

    # 4. LLM 실행
    # 프롬프트가 매우 크므로(36K+ chars) stdin으로 전달해야 한다.
    # codex: codex exec --skip-git-repo-check -C <cwd> - 사용 (stdin)
    # claude: claude -p 사용 (stdin)
    # gemini/kilo/cline: 직접 subprocess + stdin
    import subprocess as _subprocess
    import tempfile

    available = get_available_tools()
    if tool not in available:
        logger.warning(f"CLI 도구 '{tool}'를 찾을 수 없습니다. 사용 가능: {available}")
        if "codex" in available:
            tool = "codex"
        elif available:
            tool = available[0]
        else:
            raise RuntimeError("사용 가능한 CLI 도구가 없습니다.")

    logger.info(f"patina 실행: mode={mode}, tool={tool}, profile={profile_name}")

    # 프롬프트를 임시 파일에 저장
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp_prompt:
        tmp_prompt.write(prompt)
        tmp_prompt_path = Path(tmp_prompt.name)

    raw_output = ""
    try:
        if tool == "codex":
            # codex는 stdin 기반 codex exec 사용
            from .executor import run_codex as _run_codex

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp_output:
                tmp_output_path = Path(tmp_output.name)

            exit_code = _run_codex(
                tmp_prompt_path,
                cwd=Path.cwd(),
                output_path=tmp_output_path,
                tool="codex",
            )
            if exit_code != 0:
                logger.warning(f"patina codex 실행 종료 코드: {exit_code}")
            raw_output = tmp_output_path.read_text(encoding="utf-8", errors="ignore")
            try:
                tmp_output_path.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            # claude/gemini/kilo/cline: stdin으로 직접 실행
            tool_cmds = {
                "claude": ["claude", "-p"],
                "gemini": ["gemini", "--prompt"],
                "kilo": ["kilo", "run"],
                "cline": ["cline", "--prompt"],
            }
            cmd_base = tool_cmds.get(tool, [tool, "-p"])

            # claude/kilo는 stdin, gemini/cline도 stdin으로 통일
            cmd = cmd_base + ([] if tool in ("claude", "kilo") else [])
            result = _subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600,
                encoding="utf-8",
            )
            if result.returncode != 0:
                logger.warning(
                    f"patina {tool} 실행 실패 (exit code: {result.returncode}): "
                    f"{result.stderr[:200]}"
                )
            raw_output = result.stdout or ""
    finally:
        try:
            tmp_prompt_path.unlink(missing_ok=True)
        except Exception:
            pass

    # 5. 결과 파싱
    result: dict[str, Any] = {
        "mode": mode,
        "tool": tool,
        "raw_output": raw_output,
        "answers": answers,
        "processed": {},
        "char_deltas": {},
        "warnings": [],
        "reassembled_text": writer_text,
    }

    if mode in ("rewrite", "ouroboros"):
        # 교정 결과에서 각 Q별 새 본문 추출 시도
        processed = _parse_rewrite_output(raw_output, answers)
        result["processed"] = processed

        # 글자수 변동 측정
        char_deltas = {}
        for q_id, new_body in processed.items():
            if q_id in answers:
                delta = measure_char_delta(answers[q_id]["body"], new_body)
                char_deltas[q_id] = delta
                if abs(delta["delta_pct"]) > 5:
                    warning = (
                        f"{q_id} 글자수 변동 {delta['delta_pct']:+.1f}% "
                        f"({delta['original_chars']}자 → {delta['new_chars']}자). "
                        f"5% 초과: 확인 필요."
                    )
                    result["warnings"].append(warning)
                    logger.warning(warning)
        result["char_deltas"] = char_deltas

        # 재조합
        if processed:
            result["reassembled_text"] = reassemble_answers(writer_text, processed)

    elif mode == "score":
        # 점수 결과는 raw_output에서 직접 파싱 (LLM이 테이블로 반환)
        result["score_output"] = raw_output

    return result


def run_patina_ouroboros(
    writer_text: str,
    tool: str = "codex",
    profile_name: str = "resume",
    lang: str = "ko",
    target_score: int = 30,
    max_iterations: int = 3,
) -> dict[str, Any]:
    """
    Ouroboros 모드: 점수 30 이하까지 반복 교정한다.

    resume-agent 레벨에서 ouroboros 루프를 구현한다.
    patina의 SKILL.md ouroboros 로직을 직접 수행한다.
    """
    result = run_patina(
        writer_text,
        tool=tool,
        mode="ouroboros",
        profile_name=profile_name,
        lang=lang,
    )

    # ouroboros 모드는 LLM이 내부적으로 반복하므로
    # 결과를 그대로 반환한다.
    # 필요시 resume-agent 레벨에서 재실행 로직을 추가할 수 있다.
    return result


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------


def parse_score_from_output(output: str) -> dict[str, Any]:
    """
    score 모드 LLM 출력에서 점수를 파싱한다.

    Returns:
        {"overall_score": float | None, "interpretation": str, "raw": str}
    """
    # "전체" 또는 "**전체**" 뒤의 숫자 추출
    score_match = re.search(
        r"(?:전체|Overall)\s*\|[^|]*\|[^|]*\|[^|]*\|\s*\*{0,2}\s*([\d.]+)",
        output,
    )
    if score_match:
        score = float(score_match.group(1))
        if score <= 15:
            interpretation = "사람다움"
        elif score <= 30:
            interpretation = "거의 사람다움"
        elif score <= 50:
            interpretation = "혼재"
        elif score <= 70:
            interpretation = "AI 느낌"
        else:
            interpretation = "AI 생성"
        return {
            "overall_score": score,
            "interpretation": interpretation,
            "raw": output,
        }

    return {"overall_score": None, "interpretation": "파싱 실패", "raw": output}


def _parse_rewrite_output(
    output: str,
    original_answers: dict[str, dict[str, str]],
) -> dict[str, str]:
    """
    rewrite 모드 LLM 출력에서 각 Q별 새 본문을 추출한다.

    LLM 출력 형식이 다양할 수 있으므로 여러 패턴을 시도한다.
    """
    processed: dict[str, str] = {}

    # 패턴 1: "### Q1 답변 본문" 또는 "### Q1" 헤더로 분리
    blocks = re.split(r"(?=###\s*Q\d+)", output)

    for block in blocks:
        q_match = re.match(r"###\s*Q(\d+)", block)
        if not q_match:
            continue
        q_id = f"Q{q_match.group(1)}"
        if q_id not in original_answers:
            continue

        # 헤더 뒤의 본문 추출
        body = re.sub(r"^###\s*Q\d+.*?\n", "", block).strip()
        # 불필요한 마크다운 래퍼 제거
        body = re.sub(r"^```\w*\n?", "", body)
        body = re.sub(r"\n?```$", "", body)
        if body:
            processed[q_id] = body

    # 패턴 2: "Q1:" 또는 "Q1." 접두사로 분리
    if not processed:
        blocks = re.split(r"(?=Q\d+[:.]\s)", output)
        for block in blocks:
            q_match = re.match(r"Q(\d+)[:.]\s", block)
            if not q_match:
                continue
            q_id = f"Q{q_match.group(1)}"
            if q_id not in original_answers:
                continue
            body = re.sub(r"^Q\d+[:.]\s*", "", block).strip()
            if body:
                processed[q_id] = body

    return processed


def get_patina_status() -> dict[str, Any]:
    """
    patina 브릿지 상태 확인.

    Returns:
        {"available": bool, "skill_dir": str, "patterns": list, "profiles": list, "errors": list}
    """
    errors = []
    skill_dir = None
    patterns = []
    profiles = []

    try:
        skill_dir = str(get_patina_skill_dir())
    except FileNotFoundError as e:
        errors.append(str(e))
        return {
            "available": False,
            "skill_dir": None,
            "patterns": [],
            "profiles": [],
            "errors": errors,
        }

    patina_dir = Path(skill_dir)

    # 패턴 파일 확인
    patterns_dir = patina_dir / "patterns"
    if patterns_dir.is_dir():
        patterns = [f.name for f in patterns_dir.glob("ko-*.md")]
    else:
        errors.append(f"patterns 디렉토리 없음: {patterns_dir}")

    # 프로필 파일 확인
    profiles_dir = patina_dir / "profiles"
    if profiles_dir.is_dir():
        profiles = [f.stem for f in profiles_dir.glob("*.md")]
    else:
        errors.append(f"profiles 디렉토리 없음: {profiles_dir}")

    # 필수 파일 확인
    for required in ["SKILL.md", "core/scoring.md", "core/voice.md"]:
        if not (patina_dir / required).exists():
            errors.append(f"필수 파일 없음: {required}")

    return {
        "available": len(errors) == 0,
        "skill_dir": skill_dir,
        "patterns": sorted(patterns),
        "profiles": sorted(profiles),
        "errors": errors,
    }
