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

if [ ! -d "$BUILD_DIR/venv" ]; then
  echo "Creating virtualenv in build/venv ..."
  python3 -m venv "$BUILD_DIR/venv"
fi

echo "Activating venv and installing dependencies ..."
# shellcheck source=/dev/null
. "$BUILD_DIR/venv/bin/activate"

pip install -q -r "$REPO_ROOT/orchestrator/requirements.txt"
pip install -q -r "$REPO_ROOT/resilience_mcp/requirements.txt"
[ -f "$REPO_ROOT/shared/requirements.txt" ] && pip install -q -r "$REPO_ROOT/shared/requirements.txt" || true

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
create_runner "list_tools"       "examples/list_tools.py"
create_runner "call_mcp_tool"    "examples/call_mcp_tool.py"
create_runner "transform_request" "examples/transform_request.py"

# Optional: script to start the orchestrator server from the build env
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

echo ""
echo "Done. From repo root you can run:"
echo "  ./build/run_list_tools.sh"
echo "  ./build/run_call_mcp_tool.sh"
echo "  ./build/run_transform_request.sh   # needs orchestrator running; set OPENAI_API_KEY for LLM"
echo "  ./build/run_orchestrator.sh         # start the orchestrator API server"
