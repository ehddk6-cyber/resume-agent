from typing import List
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from .models import Experience
from .workspace import Workspace
from .state import load_experiences, save_experiences, initialize_state

console = Console()


def run_editor(ws: Workspace) -> None:
    """터미널 기반 경험 데이터 에디터"""
    ws.ensure()
    initialize_state(ws)

    experiences = load_experiences(ws)
    if not experiences:
        console.print(
            "[yellow]현재 등록된 경험이 없습니다. 먼저 wizard나 mine-past를 통해 경험을 추가하세요.[/yellow]"
        )
        return

    while True:
        console.clear()
        console.print("🎯 [bold cyan]경험 뱅크 에디터[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("번호", style="dim", width=4)
        table.add_column("제목", width=30)
        table.add_column("조직", width=15)
        table.add_column("수치/성과", width=20)
        table.add_column("증거수준")

        for idx, exp in enumerate(experiences):
            table.add_row(
                str(idx + 1),
                exp.title,
                exp.organization,
                exp.metrics[:20] + "..." if len(exp.metrics) > 20 else exp.metrics,
                exp.evidence_level.value,
            )

        console.print(table)
        console.print("\n[dim]수정할 번호를 입력하세요. (종료: q)[/dim]")

        choice = Prompt.ask("선택")
        if choice.lower() == "q":
            save_experiences(ws, experiences)
            console.print("[green]변경사항이 저장되었습니다.[/green]")
            break

        if choice.isdigit() and 1 <= int(choice) <= len(experiences):
            idx = int(choice) - 1
            exp = experiences[idx]

            console.print(f"\n[bold]현재 경험 수정:[/bold] {exp.title}")
            new_title = Prompt.ask("제목", default=exp.title)
            new_action = Prompt.ask("행동(Action)", default=exp.action)
            new_metrics = Prompt.ask("수치(Metrics)", default=exp.metrics)

            exp.title = new_title
            exp.action = new_action
            exp.metrics = new_metrics

            # 수치가 추가되었다면 증거 수준 L3로 자동 상향
            if new_metrics and new_metrics != "정량 수치 없음":
                exp.evidence_level = "L3"
                console.print(
                    "[yellow]수치 데이터가 감지되어 증거수준이 L3로 조정되었습니다.[/yellow]"
                )

            experiences[idx] = exp
            console.print("[green]수정되었습니다.[/green]")
            Prompt.ask("계속하려면 Enter를 누르세요", default="")
