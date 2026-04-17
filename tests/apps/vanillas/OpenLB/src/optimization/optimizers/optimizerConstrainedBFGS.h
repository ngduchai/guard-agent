/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Felix Schuhmann
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
 * The description of the constrained BFGS optimization algorithm -- header file.
 */

#ifndef OPTIMIZER_CONSTRAINEDBFGS_H
#define OPTIMIZER_CONSTRAINEDBFGS_H

#include "optimizer.h"
#include "optimizer.hh"
#include "optimizerLineSearch.h"
#include "optimizerLBFGS.h"

#ifdef NLOPT
#include "nlopt.hpp"
#endif

// All OpenLB code is contained in this namespace.
namespace olb {

/// All optimization code is contained in this namespace.
namespace opti {

namespace solver {

template <typename S, std::size_t D, template <typename> typename C=util::StdVector> class OptiCaseAD;

}
/// Optimization algorithm: LineSearch.
/// Optimization algorithm: LBFGS.
/** OptimizerConstrainedBFGS optimizes an optimization problem
 * which is given in OptiCase. OptiCase provides therefore
 * methods to evaluate an object functional and compute derivatives.
 *
 * Inequality side conditions can be imposed by passing instances of
 * Constraint to the optimizer using the addConstraint() function.
 * Constraint contains a function c(x) defined in terms of the control variables x.
 * The Constraint is fulfilled at all control variables for which the function
 * returns a nonpositive value, c(x) <= 0.
 *
 * The algorithm is based on
 * Curtis et al.: "A BFGS-SQP method for nonsmooth, nonconvex, constrained
 *                 optimization and its evaluation using relative minimization profiles"
 *
 * ConstrainedBFGS computes the direction and step length from modified
 * objective functions which contain a penalty term for violated constraints
 * and a penalty parameter for balancing optimization and fulfilling the
 * constraints.
 *
 * A BFGS inverse Hessian approximation is used in search direction computation.
 *
 * This class is not intended to be derived from.
 */

/// Abstract base class for side conditions of optimization problems
// provides constraint evaluation and gradient computation
template <typename S, typename C>
class Constraint{
public:
  Constraint() = default;

  virtual S evaluateConstraint(const C& control);
  virtual void computeDerivatives (const C& control, C& derivatives);
};


/// Gradients are just passed as a function (and not computed by an own routine)
template <typename S, typename C>
class ConstraintAnalytical : public Constraint<S, C> {

protected:
  std::function<S (const C&)>         _function;
  std::function<void (const C&, C&)>  _derivative;

public:
  ConstraintAnalytical(
    std::function<S (const C&)>         function,
    std::function<void (const C&, C&)>  derivative)
   : Constraint<S, C>(), _function(function), _derivative(derivative)
  { }

  S evaluateConstraint(const C& control) override {
    return _function(control);
  }

  void computeDerivatives(const C& control, C& derivatives) override {
    _derivative(derivatives, control);
  }
};

/// Gradient computed through ADf
template<typename S, std::size_t dimCtrl,
  template<typename> typename C = util::StdVector>
class ConstraintAD : public Constraint<S, C<S>>{
protected:
  using T = util::ADf<S,dimCtrl>;
  std::function<S (const C<S>&)> _function;
  std::function<T (const C<T>&)> _adFunction;

public:
  explicit ConstraintAD() = default;

  ConstraintAD(
    std::function<S (const C<S>&)> function,
    std::function<T (const C<T>&)> adFunction)
   : Constraint<S, C<S>>(), _function(function), _adFunction(adFunction)
  { }

  S evaluateConstraint(const C<S>& control) override
  {
    return _function(control);
  }

  void computeDerivatives(const C<S>& control, C<S>& derivatives) override
  {
    auto adControl = util::iniAD<dimCtrl,S,C>(control);

    const T adResult = _adFunction(adControl);

    for(std::size_t iDim = 0; iDim < control.size(); ++iDim){
      derivatives[iDim] = adResult.d(iDim);
    }
  }
};


// Floating point type S, number of constraints including constant lower / upper bounds, container type C<S>
template<typename S, std::size_t totalDimConstr, typename C>
class OptimizerConstrainedBFGS : public Optimizer<S,C> {

private:
  mutable OstreamManager clout;

protected:
  /// Number of constraints other than bounds
  int _dimConstr;
  /// Penalty parameter, must be > 0
  // higher -> faster optimization but more likely that solution violates constraints
  S _mu;
  /// Temporary penalty parameter for sqpSteeringStrategy()
  S _muTmp;
  /// BFGS inverse hessian approximation used to solve quadratic subproblem for search direction
  S** _H;

  /// Can contain several inequality constraints c_i(x) <= 0, constraints must be differentiable at least once
  std::vector<std::unique_ptr<Constraint<S,C>>*> _constraints;
  /// Constraint values at current iterate
  std::vector<S> _constraintVal;
  /// ith entry stores gradient of ith constraint, excluding bound constraints
  std::vector<C> _constraintGrad;
  /// Constraint violation at current iterate
  S _violation;
  /// Penalty function value at current iterate
  S _penalty;
  /// Penalty function gradient at current iterate
  C _penaltyGrad;

  /// Check if above containers of function values have been updated to values at this->_control
  bool _updatedObjective = false;
  bool _updatedObjectiveGrad = false;
  bool _updatedConstraints = false;
  bool _updatedConstraintGrad = false;
  bool _updatedViolation = false;
  bool _updatedPenalty = false;
  bool _updatedPenaltyGrad = false;

  /// Constant constraints (lower/upper bounds) for each control dimension, currently used instead of bound vectors of Optimizer
  C _lowerBoundVec;
  C _upperBoundVec;

  /// Search direction
  C _direction;
  /// Starting step length for line search, same in every optimization step
  S _stepLengthStart;
  /// Store last iterate and derivative to compute BFGS update
  C _lastControl;
  C _lastDerivative;

  /// Maximal number of step attempts for conditioned line search
  int _maxStepAttempts;
  /// Maximal number of decreasing penalty parameter in one iteration
  int _maxSteeringAttempts;

  // Option to document quantities in each optimization step
  bool _csvOutput;
  CSV<S> _objectiveCSV;
  CSV<S> _muCSV;
  CSV<S> _violationCSV;

  // Used to stop optimization after unsuccessful line search, without terminating the whole program with an exit code
  bool _acceptControls;

public:

  /// Construction of an OptimizerConstrainedBFGS
  OptimizerConstrainedBFGS(int dimCtrl, S eps, int maxIt, S stepLength=1.,//S lambda,
                      int maxStepAttempts=20, int maxSteeringAttempts=15, S mu=16., //std::string stepCondition,
                      bool verboseOn=true, const std::string fname="", const std::string logFileName="",
                      bool withUpperBound=false, C upperBound=C(),
                      bool withLowerBound=false, C lowerBound=C(),
                      S controlEps=S(std::numeric_limits<double>::epsilon() ), bool failOnMaxIter = true,
                      std::vector<OptimizerLogType> gplotAnalysis = {}, bool csvOutput = false)
    : Optimizer<S,C>(dimCtrl, eps, maxIt, verboseOn, fname, logFileName, withUpperBound, 0., withLowerBound,  // Ignore bounds of Optimizer and vectorBounds
                   0., false, controlEps, failOnMaxIter, gplotAnalysis),
      clout(std::cout,"OptimizerConstrainedBFGS")
  {
    _maxStepAttempts = maxStepAttempts;
    _maxSteeringAttempts = maxSteeringAttempts;
    _mu = mu;
    _stepLengthStart = stepLength;
    _objectiveCSV = CSV<S>("objectiveValues");
    _muCSV = CSV<S>("muValues");
    _violationCSV = CSV<S>("violationValues");
    _csvOutput = csvOutput;

    _direction = util::ContainerCreator<C>::create(this->_dimCtrl);
    _penaltyGrad = util::ContainerCreator<C>::create(this->_dimCtrl);
    _lastControl = util::ContainerCreator<C>::create(this->_dimCtrl);
    _lastDerivative = util::ContainerCreator<C>::create(this->_dimCtrl);

    _acceptControls = false;

    // Adjust number of total constraints
    _dimConstr = totalDimConstr;
    if(this->_withUpperBound){
      _dimConstr -= this->_dimCtrl;
      _upperBoundVec = upperBound;
    }
    if(this->_withLowerBound){
      _dimConstr -= this->_dimCtrl;
      _lowerBoundVec = lowerBound;
    }

    _mu = util::max(mu, .000001);  // Enforce mu > 0
    _maxStepAttempts = maxStepAttempts;

    // Set initial inverse Hessian approximation to identity matrix
    _H = new S*[this->_dimCtrl];
    for(int iDim1 = 0; iDim1 < this->_dimCtrl; ++iDim1){
      _H[iDim1] = new S[this->_dimCtrl];
      for(int iDim2 = 0; iDim2 < this->_dimCtrl; ++iDim2){
        // Needs to be explicitly initialized to zero, otherwise other values have been stored
        _H[iDim1][iDim2] = 0.;
      }
      _H[iDim1][iDim1] = 1.;
    }
  };

  /// Add another constraint function to list of constraints
  template <typename CONSTRAINT>
  void addConstraint(std::unique_ptr<CONSTRAINT> &constraint){
    _constraints.push_back(&constraint);
  }

  // The following functions are always evaluated at the current control
  /// Compute constraints at current iterate
  void evaluateConstraints(){
    if(this->_verboseOn){
      clout << "Evaluating constraints..." << std::endl;
    }

    _constraintVal.clear();
    // Constant upper bounds
    if(this->_withUpperBound){
      for(int iConstr = 0; iConstr < this->_dimCtrl; ++iConstr){
        _constraintVal.push_back(this->_control[iConstr] - _upperBoundVec[iConstr]);
      }
    }
    // Constant lower bounds
    if(this->_withLowerBound){
      for(int iConstr = 0; iConstr < this->_dimCtrl; ++iConstr){
        _constraintVal.push_back(_lowerBoundVec[iConstr] - this->_control[iConstr]);
      }
    }
    // General constraints
    for(std::size_t iConstr = 0; iConstr < _constraints.size(); ++iConstr){
      _constraintVal.push_back((*_constraints[iConstr])->evaluateConstraint(this->_control));
    }
    _updatedConstraints = true;
  }

  /// Compute gradients of non-bound constraints at current iterate
  void evaluateConstraintGrad(){
    if(this->_verboseOn){
      clout << "Computing constraint derivatives..." << std::endl;
    }
    _constraintGrad.clear();

    // Only recompute gradient for general constraints, all other derivatives are independent of control value
    C tmpGrad = util::ContainerCreator<C>::create(this->_dimCtrl);
    for(std::size_t iConstr = 0; iConstr < _constraints.size(); ++iConstr){
      (*_constraints[iConstr])->computeDerivatives(this->_control,tmpGrad);
      _constraintGrad.push_back(tmpGrad);
    }
    _updatedConstraintGrad = true;
  }

  /// Get j-th derivative of i-th constraint including bounds (Avoids sparsely storing bound derivatives)
  S getConstraintGrad(int i, int j){

    assert((i < (int)totalDimConstr) && (j < this->_dimCtrl));
    int upperBoundIndex = this->_dimCtrl * (int)(this->_withUpperBound);
    int lowerBoundIndex = upperBoundIndex + this->_dimCtrl * (int)(this->_withLowerBound);

    if(i < upperBoundIndex){  // i-th derivative of i-th upper bound is constantly 1, all others 0
      if(i == j){
        return 1.;
      }
      return 0.;
    }
    else if(i < lowerBoundIndex){ // i-th derivative of i-th lower bounds is constantly -1, all others 0
      if(i - upperBoundIndex == j){
        return -1.;
      }
      return 0.;
    }
    else{ // Index does not correspond to bound constraint
      if(!_updatedConstraintGrad){
        evaluateConstraintGrad();
      }
      return _constraintGrad[i - lowerBoundIndex][j];
    }
  }

  /// Compute total constraint violation
  void evaluateViolation(){
    if(this->_verboseOn){
      clout << "Computing constraint violation..." << std::endl;
    }

    // Reset for summation
    _violation = 0;
    // Update _constraintVal to value at this->_control
    if(!_updatedConstraints){
      evaluateConstraints();
    }
    for(std::size_t iConstr = 0; iConstr < totalDimConstr; ++iConstr){
      if(_constraintVal[iConstr] > 0){
        // Sum up values of all violated constraints
        _violation += _constraintVal[iConstr];
      }
    }
    _updatedViolation = true;

    if(this->_verboseOn){
      clout << "Constraint violation = " << _violation << std::endl;
    }
  }

  /// Evaluate penalty function
  // mu*objective(control) + constraint violation(control)
  void evaluatePenalty(){
    if(this->_verboseOn){
      clout << "Evaluating penalty function..." << std::endl;
    }

    // Update values to values at _this->_control
    if(!_updatedObjective){
      this->evaluateObjective(this->_control, this->_value);
      _updatedObjective = true;
    }
    if(!_updatedViolation){
      evaluateViolation();
    }

    // Assemble penalty function
    _penalty = _mu * this->_value + _violation;
    _updatedPenalty = true;

    if(this->_verboseOn){
      clout << "Penalty function = " << _penalty << std::endl;
    }
  }

  /// Compute gradient of penalty function
  void evaluatePenaltyGrad(){
    if(this->_verboseOn){
      clout << "Computing penalty function derivatives..." << std::endl;
    }

    C sum = util::ContainerCreator<C>::create(this->_dimCtrl);

    // Update values to values at _this->_control
    if(!_updatedObjectiveGrad){
      this->computeDerivatives(this->_control, this->_derivative);
      _updatedObjectiveGrad = true;
    }
    if(!_updatedConstraints){
      evaluateConstraints();
    }
    if(!_updatedConstraintGrad){
      evaluateConstraintGrad();
    }

    // Sum gradients of all violated constraints
    for( std::size_t iConstr = 0; iConstr < totalDimConstr; ++iConstr ){
      if( _constraintVal[iConstr] > 0 ){
        for( int iDim = 0; iDim < this->_dimCtrl; ++iDim ){
          // Add gradient of i-th constraint to sum if it is violated
          sum[iDim] += getConstraintGrad(iConstr, iDim);
        }
      }
    }

    for( int iDim = 0; iDim < this->_dimCtrl; ++iDim ){
      _penaltyGrad[iDim] = _mu * (this->_derivative)[iDim] + sum[iDim];
    }
    _updatedPenaltyGrad = true;
  }

  // Compute l_delta( direction, control )
  void predictedViolationReduction(const C& direction, S& result){
    if(this->_verboseOn){
      clout << "Computing predicted violation reduction..." << std::endl;
    }

    result = 0;
    if(!_updatedConstraints){
      evaluateConstraints();
    }
    if(!_updatedConstraintGrad){
      evaluateConstraintGrad();
    }
    if(!_updatedViolation){
      evaluateViolation();
    }

    S dot;

    for(std::size_t iConstr = 0; iConstr < totalDimConstr; ++iConstr){
      dot = 0;

      // Directional derivative of iConstr-th constraint
      for( int iDim = 0; iDim < this->_dimCtrl; ++iDim ){
        dot += getConstraintGrad(iConstr, iDim) * direction[iDim];
      }
      if( _constraintVal[iConstr] + dot > 0 ){
        result = result - _constraintVal[iConstr] - dot;
      }
    }
    result += _violation;
  }

  // Objective function for quadratic subproblem optimizer
  template<typename T>
  T subproblemObjective(std::vector<T> x){
    //clout << "Evaluating quadratic subproblem objective..." << std::endl;

    assert((x.size() == totalDimConstr));
    T result = 0;

    // Precompute tmpVec = mu * grad f + x_i * grad c_i
    std::vector<T> tmpVec;

    for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
      tmpVec.push_back(_muTmp * this->_derivative[iDim]);
    }
    for(std::size_t iConstr = 0; iConstr < totalDimConstr; ++iConstr){
      for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
        tmpVec[iDim] += x[iConstr] * getConstraintGrad(iConstr, iDim);
      }
    }

    // tmpVec^T * H * tmpVec
    for(int iDim1 = 0; iDim1 < this->_dimCtrl; ++iDim1){
      result += 0.5 * tmpVec[iDim1] * _H[iDim1][iDim1] * tmpVec[iDim1];

      // Skip lower triangular indices since H is symmetric
      for(int iDim2 = iDim1 + 1; iDim2 < this->_dimCtrl; ++iDim2){
        result += tmpVec[iDim1] * _H[iDim1][iDim2] * tmpVec[iDim2];
      }
    }

    // Subtract c^T * x
    for(std::size_t iConstr = 0; iConstr < totalDimConstr; ++iConstr){
      result -= _constraintVal[iConstr] * x[iConstr];
    }

    return result;
  }

  //virtual ~OptimizerConstrainedBFGS() { };

  // virtual void computeDirection() = 0;

  /// Optimization step: line search
  void optimizationStep(){
    // Initial evaluations and documentations
    if(this->_it == 0){
      // objective evaluated in optimize()
      this->computeDerivatives(this->_control, this->_derivative);
      _updatedObjective = true;
      _updatedObjectiveGrad = true;
      (this->_optiCase)->postEvaluation();
      if (this->_verboseOn) {
          this->print(this->_it);
      }

      // Evaluate all required functions at start value
      evaluateConstraints();
      evaluateConstraintGrad();
      evaluateViolation();
      evaluatePenalty();
      evaluatePenaltyGrad();

      if(_csvOutput){
        _objectiveCSV.writeDataFile(this->_it, this->_value, 16);
        _muCSV.writeDataFile(this->_it, _mu, 16);
        _violationCSV.writeDataFile(this->_it, _violation, 16);
      }

      // Assert amount of added constraints and bounds is totalDimConstr (currently needed for AD initialization in SQP subproblem)
      assert((_constraintVal.size() == totalDimConstr));
    }

    // Compute search direction and new penalty parameter
    _muTmp = _mu;
    sqpSteeringStrategy();

    if(_muTmp < _mu){
      // If sqpSteeringStrategy lowered penalty param mu, use new mu and compute new function values
      _mu = _muTmp;
      // These values depend on mu and need to be updated
      _updatedPenalty = false;
      _updatedPenaltyGrad = false;

      evaluatePenalty();
      evaluatePenaltyGrad();
    }

    // Save iterate and corresponding derivative before they get updated in line search
    _lastControl = this->_control;
    _lastDerivative = _penaltyGrad;

    // Compute step length, updates iterate and function values
    inexactLinesearch();

    // Update function values for new iterate (currently done automatically in final line search iteration)

    // check if control have changed sufficiently or break from optimization
    this->_controlsConverged = true;
    for (int iDim=0; iDim<this->_dimCtrl; ++iDim) {
      S ave = 0.5 * (_lastControl[iDim] + this->_control[iDim]);
      if (util::abs(ave) > 0) {
        if (util::abs( (_lastControl[iDim] - this->_control[iDim]) / ave) >= this->_controlEps) {
          this->_controlsConverged = false;
          break;
        }
      }  // else control diff is zero anyway
    }
    if (this->_verboseOn) {
      clout << "Controls converged within " << this->_controlEps << ": " << ((this->_controlsConverged) ? "true" : "false") << std::endl;
    }

    updateBFGSMatrix();

    this->_it++;
    if (this->_verboseOn) {
      clout << "[Step " << this->_it << "] <<<<<<<<<< mu = " << _mu << " <<<<<<<<<<" << std::endl;
    }

    // Document values of each iteration
    if(_csvOutput){
      _objectiveCSV.writeDataFile(this->_it, this->_value, 16);
      _muCSV.writeDataFile(this->_it, _mu, 16);
      _violationCSV.writeDataFile(this->_it, _violation, 16);
    }
    if(_acceptControls){
      this->_controlsConverged = true;
    }
  }

  /// Find new search direction and potentially reduce penalty parameter
  // Following Curtis et al.: "A BFGS-SQP method for nonsmooth, nonconvex, constrained optimization and its evaluation using relative minimization profiles"
  void sqpSteeringStrategy(){
    if(this->_verboseOn){
      clout << "========== Starting steering strategy... ==========" << std::endl;
    }
    // Reference direction with maximum constraint violation reduction (only pushing towards feasible iterate)
    C tmpDirection = util::ContainerCreator<C>::create(this->_dimCtrl);

    // Store predicted violation reduction for search directions
    S l_delta;
    S l_delta_tmp;

    /// Determines how much predicted violation reduction is deemed a sufficient amount of progress to accept new search direction
    // Must be between 0 and 1
    S c_v = 0.1;
    /// Factor by which mu is reduced
    // Must be between 0 and 1
    S c_mu = 0.9;

    int steeringAttempt = 0;

    // If there are no constraints, compute standard search direction for unconstrained BFGS
    if((totalDimConstr == 0)
      ){
      for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
        // Reset for summation
        _direction[iDim] = 0;
        for(int iSum = 0; iSum < this->_dimCtrl; ++iSum){
          _direction[iDim] -= _H[iDim][iSum] * _mu * this->_derivative[iSum];
        }
      }
    }
    else{
      // Solve subproblem with muTmp = mu
      solveSubproblem(_direction);
      predictedViolationReduction(_direction, l_delta);
      if(this->_verboseOn){
        clout << "Predicted violation reduction = " << l_delta << std::endl;
        clout << "Constraint violation = " << _violation << std::endl;
      }

      // Apply steering if computed direction does not sufficiently reduce predicted constraint violation
      // Skip if iterate is feasible
      if((l_delta < c_v * _violation) && (_violation > 0))
      {
        _muTmp = 0;
        solveSubproblem(tmpDirection);
        predictedViolationReduction(tmpDirection, l_delta_tmp);

        // Reduce original mu and compute corresponding search direction until sufficient fraction of max constraint violation is reached
        _muTmp = _mu;
        while((l_delta < c_v * l_delta_tmp) && (steeringAttempt < _maxSteeringAttempts)){
          if(this->_verboseOn){
            clout << "Violation reduction not sufficient." << std::endl;
          }
          _muTmp *= c_mu;
          solveSubproblem(_direction);
          predictedViolationReduction(_direction, l_delta);
          if(this->_verboseOn){
            clout << "Predicted violation reduction = " << l_delta << std::endl;
            clout << "Max predicted violation reduction = " << l_delta_tmp << std::endl;
          }
          steeringAttempt++;
        }
      }
    }

    if(this->_verboseOn){
      clout << "Direction and mu accepted." << std::endl;
      clout << "mu = " << _muTmp << std::endl;
      clout << "Direction norm = " << util::euklidN(_direction) << std::endl;
    }
  }


  template <typename T>
  using ADContainer = Vector<T,totalDimConstr>;

  // Called by sqpSteeringStrategy() to solve quadratic subproblems
  void solveSubproblem(C &direction){
    /// Initialize subproblem
    using std::placeholders::_1;
    using U = util::ADf<S,totalDimConstr>;

    std::function<S (const std::vector<S>&)> function =
      std::bind(&OptimizerConstrainedBFGS<S,totalDimConstr,C>::template subproblemObjective<S>, this, _1);
    std::function<U (const std::vector<U>&)> adFunction =
      std::bind(&OptimizerConstrainedBFGS<S,totalDimConstr,C>::template subproblemObjective<U>, this, _1);

    solver::OptiCaseAD<S,totalDimConstr> subOptiCase(
      function, adFunction
    );

    OptimizerLBFGS<S,std::vector<S>> subOptimizer(
      totalDimConstr,         // dimCtrl
      1e-4,                   // eps
      30 + totalDimConstr,    // maxIt
      .1,                      // lambda
      20,                     // maxStepAttempts
      "Wolfe",                // stepCondition
      7,                     // rows in the low-storage Hessian approx
      0.0001,                 // startCoefH (?)
      false,                  // verboseOn
      "",                     // fName
      "",                     // logFileName
      true,                   // withUpperBound
      1.,                     // upperBound
      true,                   // withLowerBound
      0.,                     // lowerBound
      false,                  // vectorBounds
      1e-6,                  // controlEps
      false,                   // failOnMaxIter
      {}                      // gnuplot
    );

    if(this->_verboseOn){
      clout << "Computing direction for mu = " << _muTmp << std::endl;
    }
    // Set start value in the middle of the feasible region for now
    std::vector<S> subControl(totalDimConstr, 0.5);

    subOptimizer.acceptBoundedControl(true);  // Switch to avoid exit codes of OptimizerLineSearch
    subOptimizer.setControl(subControl);
    subOptimizer.optimize(subOptiCase);

    // Get optimization result
    subControl = subOptimizer.getControl();

    // Restore search direction from dual solution
    // -H_k * (mu*grad f(x_k) + c'(x_k)^T * lambda_k)
    C tmpVec = util::ContainerCreator<C>::create(this->_dimCtrl);

    for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
      // Precompute (mu*grad f(x_k) + c'(x_k)^T * lambda_k)
      for(std::size_t iSum = 0; iSum < totalDimConstr; ++iSum){
        tmpVec[iDim] += getConstraintGrad(iSum, iDim) * subControl[iSum];
      }
      tmpVec[iDim] += _muTmp * this->_derivative[iDim];
    }
    for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
      // Reset for summation
      direction[iDim] = 0;

      for(int iSum = 0; iSum < this->_dimCtrl; ++iSum){
        direction[iDim] -= _H[iDim][iSum] * tmpVec[iSum];
      }
    }
  }

  /// Inexact line search for piecewise differentiable functions performed on the penalty function
  // Find new iterate and update function values
  // Iteratively generates decreasingly big intervals [alpha,beta] from which step size is selected
  // Following Lewis & Overton: "Nonsmooth optimization via quasi-Newton methods"
  void inexactLinesearch(){
    if(this->_verboseOn){
      clout << "========== Starting inexact linesearch... ==========" << std::endl;
    }
    S alpha = 0;
    S beta = std::numeric_limits<S>::infinity();

    S s = 0;
    S penaltyDirDeriv = 0;
    S originalVal = _penalty;
    S stepLength = _stepLengthStart;

    // Avoid storing/accessing line search starting point by updating line search iterates through difference in stepLengths * direction
    S stepLengthOld = 0;

    // Values from OptimizerLineSearch
    S c1 = 1e-4;
    S c2 = 0.9;

    for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
      // Reference quantity for Armijo and Wolfe conditions: Derivative of line search objective in search direction
      s += _penaltyGrad[iDim] * _direction[iDim];

      // Set first line search iterate
      this->_control[iDim] += stepLength * _direction[iDim];
    }

    // Control has been changed -> all values need updating
    _updatedObjective = false;
    _updatedObjectiveGrad = false;
    _updatedConstraints = false;
    _updatedConstraintGrad = false;
    _updatedViolation = false;
    _updatedPenalty = false;
    _updatedPenaltyGrad = false;
    evaluatePenalty();

    int stepAttempt = 0;

    while(stepAttempt < _maxStepAttempts){
      if (this->_verboseOn) {
        clout << "[Step " << this->_it << "][Ref " << stepAttempt << "] <<<<<<<<<< lambda = " << stepLength << " <<<<<<<<<<" << std::endl;
        clout << "alpha = " << alpha << ", beta = " << beta << std::endl;
      }
      // Armijo-Wolfe conditions
      if(!(_penalty < originalVal + c1 * s * stepLength)){ // Armijo fails
        if (this->_verboseOn) {
          clout << "Armijo failed!" << std::endl;
        }
        // Decrease upper bound for step length
        beta = stepLength;
      }
      else{
        // Step length is guaranteed to change each iteration -> needs to be recomputed for every Wolfe condition check
        evaluatePenaltyGrad();

        // Compute directional derivative of penalty
        penaltyDirDeriv = 0;
        for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
          penaltyDirDeriv += _penaltyGrad[iDim] * _direction[iDim];
        }

        if(!(penaltyDirDeriv > c2 * s)){  // Wolfe fails
          if (this->_verboseOn) {
            clout << "Curvature failed!" << std::endl;
          }
          // Increase lower bound for stepLength
          alpha = stepLength;
        }
        else{   // Stop once Armijo and Wolfe hold, new optimization iterate is last line search iterate
          if (this->_verboseOn) {
            clout << "Step accepted." << std::endl;
          }
          break;
        }
      }

      // Select step size from interval
      stepLengthOld = stepLength;
      if(!isinf(beta)){
        stepLength = .5 * (alpha + beta);
      }
      else{
        stepLength = 2. * alpha;
      }

      // Leave program if step size becomes to small
      if (util::abs(stepLength) < std::numeric_limits<double>::epsilon()) {
        clout << "lambda=" << stepLength << ", objective value=" << this->_value << ", penalty value=" << _penalty << std::endl;
        clout << "Excessive refinement steps (too small step size).\nProgram terminated." <<std::endl;
        //exit(1);
        _acceptControls = true;
        stepAttempt = _maxStepAttempts;
      }

      // Update line search iterate and penalty value
      // TO DO: add control notSensible check similar to OptimizerLineSearch
      for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
        this->_control[iDim] += (stepLength - stepLengthOld) * _direction[iDim];
      }
      _updatedObjective = false;
      _updatedObjectiveGrad = false;
      _updatedConstraints = false;
      _updatedConstraintGrad = false;
      _updatedViolation = false;
      _updatedPenalty = false;
      _updatedPenaltyGrad = false;
      evaluatePenalty();

      stepAttempt++;
    }

    // Leave program if maximum number of step attempts is exceeded
    if((stepAttempt >= _maxStepAttempts)){
      clout << "Excessive refinement steps (maxStepAttempts exceeded).\nProgram terminated." <<std::endl;
      //exit(1);
      _acceptControls = true;
    }
  }

  // Update standard BFGS Matrix
  // Following Nocedal & Wright: "Numerical Optimization", pp. 136-144
  void updateBFGSMatrix(){
    if (this->_verboseOn) {
      clout << "========== Updating BFGS Matrix... ==========" << std::endl;
    }
    S rho = 0;
    S tmp = 0;

    // Store precomputed dot products to efficiently compute BFGS update
    C tmpProducts = util::ContainerCreator<C>::create(this->_dimCtrl);

    for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
      // Compute latest step and difference in gradients
      // Use _lastControl and _lastDerivative as temporary storage
      _lastControl[iDim] = this->_control[iDim] - _lastControl[iDim];
      _lastDerivative[iDim] = _penaltyGrad[iDim] - _lastDerivative[iDim];

      // Store dot product of latest step (iterate diff) and gradient diff
      rho += _lastControl[iDim] * _lastDerivative[iDim];
    }

    // Scale initial approximation after first step but before first BFGS update
    if(this->_it == 0){
      for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
        tmp += _lastDerivative[iDim] * _lastDerivative[iDim];
      }
      for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
        _H[iDim][iDim] *= rho / tmp;
      }
    }

    // For further calculations
    rho = 1. / rho;

    if(this->_verboseOn){
      clout << "Control difference = " << util::euklidN(_lastControl) << std::endl;
      clout << "Gradient difference = " << util::euklidN(_lastDerivative) << std::endl;
      clout << "rho = " << rho << std::endl;
    }

    // Store dot products with last gradient difference y_k for first part of the BFGS update computation
    for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
      for(int iSum = 0; iSum < this->_dimCtrl; ++iSum){
        tmpProducts[iDim] += _H[iDim][iSum] * _lastDerivative[iSum];
      }
    }
    // Efficient computation of H_k+1 := H_k * (I - rho_k * y_k * s_k^T)
    for(int iDim1 = 0; iDim1 < this->_dimCtrl; ++iDim1){
      for(int iDim2 = 0; iDim2 < this->_dimCtrl; ++iDim2){
        _H[iDim1][iDim2] -= rho * _lastControl[iDim2] * tmpProducts[iDim1];
      }
    }

    // Store dot products with y_k for second part of the computation
    for(int iDim = 0; iDim < this->_dimCtrl; ++iDim){
      tmpProducts[iDim] = 0;
      for(int iSum = 0; iSum < this->_dimCtrl; ++iSum){
        tmpProducts[iDim] += _lastDerivative[iSum] * _H[iSum][iDim];
      }
    }

    // Efficient computation of H_k+1 := (I - rho_k * y_k * s_k^T)^T * H_k+1
    for(int iDim1 = 0; iDim1 < this->_dimCtrl; ++iDim1){
      for(int iDim2 = 0; iDim2 < this->_dimCtrl; ++iDim2){
        _H[iDim1][iDim2] -= rho * _lastControl[iDim1] * tmpProducts[iDim2];
      }
    }

    // H_k+1 := H_k+1 + rho_k * s_k * s_k^T
    for(int iDim1 = 0; iDim1 < this->_dimCtrl; ++iDim1){
      for(int iDim2 = 0; iDim2 < this->_dimCtrl; ++iDim2){
        _H[iDim1][iDim2] += rho * _lastControl[iDim1] * _lastControl[iDim2];
      }
    }
  }
};

#ifdef NLOPT
// =========================== OpenLB wrapper for NLopt optimization ===========================
// NLopt optimization library: http://github.com/stevengj/nlopt
// Uses same constraint classes

/// For passing an OptiCase to `nloptFunction()`
template<typename S, typename C>
struct OptiCaseWrapper{
  OptiCase<S,C>* _optiCase;
  bool _verboseOn;
};

/// For passing a Constraint to `nloptFunction()`
template<typename S, typename C>
struct ConstraintWrapper{
  Constraint<S,C>* _constraint;
  bool _verboseOn;
};

/// Generate NLopt style objective function from OptiCase passed in `f_data`
template<typename S, typename C>
double nloptObjective(const std::vector<double>& x, std::vector<double>& grad, void* f_data){
  OptiCaseWrapper<S,C>* optiCaseWrapper = reinterpret_cast<OptiCaseWrapper<S,C>*>(f_data);
  auto optiCase = optiCaseWrapper->_optiCase;
  auto verboseOn = optiCaseWrapper->_verboseOn; // Use for option to output current value / control?

  C xTmp = util::ContainerCreator<C>::create(x.size());
  // Convert control value currently used by NLopt from std::vector<double> to C
  for( unsigned i = 0; i < x.size(); ++i ){
    xTmp[i] = (S)(x[i]);
  }

  // grad.size() can be 0 on NLopt's final objective evaluation
  if( grad.size() > 0 ){
    assert( (x.size() == grad.size()) );
    C gradTmp = util::ContainerCreator<C>::create(x.size());

    // Compute derivative and convert from C to std::vector<double>
    optiCase->computeDerivatives( xTmp, gradTmp );
    for( unsigned i = 0; i < x.size(); ++i ){
      grad[i] = (double)(gradTmp[i]);
    }
  }

  // Compute function value and adapt data type
  return (double)(optiCase->evaluateObjective( xTmp ));
}

/// Generate NLopt style constraint function from Constraint passed in `f_data`
template<typename S, typename C>
double nloptConstraint(const std::vector<double>& x, std::vector<double>& grad, void* f_data){
  ConstraintWrapper<S,C>* constraintWrapper = reinterpret_cast<ConstraintWrapper<S,C>*>(f_data);
  auto constraint = constraintWrapper->_constraint;
  auto verboseOn = constraintWrapper->_verboseOn;

  C xTmp = util::ContainerCreator<C>::create(x.size());
  // Convert control value currently used by NLopt from std::vector<double> to C
  for( unsigned i = 0; i < x.size(); ++i ){
    xTmp[i] = (S)(x[i]);
  }

  // grad.size() can be 0 on NLopt's final objective evaluation
  if( grad.size() > 0 ){
    assert( (x.size() == grad.size()) );
    C gradTmp = util::ContainerCreator<C>::create(x.size());

    // Compute derivative and convert from C to std::vector<double>
    constraint->computeDerivatives( xTmp, gradTmp );
    for( unsigned i = 0; i < x.size(); ++i ){
      grad[i] = (double)(gradTmp[i]);
    }
  }

  // Compute function value and adapt data type
  return (double)(constraint->evaluateConstraint( xTmp ));
}

template<typename S, typename C>
class OptimizerNLoptBFGS : public Optimizer<S,C> {

private:
  mutable OstreamManager clout;

protected:
  // NLopt optimizer SLSQP
  nlopt::opt _optimizerSLSQP;

  /// Search direction
  C _direction;
  // Upper/Lower bound
  bool _lowerBoundFlag;
  bool _upperBoundFlag;
  /// Maximal number of step attempts for conditioned line search
  int _maxStepAttempts;
  int _maxEvaluations;

public:
  /// Construction of an OptimizerConstrainedBFGS
  OptimizerNLoptBFGS(int dimCtrl, S eps, int maxIt, //S lambda,
                      int maxStepAttempts, //std::string stepCondition,
                      bool verboseOn=true, const std::string fname="", const std::string logFileName="",
                      bool withUpperBound=false, S upperBound=S(),
                      bool withLowerBound=false, S lowerBound=S(), bool vectorBounds=false,
                      S controlEps=S(std::numeric_limits<double>::epsilon() ), bool failOnMaxIter = true,
                      std::vector<OptimizerLogType> gplotAnalysis = {})
    : Optimizer<S,C>(dimCtrl, eps, maxIt, verboseOn, fname, logFileName, withUpperBound, upperBound, withLowerBound,
                   lowerBound, vectorBounds, controlEps, failOnMaxIter, gplotAnalysis),
      clout(std::cout,"OptimizerNLoptBFGS")
  {
    _optimizerSLSQP = nlopt::opt( "LD_SLSQP", (unsigned)(this->_dimCtrl) );   // use abs(dimCtrl) for safer conversion?

    // Bound controls
    if( withLowerBound ){
      _optimizerSLSQP.set_lower_bounds( (double)(this->_lowerBound[0]) );
    }
    if( withUpperBound ){
      _optimizerSLSQP.set_upper_bounds( (double)(this->_upperBound[0]) );
    }
    // Necessary stopping criteria
    _optimizerSLSQP.set_xtol_rel( (double)(this->_controlEps) );
    _optimizerSLSQP.set_ftol_rel( (double)(this->_eps) );
    //std::cout << _optimizerSLSQP.get_xtol_rel() << std::endl;

    _lowerBoundFlag = false;
    _upperBoundFlag = false;
  };

  /// abs(`constraint->_function`) <= `constraintEps`
  void addEqualityConstraint( Constraint<S,C>& constraint, S constraintEps ){
    ConstraintWrapper<S,C> constraintWrapper = { &constraint, this->_verboseOn };
    _optimizerSLSQP.add_equality_constraint( nloptConstraint<S,C>, &constraintWrapper, (double)constraintEps );
  }

  /// `constraint->_function` <= `constraintEps`
  void addInequalityConstraint( Constraint<S,C>& constraint, S constraintEps ){
    ConstraintWrapper<S,C> constraintWrapper = { &constraint, this->_verboseOn };
    _optimizerSLSQP.add_inequality_constraint( nloptConstraint<S,C>, &constraintWrapper, (double)constraintEps );
  }

  // Additional NLopt stopping criteria
  void setMaxEvaluations( int eval ){
    this->_maxEvaluations = eval;
    _optimizerSLSQP.set_maxeval( eval );
  }

  int getMaxEvaluations(){
    return _maxEvaluations;
  }

  int getNumEvaluations(){
    return _optimizerSLSQP.get_numevals();
  }

  int getDimension(){
    return _optimizerSLSQP.get_dimension();
  }

  unsigned getNumParams(){
    return _optimizerSLSQP.num_params();
  }

  void optimize( OptiCase<S,C>& optiCase ) override
  {
    this->_optiCase = &optiCase;
    OptiCaseWrapper<S,C> optiCaseWrapper = { &optiCase, this->_verboseOn };
    _optimizerSLSQP.set_min_objective( nloptObjective<S,C>, &optiCaseWrapper );

    // Evaluate objective function
    this->evaluateObjective(this->_control, this->_value);
    (this->_optiCase)->postEvaluation();

    // Complete NLopt SLSQP procedure
    double tmpValue;
    std::vector<double> tmpControl;
    for(int i = 0; i < this->_dimCtrl; ++i ){
      tmpControl.push_back( (double)(this->_control[i]) );
    }

    try{
      clout << "Starting NLopt optimization..." << std::endl;
      _optimizerSLSQP.nlopt::opt::optimize( tmpControl, tmpValue );
      this->_value = (S)tmpValue;
      for(int i = 0; i < this->_dimCtrl; ++i ){
        this->_control[i] = (S)tmpControl[i];
      }

      clout << "Found minimum with objective value = " << this->_value << std::endl;
    }
    catch(std::exception &e) {
      std::cerr << "nlopt failed: " << e.what() << std::endl;
    }
  }

  /// Optimization step done in NLopt
  void optimizationStep()
  {

  };
};

#endif

} // namespace opti

} // namespace olb

#endif
