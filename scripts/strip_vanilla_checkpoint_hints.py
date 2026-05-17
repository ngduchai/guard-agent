"""
strip_vanilla_checkpoint_hints.py

Sanitize each vanilla app under tests/apps/vanillas/ so the LLM agent sees
no checkpoint/resilience hints when it explores the code.  Operates on the
files the agent is actually likely to read:

  * app.yaml             — drop ckpt_build:, ckpt_run:, checkpoint:,
                           restart_cmd:, kill_after:, and comparison
                           keep/strip patterns that mention checkpoint
  * helper scripts at the top level (run_*.sh / xhpcg_run / *_restart.sh)
    that contain restart-detection logic — strip the restart blocks but
    keep the launcher boilerplate so the build still works
  * input files referenced from run.cmd — drop lines with restart_interval,
    amr.restart, amr.checkpoint, file_type=rst, checkpoint=, etc.
  * orphan agent docs (AGENTS.md, CLAUDE.md, .opencode/) at the top level
  * leftover restart_cmd-only directories (e.g. tests/restart/)

Does NOT touch deep upstream source files (e.g. LAMMPS' src/USER-COLVARS,
SAMRAI's source/test/restartdb) since those are outside the agent's
typical exploration path AND removing them risks breaking the build.
A second pass can address those if the audit shows vanilla still recovers.
"""
from __future__ import annotations
import re, shutil, sys
from pathlib import Path

ROOT = Path("tests/apps/vanillas")
DRY_RUN = "--dry-run" in sys.argv

CKPT_KEYS = ("checkpoint:", "ckpt_build:", "ckpt_run:")
RESTART_LINE_KEYS = ("restart_cmd:", "kill_after:")
COMP_BAD_PATTERNS = ('"checkpoint"', "'checkpoint'", "'ckpt'", '"ckpt"', "'restart'", '"restart"')

INPUT_FILE_BAD_RE = re.compile(
    r"(amr\s*\.\s*(restart|check_int|checkpoint)\b"
    r"|amr\s*\.\s*plot_int\b"   # plotfiles also activate restart in some amrex apps
    r"|restart_(file|interval|read|write)\b"
    r"|file_type\s*=\s*rst\b"
    r"|<output[0-9]+>[^<]*file_type\s*=\s*rst"
    r"|checkpoint\s*=\s*[\"']?-?[0-9]"
    r"|cont_check\b"
    r"|<DumpRestart>"
    r"|<dump_restart>)",
    re.IGNORECASE,
)

WRAPPER_RESTART_BLOCK_PATTERNS = [
    # bash patterns that detect existing checkpoint/restart files
    re.compile(r"# .*[Rr]estart.*\n(?:.*\n){0,40}?fi\s*$", re.MULTILINE),
    re.compile(r"if\s*\[\s*-d\s*\"\$.*[Cc]?[Kk]?[Pp][Tt][^\"]*\".*\]\s*&&[^]]*\n(?:.*\n){0,30}?fi\s*$", re.MULTILINE),
    re.compile(r".*latest=.*ckpt.*\n.*\$.*BIN.*\$latest.*\n", re.MULTILINE),
]

def edit_app_yaml(path: Path) -> tuple[bool, list[str]]:
    """Strip ckpt_build:, ckpt_run:, checkpoint:, restart_cmd:, kill_after:
    and any comparison keep_patterns / strip_patterns containing 'checkpoint'.
    """
    if not path.exists():
        return False, []
    text = path.read_text()
    new_lines: list[str] = []
    in_strip_block = False
    block_indent = ""
    notes = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not in_strip_block:
            stripped = line.lstrip()
            # Top-level keys to drop entirely (block + body)
            if any(stripped.startswith(k) for k in CKPT_KEYS):
                in_strip_block = True
                block_indent = re.match(r"\s*", line).group(0)
                notes.append(f"removed top-level {stripped[:30]}")
                continue
            # Single-line keys (restart_cmd, kill_after) to drop
            if any(stripped.startswith(k) for k in RESTART_LINE_KEYS):
                notes.append(f"removed line: {stripped[:50]}")
                continue
            # Comparison patterns mentioning checkpoint
            if "keep_patterns" in stripped or "strip_patterns" in stripped:
                # Sometimes the inline list contains "checkpoint" — scrub the whole entry
                if any(p in raw for p in COMP_BAD_PATTERNS):
                    notes.append("removed checkpoint-mentioning comparison pattern")
                    continue
            # List-item patterns: e.g.   - "checkpoint"
            if stripped.startswith("- ") and any(p in stripped for p in COMP_BAD_PATTERNS):
                notes.append(f"removed pattern entry: {stripped[:50]}")
                continue
            new_lines.append(line)
        else:
            # in strip block: drop until we leave its indentation
            if not line.strip():
                # blank line — keep skipping (still in block conceptually)
                continue
            cur_indent = re.match(r"\s*", line).group(0)
            if len(cur_indent) <= len(block_indent):
                # left the block
                in_strip_block = False
                # process this line normally
                stripped = line.lstrip()
                if any(stripped.startswith(k) for k in CKPT_KEYS):
                    in_strip_block = True
                    block_indent = cur_indent
                    notes.append(f"removed top-level {stripped[:30]}")
                    continue
                new_lines.append(line)
    new_text = "\n".join(new_lines).rstrip() + "\n"
    changed = new_text != text
    if changed and not DRY_RUN:
        path.write_text(new_text)
    return changed, notes


def strip_input_file(path: Path) -> tuple[bool, list[str]]:
    if not path.exists() or not path.is_file():
        return False, []
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return False, []
    out_lines = []
    notes = []
    for line in text.splitlines():
        if INPUT_FILE_BAD_RE.search(line):
            notes.append(f"  removed: {line.strip()[:80]}")
            continue
        out_lines.append(line)
    new_text = "\n".join(out_lines)
    if text.endswith("\n"):
        new_text += "\n"
    changed = new_text != text
    if changed and not DRY_RUN:
        path.write_text(new_text)
    return changed, notes


def strip_wrapper_script(path: Path) -> tuple[bool, list[str]]:
    """Strip restart-detection blocks from a launcher shell script."""
    if not path.exists() or not path.is_file():
        return False, []
    text = path.read_text(errors="ignore")
    notes = []
    new_text = text
    for pat in WRAPPER_RESTART_BLOCK_PATTERNS:
        if pat.search(new_text):
            new_text = pat.sub("", new_text)
            notes.append(f"  stripped restart-detection block")
    # Also strip lines with explicit ckpt/restart variables
    out_lines = []
    for line in new_text.splitlines():
        s = line.strip()
        if re.search(r"^:?\s*\"?\$?\{?(SST_CKPT|SST_CHECKPOINT|CKPT|CHECKPOINT|RESTART)", s) or \
           re.search(r"--checkpoint-(prefix|sim-period)|sstcpt|checkpoint_output|restart\.sh", s):
            notes.append(f"  removed line: {s[:80]}")
            continue
        out_lines.append(line)
    new_text = "\n".join(out_lines)
    if text.endswith("\n"):
        new_text += "\n"
    changed = new_text != text
    if changed and not DRY_RUN:
        path.write_text(new_text)
    return changed, notes


def remove_orphan(path: Path) -> bool:
    """Delete a file/dir entirely (orphan AGENTS.md, CLAUDE.md, etc)."""
    if not path.exists():
        return False
    if not DRY_RUN:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    return True


def list_run_cmd_inputs(app: Path) -> list[Path]:
    """From app.yaml's run.cmd, harvest paths that look like input files."""
    yaml = app / "app.yaml"
    if not yaml.exists():
        return []
    out = []
    txt = yaml.read_text()
    for line in txt.splitlines():
        m = re.search(r'cmd:\s*"([^"]+)"', line)
        if not m:
            continue
        cmd = m.group(1)
        # Heuristic: tokens with extension or that exist as a file under app/
        for tok in re.split(r"\s+", cmd):
            if tok.startswith("-") or tok.startswith("./") or tok.startswith("$"):
                if tok.startswith("./"):
                    tok = tok[2:]
                else:
                    continue
            cand = app / tok
            if cand.is_file():
                out.append(cand)
    return out


def process_app(app: Path) -> dict:
    name = app.name
    summary = {"app": name, "yaml_changed": False, "files_edited": [],
               "files_removed": []}

    # 1. app.yaml
    chg, notes = edit_app_yaml(app / "app.yaml")
    summary["yaml_changed"] = chg
    if notes:
        summary["yaml_notes"] = notes

    # 2. orphan top-level agent docs
    for orphan in (app / "AGENTS.md", app / "CLAUDE.md", app / ".opencode"):
        if remove_orphan(orphan):
            summary["files_removed"].append(str(orphan.relative_to(app)))

    # 3. helper scripts at top level (or in well-known subdirs)
    for sh_path in [
        app / "run_with_restart.sh",
        app / "mmsp_run.sh",
        app / "run_sst.sh",
        app / "athena_run.sh",
        app / "bin" / "xhpcg_run",
        app / "bench" / "run_with_restart.sh",
    ]:
        chg, notes = strip_wrapper_script(sh_path)
        if chg:
            summary["files_edited"].append(str(sh_path.relative_to(app)))

    # 4. input files referenced from run.cmd
    for inp in list_run_cmd_inputs(app):
        chg, notes = strip_input_file(inp)
        if chg:
            summary["files_edited"].append(str(inp.relative_to(app)))

    # 5. specific known input files (apps where run.cmd uses cd or wrappers)
    known_inputs = {
        "Athena++": ["inputs/hydro/athinput.blast", "inputs/hydro/athinput.blast_ckpt"],
        "Nyx": ["Exec/HydroTests/inputs.validation",
                "Exec/HydroTests/inputs.restart"],
        "WarpX": ["test_input/inputs_validation"],
        "SAMRAI": ["validation_inputs/linadv.2d.input"],
        "QMCPACK": ["examples/molecules/He/he_simple_opt.xml",
                    "examples/molecules/He/he_simple_opt_ckpt.xml"],
        "CLAMR": [],
        "HPCG": [],
        "SPARTA": ["examples/free/in.validation",
                   "examples/free/in.restart"],
        "SPPARKS": ["examples/ising/in.validation",
                    "examples/ising/in.restart"],
        "LAMMPS": ["bench/in.lj_long", "bench/in.lj_ckpt", "bench/in.lj_restart"],
        "MMSP": [],
        "OpenLB": [],
        "ROSS": [],
        "PRK_Stencil": [],
        "Smilei": ["namelist_minimal.py"],
        "SW4lite": ["tests/validation_test.in"],
        "miniVite": [],
        "HyPar": ["Examples/1D/FPDoubleWell/solver.inp"],
        "SST": ["bench.py"],
        "CoMD": [],
    }
    for inp in known_inputs.get(name, []):
        path = app / inp
        chg, notes = strip_input_file(path)
        if chg:
            summary["files_edited"].append(str(path.relative_to(app)))

    return summary


def main():
    apps = sorted(p for p in ROOT.iterdir() if p.is_dir())
    print(f"=== {'DRY RUN' if DRY_RUN else 'APPLYING'} cleanup across {len(apps)} apps ===\n")
    for app in apps:
        s = process_app(app)
        print(f"── {s['app']:13} ── yaml_changed={s['yaml_changed']}, "
              f"edited={len(s['files_edited'])}, removed={len(s['files_removed'])}")
        if s.get("yaml_notes"):
            for n in s["yaml_notes"]:
                print(f"     yaml: {n}")
        for f in s["files_edited"]:
            print(f"     edit: {f}")
        for f in s["files_removed"]:
            print(f"     rm:   {f}")


if __name__ == "__main__":
    main()
