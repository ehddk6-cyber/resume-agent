from __future__ import annotations

from resume_agent.cli_tool_manager import CLIToolManager


def test_cli_tool_manager_supports_kilo(monkeypatch) -> None:
    monkeypatch.setattr(
        "resume_agent.cli_tool_manager.shutil.which",
        lambda _name: "/usr/bin/fake",
    )

    manager = CLIToolManager("kilo")

    assert manager.get_tool_info()["tool"] == "kilo"
    assert manager.get_tool_info()["prompt_options"] == ["run"]
