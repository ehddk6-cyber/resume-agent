import re
import json
import datetime
from enum import Enum
from pathlib import Path
from typing import List, Set

from pydantic import BaseModel

from .models import Experience, EvidenceLevel, VerificationStatus


def _json_default(value):
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class VaultManager:
    """Global Vault (취업 디렉토리) 관리자"""

    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.global_state_dir = self.vault_root / "state"
        self.global_experiences_file = self.global_state_dir / "global_experiences.json"

        # Ensure global state dir exists
        if not self.global_state_dir.exists():
            self.global_state_dir.mkdir(parents=True, exist_ok=True)

    def load_global_experiences(self) -> List[Experience]:
        """전역 저장소에서 경험 목록을 불러옵니다."""
        if not self.global_experiences_file.exists():
            return []
        try:
            data = json.loads(self.global_experiences_file.read_text(encoding="utf-8"))
            return [Experience.model_validate(item) for item in data]
        except Exception:
            return []

    def save_global_experiences(self, experiences: List[Experience]) -> None:
        """경험 목록을 전역 저장소에 저장합니다."""
        data = [exp.model_dump() for exp in experiences]
        self.global_experiences_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )

    def sync_to_global(self, local_experiences: List[Experience]) -> None:
        """로컬 워크스페이스의 경험을 전역 저장소에 병합합니다 (충돌 해결 포함)."""
        global_exps = {exp.id: exp for exp in self.load_global_experiences()}

        updated_count = 0
        new_count = 0

        for local_exp in local_experiences:
            if local_exp.id in global_exps:
                global_exp = global_exps[local_exp.id]

                # 내용이 다른 경우에만 날짜 비교
                if local_exp.model_dump(
                    exclude={"updated_at"}
                ) != global_exp.model_dump(exclude={"updated_at"}):
                    # 로컬이 더 최신인 경우에만 갱신
                    if local_exp.updated_at > global_exp.updated_at:
                        global_exps[local_exp.id] = local_exp
                        updated_count += 1
            else:
                global_exps[local_exp.id] = local_exp
                new_count += 1

        if updated_count > 0 or new_count > 0:
            # 안전을 위해 백업 생성
            if self.global_experiences_file.exists():
                backup_file = self.global_experiences_file.with_suffix(".json.bak")
                import shutil

                shutil.copy2(self.global_experiences_file, backup_file)

            self.save_global_experiences(list(global_exps.values()))
            print(
                f"🌍 Global Vault 동기화: {new_count}개 신규, {updated_count}개 갱신 완료 (백업 생성됨)"
            )

    def scan_evidence_keywords(self) -> Set[str]:
        """자격증, 경력증명서 폴더에서 증빙 파일명 키워드를 추출합니다."""
        evidence_keywords = set()

        target_dirs = ["자격증", "경력증명서", "학교성적"]

        for dir_name in target_dirs:
            dir_path = self.vault_root / dir_name
            if not dir_path.exists() or not dir_path.is_dir():
                continue

            for file_path in dir_path.glob("*.*"):
                if file_path.is_file():
                    # 확장자 제거 후 키워드 추출 (예: "컴퓨터활용능력1급.pdf" -> "컴퓨터활용능력")
                    base_name = file_path.stem
                    # 특수문자 제거나 공백 기준 분리 등
                    clean_name = re.sub(r"[\(\)\[\]_]", " ", base_name).strip()
                    for word in clean_name.split():
                        if len(word) >= 2:  # 너무 짧은 단어 제외
                            evidence_keywords.add(word)

        return evidence_keywords

    def verify_experiences(self, experiences: List[Experience]) -> int:
        """
        경험 목록을 증빙 키워드와 대조하여 검증 상태를 자동 업데이트합니다.
        Returns: 검증(VERIFIED) 상태로 승격된 경험의 수
        """
        evidence_keywords = self.scan_evidence_keywords()
        if not evidence_keywords:
            return 0

        verified_count = 0

        for exp in experiences:
            # 이미 검증된 상태면 건너뜀
            if exp.verification_status == VerificationStatus.VERIFIED:
                continue

            # 경험의 제목이나 조직명에 증빙 키워드가 포함되어 있는지 확인
            search_text = f"{exp.title} {exp.organization}"

            is_verified = False
            matched_keywords = []
            for kw in evidence_keywords:
                if kw in search_text:
                    is_verified = True
                    matched_keywords.append(kw)

            if is_verified:
                exp.verification_status = VerificationStatus.VERIFIED
                exp.evidence_level = EvidenceLevel.L3
                if "자동 검증" not in exp.evidence_text:
                    exp.evidence_text = f"[자동 검증] 증빙 파일 발견 (키워드: {', '.join(matched_keywords)})\n{exp.evidence_text}".strip()
                verified_count += 1

        return verified_count
