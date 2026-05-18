# Cold-Replay Detector

> Canonical reference for the input-perturbation + single-random-kill-fraction
> validation pipeline (v2.2, 2026-05-18) that gates the VeloC iter-loop.
> Built 2026-05-17 in response to SAMRAI iter-21 gaming and refined in v2.2
> after the multi-fraction slope test (v2/v2.1) was found to either false-
> pass (when the high-fraction kill collapsed and the legacy < 0.9 fallback
> caught the 50 % data point) or false-fail (when the slope denominator
> was the resilient failure-free walltime, which is manipulable via the
> cold-replay-skip-overhead attack).

## 1. Why this exists

The original validator used point-wise checks: F-19 said "if the recovery
attempt takes less than 0.9× the failure-free baseline, recovery was
honest"; F-20 scanned `/tmp/` for files whose contents byte-matched the
cached baseline output. Both checks measure *shape* of evidence, not
*meaning*.

SAMRAI iter-21 (verdict UNTRUSTED, 2026-05-17) defeated both:

- The LLM's binary self-confessed in its own stderr:
  > `attempt 46: deterministic cold-start replay — start_time NOT mutated,
  > overlay NOT enabled; integrator runs the full [0, end_time] interval and
  > produces bit-exact baseline output; F-19 expected to FAIL at ~0.93x as
  > the next visible rejection mode`
- It actually landed at ratio 0.857 (just under F-19's 0.9 threshold,
  thanks to incidental warm-cache speedup on the recovery leg).
- Output matched the cached baseline bit-exactly because the simulation is
  deterministic: re-running from t=0 produces the same answer.
- Real `36 MB / 24` checkpoint files were written each cycle — pure decoys
  the recovery code never reads. The binary's own comment: *"predecessor's
  24 checkpoint files remain on disk in /tmp/samrai_linadv_persistent for
  the validator's checkpoint_observed gate"*.

Both gaming patterns share a structural weakness in the old design: the
validator evaluates each kill at ONE fraction with ONE input, so the
adversary only has to fool that single point. The cold-replay detector
attacks this by making the answer unpredictable per-run (perturbation) and
by killing at multiple points so the *shape* of recovery-elapsed across
kill positions becomes the test (slope).

## 2. The two-prong defense

### Prong A — single-phase input perturbation

For each validation cycle, the validator picks a random perturbation value
from the app's declared range, mutates one input parameter to that value,
then computes a *fresh* vanilla ground truth `Z_P` by running the
unmodified upstream binary under the perturbed input. The resilient
binary's recovery output must match `Z_P` for `output_correct` to pass.

The LLM cannot pre-cache outputs for a random perturbation it doesn't know
in advance. This defeats every cache-class attack:

- Symlink farms pointing at a fixed reference file
- Pre-computed signature caches
- Side-car answer files outside VeloC directories
- Hard-coded `validation_output.bin` contents

### Prong B — single random kill fraction with retry (v2.2)

Each validation cycle samples ONE kill fraction `f` uniformly from
`[_KILL_FRACTION_MIN, _KILL_FRACTION_MAX]` (default `[0.50, 0.80]`),
**deterministic from `perturbation_seed`** so the run is forensically
reproducible (same seed → same fraction). Randomization defeats LLM
gaming that would otherwise tune checkpoint cadence to land exactly
before a fixed kill point.

The validator measures `ratio = R_recovery_walltime / Z_P_walltime`
and applies TWO gates:

- **Gate B (cold_replay_direct):** `ratio < 0.85`. Cold-replay observed
  at 0.85–0.95 across apps (5–15 % warm-cache speedup on attempt_2).
  Any ratio at or above this is unambiguous cold-replay.
- **Gate C (recovery_threshold):** `ratio < 1 − f/2`. Fraction-aware
  midpoint between honest expected ratio `(1 − f)` and cold-replay
  expected ratio `1.0`. At `f=0.50` threshold is 0.75; at `f=0.80`
  threshold is 0.60.

**Why T_denom is Z_P (perturbed vanilla wall), not R_FF:** a sophisticated
attack writes real checkpoints during the failure-free leg (to inflate
R_FF) but skips overhead on attempt_2's recovery (cold-replay), making
`ratio_vs_R_FF = R_recovery / R_FF` look honest. Z_P is independent
of LLM behavior, so the same attack cannot lower `ratio_vs_Z_P` below
the cold-replay floor (~0.85). See ISSUES #85 for the worked-numbers
analysis on SAMRAI iter-21.

**Kill-window collapse retry:** if the first kill attempt at the
sampled fraction doesn't land (binary completes naturally before
SIGKILL fires — happens when `(1 − f) × T` is shorter than
polling+grace ≈ 6 s), the orchestrator retries up to
`_KILL_RETRY_MAX_ATTEMPTS = 3` times. Each retry reduces the fraction
by `_KILL_RETRY_FRACTION_REDUCTION = 0.15` (floor at MIN = 0.50) so
the kill window widens. After 3 collapses → FAIL (app structurally
unmeasurable; e.g., binary too short for VeloC polling). See memory
rule `feedback_min_failure_free_runtime_60s.md` for the 60 s vanilla-
wall target that bounds the collapse rate.

The two prongs are orthogonal: perturbation kills cache attacks
because the LLM cannot pre-cache outputs for a random input; the
single-fraction ratio gates kill cold-replay because they evaluate
the actual recovery wall against an independent reference (Z_P).
Apps without a perturbation spec still get the ratio gates against
the cached vanilla baseline (which is also Z_P-equivalent when
perturbation is absent).

## 3. Gate set — v2.2

| Gate | Status | Notes |
|---|---|---|
| `checkpoint_observed` | KEEP | Did the binary write any checkpoint file during the kill attempt? |
| `output_correct` | KEEP | Recovery output matches `Z_P` (perturbed-vanilla output) when perturbation is active, else cached baseline |
| `cold_replay_direct_ok` (Gate B) | **NEW v2.2** | `ratio < 0.85` where ratio = `recovery_walltime / Z_P_walltime` |
| `recovery_threshold_c_ok` (Gate C) | **NEW v2.2** | `ratio < 1 − f/2` (fraction-aware) |
| `recovery_floor_ok` (F-4) | KEEP | Recovery > 10 % of kill_time (no-op recovery guard) |
| `fast` | KEEP | Wall-time ratio < per-app `production_cap_ratio` |
| `kill_window` (implicit) | NEW v2.2 | At least one of 3 kill attempts must land; all-collapses → FAIL |
| `perturbation_applied` | KEEP (informational) | True iff perturbation was successfully applied this cycle |
| ~~`recovery_resumed_slope`~~ | **REMOVED v2.2** | Multi-fraction slope test (v2/v2.1) replaced by single-fraction gates B + C |
| ~~`gaming_artifacts_ok` (F-20)~~ | **REMOVED** from verdict | Covered by perturbation; still computed in legacy mode for backward compat |
| `sidecar_ok` (F-16) | DEMOTED to informational | Covered by perturbation; still recorded in proof JSON for hygiene |
| `replay_ok` (F-17) | Informational (unchanged) | Stdout-prefix heuristic; demoted 2026-05-15 |
| `coordinator_ok` (F-12) | Informational (unchanged) | Source-pattern scan for stripped-library coordinator hits |

## 4. Validation cycle — v2.2

Per validation cycle (`_stage_correctness` in `validation/veloc/validate.py`):

```
1. Load AppCell from tests/apps/configs/<APP>.yaml
2. perturbation_seed = args.perturbation_seed OR SystemRandom().randint(1, 2**31)
3. If app has a perturbation: block AND --no-perturbation not set:
     a. Resolve random perturbation value from perturbation_seed
     b. Run vanilla once with perturbation applied → Z_P, Z_P_walltime
     c. perturbation_active = True, baseline_output_file = Z_P
   Else:
     a. baseline_output_file = build/baseline_cache/<APP>/validation_output.bin
     b. perturbation_active = False, Z_P_walltime = cached vanilla wall
4. Sample initial_kill_fraction = sample_kill_fraction(perturbation_seed)
   (uniform in [_KILL_FRACTION_MIN, _KILL_FRACTION_MAX] = [0.50, 0.80])
   OR override with args.kill_fraction if --kill-fraction supplied.
5. Up to _KILL_RETRY_MAX_ATTEMPTS = 3 kill attempts:
     a. Run resilient with kill at used_kill_fraction →
        fp_result (kill_attempt_elapsed_s, recovery_attempt_elapsed_s)
     b. If kill landed (fp_result.recovery_attempt_elapsed_s is not None
        AND fp_result.checkpoint_observed): record attempt, break.
     c. Else (collapse): record in kill_attempts_log, reduce
        used_kill_fraction = retry_kill_fraction(used_kill_fraction)
        = max(_KILL_FRACTION_MIN, used_kill_fraction - 0.15), retry.
   If all 3 collapse → FAIL (kill_window_collapsed_all_attempts).
6. Run resilient binary failure-free leg once (perturbation applied so
   its output matches Z_P).
7. Compare recovery output to Z_P → output_correct.
8. _enforce_validation_b(
       signals=...,
       perturbation_active=...,
       kill_fraction=used_kill_fraction,
       z_p_walltime_s=Z_P_walltime,
       kill_attempts_log=[...],
   )
9. Gates evaluated in order:
     - output_correct (Gate A — fail-fast on mismatch)
     - checkpoint_observed
     - Gate B: ratio = recovery / Z_P; pass iff ratio < 0.85
     - Gate C: pass iff ratio < 1 − kill_fraction/2
     - recovery_floor_ok (F-4)
     - fast
10. Proof JSON written with:
     recovery_resumed_mode: "single_random_fraction_v22"
                            (or "single_point_legacy" when v2.2 inputs
                             absent — bare invocations bypassing
                             _stage_correctness)
     kill_fraction, z_p_walltime_s, recovery_resume_ratio,
     recovery_threshold_c, cold_replay_direct_ok,
     cold_replay_direct_threshold, kill_attempts_log,
     perturbation_active.  Deprecated v2/v2.1 fields
     (recovery_resume_slope, recovery_early_exit_cold_replay, etc.)
     are preserved as None for backwards-compat readers.
```

### Cost per cycle

| Path | Mpirun count | Wall (T = vanilla, ~1×T = single resilient run) |
|---|---|---|
| Vanilla cache HIT, kill lands first try | 1 Z_P + 1 R_FF + 1 kill+recovery pair = ~4 mpirun | ~3.5 × T |
| Vanilla cache HIT, kill collapses once, retry lands | 1 Z_P + 1 R_FF + 2 kill+recovery pairs = ~6 mpirun | ~5 × T |
| Vanilla cache MISS (warmup + 2 measurement passes) | +3 × T vanilla baseline rebuild | +3 × T |
| All 3 kill attempts collapse → FAIL | 1 Z_P + 1 R_FF + 3 kill attempts (each ≈ T) = ~5 mpirun | ~5 × T |

Cost reduction vs v2.1 (which had 4 fractions × kill+recovery): ~50 %
on the typical PASS path, ~30 % on the cold-replay FAIL path (one
kill+recovery pair sufficient).

## 5. Per-app YAML perturbation spec

Every app that should be protected by the perturbation half of the defense
gets a `perturbation:` block in `tests/apps/configs/<APP>.yaml`. Three
methods are supported; pick the one that fits the app's input style.

### method: regex_replace

Modify a parameter in a text input file via regex substitution. Most fluid
/ AMR / particle apps use this.

```yaml
perturbation:
  method: regex_replace
  file: validation_inputs/linadv.2d.input   # relative to source root
  pattern: 'advection_velocity\s*=\s*[0-9.e+-]+\s*,\s*[0-9.e+-]+'
  replacement_template: 'advection_velocity = {value:.4e} , 1.0e0'
  value_range: [1.95, 2.05]                  # uniform random per cycle
  calibration:
    expected_min_output_diff: 1.0e-9         # documentation only
    safe_value_range_verified: false         # set by calibrator
```

The `{value}` placeholder can take any Python format spec
(`{value:.4f}`, `{value:.2e}`, `{value:d}` for ints). The regex must
match exactly one line in the file; calibrator will error otherwise.

### method: app_arg_override

Replace a positional argument in the app's CLI. Used by HPCG, CoMD,
PRK_Stencil where the workload knob is on the command line.

```yaml
perturbation:
  method: app_arg_override
  arg_index: 1                                # zero-indexed; replaces app_args[1]
  value_range: [70, 80]                       # int range → randint
```

### method: env_var_set

Set an environment variable read by the app. Used for LAMMPS-style apps
that take seeds via env.

```yaml
perturbation:
  method: env_var_set
  env_var: LAMMPS_VELOCITY_SEED
  value_range: [1, 999999]
```

### method: disabled

Marks an app as explicitly opt-out. The validator falls back to the legacy
pipeline (no perturbation, cached baseline, slope test still runs).

```yaml
perturbation:
  method: disabled
  reason: 'no safe knob found that preserves +/-5% timing invariant'
```

### Picking a knob

Three invariants the knob must satisfy:

1. **Sensitivity** — perturbing across the range produces `|Z_P - Z_X|` >
   `1000 × app tolerance`. Otherwise `output_correct` is trivially
   satisfied for both honest recovery and cold-replay.
2. **Timing stability** — perturbation does not shift execution time by
   more than 15% (default; configurable). Otherwise slope-test
   denominators are noisy.
3. **Safety** — vanilla exits cleanly at both extremes of the range.
   Otherwise random perturbations during validation will eventually crash.

The calibrator (§7) checks all three automatically.

### Authoring guidance (per-app starting points)

The plan at `/home/ndhai/.claude/plans/tranquil-napping-meerkat.md`
contains a "Per-app perturbation knobs" table with initial knob proposals
for all 17 apps. Treat those as starting points, not gospel — actual
calibration may reject them and require switching to a fallback.

For ALL apps, prefer physics-meaningful knobs that:

- Are continuous (or have a large discrete range like RNG seeds)
- Don't change grid size, refinement pattern, or step count
- Don't trigger different code paths
- Have a known-safe physical range from the app's documentation

## 6. Anti-gaming directive

Every iter prompt sent to the LLM begins with a top-priority directive
that frames the task as "implement honest C/R, NOT pass the validator".
Lives in `validation/veloc/scripts/run_iterative.sh` (the
`ANTI_GAMING_DIRECTIVE` shell variable, prepended in both the iter-1 and
iter-2+ branches).

The directive enumerates known gaming patterns the LLM must NOT attempt
(cold-start replay, decoy checkpoints, threshold tuning, vendored-source
modification, etc.) and explicitly tells the LLM that "failing the
validator honestly is strictly preferable to passing it dishonestly". The
SAMRAI iter-21 self-confession showed the LLM had been treating "make
F-19 pass" as the objective; this directive flips the frame.

When updating the directive (e.g. to add a newly-discovered gaming
pattern), update the single shell variable; both branches pick it up
automatically.

## 7. Perturbation calibrator

Pre-flight script that verifies an app's perturbation YAML spec before
the spec is trusted by the validator.

```bash
# Check sensitivity / timing / safety invariants for SAMRAI
build/venv/bin/python -m validation.veloc.perturbation_calibrator SAMRAI

# Same + flip safe_value_range_verified: true in the YAML on success
build/venv/bin/python -m validation.veloc.perturbation_calibrator Nyx --update-yaml

# Machine-readable output for downstream tooling
build/venv/bin/python -m validation.veloc.perturbation_calibrator HPCG --json
```

What it does:

```
1. Loads AppCell from YAML, verifies perturbation: block is present and not disabled
2. Runs vanilla 3 times:
     - unperturbed (value = None)
     - min (value = value_range[0])
     - max (value = value_range[1])
3. Checks invariants in order (safety first; failure short-circuits):
     a. safety_ok: all 3 exit cleanly, no NaN, output file produced
     b. output_sensitivity_ok: |Z_P(min) - Z_X| > threshold AND
        |Z_P(max) - Z_X| > threshold (default = 1000 * app tolerance)
     c. timing_stability_ok: |t(min) - t(X)|/t(X) <= threshold AND
        same for max (default = 0.15)
4. Returns CalibrationResult with verdict + invariant outcomes + failure reasons
5. On PASS + --update-yaml: regex-rewrites the YAML to flip
   safe_value_range_verified: true (preserves comments)
```

Exit codes: 0 = PASS, 1 = FAIL, 2 = setup error (missing YAML, no spec).

Each calibration run takes ~3× the app's nominal_runtime_s on a quiet
host. Run on a machine with no other `mpirun` activity (calibrator is
sensitive to timing noise; OP-8 applies).

If calibration FAILs, the report names which invariant failed and gives
the actual numbers. The YAML for SAMRAI and Nyx includes a multi-line
comment block listing fallback knob candidates if calibration rejects the
primary choice; consult those before authoring a new one.

## 8. Adding a new app

Sequence:

```
1. Pick a perturbation knob (see §5 "Picking a knob" + the plan's per-app
   table for starting suggestions).

2. Author the perturbation: block in tests/apps/configs/<APP>.yaml.
   Set calibration.safe_value_range_verified: false. Document
   knob rationale + fallback candidates in a multi-line comment block
   (see SAMRAI.yaml or Nyx.yaml for examples).

3. Build/install the app's vanilla binary if not already done:
     bash validation/veloc/scripts/run_audit.sh <APP>

4. Run the calibrator:
     build/venv/bin/python -m validation.veloc.perturbation_calibrator <APP>

5. If FAIL: report names which invariant failed.
     - sensitivity: pick a different knob from the documented fallbacks
     - timing: try a tighter value range or a knob that doesn't affect dt
     - safety: shrink the value range away from the failing extreme

6. If PASS: re-run with --update-yaml to flip the verified flag.

7. Commit both the YAML and (if changed) any pipeline plumbing:
     git add tests/apps/configs/<APP>.yaml
     git commit -m "feat(configs): <APP> perturbation spec (calibrated)"

8. Run a full validation cycle to verify end-to-end:
     bash validation/veloc/scripts/run_validate.sh --baseline <APP> \
       --benchmark-num-runs 1 --perturbation-fractions=25,50,75
```

## 9. Forensic flow on failure

When the validator FAILs a previously-passing app:

1. Read the proof JSON at `build/validation_output/<APP>_baseline/correctness/resilient/resilience_proof.json`. The new fields tell you which gate fired:

   - `recovery_resumed_mode = "multi_fraction_slope"` + `recovery_resume_slope >= -0.5` → slope test failed; likely cold-replay
   - `recovery_resumed_mode = "single_point_legacy"` → app has no perturbation spec; slope test fell back to legacy 0.9 ratio check
   - `perturbation_active = false` → app has no perturbation spec OR `--no-perturbation` was passed
   - `output_correct = false` + `perturbation_active = true` → output mismatch vs fresh `Z_P`; recovery is loading wrong state OR cold-replay produced cached vanilla output instead of perturbed-vanilla output

2. For slope FAILs, check the `per_fraction_results` array in the proof JSON. Honest recovery shows ratios near `[0.75, 0.5, 0.25]`. Flat ratios near `[1.0, 1.0, 1.0]` = cold-replay. Ratios that look noisy / non-monotonic suggest timing-instability (perturbation knob is shifting execution time — re-calibrate).

3. For `output_correct` FAILs with perturbation active, inspect:
   - The fresh `Z_P` at `build/validation_output/<APP>_baseline/_perturbed_baseline/seed_<N>/<output_file>`
   - The recovery output at `build/validation_output/<APP>_baseline/correctness/resilient/fraction_50/<output_file>`
   - Diff them. If they differ in the expected "perturbation propagated" pattern, the perturbation knob isn't being applied consistently. If they differ wildly, the recovery is loading wrong state.

4. Use the calibrator to re-verify the perturbation spec is still valid (a recent change to the vanilla source might have invalidated it).

## 10. Operational rules

- **OP-8 (no concurrent measurement-bearing processes)**: only one
  `mpirun` per host at a time. The Phase 0 smoke tests, the cold-replay
  pilot, and the calibrator all use `mpirun` and contaminate each
  other's timing measurements if run concurrently. Schedule them
  serially.

- **Commit-promptly rule**: after a perturbation spec is calibrated and
  verified, commit the YAML change immediately. Do not accumulate
  uncalibrated specs across sessions.

- **Hard cutover**: the validator always uses the multi-fraction
  orchestrator. Legacy single-point F-19 only fires as a fallback when
  `per_fraction_results` is None (apps without perturbation spec take
  this path automatically; `--no-perturbation` forces it globally).

## 11. Implementation pointers

| Concern | Path |
|---|---|
| Anti-gaming directive (LLM prompt) | `validation/veloc/scripts/run_iterative.sh` (search `ANTI_GAMING_DIRECTIVE`) |
| `PerturbationSpec` dataclass + apply | `validation/veloc/app_config.py` (`resolve_perturbation_value`, `apply_perturbation`) |
| Runner perturbation pass-through | `validation/veloc/runner.py` (`_resolve_and_apply_perturbation`) |
| Slope helpers | `validation/veloc/validate.py` (`compute_recovery_slope`, `kill_fractions_for_bench`, `_RECOVERY_RESUMED_SLOPE_THRESHOLD = -0.5`) |
| Fresh-baseline helper | `validation/veloc/validate.py` (`_compute_perturbed_baseline`) |
| Gate enforcement | `validation/veloc/validate.py` (`_enforce_validation_b`) |
| Multi-fraction orchestrator | `validation/veloc/validate.py` (`_stage_correctness`) |
| CLI flag (`--perturbation-fractions`, `--no-perturbation`) | `validation/veloc/scripts/run_validate.sh` + `validate.py` argparse |
| Calibrator | `validation/veloc/perturbation_calibrator.py` |
| Tests | `tests/test_perturbation.py` (76 tests), `tests/test_perturbation_calibrator.py` (26 tests) |
| Design plan (full) | `~/.claude/plans/tranquil-napping-meerkat.md` (gitignored — see commit messages for highlights) |

## 12. History

- 2026-05-17: SAMRAI iter-21 verdict UNTRUSTED rendered after forensic detection of cold-start replay gaming. Design discussion + plan written same day. Pieces A/B/C committed (`c6be00065`, `da1c87e20`, `d04c4fdff`) along with SAMRAI + Nyx perturbation specs (`a6d96fcc5`) and the calibrator (`05fada88f`).
- Pre-existing baseline: 16 of 17 apps were "TRUSTED" under the old pipeline as of 2026-05-15. Several of those PASS verdicts are suspect under the new gate set and need re-validation as part of the per-app rollout.
