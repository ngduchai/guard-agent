# `<APP>` — LLM Resilience Engineering Report

**App**: `<name>` — `<one-line domain description>`
**Vanilla source**: `tests/apps/vanillas/<APP>/`
**Reference source**: `tests/apps/checkpointed/<APP>/`
**LLM-generated source**: `build/tests_baseline/<APP>/`
**Iteration outcome**: PASS in **N iters** / **X**s wall / **Y**M tokens

---

## 1. LLM Methodology

### 1.1 Overall reasoning process (text/table DAG)

A turn-by-turn record of LLM thought↔action across all iterations. The
LLM's narrative in `opencode_stdout.txt` is structured into explicit
**Intent / Motivation / Expectation / Result** blocks per turn — extract
those verbatim into specific, concrete cells. Generic summaries like
"identify app" or "locate loop" are NOT acceptable; the cell must convey
**what specifically the LLM was looking for and what it found**.

**Format**: per-iter section heading + 2-column table (Thought | Action) +
blockquote RESULT + arrow-feedback line into next iter. Color coding via
emoji prefix: 🧠 = thought, 🔧 = action, ❌ = fail, ✅ = pass.

#### Example (HPCG iter 1+2)

```markdown
### Iter 1 — 685s — ❌ FAIL

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **1.a** | Which binary does the harness actually launch — Makefile-built `bin/xhpcg` or `app.yaml`'s `bin/xhpcg_run`? They might disagree. | read [app.yaml](../../build/tests_baseline/HPCG/app.yaml) + [prompt.txt](../../build/tests_baseline/HPCG/prompt.txt) → run cmd is `mpirun ./xhpcg_run`; Makefile produces `bin/xhpcg`. **Wrapper-script mismatch confirmed.** |
| **1.b** | Where exactly is the timed CG-sets loop, and what state crosses the loop boundary each iter? | read [main.cpp:335-341](../../build/tests_baseline/HPCG/src/main.cpp#L335) + [CG.cpp](../../build/tests_baseline/HPCG/src/CG.cpp) → loop is `for (i=0; i<numberOfCgSets; ++i)`; CG zeroes `x` each set, so only `i`, `times[10]`, `testnorms_data.values[i]` accumulate. |
| **1.c** | Where does `HPCG_VALIDATION=PASSED` come from? Must not break that contract. | `grep -rn 'HPCG_VALIDATION='` → only hit is in [bin/xhpcg_run](../../build/tests_baseline/HPCG/bin/xhpcg_run) shell wrapper, NOT in C++ source. |
| **...** | (more turns) | ... |

> ❌ **RESULT**: harness aborts before app launch — `No VeloC checkpoint directories resolved from veloc.cfg under tests_baseline/HPCG`. Only `bin/veloc.cfg` exists; validator probes only codebase root + build dir.

→ **Feedback into iter 2**: `validate_stderr.txt: "No VeloC checkpoint directories resolved"`

### Iter 2 — 433s — ❌ FAIL

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **2.a** | Validator probes codebase root — copy cfg there too. | write byte-identical [veloc.cfg](../../build/tests_baseline/HPCG/veloc.cfg) at codebase root |

> ❌ **RESULT**: kill+recovery 1.56× (cap 1.20×); 16 ckpt files observed; recovery re-ran ALL 180 CG sets from scratch.

→ **Feedback into iter 3**: `validate_stderr: "kill+recovery wall-time 1.56x ≥ 1.20x cap"`
```

#### Node-content rubric

Each 🧠 **Thought** cell = the LLM's **specific question or hypothesis** —
NOT a generic plan. Each 🔧 **Action** cell = the **specific tool call +
key finding** in one sentence — NOT a generic "read X". The verb
"explore" is banned; the verb "identify" only OK with a specific
identification target.

**Bad (forbidden)**:
- ❌ "THOUGHT: identify app + run config"
- ❌ "ACTION: read app.yaml, prompt.txt"

**Good** (specific):
- ✅ `🧠 Thought: which binary does the validator launch — xhpcg or xhpcg_run? app.yaml says xhpcg_run but Makefile builds xhpcg.`
- ✅ `🔧 Action: read app.yaml → confirms wrapper script bin/xhpcg_run is run, not Makefile-built bin/xhpcg`

#### Filling-in rules

- **Chain length** (= number of table rows per iter) matches the actual
  count of distinct Intent blocks in `iter_K/opencode_stdout.txt`.
  Don't pad; don't compress.
- **Cell content** = LLM's own words distilled to one specific sentence
  (paraphrase OK, but content must be specific). Quoted phrases get
  backticks.
- **Action cell** must mention the specific FILE/SYMBOL/COMMAND and what
  was found.
- **RESULT blockquote** quotes the actual error text from
  `validate_stderr.txt` (or PASS reason). One paragraph.
- **Feedback arrow** between iters quotes the specific signal the LLM
  saw that drove the next iter (one short phrase).
- **All file paths** are clickable markdown links `[label](path#L42)`,
  relative from `docs/llm_resilience_report/`.

**Sources** (cite per iteration, as clickable links):
- [`iter_K/opencode_stdout.txt`](../../build/iterative_logs/<APP>_baseline/iter_K/opencode_stdout.txt) — LLM's narrated Intent/Motivation/Expectation/Result blocks
- [`iter_K/validate_stdout.txt`](../../build/iterative_logs/<APP>_baseline/iter_K/validate_stdout.txt) + [`validate_stderr.txt`](../../build/iterative_logs/<APP>_baseline/iter_K/validate_stderr.txt) — verdict
- [`iter_K/inspection.json`](../../build/iterative_logs/<APP>_baseline/iter_K/inspection.json) — list of files modified
- [`iter_K/metrics.json`](../../build/iterative_logs/<APP>_baseline/iter_K/metrics.json) — pass/fail + per-iter timing

### 1.2 Critical state identification

| Question | Answer |
|---|---|
| Detection algorithm | `<e.g., "scanned src/main.cpp for variables crossing the timed loop boundary; identified Y as live across iterations">` |
| Source tools / queries the LLM used | `<opencode tool calls — read X, grep Y, ...>` |
| State considered & rejected | `<e.g., "considered protecting Z but rejected because deterministic from W">` |
| State eventually protected | `<bulleted list with brief rationale per item>` |

(Source: opencode reasoning narration in `iter_N/opencode_stdout.txt`.)

### 1.3 Protection + recovery algorithm

```pseudocode
ON STARTUP:
  1. VELOC_Init(MPI_COMM_WORLD, "veloc.cfg")
  2. VELOC_Mem_protect for each region
  3. v = VELOC_Restart_test("<id>", 0)
     IF v > 0:
        VELOC_Restart("<id>", v)
        <recovery actions specific to this app>

DURING COMPUTATION:
  EVERY <cadence> in <location:line>:
     VELOC_Checkpoint("<id>", <version>)

ON SHUTDOWN:
  VELOC_Finalize(1)
```

(Pseudocode reflecting the LLM's actual implementation; cite source `file:line`.)

### 1.4 LLM vs reference comparison

#### State coverage

| Application state | LLM | Reference | Notes |
|---|:---:|:---:|---|
| `<state element 1>` | ☑ | ☑ | `<both approaches save this — bytes>` |
| `<state element 2>` | ☑ | ☐ | `<LLM saves, reference doesn't — why>` |
| `<state element 3>` | ☐ | ☑ | `<reference saves, LLM doesn't — why>` |
| `<state element 4>` | ☐ | ☐ | `<neither saves — derivable from others>` |

#### Checkpoint strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where checkpoint is invoked (`file:func:line`) | `<...>` | `<...>` |
| Which process(es) invoke (rank 0 only / all ranks / etc.) | `<...>` | `<...>` |
| Cadence (every N iters / every N seconds / event-triggered) | `<...>` | `<...>` |
| Per-write storage | `<bytes/frame from raw_metrics.json>` | `<bytes/frame>` |
| Frames retained on disk | `<count>` | `<count>` |
| Cumulative on disk at end | `<MB>` | `<MB>` |

#### Recovery strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where recovery is detected (`file:line`) | `<...>` | `<...>` |
| What's done after restore | `<e.g., shrink loop bound to skip already-completed work>` | `<e.g., resume loop from saved index>` |
| Time to recover (kill + restart total / failure-free baseline) | `<a × baseline>` | `<b × baseline>` |
| Output correctness | `<bit-identical / numerically-equivalent / approximated-via-X>` | `<...>` |
