#!/usr/bin/env bash
# =============================================================================
# install_deps.sh — Install Kokkos and Cabana for ExaMPM (no sudo required)
#
# Builds Kokkos and Cabana from source and installs them to a user-local
# prefix (~/.local by default). No root/sudo privileges are needed.
#
# Prerequisites (assumed already installed on the system):
#   - CMake >= 3.12
#   - C++17-capable compiler (g++ >= 7)
#   - MPI (e.g., OpenMPI or MPICH)
#   - HDF5 with parallel support (optional, for particle output)
#   - wget or curl, tar, make
#
# Usage:
#   ./install_deps.sh [OPTIONS]
#
# Options:
#   --prefix DIR          Installation prefix (default: ~/.local)
#   --kokkos-version V    Kokkos version (default: 4.3.01)
#   --cabana-version V    Cabana version (default: 0.7.0)
#   --no-hdf5             Skip HDF5 support in Cabana (no particle output)
#   --serial-only         Build Kokkos with Serial backend only (no OpenMP)
#   --force-rebuild       Force rebuild even if already installed
#   -h, --help            Show this help message
#
# After running this script, build ExaMPM with:
#   make
# or:
#   mkdir build && cd build
#   cmake .. -DCMAKE_PREFIX_PATH=~/.local
#   cmake --build . --parallel
#
# To run (serial, 1 MPI rank):
#   mpirun -np 1 ./build/examples/FreeFall 0.05 2 0 0.001 1.0 10 serial
#   mpirun -np 1 ./build/examples/DamBreak 0.05 2 0 0.001 1.0 10 serial
# =============================================================================

set -euo pipefail

# ---- Defaults ----------------------------------------------------------------
INSTALL_PREFIX="${HOME}/.local"
KOKKOS_VERSION="4.3.01"
CABANA_VERSION="0.7.0"
ENABLE_HDF5=true
KOKKOS_DEVICES="OpenMP"
FORCE_REBUILD=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Argument parsing --------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      INSTALL_PREFIX="$2"; shift 2 ;;
    --kokkos-version)
      KOKKOS_VERSION="$2"; shift 2 ;;
    --cabana-version)
      CABANA_VERSION="$2"; shift 2 ;;
    --no-hdf5)
      ENABLE_HDF5=false; shift ;;
    --serial-only)
      KOKKOS_DEVICES="Serial"; shift ;;
    --force-rebuild)
      FORCE_REBUILD=true; shift ;;
    -h|--help)
      sed -n '2,50p' "$0"; exit 0 ;;
    *)
      echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ---- Helpers -----------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
error() { echo "[ERROR] $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" &>/dev/null || error "Required command '$1' not found. Please install it first."
}

# Download helper: tries wget first, then curl
download() {
  local url="$1"
  local dest="$2"
  if command -v wget &>/dev/null; then
    wget -q --show-progress -O "$dest" "$url"
  elif command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$dest" "$url"
  else
    error "Neither wget nor curl found. Please install one of them."
  fi
}

# Get actual top-level directory name from a tarball.
# Note: We use a subshell with pipefail disabled to avoid SIGPIPE (exit 141)
# when head closes the pipe early while tar is still listing files.
tarball_top_dir() {
  (set +o pipefail; tar -tzf "$1" | head -1 | cut -d/ -f1)
}

# ---- Check system prerequisites ----------------------------------------------
info "=== Checking system prerequisites ==="

require_cmd cmake
CMAKE_VERSION=$(cmake --version | head -1 | awk '{print $3}')
info "CMake found: $CMAKE_VERSION"

require_cmd g++
GXX_VERSION=$(g++ --version | head -1)
info "C++ compiler: $GXX_VERSION"

require_cmd tar
require_cmd make

if ! command -v wget &>/dev/null && ! command -v curl &>/dev/null; then
  error "Neither wget nor curl found. Please install one of them."
fi

# Check MPI is available (required by Cabana)
if ! command -v mpicxx &>/dev/null; then
  error "MPI C++ compiler (mpicxx) not found. Please install MPI (e.g., OpenMPI or MPICH) first."
fi
info "MPI C++ compiler: $(mpicxx --version 2>&1 | head -1)"

# Check HDF5 (optional)
if $ENABLE_HDF5; then
  if command -v h5pcc &>/dev/null; then
    info "Parallel HDF5 found (h5pcc available)."
  elif command -v h5cc &>/dev/null; then
    warn "Serial HDF5 found (h5cc). Cabana requires parallel HDF5 for particle output."
    warn "If the build fails, re-run with --no-hdf5 or install parallel HDF5."
  else
    echo "[ERROR] Parallel HDF5 (h5pcc) not found." >&2
    echo "[ERROR] HDF5 is required for particle output (.h5 files) and validation comparison." >&2
    echo "[ERROR] Install parallel HDF5 first, e.g.:" >&2
    echo "[ERROR]   Debian/Ubuntu: apt install libhdf5-mpi-dev" >&2
    echo "[ERROR]   RHEL/CentOS:   yum install hdf5-openmpi-devel" >&2
    error "Or re-run with --no-hdf5 to explicitly skip HDF5 support (no .h5 particle output)."
  fi
fi

NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
info "Parallel jobs: $NPROC"
info "Install prefix: $INSTALL_PREFIX"
mkdir -p "$INSTALL_PREFIX"

# ---- Install Kokkos from source ----------------------------------------------
info "=== Checking for Kokkos ==="

KOKKOS_FOUND=false
if ! $FORCE_REBUILD; then
  for search_dir in "$INSTALL_PREFIX" /usr /usr/local /opt/kokkos "${HOME}/.local"; do
    if [[ -f "$search_dir/lib/cmake/Kokkos/KokkosConfig.cmake" ]] || \
       [[ -f "$search_dir/lib64/cmake/Kokkos/KokkosConfig.cmake" ]]; then
      KOKKOS_FOUND=true
      info "Kokkos already installed at: $search_dir"
      break
    fi
  done
fi

if $KOKKOS_FOUND; then
  info "Kokkos is already installed. Skipping Kokkos build."
  info "Use --force-rebuild to reinstall."
else
  info "=== Installing Kokkos $KOKKOS_VERSION ==="

  KOKKOS_TARBALL="kokkos-${KOKKOS_VERSION}.tar.gz"
  KOKKOS_URL="https://github.com/kokkos/kokkos/archive/refs/tags/${KOKKOS_VERSION}.tar.gz"
  KOKKOS_BUILD_DIR="/tmp/kokkos-build-${KOKKOS_VERSION}"

  if [[ ! -f "/tmp/${KOKKOS_TARBALL}" ]]; then
    info "Downloading Kokkos from $KOKKOS_URL ..."
    download "$KOKKOS_URL" "/tmp/${KOKKOS_TARBALL}" || \
      error "Failed to download Kokkos. Check your internet connection."
  else
    info "Kokkos tarball already downloaded."
  fi

  KOKKOS_EXTRACTED_NAME=$(tarball_top_dir "/tmp/${KOKKOS_TARBALL}")
  KOKKOS_SRC_DIR="/tmp/${KOKKOS_EXTRACTED_NAME}"

  if [[ ! -d "$KOKKOS_SRC_DIR" ]]; then
    info "Extracting Kokkos..."
    tar -xzf "/tmp/${KOKKOS_TARBALL}" -C /tmp/
  else
    info "Kokkos source already extracted at $KOKKOS_SRC_DIR."
  fi

  OPENMP_FLAG=$([ "$KOKKOS_DEVICES" = "OpenMP" ] && echo "ON" || echo "OFF")
  info "Configuring Kokkos (devices: $KOKKOS_DEVICES)..."
  rm -rf "$KOKKOS_BUILD_DIR"
  mkdir -p "$KOKKOS_BUILD_DIR"

  cmake -S "$KOKKOS_SRC_DIR" -B "$KOKKOS_BUILD_DIR" \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    -DCMAKE_BUILD_TYPE=Release \
    -DKokkos_ENABLE_SERIAL=ON \
    -DKokkos_ENABLE_OPENMP="${OPENMP_FLAG}" \
    -DCMAKE_CXX_STANDARD=17

  info "Building Kokkos with $NPROC parallel jobs..."
  cmake --build "$KOKKOS_BUILD_DIR" --parallel "$NPROC"

  info "Installing Kokkos to $INSTALL_PREFIX ..."
  cmake --install "$KOKKOS_BUILD_DIR"

  rm -rf "$KOKKOS_BUILD_DIR"
  info "Kokkos $KOKKOS_VERSION installed successfully."
fi

# ---- Install Cabana from source ----------------------------------------------
info "=== Checking for Cabana ==="

CABANA_FOUND=false
if ! $FORCE_REBUILD; then
  for search_dir in "$INSTALL_PREFIX" /usr /usr/local "${HOME}/.local"; do
    if [[ -f "$search_dir/lib/cmake/Cabana/CabanaConfig.cmake" ]] || \
       [[ -f "$search_dir/lib64/cmake/Cabana/CabanaConfig.cmake" ]]; then
      CABANA_FOUND=true
      info "Cabana already installed at: $search_dir"
      break
    fi
  done
fi

if $CABANA_FOUND; then
  info "Cabana is already installed. Skipping Cabana build."
  info "Use --force-rebuild to reinstall."
else
  info "=== Installing Cabana $CABANA_VERSION ==="

  CABANA_TARBALL="cabana-${CABANA_VERSION}.tar.gz"
  CABANA_URL="https://github.com/ECP-copa/Cabana/archive/refs/tags/${CABANA_VERSION}.tar.gz"
  CABANA_BUILD_DIR="/tmp/cabana-build-${CABANA_VERSION}"

  if [[ ! -f "/tmp/${CABANA_TARBALL}" ]]; then
    info "Downloading Cabana from $CABANA_URL ..."
    download "$CABANA_URL" "/tmp/${CABANA_TARBALL}" || \
      error "Failed to download Cabana. Check your internet connection."
  else
    info "Cabana tarball already downloaded."
  fi

  # Determine the actual extracted directory name from the tarball.
  # GitHub archives use the repo name with original casing (e.g. Cabana-0.7.0).
  CABANA_EXTRACTED_NAME=$(tarball_top_dir "/tmp/${CABANA_TARBALL}")
  CABANA_SRC_DIR="/tmp/${CABANA_EXTRACTED_NAME}"

  if [[ ! -d "$CABANA_SRC_DIR" ]]; then
    info "Extracting Cabana..."
    tar -xzf "/tmp/${CABANA_TARBALL}" -C /tmp/
  else
    info "Cabana source already extracted at $CABANA_SRC_DIR."
  fi

  # Configure Cabana cmake options
  CABANA_CMAKE_OPTS=(
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX"
    -DCMAKE_PREFIX_PATH="$INSTALL_PREFIX"
    -DCMAKE_BUILD_TYPE=Release
    -DCabana_REQUIRE_MPI=ON
    -DCabana_ENABLE_GRID=ON
  )

  if $ENABLE_HDF5; then
    CABANA_CMAKE_OPTS+=( -DCabana_REQUIRE_HDF5=ON )
    info "Cabana will be built with parallel HDF5 support."
  else
    CABANA_CMAKE_OPTS+=( -DCMAKE_DISABLE_FIND_PACKAGE_HDF5=ON )
    info "Cabana will be built without HDF5 support."
  fi

  info "Configuring Cabana..."
  rm -rf "$CABANA_BUILD_DIR"
  mkdir -p "$CABANA_BUILD_DIR"

  cmake -S "$CABANA_SRC_DIR" -B "$CABANA_BUILD_DIR" "${CABANA_CMAKE_OPTS[@]}"

  info "Building Cabana with $NPROC parallel jobs..."
  cmake --build "$CABANA_BUILD_DIR" --parallel "$NPROC"

  info "Installing Cabana to $INSTALL_PREFIX ..."
  cmake --install "$CABANA_BUILD_DIR"

  rm -rf "$CABANA_BUILD_DIR"
  info "Cabana $CABANA_VERSION installed successfully."
fi

# ---- Summary -----------------------------------------------------------------
info ""
info "=== Dependency installation complete ==="
info ""
info "Installed / verified:"
info "  - CMake:  $(cmake --version | head -1)"
info "  - C++:    $(g++ --version | head -1)"
info "  - MPI:    $(mpicxx --version 2>&1 | head -1)"
info "  - Kokkos: $KOKKOS_VERSION (prefix: $INSTALL_PREFIX)"
info "  - Cabana: $CABANA_VERSION (prefix: $INSTALL_PREFIX)"
if $ENABLE_HDF5; then
  info "  - HDF5:   parallel HDF5 (particle output enabled)"
else
  info "  - HDF5:   disabled (no particle output)"
fi
info ""
info "IMPORTANT: Add the install prefix to your environment if not already set:"
info "  export PATH=\"${INSTALL_PREFIX}/bin:\$PATH\""
info "  export LD_LIBRARY_PATH=\"${INSTALL_PREFIX}/lib:\${LD_LIBRARY_PATH:-}\""
info ""
info "You can now build ExaMPM:"
SCRIPT_REL=$(realpath --relative-to="$(pwd)" "$SCRIPT_DIR" 2>/dev/null || echo "$SCRIPT_DIR")
info "  cd $SCRIPT_REL"
info "  make"
info ""
info "To run FreeFall (serial, 1 MPI rank):"
info "  mpirun -np 1 ./build/examples/FreeFall 0.05 2 0 0.001 1.0 10 serial"
info ""
info "To run DamBreak (serial, 1 MPI rank):"
info "  mpirun -np 1 ./build/examples/DamBreak 0.05 2 0 0.001 1.0 10 serial"
