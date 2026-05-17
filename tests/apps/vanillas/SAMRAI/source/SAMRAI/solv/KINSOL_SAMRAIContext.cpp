/*************************************************************************
 *
 * This file is part of the SAMRAI distribution.  For full copyright
 * information, see COPYRIGHT and LICENSE.
 *
 * Copyright:     (c) 1997-2026 Lawrence Livermore National Security, LLC
 * Description:   KINSOL solver for use within a SAMRAI-based application.
 *
 ************************************************************************/
#include "SAMRAI/solv/KINSOL_SAMRAIContext.h"

#ifdef HAVE_SUNDIALS

#include "SAMRAI/solv/Sundials_SAMRAIVector.h"
#include "SAMRAI/tbox/Utilities.h"

namespace SAMRAI {
namespace solv {

const int KINSOL_SAMRAIContext::SOLV_KINSOL_SAMRAI_CONTEXT_VERSION = 1;

/*
 *************************************************************************
 *
 * Constructor and destructor for KINSOL_SAMRAIContext.  The
 * constructor sets default values for data members, then overrides
 * them with values read from input or restart.  The C++ wrapper for
 * KINSOL is also created in the constructor.  The destructor destroys
 * the wrappers for KINSOL and the solution vector.
 *
 *************************************************************************
 */

KINSOL_SAMRAIContext::KINSOL_SAMRAIContext(
   const std::string& object_name,
   KINSOLAbstractFunctions* my_functions,
   const std::shared_ptr<tbox::Database>& input_db):
   d_object_name(object_name),
   d_KINSOL_solver(new KINSOLSolver(object_name, my_functions, 0, 0)),
   d_solution_vector(0),
   d_residual_stop_tolerance(-1.0),
   d_max_nonlinear_iterations(200),
   d_max_krylov_dimension(10),
   d_global_newton_strategy(0),
   d_max_newton_step(-1.0),
   d_nonlinear_step_tolerance(-1.0),
   d_relative_function_error(-1.0),
   d_linear_convergence_test(3),
   d_max_subsetup_calls(5),
   d_residual_monitoring_constant(0.0),
   d_linear_solver_constant_tolerance(0.1),
   d_max_solves_no_precond_setup(10),
   d_max_linear_solve_restarts(0),
   d_KINSOL_print_flag(0),
   d_no_min_eps(false),
   d_uses_preconditioner(false),
   d_uses_jac_times_vector(false)
{
   TBOX_ASSERT(!object_name.empty());
   TBOX_ASSERT(my_functions != 0);

   d_residual_monitoring_params[0] = 0.00001;
   d_residual_monitoring_params[1] = 0.9;

   d_eisenstat_walker_params[0] = 2.0;
   d_eisenstat_walker_params[1] = 0.9;

   /*
    * Initialize object with data read from the input and restart databases.
    */
   bool is_from_restart = false;
   if (is_from_restart) {
      getFromRestart();
   }
   getFromInput(input_db, is_from_restart);
}

KINSOL_SAMRAIContext::~KINSOL_SAMRAIContext()
{

   if (d_solution_vector) {
      Sundials_SAMRAIVector::destroySundialsVector(d_solution_vector);
   }
   if (d_KINSOL_solver) {
      delete d_KINSOL_solver;
   }
}

/*
 *************************************************************************
 *
 * Routines to initialize KINSOL solver and solve nonlinear system.
 *
 *************************************************************************
 */

void
KINSOL_SAMRAIContext::initialize(
   const std::shared_ptr<SAMRAIVectorReal<double> >& solution)
{
   TBOX_ASSERT(solution);

   d_solution_vector = Sundials_SAMRAIVector::createSundialsVector(solution);
   d_KINSOL_solver->initialize(d_solution_vector);
}

int
KINSOL_SAMRAIContext::solve()
{
   return d_KINSOL_solver->solve();
}

/*
 *************************************************************************
 *
 * Initialize KINSOL solver and solve nonlinear system from input.
 * Note that all restart values for parameters may be overridden with
 * input values.
 *
 *************************************************************************
 */

void
KINSOL_SAMRAIContext::getFromInput(
   const std::shared_ptr<tbox::Database>& input_db,
   bool is_from_restart)
{
   if (input_db) {
      if (!is_from_restart) {

         d_residual_stop_tolerance =
            input_db->getDoubleWithDefault("residual_stop_tolerance", -1.0);
         d_KINSOL_solver->setResidualStoppingTolerance(
            d_residual_stop_tolerance);

         d_max_nonlinear_iterations =
            input_db->getIntegerWithDefault("max_nonlinear_iterations", 200);
         d_KINSOL_solver->setMaxIterations(d_max_nonlinear_iterations);

         d_max_krylov_dimension =
            input_db->getIntegerWithDefault("max_krylov_dimension", 10);
         d_KINSOL_solver->setMaxKrylovDimension(d_max_krylov_dimension);

         d_global_newton_strategy =
            input_db->getIntegerWithDefault("global_newton_strategy", 0);
         d_KINSOL_solver->setGlobalStrategy(d_global_newton_strategy);

         d_max_newton_step =
            input_db->getDoubleWithDefault("max_newton_step", -1.0);
         d_KINSOL_solver->setMaxNewtonStep(d_max_newton_step);

         d_nonlinear_step_tolerance =
            input_db->getDoubleWithDefault("nonlinear_step_tolerance", -1.0);
         d_KINSOL_solver->setNonlinearStepTolerance(
            d_nonlinear_step_tolerance);

         d_relative_function_error =
            input_db->getDoubleWithDefault("relative_function_error", -1.0);
         d_KINSOL_solver->setRelativeFunctionError(d_relative_function_error);

         d_linear_convergence_test =
            input_db->getIntegerWithDefault("linear_convergence_test", 3);
         d_KINSOL_solver->setLinearSolverConvergenceTest(
            d_linear_convergence_test);

         d_max_subsetup_calls =
            input_db->getIntegerWithDefault("max_subsetup_calls", 5);
         d_KINSOL_solver->setMaxSubSetupCalls(d_max_subsetup_calls);

         if (input_db->keyExists("residual_monitoring_params")) {
            input_db->getDoubleArray("residual_monitoring_params",
               d_residual_monitoring_params, 2);
         }
         d_KINSOL_solver->setResidualMonitoringParams(
            d_residual_monitoring_params[0],
            d_residual_monitoring_params[1]);

         d_residual_monitoring_constant =
            input_db->getDoubleWithDefault("residual_monitoring_constant", 0.0);
         d_KINSOL_solver->setResidualMonitoringConstant(
            d_residual_monitoring_constant);

         d_no_min_eps = input_db->getBoolWithDefault("no_min_eps", false);
         d_KINSOL_solver->setNoMinEps(d_no_min_eps);

         if (input_db->keyExists("eisenstat_walker_params")) {
            input_db->getDoubleArray("eisenstat_walker_params",
               d_eisenstat_walker_params, 2);
         }
         d_KINSOL_solver->setEisenstatWalkerParameters(
            d_eisenstat_walker_params[0],
            d_eisenstat_walker_params[1]);

         d_linear_solver_constant_tolerance =
            input_db->getDoubleWithDefault("linear_solver_constant_tolerance", 0.1);
         d_KINSOL_solver->setLinearSolverConstantTolerance(
            d_linear_solver_constant_tolerance);

         d_max_solves_no_precond_setup =
            input_db->getIntegerWithDefault("max_solves_no_precond_setup", 10);
         d_KINSOL_solver->setMaxStepsWithNoPrecondSetup(
            d_max_solves_no_precond_setup);

         d_max_linear_solve_restarts =
            input_db->getIntegerWithDefault("max_linear_solve_restarts", 0);
         d_KINSOL_solver->setMaxLinearSolveRestarts(
            d_max_linear_solve_restarts);

         d_KINSOL_log_filename =
            input_db->getStringWithDefault("KINSOL_log_filename", "");
         d_KINSOL_print_flag =
            input_db->getIntegerWithDefault("KINSOL_print_flag", 0);
         d_KINSOL_solver->setLogFileData(d_KINSOL_log_filename,
            d_KINSOL_print_flag);

         d_uses_preconditioner =
            input_db->getBoolWithDefault("uses_preconditioner", false);
         d_KINSOL_solver->setPreconditioner(
            (d_uses_preconditioner == false) ? 0 : 1);

         d_uses_jac_times_vector =
            input_db->getBoolWithDefault("uses_jac_times_vector", false);
         d_KINSOL_solver->setJacobianTimesVector(
            (d_uses_jac_times_vector == false) ? 0 : 1);
      } else {
         bool read_on_restart =
            input_db->getBoolWithDefault("read_on_restart", false);
         if (!read_on_restart) {
            return;
         }

         d_residual_stop_tolerance =
            input_db->getDoubleWithDefault("residual_stop_tolerance",
               d_residual_stop_tolerance);
         d_KINSOL_solver->setResidualStoppingTolerance(
            d_residual_stop_tolerance);

         d_max_nonlinear_iterations =
            input_db->getIntegerWithDefault("max_nonlinear_iterations",
               d_max_nonlinear_iterations);
         d_KINSOL_solver->setMaxIterations(d_max_nonlinear_iterations);

         d_max_krylov_dimension =
            input_db->getIntegerWithDefault("max_krylov_dimension",
               d_max_krylov_dimension);
         d_KINSOL_solver->setMaxKrylovDimension(d_max_krylov_dimension);

         d_global_newton_strategy =
            input_db->getIntegerWithDefault("global_newton_strategy",
               d_global_newton_strategy);
         d_KINSOL_solver->setGlobalStrategy(d_global_newton_strategy);

         d_max_newton_step =
            input_db->getDoubleWithDefault("max_newton_step",
               d_max_newton_step);
         d_KINSOL_solver->setMaxNewtonStep(d_max_newton_step);

         d_nonlinear_step_tolerance =
            input_db->getDoubleWithDefault("nonlinear_step_tolerance",
               d_nonlinear_step_tolerance);
         d_KINSOL_solver->setNonlinearStepTolerance(
            d_nonlinear_step_tolerance);

         d_relative_function_error =
            input_db->getDoubleWithDefault("relative_function_error",
               d_relative_function_error);
         d_KINSOL_solver->setRelativeFunctionError(d_relative_function_error);

         d_linear_convergence_test =
            input_db->getIntegerWithDefault("linear_convergence_test",
               d_linear_convergence_test);
         d_KINSOL_solver->setLinearSolverConvergenceTest(
            d_linear_convergence_test);

         d_max_subsetup_calls =
            input_db->getIntegerWithDefault("max_subsetup_calls",
               d_max_subsetup_calls);
         d_KINSOL_solver->setMaxSubSetupCalls(d_max_subsetup_calls);

         if (input_db->keyExists("residual_monitoring_params")) {
            input_db->getDoubleArray("residual_monitoring_params",
               d_residual_monitoring_params, 2);
         }
         d_KINSOL_solver->setResidualMonitoringParams(
            d_residual_monitoring_params[0],
            d_residual_monitoring_params[1]);

         d_residual_monitoring_constant =
            input_db->getDoubleWithDefault("residual_monitoring_constant",
               d_residual_monitoring_constant);
         d_KINSOL_solver->setResidualMonitoringConstant(
            d_residual_monitoring_constant);

         d_no_min_eps = input_db->getBoolWithDefault("no_min_eps",
               d_no_min_eps);
         d_KINSOL_solver->setNoMinEps(d_no_min_eps);

         if (input_db->keyExists("eisenstat_walker_params")) {
            input_db->getDoubleArray("eisenstat_walker_params",
               d_eisenstat_walker_params, 2);
         }
         d_KINSOL_solver->setEisenstatWalkerParameters(
            d_eisenstat_walker_params[0],
            d_eisenstat_walker_params[1]);

         d_linear_solver_constant_tolerance =
            input_db->getDoubleWithDefault("linear_solver_constant_tolerance",
               d_linear_solver_constant_tolerance);
         d_KINSOL_solver->setLinearSolverConstantTolerance(
            d_linear_solver_constant_tolerance);

         d_max_solves_no_precond_setup =
            input_db->getIntegerWithDefault("max_solves_no_precond_setup",
               d_max_solves_no_precond_setup);
         d_KINSOL_solver->setMaxStepsWithNoPrecondSetup(
            d_max_solves_no_precond_setup);

         d_max_linear_solve_restarts =
            input_db->getIntegerWithDefault("max_linear_solve_restarts",
               d_max_linear_solve_restarts);
         d_KINSOL_solver->setMaxLinearSolveRestarts(
            d_max_linear_solve_restarts);

         d_KINSOL_log_filename =
            input_db->getStringWithDefault("KINSOL_log_filename",
               d_KINSOL_log_filename);
         d_KINSOL_print_flag =
            input_db->getIntegerWithDefault("KINSOL_print_flag",
               d_KINSOL_print_flag);
         d_KINSOL_solver->setLogFileData(d_KINSOL_log_filename,
            d_KINSOL_print_flag);

         d_uses_preconditioner =
            input_db->getBoolWithDefault("uses_preconditioner",
               d_uses_preconditioner);
         d_KINSOL_solver->setPreconditioner(
            (d_uses_preconditioner == false) ? 0 : 1);

         d_uses_jac_times_vector =
            input_db->getBoolWithDefault("uses_jac_times_vector",
               d_uses_jac_times_vector);
         d_KINSOL_solver->setJacobianTimesVector(
            (d_uses_jac_times_vector == false) ? 0 : 1);
      }
   }
}

/*
 *************************************************************************
 *
 * Read data members from restart database.
 *
 *************************************************************************
 */

void
KINSOL_SAMRAIContext::getFromRestart()
{
   /* Checkpoint/restart API removed in vanilla strip 2026-05-15. */
}

/*
 *************************************************************************
 *
 * Write data members to restart database.
 *
 *************************************************************************
 */

void
KINSOL_SAMRAIContext::putToRestart(
   const std::shared_ptr<tbox::Database>& restart_db) const
{
   /* Checkpoint/restart API removed in vanilla strip 2026-05-15. */
}

/*
 *************************************************************************
 *
 * Write all class data members to specified output stream.
 *
 *************************************************************************
 */

void
KINSOL_SAMRAIContext::printClassData(
   std::ostream& os) const
{
   os << "\nKINSOL_SAMRAIContext::printClassData..." << std::endl;
   os << "KINSOL_SAMRAIContext: this = "
      << (KINSOL_SAMRAIContext *)this << std::endl;
   os << "d_object_name = " << d_object_name << std::endl;
   os << "d_KINSOL_solver = " << (KINSOLSolver *)d_KINSOL_solver << std::endl;
   os << "d_solution_vector = "
      << (SundialsAbstractVector *)d_solution_vector;
   os << "\nd_residual_stop_tolerance = " << d_residual_stop_tolerance
      << std::endl;
   os << "d_max_nonlinear_iterations = " << d_max_nonlinear_iterations
      << std::endl;
   os << "d_max_krylov_dimension = " << d_max_krylov_dimension << std::endl;
   os << "d_global_newton_strategy = " << d_global_newton_strategy << std::endl;
   os << "d_max_newton_step = " << d_max_newton_step << std::endl;
   os << "d_nonlinear_step_tolerance = " << d_nonlinear_step_tolerance
      << std::endl;
   os << "d_relative_function_error = " << d_relative_function_error
      << std::endl;
   os << "\nd_linear_convergence_test = " << d_linear_convergence_test
      << std::endl;
   os << "d_eisenstat_walker_params = "
      << d_eisenstat_walker_params[0] << " , "
      << d_eisenstat_walker_params[1] << std::endl;
   os << "d_linear_solver_constant_tolerance = "
      << d_linear_solver_constant_tolerance << std::endl;
   os << "d_max_solves_no_precond_setup = " << d_max_solves_no_precond_setup;
   os << "\nd_max_linear_solve_restarts = " << d_max_linear_solve_restarts;
   os << "\nd_KINSOL_log_filename = " << d_KINSOL_log_filename << std::endl;
   os << "d_KINSOL_print_flag = " << d_KINSOL_print_flag << std::endl;

}

}
}

#endif
