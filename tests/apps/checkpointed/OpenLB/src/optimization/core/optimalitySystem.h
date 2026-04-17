/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2026 Shota Ito
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

#ifndef OPTIMALITY_SYSTEM_H
#define OPTIMALITY_SYSTEM_H

#include "case/parameters.h"

namespace olb {

namespace opti {

/// Class to abstract adjoint-related gradient computations for single-lattice,
/// stationary primal problems. This class provide helper functions for:
/// - creating operators for objective evaluations and their derivatives
/// - creating operators for evaluating the optimality condition
/// - make sure to copy required fields accross primal and adjoint lattices
/// Note: the adjoint dynamics from discreteAdjointDynamics.h are assumed to be used
template <concepts::DifferentiableFunctor OBJECTIVE,
          typename PRIMAL_DYNAMICS,
          typename CONTROLLED_FIELD,
          typename T=PRIMAL_DYNAMICS::value_t,
          typename DESCRIPTOR=PRIMAL_DYNAMICS::descriptor_t
>
class StationaryOptimalitySystem {
public:
  using value_t = T;
  using descriptor_t = DESCRIPTOR;
  using objective_t = OBJECTIVE;
  using dynamics_t = PRIMAL_DYNAMICS;
  using controls_t = CONTROLLED_FIELD;

private:
  template <typename FUNCTOR, typename FIELD>
  using WriteFunctorIntoFieldO = SuperLatticeCoupling<SingleLatticeO<operators::WriteFunctorO<FUNCTOR,FIELD>>,
                                                      meta::map<names::Lattice1,
                                                      descriptors::VALUED_DESCRIPTOR<T,DESCRIPTOR>>>;

  template <typename RESPECT_TO>
  using djd_t = functors::DerivativeF<OBJECTIVE,RESPECT_TO,PRIMAL_DYNAMICS>;

  // Operator which execute the objective functor and write in opti::J
  std::unique_ptr<WriteFunctorIntoFieldO<OBJECTIVE,opti::J>> j;
  // Derivative of the objective regarding the populations and write in opti::DJDF
  std::unique_ptr<WriteFunctorIntoFieldO<djd_t<descriptors::POPULATION>,opti::DJDF>> djdf;
  // Derivative of the objective regarding the controls and write in opti::DJDALPA
  std::unique_ptr<WriteFunctorIntoFieldO<djd_t<CONTROLLED_FIELD>,opti::DJDALPHA<CONTROLLED_FIELD>>> djdalpha;
  // Derivative of the primal dynamics regarding the controls and write in opti::DCDALPHA
  std::unique_ptr<WriteFunctorIntoFieldO<functors::DerivativeF<functors::CollisionF<PRIMAL_DYNAMICS>,
                                                               CONTROLLED_FIELD,
                                                               PRIMAL_DYNAMICS>,
                                         opti::DCDALPHA<CONTROLLED_FIELD>>> dcdalpha;

public:
  template <typename... ARGS>
  void setObjectiveParameters(SuperLattice<T,DESCRIPTOR>& lattice,
                              ARGS&&... args) {
    j = makeWriteFunctorO<OBJECTIVE,opti::J>(lattice);
    auto objectiveParameters = makeParametersD<T,DESCRIPTOR>(std::forward<ARGS&&>(args)...);
    using passed = typename meta::map<ARGS...>::keys_t;
    using required = typename OBJECTIVE::parameters_t;
    passed::for_each([&](auto id) {
      using field_t = typename decltype(id)::type;
      static_assert(required::template contains<field_t>(),
                    "Parameter passed which is not required by the objective functor");
      j->template setParameter<field_t>(objectiveParameters.template get<field_t>());
    });
  }

  // Execute cell-scoped objective operator and integrate the result
  T evaluateObjectiveF(SuperLattice<T,DESCRIPTOR>& lattice,
                       FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& indicator) {
    j->restrictTo(std::forward<decltype(indicator)>(indicator));
    j->apply();
    return integrateField<opti::J>(lattice,
                                   std::forward<decltype(indicator)>(indicator),
                                   lattice.getUnitConverter().getPhysDeltaX())[0];
  }

  // Compute derivatives required for the adjoint source term
  void differentiateObjectiveFByPopulations(SuperLattice<T,DESCRIPTOR>& lattice,
                                            FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& indicator) {
    djdf = makeWriteFunctorO<djd_t<descriptors::POPULATION>,opti::DJDF>(lattice);
    using parameters_t = typename OBJECTIVE::parameters_t;
    parameters_t::for_each([&](auto id){
      using field_t = typename decltype(id)::type;
      djdf->template setParameter<field_t>(j->template getParameter<field_t>());
    });
    // DerivativeF only computes in the cell-scope; the objective is mostly a weighted sum over all cells, which is why this is required
    djdf->template setParameter<parameters::FACTOR>(util::pow(lattice.getUnitConverter().getPhysDeltaX(), DESCRIPTOR::d));
    djdf->restrictTo(std::forward<decltype(indicator)>(indicator));
    djdf->apply();
  }

  // Compiute derivatives required for the optimality condition
  void differentiateObjectiveFByControls(SuperLattice<T,DESCRIPTOR>& lattice,
                                         FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& indicator) {
    djdalpha = makeWriteFunctorO<djd_t<CONTROLLED_FIELD>,opti::DJDALPHA<CONTROLLED_FIELD>>(lattice);
    using parameters_t = typename OBJECTIVE::parameters_t;
    parameters_t::for_each([&](auto id){
      using field_t = typename decltype(id)::type;
      djdalpha->template setParameter<field_t>(j->template getParameter<field_t>());
    });
    // DerivativeF only computes in the cell-scope; the objective is mostly a weighted sum over all cells, which is why this is required
    djdalpha->template setParameter<parameters::FACTOR>(util::pow(lattice.getUnitConverter().getPhysDeltaX(), DESCRIPTOR::d));
    djdalpha->restrictTo(std::forward<decltype(indicator)>(indicator));
    djdalpha->apply();
  }

  // This is required as currently it is not possible to retreive parameters from solely the dynamics type
  template <typename... ARGS>
  void setPrimalCollisionParameters(SuperLattice<T,DESCRIPTOR>& lattice,
                                    ARGS&&... args) {
    using dcdalpha_t = functors::DerivativeF<functors::CollisionF<PRIMAL_DYNAMICS>,
                                             CONTROLLED_FIELD,
                                             PRIMAL_DYNAMICS>;
    dcdalpha = makeWriteFunctorO<dcdalpha_t,opti::DCDALPHA<CONTROLLED_FIELD>>(lattice);
    auto dynamicsParameters = makeParametersD<T,DESCRIPTOR>(std::forward<ARGS&&>(args)...);
    using passed = typename meta::map<ARGS...>::keys_t;
    passed::for_each([&](auto id) {
      using field_t = typename decltype(id)::type;
      dcdalpha->template setParameter<field_t>(dynamicsParameters.template get<field_t>());
    });
    // Here no normalization is required as the collision is no integral operation
    dcdalpha->template setParameter<parameters::FACTOR>(1.0);
  };

  // Compiute derivatives required for the optimality condition
  void differentiateCollisionFByControls(FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& indicator) {
    dcdalpha->restrictTo(std::forward<decltype(indicator)>(indicator));
    dcdalpha->apply();
  };

  // NOTE: this function assumes that discrete adjoint collision is used
  void initializeAdjointProblem(SuperLattice<T,DESCRIPTOR>& adjointLattice,
                                SuperLattice<T,DESCRIPTOR>& controlledLattice,
                                FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& indicator) {
    this->differentiateObjectiveFByPopulations(controlledLattice, std::forward<decltype(indicator)>(indicator));
    copyFields<CONTROLLED_FIELD,CONTROLLED_FIELD>(controlledLattice, adjointLattice);
    // Make sure that the adjoint collision requires shifted-populations (f - descriptors::t)
    copyFields<descriptors::POPULATION,opti::F>(controlledLattice, adjointLattice);
    copyFields<opti::DJDF,opti::DJDF>(controlledLattice, adjointLattice);
  }

  // Computes total derivatives of the objectives regarding the control parameters
  std::vector<T> evaluateOptimalityCondition(SuperLattice<T,DESCRIPTOR>& adjointLattice,
                                             SuperLattice<T,DESCRIPTOR>& controlledLattice,
                                             FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& indicator) {
    // Compute objective derivative regarding controlls
    this->differentiateObjectiveFByControls(controlledLattice, std::forward<decltype(indicator)>(indicator));
    this->differentiateCollisionFByControls(std::forward<decltype(indicator)>(indicator));
    auto optimalityO = makeWriteFunctorO<functors::OptimalityF<PRIMAL_DYNAMICS,CONTROLLED_FIELD>,
                                         opti::SENSITIVITY<CONTROLLED_FIELD>>(adjointLattice);

    // Jacobian is computed on primal lattice as jacobian is evaluated for primal populations
    copyFields<opti::DCDALPHA<CONTROLLED_FIELD>,opti::DCDALPHA<CONTROLLED_FIELD>>(controlledLattice, adjointLattice);
    copyFields<opti::DJDALPHA<CONTROLLED_FIELD>,opti::DJDALPHA<CONTROLLED_FIELD>>(controlledLattice, adjointLattice);
    optimalityO->restrictTo(std::forward<decltype(indicator)>(indicator));
    optimalityO->apply();

    adjointLattice.setProcessingContext(ProcessingContext::Evaluation);
    return getSerializedFromField<opti::SENSITIVITY<CONTROLLED_FIELD>>(adjointLattice,
                                                                       std::forward<decltype(indicator)>(indicator));
  }
};

}

}

#endif
