"""
공통 유틸리티 함수 - 외부 의존성 없는 순수 유틸리티
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    """영문/숫자만 남기고 하이픈으로 연결한 슬러그 생성 (최대 80자)"""
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)
    return slug[:80] or "source"


def timestamp_slug() -> str:
    """UTC 기준 타임스탬프 슬러그 (예: 20260326_141500)"""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def safe_read_text(path: Path) -> str:
    """파일이 존재하면 텍스트를 읽고, 없으면 빈 문자열 반환"""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json_if_exists(path: Path) -> Any:
    """JSON 파일이 존재하면 파싱하고, 없으면 빈 리스트 반환"""
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def relative(root: Path, path: Path) -> str:
    """root 기준 상대 경로 문자열 반환"""
    return str(path.resolve().relative_to(root.resolve()))


def write_if_missing(path: Path, content: str) -> None:
    """파일이 없을 때만 생성"""
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def normalize_example(name: str, body: str) -> str:
    """소스 예시를 표준 마크다운 형식으로 변환"""
    return f"# Source: {name}\n\n{body.strip()}\n"


def normalize_contract_output(text: str, headings: list[str]) -> str:
    """
    LLM 출력에서 지정된 헤딩 이후의 텍스트만 추출합니다.
    여러 헤딩 중 가장 먼저 등장하는 위치부터 잘라냅니다.
    """
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
