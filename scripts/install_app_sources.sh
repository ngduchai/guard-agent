#!/usr/bin/env bash
# Download complete source trees for benchmark applications.
#
# Usage:
#   ./scripts/install_app_sources.sh              # download all
#   ./scripts/install_app_sources.sh --app AMG     # download one app
#   ./scripts/install_app_sources.sh --list        # list available apps
#
# Downloads full upstream source into tests/apps/vanillas/<app>/,
# preserving the existing app.yaml and prompt.txt files.
#
# Skipped apps (require exotic dependencies or are architecture-incompatible):
#   Chameleon (StarPU), DPLASMA (PaRSEC), Uintah (complex), ExaML (x86-only), deal.II (huge)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VANILLAS="${PROJECT_ROOT}/tests/apps/vanillas"
TMPDIR="${TMPDIR:-/tmp}/guard-agent-sources"

# ── Parse arguments ──────────────────────────────────────────────────────
APP_FILTER=""
LIST_ONLY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)     APP_FILTER="$2"; shift 2 ;;
    --app=*)   APP_FILTER="${1#--app=}"; shift ;;
    --list)    LIST_ONLY=true; shift ;;
    -h|--help)
      sed -n '2,/^set -euo/{ /^#/s/^# \?//p }' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

ok()   { echo "[OK]    $*"; }
skip() { echo "[SKIP]  $*"; }
info() { echo "[INFO]  $*"; }
fail() { echo "[FAIL]  $*" >&2; }

JOBS="$(nproc 2>/dev/null || echo 2)"

# ── App definitions ──────────────────────────────────────────────────────
# Each entry: name|repo_url|branch_or_tag|clone_flags|source_subdir
#   source_subdir: if the relevant source is in a subdirectory of the repo
APPS=(
  # Active 19-app benchmark suite — see tests/apps/README.md for attribution.
  # Format: name|url|branch|extra-clone-flags|subdir-after-clone-to-extract
  "CoMD|https://github.com/exmatex/CoMD.git|||"
  "CLAMR|https://github.com/lanl/CLAMR.git|||"
  "SW4lite|https://github.com/geodynamics/sw4lite.git|||"
  "MMSP|https://github.com/mesoscale/mmsp.git||--recurse-submodules|"
  "HyPar|https://github.com/debog/hypar.git|||"
  "SPPARKS|https://github.com/sandialabs/spparks.git|||"
  "HPCG|https://github.com/hpcg-benchmark/hpcg.git|||"
  "PRK_Stencil|https://github.com/ParRes/Kernels.git|||MPI1/Stencil"
  "SST|https://github.com/sstsimulator/sst-core.git|||"
  "Athena++|https://github.com/PrincetonUniversity/athena.git|||"
  "SPARTA|https://github.com/sandialabs/sparta.git|||"
  "OpenLB|https://gitlab.com/openlb/release.git|||"
  "Smilei|https://github.com/SmileiPIC/Smilei.git|||"
  "LAMMPS|https://github.com/lammps/lammps.git|stable_2Aug2023||"
  "SAMRAI|https://github.com/LLNL/SAMRAI.git||--recurse-submodules|"
  "ROSS|https://github.com/ROSS-org/ROSS.git||--recurse-submodules|"
  "WarpX|https://github.com/ECP-WarpX/WarpX.git|||"
  "QMCPACK|https://github.com/QMCPACK/qmcpack.git|||"
  "Nyx|https://github.com/AMReX-Astro/Nyx.git||--recurse-submodules|"

  # Apps formerly considered but dropped from the suite.  Kept here as a
  # historical record so a future operator can re-evaluate without having to
  # re-discover the URLs.
  # "AMG|https://github.com/LLNL/AMG.git|||"            # dropped: superseded by HPCG for class (1) preconditioned Krylov coverage
  # "miniFE|https://github.com/Mantevo/miniFE.git|||ref/src"  # dropped: lighter than HPCG and overlaps it
  # "Palabos|https://github.com/omalaspinas/palabos.git|||"   # dropped: OpenLB chosen as the LBM representative
  # "RAxML-NG|https://github.com/amkozlov/raxml-ng.git||--recurse-submodules|"  # dropped: out of scope for current taxonomy
  # "AMReX|https://github.com/AMReX-Codes/amrex.git|24.10||"   # dropped: AMReX is a framework dependency of Nyx/WarpX, not an app on its own
  # "Nektar++|https://gitlab.nektar.info/nektar/nektar.git|v5.7.0||"  # dropped: build-cost too high for current tier budget
  # "SU2|https://github.com/su2code/SU2.git|v8.1.0|--recurse-submodules|"  # dropped: covered by Athena++ for class (3) AMR
  # "miniVite|https://github.com/Exa-Graph/miniVite.git|||"  # dropped: FTI inlined into source without #ifdef guards (Issue #18)
)

if $LIST_ONLY; then
  echo "Available apps for source download:"
  for entry in "${APPS[@]}"; do
    IFS='|' read -r name url branch flags subdir <<< "$entry"
    tag="${branch:-HEAD}"
    echo "  ${name}  (${url} @ ${tag})"
  done
  echo ""
  echo "Skipped: Chameleon, DPLASMA, Uintah, ExaML, deal.II"
  exit 0
fi

echo "============================================================"
echo "  Downloading benchmark app source trees"
echo "  Project root : ${PROJECT_ROOT}"
echo "  Temp dir     : ${TMPDIR}"
echo "============================================================"
echo ""

mkdir -p "${TMPDIR}"

# ── Download function ────────────────────────────────────────────────────
download_app() {
  local name="$1" url="$2" branch="$3" flags="$4" subdir="$5"
  local dest="${VANILLAS}/${name}"

  # Check if already has complete source (heuristic: >20 source files)
  local src_count
  src_count=$(find "${dest}" -name '*.c' -o -name '*.cpp' -o -name '*.cc' -o -name '*.h' -o -name '*.hpp' -o -name '*.f' -o -name '*.f90' 2>/dev/null | wc -l)
  if [[ ${src_count} -gt 20 ]]; then
    skip "${name}: already has ${src_count} source files"
    return 0
  fi

  info "Downloading ${name} from ${url} ..."

  # Save existing app.yaml and prompt.txt
  local saved_yaml="" saved_prompt=""
  if [[ -f "${dest}/app.yaml" ]]; then
    saved_yaml=$(cat "${dest}/app.yaml")
  fi
  if [[ -f "${dest}/prompt.txt" ]]; then
    saved_prompt=$(cat "${dest}/prompt.txt")
  fi

  # Clone to temp
  local tmp_clone="${TMPDIR}/${name}"
  rm -rf "${tmp_clone}"

  local clone_cmd="git clone --depth 1"
  if [[ -n "${branch}" ]]; then
    clone_cmd+=" --branch ${branch}"
  fi
  if [[ -n "${flags}" ]]; then
    clone_cmd+=" ${flags}"
  fi
  clone_cmd+=" ${url} ${tmp_clone}"

  if ! eval "${clone_cmd}" 2>&1; then
    fail "${name}: git clone failed"
    return 1
  fi

  # Determine source directory
  local src_dir="${tmp_clone}"
  if [[ -n "${subdir}" ]]; then
    src_dir="${tmp_clone}/${subdir}"
  fi

  if [[ ! -d "${src_dir}" ]]; then
    fail "${name}: source subdirectory '${subdir}' not found in clone"
    return 1
  fi

  # Replace vanilla directory with full source
  rm -rf "${dest}"
  cp -a "${src_dir}" "${dest}"

  # Remove .git directory to save space
  rm -rf "${dest}/.git"

  # Restore app.yaml and prompt.txt
  if [[ -n "${saved_yaml}" ]]; then
    echo "${saved_yaml}" > "${dest}/app.yaml"
  fi
  if [[ -n "${saved_prompt}" ]]; then
    echo "${saved_prompt}" > "${dest}/prompt.txt"
  fi

  # Clean up temp clone
  rm -rf "${tmp_clone}"

  local new_count
  new_count=$(find "${dest}" -name '*.c' -o -name '*.cpp' -o -name '*.cc' -o -name '*.h' -o -name '*.hpp' 2>/dev/null | wc -l)
  ok "${name}: downloaded (${new_count} source files)"
}

# ── Main ─────────────────────────────────────────────────────────────────
downloaded=0
skipped=0
failed=0

for entry in "${APPS[@]}"; do
  IFS='|' read -r name url branch flags subdir <<< "$entry"

  # Filter if --app specified
  if [[ -n "${APP_FILTER}" ]] && [[ "${name}" != "${APP_FILTER}" ]]; then
    continue
  fi

  if download_app "${name}" "${url}" "${branch}" "${flags}" "${subdir}"; then
    ((downloaded++)) || true
  else
    ((failed++)) || true
  fi
  echo ""
done

echo "============================================================"
echo "  Source download complete."
echo "  Downloaded: ${downloaded}  Failed: ${failed}"
echo ""
echo "  Next steps:"
echo "    1. Run: ./scripts/install_system_deps.sh   (if not done)"
echo "    2. Run: ./setup.sh --clean"
echo "    3. Run: ./build/run_validate_apps.sh"
echo "============================================================"
