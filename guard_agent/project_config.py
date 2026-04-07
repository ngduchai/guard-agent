"""Parser for the optional .guard-agent.yaml project configuration file.

The config file lets developers customize resilience settings (checkpoint mode,
interval, environment paths, hints). All fields are optional with sensible
defaults — the tool works with no config file at all.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from guard_agent.schemas import GuardAgentConfig


_CONFIG_FILENAME = ".guard-agent.yaml"


def find_config(start_dir: str | Path | None = None) -> Path | None:
    """Walk up from *start_dir* looking for .guard-agent.yaml.

    Returns the path to the config file, or None if not found.
    """
    directory = Path(start_dir or os.getcwd()).resolve()
    for parent in [directory, *directory.parents]:
        candidate = parent / _CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(
    path: str | Path | None = None,
    overrides: dict | None = None,
) -> GuardAgentConfig:
    """Load and validate .guard-agent.yaml, applying defaults for missing fields.

    If *path* is None, searches upward from cwd. If no config file is found,
    returns a config with all defaults.
    """
    config_data: dict = {}

    if path is not None:
        config_path = Path(path)
    else:
        config_path = find_config()

    if config_path is not None and config_path.is_file():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
            if isinstance(raw, dict):
                config_data = raw

    if overrides:
        config_data = _deep_merge(config_data, overrides)

    return GuardAgentConfig(**config_data)


def create_default_config() -> str:
    """Return the default .guard-agent.yaml content as a YAML string."""
    return """\
# guard-agent configuration
# All fields are optional — sensible defaults are used when omitted.

resilience:
  library: veloc            # Checkpoint library (currently only veloc supported)
  mode: memory              # memory (VeloC memory-based) or file-based
  checkpoint_interval: auto # auto (Young-Daly formula) or interval in seconds
  mtbf: 36000               # Mean Time Between Failures in seconds (10 hours)
  max_versions: 3           # Number of checkpoint versions to keep

environment:
  type: hpc                 # hpc or cloud
  scratch_dir: /tmp/veloc_scratch       # Node-local fast storage (ephemeral)
  persistent_dir: /tmp/veloc_persistent # Shared persistent storage

source:
  paths:                    # Source directories to analyze
    - src/
  language: auto            # auto (detect from extensions), c, or cpp
  build_system: cmake       # cmake or none

hints:
  critical_variables: []    # Manually specify variables to checkpoint
  checkpoint_location: main_loop  # Where to place checkpoints
"""


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
