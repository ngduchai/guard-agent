"""Regression tests for ``runner._build_missing_veloc_cfg_message``.

Context: 2026-05-24 Nyx blocker.  The LLM placed ``veloc.cfg`` at
``build/tests_baseline/Nyx/Exec/HydroTests/veloc.cfg`` (a subdir of the
build).  The validator at runner.py:1971-1990 searches ONLY two fixed
paths (build_dir and source_dir roots) and raised an opaque FATAL the
LLM could not act on, so iter looped 27 times on the same failure.

The fix keeps the two-path search intact (per the OpenCode permission
model: only ``build/tests_baseline/<APP>/`` is writable, so the search
order itself is correct) but rewrites the FATAL into an actionable
message that:
  1. lists both exact paths checked,
  2. flags which one is writable from the LLM sandbox,
  3. surfaces any misplaced ``veloc.cfg`` already in the source tree
     (this is the Nyx case),
  4. embeds a minimal cfg template.
"""

from __future__ import annotations

from pathlib import Path

from validation.veloc.runner import _build_missing_veloc_cfg_message


def test_message_lists_both_expected_paths(tmp_path: Path) -> None:
    """Message must include the two exact search paths verbatim."""
    src = tmp_path / "src"
    build = tmp_path / "build"
    src.mkdir()
    build.mkdir()
    msg = _build_missing_veloc_cfg_message(src, build, "veloc.cfg")
    assert str(src / "veloc.cfg") in msg
    assert str(build / "veloc.cfg") in msg


def test_message_recommends_source_dir_as_writable(tmp_path: Path) -> None:
    """The recommendation must point at source_dir (not build_dir)."""
    src = tmp_path / "src"
    build = tmp_path / "build"
    src.mkdir()
    build.mkdir()
    msg = _build_missing_veloc_cfg_message(src, build, "veloc.cfg")
    # The recommended path is the one annotated "CREATE IT HERE".
    expected_primary = str(src / "veloc.cfg")
    recommended_line = next(
        ln for ln in msg.splitlines() if "CREATE IT HERE" in ln
    )
    assert expected_primary in recommended_line
    # build_dir must be marked as deny-listed, never as the target.
    denied_line = next(
        ln for ln in msg.splitlines() if "deny-listed" in ln
    )
    assert str(build / "veloc.cfg") in denied_line


def test_message_includes_template_with_required_keys(tmp_path: Path) -> None:
    """Required cfg keys must appear so the LLM can compose a valid cfg."""
    msg = _build_missing_veloc_cfg_message(
        tmp_path / "src", tmp_path / "build", "veloc.cfg",
    )
    assert "scratch" in msg
    assert "persistent" in msg
    assert "mode" in msg


def test_message_surfaces_misplaced_cfg_in_subdir(tmp_path: Path) -> None:
    """Nyx case: LLM put cfg in a subdir → diagnostic must point at it."""
    src = tmp_path / "src"
    (src / "Exec" / "HydroTests").mkdir(parents=True)
    misplaced = src / "Exec" / "HydroTests" / "veloc.cfg"
    misplaced.write_text("scratch = /tmp/x\npersistent = /tmp/y\n")
    msg = _build_missing_veloc_cfg_message(src, tmp_path / "build", "veloc.cfg")
    assert "DIAGNOSTIC" in msg
    assert str(misplaced) in msg


def test_message_does_not_flag_cfg_at_expected_root(tmp_path: Path) -> None:
    """An expected-root cfg must NOT appear under DIAGNOSTIC (would be
    nonsensical since the validator already found it)."""
    src = tmp_path / "src"
    src.mkdir()
    expected = src / "veloc.cfg"
    expected.write_text("scratch = /tmp/x\npersistent = /tmp/y\n")
    msg = _build_missing_veloc_cfg_message(src, tmp_path / "build", "veloc.cfg")
    # No DIAGNOSTIC section when only the expected-root cfg exists.
    assert "DIAGNOSTIC" not in msg


def test_message_caps_misplaced_list_to_avoid_spam(tmp_path: Path) -> None:
    """Pathological case: many misplaced cfgs → message must cap at 5."""
    src = tmp_path / "src"
    for i in range(10):
        sub = src / f"sub_{i}"
        sub.mkdir(parents=True)
        (sub / "veloc.cfg").write_text("scratch = /tmp/x\n")
    msg = _build_missing_veloc_cfg_message(src, tmp_path / "build", "veloc.cfg")
    # At most 5 misplaced paths surfaced — count the "  - " bullet lines
    # within the DIAGNOSTIC section (excludes the template-key bullets
    # which use "  scratch" / "  persistent" without a leading dash).
    bullet_lines = [
        ln for ln in msg.splitlines() if ln.startswith("  - ")
    ]
    assert 1 <= len(bullet_lines) <= 5


def test_message_handles_unreadable_source_dir_without_crash(
    tmp_path: Path,
) -> None:
    """OSError from rglob must not crash; message still produced."""
    nonexistent = tmp_path / "does_not_exist"
    msg = _build_missing_veloc_cfg_message(
        nonexistent, tmp_path / "build", "veloc.cfg",
    )
    # Core content still present even with no scan possible.
    assert "veloc.cfg" in msg
    assert "CREATE IT HERE" in msg
