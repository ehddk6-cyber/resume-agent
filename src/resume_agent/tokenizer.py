"""
한국어 토크나이저 - kiwipiepy 기반 형태소 분석
kiwipiepy 미설치 시 정규식 폴백
"""

from __future__ import annotations

import re
from typing import List

# kiwipiepy 로드 시도 — 없으면 False
_USE_KIWI = False
try:
    from kiwipiepy import Kiwi

    _KIWI: Kiwi | None = None
    _USE_KIWI = True
except ImportError:
    Kiwi = None  # type: ignore[assignment,misc]
    _KIWI = None


def _get_kiwi() -> "Kiwi | None":
    """Kiwi 인스턴스 싱글톤 로더"""
    global _KIWI
    if not _USE_KIWI:
        return None
    if _KIWI is None:
        _KIWI = Kiwi()
    return _KIWI


# kiwipiepy POS tags to keep
_ALLOWED_POS_PREFIXES = ("NN", "VA", "VV", "VCN")


def extract_morphemes(text: str, normalize: bool = True) -> List[str]:
    """
    텍스트에서 형태소를 추출합니다.

    kiwipiepy 사용 가능 시: 명사/형용사/동사만 추출
    폴백: 정규식 토크나이징

    Args:
        text: 분석할 텍스트
        normalize: True면 소문자 변환 + 공백 정규화

    Returns:
        형태소 리스트
    """
    if not text or not text.strip():
        return []

    kiwi = _get_kiwi()
    if kiwi is not None:
        return _kiwi_extract(kiwi, text, normalize)
    return _regex_extract(text, normalize)


def _kiwi_extract(kiwi: "Kiwi", text: str, normalize: bool) -> List[str]:
    """kiwipiepy 기반 형태소 추출"""
    tokens: List[str] = []
    morphs = kiwi.tokenize(text)
    for morph in morphs:
        if not any(morph.tag.startswith(pos) for pos in _ALLOWED_POS_PREFIXES):
            continue
        word = morph.form.lower() if normalize else morph.form
        if len(word) < 2:
            continue
        tokens.append(word)
    return tokens


def _regex_extract(text: str, normalize: bool) -> List[str]:
    """정규식 폴백 토크나이징"""
    processed = text.lower() if normalize else text
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", processed)
    return tokens


def extract_nouns(text: str) -> List[str]:
    """
    명사만 추출합니다.
    kiwipiepy 미사용 시 전체 토큰 반환.
    """
    if not text or not text.strip():
        return []

    kiwi = _get_kiwi()
    if kiwi is not None:
        results: List[str] = []
        for morph in kiwi.tokenize(text):
            if morph.tag.startswith("NN") and len(morph.form) >= 2:
                results.append(morph.form)
        return results
    return _regex_extract(text, normalize=True)


def tokenize_for_embedding(text: str) -> str:
    """
    임베딩 입력용 토크나이징.
    형태소를 공백으로 연결한 문자열 반환.
    """
    morphemes = extract_morphemes(text, normalize=True)
    return " ".join(morphemes) if morphemes else text.strip()
