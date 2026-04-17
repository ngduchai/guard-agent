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

#ifndef DERIVATIVES_H
#define DERIVATIVES_H

namespace olb {

namespace opti {

namespace derivatives {

/// @brief   Logic to compute objective derivatives by manual definition
// Derivative needs to be passed via a callable (e.g. currently for adjoint optimization)
struct Manual {
  // Define how to compute the derivative using the OptiCase instance
  template <typename OPTICASE, typename T=OPTICASE::value_t, typename F=OPTICASE::derivative_t>
  static F getDerivativeF(OPTICASE& optiCase) {
    return [&optiCase](const std::vector<T>& controls) -> std::vector<T> {
      throw std::logic_error("Logic for derivative");
    };
  }
};

/// @brief   Logic to compute objective derivatives using forward difference quotients
struct FDQ {
  // Define how to compute the derivative using the OptiCase instance
  template <typename OPTICASE, typename T=OPTICASE::value_t, typename F=OPTICASE::derivative_t>
  static F getDerivativeF(OPTICASE& optiCase) {
    return [&optiCase](const std::vector<T>& controls) -> std::vector<T> {
      std::vector<T> derivatives;
      derivatives.reserve(controls.size());
      const T objective = optiCase.computeObjective(controls);
      for (std::size_t d=0; d < controls.size(); ++d) {
        std::vector<T> shiftedControl(controls);
        shiftedControl[d] += T(1e-8);
        const T shiftedObjective = optiCase.computeObjective(shiftedControl);
        // FDQ stencil
        derivatives[d] = (shiftedObjective - objective) / T(1e-8);
      }
      return derivatives;
    };
  }
};

/// @brief   Logic to compute objective derivatives using central difference quotients
struct CDQ {
  // Define how to compute the derivative using the OptiCase instance
  template <typename OPTICASE, typename T=OPTICASE::value_t, typename F=OPTICASE::derivative_t>
  static F getDerivativeF(OPTICASE& optiCase) {
    return [&optiCase](const std::vector<T>& controls) -> std::vector<T> {
      std::vector<T> derivatives;
      derivatives.reserve(controls.size());
      for (std::size_t d=0; d<controls.size(); ++d) {
        std::vector<T> shiftedControl(controls);
        shiftedControl[d] += T(5e-6);
        const T shiftedObjective_plus = optiCase.computeObjective(shiftedControl);
        shiftedControl[d] = controls[d] - T(5e-6);
        const T shiftedObjective_minus = optiCase.computeObjective(shiftedControl);
        // CDQ stencil
        derivatives[d] = T(0.5) * (shiftedObjective_plus - shiftedObjective_minus) / T(5e-6);
      }
      return derivatives;
    };
  }
};

/// @brief   Logic to compute objective derivatives by automatic differentiation forward mode
struct ADf {
  // Define how to compute the derivative using the OptiCase instance
  template <typename OPTICASE, typename T=OPTICASE::value_t, typename F=OPTICASE::derivative_t>
  static F getDerivativeF(OPTICASE& optiCase) {
    return [&optiCase](const std::vector<T>& controls) -> std::vector<T> {
      using U = typename OPTICASE::template case_t<names::Derivatives>::reference_component_t::value_t;
      std::vector<U> tmp = util::copyAs<U>(controls);
      util::iniDiagonal(tmp);
      U derivative = optiCase.template computeObjective<U>(tmp);
      return util::extractDerivatives(derivative);
    };
  }

};

} // namespace derivatives

} // namespace opti

} // namepsace olb

#endif
