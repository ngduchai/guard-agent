"""Regression tests for ``runner._find_executable``.

Specifically covers the dangling-symlink case discovered while debugging
PRK_Stencil BLOCKED on 2026-05-19 (see ISSUES.md entry):

  - ``baseline_cache/PRK_Stencil/stencil`` was a top-level symlink that
    once pointed at the vanilla in-tree binary; after deep-strip the
    target was removed, leaving a dangling symlink.
  - ``os.walk`` lists dangling symlinks in ``files``, so the previous
    ``_find_executable`` returned the dangling path and mpirun then
    crashed with "could not access or execute an executable".
  - The real binary lived deeper at ``_build/Stencil/stencil``.

The fix: ``_find_executable`` now skips entries that fail ``exists()``
(rejects dangling symlinks) and ``os.access(..., X_OK)`` (rejects
same-named non-executable files), so the recursive walk reaches the
real binary.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from validation.veloc.runner import _find_executable


def _touch_exec(path: Path) -> Path:
    """Create an empty file at *path* with the executable bit set."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def test_finds_canonical_build_bin(tmp_path: Path) -> None:
    exe = _touch_exec(tmp_path / "_build" / "bin" / "myapp")
    assert _find_executable(tmp_path, "myapp") == exe


def test_finds_top_level_executable(tmp_path: Path) -> None:
    exe = _touch_exec(tmp_path / "myapp")
    assert _find_executable(tmp_path, "myapp") == exe


def test_finds_deeply_nested_executable_via_walk(tmp_path: Path) -> None:
    exe = _touch_exec(tmp_path / "_build" / "Stencil" / "stencil")
    assert _find_executable(tmp_path, "stencil") == exe


def test_dangling_top_level_symlink_does_not_shadow_real_binary(
    tmp_path: Path,
) -> None:
    """The PRK_Stencil regression: top-level dangling symlink + real
    binary nested deeper. _find_executable must skip the dangling entry
    and return the real binary."""
    dangling_target = tmp_path / "vanilla_src" / "stencil"  # never created
    (tmp_path / "stencil").symlink_to(dangling_target)
    real_exe = _touch_exec(tmp_path / "_build" / "Stencil" / "stencil")

    resolved = _find_executable(tmp_path, "stencil")
    assert resolved == real_exe
    # And critically: NOT the dangling symlink path
    assert resolved != tmp_path / "stencil"


def test_dangling_nested_symlink_does_not_shadow_real_binary(
    tmp_path: Path,
) -> None:
    """Same as above but the dangling entry sits inside a subdir that
    os.walk descends into BEFORE the real binary's subdir."""
    # Force an early dangling hit by naming the subdir lexicographically
    # ahead of the real one.
    (tmp_path / "a_dir").mkdir()
    (tmp_path / "a_dir" / "myapp").symlink_to(tmp_path / "missing_target")
    real_exe = _touch_exec(tmp_path / "z_dir" / "myapp")

    resolved = _find_executable(tmp_path, "myapp")
    assert resolved == real_exe


def test_same_named_non_executable_data_file_is_skipped(tmp_path: Path) -> None:
    """A data file with the same basename but no +x bit must not be
    returned; the walk should continue and find the real executable."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "stencil").write_text("# this is config, not the binary\n")
    real_exe = _touch_exec(tmp_path / "_build" / "Stencil" / "stencil")

    assert _find_executable(tmp_path, "stencil") == real_exe


def test_missing_executable_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="myapp"):
        _find_executable(tmp_path, "myapp")


def test_only_dangling_symlink_present_raises(tmp_path: Path) -> None:
    """If the ONLY match is dangling, we must raise rather than return
    an unrunnable path."""
    (tmp_path / "myapp").symlink_to(tmp_path / "nowhere")
    with pytest.raises(FileNotFoundError, match="myapp"):
        _find_executable(tmp_path, "myapp")
