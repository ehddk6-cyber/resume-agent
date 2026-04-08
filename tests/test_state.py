"""상태 관리 모듈 테스트"""

import json
from pathlib import Path

import pytest

from resume_agent.state import (
    initialize_state,
    read_json,
    write_json,
    write_if_missing,
    load_project,
    save_project,
    load_experiences,
    save_experiences,
    load_knowledge_sources,
    save_knowledge_sources,
    load_success_cases,
    save_success_cases,
    load_artifacts,
    save_artifacts,
    upsert_artifact,
)
from resume_agent.workspace import Workspace
from resume_agent.models import (
    ApplicationProject,
    Experience,
    GeneratedArtifact,
    ArtifactType,
    EvidenceLevel,
    SuccessCase,
    SuccessPattern,
)
from datetime import datetime, timezone


@pytest.fixture
def ws(tmp_path):
    workspace = Workspace(tmp_path)
    workspace.ensure()
    return workspace


class TestReadJson:
    def test_returns_default_when_missing(self, tmp_path):
        result = read_json(tmp_path / "missing.json", {"default": True})
        assert result == {"default": True}

    def test_reads_valid_json(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        assert read_json(f, {}) == {"key": "value"}

    def test_handles_corrupted_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{broken json", encoding="utf-8")
        result = read_json(f, [])
        assert result == []
        assert f.with_suffix(".json.bak").exists()

    def test_returns_list_default(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]", encoding="utf-8")
        assert read_json(f, []) == []


class TestWriteJson:
    def test_creates_file(self, tmp_path):
        f = tmp_path / "out.json"
        write_json(f, {"a": 1})
        assert f.exists()
        assert json.loads(f.read_text()) == {"a": 1}

    def test_overwrites_existing(self, tmp_path):
        f = tmp_path / "out.json"
        write_json(f, {"old": True})
        write_json(f, {"new": True})
        assert json.loads(f.read_text()) == {"new": True}

    def test_serializes_known_runtime_types_explicitly(self, tmp_path):
        f = tmp_path / "out.json"
        stamp = datetime(2026, 3, 30, 12, 34, tzinfo=timezone.utc)

        write_json(f, {"ts": stamp, "path": Path("/tmp/example")})

        assert json.loads(f.read_text()) == {
            "ts": stamp.isoformat(),
            "path": "/tmp/example",
        }

    def test_raises_for_unknown_runtime_type(self, tmp_path):
        f = tmp_path / "out.json"

        with pytest.raises(TypeError):
            write_json(f, {"bad": object()})


class TestWriteIfMissing:
    def test_creates_when_missing(self, tmp_path):
        f = tmp_path / "new.json"
        write_if_missing(f, {"x": 1})
        assert f.exists()

    def test_does_not_overwrite(self, tmp_path):
        f = tmp_path / "existing.json"
        f.write_text("original", encoding="utf-8")
        write_if_missing(f, "replacement")
        assert f.read_text() == "original"


class TestInitializeState:
    def test_creates_all_state_files(self, ws):
        initialize_state(ws)
        state_files = [
            ws.state_dir / "profile.json",
            ws.state_dir / "experiences.json",
            ws.state_dir / "project.json",
            ws.state_dir / "knowledge_sources.json",
            ws.state_dir / "success_cases.json",
            ws.state_dir / "artifacts.json",
        ]
        for f in state_files:
            assert f.exists(), f"Missing: {f}"

    def test_idempotent(self, ws):
        initialize_state(ws)
        initialize_state(ws)
        experiences = load_experiences(ws)
        assert len(experiences) >= 1


class TestProject:
    def test_save_and_load(self, ws):
        project = ApplicationProject(
            company_name="TestCo", job_title="Engineer", career_stage="SENIOR"
        )
        save_project(ws, project)
        loaded = load_project(ws)
        assert loaded.company_name == "TestCo"
        assert loaded.job_title == "Engineer"
        assert loaded.career_stage.value == "SENIOR"


class TestExperiences:
    def test_save_and_load(self, ws):
        exps = [
            Experience(
                id="e1",
                title="Test Exp",
                organization="Test Org",
                period_start="2024-01-01",
                situation="situation text",
                task="task text",
                action="action text",
                result="result text",
                evidence_level=EvidenceLevel.L2,
            )
        ]
        save_experiences(ws, exps)
        loaded = load_experiences(ws)
        assert len(loaded) == 1
        assert loaded[0].title == "Test Exp"

    def test_empty_list(self, ws):
        save_experiences(ws, [])
        assert load_experiences(ws) == []


class TestKnowledgeSources:
    def test_save_and_load(self, ws):
        save_knowledge_sources(ws, [])
        assert load_knowledge_sources(ws) == []


class TestArtifacts:
    def test_upsert_adds_new(self, ws):
        artifact = GeneratedArtifact(
            id="art-1",
            artifact_type=ArtifactType.WRITER,
            accepted=True,
            output_path="out.md",
            raw_output_path="raw.md",
            created_at=datetime.now(timezone.utc),
        )
        upsert_artifact(ws, artifact)
        artifacts = load_artifacts(ws)
        assert len(artifacts) == 1
        assert artifacts[0].id == "art-1"

    def test_upsert_replaces_existing(self, ws):
        a1 = GeneratedArtifact(
            id="art-1",
            artifact_type=ArtifactType.WRITER,
            accepted=False,
            output_path="old.md",
            raw_output_path="old_raw.md",
            created_at=datetime.now(timezone.utc),
        )
        a2 = GeneratedArtifact(
            id="art-1",
            artifact_type=ArtifactType.WRITER,
            accepted=True,
            output_path="new.md",
            raw_output_path="new_raw.md",
            created_at=datetime.now(timezone.utc),
        )
        upsert_artifact(ws, a1)
        upsert_artifact(ws, a2)
        artifacts = load_artifacts(ws)
        assert len(artifacts) == 1
        assert artifacts[0].accepted is True


class TestSuccessCases:
    def test_save_and_load(self, ws):
        cases = [
            SuccessCase(
                title="A / 사무 / 2025",
                company_name="테스트회사",
                job_title="사무",
                detected_patterns=[
                    SuccessPattern.STAR_STRUCTURE,
                    SuccessPattern.QUANTIFIED_RESULT,
                ],
            ),
            SuccessCase(
                title="B / 개발 / 2025",
                company_name="테스트회사2",
                job_title="개발",
                detected_patterns=[SuccessPattern.COLLABORATION],
            ),
        ]
        save_success_cases(ws, cases)
        loaded = load_success_cases(ws)
        assert len(loaded) == 2
        assert loaded[0].company_name == "테스트회사"
        assert loaded[0].detected_patterns[0] == SuccessPattern.STAR_STRUCTURE
        assert loaded[1].detected_patterns[0] == SuccessPattern.COLLABORATION

    def test_empty_list(self, ws):
        save_success_cases(ws, [])
        assert load_success_cases(ws) == []

    def test_roundtrip_preserves_enum_values(self, ws):
        cases = [
            SuccessCase(
                title="C",
                company_name="회사C",
                detected_patterns=[
                    SuccessPattern.PROBLEM_SOLVING,
                    SuccessPattern.GROWTH_STORY,
                ],
            )
        ]
        save_success_cases(ws, cases)
        loaded = load_success_cases(ws)
        for pattern in loaded[0].detected_patterns:
            assert isinstance(pattern, SuccessPattern)
        assert SuccessPattern.PROBLEM_SOLVING in loaded[0].detected_patterns
        assert SuccessPattern.GROWTH_STORY in loaded[0].detected_patterns
