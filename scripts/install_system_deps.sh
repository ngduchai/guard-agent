#!/usr/bin/env bash
# Install system packages required by benchmark applications.
#
# Usage:
#   sudo ./scripts/install_system_deps.sh
#
# Packages installed:
#   - BLAS/LAPACK development headers (libopenblas-dev, liblapacke-dev)
#   - Boost C++ libraries (libboost-all-dev)
#   - HDF5 with MPI support (libhdf5-openmpi-dev)
#   - Build tools (autoconf, automake, libtool, pkg-config)
#   - zlib development headers
set -euo pipefail

if [[ $EUID -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
  echo "This script needs root privileges. Run with sudo or as root."
  exit 1
fi

SUDO=""
if [[ $EUID -ne 0 ]]; then
  SUDO="sudo"
fi

echo "============================================================"
echo "  Installing system dependencies for benchmark apps"
echo "============================================================"
echo ""

$SUDO apt-get update -qq

$SUDO apt-get install -y \
  build-essential \
  gfortran \
  libopenblas-dev \
  liblapack-dev \
  liblapacke-dev \
  libboost-all-dev \
  libhdf5-openmpi-dev \
  autoconf automake libtool \
  pkg-config \
  zlib1g-dev \
  libjemalloc-dev

echo ""
echo "[OK] System dependencies installed."
