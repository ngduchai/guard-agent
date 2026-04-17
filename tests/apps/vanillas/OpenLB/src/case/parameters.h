/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender
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

#ifndef CASE_PARAMETERS_H
#define CASE_PARAMETERS_H

#include "io/cliReader.h"
#include "core/meta.h"

namespace olb {

namespace parameters {

struct OVERLAP : public descriptors::TYPED_FIELD_BASE<unsigned,1> {
  template <typename T, typename DESCRIPTOR>
  static constexpr auto getInitialValue() {
    return Vector<value_type<T>,1>{3};
  }
};

// Characteristic numbers
struct REYNOLDS    : public descriptors::FIELD_BASE<1> { };
struct RAYLEIGH    : public descriptors::FIELD_BASE<1> { };
struct PRANDTL     : public descriptors::FIELD_BASE<1> { };
struct TAYLOR      : public descriptors::FIELD_BASE<1> { };
struct SMAGORINSKY : public descriptors::FIELD_BASE<1> { };
struct SCHMIDT     : public descriptors::FIELD_BASE<1> { };
struct PECLET      : public descriptors::FIELD_BASE<1> { };
struct KNUDSEN     : public descriptors::FIELD_BASE<1> { };
struct STOKES       : public descriptors::FIELD_BASE<1> { };
struct NUSSELT      : public descriptors::FIELD_BASE<1> { };
struct PRANDTL_TURB : public descriptors::FIELD_BASE<1> { };

// Converter-related parameters
struct RESOLUTION : public descriptors::TYPED_FIELD_BASE<int,1> {
  template <typename T, typename DESCRIPTOR, typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value > 0;
  }
};
struct TIME_RESOLUTION : public descriptors::TYPED_FIELD_BASE<int,1> { };

struct PHYS_DELTA_X : public descriptors::FIELD_BASE<1> { };
struct PHYS_DELTA_T : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_VELOCITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_LENGTH : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_TIME : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_VISCOSITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_DENSITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_PRESSURE : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_TEMPERATURE : public descriptors::FIELD_BASE<1> { };
struct PHYS_THERMAL_CONDUCTIVITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_HEAT_CAPACITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_THERMAL_DIFFUSIVITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_THERMAL_EXPANSION : public descriptors::FIELD_BASE<1> { };

struct PHYS_CP : public descriptors::FIELD_BASE<1> { };

struct VOLUME : public descriptors::FIELD_BASE<1> { };

struct LATTICE_CHAR_VELOCITY : public descriptors::FIELD_BASE<1> { };
struct LATTICE_RELAXATION_TIME : public descriptors::FIELD_BASE<1> { };

struct CFL : public descriptors::FIELD_BASE<1> {};

struct TIME_STEPS: public descriptors::TYPED_FIELD_BASE<std::size_t,1> { };

struct DOMAIN_EXTENT : public descriptors::FIELD_BASE<0,1> { };
struct DOMAIN_L : public descriptors::FIELD_BASE<1> { };

struct ORIGIN : public descriptors::FIELD_BASE<0,1> { };

struct T_HOT  : public descriptors::FIELD_BASE<1> { };
struct T_COLD : public descriptors::FIELD_BASE<1> { };
struct T_MEAN   : public descriptors::FIELD_BASE<1> { };
struct T_PERTURBATION : public descriptors::FIELD_BASE<1> { };

struct RHO_1  : public descriptors::FIELD_BASE<1> { };
struct RHO_2  : public descriptors::FIELD_BASE<1> { };

struct PHYS_DENSITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_KINEMATIC_VISCOSITY : public descriptors::FIELD_BASE<1> { };
struct PHYS_DIFFUSIVITY : public descriptors::FIELD_BASE<1> { };

// Solids (NCE)
struct YOUNGS_MODULUS : public descriptors::FIELD_BASE<1> { };
struct POISSON_RATIO : public descriptors::FIELD_BASE<1> { };
struct PHYS_CHAR_DISPLACEMENT : public descriptors::FIELD_BASE<1> { };
struct OMEGA_SOLID : public descriptors::FIELD_BASE<0,0,1> { };

// Multicomponent
struct NU_VAPOR        : public descriptors::FIELD_BASE<1> { };
struct NU_LIQUID       : public descriptors::FIELD_BASE<1> { };
struct RHO_VAPOR       : public descriptors::FIELD_BASE<1> { };
struct RHO_LIQUID      : public descriptors::FIELD_BASE<1> { };
struct THETA           : public descriptors::FIELD_BASE<1> { };
struct SURFACE_TENSION : public descriptors::FIELD_BASE<1> { };
struct INTERFACE_WIDTH : public descriptors::FIELD_BASE<1> { };

struct COUPLING_G       : public descriptors::FIELD_BASE<1> { };
struct NOISE            : public descriptors::FIELD_BASE<1> { };
struct FORCE            : public descriptors::FIELD_BASE<1> { };
struct ZERO             : public descriptors::FIELD_BASE<1> { };

// Solids pseudo-time
struct IT_LOG_PSEUDO_TIME : public descriptors::TYPED_FIELD_BASE<int,1> { };
struct IT_VTK_PSEUDO_TIME : public descriptors::TYPED_FIELD_BASE<int,1> { };

struct VTK_ENABLED     : public descriptors::TYPED_FIELD_BASE<bool,1> { };
struct GNUPLOT_ENABLED : public descriptors::TYPED_FIELD_BASE<bool,1> { };

struct MAX_PHYS_T : public descriptors::FIELD_BASE<1> { };
struct MAX_LATTICE_T : public descriptors::TYPED_FIELD_BASE<std::size_t,1> { };

struct PHYS_BOUNDARY_VALUE_UPDATE_T : public descriptors::FIELD_BASE<1> { };
struct PHYS_START_T : public descriptors::FIELD_BASE<1> { };
struct PHYS_SAVE_ITER : public descriptors::FIELD_BASE<1> { };
struct PHYS_VTK_ITER_T : public descriptors::FIELD_BASE<1> { };
struct PHYS_STAT_ITER_T       : public descriptors::FIELD_BASE<1> { };
struct PHYS_START_PERIOD : public descriptors::FIELD_BASE<1> { };

struct LATTICE_STAT_ITER_T    : public descriptors::TYPED_FIELD_BASE<int,1> { };
struct LATTICE_VTK_ITER_T     : public descriptors::TYPED_FIELD_BASE<int,1> { };

struct CONVERGED : public descriptors::TYPED_FIELD_BASE<bool,1> { };
struct CONVERGENCE_PRECISION : public descriptors::FIELD_BASE<1> { };
struct EPSILON : public descriptors::FIELD_BASE<1> { };
struct CONV_ITER : public descriptors::FIELD_BASE<1> { };
struct INTERVAL_CONVERGENCE_CHECK : public descriptors::FIELD_BASE<1> { };

struct GRAVITY : public descriptors::FIELD_BASE<0,1> { };

struct GRAVITATIONAL_ACC  : public descriptors::FIELD_BASE<1> { };
struct GRAVITATIONAL_CONST : public descriptors::FIELD_BASE<1> { };
struct INITIAL_FALLING_SPEED : public descriptors::FIELD_BASE<0,1> { };

struct TURBULENCE_INTENSITY    : public descriptors::FIELD_BASE<1> { };
struct TURBULENCE_N_SEEDS      : public descriptors::FIELD_BASE<1> { };
struct TURBULENCE_N_TIME       : public descriptors::FIELD_BASE<1> { };
struct TURBULENCE_SIGMA        : public descriptors::FIELD_BASE<1> { };

struct NU : public descriptors::FIELD_BASE<1> { };
struct RHO_VAPOR_ANALYTICAL : public descriptors::FIELD_BASE<1> { };
struct RHO_LIQUID_ANALYTICAL : public descriptors::FIELD_BASE<1> { };
struct LIQUID_PHASE_LENGTH : public descriptors::FIELD_BASE<1> { };
struct THICKNESS : public descriptors::FIELD_BASE<1> { };
struct INTERFACE_VELOCITY_ANALYTICAL : public descriptors::FIELD_BASE<1> { };
struct BOUNDARY_CHEMICAL_POTENTIAL : public descriptors::FIELD_BASE<1> { };

struct ABSORPTION : public descriptors::FIELD_BASE<1> {};
struct SCATTERING : public descriptors::FIELD_BASE<1> {};
struct MU_EFF : public descriptors::FIELD_BASE<1> {};
struct ANINOSOTROPY_FACTOR : public descriptors::FIELD_BASE<1> {};
struct MCVALUE : public descriptors::FIELD_BASE<1> {};
struct TOTAL_ENERGY : public descriptors::FIELD_BASE<1> {};
struct INTENSITY : public descriptors::FIELD_BASE<1> {};

struct PART_RADIUS : public descriptors::FIELD_BASE<1> {};
struct PART_RHO : public descriptors::FIELD_BASE<1> {};

// Optimization
struct INITIAL_CONTROL_SCALAR : public descriptors::FIELD_BASE<1> { };
struct REGULARIZATION_FACTOR : public descriptors::FIELD_BASE<1> { };
struct MAX_OPTI_ITER : public descriptors::FIELD_BASE<1> { };
struct MAX_STEP_CONTROL_ITER : public descriptors::FIELD_BASE<1> { };
struct OPTI_CONVERGENCE_TOLERANCE : public descriptors::FIELD_BASE<1> { };

// Primitives
struct FACTOR : public descriptors::FIELD_BASE<1> { };
struct OMEGA : public descriptors::FIELD_BASE<1> { };
struct DT : public descriptors::FIELD_BASE<1> { };
struct DX : public descriptors::FIELD_BASE<1> { };
struct LATTICE_VISCOSITY : public descriptors::FIELD_BASE<1> { };
struct CONVERSION_VELOCITY : public descriptors::FIELD_BASE<1> { };
struct REG_ALPHA : public descriptors::FIELD_BASE<1> { };
struct NORMALIZE : public descriptors::FIELD_BASE<1> { };

struct RADIUS : public descriptors::FIELD_BASE<1> { };
struct CENTER : public descriptors::FIELD_BASE<0,1> { };


/// Returns name of PARAMETER for human consumption
template <typename PARAMETER>
std::string name() {
  auto raw = meta::nice_name<PARAMETER>();
  if (raw.starts_with("olb::")) {
    raw = std::string_view(raw.cbegin() + 5,
                           raw.cend());
  }
  if (raw.starts_with("parameters::")) {
    raw = std::string_view(raw.cbegin() + 12,
                           raw.cend());
  }
  return std::string(raw);
}

}

}

#endif
