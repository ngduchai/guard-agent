/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2012, 2021 Mathias J. Krause, Julius Jeßberger
 *                2025       Shota Ito
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


#ifndef OPTI_CASE_H
#define OPTI_CASE_H

#include "derivatives.h"
#include "case/case.h"

namespace olb {

namespace opti {

template <typename T> class Controller;
template <concepts::DifferentiableFunctor OBJECTIVE,
          typename PRIMAL_DYNAMICS,
          typename CONTROLLED_FIELD,
          typename T, typename DESCRIPTOR> class OptimalitySystem;

/// Abstract base class for optimization tasks
// provides function evaluation and gradient computation
template <typename T>
struct AbstractOptiCase {
  AbstractOptiCase() = default;

  virtual T computeObjective(const std::vector<T>& control, unsigned optiStep=0) = 0;
  virtual std::vector<T> computeDerivatives(const std::vector<T>& control, unsigned optiStep=0) = 0;
  virtual std::vector<T>& getControlVector() = 0;
};

// Help struct to assess data type and descriptor from the case-map
template <typename MAP>
struct LatticeTypeFromCase {
  template <typename NAME>
  using lattice_t = MAP::template value<NAME>::reference_component_t;
};

template <typename MAP>
using ValueTypeFromControlledCase = LatticeTypeFromCase<MAP>::template lattice_t<names::Controlled>::value_t;
template <typename MAP>
using ValueTypeFromDerivativesCase = LatticeTypeFromCase<MAP>::template lattice_t<names::Derivatives>::value_t;

/// @brief   OptiCase class specialized for optimizing simulation cases
/// @tparam  DERIVATIVE Logic how to compute the objective derivative regarding control parameters
/// @tparam  MAP        Assigns names to cases to distinguish different simualtion types
template <typename DERIVATIVE, typename MAP>
class OptiCase : public AbstractOptiCase<ValueTypeFromControlledCase<MAP>> {
public:
  // Get value type and descriptor type from the controlled case
  using value_t = ValueTypeFromControlledCase<MAP>;
  using objective_t = std::function<value_t(const std::vector<value_t>&)>;
  using derivative_t = std::function<std::vector<value_t>(const std::vector<value_t>&)>;

  template <typename COMPONENT>
  using ptr_to_component = COMPONENT*;

  template <typename NAME>
  requires (is_case_v<typename MAP::template value<NAME>>)
  using case_t = MAP::template value<NAME>;

private:
  // Cases and other components stored via non-owning pointers accessed by NAME types
  utilities::TypeIndexedTuple<typename MAP::template map_values<
    ptr_to_component
  >> _components;

  // Instace for managing control parameters
  Controller<value_t> _controller;
  // Encapsulate logic how to compute objective starting from setting controls
  objective_t _objective;
  // Encapsulate logic how to compute derivatives starting from setting controls
  derivative_t _derivative;

  std::size_t _optimizationStep = 0;

public:
  OptiCase() : _derivative(DERIVATIVE::getDerivativeF(*this)) { };

  template <typename NAME>
  void set(typename MAP::template value<NAME>& component) {
    _components.template set<NAME>(&component);
  }

  template <typename NAME>
  auto& get(NAME) {
    if (_components.template get<NAME>() == nullptr) {
      throw std::runtime_error("Accessed component was not set.");
    }
    return *_components.template get<NAME>();
  }

  template <typename NAME>
  void setCase(typename MAP::template value<NAME>& caseRef) {
    static_assert(is_case_v<typename MAP::template value<NAME>>,
                  "Name does not correspond to a CASE");
    this->set<NAME>(caseRef);
    caseRef.setName(NAME{}.name);
  }

  template <typename NAME>
  auto& getCase(NAME) {
    static_assert(is_case_v<typename MAP::template value<NAME>>,
                  "Name does not correspond to a CASE");
    return this->get(NAME{});
  }

  auto& getController() {
    return _controller;
  }

  std::vector<value_t>& getControlVector() override {
    return _controller.get();
  }

  // Set objective evalution routine via a lambda function
  void setObjective(objective_t f) {
    _objective = std::move(f);
  }

  // This overload is required when a free functions is passed
  void setObjective(std::function<value_t(OptiCase<DERIVATIVE, MAP>&)> f) {
    _objective = [this, f](const std::vector<value_t>& control) -> value_t {
      _controller.set(control);
      return f(*this);
    };
  }

  // Set derivative evalution routine
  void setDerivative(derivative_t derivative) {
    _derivative = std::move(derivative);
  }
  // This overload is required when a free functions is passed
  void setDerivative(std::function<std::vector<value_t>(OptiCase<DERIVATIVE, MAP>&)> f) {
    _derivative = [this, f](const std::vector<value_t>& control) -> std::vector<value_t> {
      _controller.set(control);
      return f(*this);
    };
  }

  // Compute objective value, called by the optimizer
  value_t computeObjective(const std::vector<value_t>& control, unsigned optiStep=0) override {
    if (!_objective) {
      throw std::runtime_error("Objective computation is not yet defined.");
    }
    _optimizationStep = optiStep;
    return _objective(control);
  }

  // Compute derivatives, called by the optimizer
  std::vector<value_t> computeDerivatives(const std::vector<value_t>& control, unsigned optiStep=0) override {
    if (!_derivative) {
      throw std::runtime_error("Derivative computation is not yet defined. (Define derivative manually, e.g. for OptiCaseAdjoint)");
    }
    _optimizationStep = optiStep;
    return _derivative(control);
  }

  // Optimization step
  std::size_t getOptimizationStep() {
    return _optimizationStep;
  }
};

/// @brief   OptiCase class specialized for optimizing simulation cases with template specialization for
///          the util::ADf type.
/// @tparam  MAP        Assigns names to cases to distinguish different simualtion types
template <typename MAP>
class OptiCase<derivatives::ADf, MAP>
  : public AbstractOptiCase<ValueTypeFromControlledCase<MAP>> {
public:
  // Get value type and descriptor type from the case map
  using value_t = ValueTypeFromControlledCase<MAP>;
  using adf_value_t = ValueTypeFromDerivativesCase<MAP>;
  using objective_t = std::function<value_t(const std::vector<value_t>&)>;
  using adf_objective_t = std::function<adf_value_t(const std::vector<adf_value_t>&)>;
  using derivative_t = std::function<std::vector<value_t>(const std::vector<value_t>&)>;

  template <typename CASE>
  using ptr_to_case = CASE*;

  template <typename NAME>
  using case_t = MAP::template value<NAME>;

private:
  // Cases stored via non-owning pointers accessed by NAME types
  utilities::TypeIndexedTuple<typename MAP::template map_values<
    ptr_to_case
  >> _cases;

  // Instace for managing control parameters
  Controller<value_t> _controller;
  // Encapsulate logic how to compute objective starting from setting controls
  objective_t _objective;
  // Provide objective function with the ADf type
  adf_objective_t _objectiveD;
  // Encapsulate logic how to compute derivatives starting from setting controls
  derivative_t _derivative;

  std::size_t _optimizationStep = 0;

public:
  OptiCase() : _derivative(derivatives::ADf::getDerivativeF(*this)) { };

  template <typename NAME>
  void setCase(typename MAP::template value<NAME>& caseRef) {
    _cases.template set<NAME>(&caseRef);
    caseRef.setName(NAME{}.name);
  }

  template <typename NAME>
  auto& getCase(NAME) {
    if (_cases.template get<NAME>() == nullptr) {
      throw std::runtime_error("Accessed case was not set.");
    }
    return *_cases.template get<NAME>();
  }

  template <typename VALUE_TYPE>
  auto& getCaseByType() {
    if constexpr (util::is_adf_v<VALUE_TYPE>) {
      return *_cases.template get<names::Derivatives>();
    } else {
      return *_cases.template get<names::Controlled>();
    }
  }

  // Returns only-read Control instance with ADf type
  // TODO Introduce concept::ForwardAD TYPE checking the requirement
  template <typename VALUE_TYPE> requires (util::is_adf_v<VALUE_TYPE>)
  const Controller<adf_value_t> getController() {
    std::vector<adf_value_t> controls = util::copyAs<adf_value_t>(_controller.get());
    util::iniDiagonal(controls);
    return Controller<adf_value_t>{controls};
  }
  // Fallback case if TYPE is not ADf type
  template <typename VALUE_TYPE>
  Controller<VALUE_TYPE>& getController() {
    return getController();
  }
  // Default case
  Controller<value_t>& getController() {
    return _controller;
  }

  std::vector<value_t>& getControlVector() override {
    return _controller.get();
  }

  // Set objective evalution routine
  void setObjective(objective_t f,
                    adf_objective_t df) {
    _objective = std::move(f);
    _objectiveD = std::move(df);
  }
  // This overload is required when a free functions is passed
  void setObjective(std::function<value_t(OptiCase<derivatives::ADf,MAP>&)> f,
                    std::function<adf_value_t(OptiCase<derivatives::ADf,MAP>&)> df) {
    _objective = [this, f](const std::vector<value_t>& control) -> value_t {
      _controller.set(control);
      return f(*this);
    };
    _objectiveD = [this, df](const std::vector<adf_value_t>& control) -> adf_value_t {
      _controller.set(util::copyAs<value_t>(control));
      return df(*this);
    };
  }

  // Compute objective value, called by the optimizer
  value_t computeObjective(const std::vector<value_t>& control, unsigned optiStep=0) override {
    if (!_objective) {
      throw std::runtime_error("Objective computation is not yet defined.");
    }
    _optimizationStep = optiStep;
    return _objective(control);
  }

  // Evaluate objective computation with the ADf type
  template <typename VALUE_TYPE> requires (util::is_adf_v<VALUE_TYPE>)
  adf_value_t computeObjective(const std::vector<adf_value_t>& control) {
    if (!_objectiveD) {
      throw std::runtime_error("Objective computation (with ADf) is not yet defined.");
    }
    return _objectiveD(control);
  }

  // Fallback for the objective computation
  template <typename VALUE_TYPE>
  VALUE_TYPE computeObjective(const std::vector<VALUE_TYPE>& control) {
    return computeObjective(control);
  }

  // Compute derivatives, called by the optimizer
  std::vector<value_t> computeDerivatives(const std::vector<value_t>& control, unsigned optiStep=0) override {
    if (!_derivative) {
      throw std::runtime_error("Derivative computation is not yet defined. (Define derivative manually, e.g. for OptiCaseAdjoint)");
    }
    _optimizationStep = optiStep;
    return _derivative(control);
  }

  // Optimization step
  std::size_t getOptimizationStep() {
    return _optimizationStep;
  }
};

template <typename... MAP>
using OptiCaseFDQ = OptiCase<derivatives::FDQ, meta::map<MAP...>>;

template <typename... MAP>
using OptiCaseCDQ = OptiCase<derivatives::CDQ, meta::map<MAP...>>;

template <typename... MAP>
using OptiCaseAdjoint = OptiCase<derivatives::Manual, meta::map<MAP...>>;

template <typename... MAP>
using OptiCaseADf = OptiCase<derivatives::ADf,meta::map<MAP...>>;

template <unsigned N, typename... MAP>
using OptiCaseADfFromDim = OptiCase<
  derivatives::ADf,
  std::conditional_t<
    meta::map<MAP...>::template contains_key<names::Derivatives>(), // condition: if Derivatives exist
    meta::map<MAP...>, // then do nothing
    meta::map<MAP...,  // if not, extend the map
              names::Derivatives, typename meta::map<MAP...>::template value<names::Controlled>
                                                            ::template exchange_value_t<util::ADf<
                typename meta::map<MAP...>::template value<names::Controlled>::reference_component_t::value_t, N
                                                                                                    >
                                                                                          >
             >
  >
>;

// Wrapper class for analytical functions to pass to OptiCase
template <typename T>
class FunctionCase {
private:
  struct Discretization {
    using value_t = T;
  };

public:
  using reference_component_t = Discretization;
};

template <typename T, typename DERIVATIVE>
using OptiCaseAnalytical = std::conditional_t<
  util::is_adf_v<T>,
  OptiCase<derivatives::ADf, meta::map<names::Controlled, FunctionCase<BaseType<T>>,
                                       names::Derivatives, FunctionCase<T>>>,
  OptiCase<DERIVATIVE, meta::map<names::Controlled, FunctionCase<T>>>
>;

} // namespace opti

} // namespace olb

#endif
