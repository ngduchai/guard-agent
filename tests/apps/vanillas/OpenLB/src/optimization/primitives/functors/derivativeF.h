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

#ifndef DERIVATIVE_PRIMITIVE_F_H
#define DERIVATIVE_PRIMITIVE_F_H

#include "core/matrixView.h"
#include "dualLbHelpers.h"

namespace olb {

namespace functors {

/// Generic functor to compute the jacobian for any evaluated functor in respect to
/// the variables stored in the field RESPECT_TO. Dynamics type is required to
/// provide a cell with full cell interface, e.g., to compute the derivative of a collision.
template <concepts::DifferentiableFunctor FUNCTOR, typename RESPECT_TO, typename DYNAMICS>
struct DerivativeF {

  using parameters_t = typename FUNCTOR::parameters_t::template include<parameters::FACTOR>;
  using result_t = descriptors::FIELD_MATRIX<typename FUNCTOR::result_t, RESPECT_TO>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;

    /// Collecting all accessed fields in order to include them all for correct derivative computation
    using COMBINED_FIELDS = meta::merge<typename CELL::descriptor_t::fields_t, typename FUNCTOR::fields_t>;
    using DESCRIPTOR = typename COMBINED_FIELDS::template decompose_into<CELL::descriptor_t::template extend_by_fields>;

    /// Forward AD type for derivative computation
    using ADf = typename util::ADf<V,DESCRIPTOR::template size<RESPECT_TO>()>;
    using ADf_DYNAMICS = typename DYNAMICS::template exchange_value_type<ADf>;
    const V factor = parameters.template get<parameters::FACTOR>();

    /// Full cell providing complete cell interface instantiated with forward AD type
    FullCellD<ADf,DESCRIPTOR,ADf_DYNAMICS> adfCell;
    auto adfParams = parameters.template copyAs<ADf>();
    DESCRIPTOR::fields_t::for_each([&](auto id) {
      using FIELD = typename decltype(id)::type;
      adfCell.template setField<FIELD>(FieldD<ADf,DESCRIPTOR,FIELD>(cell.template getField<FIELD>()));
    });

    for (std::size_t iDim=0; iDim<DESCRIPTOR::template size<RESPECT_TO>(); ++iDim) {
      adfCell.template getFieldComponent<RESPECT_TO>(iDim).setDiffVariable(iDim);
    }

    FieldD<ADf,DESCRIPTOR,typename FUNCTOR::result_t> y = FUNCTOR{}.compute(adfCell, adfParams);
    FieldD<V,DESCRIPTOR,typename DerivativeF::result_t> jacobian;
    /// Provide matrix-native view on the serial FieldD
    auto view = DerivativeF::result_t::template getMatrixView<V,DESCRIPTOR>(jacobian);
    for (unsigned row=0; row<view.rows; ++row) {
      for (unsigned col=0; col<view.cols; ++col) {
        view[row][col] = (y[row]).d(col);
        view[row][col] *= factor; // scaling due to cell-wise contribution
      }
    }

    return jacobian;
  }
};

///// Manually derived dual functors (functors differentiated regarding populations) /////

struct DissipationDF {

  using parameters_t = meta::list<parameters::OMEGA,
                                  parameters::DT,
                                  parameters::PHYS_CHAR_VISCOSITY>;

  using result_t = descriptors::FIELD_MATRIX<descriptors::DISSIPATION,
                                             descriptors::POPULATION>;
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

    FieldD<V,DESCRIPTOR,result_t> dissipationD{};
    for (std::size_t jPop=0; jPop < DESCRIPTOR::q; ++jPop) {
      dissipationD[jPop] = 0;
      V dpidf[util::TensorVal<DESCRIPTOR>::n];
      opti::dualLbMomentaHelpers<DESCRIPTOR>::dPiDf(cell, dpidf, jPop);
      for (std::size_t iAlpha=0; iAlpha < DESCRIPTOR::d; ++iAlpha) {
        for (std::size_t iBeta=0; iBeta < DESCRIPTOR::d; ++iBeta) {
          const int iPi = util::serialSymmetricTensorIndex<DESCRIPTOR::d>(iAlpha, iBeta);
          dissipationD[jPop] += pi[iPi] * dpidf[iPi] - pi[iPi] * pi[iPi] / rho;
        }
      }
      dissipationD[jPop] *= 2. * util::pow(omega*descriptors::invCs2<V,DESCRIPTOR>() / rho, 2)
                            / 2. * physViscosity / dt / dt;
    }
    return dissipationD;
  }
};

struct PorousDissipationDF {

  using parameters_t = meta::list<parameters::OMEGA,
                                  parameters::DX,
                                  parameters::LATTICE_VISCOSITY,
                                  parameters::CONVERSION_VELOCITY,
                                  parameters::PHYS_CHAR_VISCOSITY>;

  using result_t = descriptors::FIELD_MATRIX<descriptors::POROUS_DISSIPATION,
                                         descriptors::POPULATION>;
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

    Vector<V,DESCRIPTOR::d> u{0};
    cell.computeU(u.data());
    const V gridTerm = dx * dx * viscosity / omega;
    const V invPermeability = (V(1) - porosity) / gridTerm;
    Vector<V,DESCRIPTOR::d> dudf;
    FieldD<V,DESCRIPTOR,result_t> dissipationD{};
    for (std::size_t jPop=0; jPop < DESCRIPTOR::q; ++jPop) {
      opti::dualLbMomentaHelpers<DESCRIPTOR>::dUDf(cell, dudf, jPop);
      dissipationD[jPop] = physViscosity * invPermeability * 2. * (u * dudf) *
                       conversionVelocity * conversionVelocity;
    }
    return dissipationD;
  }
};

struct TotalDissipationDalpha {

  using parameters_t = meta::list<parameters::OMEGA,
                                  parameters::DX,
                                  parameters::LATTICE_VISCOSITY,
                                  parameters::CONVERSION_VELOCITY,
                                  parameters::PHYS_CHAR_VISCOSITY,
                                  parameters::REG_ALPHA>;

  using result_t = descriptors::FIELD_MATRIX<descriptors::DISSIPATION,
                                             descriptors::POROSITY>;
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
    const V regAlpha = parameters.template get<parameters::REG_ALPHA>();

    Vector<V,DESCRIPTOR::d> u{0};
    cell.computeU(u.data());
    const V gridTerm = dx * dx * viscosity / omega;
    const V invPermeability = (V(1) - porosity) / gridTerm;
    const V uNormSq = util::euklidN2(u.data(), DESCRIPTOR::d) * conversionVelocity
                  * conversionVelocity;
    FieldD<V,DESCRIPTOR,result_t> dJDalpha = physViscosity * uNormSq * invPermeability + regAlpha;
    return dJDalpha;
  }
};

}

}

#endif
