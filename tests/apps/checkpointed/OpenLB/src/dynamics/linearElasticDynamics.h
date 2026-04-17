/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2024 Florian Kaiser, Stephan Simonis
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

/** \file
 * A collection of dynamics classes (e.g. BGK) with which a Cell object
 * can be instantiated -- header file.
 */
#ifndef LINEAR_ELASTIC_DYNAMICS_H
#define LINEAR_ELASTIC_DYNAMICS_H

#include "dynamics/dynamics.h"
#include "core/unitConverter.h"
#include "collisionMRT.h"

namespace olb
{

// ======= Implementation of collision for linear elasticity with periodic boundary conditions =======
// following Boolakee, O. (2023).
// A new lattice Boltzmann scheme for linear elastic solids: periodic problems.
// Computer Methods in Applied Mechanics and Engineering, 404.
template<typename T, typename DESCRIPTOR>
struct BoolakeeLinearElasticity final : public dynamics::CustomCollision<
  T,DESCRIPTOR,
  momenta::BulkTuple
> {
  using MomentaF = typename momenta::BulkTuple::template type<DESCRIPTOR>;
  using EquilibriumF = typename equilibria::None::template type<DESCRIPTOR, momenta::BulkTuple>;
  using parameters = meta::list<descriptors::OMEGA_SOLID>;

  template<typename M>
  using exchange_momenta = BoolakeeLinearElasticity<T,DESCRIPTOR>;

  template<typename V>
  using exchange_value_type = BoolakeeLinearElasticity<V,DESCRIPTOR>;

  std::type_index id() override
  {
    return typeid(BoolakeeLinearElasticity);
  };

  AbstractParameters<T,DESCRIPTOR>& getParameters(BlockLattice<T,DESCRIPTOR>& block) override
  {
    return block.template getData<OperatorParameters<BoolakeeLinearElasticity>>();
  }

  template <typename CELL, typename PARAMETERS, typename V=typename CELL::value_t>
  CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform
  {
    auto allOmegas = parameters.template get<descriptors::OMEGA_SOLID>();

    const V theta     = descriptors::invCs2<V,DESCRIPTOR>();

    const V omega_11  = allOmegas[0];
    const V omega_d   = allOmegas[1];
    const V omega_s   = allOmegas[2];
    const V omega_12  = allOmegas[3];
    const V omega_21  = allOmegas[4];
    const V omega_22  = allOmegas[5];

    V Omega[8][8] =
    {
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, omega_11, 0, 0, 0, 0, 0},
      {0, 0, 0, omega_s, 0, 0, 0, 0},
      {0, 0, 0, 0, omega_d, 0, 0, 0},
      {0, 0, 0, 0, 0, omega_12, 0, 0},
      {0, 0, 0, 0, 0, 0, omega_21, 0},
      {0, 0, 0, 0, 0, 0, 0, omega_22},
    };

    // Compute Forcing
    const auto force    = cell.template getField<descriptors::FORCE>();
    V f1[DESCRIPTOR::q] = {force[0], force[1], 0., 0., 0., 0., 0., 0.};

    // Calculate m and store on field
    V m[DESCRIPTOR::q];
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop)
    {
      m[iPop] = 0.5 * f1[iPop];
      for (int jPop = 0; jPop < DESCRIPTOR::q; ++jPop)
      {
        m[iPop] += descriptors::mSolid<V,DESCRIPTOR>(iPop, jPop) * cell[jPop];
      }
    }

    // Compute meq
    V momentaFactors[DESCRIPTOR::q][2] =
    {
      {1, 0},
      {0, 1},
      {0, 0},
      {0, 0},
      {0, 0},
      {theta, 0},
      {0, theta},
      {0, 0}
    };

    V meq[DESCRIPTOR::q] { };
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop)
    {
      meq[iPop] = 0.;
      for (int jPop = 0; jPop < 2; ++jPop)
      {
        meq[iPop] += momentaFactors[iPop][jPop] * m[jPop];
      }
    }

    // compute bracket
    V bracket[DESCRIPTOR::q] { };
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop)
    {
      bracket[iPop] = 0.5 * f1[iPop] + m[iPop];
      for (int jPop = 0; jPop < DESCRIPTOR::q; ++jPop)
      {
        bracket[iPop] += Omega[iPop][jPop] * (meq[jPop] - m[jPop]);
      }
    }

    // Compute new cell value
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop)
    {
      cell[iPop] = 0.;
      for (int jPop = 0; jPop < DESCRIPTOR::q; ++jPop)
      {
        cell[iPop] += descriptors::invMSolid<V,DESCRIPTOR>(iPop, jPop) * bracket[jPop];
      }
    }

    // Calculate bared moments
    V m_bared[DESCRIPTOR::q] = {0., 0., 0., 0., 0., 0., 0., 0.};
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop)
    {
      m_bared[iPop] = (m[iPop] + bracket[iPop]) / 2.;
    }

    cell.template setField<descriptors::BARED_MOMENT_VECTOR>(m_bared);
    cell.template setField<descriptors::MOMENT_VECTOR>(bracket);

    // Numerical Displacement for analysis
    cell.template setField<descriptors::DISP_SOLID>({m_bared[0], m_bared[1]});

    V sigmaxx = -((m[3] + m[4]) / 2. - .25 * (omega_s * m[3] + omega_d * m[4]));
    V sigmaxy = -  m[2] * (1. - omega_11 / 2.);
    V sigmayx = sigmaxy;
    V sigmayy = -((m[3] - m[4]) / 2. - .25 * (omega_s * m[3] - omega_d * m[4]));

    cell.template setField<descriptors::SIGMA_SOLID>({sigmaxx, sigmaxy, sigmayx, sigmayy});

    return {-1, -1};
  };

  void computeEquilibrium(ConstCell<T,DESCRIPTOR>& cell,
                                  T rho,
                                  const T u[DESCRIPTOR::d],
                                  T fEq[DESCRIPTOR::q]) const override
  {
    EquilibriumF().compute(cell, rho, u, fEq);
  }

  std::string getName() const override
  {
    return "BoolakeeLinearElasticity<" + MomentaF().getName() + ">";
  };
};


// ======= Implementation of collision for linear elasticity with boundary conditions =======
// following Boolakee, O. (2023).
// Dirichlet and Neumann boundary conditions for a lattice Boltzmann scheme for linear elastic solids on arbitrary domains.
// Computer Methods in Applied Mechanics and Engineering, 415.
template<typename T, typename DESCRIPTOR>
struct BoolakeeLinearElasticityBoundary final : public dynamics::CustomCollision<
  T,DESCRIPTOR,
  momenta::BulkTuple
> {
  using MomentaF = typename momenta::BulkTuple::template type<DESCRIPTOR>;
  using EquilibriumF = typename equilibria::None::template type<DESCRIPTOR, momenta::BulkTuple>;
  using parameters = meta::list<descriptors::MAGIC_SOLID,descriptors::OMEGA_SOLID>;

  template<typename M>
  using exchange_momenta = BoolakeeLinearElasticityBoundary<T,DESCRIPTOR>;

  template<typename V>
  using exchange_value_type = BoolakeeLinearElasticityBoundary<V,DESCRIPTOR>;

  std::type_index id() override
  {
    return typeid(BoolakeeLinearElasticityBoundary);
  };

  AbstractParameters<T,DESCRIPTOR>& getParameters(BlockLattice<T,DESCRIPTOR>& block) override
  {
    return block.template getData<OperatorParameters<BoolakeeLinearElasticityBoundary>>();
  }

  template <typename CELL, typename PARAMETERS, typename V=typename CELL::value_t>
  CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform
  {
    auto allOmegas = parameters.template get<descriptors::OMEGA_SOLID>();

    // dx, dt, theta, mü, lambda, kappa, uChar, epsilon
    /*
    const V dx        = magic[0];
    const V dt        = magic[1];
    const V mu        = magic[3];
    const V lambda    = magic[4];
    const V bulk      = lambda + mu;
    const V kappa     = magic[5];
    const V charU     = magic[6];
    const V epsilon   = magic[7];
    */
    const V theta     = descriptors::invCs2<V, DESCRIPTOR>();

    const V omega_11  = allOmegas[0];
    const V omega_s   = allOmegas[1];
    const V omega_d   = allOmegas[2];
    const V omega_12  = allOmegas[3];
    const V omega_21  = allOmegas[4];
    const V omega_22  = allOmegas[5];

    V Omega[8][8] = {
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, omega_11, 0, 0, 0, 0, 0},
      {0, 0, 0, omega_s, 0, 0, 0, 0},
      {0, 0, 0, 0, omega_d, 0, 0, 0},
      {0, 0, 0, 0, 0, omega_12, 0, 0},
      {0, 0, 0, 0, 0, 0, omega_21, 0},
      {0, 0, 0, 0, 0, 0, 0, omega_22},
    };

    V tau_s = 1. / omega_s - 0.5;
    V tau_f = 1. / 2.;

    // Calculate gamma and compute m_f
    V gamma = theta * tau_f/ ((1. + theta) * (tau_s - tau_f));

    V MatrixM[DESCRIPTOR::q][DESCRIPTOR::q] = {
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 0, 0, 0, 0, 0, 0, 0},
      {gamma, gamma, gamma, gamma, (1. + 2. * gamma), (1. + 2. * gamma), (1. + 2. * gamma), (1. + 2. * gamma)},
    };
    for (int iPop = 0; iPop < 7; ++iPop) {
      for (int jPop = 0; jPop < DESCRIPTOR::q; ++jPop) {
        MatrixM[iPop][jPop] = descriptors::mSolid<V,DESCRIPTOR>(iPop, jPop);
      }
    }

    // Get Forcing
    const auto force    = cell.template getField<descriptors::FORCE>();
    V f1[DESCRIPTOR::q] = {force[0], force[1], 0., 0., 0., 0., 0., 0.};

    // Calculate moments
    V m[DESCRIPTOR::q] = {0., 0., 0., 0., 0., 0., 0., 0.};
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
      // m[iPop] = V{0.5} * f1[iPop];
      for (int jPop = 0; jPop < DESCRIPTOR::q; ++jPop) {
        // m[iPop] += descriptors::mSolid<V,DESCRIPTOR>(iPop, jPop) * cell[jPop];
        m[iPop] += MatrixM[iPop][jPop] * cell[jPop];
      }
    }

    V momentaFactors[DESCRIPTOR::q][2] = {
      {1, 0},
      {0, 1},
      {0, 0},
      {0, 0},
      {0, 0},
      {theta, 0},
      {0, theta},
      {0, 0}
    };

    // Compute meq
    V meq[DESCRIPTOR::q] { };
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
      meq[iPop] = 0.;
      for (int jPop = 0; jPop < 2; ++jPop) {
        meq[iPop] += momentaFactors[iPop][jPop] * m[jPop];
      }
    }

    // compute bracket
    V bracket[DESCRIPTOR::q] {f1[0] + m[0], f1[1] + m[1], 0., 0., 0., 0., 0., 0.};
    for (int iPop = 2; iPop < DESCRIPTOR::q; ++iPop) {
      // bracket[iPop] = V{0.5} * f1[iPop] + m[iPop];
      bracket[iPop] = m[iPop];
      for (int jPop = 0; jPop < DESCRIPTOR::q; ++jPop) {
        bracket[iPop] += Omega[iPop][jPop] * (meq[jPop] - m[jPop]);
      }
    }

    V invMatrix[DESCRIPTOR::q][DESCRIPTOR::q] = {
      { 0.5,    0.0,   0.0,   gamma/2. + 0.25,   0.25,  -0.5,   0.0,  -0.5 },
      { 0.0,    0.5,   0.0,   gamma/2. + 0.25,  -0.25,   0.0,  -0.5,  -0.5 },
      {-0.5,    0.0,   0.0,   gamma/2. + 0.25,   0.25,   0.5,   0.0,  -0.5 },
      { 0.0,   -0.5,   0.0,   gamma/2. + 0.25,  -0.25,   0.0,   0.5,  -0.5 },
      { 0.0,    0.0,   0.25, -gamma/4.0,         0.0,    0.25,  0.25,  0.25 },
      { 0.0,    0.0,  -0.25, -gamma/4.0,         0.0,   -0.25,  0.25,  0.25 },
      { 0.0,    0.0,   0.25, -gamma/4.0,         0.0,   -0.25, -0.25,  0.25 },
      { 0.0,    0.0,  -0.25, -gamma/4.0,         0.0,    0.25, -0.25,  0.25 },
    };

    // Compute new cell value
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
      cell[iPop] = 0.;
      for (int jPop = 0; jPop < DESCRIPTOR::q; ++jPop) {
        cell[iPop] += invMatrix[iPop][jPop] * bracket[jPop];
      }
    }

    // Calculate bared moments
    V m_bared[DESCRIPTOR::q] = {0., 0., 0., 0., 0., 0., 0., 0.};
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
      m_bared[iPop] = (m[iPop] + bracket[iPop]) / 2.;
    }

    auto previous_cell = cell.template getField<descriptors::CURRENT_CELL>();
    cell.template setField<descriptors::CURRENT_CELL>({cell[0], cell[1], cell[2], cell[3], cell[4], cell[5], cell[6], cell[7]});
    cell.template setField<descriptors::PREVIOUS_CELL>({previous_cell[0], previous_cell[1], previous_cell[2], previous_cell[3], previous_cell[4], previous_cell[5], previous_cell[6], previous_cell[7]});

    cell.template setField<descriptors::BARED_MOMENT_VECTOR>(m_bared);
    cell.template setField<descriptors::MOMENT_VECTOR>(bracket);
    cell.template setField<descriptors::DISP_SOLID>({m_bared[0], m_bared[1]});

    // Compute Stress Field in lattice units
    V sigma_xx = -((m[3] + m[4]) / 2. - .25 * (omega_s * m[3] + omega_d * m[4]));
    V sigma_xy = -  m[2] * (1. - omega_11 / 2.);
    V sigma_yx = sigma_xy;
    V sigma_yy = -((m[3] - m[4]) / 2. - .25 * (omega_s * m[3] - omega_d * m[4]));

    cell.template setField<descriptors::SIGMA_SOLID>({sigma_xx, sigma_xy, sigma_yx, sigma_yy});

    return {-1, -1};
  };

  void computeEquilibrium(ConstCell<T,DESCRIPTOR>& cell,
                                T rho,
                                const T u[DESCRIPTOR::d],
                                T fEq[DESCRIPTOR::q]) const override
  {
    EquilibriumF().compute(cell, rho, u, fEq);
  }

  std::string getName() const override
  {
    return "BoolakeeLinearElasticityBoundary<" + MomentaF().getName() + ">";
  };
};

} // namespace olb

#endif
