"""Tests for the failure injector's PID matching logic.

The matcher must:
  1. Match native MPI binaries by argv[0] basename (CoMD-mpi, miniVite, HyPar).
  2. Match shell-script wrappers by argv[1] basename when argv[0] is a shell
     interpreter (mmsp_run.sh, run_sst.sh, xhpcg_run — note the lack of .sh on
     HPCG's wrapper).
  3. Skip MPI launchers (mpirun/mpiexec/orted/srun) at argv[0].
  4. Never match the validation wrapper ``bash run_validate.sh --reference
     <APP>`` even when <APP> equals the app's binary name.
"""

from validation.veloc.failure_injector import (
    _build_descendants,
    _find_rank_pids_local,
    _split_ppid_from_pscmd,
    match_rank_pids,
)


def test_matches_native_binary_by_argv0() -> None:
    ps_output = """\
1001 /usr/bin/mpirun -np 4 /path/clamr_mpionly -n 256 -t 5000
1002 /path/clamr_mpionly -n 256 -t 5000
1003 /path/clamr_mpionly -n 256 -t 5000
"""
    assert match_rank_pids(ps_output, "clamr_mpionly") == [1002, 1003]


def test_skips_mpi_launchers() -> None:
    ps_output = """\
2001 mpirun -np 4 ./HyPar
2002 mpiexec -n 4 ./HyPar
2003 srun --ntasks=4 ./HyPar
2004 orted --tree-spawn -mca ess env -mca ess_base_jobid 0 HyPar
2005 ./HyPar
"""
    assert match_rank_pids(ps_output, "HyPar") == [2005]


def test_does_not_match_validation_wrapper_for_binary_app() -> None:
    """Regression: ``bash run_validate.sh --reference miniVite`` previously
    matched substring "miniVite" and got killed instead of the actual rank."""
    ps_output = """\
3001 bash /home/u/repo/validation/veloc/scripts/run_validate.sh --reference miniVite --skip-benchmarks
3002 /path/build/miniVite -n 500000
3003 /path/build/miniVite -n 500000
3004 /path/build/miniVite -n 500000
3005 /path/build/miniVite -n 500000
"""
    assert match_rank_pids(ps_output, "miniVite") == [3002, 3003, 3004, 3005]


def test_matches_script_wrapper_via_argv1() -> None:
    """MMSP / SST / Athena++ launch as ``bash <script>.sh ...``.  The actual
    rank is the bash process; match by argv[1] basename."""
    ps_output = """\
4001 bash /path/mmsp_run.sh test.dat 1000 100
4002 bash /path/mmsp_run.sh test.dat 1000 100
4003 /path/parallel test.dat 1000 100
"""
    assert match_rank_pids(ps_output, "mmsp_run.sh") == [4001, 4002]


def test_matches_script_wrapper_without_sh_extension() -> None:
    """HPCG's xhpcg_run is a Bourne-Again shell script with no .sh suffix."""
    ps_output = """\
5001 bash /path/bin/xhpcg_run --nx=32 --ny=32 --nz=32 --rt=60
5002 bash /path/bin/xhpcg_run --nx=32 --ny=32 --nz=32 --rt=60
5003 /path/bin/xhpcg --nx=32 --ny=32 --nz=32 --rt=60
"""
    assert match_rank_pids(ps_output, "xhpcg_run") == [5001, 5002]


def test_does_not_match_validation_wrapper_for_script_app() -> None:
    """Wrapper for a script-based app (`bash run_validate.sh --reference
    MMSP`) must never match — argv[1] is run_validate.sh, not mmsp_run.sh."""
    ps_output = """\
6001 bash /home/u/repo/validation/veloc/scripts/run_validate.sh --reference MMSP --skip-benchmarks
6002 bash /path/mmsp_run.sh test.dat 1000 100
"""
    assert match_rank_pids(ps_output, "mmsp_run.sh") == [6002]


def test_skips_python_interpreters() -> None:
    """A stray ``python validate.py --executable-name xhpcg_run`` must not be
    matched as a rank (its argv[1] is validate.py, not xhpcg_run)."""
    ps_output = """\
7001 python /path/validate.py --executable-name xhpcg_run --output-dir /x
7002 bash /path/bin/xhpcg_run --nx=32
"""
    assert match_rank_pids(ps_output, "xhpcg_run") == [7002]


def test_handles_empty_and_malformed_lines() -> None:
    ps_output = """\

   not a number cmd
8001
8002 /path/myapp
"""
    assert match_rank_pids(ps_output, "myapp") == [8002]


def test_returns_empty_when_no_match() -> None:
    ps_output = """\
9001 /usr/bin/sshd -D
9002 /usr/sbin/cron -f
"""
    assert match_rank_pids(ps_output, "myapp") == []


# ---------------------------------------------------------------------------
# Friendly-fire regression — 2026-05-04 incident
#
# A bench chain killed its own ``run_validate.sh --reference HyPar``
# wrapper because the substring matcher saw "HyPar" in the wrapper's
# argv.  These tests capture the exact ps lines from the incident so a
# future refactor cannot regress.
# ---------------------------------------------------------------------------

def test_friendly_fire_2026_05_04_chain_wrapper_not_matched() -> None:
    """Exact ps line from the 2026-05-04 incident: the chain wrapper had
    PID 3081560 and was a smaller PID than the actual mpirun's HyPar
    child.  The substring matcher matched the wrapper first; the new
    matcher must skip it (argv[0]=bash, argv[1]=run_validate.sh)."""
    ps_output = """\
3081560 bash /home/ndhai/diaspora/guard-agent/validation/veloc/scripts/run_validate.sh --reference HyPar
3088452 /usr/bin/mpirun -np 1 /home/ndhai/diaspora/guard-agent/build/validation_output/HyPar_reference/build/resilient/build/src/HyPar
3088457 /home/ndhai/diaspora/guard-agent/build/validation_output/HyPar_reference/build/resilient/build/src/HyPar
"""
    # Only the actual rank binary, never the wrapper or mpirun.
    assert match_rank_pids(ps_output, "HyPar") == [3088457]


def test_python_validate_with_executable_name_flag_not_matched() -> None:
    """``python -m validation.veloc.validate ... --executable-name HyPar``
    must not match — argv[0]=python, even though argv contains 'HyPar'."""
    ps_output = """\
4001 python -m validation.veloc.validate /vanilla /resilient --executable-name HyPar --output-dir /out
4002 /path/HyPar
"""
    assert match_rank_pids(ps_output, "HyPar") == [4002]


# ---------------------------------------------------------------------------
# Descendant filter — defence in depth
# ---------------------------------------------------------------------------

def test_split_ppid_from_pscmd_basic() -> None:
    raw = """\
100 1 /usr/bin/mpirun -np 4 ./HyPar
200 100 ./HyPar
300 100 ./HyPar
"""
    pid_cmd, ppid_of = _split_ppid_from_pscmd(raw)
    assert ppid_of == {100: 1, 200: 100, 300: 100}
    assert "100 /usr/bin/mpirun -np 4 ./HyPar" in pid_cmd
    assert "200 ./HyPar" in pid_cmd


def test_split_ppid_drops_malformed_lines() -> None:
    raw = """
not numeric line
123 abc /not-a-ppid-int
500 100 /path/HyPar
"""
    pid_cmd, ppid_of = _split_ppid_from_pscmd(raw)
    assert ppid_of == {500: 100}
    assert pid_cmd.strip() == "500 /path/HyPar"


def test_build_descendants_direct_children() -> None:
    ppid_of = {100: 1, 200: 100, 300: 100, 400: 999}
    assert _build_descendants(ppid_of, 100) == {200, 300}
    assert _build_descendants(ppid_of, 999) == {400}


def test_build_descendants_grandchildren() -> None:
    """mpirun typically grandparents the actual ranks via orted/hydra."""
    ppid_of = {100: 1, 200: 100, 300: 200, 400: 200, 500: 300}
    # 100 -> 200 -> {300, 400}; 300 -> 500.  All except 100 itself.
    assert _build_descendants(ppid_of, 100) == {200, 300, 400, 500}


def test_build_descendants_unrelated_chain() -> None:
    """Two unrelated mpirun jobs: descendants of one must not include the
    other's children even if they run the same binary."""
    ppid_of = {
        100: 1, 200: 100, 300: 100,           # mpirun A's ranks
        400: 1, 500: 400, 600: 400,           # mpirun B's ranks
    }
    assert _build_descendants(ppid_of, 100) == {200, 300}
    assert _build_descendants(ppid_of, 400) == {500, 600}


def test_build_descendants_handles_ppid_loop_defensively() -> None:
    """Pathological ppid cycle (shouldn't happen on real systems) must
    not infinite-loop."""
    ppid_of = {100: 200, 200: 100}
    # Neither pid descends from a non-existent parent.
    assert _build_descendants(ppid_of, 999) == set()
