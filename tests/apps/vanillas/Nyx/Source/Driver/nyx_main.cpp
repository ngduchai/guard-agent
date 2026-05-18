
#include <iostream>
#include <iomanip>
#include <sstream>
#include <limits>
#include <algorithm>
#include <cstdio>

#include <AMReX_CArena.H>
#include <AMReX_REAL.H>
#include <AMReX_Utility.H>
#include <AMReX_IntVect.H>
#include <AMReX_Box.H>
#include <AMReX_Amr.H>
#include <AMReX_ParmParse.H>
#include <AMReX_ParallelDescriptor.H>
#include <AMReX_AmrLevel.H>
#include <AMReX_Geometry.H>
#include <AMReX_MultiFab.H>
#ifdef BL_USE_MPI
#include <MemInfo.H>
#endif
#include <Nyx.H>

#ifdef REEBER
#ifdef REEBER_HIST
#include <ReeberAnalysis.H> // This actually works both in situ and in-transit.
#endif
#endif

#include <Nyx_output.H>

std::string inputs_name = "";

#ifdef GIMLET
#include <DoGimletAnalysis.H>
#include <postprocess_tau_fields.H>
#include <fftw3-mpi.h>
#include <MakeFFTWBoxes.H>
#endif

#ifdef HENSON
#include <henson/context.h>
#include <henson/data.h>
#endif

using namespace amrex;

const int NyxHaloFinderSignal(42);
const int resizeSignal(43);
const int GimletSignal(55);
const int quitSignal(-44);

amrex::LevelBld* getLevelBld ();

// Compute physics-derived scalar reductions over the FINAL hydrodynamic
// state (State_Type MultiFab on every level) and emit one
// VALIDATION_SIGNATURE line per conserved component on rank 0.  This is the
// content-faithful golden-vs-recovery comparison anchor used by the
// validation framework: an LLM stub that initializes but skips integration
// produces a different signature because the shock has not propagated; an
// LLM stub that replays captured baseline stdout is caught by the
// framework's anti-replay check.  Dumps OUTPUT only (the conserved
// hydrodynamic variables that are the user-facing scientific result), not
// internal scratch / ghost / integrator state.
static void dumpValidationSignature (amrex::Amr* amrptr)
{
    using namespace amrex;

    constexpr int N_OUT = 6;
    const int comps[N_OUT]    = { 0, 1, 2, 3, 4, 5 };
    const char* names[N_OUT]  = { "den", "xmom", "ymom", "zmom", "eden", "eint" };

    Real total_sum [N_OUT] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    Real total_sum2[N_OUT] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    Real total_max [N_OUT];
    Real total_min [N_OUT];
    for (int c = 0; c < N_OUT; ++c) {
        total_max[c] = -std::numeric_limits<Real>::infinity();
        total_min[c] =  std::numeric_limits<Real>::infinity();
    }
    long total_count = 0;

    const int n_levels = amrptr->finestLevel() + 1;
    for (int lev = 0; lev < n_levels; ++lev) {
        AmrLevel& al = amrptr->getLevel(lev);
        // State_Type == 0 in Nyx (see Nyx.H StateType enum).
        const MultiFab& mf = al.get_new_data(0);

        const long ncells_this_level =
            static_cast<long>(al.Geom().Domain().numPts());
        total_count += ncells_this_level;

        for (int c = 0; c < N_OUT; ++c) {
            total_sum [c] += mf.sum(comps[c]);
            const Real n2 = mf.norm2(comps[c]);
            total_sum2[c] += n2 * n2;
            total_max [c]  = std::max(total_max[c], mf.max(comps[c]));
            total_min [c]  = std::min(total_min[c], mf.min(comps[c]));
        }
    }

    if (ParallelDescriptor::IOProcessor()) {
        std::cout << std::scientific << std::setprecision(10);
        for (int c = 0; c < N_OUT; ++c) {
            std::cout << "VALIDATION_SIGNATURE:"
                      << " field=" << names[c]
                      << " sum="   << total_sum [c]
                      << " sum2="  << total_sum2[c]
                      << " max="   << total_max [c]
                      << " min="   << total_min [c]
                      << " count=" << total_count << std::endl;
        }
    }
}

// File-based binary signature dump for Step 0 file-comparison framework.
// Writes 31 raw doubles (248 bytes) to "validation_output.bin" in CWD on rank 0:
//   For each of the 6 conserved hydro components (den, xmom, ymom, zmom, eden,
//   eint) in fixed order: sum, sum², max, min, count_as_double  (5 × 6 = 30)
//   followed by 1 final-value double: amrptr->cumTime() (final physical time)
// Uses MPI_SUM / MPI_MAX / MPI_MIN reductions via AMReX MultiFab API
// (rank-order independent).  Byte layout MUST match between vanilla and
// reference for cross-consistency PASS at validate Step 0.6c.
static void dumpValidationSignatureBin (amrex::Amr* amrptr)
{
    using namespace amrex;

    constexpr int N_OUT = 6;
    const int comps[N_OUT] = { 0, 1, 2, 3, 4, 5 };

    Real total_sum [N_OUT] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    Real total_sum2[N_OUT] = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    Real total_max [N_OUT];
    Real total_min [N_OUT];
    for (int c = 0; c < N_OUT; ++c) {
        total_max[c] = -std::numeric_limits<Real>::infinity();
        total_min[c] =  std::numeric_limits<Real>::infinity();
    }
    long total_count = 0;

    const int n_levels = amrptr->finestLevel() + 1;
    for (int lev = 0; lev < n_levels; ++lev) {
        AmrLevel& al = amrptr->getLevel(lev);
        // State_Type == 0 in Nyx (see Nyx.H StateType enum).
        const MultiFab& mf = al.get_new_data(0);

        const long ncells_this_level =
            static_cast<long>(al.Geom().Domain().numPts());
        total_count += ncells_this_level;

        for (int c = 0; c < N_OUT; ++c) {
            total_sum [c] += mf.sum(comps[c]);
            const Real n2 = mf.norm2(comps[c]);
            total_sum2[c] += n2 * n2;
            total_max [c]  = std::max(total_max[c], mf.max(comps[c]));
            total_min [c]  = std::min(total_min[c], mf.min(comps[c]));
        }
    }

    if (ParallelDescriptor::IOProcessor()) {
        double buf[31];
        int idx = 0;
        for (int c = 0; c < N_OUT; ++c) {
            buf[idx++] = static_cast<double>(total_sum [c]);
            buf[idx++] = static_cast<double>(total_sum2[c]);
            buf[idx++] = static_cast<double>(total_max [c]);
            buf[idx++] = static_cast<double>(total_min [c]);
            buf[idx++] = static_cast<double>(total_count);
        }
        buf[idx++] = static_cast<double>(amrptr->cumTime());
        // idx == 31

        std::FILE* fp = std::fopen("validation_output.bin", "wb");
        if (fp != nullptr) {
            std::fwrite(buf, sizeof(double), 31, fp);
            std::fclose(fp);
        }
    }
}

void
nyx_main (int argc, char* argv[])
{
    // check to see if it contains --describe
    if (argc >= 2) {
        for (auto i = 1; i < argc; i++) {
            if (std::string(argv[i]) == "--describe") {
                Nyx::writeBuildInfo();
                return;
            }
        }
    }
    amrex::Initialize(argc, argv);
    {

    // save the inputs file name for later
    if (argc > 1) {
      if (!strchr(argv[1], '=')) {
        inputs_name = argv[1];
      }
    }
    BL_PROFILE_REGION_START("main()");
    BL_PROFILE_VAR("main()", pmain);

    //
    // Don't start timing until all CPUs are ready to go.
    //
    ParallelDescriptor::Barrier("Starting main.");

    BL_COMM_PROFILE_NAMETAG("main TOP");

    Real dRunTime1 = ParallelDescriptor::second();

    std::cout << std::setprecision(10);

    int max_step;
    Real stop_time;
    ParmParse pp;

    max_step  = -1;
    stop_time = -1.0;

    pp.query("max_step",  max_step);
    pp.query("stop_time", stop_time);

    if (max_step < 0 && stop_time < 0.0)
    {
        amrex::Abort("**** Error: either max_step or stop_time has to be positive!");
    }

    // Reeber has to do some initialization.
#ifdef REEBER
#ifdef REEBER_HIST
    reeber_int = initReeberAnalysis();
#endif
#endif

    // We hard-wire the initial time to 0
    Real strt_time =  0.0;

    Amr *amrptr = new Amr(getLevelBld());
    amrptr->init(strt_time,stop_time);

#ifdef BL_USE_MPI
    // ---- initialize nyx memory monitoring
    MemInfo *mInfo = MemInfo::GetInstance();
    mInfo->LogSummary("MemInit  ");
#endif

    const Real time_before_main_loop = ParallelDescriptor::second();

    bool finished(false);
    {

    BL_PROFILE_REGION("R::Nyx::coarseTimeStep");

    while ( ! finished)
    {
     // If we set the regrid_on_restart flag and if we are *not* going to take
     // a time step then we want to go ahead and regrid here.
     //
     if (amrptr->RegridOnRestart()) {
       if (    (amrptr->levelSteps(0) >= max_step ) ||
               ( (stop_time >= 0.0) &&
                 (amrptr->cumTime() >= stop_time)  )    )
       {
           // Regrid only!
           amrptr->RegridOnly(amrptr->cumTime());
       }
     }

     if (amrptr->okToContinue()
          && (amrptr->levelSteps(0) < max_step || max_step < 0)
          && (amrptr->cumTime() < stop_time || stop_time < 0.0))

     {
       amrptr->coarseTimeStep(stop_time);          // ---- Do a timestep.
#ifdef HENSON
       henson_save_pointer("amr",  amrptr);        // redundant to do every timesetp, but negligible overhead
       henson_save_pointer("dmpc", Nyx::theDMPC());
       henson_yield();
#endif
     } else {
       finished = true;
     }

    }  // ---- end while( ! finished)

    }

    const Real time_without_init = ParallelDescriptor::second() - time_before_main_loop;
    if (ParallelDescriptor::IOProcessor()) std::cout << "Time w/o init: " << time_without_init << std::endl;

    // call is removed so the LLM cannot rely on a guaranteed end-of-run
    // restart state).
    if (amrptr->stepOfLastPlotFile() < amrptr->levelSteps(0)) {
        amrptr->writePlotFile();
    }

    // Validation framework golden-vs-recovery comparison anchor.  Must run
    // BEFORE delete amrptr (which tears down the AmrLevel and its state
    // MultiFabs).
    dumpValidationSignature(amrptr);
    dumpValidationSignatureBin(amrptr);

    delete amrptr;

    //
    // This MUST follow the above delete as ~Amr() may dump files to disk.
    //
    const int IOProc = ParallelDescriptor::IOProcessorNumber();

    Real dRunTime2 = ParallelDescriptor::second() - dRunTime1;

    ParallelDescriptor::ReduceRealMax(dRunTime2, IOProc);

    if (ParallelDescriptor::IOProcessor())
    {
        std::cout << "Run time = " << dRunTime2 << std::endl;
    }

    BL_PROFILE_VAR_STOP(pmain);
    BL_PROFILE_REGION_STOP("main()");
    BL_PROFILE_SET_RUN_TIME(dRunTime2);

    }
    amrex::Finalize();
}
