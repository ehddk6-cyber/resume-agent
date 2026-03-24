"""
다중 CLI 도구 지원 - 사용자가 제공한 CLI 도구 중 선택하여 사용
"""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class CLITool(Enum):
    """지원하는 CLI 도구 목록"""
    CODEX = "codex"
    CLAUDE = "claude"
    GEMINI = "gemini"
    CLINE = "cline"


class CLIToolManager:
    """
    사용자가 제공한 CLI 도구 중 선택하여 사용
    
    장점:
    - 사용자 자유도 향상 (원하는 도구 선택 가능)
    - API 키 불필요 (CLI 도구 직접 호출)
    - 단순한 구조 (폴백 로직 없음)
    """
    
    # CLI 도구별 실행 명령어
    TOOL_COMMANDS = {
        CLITool.CODEX: "codex",
        CLITool.CLAUDE: "claude",
        CLITool.GEMINI: "gemini",
        CLITool.CLINE: "cline"
    }
    
    # CLI 도구별 프롬프트 옵션
    TOOL_PROMPT_OPTIONS = {
        CLITool.CODEX: ["-p"],
        CLITool.CLAUDE: ["-p"],
        CLITool.GEMINI: ["--prompt"],
        CLITool.CLINE: ["--prompt"]
    }
    
    def __init__(self, tool_name: str = "codex"):
        """
        Args:
            tool_name: 사용할 CLI 도구 이름 (codex, claude, gemini, cline)
        """
        try:
            self.tool = CLITool(tool_name.lower())
        except ValueError:
            raise ValueError(
                f"지원하지 않는 도구: {tool_name}\n"
                f"지원하는 도구: {', '.join([t.value for t in CLITool])}"
            )
        
        self.tool_command = self.TOOL_COMMANDS[self.tool]
        self.prompt_options = self.TOOL_PROMPT_OPTIONS[self.tool]
        
        # 도구가 설치되어 있는지 확인
        if not self.is_available():
            raise RuntimeError(
                f"{self.tool.value} CLI 도구를 찾을 수 없습니다.\n"
                f"설치 방법: {self._get_installation_guide()}"
            )
    
    def is_available(self) -> bool:
        """CLI 도구가 설치되어 있는지 확인"""
        return shutil.which(self.tool_command) is not None
    
    def _get_installation_guide(self) -> str:
        """CLI 도구 설치 가이드 반환"""
        guides = {
            CLITool.CODEX: "npm install -g @openai/codex",
            CLITool.CLAUDE: "npm install -g @anthropic-ai/claude-cli",
            CLITool.GEMINI: "pip install google-generativeai",
            CLITool.CLINE: "npm install -g cline"
        }
        return guides.get(self.tool, "공식 문서를 참조하세요.")
    
    def execute(self, prompt: str, timeout: int = 300) -> str:
        """
        선택된 CLI 도구로 프롬프트 실행
        
        Args:
            prompt: 실행할 프롬프트
            timeout: 타임아웃 (초)
        
        Returns:
            CLI 도구의 출력 결과
        
        Raises:
            RuntimeError: 실행 실패 시
            TimeoutExpired: 타임아웃 시
        """
        # 명령어 구성
        cmd = [self.tool_command] + self.prompt_options + [prompt]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"{self.tool.value} 실행 실패 (exit code: {result.returncode})\n"
                    f"stderr: {result.stderr}"
                )
            
            return result.stdout
        
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"{self.tool.value} 실행 타임아웃 ({timeout}초 초과)"
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"{self.tool.value} CLI 도구를 찾을 수 없습니다.\n"
                f"설치 방법: {self._get_installation_guide()}"
            )
    
    def execute_with_file(self, prompt_file: Path, timeout: int = 300) -> str:
        """
        프롬프트 파일을 사용하여 실행
        
        Args:
            prompt_file: 프롬프트 파일 경로
            timeout: 타임아웃 (초)
        
        Returns:
            CLI 도구의 출력 결과
        """
        if not prompt_file.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        return self.execute(prompt, timeout)
    
    def get_tool_info(self) -> Dict[str, Any]:
        """현재 사용 중인 도구 정보 반환"""
        return {
            "tool": self.tool.value,
            "command": self.tool_command,
            "available": self.is_available(),
            "prompt_options": self.prompt_options
        }


def get_available_tools() -> list[str]:
    """설치된 CLI 도구 목록 반환"""
    available = []
    for tool in CLITool:
        if shutil.which(CLIToolManager.TOOL_COMMANDS[tool]):
            available.append(tool.value)
    return available


def create_cli_tool_manager(tool_name: str = "codex") -> CLIToolManager:
    """CLIToolManager 인스턴스 생성 편의 함수"""
    return CLIToolManager(tool_name)