"""
프로그레스바 및 상태 표시 - 파이프라인 진행 상황 시각화
"""

from __future__ import annotations

import shutil
import sys
import time
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class ProgressBar:
    """
    터미널 기반 프로그레스바
    
    기능:
    - 단계별 진행 상황 표시
    - 성공/실패 상태 표시
    - 예상 시간 표시
    """
    
    def __init__(self, total_steps: int, description: str = "진행 중"):
        if total_steps <= 0:
            raise ValueError("total_steps는 1 이상이어야 합니다.")
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = time.time()
        self.steps: List[Dict[str, Any]] = []
        encoding = (sys.stdout.encoding or "").lower()
        self.use_unicode = "utf" in encoding
    
    def update(self, step_name: str, status: str = "running") -> None:
        """
        진행 상황 업데이트
        
        Args:
            step_name: 단계 이름
            status: 상태 ("running", "success", "failed", "skipped")
        """
        self.current_step += 1
        
        step_info = {
            "name": step_name,
            "status": status,
            "step": self.current_step
        }
        self.steps.append(step_info)
        
        self._display()
    
    def _display(self) -> None:
        """프로그레스바 표시"""
        # 진행률 계산
        progress = self.current_step / self.total_steps
        bar_length = 40
        filled = int(bar_length * progress)
        if self.use_unicode:
            bar = "█" * filled + "░" * (bar_length - filled)
        else:
            bar = "#" * filled + "-" * (bar_length - filled)
        
        # 상태 아이콘
        current_step_info = self.steps[-1] if self.steps else {}
        status_icon = {
            "running": "⏳" if self.use_unicode else "...",
            "success": "✅" if self.use_unicode else "OK",
            "failed": "❌" if self.use_unicode else "X",
            "skipped": "⏭️" if self.use_unicode else ">>"
        }.get(current_step_info.get("status", ""), "⏳" if self.use_unicode else "...")
        
        # 경과 시간
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        
        # 예상 남은 시간
        if progress > 0:
            eta = (elapsed / progress) * (1 - progress)
            eta_str = self._format_time(eta)
        else:
            eta_str = "계산 중..."
        
        # 출력
        step_name = current_step_info.get("name", "")
        terminal_width = shutil.get_terminal_size(fallback=(120, 20)).columns
        line = (
            f"{status_icon} [{bar}] {self.current_step}/{self.total_steps} - "
            f"{step_name} | 경과: {elapsed_str} | 남은: {eta_str}"
        )
        max_width = max(20, terminal_width - 1)
        if len(line) > max_width:
            line = line[: max_width - 3] + "..."
        print(f"\r{line}", end="", flush=True)
        
        # 완료 시 줄바꿈
        if self.current_step >= self.total_steps:
            print()
    
    def _format_time(self, seconds: float) -> str:
        """시간 포맷팅"""
        if seconds < 60:
            return f"{seconds:.0f}초"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}분"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}시간"
    
    def finish(self, status: str = "success") -> None:
        """프로그레스바 완료"""
        self.current_step = self.total_steps
        
        # 최종 상태 표시
        status_icon = {
            "success": "✅" if self.use_unicode else "OK",
            "failed": "❌" if self.use_unicode else "X"
        }.get(status, "✅" if self.use_unicode else "OK")
        status_text = "완료" if status == "success" else "실패"
        
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        
        print(f"\n{status_icon} {self.description} {status_text} (소요 시간: {elapsed_str})")


class StepProgress:
    """
    단계별 진행 상황 표시 (프로그레스바 없이)
    
    사용법:
    ```python
    with StepProgress("파이프라인 실행") as progress:
        progress.step("코칭 시작")
        # 작업 수행
        progress.step("코칭 완료", status="success")
    ```
    """
    
    def __init__(self, description: str = "진행 중"):
        self.description = description
        self.steps: List[Dict[str, Any]] = []
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        print(f"\n{'='*60}")
        print(f"🚀 {self.description} 시작")
        print(f"{'='*60}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        
        if exc_type is None:
            print(f"\n{'='*60}")
            print(f"✅ {self.description} 완료 (소요 시간: {elapsed_str})")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print(f"❌ {self.description} 실패 (소요 시간: {elapsed_str})")
            print(f"   오류: {exc_val}")
            print(f"{'='*60}")
        
        return False
    
    def step(self, name: str, status: str = "running") -> None:
        """
        단계 업데이트
        
        Args:
            name: 단계 이름
            status: 상태 ("running", "success", "failed", "skipped")
        """
        status_icon = {
            "running": "⏳",
            "success": "✅",
            "failed": "❌",
            "skipped": "⏭️"
        }.get(status, "⏳")
        
        print(f"  {status_icon} {name}")
        
        self.steps.append({
            "name": name,
            "status": status
        })
    
    def _format_time(self, seconds: float) -> str:
        """시간 포맷팅"""
        if seconds < 60:
            return f"{seconds:.0f}초"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}분"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}시간"


@contextmanager
def progress_bar(total_steps: int, description: str = "진행 중"):
    """
    프로그레스바 컨텍스트 매니저
    
    사용법:
    ```python
    with progress_bar(5, "파이프라인 실행") as bar:
        bar.update("1단계", "success")
        bar.update("2단계", "success")
    ```
    """
    bar = ProgressBar(total_steps, description)
    try:
        yield bar
        bar.finish("success")
    except Exception:
        bar.finish("failed")
        raise


@contextmanager
def step_progress(description: str = "진행 중"):
    """
    단계별 진행 컨텍스트 매니저
    
    사용법:
    ```python
    with step_progress("파이프라인 실행") as progress:
        progress.step("코칭 시작")
        progress.step("코칭 완료", status="success")
    """
    progress = StepProgress(description)
    with progress:
        yield progress


def print_status(message: str, status: str = "info") -> None:
    """
    상태 메시지 출력
    
    Args:
        message: 메시지
        status: 상태 ("info", "success", "warning", "error")
    """
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = icons.get(status, "ℹ️")
    print(f"{icon} {message}")


def print_header(title: str) -> None:
    """헤더 출력"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")


def print_footer(message: str = "완료") -> None:
    """푸터 출력"""
    print(f"{'='*60}")
    print(f"✅ {message}")
    print(f"{'='*60}\n")
