"""
app_registry.py – Discover and load benchmark application configurations.

Scans the ``tests/benchmark/vanillas/`` directory for apps with ``app.yaml``
files and provides a registry of benchmark applications for the validation
pipeline.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from guard_agent.schemas import (
    AppConfig,
    BuildConfig,
    CheckpointLibConfig,
    ComparisonConfig,
    RunConfig,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BENCHMARK_ROOT = "tests/benchmark"
_VANILLAS_DIR = "vanillas"
_CHECKPOINTED_DIR = "checkpointed"
_DOCS_DIR = "docs"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_apps(project_root: Path) -> list[Path]:
    """Find all vanilla app directories that contain an ``app.yaml``."""
    vanillas = project_root / _BENCHMARK_ROOT / _VANILLAS_DIR
    if not vanillas.is_dir():
        return []
    return sorted(
        d for d in vanillas.iterdir()
        if d.is_dir() and (d / "app.yaml").is_file()
    )


def load_app_config(app_dir: Path) -> AppConfig:
    """Load and validate an ``app.yaml`` file into an :class:`AppConfig`."""
    yaml_path = app_dir / "app.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(f"No app.yaml found in {app_dir}")

    with open(yaml_path) as f:
        raw = yaml.safe_load(f)

    return AppConfig(
        name=raw["name"],
        category=raw.get("category", "unknown"),
        language=raw.get("language", "cpp"),
        description=raw.get("description", ""),
        mpi_ranks=raw.get("mpi_ranks", 4),
        build=BuildConfig(**raw.get("build", {})),
        run=RunConfig(**raw.get("run", {})),
        comparison=ComparisonConfig(**raw.get("comparison", {})),
        checkpoint=CheckpointLibConfig(**raw.get("checkpoint", {})),
    )


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def vanilla_dir(project_root: Path, app_name: str) -> Path:
    """Return the vanilla source directory for an app."""
    return project_root / _BENCHMARK_ROOT / _VANILLAS_DIR / app_name


def checkpointed_dir(project_root: Path, app_name: str) -> Path:
    """Return the checkpointed source directory for an app."""
    return project_root / _BENCHMARK_ROOT / _CHECKPOINTED_DIR / app_name


def docs_dir(project_root: Path, app_name: str) -> Path:
    """Return the documentation directory for an app."""
    return project_root / _BENCHMARK_ROOT / _DOCS_DIR / app_name


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class AppRegistry:
    """Registry of all benchmark applications discovered in the project."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._apps: dict[str, AppConfig] = {}
        self._refresh()

    def _refresh(self) -> None:
        self._apps.clear()
        for app_path in discover_apps(self._root):
            cfg = load_app_config(app_path)
            self._apps[cfg.name] = cfg

    @property
    def apps(self) -> dict[str, AppConfig]:
        return dict(self._apps)

    def get(self, name: str) -> AppConfig | None:
        return self._apps.get(name)

    def by_category(self, category: str) -> list[AppConfig]:
        return [a for a in self._apps.values() if a.category == category]

    def categories(self) -> list[str]:
        return sorted({a.category for a in self._apps.values()})

    def has_checkpointed(self, name: str) -> bool:
        return checkpointed_dir(self._root, name).is_dir()

    def vanilla_path(self, name: str) -> Path:
        return vanilla_dir(self._root, name)

    def checkpointed_path(self, name: str) -> Path:
        return checkpointed_dir(self._root, name)

    def __len__(self) -> int:
        return len(self._apps)

    def __iter__(self):
        return iter(self._apps.values())
