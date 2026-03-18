#!/usr/bin/env bash
#
# Create a build directory with a venv and install the project so examples
# can be run via build/run_*.sh scripts. Run from the guard-agent repo root.
#
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$REPO_ROOT/build"
DEFAULT_OUTPUT_ROOT_REL="examples_output"

echo "Repository root: $REPO_ROOT"
echo "Build directory: $BUILD_DIR"

mkdir -p "$BUILD_DIR"
mkdir -p "$REPO_ROOT/$DEFAULT_OUTPUT_ROOT_REL"

# Copy examples into build for test/demonstration (self-contained runs from build/)
if [ -d "$REPO_ROOT/examples" ]; then
  echo "Copying examples to $BUILD_DIR/examples ..."
  rm -rf "$BUILD_DIR/examples"
  cp -r "$REPO_ROOT/examples" "$BUILD_DIR/examples"
  echo "  $BUILD_DIR/examples"
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

# Configure OpenAI API key for the deployment agent.
# The key is stored in the build directory so that build/ is self-contained.
BUILD_KEY_FILE="$BUILD_DIR/api_key"
ROOT_KEY_FILE="$REPO_ROOT/api_key"
if [ ! -f "$BUILD_KEY_FILE" ]; then
  if [ -f "$ROOT_KEY_FILE" ]; then
    echo "Copying OpenAI API key from $ROOT_KEY_FILE to $BUILD_KEY_FILE"
    cp "$ROOT_KEY_FILE" "$BUILD_KEY_FILE"
  elif [ -n "$OPENAI_API_KEY" ]; then
    echo "Writing OpenAI API key from environment to $BUILD_KEY_FILE"
    printf '%s\n' "$OPENAI_API_KEY" > "$BUILD_KEY_FILE"
  else
    echo "ERROR: OpenAI API key not configured for the deployment agent." >&2
    echo "The setup script looks for the key in either:" >&2
    echo "  - $ROOT_KEY_FILE (a file containing your key on a single line), or" >&2
    echo "  - the OPENAI_API_KEY environment variable at install time." >&2
    echo "Create one of these and re-run ./setup.sh." >&2
    exit 1
  fi
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

# Project root for the agent (full repo); paths like examples/ are relative to this.
export GUARD_AGENT_PROJECT_ROOT="${REPO_ROOT}"

# Restrict agent writes to an explicit output directory (relative to repo root).
# Users should supply an output folder like `examples_output/...`; the UI/runner
# can set this env var accordingly before launching. We default to a safe sandbox
# under examples_output/ so the repo root stays clean.
export GUARD_AGENT_OUTPUT_ROOT="${GUARD_AGENT_OUTPUT_ROOT:-examples_output}"

# Load OpenAI API key from file inside the build directory so build/ is self-contained.
KEY_FILE="${SCRIPT_DIR}/api_key"
if [ ! -f "$KEY_FILE" ]; then
  echo "ERROR: OpenAI API key file not found at '$KEY_FILE'." >&2
  echo "Re-run ./setup.sh to configure the key." >&2
  exit 1
fi

OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')"
if [ -z "$OPENAI_API_KEY" ]; then
  echo "ERROR: api_key file exists at '$KEY_FILE' but appears to be empty." >&2
  echo "Re-run ./setup.sh after fixing this file." >&2
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

# Project root for the agent (full repo); paths like examples/ are relative to this.
export GUARD_AGENT_PROJECT_ROOT="${REPO_ROOT}"

# Restrict agent writes to an explicit output directory (relative to repo root).
export GUARD_AGENT_OUTPUT_ROOT="${GUARD_AGENT_OUTPUT_ROOT:-examples_output}"

KEY_FILE="${SCRIPT_DIR}/api_key"
if [ ! -f "$KEY_FILE" ]; then
  echo "ERROR: OpenAI API key file not found at '$KEY_FILE'." >&2
  echo "Re-run ./setup.sh to configure the key." >&2
  exit 1
fi

OPENAI_API_KEY="$(head -n 1 "$KEY_FILE" | tr -d '\r\n')"
if [ -z "$OPENAI_API_KEY" ]; then
  echo "ERROR: api_key file exists at '$KEY_FILE' but appears to be empty." >&2
  echo "Re-run ./setup.sh after fixing this file." >&2
  exit 1
fi
export OPENAI_API_KEY

exec python -m uvicorn agents.veloc.webui:app --host 0.0.0.0 --port 8010 "$@"
RUNWEB
chmod +x "$BUILD_DIR/run_deploy_webui.sh"
echo "  $BUILD_DIR/run_deploy_webui.sh"

echo ""
echo "Done. From repo root you can run:"
echo "  ./build/run_transform_request.sh   # needs orchestrator running; set OPENAI_API_KEY for LLM"
echo "  ./build/run_orchestrator.sh         # start the orchestrator API server"
echo "  ./build/run_start_agent.sh          # start the interactive deployment agent"
echo "  ./build/run_deploy_webui.sh         # start the deployment agent Web UI on http://localhost:8010"
