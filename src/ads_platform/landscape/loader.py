from __future__ import annotations

from pathlib import Path

from ads_platform.landscape.artifact import EmpiricalLandscapeArtifact
from ads_platform.landscape.empirical import EmpiricalLandscapeModel


def load_empirical_landscape(path: str | Path) -> EmpiricalLandscapeModel:
    return EmpiricalLandscapeArtifact.read_json(path).build_model()
