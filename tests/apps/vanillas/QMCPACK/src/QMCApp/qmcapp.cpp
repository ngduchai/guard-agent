//////////////////////////////////////////////////////////////////////////////////////
// This file is distributed under the University of Illinois/NCSA Open Source License.
// See LICENSE file in top directory for details.
//
// Copyright (c) 2020 QMCPACK developers.
//
// File developed by: Ken Esler, kpesler@gmail.com, University of Illinois at Urbana-Champaign
//                    Luke Shulenburger, lshulen@sandia.gov, Sandia National Laboratories
//                    Jeremy McMinnis, jmcminis@gmail.com, University of Illinois at Urbana-Champaign
//                    Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//                    Ying Wai Li, yingwaili@ornl.gov, Oak Ridge National Laboratory
//                    Mark Dewing, markdewing@gmail.com, University of Illinois at Urbana-Champaign
//                    Ye Luo, yeluo@anl.gov, Argonne National Laboratory
//                    Mark A. Berrill, berrillma@ornl.gov, Oak Ridge National Laboratory
//
// File created by: Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//////////////////////////////////////////////////////////////////////////////////////

#include <stdexcept>
#include <memory>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include "Configuration.h"
#include "Message/Communicate.h"
#include "Utilities/SimpleParser.h"
#include "Utilities/ProgressReportEngine.h"
#include "Platforms/Host/OutputManager.h"
#include "OhmmsData/FileUtility.h"
#include "Host/sysutil.h"
#include "ProjectData.h"
#include "QMCApp/QMCMain.h"
#include "Utilities/qmc_common.h"

#include <array>

void output_hardware_info(Communicate* comm, Libxml2Document& doc, xmlNodePtr root);

/** @file qmcapp.cpp
 *@brief a main function for QMC simulation.
 *
 * @ingroup qmcapp
 * @brief main function for qmcapp executable.
 *
 *Actual works are done by QMCAppBase and its derived classe.
 *For other simulations, one can derive a class from QMCApps, similarly to MolecuApps.
 */
int main(int argc, char** argv)
{
  using namespace qmcplusplus;
#ifdef HAVE_MPI
  mpi3::environment env(argc, argv);
  OHMMS::Controller = new Communicate(env.world());
#endif
  try
  {
    //qmc_common  and MPI is initialized
    qmcplusplus::qmc_common.initialize(argc, argv);
    std::vector<std::string> fgroup_names_cmd, fgroup_names_txt;
    int i = 1;
    while (i < argc)
    {
      std::string c(argv[i]);
      if (c[0] == '-')
      {
        if (c == "-debug")
          ReportEngine::enableOutput();

        // Default setting is 'timer_level_coarse'
        if (c.find("-enable-timers") < c.size())
        {
#ifndef ENABLE_TIMERS
          std::cerr
              << "The '-enable-timers' command line option will have no effect. This executable was built without "
                 "ENABLE_TIMER set."
              << std::endl;
#endif
          int pos = c.find("=");
          if (pos != std::string::npos)
          {
            std::string timer_level = c.substr(pos + 1);
            getGlobalTimerManager().set_timer_threshold(timer_level);
          }
        }
        if (c.find("-verbosity") < c.size())
        {
          int pos = c.find("=");
          if (pos != std::string::npos)
          {
            std::string verbose_level = c.substr(pos + 1);
            if (verbose_level == "low")
            {
              outputManager.setVerbosity(Verbosity::LOW);
            }
            else if (verbose_level == "high")
            {
              outputManager.setVerbosity(Verbosity::HIGH);
            }
            else if (verbose_level == "debug")
            {
              outputManager.setVerbosity(Verbosity::DEBUG);
            }
            else
            {
              std::cerr << "Unknown verbosity level: " << verbose_level << std::endl;
            }
          }
        }
      }
      else
      {
        if (c.find(".xml") == c.size() - 4)
          fgroup_names_cmd.push_back(argv[i]);
        else
        {
          std::ifstream fin(argv[i], std::ifstream::in);
          bool valid = !fin.fail();
          while (valid)
          {
            std::vector<std::string> words;
            getwords(words, fin);
            if (words.size())
            {
              if (words[0].find(".xml") == words[0].size() - 4)
                  fgroup_names_txt.push_back(words[0]);
            }
            else
              valid = false;
          }
        }
      }
      ++i;
    }
    std::vector<std::string> inputs(fgroup_names_cmd.size() + fgroup_names_txt.size());
    copy(fgroup_names_txt.begin(), fgroup_names_txt.end(), inputs.begin());
    i = fgroup_names_txt.size();
    for (int k = 0; k < fgroup_names_cmd.size(); ++k)
      inputs[i++] = fgroup_names_cmd[k];
    if (inputs.empty())
    {
      if (OHMMS::Controller->rank() == 0)
      {
        std::cerr << "No valid input file is given." << std::endl;
        std::cerr << "Usage: qmcpack [options] <input-files.xml> " << std::endl;
        std::cerr << "Ensemble runs may be initialized by specifying either multiple .xml files or text files "
                     "containing lists of .xml input files."
                  << std::endl;
      }
      OHMMS::Controller->finalize();
      return 1;
    }
    //safe to move on
    Communicate* qmcComm = OHMMS::Controller;
    if (inputs.size() > 1)
    {
      if (inputs.size() > OHMMS::Controller->size())
      {
        std::ostringstream msg;
        msg << "main(). Current " << OHMMS::Controller->size() << " MPI ranks cannot accommodate all the "
            << inputs.size() << " individual calculations in the ensemble. "
            << "Increase the number of MPI ranks or reduce the number of calculations." << std::endl;
        OHMMS::Controller->barrier_and_abort(msg.str());
      }
      qmcComm               = new Communicate(*OHMMS::Controller, inputs.size());
      qmc_common.mpi_groups = inputs.size();
    }
    std::stringstream logname;
    int inpnum          = (inputs.size() > 1) ? qmcComm->getGroupID() : 0;
    std::string myinput = inputs[qmcComm->getGroupID()];
    myinput             = myinput.substr(0, myinput.size() - 4);
    logname << myinput;

    if (qmcComm->rank() != 0)
    {
      outputManager.shutOff();
      // might need to redirect debug stream to a file per rank if debugging is enabled
    }
    if (inputs.size() > 1 && qmcComm->rank() == 0)
    {
      std::array<char, 128> fn;
      if (std::snprintf(fn.data(), fn.size(), "%s.g%03d.qmc", logname.str().c_str(), qmcComm->getGroupID()) < 0)
        throw std::runtime_error("Error generating filename");
      infoSummary.redirectToFile(fn.data());
      infoLog.redirectToSameStream(infoSummary);
      infoError.redirectToSameStream(infoSummary);
    }

    bool validInput = false;
    app_log() << "  Input file(s): ";
    for (int k = 0; k < inputs.size(); ++k)
      app_log() << inputs[k] << " ";
    app_log() << std::endl;

    auto qmc = std::make_unique<QMCMain>(qmcComm);

    if (inputs.size() > 1)
      validInput = qmc->parse(inputs[qmcComm->getGroupID()]);
    else
      validInput = qmc->parse(inputs[0]);

    if (!validInput)
      qmcComm->barrier_and_abort("main(). Input invalid.");

    bool qmcSuccess = qmc->execute();
    if (!qmcSuccess)
      qmcComm->barrier_and_abort("main(). QMC Execution failed.");

    /* Step 0 v9 (QMCPACK-A 2026-05-21): augment the binary validation
     * signature with a 7th double — the trajectory hash — so the
     * comparator is sensitive to input perturbation (required by the
     * v2.2 cold-replay detector; calibrator's output_sensitivity_ok
     * invariant was unsatisfiable under v8 because the prior 6 doubles
     * were config-only and invariant under any non-crashing perturbation).
     *
     * Writes 8 raw doubles (64 bytes) to "validation_output.bin" in CWD
     * on rank 0:
     *   [0] (double)qmcComm->size()              (MPI ranks)
     *   [1] (double)inputs.size()                (number of <qmc> input files)
     *   [2] (double)(qmcSuccess ? 1.0 : 0.0)     (always 1.0 if we reach the dump)
     *   [3] (double)argc                         (command-line arg count)
     *   [4] (double)series_count                 (number of <title>.s*.scalar.dat files)
     *   [5] (double)block_count                  (total LocalEnergy rows across all .scalar.dat files)
     *   [6] (double)trajectory_sum               (sum of column 1 'LocalEnergy' across every block of every series)
     *   [7] (double)0.0                          (reserved)
     *
     * The trajectory_sum is computed BY the simulation (not derivable from
     * the input file alone): the linear optimizer reads the starting
     * Jastrow B and converges over 60 loop iterations, producing a
     * trajectory whose per-block LocalEnergy values depend on B.  Reading
     * the .scalar.dat files post-execute() is a passive observation, not
     * an intercept on the optimizer.  Determinism across runs is
     * enforced by the <random seed=.../> element in the input XML; per-app
     * patch overlay and v2.2 perturbation regex preserve the seed line.
     *
     * Rank-root-only.
     */
    if (OHMMS::Controller->rank() == 0) {
      double sig_buf[8];
      sig_buf[0] = static_cast<double>(qmcComm->size());
      sig_buf[1] = static_cast<double>(inputs.size());
      sig_buf[2] = qmcSuccess ? 1.0 : 0.0;
      sig_buf[3] = static_cast<double>(argc);

      double trajectory_sum = 0.0;
      int series_count = 0;
      int block_count = 0;
      const std::string title = qmc->getTitle();
      const std::string suffix = ".scalar.dat";
      try {
        for (const auto& entry : std::filesystem::directory_iterator(".")) {
          if (!entry.is_regular_file()) continue;
          const auto fname = entry.path().filename().string();
          // Match <title>.s###.scalar.dat — title prefix, '.s' marker, suffix.
          if (fname.size() < title.size() + suffix.size() + 5) continue;
          if (fname.compare(0, title.size(), title) != 0) continue;
          if (fname.compare(fname.size() - suffix.size(), suffix.size(), suffix) != 0) continue;
          if (fname[title.size()] != '.' || fname[title.size() + 1] != 's') continue;
          series_count++;
          std::ifstream f(entry.path());
          std::string line;
          while (std::getline(f, line)) {
            if (line.empty() || line[0] == '#') continue;
            std::istringstream iss(line);
            double idx, energy;
            if (iss >> idx >> energy) {
              trajectory_sum += energy;
              block_count++;
            }
          }
        }
      } catch (const std::exception& e) {
        // Filesystem traversal failure: emit zeros so the comparator
        // surfaces a mismatch instead of silently passing.
        std::cerr << "WARN: trajectory_sum scan failed: " << e.what() << std::endl;
        trajectory_sum = 0.0;
        series_count = 0;
        block_count = 0;
      }
      sig_buf[4] = static_cast<double>(series_count);
      sig_buf[5] = static_cast<double>(block_count);
      sig_buf[6] = trajectory_sum;
      sig_buf[7] = 0.0;

      FILE* sig_f = std::fopen("validation_output.bin", "wb");
      if (sig_f) {
        std::fwrite(sig_buf, sizeof(double), 8, sig_f);
        std::fclose(sig_f);
      }
    }

    Libxml2Document timingDoc;
    timingDoc.newDoc("resources");
    output_hardware_info(qmcComm, timingDoc, timingDoc.getRoot());
    getGlobalTimerManager().output_timing(qmcComm, timingDoc, timingDoc.getRoot());
    qmc->getParticlePool().output_particleset_info(timingDoc, timingDoc.getRoot());
    if (OHMMS::Controller->rank() == 0)
    {
      timingDoc.dump(qmc->getTitle() + ".info.xml");
    }
    getGlobalTimerManager().print(qmcComm);

    qmc.reset();
  }
  catch (const std::exception& e)
  {
    std::cerr << e.what() << std::endl;
    APP_ABORT("Unhandled Exception");
  }
  catch (...)
  {
    APP_ABORT("Unhandled Exception (not derived from std::exception)");
  }

  if (OHMMS::Controller->rank() == 0)
    std::cout << std::endl << "QMCPACK execution completed successfully" << std::endl;

  OHMMS::Controller->finalize();

  return 0;
}

void output_hardware_info(Communicate* comm, Libxml2Document& doc, xmlNodePtr root)
{
  xmlNodePtr hardware = doc.addChild(root, "hardware");

  bool using_mpi = false;
#ifdef HAVE_MPI
  using_mpi = true;
  doc.addChild(hardware, "mpi_size", comm->size());
#endif
  doc.addChild(hardware, "mpi", using_mpi);

  bool using_openmp = false;
#ifdef _OPENMP
  using_openmp = true;
  doc.addChild(hardware, "openmp_threads", omp_get_max_threads());
#endif
  doc.addChild(hardware, "openmp", using_openmp);
}
