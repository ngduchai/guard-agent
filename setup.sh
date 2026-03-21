#!/usr/bin/env bash
#
# Create a build directory with a venv and install the project so examples
# can be run via build/run_*.sh scripts. Run from the guard-agent repo root.
#
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$REPO_ROOT/build"

echo "Repository root: $REPO_ROOT"
echo "Build directory: $BUILD_DIR"

mkdir -p "$BUILD_DIR"

# ── Knowledge base: snapshot before cleaning ────────────────────────────────
# The knowledge_db/ directory accumulates VeloC insights across sessions.
# If a knowledge base already exists, save a timestamped backup now (before
# the clean sweep) and then preserve the directory intact.  Only create a
# fresh empty knowledge base when none exists yet.
KNOWLEDGE_DB_DIR="$BUILD_DIR/knowledge_db"
KNOWLEDGE_DB_FILE="$KNOWLEDGE_DB_DIR/knowledge.json"
KNOWLEDGE_BACKUP_DIR="$KNOWLEDGE_DB_DIR/backups"
_KNOWLEDGE_EXISTS=false
if [ -f "$KNOWLEDGE_DB_FILE" ]; then
  _KNOWLEDGE_EXISTS=true
  TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$KNOWLEDGE_BACKUP_DIR"
  cp "$KNOWLEDGE_DB_FILE" "$KNOWLEDGE_BACKUP_DIR/knowledge_${TIMESTAMP}.json"
  echo "Knowledge base backup saved → $KNOWLEDGE_BACKUP_DIR/knowledge_${TIMESTAMP}.json"
fi

# Clean generated/output files from a previous run before refreshing the sandbox.
# Remove everything inside BUILD_DIR except the preserved folders:
#   - log/          : run history / agent logs
#   - venv/         : Python virtual environment (expensive to recreate)
#   - knowledge_db/ : accumulated insights (preserved when it already exists)
echo "Cleaning generated files from previous runs ..."
if [ -d "$BUILD_DIR" ]; then
  for entry in "$BUILD_DIR"/*; do
    base="$(basename "$entry")"
    case "$base" in
      log|venv|knowledge_db)
        echo "  Preserving $entry"
        ;;
      *)
        rm -rf "$entry"
        echo "  Removed $entry"
        ;;
    esac
  done
fi

# ── Knowledge base: create only if none existed ──────────────────────────────
# If there was no knowledge base before the clean, create the directory now
# so the agent can initialise it on first run.
if [ "$_KNOWLEDGE_EXISTS" = false ]; then
  mkdir -p "$KNOWLEDGE_DB_DIR"
  echo "Knowledge base: no existing DB found, directory created for first run."
else
  echo "Knowledge base: existing DB preserved → $KNOWLEDGE_DB_FILE"
fi

# Copy examples into build for test/demonstration (self-contained runs from build/)
if [ -d "$REPO_ROOT/tests/examples/original" ]; then
  echo "Copying examples/original to $BUILD_DIR/examples ..."
  cp -r "$REPO_ROOT/tests/examples/original" "$BUILD_DIR/examples"
  echo "  $BUILD_DIR/examples"
fi
if [ -d "$REPO_ROOT/tests/ecp" ]; then
  echo "Copying ecp to $BUILD_DIR/ecp ..."
  cp -r "$REPO_ROOT/tests/ecp" "$BUILD_DIR"
  echo "  $BUILD_DIR/ecp"
fi
if [ -d "$REPO_ROOT/tests/data" ]; then
  echo "Copying data to $BUILD_DIR/data ..."
  cp -r "$REPO_ROOT/tests/data" "$BUILD_DIR/data"
  echo "  $BUILD_DIR/data"
fi

if [ ! -d "$BUILD_DIR/venv" ]; then
  echo "Creating virtualenv in build/venv ..."
  python3 -m venv "$BUILD_DIR/venv"
fi

echo "Activating venv and installing dependencies ..."
# shellcheck source=/dev/null
. "$BUILD_DIR/venv/bin/activate"

pip install -q -r "$REPO_ROOT/orchestrator/requirements.txt"
[ -f "$REPO_ROOT/shared/requirements.txt" ] && pip install -q -r "$REPO_ROOT/shared/requirements.txt" || true
[ -f "$REPO_ROOT/validation/requirements.txt" ] && pip install -q -r "$REPO_ROOT/validation/requirements.txt" || true

# Configure LLM API key for the deployment agent (OpenAI-compatible endpoint).
# The key is stored in the build directory so that build/ is self-contained.
# Prefer ARGO_API_KEY; fall back to OPENAI_API_KEY.
BUILD_KEY_FILE="$BUILD_DIR/api_key"
ROOT_KEY_FILE="$REPO_ROOT/api_key"

# Key source precedence:
# 1) ARGO_API_KEY env (explicit override)
# 2) OPENAI_API_KEY env (explicit override)
# 3) Root `api_key` file (so you don't need to re-set env vars)
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
  echo "ERROR: LLM API key not configured for the deployment agent." >&2
  echo "The setup script looks for the key in either:" >&2
  echo "  - $ROOT_KEY_FILE (a file containing your key on a single line), or" >&2
  echo "  - the ARGO_API_KEY environment variable at install time," >&2
  echo "  - the OPENAI_API_KEY environment variable at install time." >&2
  echo "Create one of these and re-run ./setup.sh." >&2
  exit 1
fi

# Runner scripts: set REPO_ROOT, activate venv, set PYTHONPATH, run example
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

echo "Creating example runner scripts ..."
create_runner "transform_request" "examples/transform_request.py"

# Script to start the orchestrator server from the build env
cat > "$BUILD_DIR/run_orchestrator.sh" << 'RUNORCH'
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}/orchestrator:${REPO_ROOT}"

# Force OpenAI-compatible SDK calls to the Argo endpoint.
export LLM_PROVIDER="${LLM_PROVIDER:-argo}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://apps-dev.inside.anl.gov/argoapi/v1}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-$OPENAI_BASE_URL}"

# Load LLM API key for orchestrator plans.
# The OpenAI Agents SDK consumes OPENAI_API_KEY (and OPENAI_BASE_URL), but
# we keep this runner flexible so you can pass ARGO_API_KEY at runtime.
if [ -z "${OPENAI_API_KEY:-}" ]; then
  if [ -n "${ARGO_API_KEY:-}" ]; then
    OPENAI_API_KEY="$ARGO_API_KEY"
  else
    KEY_FILE="${SCRIPT_DIR}/api_key"
    if [ ! -f "$KEY_FILE" ]; then
      echo "ERROR: LLM API key file not found at '$KEY_FILE'." >&2
      echo "Re-run ./setup.sh to configure it." >&2
      exit 1
    fi
    OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')"
  fi
fi
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY is empty." >&2
  exit 1
fi
export OPENAI_API_KEY

exec python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 "$@"
RUNORCH
chmod +x "$BUILD_DIR/run_orchestrator.sh"
echo "  $BUILD_DIR/run_orchestrator.sh"

# Script to start the interactive deployment agent from the build env
cat > "$BUILD_DIR/run_start_agent.sh" << 'RUNAGENT'
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/agents"

# Force OpenAI-compatible SDK calls to the Argo endpoint.
export LLM_PROVIDER="${LLM_PROVIDER:-argo}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://apps-dev.inside.anl.gov/argoapi/v1}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-$OPENAI_BASE_URL}"

# Project root for the agent: the build directory itself (self-contained sandbox).
# All agent file access (reads and writes) is restricted to this directory.
export GUARD_AGENT_PROJECT_ROOT="${SCRIPT_DIR}"

# Load LLM API key for the deployment agent.
# Prefer ARGO_API_KEY (runtime), otherwise use OPENAI_API_KEY (runtime), otherwise
# fall back to the stored key in build/api_key.
if [ -z "${OPENAI_API_KEY:-}" ]; then
  if [ -n "${ARGO_API_KEY:-}" ]; then
    OPENAI_API_KEY="$ARGO_API_KEY"
  else
    KEY_FILE="${SCRIPT_DIR}/api_key"
    if [ ! -f "$KEY_FILE" ]; then
      echo "ERROR: LLM API key file not found at '$KEY_FILE'." >&2
      echo "Re-run ./setup.sh to configure the key." >&2
      exit 1
    fi
    OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')"
  fi
fi
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY is empty." >&2
  exit 1
fi
export OPENAI_API_KEY

exec python -m agents.veloc.start_agent "$@"
RUNAGENT
chmod +x "$BUILD_DIR/run_start_agent.sh"
echo "  $BUILD_DIR/run_start_agent.sh"

# Script to start the deployment agent Web UI from the build env
cat > "$BUILD_DIR/run_deploy_webui.sh" << 'RUNWEB'
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/agents"

# Force OpenAI-compatible SDK calls to the Argo endpoint.
export LLM_PROVIDER="${LLM_PROVIDER:-argo}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://apps-dev.inside.anl.gov/argoapi/v1}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-$OPENAI_BASE_URL}"

# Project root for the agent: the build directory itself (self-contained sandbox).
# All agent file access (reads and writes) is restricted to this directory.
export GUARD_AGENT_PROJECT_ROOT="${SCRIPT_DIR}"

# Load LLM API key for the deployment agent.
if [ -z "${OPENAI_API_KEY:-}" ]; then
  if [ -n "${ARGO_API_KEY:-}" ]; then
    OPENAI_API_KEY="$ARGO_API_KEY"
  else
    KEY_FILE="${SCRIPT_DIR}/api_key"
    if [ ! -f "$KEY_FILE" ]; then
      echo "ERROR: LLM API key file not found at '$KEY_FILE'." >&2
      echo "Re-run ./setup.sh to configure the key." >&2
      exit 1
    fi
    OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')"
  fi
fi
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY is empty." >&2
  exit 1
fi
export OPENAI_API_KEY

exec python -m uvicorn agents.veloc.webui:app --host 0.0.0.0 --port 8010 "$@"
RUNWEB
chmod +x "$BUILD_DIR/run_deploy_webui.sh"
echo "  $BUILD_DIR/run_deploy_webui.sh"

echo ""
echo "Done. From repo root you can run:"
echo "  ./build/run_transform_request.sh   # needs orchestrator running; set ARGO_API_KEY (or OPENAI_API_KEY) for LLM"
echo "  ./build/run_orchestrator.sh         # start the orchestrator API server"
echo "  ./build/run_start_agent.sh          # start the interactive deployment agent"
echo "  ./build/run_deploy_webui.sh         # start the deployment agent Web UI on http://localhost:8010"
