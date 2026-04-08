from __future__ import annotations

import json
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, List, Type, TypeVar

from pydantic import BaseModel

from .logger import get_logger
from .models import (
    ApplicationProject,
    EvidenceLevel,
    Experience,
    GeneratedArtifact,
    KnowledgeSource,
    SuccessCase,
    UserProfile,
    VerificationStatus,
)
from .workspace import Workspace

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def initialize_state(ws: Workspace) -> None:
    ws.ensure()
    write_if_missing(ws.state_dir / "profile.json", UserProfile().model_dump())

    # Default experiences
    default_exps = [
        Experience(
            id="exp_er_flow",
            title="응급실 접수 대기 흐름 정리",
            organization="시립병원 응급센터 실습",
            period_start="2025-03-01",
            period_end="2025-04-01",
            situation="실습 시간대마다 접수 순서 문의가 반복돼 환자와 보호자의 대기 불안이 커졌습니다.",
            task="혼잡 시간에도 접수 안내와 우선순위 설명이 끊기지 않도록 흐름을 정리해야 했습니다.",
            action="자주 묻는 질문을 정리해 접수대 안내 문구를 표준화하고, 선임에게 확인받은 우선 안내 순서를 기록으로 남겼습니다.",
            result="문의가 한 번에 정리되면서 접수대 응대가 안정됐고, 선임이 다음 실습자에게도 같은 기록을 공유했습니다.",
            personal_contribution="질문 유형 정리, 안내 문구 초안 작성, 기록 문서화",
            metrics="반복 문의 메모 12건 정리",
            evidence_text="실습 메모와 선임 피드백",
            evidence_level=EvidenceLevel.L3,
            tags=["고객응대", "문제해결", "상황판단", "성과"],
            verification_status=VerificationStatus.VERIFIED,
        ).model_dump()
    ]
    write_if_missing(ws.state_dir / "experiences.json", default_exps)
    write_if_missing(ws.state_dir / "project.json", ApplicationProject().model_dump())
    write_if_missing(ws.state_dir / "knowledge_sources.json", [])
    write_if_missing(ws.state_dir / "success_cases.json", [])
    write_if_missing(ws.state_dir / "artifacts.json", [])


def load_profile(ws: Workspace) -> UserProfile:
    data = read_json(ws.state_dir / "profile.json", UserProfile().model_dump())
    return UserProfile.model_validate(data)


def load_experiences(ws: Workspace) -> List[Experience]:
    data = read_json(ws.state_dir / "experiences.json", [])
    return [Experience.model_validate(item) for item in data]


def load_project(ws: Workspace) -> ApplicationProject:
    data = read_json(ws.state_dir / "project.json", ApplicationProject().model_dump())
    return ApplicationProject.model_validate(data)


def load_knowledge_sources(ws: Workspace) -> List[KnowledgeSource]:
    data = read_json(ws.state_dir / "knowledge_sources.json", [])
    return [KnowledgeSource.model_validate(item) for item in data]


def load_artifacts(ws: Workspace) -> List[GeneratedArtifact]:
    data = read_json(ws.state_dir / "artifacts.json", [])
    return [GeneratedArtifact.model_validate(item) for item in data]


def save_profile(ws: Workspace, profile: UserProfile) -> None:
    write_json(ws.state_dir / "profile.json", profile.model_dump())


def save_experiences(ws: Workspace, experiences: List[Experience]) -> None:
    write_json(
        ws.state_dir / "experiences.json", [item.model_dump() for item in experiences]
    )


def save_project(ws: Workspace, project: ApplicationProject) -> None:
    write_json(ws.state_dir / "project.json", project.model_dump())


def save_knowledge_sources(ws: Workspace, sources: List[KnowledgeSource]) -> None:
    write_json(
        ws.state_dir / "knowledge_sources.json", [item.model_dump() for item in sources]
    )


def load_success_cases(ws: Workspace) -> List[SuccessCase]:
    data = read_json(ws.state_dir / "success_cases.json", [])
    return [SuccessCase.model_validate(item) for item in data]


def save_success_cases(ws: Workspace, cases: List[SuccessCase]) -> None:
    write_json(
        ws.state_dir / "success_cases.json", [item.model_dump() for item in cases]
    )


def save_artifacts(ws: Workspace, artifacts: List[GeneratedArtifact]) -> None:
    write_json(
        ws.state_dir / "artifacts.json", [item.model_dump() for item in artifacts]
    )


def upsert_artifact(ws: Workspace, artifact: GeneratedArtifact) -> None:
    artifacts = load_artifacts(ws)
    filtered = [item for item in artifacts if item.id != artifact.id]
    filtered.append(artifact)
    save_artifacts(ws, filtered)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted JSON file {path}, backing up and resetting: {e}")
        backup_path = path.with_suffix(".json.bak")
        try:
            path.rename(backup_path)
            logger.info(f"Backed up corrupted file to {backup_path}")
        except OSError as backup_error:
            logger.warning(f"Could not backup corrupted file: {backup_error}")
        return default
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return default


def write_json(path: Path, data: Any) -> None:
    def _json_default(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable"
        )

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


def write_if_missing(path: Path, data: Any) -> None:
    if not path.exists():
        write_json(path, data)


def load_secrets(ws: Workspace) -> dict[str, Any]:
    """민감 개인정보를 로드합니다 (.secrets.json). 파일이 없으면 빈 dict 반환."""
    secrets_path = ws.root / ".secrets.json"
    return read_json(secrets_path, {})


def save_secrets(ws: Workspace, secrets: dict[str, Any]) -> None:
    """민감 개인정보를 저장합니다 (.secrets.json)."""
    secrets_path = ws.root / ".secrets.json"
    write_json(secrets_path, secrets)
