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
#include <vector>

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

    /* Step 0 v9.1 (QMCPACK-B 2026-05-24): widen the STATE-derived signature
     * from a single trajectory column (LocalEnergy only) to four MPI-meaningful
     * accumulators (LocalEnergy, Kinetic, LocalPotential, BlockWeight) so a
     * resilient cold-replay that drifts in any energy-flavoured channel — not
     * just total energy — diverges on the comparator.  Replaces v9 schema
     * whose 6/8 slots were config-only echo (qmcComm size, inputs size,
     * qmcSuccess flag, argc) — half the comparator surface was therefore
     * tautological.
     *
     * Writes 8 raw doubles (64 bytes) to "validation_output.bin" in CWD on
     * rank 0:
     *   [0] (double)qmcComm->size()      MPI rank count        (config sanity)
     *   [1] (double)inputs.size()        <qmc> input file count(config sanity)
     *   [2] (double)(qmcSuccess?1:0)     reached-dump flag     (config sanity)
     *   [3] sum(BlockWeight)             total walker-steps    (STATE)
     *   [4] sum(LocalEnergy)             trajectory energy sum (STATE)
     *   [5] sum(Kinetic)                 kinetic-energy sum    (STATE)
     *   [6] sum(LocalPotential)          potential-energy sum  (STATE)
     *   [7] (double)block_count          completed blocks      (STATE)
     *
     * Parser strategy: read the .scalar.dat header line (`#  index  Name1
     * Name2 ...`) and resolve LocalEnergy/Kinetic/LocalPotential/BlockWeight
     * to per-file column indices.  This tolerates per-system column layout
     * variation (e.g. He uses 'Coulomb', heavy systems use 'IonElec'/'IonIon').
     * Missing columns are skipped silently and contribute zero — the comparator
     * still discriminates on the surviving columns.  Reading post-execute()
     * is a passive observation, not an intercept on the optimizer.  Per-block
     * values depend on RNG seed (preserved via patch overlay) and on starting
     * Jastrow B (perturbed by the v2.2 cold-replay detector).
     *
     * Comparator: tests/apps/configs/QMCPACK.yaml comparison.method =
     * numeric-tolerance, tolerance preserved.  Slots [3..7] react to
     * RNG/Jastrow drift; cold-replayed (re-seeded or block-skipped) runs
     * produce different trajectories and diverge.
     *
     * Rank-root-only.
     */
    if (OHMMS::Controller->rank() == 0) {
      double sig_buf[8];
      sig_buf[0] = static_cast<double>(qmcComm->size());
      sig_buf[1] = static_cast<double>(inputs.size());
      sig_buf[2] = qmcSuccess ? 1.0 : 0.0;

      double sum_local_energy = 0.0;
      double sum_kinetic = 0.0;
      double sum_local_potential = 0.0;
      double sum_block_weight = 0.0;
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

          std::ifstream f(entry.path());
          std::string line;
          // Per-file column indices (resolved from header line).
          int idx_le = -1, idx_kin = -1, idx_lp = -1, idx_bw = -1;
          bool header_seen = false;

          while (std::getline(f, line)) {
            if (line.empty()) continue;
            if (line[0] == '#') {
              if (!header_seen) {
                // Header format: "#   index   Name1   Name2   ..."
                // Skip the leading '#'; columns are whitespace-separated.
                std::istringstream hiss(line.substr(1));
                std::string tok;
                int col = -1;  // 'index' is column 0 of data rows
                while (hiss >> tok) {
                  if (tok == "index") { col = 0; continue; }
                  ++col;
                  if (tok == "LocalEnergy")    idx_le  = col;
                  else if (tok == "Kinetic")        idx_kin = col;
                  else if (tok == "LocalPotential") idx_lp  = col;
                  else if (tok == "BlockWeight")    idx_bw  = col;
                }
                header_seen = true;
              }
              continue;
            }
            // Data row: parse all whitespace-separated doubles, index by column.
            std::istringstream diss(line);
            std::vector<double> row;
            double v;
            while (diss >> v) row.push_back(v);
            if (row.empty()) continue;
            ++block_count;
            if (idx_le  >= 0 && (size_t)idx_le  < row.size()) sum_local_energy    += row[idx_le];
            if (idx_kin >= 0 && (size_t)idx_kin < row.size()) sum_kinetic         += row[idx_kin];
            if (idx_lp  >= 0 && (size_t)idx_lp  < row.size()) sum_local_potential += row[idx_lp];
            if (idx_bw  >= 0 && (size_t)idx_bw  < row.size()) sum_block_weight    += row[idx_bw];
          }
        }
      } catch (const std::exception& e) {
        // Filesystem traversal failure: emit zeros so the comparator
        // surfaces a mismatch instead of silently passing.
        std::cerr << "WARN: scalar.dat scan failed: " << e.what() << std::endl;
        sum_local_energy = 0.0;
        sum_kinetic = 0.0;
        sum_local_potential = 0.0;
        sum_block_weight = 0.0;
        block_count = 0;
      }
      sig_buf[3] = sum_block_weight;
      sig_buf[4] = sum_local_energy;
      sig_buf[5] = sum_kinetic;
      sig_buf[6] = sum_local_potential;
      sig_buf[7] = static_cast<double>(block_count);

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
