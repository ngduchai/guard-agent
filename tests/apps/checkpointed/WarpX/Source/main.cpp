/* Copyright 2016-2020 Andrew Myers, Ann Almgren, Axel Huebl
 *                     David Grote, Jean-Luc Vay, Remi Lehe
 *                     Revathi Jambunathan, Weiqun Zhang
 *
 * This file is part of WarpX.
 *
 * License: BSD-3-Clause-LBNL
 */
#include "WarpX.H"

#include "Initialization/WarpXInit.H"

#include <ablastr/profiler/ProfilerWrapper.H>
#include <ablastr/utils/timer/Timer.H>

#include <AMReX_Print.H>
#include <AMReX_ParallelDescriptor.H>

#include <cstdio>

int
main (int argc, char* argv[]) {
    warpx::initialization::initialize_external_libraries(argc, argv);
    {
        ABLASTR_PROFILE_VAR("main()", pmain);

        auto timer = ablastr::utils::timer::Timer{};
        timer.record_start_time();

        auto& warpx = WarpX::GetInstance();
        warpx.InitData();
        warpx.Evolve();
        const auto is_warpx_verbose = warpx.Verbose();

        /* Step 0 v8: emit binary validation signature for file-based comparison.
         * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on
         * rank 0.  Schema (byte-identical between vanilla and reference at
         * same workload):
         *   [0] gett_new(0)                            (final level-0 time)
         *   [1] (double)getistep(0)                    (final level-0 step count)
         *   [2] (double)maxStep()                      (config max step)
         *   [3] stopTime()                             (config stop time)
         *   [4] (double)finestLevel()                  (finest refinement level)
         *   [5] (double)getistep(finestLevel())        (step count at finest level)
         * All values are globally consistent (AMReX maintains them collectively).
         * Rank-root-only via amrex::ParallelDescriptor::IOProcessor().
         */
        if (amrex::ParallelDescriptor::IOProcessor()) {
            double sig_buf[6];
            sig_buf[0] = static_cast<double>(warpx.gett_new(0));
            sig_buf[1] = static_cast<double>(warpx.getistep(0));
            sig_buf[2] = static_cast<double>(warpx.maxStep());
            sig_buf[3] = static_cast<double>(warpx.stopTime());
            sig_buf[4] = static_cast<double>(warpx.finestLevel());
            sig_buf[5] = static_cast<double>(warpx.getistep(warpx.finestLevel()));
            FILE* sig_f = std::fopen("validation_output.bin", "wb");
            if (sig_f) {
                std::fwrite(sig_buf, sizeof(double), 6, sig_f);
                std::fclose(sig_f);
            }
        }

        WarpX::Finalize();

        timer.record_stop_time();
        if (is_warpx_verbose) {
            amrex::Print() << "Total Time                     : "
                           << timer.get_global_duration() << '\n';
        }

        ABLASTR_PROFILE_VAR_STOP(pmain);
    }
    warpx::initialization::finalize_external_libraries();
}
