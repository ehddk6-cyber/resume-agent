"""대화형 Wizard 모듈 - 사용자 입력을 통한 프로젝트 설정 및 경험 가져오기"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.panel import Panel

from .models import (
    ApplicationProject,
    CareerStage,
    EvidenceLevel,
    Experience,
    Question,
    QuestionType,
    VerificationStatus,
)
from .domain import classify_question
from .vault import VaultManager
from .pdf_utils import extract_text_from_pdf, extract_jd_keywords

console = Console()


def run_wizard(workspace_path: Path, import_path: Optional[Path] = None, jd_path: Optional[Path] = None) -> dict:
    """
    대화형 위자드 실행
    
    Args:
        workspace_path: 워크스페이스 경로
        import_path: 가져올 경험 파일 경로 (선택)
        jd_path: 직무기술서 PDF 경로 (선택)
    
    Returns:
        생성된 프로젝트와 경험 정보
    """
    console.print(Panel.fit("🎯 [bold cyan]Resume Agent Wizard[/bold cyan]"))
    
    # Vault 설정 (기본 경로는 취업 디렉토리)
    vault_manager = VaultManager(Path("취업"))
    
    # 1. 전역 경험 데이터 가져오기 (Global Vault)
    global_experiences = vault_manager.load_global_experiences()
    experiences: List[Experience] = []
    
    if global_experiences:
        if Confirm.ask(f"\n🌍 Global Vault에서 {len(global_experiences)}개의 경험을 불러오시겠습니까?", default=True):
            experiences = global_experiences
            console.print("✅ Global Vault 동기화 완료.")
            
    # 2. 추가 경험 데이터 가져오기 (import_path)
    if import_path and import_path.exists():
        console.print(f"\n📄 [yellow]지정된 경험 파일에서 데이터를 가져오는 중...[/yellow]")
        imported = import_experiences_from_file(import_path)
        experiences.extend(imported)
        console.print(f"✅ [green]{len(imported)}개 경험을 추가로 가져왔습니다.[/green]")
    elif import_path:
        console.print(f"⚠️ [red]파일을 찾을 수 없습니다: {import_path}[/red]")
    
    # 3. 기존 경험 데이터 수동 확인
    if not experiences:
        if Confirm.ask("\n📁 기존 로컬 경험 데이터 파일(.docx 등)을 가져오시겠습니까?", default=False):
            file_path = Prompt.ask("📄 경험 파일 경로", default="취업/경험정리/경험요약정리.docx")
            imported = import_experiences_from_file(Path(file_path))
            if imported:
                experiences.extend(imported)
                console.print(f"✅ [green]{len(imported)}개 경험을 가져왔습니다.[/green]")
                
    # 3.5 자동 증빙 검증 및 Global Vault 갱신
    if experiences:
        console.print("\n🔍 [yellow]Global Vault(자격증/경력증명서) 스캔 및 증빙 검증 중...[/yellow]")
        verified_count = vault_manager.verify_experiences(experiences)
        if verified_count > 0:
            console.print(f"✅ [bold green]{verified_count}개의 경험이 L3/VERIFIED로 자동 승격되었습니다![/bold green]")
        
        # 전역 저장소에 병합 업데이트
        vault_manager.sync_to_global(experiences)
    
    # 4. 회사 정보 입력 및 JD 파싱
    console.print("\n🏢 [bold]회사 정보 입력[/bold]")
    company_name = Prompt.ask("회사명")
    job_title = Prompt.ask("직무명")
    
    company_type_choices = ["공공", "대기업", "중견", "스타트업"]
    company_type = Prompt.ask(
        "기업 유형",
        choices=company_type_choices,
        default="공공"
    )
    
    research_notes = ""
    if not jd_path:
        if Confirm.ask("\n📄 직무기술서(PDF) 또는 여러 JD가 있는 폴더를 분석하여 핵심 키워드를 추출하시겠습니까?", default=False):
            jd_path_str = Prompt.ask("PDF 파일 또는 폴더 경로", default="취업/직무기술서/")
            jd_path = Path(jd_path_str)
            
    if jd_path and jd_path.exists():
        console.print(f"🔍 [yellow]직무기술서({jd_path.name}) 분석 중...[/yellow]")
        jd_text = extract_text_from_pdf(jd_path)
        jd_keywords = extract_jd_keywords(jd_text)
        if jd_keywords:
            console.print(f"✅ 핵심 키워드 추출 성공: {', '.join(jd_keywords)}")
            research_notes = f"[JD 자동추출 키워드] {', '.join(jd_keywords)}\n(이 키워드들을 자소서 작성 시 핵심 역량으로 연결하세요.)"
    
    # 4. 자소서 문항 입력
    console.print("\n📝 [bold]자소서 문항 입력[/bold] (빈 줄로 종료)")
    questions: List[Question] = []
    question_num = 1
    
    while True:
        question_text = Prompt.ask(f"문항 {question_num}")
        if not question_text.strip():
            break
        
        char_limit_str = Prompt.ask("글자수 제한 (없으면 Enter)", default="")
        char_limit = int(char_limit_str) if char_limit_str.isdigit() else None
        
        detected_type = classify_question(question_text)
        
        questions.append(Question(
            id=f"q{question_num}",
            order_no=question_num,
            question_text=question_text,
            char_limit=char_limit,
            detected_type=detected_type,
        ))
        question_num += 1
    
    # 5. 경험 선택 (경험이 있는 경우)
    if experiences and questions:
        console.print("\n📊 [bold]문항별 경험 배분[/bold]")
        _show_experience_table(experiences)
        
        for question in questions:
            console.print(f"\n[Q{question.order_no}] {question.question_text[:50]}...")
            console.print(f"  유형: {question.detected_type.value}")
            
            # 추천 경험 표시
            recommended = _recommend_experiences(question, experiences)
            if recommended:
                console.print("  [cyan]추천 경험:[/cyan]")
                for i, exp in enumerate(recommended[:3], 1):
                    console.print(f"    {i}. {exp.title}")
            
            choice = Prompt.ask(
                "선택",
                default="1",
            )
            
            if choice.isdigit() and 1 <= int(choice) <= len(experiences):
                selected = experiences[int(choice) - 1]
                console.print(f"  ✅ [green]{selected.title}[/green] 선택됨")
    
    # 6. 프로젝트 생성
    project = ApplicationProject(
        company_name=company_name,
        job_title=job_title,
        company_type=company_type,
        research_notes=research_notes,
        questions=questions,
    )
    
    # 7. 저장
    from .state import save_project, save_experiences, initialize_state
    from .workspace import Workspace
    
    ws = Workspace(root=workspace_path)
    ws.ensure()
    initialize_state(ws)
    
    save_project(ws, project)
    if experiences:
        save_experiences(ws, experiences)
    
    console.print(f"\n✅ [bold green]저장 완료![/bold green]")
    console.print(f"  - {ws.state_dir / 'project.json'}")
    console.print(f"  - {ws.state_dir / 'experiences.json'}")
    
    return {
        "project": project,
        "experiences": experiences,
        "workspace": ws,
    }


def import_experiences_from_file(file_path: Path) -> List[Experience]:
    """
    파일에서 경험 데이터 가져오기
    
    Args:
        file_path: 경험 파일 경로
    
    Returns:
        경험 목록
    """
    suffix = file_path.suffix.lower()
    
    if suffix == ".docx":
        return parse_experience_docx(file_path)
    elif suffix == ".txt":
        return parse_experience_txt(file_path)
    elif suffix == ".json":
        return parse_experience_json(file_path)
    else:
        console.print(f"⚠️ [red]지원하지 않는 파일 형식: {suffix}[/red]")
        return []


def parse_experience_docx(file_path: Path) -> List[Experience]:
    """
    DOCX 파일에서 STAR 구조 파싱
    
    Args:
        file_path: DOCX 파일 경로
    
    Returns:
        경험 목록
    """
    try:
        from docx import Document
    except ImportError:
        console.print("⚠️ [red]python-docx가 설치되지 않았습니다.[/red]")
        return []
    
    doc = Document(file_path)
    full_text = "\n".join(para.text for para in doc.paragraphs)
    
    return _parse_star_text(full_text)


def parse_experience_txt(file_path: Path) -> List[Experience]:
    """
    TXT 파일에서 STAR 구조 파싱
    """
    text = file_path.read_text(encoding="utf-8")
    return _parse_star_text(text)


def parse_experience_json(file_path: Path) -> List[Experience]:
    """
    JSON 파일에서 경험 데이터 로드
    """
    import json
    
    data = json.loads(file_path.read_text(encoding="utf-8"))
    
    if isinstance(data, list):
        return [Experience.model_validate(item) for item in data]
    elif isinstance(data, dict) and "experiences" in data:
        return [Experience.model_validate(item) for item in data["experiences"]]
    
    return []


def _parse_star_text(text: str) -> List[Experience]:
    """
    STAR 구조 텍스트 파싱
    
    패턴:
    번호. 제목: 한 줄 요약
    
    상황(Situation): ...
    과제(Task): ...
    행동(Action): ...
    결과(Result): ...
    """
    experiences: List[Experience] = []
    
    # 경험 블록 분리 패턴
    block_pattern = re.compile(
        r'(\d+)\.\s*([^:]+):\s*([^\n]+)\s*'
        r'상황\(Situation\):\s*([^\n]+(?:\n(?!(?:과제|행동|결과|상황)\()[^\n]+)*)\s*'
        r'과제\(Task\):\s*([^\n]+(?:\n(?!(?:과제|행동|결과|상황)\()[^\n]+)*)\s*'
        r'행동\(Action\):\s*([^\n]+(?:\n(?!(?:과제|행동|결과|상황)\()[^\n]+)*)\s*'
        r'결과\(Result\):\s*([^\n]+(?:\n(?!(?:과제|행동|결과|상황|\d+\.)[^\n]+)*)*)',
        re.MULTILINE
    )
    
    for match in block_pattern.finditer(text):
        num = match.group(1)
        title = match.group(2).strip()
        summary = match.group(3).strip()
        situation = match.group(4).strip()
        task = match.group(5).strip()
        action = match.group(6).strip()
        result = match.group(7).strip()
        
        # 증거 수준 판단
        evidence_level = EvidenceLevel.L1
        if any(c in result for c in ["%", "건", "명", "배", "단축", "절감", "증가", "감소"]):
            evidence_level = EvidenceLevel.L3
        elif action:
            evidence_level = EvidenceLevel.L2
        
        # 태그 추출
        full_text = f"{title} {situation} {task} {action} {result}"
        tags = _extract_tags(full_text)
        
        # 조직명 추출
        organization = _extract_organization(full_text)
        
        exp = Experience(
            id=f"exp_{num}",
            title=title,
            organization=organization,
            period_start="",  # 추후 사용자 입력 필요
            situation=situation,
            task=task,
            action=action,
            result=result,
            evidence_level=evidence_level,
            tags=tags,
            verification_status=VerificationStatus.NEEDS_VERIFICATION,
        )
        experiences.append(exp)
    
    return experiences


def _extract_tags(text: str) -> List[str]:
    """텍스트에서 태그 추출"""
    tag_keywords = {
        "협업": ["협업", "협력", "팀워크", "동료"],
        "문제해결": ["문제", "해결", "개선", "방안"],
        "고객응대": ["고객", "민원", "응대", "서비스"],
        "데이터": ["데이터", "엑셀", "분석", "수치"],
        "리더십": ["리더", "주도", "이끌", "설득"],
        "성과": ["성과", "결과", "효율", "증가", "감소"],
        "갈등": ["갈등", "중재", "조율", "충돌"],
        "위기": ["위기", "긴급", "돌발", "혼란"],
    }
    
    tags = []
    for tag, keywords in tag_keywords.items():
        if any(kw in text for kw in keywords):
            tags.append(tag)
    
    return tags[:5]  # 최대 5개


def _extract_organization(text: str) -> str:
    """텍스트에서 조직명 추출"""
    # 일반적인 조직 패턴
    org_patterns = [
        r'([가-힣]+(?:시청|구청|공단|공사|은행|금고|재단|센터|도서관))',
        r'([가-힣]+(?:청|부|처|원|국|위원회))',
    ]
    
    for pattern in org_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return ""


def _show_experience_table(experiences: List[Experience]) -> None:
    """경험 목록 테이블 표시"""
    table = Table(title="경험 목록")
    table.add_column("#", style="cyan", width=3)
    table.add_column("제목", style="green")
    table.add_column("조직", style="yellow")
    table.add_column("증거수준", style="magenta", width=6)
    
    for i, exp in enumerate(experiences, 1):
        table.add_row(
            str(i),
            exp.title[:30] + ("..." if len(exp.title) > 30 else ""),
            exp.organization[:15] + ("..." if len(exp.organization) > 15 else ""),
            exp.evidence_level.value,
        )
    
    console.print(table)


def _recommend_experiences(question: Question, experiences: List[Experience]) -> List[Experience]:
    """문항에 맞는 경험 추천"""
    from .domain import score_experience
    
    scored = []
    for exp in experiences:
        result = score_experience(question, exp, [], [], None)
        scored.append((result["score"], exp))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [exp for _, exp in scored]
