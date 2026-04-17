/*  Lattice Boltzmann sample, written in C++, using the OpenLB
 *  library
 *
 *  Copyright (C) 2025 Shota Ito
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

#ifndef PHYS_F_H
#define PHYS_F_H

namespace olb {

namespace functors {

/// Computes the physical velocity
struct VelocityF {

  using parameters_t = meta::list<parameters::CONVERSION_VELOCITY>;
  using result_t = descriptors::VELOCITY;
  using fields_t = meta::list<>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    using DESCRIPTOR = typename CELL::descriptor_t;
    V conversion = parameters.template get<parameters::CONVERSION_VELOCITY>();
    V u[DESCRIPTOR::d]{0};
    cell.computeU(u);

    FieldD<V,DESCRIPTOR,VelocityF::result_t> physU{};
    for (auto iDim=0; iDim<DESCRIPTOR::d; ++iDim) {
      physU[iDim] = u[iDim] * conversion;
    }
    return physU;
  }
};

struct DissipationF {

  using parameters_t = meta::list<parameters::OMEGA,
                                  parameters::DT,
                                  parameters::PHYS_CHAR_VISCOSITY>;

  using result_t = descriptors::DISSIPATION;
  using fields_t = meta::list<>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    using DESCRIPTOR = typename CELL::descriptor_t;
    const V omega = parameters.template get<parameters::OMEGA>();
    const V dt = parameters.template get<parameters::DT>();
    const V physViscosity = parameters.template get<parameters::PHYS_CHAR_VISCOSITY>();

    V rho = 0; V u[DESCRIPTOR::d]{0}; V pi[util::TensorVal<DESCRIPTOR>::n]{0};
    cell.computeAllMomenta(rho, u, pi);

    V PiNeqNormSqr = pi[0] * pi[0] + 2. * pi[1] * pi[1] + pi[2] * pi[2];
    if (util::TensorVal<DESCRIPTOR>::n == 6) {
      PiNeqNormSqr += pi[2] * pi[2] + pi[3] * pi[3] + 2. * pi[4] * pi[4] + pi[5] * pi[5];
    }

    FieldD<V,DESCRIPTOR,descriptors::DISSIPATION> dissipation{};
    dissipation[0] = PiNeqNormSqr *
                     util::pow(omega * descriptors::invCs2<V,DESCRIPTOR>() / rho / dt, 2) /
                     V(2) * physViscosity;
    return dissipation;
  }
};

struct PorousDissipationF {
  using parameters_t = meta::list<parameters::OMEGA,
                                  parameters::DX,
                                  parameters::LATTICE_VISCOSITY,
                                  parameters::CONVERSION_VELOCITY,
                                  parameters::PHYS_CHAR_VISCOSITY>;
  using result_t = descriptors::POROUS_DISSIPATION;
  using fields_t = meta::list<descriptors::POROSITY>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    using DESCRIPTOR = typename CELL::descriptor_t;
    const V porosity = cell.template getField<descriptors::POROSITY>();
    const V omega = parameters.template get<parameters::OMEGA>();
    const V dx = parameters.template get<parameters::DX>();
    const V viscosity = parameters.template get<parameters::LATTICE_VISCOSITY>();
    const V physViscosity = parameters.template get<parameters::PHYS_CHAR_VISCOSITY>();
    const V conversionVelocity = parameters.template get<parameters::CONVERSION_VELOCITY>();

    V u[DESCRIPTOR::d]{0};
    cell.computeU(u);
    const V gridTerm = dx * dx * viscosity / omega;
    const V invPermeability = (V(1) - porosity) / gridTerm;
    const V uNormSq = util::euklidN2(u, DESCRIPTOR::d) * conversionVelocity * conversionVelocity;

    FieldD<V,DESCRIPTOR,descriptors::POROUS_DISSIPATION> dissipation{};
    dissipation[0] = physViscosity * invPermeability * uNormSq;
    return dissipation;
  }
};

}

}

#endif
