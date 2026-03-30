"""
체크포인트 시스템 - 파이프라인 중간 실패 시 특정 단계부터 재시작 가능
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointManager:
    """각 단계 완료 시 체크포인트를 저장하고, 특정 단계부터 재시작할 수 있도록 관리"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.checkpoint_dir = workspace_root / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(
        self,
        step: str,
        state: Dict[str, Any],
        *,
        status: str = "success",
        error: Optional[str] = None,
    ) -> Path:
        """
        각 단계 완료 시 체크포인트 저장
        
        Args:
            step: 단계 이름 (예: "coach", "writer", "interview")
            state: 저장할 상태 데이터
            status: 체크포인트 상태 ("success" | "failed")
            error: 실패 시 에러 요약
        
        Returns:
            저장된 체크포인트 파일 경로
        """
        checkpoint_path = self.checkpoint_dir / f"{step}.json"
        
        checkpoint_data = {
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "error": error,
            "state": state,
        }
        
        temp_path = checkpoint_path.with_suffix(".json.tmp")
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        temp_path.replace(checkpoint_path)
        
        return checkpoint_path
    
    def load_checkpoint(self, step: str) -> Optional[Dict[str, Any]]:
        """
        특정 단계의 체크포인트 로드
        
        Args:
            step: 단계 이름
        
        Returns:
            저장된 상태 데이터 또는 None
        """
        checkpoint_path = self.checkpoint_dir / f"{step}.json"
        
        if not checkpoint_path.exists():
            return None
        
        checkpoint_data = self._read_checkpoint_file(checkpoint_path)
        if checkpoint_data is None:
            return None
        
        return checkpoint_data.get("state")
    
    def has_checkpoint(self, step: str) -> bool:
        """특정 단계의 체크포인트 존재 여부 확인"""
        checkpoint_path = self.checkpoint_dir / f"{step}.json"
        return checkpoint_path.exists()
    
    def list_checkpoints(self) -> list[str]:
        """저장된 모든 체크포인트 목록 반환"""
        checkpoints = []
        for file in self.checkpoint_dir.glob("*.json"):
            checkpoints.append(file.stem)
        return sorted(checkpoints)
    
    def get_checkpoint_info(self, step: str) -> Optional[Dict[str, Any]]:
        """체크포인트의 메타데이터 정보 반환"""
        checkpoint_path = self.checkpoint_dir / f"{step}.json"
        
        if not checkpoint_path.exists():
            return None
        
        checkpoint_data = self._read_checkpoint_file(checkpoint_path)
        if checkpoint_data is None:
            return None
        
        return {
            "step": checkpoint_data.get("step"),
            "timestamp": checkpoint_data.get("timestamp"),
            "status": checkpoint_data.get("status", "success"),
            "error": checkpoint_data.get("error"),
            "file_path": str(checkpoint_path),
        }
    
    def delete_checkpoint(self, step: str) -> bool:
        """특정 체크포인트 삭제"""
        checkpoint_path = self.checkpoint_dir / f"{step}.json"
        
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            return True
        return False
    
    def clear_all_checkpoints(self) -> int:
        """모든 체크포인트 삭제"""
        count = 0
        for file in self.checkpoint_dir.glob("*.json"):
            file.unlink()
            count += 1
        return count
    
    def get_resume_point(self) -> Optional[str]:
        """
        재시작할 수 있는 가장 마지막 단계 반환
        
        Returns:
            재시작 가능한 단계 이름 또는 None
        """
        pipeline_order = ["coach", "writer", "interview", "export"]
        completed_steps = set(self.list_checkpoints())
        last_contiguous_step: Optional[str] = None

        for step in pipeline_order:
            if step not in completed_steps:
                break
            last_contiguous_step = step

        return last_contiguous_step

    def _read_checkpoint_file(self, checkpoint_path: Path) -> Optional[Dict[str, Any]]:
        """체크포인트 파일을 안전하게 읽고 손상 시 None 반환"""
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

        return data if isinstance(data, dict) else None


def create_checkpoint_manager(workspace_root: Path) -> CheckpointManager:
    """CheckpointManager 인스턴스 생성 편의 함수"""
    return CheckpointManager(workspace_root)
