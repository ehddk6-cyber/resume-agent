"""
설정 파일 로더 - config.yaml에서 운영 설정을 로드합니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .logger import get_logger

logger = get_logger("config")

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

_CONFIG: Optional[Dict[str, Any]] = None


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """중첩 딕셔너리 병합 (override가 base를 덮어씀)."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    config.yaml을 로드합니다. 캐싱을 지원합니다.

    Args:
        config_path: 설정 파일 경로 (기본값: 프로젝트 루트의 config.yaml)
                     명시적으로 전달되면 캐시를 무시하고 해당 파일을 로드합니다.

    Returns:
        설정 딕셔너리
    """
    global _CONFIG
    if config_path is None and _CONFIG is not None:
        return _CONFIG

    path = config_path or _DEFAULT_CONFIG_PATH
    if not path.exists():
        logger.warning(f"Config file not found: {path}. Using defaults.")
        _CONFIG = _get_defaults()
        return _CONFIG

    try:
        with open(path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        _CONFIG = _deep_merge(_get_defaults(), user_config)
        logger.info(f"Config loaded from {path}")
    except Exception as e:
        logger.error(f"Failed to load config from {path}: {e}. Using defaults.")
        _CONFIG = _get_defaults()

    return _CONFIG


def get_config_value(path: str, default: Any = None) -> Any:
    """
    점(.)으로 구분된 경로로 설정값을 조회합니다.

    Args:
        path: 예: "token.warning_threshold", "scoring.reuse_penalty"
        default: 키가 없을 때 반환할 기본값

    Returns:
        설정값 또는 기본값
    """
    config = load_config()
    keys = path.split(".")
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def reload_config() -> Dict[str, Any]:
    """캐시를 무시하고 설정을 다시 로드합니다."""
    global _CONFIG
    _CONFIG = None
    return load_config()


def _get_defaults() -> Dict[str, Any]:
    """기본값을 반환합니다 (config.yaml의 값과 동일)."""
    return {
        "token": {
            "warning_threshold": 8000,
            "cost_per_1k": 0.005,
            "encoding_model": "gpt-4o",
        },
        "scoring": {
            "evidence_bonus": {"L1": 1, "L2": 4, "L3": 8},
            "reuse_penalty": 7,
            "same_org_penalty": 4,
            "verified_bonus": 3,
            "unverified_penalty": -2,
        },
        "gap_analysis": {
            "risk_thresholds": {"high": 5, "medium": 10},
        },
        "codex": {
            "max_retries": 3,
            "retry_delay_base": 2,
        },
        "validation": {
            "star_min_lengths": {
                "situation": 50,
                "task": 30,
                "action": 100,
                "result": 50,
            },
        },
        "export": {
            "char_limit_ratio_min": 0.90,
            "char_limit_ratio_max": 0.97,
        },
    }
