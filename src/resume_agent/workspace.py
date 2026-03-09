from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def profile_dir(self) -> Path:
        return self.root / "profile"

    @property
    def targets_dir(self) -> Path:
        return self.profile_dir / "targets"

    @property
    def sources_raw_dir(self) -> Path:
        return self.root / "sources" / "raw"

    @property
    def sources_normalized_dir(self) -> Path:
        return self.root / "sources" / "normalized"

    @property
    def sources_extracted_dir(self) -> Path:
        return self.root / "sources" / "extracted"

    @property
    def analysis_dir(self) -> Path:
        return self.root / "analysis"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @property
    def outputs_dir(self) -> Path:
        return self.root / "outputs"

    @property
    def prompts_dir(self) -> Path:
        return self.root / "prompts"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    def ensure(self) -> None:
        for path in (
            self.profile_dir,
            self.targets_dir,
            self.sources_raw_dir,
            self.sources_normalized_dir,
            self.sources_extracted_dir,
            self.analysis_dir,
            self.artifacts_dir,
            self.outputs_dir,
            self.prompts_dir,
            self.runs_dir,
            self.state_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        return self.root / relative_path
