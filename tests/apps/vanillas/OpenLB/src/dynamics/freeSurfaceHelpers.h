/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2021 Claudius Holeksa
 *                2024-2025 Danial Khazaeipoul
 *  E-mail contact: info@openlb.net
 *  The most recent release of OpenLB can be downloaded at
 *  <http://www.openlb.net/>
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; either version 2
 *  of the License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public
 *  License along with this program; if not, write to the Free
 *  Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 *  Boston, MA  02110-1301, USA.
*/

#pragma once

// #include <eigen3/Eigen/Dense>
#include "descriptor/fields.h"

namespace olb {

namespace FreeSurface {

struct Stage0 {};
struct Stage1 {};
struct Stage2 {};
struct Stage3 {};
struct Stage4 {};
struct Stage5 {};

template<typename T>
platform_constant T tolerance = std::is_same_v<T, float> ? T{1e-6} : T{1e-14};

template <typename T>
struct KahanSum {
  T sum{0}, c{0};

  inline void add(T x) noexcept {
    T y = x - c;
    T t = sum + y;
    c = (t - sum) - y;
    sum = t;
  }

  inline T value() const noexcept { return sum; }
};

enum class SolverType {
  plainLU,
  rowPivotingLU,
  completePivotingLU
  // eigen
};
platform_constant SolverType solver = SolverType::plainLU;

enum class NormalMethod {
  ParkerYoung,  // first  order
  LeastSquares  // second order (caution: not always!)
};
platform_constant NormalMethod method = NormalMethod::ParkerYoung;

platform_constant bool precise_formulation   = false; // Enable precise form of pressure anti bounce back BC.
platform_constant bool weighted_distribution = false; // Enable weighted mass excess distribution model.
platform_constant bool weighted_force        = false; // Enable weighted body force model, i.e., Koerner et al., 2005.

enum class Type : std::uint8_t {
  Gas       = 0,
  Interface = 1,
  Fluid     = 2,
  Solid     = 4
};

enum class Flags : std::uint8_t {
  None         = 0,
  ToGas        = 1,
  ToFluid      = 2,
  NewInterface = 4
};

struct NeighbourInfo {
  bool has_fluid_neighbours         = false;
  bool has_gas_neighbours           = false;
  std::uint8_t interface_neighbours = std::uint8_t(0);
};

// Global data structures storing: cell type, cell flags, mass, epsilon, velocity, and mass exchange
struct CELL_TYPE          : public descriptors::TYPED_FIELD_BASE<Type, 1> {};
struct CELL_FLAGS         : public descriptors::TYPED_FIELD_BASE<Flags, 1> {};
struct MASS               : public descriptors::FIELD_BASE<1> {};
struct EPSILON            : public descriptors::FIELD_BASE<1> {};
struct PREVIOUS_VELOCITY  : public descriptors::FIELD_BASE<0, 1, 0> {};
struct TEMP_MASS_EXCHANGE : public descriptors::FIELD_BASE<0, 0, 1> {};
struct HAS_INTERFACE_NBRS : public descriptors::TYPED_FIELD_BASE<bool, 1> {
  template <typename T, typename DESCRIPTOR>
  static constexpr auto getInitialValue() {
    return Vector<value_type<T>, DESCRIPTOR::template size<HAS_INTERFACE_NBRS>()>{true};
  }
};

// Parameters used in post processors
struct DROP_ISOLATED_CELLS       : public descriptors::FIELD_BASE<1> {};
struct TRANSITION                : public descriptors::FIELD_BASE<1> {};
struct LONELY_THRESHOLD          : public descriptors::FIELD_BASE<1> {};
struct HAS_SURFACE_TENSION       : public descriptors::FIELD_BASE<1> {};
struct SURFACE_TENSION_PARAMETER : public descriptors::FIELD_BASE<1> {};
struct FORCE_DENSITY             : public descriptors::FIELD_BASE<0, 1, 0> {};

template <typename T>
struct GradientGroups2D { Vector<T, 2> axes{}; Vector<T, 2> diagonals{}; };

template <typename T>
struct GradientGroups3D { Vector<T, 3> faces{}; Vector<T, 3> edges{}; Vector<T, 3> corners{}; };

template<typename T, typename DESCRIPTOR>
void initialize(SuperLattice<T, DESCRIPTOR>& sLattice);

template <typename CELL>
static bool isCellType(CELL& cell, const FreeSurface::Type& type) any_platform;

template <typename CELL>
static void setCellType(CELL& cell, const FreeSurface::Type& type) any_platform;

template <typename CELL>
static bool hasNeighbour(CELL& cell, const FreeSurface::Type& type) any_platform;

template <typename CELL>
static bool hasCellFlags(CELL& cell, const FreeSurface::Flags& type) any_platform;

template <typename CELL>
static void setCellFlags(CELL& cell, const FreeSurface::Flags& flags) any_platform;

template <typename CELL>
static bool hasNeighbourFlags(CELL& cell, const FreeSurface::Flags& flags) any_platform;

template <typename CELL>
static NeighbourInfo getNeighbourInfo(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static bool isHealthyInterface(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static void computeMassExcessWeights(CELL& cell, const bool& enableAllInterfaces, Vector<V, CELL::descriptor_t::q>& weights) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static V getClampedEpsilon(const CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
requires (CELL::descriptor_t::d == 3)
static V getClampedSmoothEpsilon(const CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
requires (CELL::descriptor_t::d == 2)
static GradientGroups2D<V> EpsilonGradientGroups(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
requires (CELL::descriptor_t::d == 3)
static GradientGroups3D<V> EpsilonGradientGroups(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static Vector<V, CELL::descriptor_t::d> computeInterfaceNormal(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static Vector<V, CELL::descriptor_t::d> ParkerYoungInterfaceNormal(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static Vector<V, CELL::descriptor_t::d> LeastSquaresInterfaceNormal(CELL& cell) any_platform;

template<typename T, int N>
static void plainLUSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) any_platform;

template<typename T, int N>
static void rowPivotingLUSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) any_platform;

template<typename T, int N>
static void completePivotingLUSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) any_platform;

// template<typename T, int N>
// static void eigenSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) any_platform;

template<typename T>
static T plicCubeReduced(const T& volume, const Vector<T, 3>& n) any_platform;

template<typename T>
static T plicCube(const T& volume, const Vector<T, 3>& n) any_platform;

template<typename T>
static T plicCubeInverse(const T& d0, const Vector<T, 3>& n) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static V computeCurvaturePLIC2D(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static V computeCurvaturePLIC3D(CELL& cell) any_platform;

template <typename CELL, typename V = typename CELL::value_t>
static V computeCurvature(CELL& cell) any_platform;

} // namespace FreeSurface

inline any_platform FreeSurface::Flags operator&(FreeSurface::Flags lhs, FreeSurface::Flags rhs) {
  return static_cast<FreeSurface::Flags>(static_cast<std::uint8_t>(lhs) & static_cast<std::uint8_t>(rhs));
}

inline any_platform FreeSurface::Flags operator|(FreeSurface::Flags lhs, FreeSurface::Flags rhs) {
  return static_cast<FreeSurface::Flags>(static_cast<std::uint8_t>(lhs) | static_cast<std::uint8_t>(rhs));
}

} // namespace olb

#include "freeSurfaceHelpers.hh"
