#!/usr/bin/env bash
#
# Set up the guard-agent build directory with a venv, test applications,
# and the guard-agent MCP tool for use with coding agents (OpenCode, Claude Code).
#
# After setup, each test application under build/tests/<app>/ contains a clean
# copy of the original source code.  Start your coding agent there and instruct
# it to make the code resilient with VeloC checkpointing.
#
# Usage:
#   ./setup.sh                 # overlay on existing build/
#   ./setup.sh --clean         # remove generated files, keep venv + data
#   ./setup.sh --deep-clean    # remove everything except backups
#
set -e

# ── Parse clean mode ────────────────────────────────────────────────────────
CLEAN_MODE="default"
for arg in "$@"; do
  case "$arg" in
    --deep-clean) CLEAN_MODE="deep-clean"; shift ;;
    --clean)      CLEAN_MODE="clean";      shift ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$REPO_ROOT/build"
PYTHON="${PYTHON:-python3}"

# ── Python version gate ──────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
  echo "ERROR: '$PYTHON' not found. Install Python ≥ 3.10 or set PYTHON=/path/to/python3.x" >&2
  exit 1
fi

PY_MAJOR=$("$PYTHON" -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$("$PYTHON" -c 'import sys; print(sys.version_info.minor)')
PY_VER="$PY_MAJOR.$PY_MINOR"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "ERROR: Python >= 3.10 is required (found $PY_VER via '$PYTHON')." >&2
  exit 1
fi

echo "Using Python $PY_VER ($PYTHON)"
echo "Repository root: $REPO_ROOT"
echo "Build directory: $BUILD_DIR"
echo "Clean mode:      $CLEAN_MODE"

mkdir -p "$BUILD_DIR"

# ── Backup persistent data before cleaning ───────────────────────────────────
KNOWLEDGE_DB_DIR="$BUILD_DIR/knowledge_db"
KNOWLEDGE_DB_FILE="$KNOWLEDGE_DB_DIR/knowledge.json"
KNOWLEDGE_BACKUP_DIR="$KNOWLEDGE_DB_DIR/backups"
_KNOWLEDGE_EXISTS=false

BACKUP_DIR="$BUILD_DIR/.backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if [ "$CLEAN_MODE" != "default" ]; then
  # Knowledge base
  if [ -f "$KNOWLEDGE_DB_FILE" ]; then
    _KNOWLEDGE_EXISTS=true
    mkdir -p "$KNOWLEDGE_BACKUP_DIR"
    cp "$KNOWLEDGE_DB_FILE" "$KNOWLEDGE_BACKUP_DIR/knowledge_${TIMESTAMP}.json"
    echo "Knowledge base backup → $KNOWLEDGE_BACKUP_DIR/knowledge_${TIMESTAMP}.json"
  fi

  # Validation output
  if [ -d "$BUILD_DIR/validation_output" ]; then
    mkdir -p "$BACKUP_DIR/validation_output"
    cp -r "$BUILD_DIR/validation_output" "$BACKUP_DIR/validation_output/$TIMESTAMP"
    echo "Validation output backup → $BACKUP_DIR/validation_output/$TIMESTAMP"
  fi

  # Logs
  if [ -d "$BUILD_DIR/log" ]; then
    mkdir -p "$BACKUP_DIR/log"
    cp -r "$BUILD_DIR/log" "$BACKUP_DIR/log/$TIMESTAMP"
    echo "Log backup → $BACKUP_DIR/log/$TIMESTAMP"
  fi
elif [ -f "$KNOWLEDGE_DB_FILE" ]; then
  _KNOWLEDGE_EXISTS=true
fi

# ── Clean BUILD_DIR according to mode ────────────────────────────────────────
if [ "$CLEAN_MODE" = "deep-clean" ]; then
  echo "Deep-cleaning: removing everything in $BUILD_DIR ..."
  if [ -d "$BUILD_DIR" ]; then
    for entry in "$BUILD_DIR"/* "$BUILD_DIR"/.[!.]* "$BUILD_DIR"/..?*; do
      [ -e "$entry" ] || continue
      base="$(basename "$entry")"
      case "$base" in
        .backups) echo "  Preserving $entry" ;;
        *)        rm -rf "$entry"; echo "  Removed $entry" ;;
      esac
    done
  fi
elif [ "$CLEAN_MODE" = "clean" ]; then
  echo "Cleaning generated files from previous runs ..."
  if [ -d "$BUILD_DIR" ]; then
    for entry in "$BUILD_DIR"/* "$BUILD_DIR"/.[!.]* "$BUILD_DIR"/..?*; do
      [ -e "$entry" ] || continue
      base="$(basename "$entry")"
      case "$base" in
        .*|log|venv|knowledge_db)
          echo "  Preserving $entry" ;;
        *)
          rm -rf "$entry"; echo "  Removed $entry" ;;
      esac
    done
  fi
else
  echo "Default mode: keeping existing build contents, overlaying new setup."
fi

# ── Knowledge base: create only if none existed ──────────────────────────────
if [ "$_KNOWLEDGE_EXISTS" = false ]; then
  mkdir -p "$KNOWLEDGE_DB_DIR"
  echo "Knowledge base: directory created for first run."
else
  echo "Knowledge base: existing DB preserved → $KNOWLEDGE_DB_FILE"
fi

# ── Copy test applications into build/ ───────────────────────────────────────
# Each app gets a clean copy of the original source code.
# The coding agent works directly on these copies.

TESTS_DIR="$BUILD_DIR/tests"
mkdir -p "$TESTS_DIR"
echo ""
echo "Setting up test applications in $TESTS_DIR ..."

# --- Example applications (small MPI programs) ---
if [ -d "$REPO_ROOT/tests/examples/original" ]; then
  for app_dir in "$REPO_ROOT/tests/examples/original"/*/; do
    app_name="$(basename "$app_dir")"
    target="$TESTS_DIR/$app_name"

    # Always start fresh — remove any previous agent modifications
    if [ -d "$target" ]; then
      rm -rf "$target"
    fi

    cp -r "$app_dir" "$target"
    echo "  $target  (from tests/examples/original/$app_name)"
  done
fi

# --- ECP applications (large HPC codes) ---
if [ -d "$REPO_ROOT/tests/ecp/vanillas" ]; then
  for app_dir in "$REPO_ROOT/tests/ecp/vanillas"/*/; do
    app_name="$(basename "$app_dir")"
    target="$TESTS_DIR/$app_name"

    if [ -d "$target" ]; then
      rm -rf "$target"
    fi

    cp -r "$app_dir" "$target"
    echo "  $target  (from tests/ecp/vanillas/$app_name)"
  done
fi

# --- 20 benchmark applications (tests/apps/vanillas) ---
if [ -d "$REPO_ROOT/tests/apps/vanillas" ]; then
  for app_dir in "$REPO_ROOT/tests/apps/vanillas"/*/; do
    app_name="$(basename "$app_dir")"
    target="$TESTS_DIR/$app_name"

    if [ -d "$target" ]; then
      rm -rf "$target"
    fi

    cp -a "$app_dir" "$target"
    echo "  $target  (from tests/apps/vanillas/$app_name)"
  done
fi

# --- Baseline copies (no guard-agent, for comparison) ---
BASELINE_DIR="$BUILD_DIR/tests_baseline"
mkdir -p "$BASELINE_DIR"
echo ""
echo "Setting up baseline test applications in $BASELINE_DIR ..."
echo "  (no guard-agent MCP — OpenCode uses only its own LLM knowledge)"

if [ -d "$REPO_ROOT/tests/examples/original" ]; then
  for app_dir in "$REPO_ROOT/tests/examples/original"/*/; do
    app_name="$(basename "$app_dir")"
    target="$BASELINE_DIR/$app_name"
    [ -d "$target" ] && rm -rf "$target"
    cp -r "$app_dir" "$target"
    echo "  $target"
  done
fi
if [ -d "$REPO_ROOT/tests/ecp/vanillas" ]; then
  for app_dir in "$REPO_ROOT/tests/ecp/vanillas"/*/; do
    app_name="$(basename "$app_dir")"
    target="$BASELINE_DIR/$app_name"
    [ -d "$target" ] && rm -rf "$target"
    cp -r "$app_dir" "$target"
    echo "  $target"
  done
fi
if [ -d "$REPO_ROOT/tests/apps/vanillas" ]; then
  for app_dir in "$REPO_ROOT/tests/apps/vanillas"/*/; do
    app_name="$(basename "$app_dir")"
    target="$BASELINE_DIR/$app_name"
    [ -d "$target" ] && rm -rf "$target"
    cp -a "$app_dir" "$target"
    echo "  $target"
  done
fi

# --- OpenCode MCP config + AGENTS.md for each test app ---
GUARD_AGENT_BIN="$BUILD_DIR/venv/bin/guard-agent"
echo ""
echo "Writing opencode.json and AGENTS.md into each test app ..."
for app_dir in "$TESTS_DIR"/*/; do
  [ -d "$app_dir" ] || continue
  cat > "$app_dir/opencode.json" << OCEOF
{
  "\$schema": "https://opencode.ai/config.json",
  "mcp": {
    "guard-agent": {
      "type": "local",
      "command": ["$GUARD_AGENT_BIN", "serve"],
      "enabled": true,
      "timeout": 600000
    }
  },
  "experimental": {
    "mcp_timeout": 600000
  }
}
OCEOF
  cat > "$app_dir/AGENTS.md" << 'AGENTSEOF'
# Rules

- After injecting VeloC checkpointing, you MUST call `validate_injection` to verify the injection works.
- If `validate_injection` fails, fix the code and call it again. Repeat until it passes.
- The task is NOT done until `validate_injection` returns `passed: true`.
- In veloc.cfg, use scratch=/tmp/scratch and persistent=/tmp/persistent unless the user specifies otherwise.
AGENTSEOF
  echo "  $(basename "$app_dir")/"
done

# --- Test data (HDF5 files, etc.) ---
DATA_DIR="$BUILD_DIR/data"
if [ -d "$REPO_ROOT/tests/data" ]; then
  if [ -d "$DATA_DIR" ]; then
    rm -rf "$DATA_DIR"
  fi
  cp -r "$REPO_ROOT/tests/data" "$DATA_DIR"
  echo "  $DATA_DIR  (test data)"
fi

# --- Reference solutions (for comparison, read-only) ---
REFS_DIR="$BUILD_DIR/ref_solutions"
if [ -d "$REPO_ROOT/tests/examples/ref_solutions" ]; then
  if [ -d "$REFS_DIR" ]; then
    rm -rf "$REFS_DIR"
  fi
  cp -r "$REPO_ROOT/tests/examples/ref_solutions" "$REFS_DIR"
  echo "  $REFS_DIR  (reference solutions for comparison)"
fi

# ── App validation prerequisites ────────────────────────────────────────────
echo ""
echo "Checking prerequisites for app validation (validate_apps.py) ..."

_PREREQ_OK=true

# MPI
if command -v mpirun &>/dev/null; then
  MPI_VER="$(mpirun --version 2>&1 | head -1)"
  echo "  MPI:       OK ($MPI_VER)"
elif command -v mpiexec &>/dev/null; then
  echo "  MPI:       OK (mpiexec found)"
else
  echo "  MPI:       MISSING (install OpenMPI or MPICH for app validation)"
  _PREREQ_OK=false
fi

# C/C++ compiler
if command -v mpicc &>/dev/null; then
  echo "  mpicc:     OK ($(mpicc --version 2>&1 | head -1))"
else
  echo "  mpicc:     MISSING (install MPI C compiler wrappers)"
  _PREREQ_OK=false
fi
if command -v mpicxx &>/dev/null; then
  echo "  mpicxx:    OK"
else
  echo "  mpicxx:    MISSING (install MPI C++ compiler wrappers)"
  _PREREQ_OK=false
fi

# CMake
if command -v cmake &>/dev/null; then
  echo "  cmake:     OK ($(cmake --version | head -1))"
else
  echo "  cmake:     MISSING (some apps require CMake)"
fi

# make
if command -v make &>/dev/null; then
  echo "  make:      OK"
else
  echo "  make:      MISSING"
  _PREREQ_OK=false
fi

if [ "$_PREREQ_OK" = true ]; then
  echo "  All prerequisites met."
else
  echo ""
  echo "  WARNING: Some prerequisites are missing. App validation may fail."
  echo "  Install the missing tools and re-run setup.sh."
fi

# ── Python venv ──────────────────────────────────────────────────────────────
if [ -d "$BUILD_DIR/venv" ]; then
  VENV_PY_VER=$("$BUILD_DIR/venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "unknown")
  if [ "$VENV_PY_VER" != "$PY_VER" ]; then
    echo "Existing venv uses Python $VENV_PY_VER but $PYTHON is $PY_VER — recreating venv ..."
    rm -rf "$BUILD_DIR/venv"
    "$PYTHON" -m venv "$BUILD_DIR/venv"
  else
    echo "Reusing existing venv (Python $VENV_PY_VER)"
  fi
else
  echo "Creating virtualenv in build/venv ..."
  "$PYTHON" -m venv "$BUILD_DIR/venv"
fi

echo "Activating venv and installing dependencies ..."
# shellcheck source=/dev/null
. "$BUILD_DIR/venv/bin/activate"

echo "Upgrading pip, setuptools, and wheel ..."
pip install --upgrade pip setuptools wheel 2>&1 | tail -1

# Install guard-agent package (includes MCP server + CLI)
echo "Installing guard-agent package ..."
pip install -q -e "$REPO_ROOT"

# Install optional dependencies for the full agent and validation
[ -f "$REPO_ROOT/orchestrator/requirements.txt" ] && pip install -q -r "$REPO_ROOT/orchestrator/requirements.txt" || true
[ -f "$REPO_ROOT/shared/requirements.txt" ] && pip install -q -r "$REPO_ROOT/shared/requirements.txt" || true
[ -f "$REPO_ROOT/validation/requirements.txt" ] && pip install -q -r "$REPO_ROOT/validation/requirements.txt" || true

# ── LLM API key ──────────────────────────────────────────────────────────────
BUILD_KEY_FILE="$BUILD_DIR/api_key"
ROOT_KEY_FILE="$REPO_ROOT/api_key"

if [ -n "$ARGO_API_KEY" ]; then
  echo "Writing Argo API key from environment to $BUILD_KEY_FILE"
  printf '%s\n' "$ARGO_API_KEY" > "$BUILD_KEY_FILE"
elif [ -n "$OPENAI_API_KEY" ]; then
  echo "Writing OpenAI API key from environment to $BUILD_KEY_FILE"
  printf '%s\n' "$OPENAI_API_KEY" > "$BUILD_KEY_FILE"
elif [ -f "$ROOT_KEY_FILE" ]; then
  echo "Copying API key from $ROOT_KEY_FILE to $BUILD_KEY_FILE"
  cp "$ROOT_KEY_FILE" "$BUILD_KEY_FILE"
else
  echo "WARNING: No LLM API key found. Full agent mode will not work." >&2
  echo "  Set ARGO_API_KEY or OPENAI_API_KEY, or create $ROOT_KEY_FILE" >&2
fi

# ── Runner scripts ───────────────────────────────────────────────────────────
echo ""
echo "Creating runner scripts ..."

# Helper to create runner scripts
create_runner() {
  local name="$1"
  local script="$2"
  local runner="$BUILD_DIR/run_${name}.sh"
  cat > "$runner" << EOF
#!/usr/bin/env bash
set -e
SCRIPT_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
REPO_ROOT="\$(cd "\$SCRIPT_DIR/.." && pwd)"
. "\$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="\${REPO_ROOT}/orchestrator:\${REPO_ROOT}"
exec python "\$REPO_ROOT/$script" "\$@"
EOF
  chmod +x "$runner"
  echo "  $runner"
}

# Orchestrator server
cat > "$BUILD_DIR/run_orchestrator.sh" << 'RUNORCH'
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}/orchestrator:${REPO_ROOT}"
export LLM_PROVIDER="${LLM_PROVIDER:-argo}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://apps-dev.inside.anl.gov/argoapi/v1}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-$OPENAI_BASE_URL}"
if [ -z "${OPENAI_API_KEY:-}" ]; then
  if [ -n "${ARGO_API_KEY:-}" ]; then
    OPENAI_API_KEY="$ARGO_API_KEY"
  else
    KEY_FILE="${SCRIPT_DIR}/api_key"
    [ -f "$KEY_FILE" ] && OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')" || { echo "ERROR: No API key." >&2; exit 1; }
  fi
fi
export OPENAI_API_KEY
exec python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 "$@"
RUNORCH
chmod +x "$BUILD_DIR/run_orchestrator.sh"
echo "  $BUILD_DIR/run_orchestrator.sh"

# Interactive VeloC agent (standalone mode)
cat > "$BUILD_DIR/run_start_agent.sh" << 'RUNAGENT'
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/agents"
export LLM_PROVIDER="${LLM_PROVIDER:-argo}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://apps-dev.inside.anl.gov/argoapi/v1}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-$OPENAI_BASE_URL}"
export GUARD_AGENT_PROJECT_ROOT="${SCRIPT_DIR}"
if [ -z "${OPENAI_API_KEY:-}" ]; then
  if [ -n "${ARGO_API_KEY:-}" ]; then
    OPENAI_API_KEY="$ARGO_API_KEY"
  else
    KEY_FILE="${SCRIPT_DIR}/api_key"
    [ -f "$KEY_FILE" ] && OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')" || { echo "ERROR: No API key." >&2; exit 1; }
  fi
fi
export OPENAI_API_KEY
exec python -m agents.veloc.start_agent "$@"
RUNAGENT
chmod +x "$BUILD_DIR/run_start_agent.sh"
echo "  $BUILD_DIR/run_start_agent.sh"

# Web UI
cat > "$BUILD_DIR/run_deploy_webui.sh" << 'RUNWEB'
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/agents"
export LLM_PROVIDER="${LLM_PROVIDER:-argo}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://apps-dev.inside.anl.gov/argoapi/v1}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-$OPENAI_BASE_URL}"
export GUARD_AGENT_PROJECT_ROOT="${SCRIPT_DIR}"
if [ -z "${OPENAI_API_KEY:-}" ]; then
  if [ -n "${ARGO_API_KEY:-}" ]; then
    OPENAI_API_KEY="$ARGO_API_KEY"
  else
    KEY_FILE="${SCRIPT_DIR}/api_key"
    [ -f "$KEY_FILE" ] && OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')" || { echo "ERROR: No API key." >&2; exit 1; }
  fi
fi
export OPENAI_API_KEY
exec python -m uvicorn agents.veloc.webui:app --host 0.0.0.0 --port 8010 "$@"
RUNWEB
chmod +x "$BUILD_DIR/run_deploy_webui.sh"
echo "  $BUILD_DIR/run_deploy_webui.sh"

# Validation scripts — thin wrappers that delegate to the git-tracked
# scripts in validation/veloc/scripts/.  This ensures setup.sh --clean
# always produces wrappers that use the latest version of the scripts.

cat > "$BUILD_DIR/run_validate.sh" << 'WRAPPER'
#!/usr/bin/env bash
# Wrapper — real script lives in validation/veloc/scripts/
exec "$(cd "$(dirname "$0")/.." && pwd)/validation/veloc/scripts/run_validate.sh" "$@"
WRAPPER
chmod +x "$BUILD_DIR/run_validate.sh"
echo "  $BUILD_DIR/run_validate.sh"

cat > "$BUILD_DIR/run_compare.sh" << 'WRAPPER'
#!/usr/bin/env bash
# Wrapper — real script lives in validation/veloc/scripts/
exec "$(cd "$(dirname "$0")/.." && pwd)/validation/veloc/scripts/run_compare.sh" "$@"
WRAPPER
chmod +x "$BUILD_DIR/run_compare.sh"
echo "  $BUILD_DIR/run_compare.sh"

cat > "$BUILD_DIR/run_iterative.sh" << 'WRAPPER'
#!/usr/bin/env bash
# Wrapper — real script lives in validation/veloc/scripts/
exec "$(cd "$(dirname "$0")/.." && pwd)/validation/veloc/scripts/run_iterative.sh" "$@"
WRAPPER
chmod +x "$BUILD_DIR/run_iterative.sh"
echo "  $BUILD_DIR/run_iterative.sh"

cat > "$BUILD_DIR/run_evaluate.sh" << 'WRAPPER'
#!/usr/bin/env bash
# Wrapper — real script lives in validation/veloc/scripts/
exec "$(cd "$(dirname "$0")/.." && pwd)/validation/veloc/scripts/run_evaluate.sh" "$@"
WRAPPER
chmod +x "$BUILD_DIR/run_evaluate.sh"
echo "  $BUILD_DIR/run_evaluate.sh"

cat > "$BUILD_DIR/run_batch.sh" << 'WRAPPER'
#!/usr/bin/env bash
# Wrapper — real script lives in validation/veloc/scripts/
exec "$(cd "$(dirname "$0")/.." && pwd)/validation/veloc/scripts/run_batch.sh" "$@"
WRAPPER
chmod +x "$BUILD_DIR/run_batch.sh"
echo "  $BUILD_DIR/run_batch.sh"

# NOTE: The inline heredoc scripts that used to live here (run_validate.sh,
# run_compare.sh, run_iterative.sh, run_evaluate.sh) have been moved to
# validation/veloc/scripts/ and are now git-tracked.  The wrappers above
# delegate to those scripts via exec.
#
# Old inline code removed — see git history for reference.
if false; then cat << 'RUNVALIDATE'
#!/usr/bin/env bash
set -e

# Usage: ./run_validate.sh [--baseline] <app_name> [extra validate.py args...]
#
# Validates the agent-modified code against the original unmodified source.
#
# Modes:
#   ./build/run_validate.sh art_simple            # validate build/tests/art_simple (with guard-agent)
#   ./build/run_validate.sh --baseline art_simple  # validate build/tests_baseline/art_simple (without guard-agent)
#
# The script auto-resolves:
#   - Original source:  tests/examples/original/<app> or tests/ecp/vanillas/<app>
#   - Resilient source: build/tests/<app> or build/tests_baseline/<app>
#   - Executable name:  from the app's CMakeLists.txt or known defaults
#   - Benchmark config: from validation/veloc/benchmark_configs/ if available
#   - Test data path:   build/data/
#
# Examples:
#   ./build/run_validate.sh art_simple
#   ./build/run_validate.sh --baseline art_simple
#   ./build/run_validate.sh art_simple --skip-benchmarks

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}"

# --- Parse --baseline flag ---
USE_BASELINE=false
if [ "${1:-}" = "--baseline" ]; then
  USE_BASELINE=true
  shift
fi

APP_NAME="${1:?Usage: run_validate.sh [--baseline] <app_name> [extra args...]}"
shift

# --- Resolve original source directory ---
ORIGINAL_SRC=""
if [ -d "$REPO_ROOT/tests/examples/original/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/examples/original/$APP_NAME"
elif [ -d "$REPO_ROOT/tests/ecp/vanillas/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/ecp/vanillas/$APP_NAME"
else
  echo "ERROR: Original source not found for '$APP_NAME'." >&2
  echo "  Checked: tests/examples/original/$APP_NAME" >&2
  echo "  Checked: tests/ecp/vanillas/$APP_NAME" >&2
  exit 1
fi

# --- Resilient source (agent-modified) ---
if [ "$USE_BASELINE" = true ]; then
  RESILIENT_SRC="$SCRIPT_DIR/tests_baseline/$APP_NAME"
  LABEL="baseline (no guard-agent)"
else
  RESILIENT_SRC="$SCRIPT_DIR/tests/$APP_NAME"
  LABEL="with guard-agent"
fi
if [ ! -d "$RESILIENT_SRC" ]; then
  echo "ERROR: Resilient source not found at $RESILIENT_SRC" >&2
  echo "  Run './setup.sh' first, then modify the code with your coding agent." >&2
  exit 1
fi

# --- Resolve executable name from CMakeLists.txt ---
EXE_NAME=""
CMAKE_FILE="$RESILIENT_SRC/CMakeLists.txt"
if [ -f "$CMAKE_FILE" ]; then
  # Extract add_executable target name
  EXE_NAME=$(grep -oP 'add_executable\s*\(\s*\K\S+' "$CMAKE_FILE" 2>/dev/null | head -1)
fi
# Fallback to known defaults
if [ -z "$EXE_NAME" ]; then
  case "$APP_NAME" in
    art_simple)      EXE_NAME="art_simple_main" ;;
    matrix_mul_mpi)  EXE_NAME="matrix_mul_mpi" ;;
    ExaMiniMD)       EXE_NAME="ExaMiniMD" ;;
    ExaMPM)          EXE_NAME="DamBreak" ;;
    Quicksilver)     EXE_NAME="qs" ;;
    *)               EXE_NAME="$APP_NAME" ;;
  esac
fi

# --- Resolve app args from prompt.txt hints ---
APP_ARGS=""
case "$APP_NAME" in
  art_simple)
    DATA_FILE="${DATA_PATH:-$SCRIPT_DIR/data/tooth_preprocessed.h5}"
    APP_ARGS="$DATA_FILE 294.078 5 2 0 4"
    ;;
esac

# --- Resolve benchmark config if available ---
BENCH_CONFIG=""
BENCH_FILE="$REPO_ROOT/validation/veloc/benchmark_configs/${APP_NAME}.json"
if [ -f "$BENCH_FILE" ]; then
  BENCH_CONFIG="--benchmark-config $BENCH_FILE"
fi

# --- Resolve comparison method ---
COMPARISON="--comparison-method hash"
case "$APP_NAME" in
  art_simple)     COMPARISON="--comparison-method ssim --ssim-threshold 0.9999 --hdf5-dataset data --output-file-name recon.h5" ;;
  ExaMiniMD)      COMPARISON="--comparison-method text-diff --output-file-name stdout.txt" ;;
  ExaMPM)         COMPARISON="--comparison-method text-diff --output-file-name stdout.txt" ;;
  Quicksilver)    COMPARISON="--comparison-method text-diff --output-file-name stdout.txt" ;;
esac

# --- Output directory ---
if [ "$USE_BASELINE" = true ]; then
  OUTPUT_DIR="$SCRIPT_DIR/validation_output/${APP_NAME}_baseline"
else
  OUTPUT_DIR="$SCRIPT_DIR/validation_output/$APP_NAME"
fi

# --- Set DATA_PATH for benchmark configs ---
export DATA_PATH="${DATA_PATH:-$SCRIPT_DIR/data/tooth_preprocessed.h5}"
export INPUT_DIR="${INPUT_DIR:-$SCRIPT_DIR/tests/ExaMiniMD/input}"
export INPUT_FILE="${INPUT_FILE:-$SCRIPT_DIR/tests/Quicksilver/Examples/ValidationMixed/validationMixed.inp}"

echo "════════════════════════════════════════════════════════════════════"
echo "  Validating: $APP_NAME ($LABEL)"
echo "════════════════════════════════════════════════════════════════════"
echo "  Original:  $ORIGINAL_SRC"
echo "  Resilient: $RESILIENT_SRC"
echo "  Executable: $EXE_NAME"
echo "  Output:    $OUTPUT_DIR"
echo ""

# Build the validation command
CMD="python -m validation.veloc.validate \
  \"$ORIGINAL_SRC\" \
  \"$RESILIENT_SRC\" \
  --executable-name \"$EXE_NAME\" \
  --output-dir \"$OUTPUT_DIR\" \
  --install-resilient \
  $COMPARISON \
  $BENCH_CONFIG"

# Append original/resilient args if set
if [ -n "$APP_ARGS" ]; then
  CMD="$CMD --original-args \"$APP_ARGS\" --resilient-args \"$APP_ARGS\""
fi

# Append any extra user args
if [ $# -gt 0 ]; then
  CMD="$CMD $*"
fi

eval $CMD
RUNVALIDATE
chmod +x "$BUILD_DIR/run_validate.sh"
echo "  $BUILD_DIR/run_validate.sh"

# Comparison runner — compare baseline vs guard-agent validation results
cat > "$BUILD_DIR/run_compare.sh" << 'RUNCOMPARE'
#!/usr/bin/env bash
set -e

# Usage: ./run_compare.sh <app_name>
#
# Compares validation results between:
#   - build/validation_output/<app>_baseline/  (OpenCode without guard-agent)
#   - build/validation_output/<app>/           (OpenCode with guard-agent)
#
# Also diffs the source code changes and checks VeloC API coverage.
# Requires both validations to have been run first.
#
# Example:
#   ./build/run_validate.sh --baseline art_simple
#   ./build/run_validate.sh art_simple
#   ./build/run_compare.sh art_simple

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}"

APP_NAME="${1:?Usage: run_compare.sh <app_name>}"

# --- Resolve paths ---
BASELINE_OUTPUT="$SCRIPT_DIR/validation_output/${APP_NAME}_baseline"
GUARDAGENT_OUTPUT="$SCRIPT_DIR/validation_output/${APP_NAME}"
BASELINE_SRC="$SCRIPT_DIR/tests_baseline/$APP_NAME"
GUARDAGENT_SRC="$SCRIPT_DIR/tests/$APP_NAME"
REPORT_DIR="$SCRIPT_DIR/validation_output"

# --- Resolve original source ---
ORIGINAL_SRC=""
if [ -d "$REPO_ROOT/tests/examples/original/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/examples/original/$APP_NAME"
elif [ -d "$REPO_ROOT/tests/ecp/vanillas/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/ecp/vanillas/$APP_NAME"
fi

# --- Check prerequisites ---
MISSING=false
if [ ! -d "$BASELINE_OUTPUT" ]; then
  echo "WARNING: Baseline validation not found at $BASELINE_OUTPUT" >&2
  echo "  Run: ./build/run_validate.sh --baseline $APP_NAME" >&2
  MISSING=true
fi
if [ ! -d "$GUARDAGENT_OUTPUT" ]; then
  echo "WARNING: Guard-agent validation not found at $GUARDAGENT_OUTPUT" >&2
  echo "  Run: ./build/run_validate.sh $APP_NAME" >&2
  MISSING=true
fi
if [ "$MISSING" = true ]; then
  echo "" >&2
  echo "Run both validations first, then compare." >&2
  exit 1
fi

# --- Resolve iterative result files ---
BASELINE_RESULT="$SCRIPT_DIR/iterative_logs/${APP_NAME}_baseline/result.json"
GUARDAGENT_RESULT="$SCRIPT_DIR/iterative_logs/${APP_NAME}_guard-agent/result.json"

ITER_FLAGS=""
[ -f "$BASELINE_RESULT" ] && ITER_FLAGS="$ITER_FLAGS --iterative-result-a $BASELINE_RESULT"
[ -f "$GUARDAGENT_RESULT" ] && ITER_FLAGS="$ITER_FLAGS --iterative-result-b $GUARDAGENT_RESULT"

python -m validation.veloc.compare "$APP_NAME" \
  --output-dir-a "$BASELINE_OUTPUT" \
  --label-a "Baseline (no guard-agent)" \
  --output-dir-b "$GUARDAGENT_OUTPUT" \
  --label-b "With guard-agent" \
  --original-src "$ORIGINAL_SRC" \
  --resilient-src-a "$BASELINE_SRC" \
  --resilient-src-b "$GUARDAGENT_SRC" \
  --report-dir "$REPORT_DIR" \
  $ITER_FLAGS
RUNCOMPARE
chmod +x "$BUILD_DIR/run_compare.sh"
echo "  $BUILD_DIR/run_compare.sh"

# Iterative runner — loop OpenCode + validation until correctness passes
cat > "$BUILD_DIR/run_iterative.sh" << 'RUNITER'
#!/usr/bin/env bash
set -e

# Usage: ./run_iterative.sh [--baseline] <app_name> [--max-iters N]
#
# Automated evaluation loop:
#   1. Run OpenCode non-interactively with the app's prompt
#   2. Run correctness validation
#   3. If PASS → done
#   4. If FAIL → feed error logs back to OpenCode and repeat
#
# Captures per-iteration metrics: elapsed time, validation result.
# Saves enriched result.json with timing data for comparison.
#
# Modes:
#   ./build/run_iterative.sh art_simple              # with guard-agent MCP
#   ./build/run_iterative.sh --baseline art_simple   # without guard-agent (baseline)
#
# Options:
#   --max-iters N    Maximum iterations (default: 5)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}"

# --- Parse args ---
USE_BASELINE=false
MAX_ITERS=5

while [ $# -gt 0 ]; do
  case "$1" in
    --baseline)   USE_BASELINE=true; shift ;;
    --max-iters)  MAX_ITERS="$2"; shift 2 ;;
    -*)           echo "Unknown option: $1" >&2; exit 1 ;;
    *)            break ;;
  esac
done

APP_NAME="${1:?Usage: run_iterative.sh [--baseline] <app_name> [--max-iters N]}"

# --- Resolve paths ---
if [ "$USE_BASELINE" = true ]; then
  APP_DIR="$SCRIPT_DIR/tests_baseline/$APP_NAME"
  LABEL="baseline"
  VALIDATE_FLAG="--baseline"
else
  APP_DIR="$SCRIPT_DIR/tests/$APP_NAME"
  LABEL="guard-agent"
  VALIDATE_FLAG=""
fi

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: App directory not found: $APP_DIR" >&2
  exit 1
fi

PROMPT_FILE="$APP_DIR/prompt.txt"
if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: No prompt.txt found in $APP_DIR" >&2
  exit 1
fi

INITIAL_PROMPT="$(cat "$PROMPT_FILE")"
LOG_DIR="$SCRIPT_DIR/iterative_logs/${APP_NAME}_${LABEL}"
mkdir -p "$LOG_DIR"

echo "════════════════════════════════════════════════════════════════════"
echo "  Iterative evaluation: $APP_NAME ($LABEL)"
echo "════════════════════════════════════════════════════════════════════"
echo "  App directory: $APP_DIR"
echo "  Max iterations: $MAX_ITERS"
echo "  Logs: $LOG_DIR"
echo ""

# --- Metrics accumulators ---
TOTAL_ELAPSED="0.0"
TOTAL_INPUT_TOKENS=0
TOTAL_OUTPUT_TOKENS=0
TOTAL_TOKENS=0
ITER_METRICS=""  # will be built as JSON array entries
EVAL_START=$(date +%s.%N)

# --- Iteration loop ---
for ITER in $(seq 1 "$MAX_ITERS"); do
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  Iteration $ITER / $MAX_ITERS"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""

  ITER_LOG="$LOG_DIR/iter_${ITER}"
  mkdir -p "$ITER_LOG"

  # --- Step 1: Build the prompt ---
  if [ "$ITER" -eq 1 ]; then
    PROMPT="$INITIAL_PROMPT"
  else
    # Feed back the validation error from the previous iteration
    PREV_LOG="$LOG_DIR/iter_$((ITER - 1))"
    PROMPT="The previous attempt to make this code resilient with VeloC checkpointing failed validation.

Here is the validation output from the failed run:

--- VALIDATION STDOUT ---
$(tail -100 "$PREV_LOG/validate_stdout.txt" 2>/dev/null || echo "(no stdout)")

--- VALIDATION STDERR ---
$(tail -100 "$PREV_LOG/validate_stderr.txt" 2>/dev/null || echo "(no stderr)")

--- BUILD OUTPUT ---
$(tail -50 "$PREV_LOG/build_output.txt" 2>/dev/null || echo "(no build output)")

Please analyze the errors above and fix the VeloC checkpoint injection.
The code is in the current directory. Review what was done wrong, fix it, and ensure:
1. VeloC is properly initialized after MPI_Init
2. Critical state is registered with VELOC_Mem_protect
3. Restart logic checks for existing checkpoints before the main loop
4. Checkpoints are taken inside the main computation loop
5. VeloC is finalized before MPI_Finalize
6. veloc.cfg exists with valid scratch/persistent paths
7. CMakeLists.txt links veloc-client"
  fi

  # Save the prompt for debugging
  printf '%s\n' "$PROMPT" > "$ITER_LOG/prompt.txt"

  # --- Step 2: Run OpenCode (timed) ---
  echo "[iter $ITER] Running OpenCode ($LABEL)..."
  OPENCODE_START=$(date +%s.%N)
  OPENCODE_START_MS=$(date +%s%3N)
  cd "$APP_DIR"

  opencode run "$PROMPT" > "$ITER_LOG/opencode_stdout.txt" 2> "$ITER_LOG/opencode_stderr.txt" || true

  cd "$SCRIPT_DIR/.."
  OPENCODE_END=$(date +%s.%N)
  OPENCODE_ELAPSED=$(echo "$OPENCODE_END - $OPENCODE_START" | bc 2>/dev/null || echo "0")
  echo "[iter $ITER] OpenCode finished in ${OPENCODE_ELAPSED}s"

  # --- Extract token usage from OpenCode's SQLite DB ---
  OPENCODE_DB="$HOME/.local/share/opencode/opencode.db"
  ITER_INPUT_TOKENS=0
  ITER_OUTPUT_TOKENS=0
  ITER_TOTAL_TOKENS=0
  if [ -f "$OPENCODE_DB" ]; then
    TOKENS_JSON=$(python3 -c "
import sqlite3, json, sys
try:
    db = sqlite3.connect('$OPENCODE_DB')
    c = db.cursor()
    # Find the most recent session in this app directory that started after our run began
    c.execute('''
        SELECT m.session_id,
               COALESCE(SUM(json_extract(m.data, \"$.tokens.input\")), 0),
               COALESCE(SUM(json_extract(m.data, \"$.tokens.output\")), 0),
               COALESCE(SUM(json_extract(m.data, \"$.tokens.total\")), 0)
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE s.directory = '$APP_DIR'
          AND json_extract(m.data, \"$.role\") = \"assistant\"
          AND json_extract(m.data, \"$.tokens.total\") IS NOT NULL
          AND s.time_created >= $OPENCODE_START_MS
        GROUP BY m.session_id
        ORDER BY s.time_created DESC
        LIMIT 1
    ''')
    row = c.fetchone()
    db.close()
    if row:
        print(json.dumps({'input': int(row[1]), 'output': int(row[2]), 'total': int(row[3])}))
    else:
        print(json.dumps({'input': 0, 'output': 0, 'total': 0}))
except Exception as e:
    print(json.dumps({'input': 0, 'output': 0, 'total': 0, 'error': str(e)}), file=sys.stderr)
    print(json.dumps({'input': 0, 'output': 0, 'total': 0}))
" 2>/dev/null)
    ITER_INPUT_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('input',0))" 2>/dev/null || echo "0")
    ITER_OUTPUT_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('output',0))" 2>/dev/null || echo "0")
    ITER_TOTAL_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
    echo "[iter $ITER] Tokens: input=$ITER_INPUT_TOKENS output=$ITER_OUTPUT_TOKENS total=$ITER_TOTAL_TOKENS"
  fi

  # --- Step 3: Run correctness validation (timed) ---
  echo "[iter $ITER] Running correctness validation..."
  VALIDATE_START=$(date +%s.%N)

  set +e
  "$SCRIPT_DIR/run_validate.sh" $VALIDATE_FLAG "$APP_NAME" \
    --skip-benchmarks --skip-report \
    > "$ITER_LOG/validate_stdout.txt" 2> "$ITER_LOG/validate_stderr.txt"
  VALIDATE_EXIT=$?
  set -e

  VALIDATE_END=$(date +%s.%N)
  VALIDATE_ELAPSED=$(echo "$VALIDATE_END - $VALIDATE_START" | bc 2>/dev/null || echo "0")
  ITER_ELAPSED=$(echo "$OPENCODE_ELAPSED + $VALIDATE_ELAPSED" | bc 2>/dev/null || echo "0")
  TOTAL_ELAPSED=$(echo "$TOTAL_ELAPSED + $ITER_ELAPSED" | bc 2>/dev/null || echo "0")

  # Extract build output for feedback (if build failed)
  grep -A 20 "Build failed\|CMake Error\|make.*Error\|error:" \
    "$ITER_LOG/validate_stdout.txt" "$ITER_LOG/validate_stderr.txt" \
    > "$ITER_LOG/build_output.txt" 2>/dev/null || true

  # Record per-iteration metrics
  ITER_PASSED="false"
  [ "$VALIDATE_EXIT" -eq 0 ] && ITER_PASSED="true"

  # Accumulate token counts
  TOTAL_INPUT_TOKENS=$((TOTAL_INPUT_TOKENS + ITER_INPUT_TOKENS))
  TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + ITER_OUTPUT_TOKENS))
  TOTAL_TOKENS=$((TOTAL_TOKENS + ITER_TOTAL_TOKENS))

  # Save per-iteration metrics
  cat > "$ITER_LOG/metrics.json" << EOFMETRICS
{
  "iter": $ITER,
  "opencode_elapsed_s": $OPENCODE_ELAPSED,
  "validation_elapsed_s": $VALIDATE_ELAPSED,
  "total_elapsed_s": $ITER_ELAPSED,
  "validation_passed": $ITER_PASSED,
  "input_tokens": $ITER_INPUT_TOKENS,
  "output_tokens": $ITER_OUTPUT_TOKENS,
  "total_tokens": $ITER_TOTAL_TOKENS
}
EOFMETRICS

  # Append to JSON array string
  [ -n "$ITER_METRICS" ] && ITER_METRICS="${ITER_METRICS},"
  ITER_METRICS="${ITER_METRICS}
    {\"iter\": $ITER, \"opencode_elapsed_s\": $OPENCODE_ELAPSED, \"validation_elapsed_s\": $VALIDATE_ELAPSED, \"total_elapsed_s\": $ITER_ELAPSED, \"validation_passed\": $ITER_PASSED, \"input_tokens\": $ITER_INPUT_TOKENS, \"output_tokens\": $ITER_OUTPUT_TOKENS, \"total_tokens\": $ITER_TOTAL_TOKENS}"

  # --- Step 4: Check result ---
  if [ "$VALIDATE_EXIT" -eq 0 ]; then
    EVAL_END=$(date +%s.%N)
    WALL_ELAPSED=$(echo "$EVAL_END - $EVAL_START" | bc 2>/dev/null || echo "0")

    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  PASS — Correctness validation passed on iteration $ITER"
    echo "  Total OpenCode+validation time: ${TOTAL_ELAPSED}s"
    echo "  Wall-clock time: ${WALL_ELAPSED}s"
    echo "  Total tokens: ${TOTAL_TOKENS} (input: ${TOTAL_INPUT_TOKENS}, output: ${TOTAL_OUTPUT_TOKENS})"
    echo "════════════════════════════════════════════════════════════════════"

    cat > "$LOG_DIR/result.json" << EOFRESULT
{
  "app_name": "$APP_NAME",
  "mode": "$LABEL",
  "passed": true,
  "iterations": $ITER,
  "max_iters": $MAX_ITERS,
  "total_elapsed_s": $TOTAL_ELAPSED,
  "wall_elapsed_s": $WALL_ELAPSED,
  "total_input_tokens": $TOTAL_INPUT_TOKENS,
  "total_output_tokens": $TOTAL_OUTPUT_TOKENS,
  "total_tokens": $TOTAL_TOKENS,
  "per_iteration": [$ITER_METRICS
  ]
}
EOFRESULT
    exit 0
  else
    echo "[iter $ITER] FAIL — Validation failed (${ITER_ELAPSED}s). $([ "$ITER" -lt "$MAX_ITERS" ] && echo "Retrying..." || echo "Max iterations reached.")"
    grep -E "FATAL|FAIL|Error|error:" "$ITER_LOG/validate_stderr.txt" 2>/dev/null | head -5
  fi
done

# --- Max iterations exhausted ---
EVAL_END=$(date +%s.%N)
WALL_ELAPSED=$(echo "$EVAL_END - $EVAL_START" | bc 2>/dev/null || echo "0")

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  FAIL — Did not pass after $MAX_ITERS iterations"
echo "  Total OpenCode+validation time: ${TOTAL_ELAPSED}s"
echo "  Wall-clock time: ${WALL_ELAPSED}s"
echo "  Total tokens: ${TOTAL_TOKENS} (input: ${TOTAL_INPUT_TOKENS}, output: ${TOTAL_OUTPUT_TOKENS})"
echo "════════════════════════════════════════════════════════════════════"
echo "  Logs: $LOG_DIR"

cat > "$LOG_DIR/result.json" << EOFRESULT
{
  "app_name": "$APP_NAME",
  "mode": "$LABEL",
  "passed": false,
  "iterations": $MAX_ITERS,
  "max_iters": $MAX_ITERS,
  "total_elapsed_s": $TOTAL_ELAPSED,
  "wall_elapsed_s": $WALL_ELAPSED,
  "total_input_tokens": $TOTAL_INPUT_TOKENS,
  "total_output_tokens": $TOTAL_OUTPUT_TOKENS,
  "total_tokens": $TOTAL_TOKENS,
  "per_iteration": [$ITER_METRICS
  ]
}
EOFRESULT
exit 1
RUNITER
chmod +x "$BUILD_DIR/run_iterative.sh"
echo "  $BUILD_DIR/run_iterative.sh"

# Unified evaluation — runs both baseline and guard-agent, then compares
cat > "$BUILD_DIR/run_evaluate.sh" << 'RUNEVALUATE'
#!/usr/bin/env bash

# Usage: ./run_evaluate.sh <app_name> [--max-iters N]
#
# Runs the full evaluation pipeline:
#   1. Baseline:    opencode without guard-agent (iterative loop)
#   2. Guard-agent: opencode with guard-agent MCP (iterative loop)
#   3. Comparison:  side-by-side report with metrics
#
# Example:
#   ./build/run_evaluate.sh art_simple
#   ./build/run_evaluate.sh art_simple --max-iters 10

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MAX_ITERS_FLAG=""
APP_NAME=""

for arg in "$@"; do
  case "$arg" in
    --max-iters) MAX_ITERS_FLAG="--max-iters"; continue ;;
    *)
      if [ "$MAX_ITERS_FLAG" = "--max-iters" ] && [ -z "$MAX_ITERS_VAL" ]; then
        MAX_ITERS_VAL="$arg"
        MAX_ITERS_FLAG="--max-iters $arg"
        continue
      fi
      [ -z "$APP_NAME" ] && APP_NAME="$arg"
      ;;
  esac
done

if [ -z "$APP_NAME" ]; then
  echo "Usage: run_evaluate.sh <app_name> [--max-iters N]" >&2
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Full Evaluation: $APP_NAME"
echo "║  Baseline (no guard-agent) vs Guard-agent (with MCP tools)"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# --- Phase 1: Guard-agent ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 1: Guard-agent (OpenCode with guard-agent MCP)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
set +e
"$SCRIPT_DIR/run_iterative.sh" "$APP_NAME" $MAX_ITERS_FLAG
GUARDAGENT_EXIT=$?
set -e
echo ""

# --- Phase 2: Baseline ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 2: Baseline (OpenCode without guard-agent)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
set +e
"$SCRIPT_DIR/run_iterative.sh" --baseline "$APP_NAME" $MAX_ITERS_FLAG
BASELINE_EXIT=$?
set -e
echo ""

# --- Phase 3: Comparison ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 3: Comparison"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
"$SCRIPT_DIR/run_compare.sh" "$APP_NAME"
echo ""

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Evaluation complete: $APP_NAME"
echo "║  Guard-agent exit:  $GUARDAGENT_EXIT $([ $GUARDAGENT_EXIT -eq 0 ] && echo '(PASS)' || echo '(FAIL)')"
echo "║  Baseline exit:     $BASELINE_EXIT $([ $BASELINE_EXIT -eq 0 ] && echo '(PASS)' || echo '(FAIL)')"
echo "║  Report: build/validation_output/comparison_${APP_NAME}.md"
echo "╚══════════════════════════════════════════════════════════════════════╝"
RUNEVALUATE
fi  # end dead code block

# App validation runner (validate vanilla vs checkpointed pairs)
create_runner "validate_apps" "validation/veloc/validate_apps.py"

# ── Print summary ────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Setup complete."
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Test applications (clean originals, ready for resilience injection):"
if [ -d "$TESTS_DIR" ]; then
  for app_dir in "$TESTS_DIR"/*/; do
    [ -d "$app_dir" ] || continue
    app_name="$(basename "$app_dir")"
    prompt_file="$app_dir/prompt.txt"
    echo "  build/tests/$app_name/"
    if [ -f "$prompt_file" ]; then
      echo "    prompt: $(head -1 "$prompt_file")"
    fi
  done
fi
echo ""
echo "Workflow (with guard-agent):"
echo "  1. cd build/tests/<app_name>"
echo "  2. Start OpenCode (guard-agent MCP auto-configured)"
echo "  3. Instruct the agent to make the code resilient"
echo "  4. Validate: ./build/run_validate.sh <app_name>"
echo ""
echo "Workflow (baseline — no guard-agent, for comparison):"
echo "  1. cd build/tests_baseline/<app_name>"
echo "  2. Start OpenCode (no MCP, agent uses its own knowledge)"
echo "  3. Instruct the agent to make the code resilient"
echo "  4. Validate: ./build/run_validate.sh --baseline <app_name>"
echo ""
echo "Full evaluation (runs both approaches, then compares):"
echo "  ./build/run_evaluate.sh art_simple                  # baseline + guard-agent + comparison"
echo "  ./build/run_evaluate.sh art_simple --max-iters 10   # custom max iterations"
echo ""
echo "Or run each approach separately:"
echo "  ./build/run_iterative.sh --baseline art_simple      # baseline only"
echo "  ./build/run_iterative.sh art_simple                 # guard-agent only"
echo "  ./build/run_compare.sh art_simple                   # compare results"
echo ""
echo "Guard-agent MCP server command:"
echo "  guard-agent serve"
echo ""
echo "Standalone agent (requires LLM API key):"
echo "  ./build/run_start_agent.sh"
echo ""
echo "Reference solutions for comparison:"
echo "  build/ref_solutions/"
echo ""
echo "Test data:"
echo "  build/data/"
echo ""
echo "App validation (verify vanilla/checkpointed pairs):"
echo "  ./build/run_validate_apps.sh --list              # list all 20 apps"
echo "  ./build/run_validate_apps.sh --status            # show progress"
echo "  ./build/run_validate_apps.sh --app CoMD          # validate one app"
echo "  ./build/run_validate_apps.sh                     # validate all (resumes automatically)"
echo "  ./build/run_validate_apps.sh --fresh             # re-validate from scratch"
echo ""
