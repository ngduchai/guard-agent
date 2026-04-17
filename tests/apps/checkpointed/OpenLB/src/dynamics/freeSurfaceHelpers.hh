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

#include <atomic>

namespace olb {

namespace FreeSurface {

template<typename T, typename DESCRIPTOR>
void initialize(SuperLattice<T,DESCRIPTOR>& sLattice) {
  sLattice.executePostProcessors(FreeSurface::Stage0());
  sLattice.executePostProcessors(FreeSurface::Stage1());
  sLattice.executePostProcessors(FreeSurface::Stage2());
  sLattice.executePostProcessors(FreeSurface::Stage3());
  sLattice.executePostProcessors(FreeSurface::Stage4());
  sLattice.executePostProcessors(FreeSurface::Stage5());
}

template <typename CELL>
bool any_platform isCellType(CELL& cell, const FreeSurface::Type& type){
  return cell.template getField<FreeSurface::CELL_TYPE>() == type;
}

template <typename CELL>
void any_platform setCellType(CELL& cell, const FreeSurface::Type& type) {
  cell.template setField<FreeSurface::CELL_TYPE>(type);
}

template <typename CELL>
bool any_platform hasNeighbour(CELL& cell, const FreeSurface::Type& type) {
  using DESCRIPTOR = typename CELL::descriptor_t;

  for (int iPop = 1; iPop < DESCRIPTOR::q; ++iPop) {
    auto nbrCell = cell.neighbor(descriptors::c<DESCRIPTOR>(iPop));
    if (isCellType(nbrCell, type)) { return true; }
  }

  return false;
}

template <typename CELL>
bool any_platform hasCellFlags(CELL& cell, const FreeSurface::Flags& flags) {
  return static_cast<bool>(cell.template getField<FreeSurface::CELL_FLAGS>() & flags);
}

template <typename CELL>
void any_platform setCellFlags(CELL& cell, const FreeSurface::Flags& flags) {
  cell.template setField<FreeSurface::CELL_FLAGS>(flags);
}

template <typename CELL>
bool any_platform hasNeighbourFlags(CELL& cell, const FreeSurface::Flags& flags) {
  using DESCRIPTOR = typename CELL::descriptor_t;

  for (int iPop = 1; iPop < DESCRIPTOR::q; ++iPop) {
    auto nbrCell = cell.neighbor(descriptors::c<DESCRIPTOR>(iPop));
    if (hasCellFlags(nbrCell, flags)) { return true; }
  }

  return false;
}

template <typename CELL>
NeighbourInfo any_platform getNeighbourInfo(CELL& cell) {
  NeighbourInfo info{};
  using DESCRIPTOR = typename CELL::descriptor_t;

  for (int iPop = 1; iPop < DESCRIPTOR::q; ++iPop) {
    auto nbrCell = cell.neighbor(descriptors::c<DESCRIPTOR>(iPop));

    if (isCellType(nbrCell, FreeSurface::Type::Gas)) {
      info.has_gas_neighbours = true;
    }
    else if (isCellType(nbrCell, FreeSurface::Type::Fluid)) {
      info.has_fluid_neighbours = true;
    }
    else if (isCellType(nbrCell, FreeSurface::Type::Interface)) {
      ++info.interface_neighbours;
    }
  }

  return info;
}

template <typename CELL, typename V>
bool any_platform isHealthyInterface(CELL& cell) {
  using DESCRIPTOR = typename CELL::descriptor_t;
  bool has_fluid_neighbours = false;
  bool has_gas_neighbours = false;

  if (!isCellType(cell, FreeSurface::Type::Interface)) { return false; }

  for (int iPop = 1; iPop < DESCRIPTOR::q; ++iPop) {
    auto nbrCell = cell.neighbor(descriptors::c<DESCRIPTOR>(iPop));
    if (isCellType(nbrCell, FreeSurface::Type::Gas)) {
      has_gas_neighbours = true;
      if (has_fluid_neighbours) { return true; }
    }
    else if (isCellType(nbrCell, FreeSurface::Type::Fluid)) {
      has_fluid_neighbours = true;
      if (has_gas_neighbours) { return true; }
    }
  }

  return false;
}

template <typename CELL, typename V>
void any_platform computeMassExcessWeights(CELL& cell, const bool& enableAllInterfaces, Vector<V, CELL::descriptor_t::q>& weights) {
  using DESCRIPTOR = typename CELL::descriptor_t;

  // Compute normalized interface normal
  auto normal = computeInterfaceNormal(cell);
  normal = norm_squared(normal) < tolerance<V> ? Vector<V, DESCRIPTOR::d>{} : util::normalize(normal);

  for (int iPop = 1; iPop < DESCRIPTOR::q; ++iPop) {
    auto direction = descriptors::c<DESCRIPTOR>(iPop);
    auto nbrCell = cell.neighbor(direction);
    const bool hasNoFlags = !hasCellFlags(nbrCell, FreeSurface::Flags::ToGas | FreeSurface::Flags::ToFluid);

    Vector<V, DESCRIPTOR::d> ei{};
    if constexpr (DESCRIPTOR::d == 3) {
      ei = {V(direction[0]), V(direction[1]), V(direction[2])};
    }
    else { ei = {V(direction[0]), V(direction[1])}; }

    if (isCellType(nbrCell, FreeSurface::Type::Interface) && hasNoFlags) {
      const V nDotDirection = util::dotProduct(normal, ei);

      if (hasCellFlags(cell, FreeSurface::Flags::ToFluid)) {
        // This cell was converted from interface to fluid, so the normal vector is used as is
        weights[iPop] = nDotDirection > V(0) ? nDotDirection : V(0);
      }
      else if (hasCellFlags(cell, FreeSurface::Flags::ToGas)) {
        // This cell was converted from interface to gas, so the normal vector is inverted
        weights[iPop] = nDotDirection < V(0) ? -nDotDirection : V(0);
      }
    }
    else if (hasCellFlags(nbrCell, FreeSurface::Flags::NewInterface) && enableAllInterfaces) {
      const V nDotDirection = util::dotProduct(normal, ei);

      if (hasCellFlags(cell, FreeSurface::Flags::ToFluid)) {
        // This cell was converted from interface to fluid, so the normal vector is used as is
        weights[iPop] = nDotDirection > V(0) ? nDotDirection : V(0);
      }
      else if (hasCellFlags(cell, FreeSurface::Flags::ToGas)) {
        // This cell was converted from interface to gas, so the normal vector is inverted
        weights[iPop] = nDotDirection < V(0) ? -nDotDirection : V(0);
      }
    }
    else {
      // If the neighbour is not an interface cell, the weight is set to zero
      weights[iPop] = V(0);
    }
  }
}

template <typename CELL, typename V>
V any_platform getClampedEpsilon(const CELL& cell) {
  V epsilon = cell.template getField<FreeSurface::EPSILON>();
  return util::max(V(0), util::min(V(1), epsilon));
}

template <typename CELL, typename V>
requires (CELL::descriptor_t::d == 3)
V any_platform getClampedSmoothEpsilon(const CELL& cell) {
  // Williams et al. K8 kernel, i.e., explicitly avoiding expensive std::pow method.
  auto kernel = [](V inv_r2, const auto& direction) -> V {
    const auto norm_2 = norm_squared(direction);
    const V tmp = V{1} - V(norm_2) * inv_r2;
    if (tmp > V{0}) { return tmp * tmp * tmp * tmp; }
    return V{0};
  };

  const V radius = V{2};
  const V inv_r2 = V{1} / (radius * radius);

  V numer = V{0};
  V denom = V{0};

  for (int iPop = 1; iPop < descriptors::q<descriptors::D3Q27<>>(); ++iPop) {
    const auto direction = descriptors::c<descriptors::D3Q27<>>(iPop);
    const V weight = kernel(inv_r2, direction);
    if (weight > V{0}) {
      const auto nbrCell = cell.neighbor(direction);
      numer += weight * nbrCell.template getField<FreeSurface::EPSILON>();
      denom += weight;
    }
  }

  return util::max(V(0), util::min(V(1), numer / denom));
}

template <typename CELL, typename V>
requires (CELL::descriptor_t::d == 2)
GradientGroups2D<V> any_platform EpsilonGradientGroups(CELL& cell) {
  // Perform optimized arithmetics for D2Q9, i.e., used to compute interface normal.
  GradientGroups2D<V> tmp;

  auto eps_minusY       = getClampedEpsilon(cell.neighbor({0, -1}));
  auto eps_plusY        = getClampedEpsilon(cell.neighbor({0, 1}));
  auto eps_minusX       = getClampedEpsilon(cell.neighbor({-1, 0}));
  auto eps_plusX        = getClampedEpsilon(cell.neighbor({1, 0}));
  auto eps_minusYminusX = getClampedEpsilon(cell.neighbor({-1, -1}));
  auto eps_minusYplusX  = getClampedEpsilon(cell.neighbor({1, -1}));
  auto eps_plusYminusX  = getClampedEpsilon(cell.neighbor({-1, 1}));
  auto eps_plusYplusX   = getClampedEpsilon(cell.neighbor({1, 1}));

  // Rearrange arithmetic operations to minimize the number of cancellation events, i.e., positive and negative terms.
  tmp.axes[0]      = eps_minusX - eps_plusX;
  tmp.diagonals[0] = (eps_minusYminusX + eps_plusYminusX) - (eps_plusYplusX + eps_minusYplusX);

  tmp.axes[1]      = eps_minusY - eps_plusY;
  tmp.diagonals[1] = (eps_minusYminusX + eps_minusYplusX) - (eps_plusYplusX + eps_plusYminusX);

  return tmp;
}

template <typename CELL, typename V>
requires (CELL::descriptor_t::d == 3)
GradientGroups3D<V> any_platform EpsilonGradientGroups(CELL& cell) {
  // Perform optimized arithmetics for D3Q27, i.e., used to compute interface normal.
  GradientGroups3D<V> tmp;

  auto eps_minusY             = getClampedEpsilon(cell.neighbor({0, -1, 0}));
  auto eps_plusY              = getClampedEpsilon(cell.neighbor({0, 1, 0}));
  auto eps_minusX             = getClampedEpsilon(cell.neighbor({-1, 0, 0}));
  auto eps_plusX              = getClampedEpsilon(cell.neighbor({1, 0, 0}));
  auto eps_minusYminusX       = getClampedEpsilon(cell.neighbor({-1, -1, 0}));
  auto eps_minusYplusX        = getClampedEpsilon(cell.neighbor({1, -1, 0}));
  auto eps_plusYminusX        = getClampedEpsilon(cell.neighbor({-1, 1, 0}));
  auto eps_plusYplusX         = getClampedEpsilon(cell.neighbor({1, 1, 0}));
  auto eps_minusZ             = getClampedEpsilon(cell.neighbor({0, 0, -1}));
  auto eps_plusZ              = getClampedEpsilon(cell.neighbor({0, 0, 1}));
  auto eps_minusZminusY       = getClampedEpsilon(cell.neighbor({0, -1, -1}));
  auto eps_minusZplusY        = getClampedEpsilon(cell.neighbor({0, 1, -1}));
  auto eps_minusZminusX       = getClampedEpsilon(cell.neighbor({-1, 0, -1}));
  auto eps_minusZplusX        = getClampedEpsilon(cell.neighbor({1, 0, -1}));
  auto eps_plusZminusY        = getClampedEpsilon(cell.neighbor({0, -1, 1}));
  auto eps_plusZplusY         = getClampedEpsilon(cell.neighbor({0, 1, 1}));
  auto eps_plusZminusX        = getClampedEpsilon(cell.neighbor({-1, 0, 1}));
  auto eps_plusZplusX         = getClampedEpsilon(cell.neighbor({1, 0, 1}));
  auto eps_minusZminusYminusX = getClampedEpsilon(cell.neighbor({-1, -1, -1}));
  auto eps_minusZplusYminusX  = getClampedEpsilon(cell.neighbor({-1, 1, -1}));
  auto eps_minusZminusYplusX  = getClampedEpsilon(cell.neighbor({1, -1, -1}));
  auto eps_minusZplusYplusX   = getClampedEpsilon(cell.neighbor({1, 1, -1}));
  auto eps_plusZminusYminusX  = getClampedEpsilon(cell.neighbor({-1, -1, 1}));
  auto eps_plusZplusYminusX   = getClampedEpsilon(cell.neighbor({-1, 1, 1}));
  auto eps_plusZminusYplusX   = getClampedEpsilon(cell.neighbor({1, -1, 1}));
  auto eps_plusZplusYplusX    = getClampedEpsilon(cell.neighbor({1, 1, 1}));

  // Rearrange arithmetic operations to minimize the number of cancellation events, i.e., positive and negative terms.
  tmp.faces[0]   = eps_minusX - eps_plusX;
  tmp.edges[0]   = (eps_minusYminusX + eps_minusZminusX + eps_plusYminusX + eps_plusZminusX) - (eps_plusYplusX + eps_plusZplusX + eps_minusYplusX + eps_minusZplusX);
  tmp.corners[0] = (eps_minusZminusYminusX + eps_plusZminusYminusX + eps_minusZplusYminusX + eps_plusZplusYminusX) - (eps_plusZplusYplusX + eps_minusZplusYplusX + eps_plusZminusYplusX + eps_minusZminusYplusX);

  tmp.faces[1]   = eps_minusY - eps_plusY;
  tmp.edges[1]   = (eps_minusYminusX + eps_minusZminusY + eps_minusYplusX + eps_plusZminusY) - (eps_plusYplusX + eps_plusZplusY + eps_plusYminusX + eps_minusZplusY);
  tmp.corners[1] = (eps_minusZminusYminusX + eps_plusZminusYminusX + eps_plusZminusYplusX + eps_minusZminusYplusX) - (eps_plusZplusYplusX + eps_minusZplusYplusX + eps_minusZplusYminusX + eps_plusZplusYminusX);

  tmp.faces[2]   = eps_minusZ - eps_plusZ;
  tmp.edges[2]   = (eps_minusZminusX + eps_minusZminusY + eps_minusZplusX + eps_minusZplusY) - (eps_plusZplusX + eps_plusZplusY + eps_plusZminusX + eps_plusZminusY);
  tmp.corners[2] = (eps_minusZminusYminusX + eps_minusZplusYplusX + eps_minusZplusYminusX + eps_minusZminusYplusX) - (eps_plusZplusYplusX + eps_plusZminusYminusX + eps_plusZminusYplusX + eps_plusZplusYminusX);

  return tmp;
}

template <typename CELL, typename V>
Vector<V, CELL::descriptor_t::d> any_platform computeInterfaceNormal(CELL& cell) {
  if constexpr (method == NormalMethod::ParkerYoung) {
    return ParkerYoungInterfaceNormal(cell);
  }
  else if constexpr (method == NormalMethod::LeastSquares) {
    return LeastSquaresInterfaceNormal(cell);
  }
  else {
    static_assert(method == NormalMethod::ParkerYoung || method == NormalMethod::LeastSquares,
      "Unknown interface normal method, only ParkerYoung and LeastSquares methods are allowed.");
  }
}

template <typename CELL, typename V>
Vector<V, CELL::descriptor_t::d> any_platform ParkerYoungInterfaceNormal(CELL& cell) {

  // Compute interface normal using Parker-Young approximation
  Vector<V, CELL::descriptor_t::d> normal{};
  // Compute interface normal (always) for D3Q27 descriptor, i.e., irrespective of cell descriptor.
  if constexpr (CELL::descriptor_t::d == 3) {
    // Compute gradient of EPSILON using optimized arithmetics.
    auto groups = EpsilonGradientGroups(cell);

    // Compute interface normal in each direction.
    normal[0]  = V(4) * groups.faces[0];
    normal[0] += V(2) * groups.edges[0];
    normal[0] += V(1) * groups.corners[0];

    normal[1]  = V(4) * groups.faces[1];
    normal[1] += V(2) * groups.edges[1];
    normal[1] += V(1) * groups.corners[1];

    normal[2]  = V(4) * groups.faces[2];
    normal[2] += V(2) * groups.edges[2];
    normal[2] += V(1) * groups.corners[2];

    return normal;
  }
  // Compute interface normal (always) for D2Q9 descriptor, i.e., irrespective of cell descriptor.
  else if constexpr (CELL::descriptor_t::d == 2) {
    // Compute gradient of EPSILON using optimized arithmetics.
    auto groups = EpsilonGradientGroups(cell);

    // Compute interface normal in each direction.
    normal[0]  = V(4) * groups.axes[0];
    normal[0] += V(2) * groups.diagonals[0];

    normal[1]  = V(4) * groups.axes[1];
    normal[1] += V(2) * groups.diagonals[1];

    return normal;
  }
  else {
    static_assert(CELL::descriptor_t::d == 2 || CELL::descriptor_t::d == 3,
      "Parker-Young interface normal is only implemented for 2D and 3D.");
    return normal;
  }
}

template <typename CELL, typename V>
Vector<V, CELL::descriptor_t::d> any_platform LeastSquaresInterfaceNormal(CELL& cell) {

  // Compute interface normal using weighted least-squares gradient
  Vector<V, CELL::descriptor_t::d> normal{};

  // Compute interface normal (always) for D3Q27 descriptor, i.e., irrespective of cell descriptor.
  if constexpr (CELL::descriptor_t::d == 3) {

    // Construct the system of equations
    std::array<V, 9> A{};
    std::array<V, 3> x{};
    std::array<V, 3> rhs{};

    // Always use D3Q27 descriptor to build the linear system, i.e., corners are essential for geometry operations.
    constexpr std::uint8_t exponent = std::uint8_t(1);
    const V weight_1 = V(1);
    const V weight_2 = (exponent == std::uint8_t(1)) ? (V(1) / util::sqrt(V(2))) : V(0.5);
    const V weight_3 = (exponent == std::uint8_t(1)) ? (V(1) / util::sqrt(V(3))) : V(1) / V(3);

    // Compute gradient of EPSILON using optimized arithmetics.
    auto groups = EpsilonGradientGroups(cell);

    // Prepare the linear system matrix A, exploiting D3Q27 stencil symmetry.
    A[0] = V(2) * weight_1 + V(8) * weight_2 + V(8) * weight_3;
    A[1] = V(0);
    A[2] = V(0);
    A[4] = V(2) * weight_1 + V(8) * weight_2 + V(8) * weight_3;
    A[5] = V(0);
    A[8] = V(2) * weight_1 + V(8) * weight_2 + V(8) * weight_3;

    // Prepare the linear system matrix rhs, exploiting D3Q27 stencil symmetry.
    rhs[0]  = (weight_1 * groups.faces[0]) + (weight_2 * groups.edges[0]) + (weight_3 * groups.corners[0]);
    rhs[1]  = (weight_1 * groups.faces[1]) + (weight_2 * groups.edges[1]) + (weight_3 * groups.corners[1]);
    rhs[2]  = (weight_1 * groups.faces[2]) + (weight_2 * groups.edges[2]) + (weight_3 * groups.corners[2]);

    // Enforce symmetry to eliminate round-off errors.
    for (std::uint8_t i = 1; i < 3; ++i) {
      for (std::uint8_t j = 0; j < i; ++j) { A[i * 3 + j] = A[j * 3 + i]; }
    }

    // Solve the linear system A * n = rhs
    if constexpr (solver == SolverType::plainLU) {
      plainLUSolver<V, 3>(A, x, rhs, 3);
    }
    else if constexpr (solver == SolverType::rowPivotingLU) {
      rowPivotingLUSolver<V, 3>(A, x, rhs, 3);
    }
    else if constexpr (solver == SolverType::completePivotingLU) {
      completePivotingLUSolver<V, 3>(A, x, rhs, 3);
    }
    /*else if constexpr (solver == SolverType::eigen) {
      eigenSolver<V, 3>(A, x, rhs, 3);
    }*/
    else {
      // Fall back to default solver
      plainLUSolver<V, 3>(A, x, rhs, 3);
    }

    normal[0] = x[0]; normal[1] = x[1]; normal[2] = x[2];
    return normal;
  }
  // Compute interface normal (always) for D2Q9 descriptor, i.e., irrespective of cell descriptor.
  else if constexpr (CELL::descriptor_t::d == 2) {

    // Construct the system of equations
    std::array<V, 4> A{};
    std::array<V, 2> x{};
    std::array<V, 2> rhs{};

    // Always use D2Q9 descriptor to build the linear system, i.e., diagonals are essential for geometry operations.
    constexpr std::uint8_t exponent = std::uint8_t(1);
    const V weight_1 = V(1);
    const V weight_2 = (exponent == std::uint8_t(1)) ? (V(1) / util::sqrt(V(2))) : V(0.5);

    // Compute gradient of EPSILON using optimized arithmetics.
    auto groups = EpsilonGradientGroups(cell);

    // Prepare the linear system matrix A, exploiting D2Q9 stencil symmetry.
    A[0] = V(2) * weight_1 + V(4) * weight_2;
    A[1] = V(0);
    A[3] = V(2) * weight_1 + V(4) * weight_2;

    // Prepare the linear system matrix rhs, exploiting D2Q9 stencil symmetry.
    rhs[0]  = (weight_1 * groups.axes[0]) + (weight_2 * groups.diagonals[0]);
    rhs[1]  = (weight_1 * groups.axes[1]) + (weight_2 * groups.diagonals[1]);

    // Enforce symmetry to eliminate round-off errors.
    A[2] = A[1];

    // Solve the linear system A * n = rhs
    if constexpr (solver == SolverType::plainLU) {
      plainLUSolver<V, 2>(A, x, rhs, 2);
    }
    else if constexpr (solver == SolverType::rowPivotingLU) {
      rowPivotingLUSolver<V, 2>(A, x, rhs, 2);
    }
    else if constexpr (solver == SolverType::completePivotingLU) {
      completePivotingLUSolver<V, 2>(A, x, rhs, 2);
    }
    /*else if constexpr (solver == SolverType::eigen) {
      eigenSolver<V, 2>(A, x, rhs, 2);
    }*/
    else {
      // Fall back to default solver
      plainLUSolver<V, 2>(A, x, rhs, 2);
    }

    normal[0] = x[0]; normal[1] = x[1];
    return normal;
  }
  else {
    static_assert(CELL::descriptor_t::d == 2 || CELL::descriptor_t::d == 3,
      "Least-Squares interface normal is only implemented for 2D and 3D.");
    return normal;
  }
}

template<typename T, int N>
void any_platform plainLUSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) {
  // Add Tikhonov Regularization to the diagonal elements of M
  for (int i = 0; i < Nsol; ++i) { M[i * N + i] += T(0); }

  // (1) Simple LU decomposition method.
  for (int i = 0; i < Nsol; ++i) {
    // Perform standard elimination procedure.
    for (int j = i + 1; j < Nsol; ++j) {
      M[j * N + i] /= M[i * N + i];
      for (int k = i + 1; k < Nsol; ++k) { M[j * N + k] -= M[j * N + i] * M[i * N + k]; }
    }
  }

  // (2) Forward substitution step, i.e., solve L * x = b in place.
  for (int i = 0; i < Nsol; ++i) {
    x[i] = rhs[i];
    for (int j = 0; j < i; ++j) { x[i] -= M[i * N + j] * x[j]; }
  }

  // (3) Backward substitution step, i.e., solve U * x = b in place.
  for (int i = Nsol - 1; i >= 0; --i) {
    for (int j = i + 1; j < Nsol; ++j) { x[i] -= M[i * N + j] * x[j]; }
    x[i] /= M[i * N + i];
  }
}

template<typename T, int N>
void any_platform rowPivotingLUSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) {
  // Add Tikhonov Regularization to the diagonal elements of M
  for (int i = 0; i < Nsol; ++i) { M[i * N + i] += T(0); }

  // Permutation vector to record row swaps.
  std::array<int, N> row_perm{};
  for (int i = 0; i < N; ++i) { row_perm[i] = i; }

  // LU decomposition method with row pivoting.
  for (int i = 0; i < Nsol; ++i) {
    int pivot_row = i;
    T max_value = std::abs(M[i * N + i]);

    for (int j = i + 1; j < Nsol; ++j) {
      T value = std::abs(M[j * N + i]);
      if (value > max_value) { max_value = value; pivot_row = j; }
    }

    // Apply row swap operation.
    if (pivot_row != i) {
      for (int k = 0; k < Nsol; ++k) { std::swap(M[i * N + k], M[pivot_row * N + k]); }
      std::swap(row_perm[i], row_perm[pivot_row]);
      std::swap(rhs[i], rhs[pivot_row]);
    }

    // Perform standard elimination procedure.
    for (int j = i + 1; j < Nsol; ++j) {
      M[j * N + i] /= M[i * N + i];
      for (int k = i + 1; k < Nsol; ++k) { M[j * N + k] -= M[j * N + i] * M[i * N + k]; }
    }
  }

  // (1) Copy the permutated right-hand side array into x array.
  for (int i = 0; i < Nsol; ++i) { x[i] = rhs[i]; }

  // (2) Forward substitution step, i.e., solve L * x = b in place.
  for (int i = 0; i < Nsol; ++i) {
    for (int j = 0; j < i; ++j) { x[i] -= M[i * N + j] * x[j]; }
  }

  // (3) Backward substitution step, i.e., solve U * x = b in place.
  for (int i = Nsol - 1; i >= 0; --i) {
    for (int j = i + 1; j < Nsol; ++j) { x[i] -= M[i * N + j] * x[j]; }
    x[i] /= M[i * N + i];
  }
}

template<typename T, int N>
void any_platform completePivotingLUSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) {
  // Add Tikhonov Regularization to the diagonal elements of M
  for (int i = 0; i < Nsol; ++i) { M[i * N + i] += T(0); }

  // Permutation vectors to record row and columns swaps.
  std::array<int, N> row_perm{}, col_perm{};
  for (int i = 0; i < N; ++i) { row_perm[i] = i; col_perm[i] = i; }

  // Track rank-revealing behavior
  int nonzero_pivots = Nsol;
  T global_pivot = T(0);

  // LU decomposition method with complete pivoting.
  for (int i = 0; i < Nsol; ++i) {
    int pivot_row = i, pivot_col = i;
    T max_value = std::abs(M[i * N + i]);

    for (int r = i; r < Nsol; ++r) {
      for (int c = i; c < Nsol; ++c) {
        T value = std::abs(M[r * N + c]);
        if (value > max_value) { max_value = value; pivot_row = r; pivot_col = c; }
      }
    }

    // Break if the entire corner elements are zero, respecting a pre-defined tolerance.
    if (max_value == T(0)) { nonzero_pivots = i; break; }

    // Update the global maximum pivot.
    if (max_value > global_pivot) { global_pivot = max_value; }

    // Apply row swap operation.
    if (pivot_row != i) {
      for (int k = 0; k < Nsol; ++k) { std::swap(M[i * N + k], M[pivot_row * N + k]); }
      std::swap(row_perm[i], row_perm[pivot_row]);
      std::swap(rhs[i], rhs[pivot_row]);
    }

    // Apply column swap operation.
    if (pivot_col != i) {
      for (int k = 0; k < Nsol; ++k) { std::swap(M[k * N + i], M[k * N + pivot_col]); }
      std::swap(col_perm[i], col_perm[pivot_col]);
    }

    // Perform standard elimination procedure.
    for (int j = i + 1; j < Nsol; ++j) {
      M[j * N + i] /= M[i * N + i];
      for (int k = i + 1; k < Nsol; ++k) { M[j * N + k] -= M[j * N + i] * M[i * N + k]; }
    }
  }

  // Compute the number of reliably non-zero pivots, i.e., rank.
  int rank = 0;
  for (int i = 0; i < nonzero_pivots; ++i) {
    if (std::abs(M[i * N + i]) > tolerance<T> * global_pivot) { ++rank; }
  }

  // (1) Copy the permutated right-hand side array into x array.
  for (int i = 0; i < Nsol; ++i) { x[i] = rhs[i]; }

  if (rank == 0) {
    // No reliable rank found, set the solution array to zero.
    for (int i = 0; i < Nsol; ++i) { x[i] = T(0); }
  }
  else {
    // (2) Forward substitution step, i.e., solve L * x = b in place.
    for (int i = 0; i < Nsol; ++i) {
      for (int j = 0; j < i; ++j) { x[i] -= M[i * N + j] * x[j]; }
    }

    // (3) Backward substitution step, i.e., solve U * x = b in place.
    // Note: only over the first "rank" pivots.
    for (int i = rank; i < Nsol; ++i) { x[i] = T(0); }
    for (int i = rank - 1; i >= 0; --i) {
      for (int j = i + 1; j < rank; ++j) { x[i] -= M[i * N + j] * x[j]; }
      x[i] /= M[i * N + i];
    }
  }

  // (4) Reconstruct original x by inverting the permutation, i.e.,
  // for each index i, the original index is given by col_perm[i].
  std::array<T, N> tmp = x;
  for (int i = 0; i < Nsol; ++i) { x[col_perm[i]] = tmp[i]; }
}

/*template<typename T, int N>
void eigenSolver(std::array<T, N * N>& M, std::array<T, N>& x, std::array<T, N>& rhs, const int Nsol) {
  // Using Eigen fixed-size matrices to solve the linear system for Nsol.
  Eigen::Matrix<T, N, N, Eigen::RowMajor> A = Eigen::Matrix<T, N, N, Eigen::RowMajor>::Zero();
  Eigen::Matrix<T, N, 1> B = Eigen::Matrix<T, N, 1>::Zero();
  const int n = std::max(0, std::min(Nsol, N));

  // Copy top-left (n×n) from M and first n of rhs.
  for (int i = 0; i < n; ++i) {
    B(i) = rhs[i];
    for (int j = 0; j < n; ++j) { A(i, j) = M[i * N + j]; }
  }

  // Pad the unused block of A with identity and the tail of B (rhs) with zeros.
  if (n < N) {
    A.block(n, n, N - n, N - n).setIdentity();
    B.tail(N - n).setZero();
  }

  A = T(0.5) * (A + A.transpose());
  auto solver = Eigen::FullPivLU<Eigen::Matrix<T, N, N, Eigen::RowMajor>>(A);
  solver.setThreshold(tolerance<T>);
  solver.compute(A);
  Eigen::Matrix<T, N, 1> Y = solver.solve(B);
  for (int i = 0; i < N; ++i) x[i] = Y(i);
}*/

// Offset helper: optimized PLIC algorithm taken from Moritz Lehmann FluidX3D
template<typename T>
T any_platform plicCubeReduced(const T& volume, const Vector<T, 3>& n) {
  const T n1 = n[0], n2 = n[1], n3 = n[2];
  const T n12 = n1 + n2, n3V = n3 * volume;

  // (I) Case 5
  if (n12 <= T(2) * n3V) { return n3V + T(0.5) * n12; }

  // (II) After case 5, check n2 > 0 is true
  const T sqn1 = util::sqr(n1), n26 = T(6) * n2, v1 = sqn1 / n26;

  // (III) Case 2
  if (v1 <= n3V && n3V < v1 + T(0.5) * (n2 - n1)) {
    return T(0.5) * (n1 + util::sqrt(sqn1 + T(8) * n2 * (n3V - v1)));
  }

  // (IV) Case 1
  const T V6 = n1 * n26 * n3V;
  if (n3V < v1) { return std::cbrt(V6); }

  // (V) After case 2, check n1 > 0 is true
  const T v3 = n3 < n12 ? (util::sqr(n3) * (T(3) * n12 - n3) + sqn1 * (n1 - T(3) * n3) + util::sqr(n2) * (n2 - T(3) * n3)) / (n1 * n26) : T(0.5) * n12;
  const T sqn12 = sqn1 + util::sqr(n2), V6cbn12 = V6 - util::cube(n1) - util::cube(n2);
  const bool case34 = n3V < v3; // true: case (3), false: case (4)
  const T a = case34 ? V6cbn12 : T(0.5) * (V6cbn12 - util::cube(n3));
  const T b = case34 ? sqn12 : T(0.5) * (sqn12 + util::sqr(n3));
  const T c = case34 ? n12 : T(0.5);
  const T t = util::sqrt(util::sqr(c) - b);
  static constexpr T oneThird = T(1) / T(3);

  return c - T(2) * t * util::sin(oneThird * util::asin((util::cube(c) - T(0.5) * a - T(1.5) * b * c) / util::cube(t)));
}

// Offset computer: optimized PLIC algorithm taken from Moritz Lehmann FluidX3D
template<typename T>
T any_platform plicCube(const T& volume, const Vector<T, 3>& n) {
  // Unit cube-plane intersection: using volume and normal vector to compute the offset
  const T ax = util::abs(n[0]), ay = util::abs(n[1]), az = util::abs(n[2]);

  // Eliminate symmetry cases, and normalize n using L1 norm
  const T V = T(0.5) - util::abs(volume - T(0.5)), l = ax + ay + az;
  const T n1 = util::min(util::min(ax, ay), az) / l;
  const T n3 = util::max(util::max(ax, ay), az) / l;
  const T n2 = std::fdim(T(1), n1 + n3); // ensure n2 >= 0
  const T d = plicCubeReduced<T>(V, {n1, n2, n3});

  return l * std::copysign(T(0.5) - d, volume - T(0.5));
}

// Volume computer: optimized inverse PLIC algorithm taken from Moritz Lehmann FluidX3D
template<typename T>
T any_platform plicCubeInverse(const T& d0, const Vector<T, 3>& n) {
  // Eliminate majority of cases due to symmetry
  const T n1 = util::min(util::min(util::abs(n[0]), util::abs(n[1])), util::abs(n[2]));
  const T n3 = util::max(util::max(util::abs(n[0]), util::abs(n[1])), util::abs(n[2]));
  const T n2 = util::abs(n[0]) - n1 + util::abs(n[1]) + util::abs(n[2]) - n3;

  // Compute PLIC using reduced symmetry, shifting origin from (0.0, 0.0, 0.0) to (0.5, 0.5, 0.5)
  const T d = T(0.5) * (n1 + n2 + n3) - util::abs(d0);

  T V = T(0);
  if (util::min(n1 + n2, n3) <= d && d <= n3) {
    // (I) Case 5
    V = (d - T(0.5) * (n1 + n2)) / n3;
  }
  else if (d < n1) {
    // (II) Case 1
    V = util::cube(d) / (T(6) * n1 * n2 * n3);
  }
  else if (d <= n2) {
    // (III) Case 2
    V = (T(3) * d * (d - n1) + util::sqr(n1)) / (T(6) * n2 * n3);
  }
  else {
    // (IV) Case 3 or 4
    V = (util::cube(d) - util::cube(d - n1) - util::cube(d - n2) - util::cube(std::fdim(d, n3))) / (T(6) * n1 * n2 * n3);
  }

  return std::copysign(T(0.5) - V, d0) + T(0.5);
}

// Compute 2D interface curvature using Moritz Lehmann's FluidX3D algorithm
template <typename CELL, typename V>
V any_platform computeCurvaturePLIC2D(CELL& cell) {
  using DESCRIPTOR = typename CELL::descriptor_t;

  // Setup a new coordinate system where bz is perpendicular to the surface, while bx and by are
  // tangent to the surface.
  const auto normal = computeInterfaceNormal(cell);
  Vector<V, 3> by = {normal[0], normal[1], V(0)};
  if (norm_squared(by) < tolerance<V>) { return V(0); }
  by = util::normalize(by);

  const Vector<V, 3> rn{V(0), V(0), V(1)};
  const Vector<V, 3> bx = crossProduct(by, rn);

  // Number of healthy interface neighbours
  std::uint8_t nbrInterfaces = std::uint8_t(0);

  // Compute z-offset of center point using PLIC cube
  const V centerOffset = plicCube<V>(getClampedEpsilon(cell), by);

  // Number of neighbouring interface points, i.e., less than or equal to 8 (neighbours) - 1 (liquid) - 1 (gas).
  // Note: increased to 8 to support rare cases where an interface cell only has interface neighbours.
  std::array<Vector<V, DESCRIPTOR::d>, 8> points{};

  // Always use D2Q9 descriptor to build the linear system, i.e., diagonals are essential for geometry operations.
  for (int iPop = 1; iPop < descriptors::q<descriptors::D2Q9<>>(); ++iPop) {
    const auto direction = descriptors::c<descriptors::D2Q9<>>(iPop);
    auto nbrCell = cell.neighbor(direction);

    // Check if the neighbour is an interface cell or has a gas neighbour
    if (!isCellType(nbrCell, FreeSurface::Type::Interface) || !hasNeighbour(nbrCell, FreeSurface::Type::Gas)) {
      continue;
    }

    // Here it is assumed that neighbor normal vector is the same as center normal vector
    const Vector<V, 3> ei = {V(direction[0]), V(direction[1]), V(0)};
    const V offset = plicCube<V>(getClampedEpsilon(nbrCell), by) - centerOffset;

    // Transform coordinate system into (x, f(x)) and apply PLIC offset
    points[nbrInterfaces++] = {util::dotProduct(ei, bx), util::dotProduct(ei, by) + offset};
  }

  // Prepare the linear equation system, to be initialized with zeros
  std::array<V, 4> M{};
  std::array<V, 2> solution{};
  std::array<V, 2> b{};

  for (std::uint8_t i = 0; i < nbrInterfaces; ++i) {
    const V x = points[i][0];
    const V y = points[i][1];
    const V x2 = util::sqr(x);
    const V x3 = util::sqr(x) * x;

    M[0] += x2 * x2;
    M[1] += x3;
    M[3] += x2;

    b[0] += x2 * y;
    b[1] += x * y;
  }

  // Enforce symmetry to eliminate round-off errors.
  M[2] = M[1];

  // Solve the linear system of equations, compile-time selection.
  if constexpr (solver == SolverType::plainLU) {
    plainLUSolver<V, 2>(M, solution, b, util::min(2, nbrInterfaces));
  }
  else if constexpr (solver == SolverType::rowPivotingLU) {
    rowPivotingLUSolver<V, 2>(M, solution, b, util::min(2, nbrInterfaces));
  }
  else if constexpr (solver == SolverType::completePivotingLU) {
    completePivotingLUSolver<V, 2>(M, solution, b, util::min(2, nbrInterfaces));
  }
  /*else if constexpr (solver == SolverType::eigen) {
    eigenSolver<V, 2>(M, solution, b, util::min(2, nbrInterfaces));
  }*/
  else {
    // Fall back to default solver
    plainLUSolver<V, 2>(M, solution, b, util::min(2, nbrInterfaces));
  }

  // Compute curvature from the linear system solution, i.e., fitting f(x) = A * x^2 + H * x.
  const V A = solution[0], H = solution[1];
  const V curvature = V(2) * A * util::cube(V(1) / util::sqrt(H * H + V(1)));
  return util::max(V(-1), util::min(V(1), curvature));
}

// Compute 3D interface curvature using Moritz Lehmann's FluidX3D algorithm
template <typename CELL, typename V>
V any_platform computeCurvaturePLIC3D(CELL& cell) {
  using DESCRIPTOR = typename CELL::descriptor_t;

  // Setup a new coordinate system where bz is perpendicular to the surface, while bx and by are
  // tangent to the surface.
  auto bz = computeInterfaceNormal(cell);
  if (norm_squared(bz) < tolerance<V>) { return V(0); }
  bz = util::normalize(bz);

  // A random normalized vector that is just by random chance not collinear with bz
  // const Vector<V, DESCRIPTOR::d> rn{V(0.5402151198529208), V(0.2765640977634561), V(0.7947829415070379)};

  // Normalization is necessary here because bz and rn are not perpendicular
  // const Vector<V, DESCRIPTOR::d> by = util::normalize(crossProduct(bz, rn));
  // const Vector<V, DESCRIPTOR::d> bx = crossProduct(by, bz);

  // Build orthonormal basis (bx, by) from bz without a global reference vector, i.e., Duff et al., (2017).
  Vector<V, DESCRIPTOR::d> bx, by;
  {
    const V sign   = std::copysign(V(1), bz[2]);
    const V coef_a = V(-1) / (sign + bz[2]);
    const V coef_b = bz[0] * bz[1] * coef_a;
    bx = Vector<V, DESCRIPTOR::d>{ V(1) + sign * bz[0] * bz[0] * coef_a, sign * coef_b, -sign * bz[0] };
    by = Vector<V, DESCRIPTOR::d>{ coef_b, sign + bz[1] * bz[1] * coef_a, -bz[1] };
    bx = util::normalize(bx);
    by = util::normalize(crossProduct(bz, bx));
  }

  // Number of healthy interface neighbours
  std::uint8_t nbrInterfaces = std::uint8_t(0);

  // Compute z-offset of center point using PLIC cube
  const V centerOffset = plicCube<V>(getClampedEpsilon(cell), bz);

  // Number of neighbouring interface points, i.e., less than or equal to 26 (neighbours) - 1 (liquid) - 1 (gas).
  // Note: increased to 26 to support rare cases where an interface cell only has interface neighbours.
  std::array<Vector<V, DESCRIPTOR::d>, 26> points{};

  // Always use D3Q27 descriptor to build the linear system, i.e., corners are essential for geometry operations.
  for (int iPop = 1; iPop < descriptors::q<descriptors::D3Q27<>>(); ++iPop) {
    const auto direction = descriptors::c<descriptors::D3Q27<>>(iPop);
    auto nbrCell = cell.neighbor(direction);

    // Check if the neighbour is an interface cell or has a gas neighbour
    if (!isCellType(nbrCell, FreeSurface::Type::Interface) || !hasNeighbour(nbrCell, FreeSurface::Type::Gas)) {
      continue;
    }

    // Here it is assumed that neighbor normal vector is the same as center normal vector
    const Vector<V, DESCRIPTOR::d> ei = {V(direction[0]), V(direction[1]), V(direction[2])};
    const V offset = plicCube<V>(getClampedEpsilon(nbrCell), bz) - centerOffset;

    // Transform coordinate system into (x, y, f(x,y)) and apply PLIC offset
    points[nbrInterfaces++] = {util::dotProduct(ei, bx), util::dotProduct(ei, by), util::dotProduct(ei, bz) + offset};
  }

  // Prepare the linear equation system, to be initialized with zeros
  std::array<V, 25> M{};
  std::array<V, 5> solution{};
  std::array<V, 5> b{};

  for (std::uint8_t i = 0; i < nbrInterfaces; ++i) {
    const V x = points[i][0];
    const V y = points[i][1];
    const V z = points[i][2];
    const V x2 = util::sqr(x);
    const V y2 = util::sqr(y);
    const V x3 = x2 * x;
    const V y3 = y2 * y;

    M[0] += x2 * x2;
    M[1] += x2 * y2;
    M[2] += x3 * y;
    M[3] += x3;
    M[4] += x2 * y;
    M[6] += y2 * y2;
    M[7] += x * y3;
    M[8] += x * y2;
    M[9] += y3;
    M[12] += x2 * y2;
    M[13] += x2 * y;
    M[14] += x * y2;
    M[18] += x2;
    M[19] += x * y;
    M[24] += y2;

    b[0] += x2 * z;
    b[1] += y2 * z;
    b[2] += x * y * z;
    b[3] += x * z;
    b[4] += y * z;
  }

  // Enforce symmetry to eliminate round-off errors.
  for (std::uint8_t i = 1; i < 5; ++i) {
    for (std::uint8_t j = 0; j < i; ++j) { M[i * 5 + j] = M[j * 5 + i]; }
  }

  // Solve the linear system of equations, compile-time selection.
  if constexpr (solver == SolverType::plainLU) {
    plainLUSolver<V, 5>(M, solution, b, util::min(5, nbrInterfaces));
  }
  else if constexpr (solver == SolverType::rowPivotingLU) {
    rowPivotingLUSolver<V, 5>(M, solution, b, util::min(5, nbrInterfaces));
  }
  else if constexpr (solver == SolverType::completePivotingLU) {
    completePivotingLUSolver<V, 5>(M, solution, b, util::min(5, nbrInterfaces));
  }
  /*else if constexpr (solver == SolverType::eigen) {
    eigenSolver<V, 5>(M, solution, b, util::min(5, nbrInterfaces));
  }*/
  else {
    // Fall back to default solver
    plainLUSolver<V, 5>(M, solution, b, util::min(5, nbrInterfaces));
  }

  // Compute curvature from the linear system solution, i.e., fitting f(x,y) = A * x^2 + B * y^2 + C * x * y + H * x + I * y.
  const V A = solution[0], B = solution[1], C = solution[2], H = solution[3], I = solution[4];
  const V curvature = (A * (I * I + V(1)) + B * (H * H + V(1)) - C * H * I) * util::cube(V(1) / util::sqrt(H * H + I * I + V(1)));
  return util::max(V(-1), util::min(V(1), curvature));
}

template <typename CELL, typename V>
V any_platform computeCurvature(CELL& cell) {
  using DESCRIPTOR = typename CELL::descriptor_t;

  if constexpr (DESCRIPTOR::d == 2) {
    return computeCurvaturePLIC2D(cell);
  }
  else if constexpr (DESCRIPTOR::d == 3) {
    return computeCurvaturePLIC3D(cell);
  }
  else {
    static_assert(DESCRIPTOR::d == 2 || DESCRIPTOR::d == 3,
      "Interface curvature method is only implemented for 2D and 3D.");
    return V(0);
  }
}

} // namespace FreeSurface

} // namespace olb
