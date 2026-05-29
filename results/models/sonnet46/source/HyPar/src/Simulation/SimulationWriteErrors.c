/*! @file SimulationWriteErrors.c
    @brief Write errors for each simulation
    @author Debojyoti Ghosh
*/

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <basic.h>
#include <common.h>
#include <mpivars.h>
#include <simulation_object.h>

/* HyPar validation signature dumper (Step 0 v8: file-based comparison).
 *
 * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on rank 0.
 * Byte layout MUST be identical between vanilla and reference at the same
 * workload so Step 0.6c cross-consistency passes:
 *   [0] sim[0].solver.error[0]                     (L1 error)
 *   [1] sim[0].solver.error[1]                     (L2 error)
 *   [2] sim[0].solver.error[2]                     (Linfinity error)
 *   [3] (double)nsims                              (number of simulations)
 *   [4] (double)sim[0].solver.ndims                (spatial dimensions)
 *   [5] sim[0].solver.dt                           (time step size)
 *
 * solver.error[] is computed at end-of-run by HyPar's existing error-computation
 * machinery (already includes global MPI reductions per HyPar's design).  The
 * dumper is rank-root-only by construction; caller MUST invoke from inside the
 * existing `if (!rank)` block in SimWriteErrors.
 */
static void dumpValidationSignatureBin_hypar(const SimulationObject* sim, int nsims)
{
  double buf[6];
  buf[0] = sim[0].solver.error[0];
  buf[1] = sim[0].solver.error[1];
  buf[2] = sim[0].solver.error[2];
  buf[3] = (double)nsims;
  buf[4] = (double)sim[0].solver.ndims;
  buf[5] = sim[0].solver.dt;
  FILE* f = fopen("validation_output.bin", "wb");
  if (f) {
    fwrite(buf, sizeof(double), 6, f);
    fclose(f);
  }
}

/*! Writes out the errors and other data for each simulation.
*/

void SimWriteErrors(void  *s,               /*!< Array of simulations of type #SimulationObject */
                    int   nsims,            /*!< Number of simulations */
                    int   rank,             /*!< MPI rank of this process */
                    double solver_runtime,  /*!< Measured runtime of solver */
                    double main_runtime     /*!< Measured total runtime */
                   )
{
  SimulationObject* sim = (SimulationObject*) s;
  int n;

  if (!rank) {

    if (nsims > 1) printf("\n");

    for (n = 0; n < nsims; n++) {

      char err_fname[_MAX_STRING_SIZE_],
           cons_fname[_MAX_STRING_SIZE_],
           fc_fname[_MAX_STRING_SIZE_];
      strcpy(err_fname,"errors");
      strcpy(cons_fname,"conservation");
      strcpy(fc_fname,"function_counts");
#ifdef with_librom
      char rom_diff_fname[_MAX_STRING_SIZE_];
      strcpy(rom_diff_fname,"pde_rom_diff");
#endif


      if (nsims > 1) {

        strcat(err_fname,"_");
        strcat(cons_fname,"_");
        strcat(fc_fname,"_");
#ifdef with_librom
        strcat(rom_diff_fname,"_");
#endif

        char index[_MAX_STRING_SIZE_];
        GetStringFromInteger(n, index, (int)log10(nsims)+1);

        strcat(err_fname,index);
        strcat(cons_fname,index);
        strcat(fc_fname,index);
#ifdef with_librom
        strcat(rom_diff_fname,index);
#endif
      }

      strcat(err_fname,".dat");
      strcat(cons_fname,".dat");
      strcat(fc_fname,".dat");
#ifdef with_librom
      strcat(rom_diff_fname,".dat");
#endif

      FILE *out;
      /* write out solution errors and wall times to file */
      out = fopen(err_fname,"w");
      for (int d=0; d<sim[n].solver.ndims; d++) fprintf(out,"%4d ",sim[n].solver.dim_global[d]);
      for (int d=0; d<sim[n].solver.ndims; d++) fprintf(out,"%4d ",sim[n].mpi.iproc[d]);
      fprintf(out,"%1.16E  ",sim[n].solver.dt);
      fprintf(out,"%1.16E %1.16E %1.16E   ",sim[n].solver.error[0],sim[n].solver.error[1],sim[n].solver.error[2]);
      fprintf(out,"%1.16E %1.16E\n",solver_runtime,main_runtime);
      fclose(out);
      /* write out conservation errors to file */
      out = fopen(cons_fname,"w");
      for (int d=0; d<sim[n].solver.ndims; d++) fprintf(out,"%4d ",sim[n].solver.dim_global[d]);
      for (int d=0; d<sim[n].solver.ndims; d++) fprintf(out,"%4d ",sim[n].mpi.iproc[d]);
      fprintf(out,"%1.16E  ",sim[n].solver.dt);
      for (int d=0; d<sim[n].solver.nvars; d++) fprintf(out,"%1.16E ",sim[n].solver.ConservationError[d]);
      fprintf(out,"\n");
      fclose(out);
      /* write out function call counts to file */
      out = fopen(fc_fname,"w");
      fprintf(out,"%d\n",sim[n].solver.n_iter);
      fprintf(out,"%d\n",sim[n].solver.count_hyp);
      fprintf(out,"%d\n",sim[n].solver.count_par);
      fprintf(out,"%d\n",sim[n].solver.count_sou);
#ifdef with_petsc
      fprintf(out,"%d\n",sim[n].solver.count_RHSFunction);
      fprintf(out,"%d\n",sim[n].solver.count_IFunction);
      fprintf(out,"%d\n",sim[n].solver.count_IJacobian);
      fprintf(out,"%d\n",sim[n].solver.count_IJacFunction);
#endif
      fclose(out);
#ifdef with_librom
      /* write out solution errors and wall times to file */
      if (sim[n].solver.rom_diff_norms[0] >= 0) {
        out = fopen(rom_diff_fname,"w");
        for (int d=0; d<sim[n].solver.ndims; d++) fprintf(out,"%4d ",sim[n].solver.dim_global[d]);
        for (int d=0; d<sim[n].solver.ndims; d++) fprintf(out,"%4d ",sim[n].mpi.iproc[d]);
        fprintf(out,"%1.16E  ",sim[n].solver.dt);
        fprintf(out,"%1.16E %1.16E %1.16E   ",sim[n].solver.rom_diff_norms[0],sim[n].solver.rom_diff_norms[1],sim[n].solver.rom_diff_norms[2]);
        fprintf(out,"%1.16E %1.16E\n",solver_runtime,main_runtime);
        fclose(out);
      }
#endif

      /* print solution errors, conservation errors, and wall times to screen */
      if (sim[n].solver.error[0] >= 0) {
        printf("Computed errors for domain %d:\n", n);
        printf("  L1         Error           : %1.16E\n",sim[n].solver.error[0]);
        printf("  L2         Error           : %1.16E\n",sim[n].solver.error[1]);
        printf("  Linfinity  Error           : %1.16E\n",sim[n].solver.error[2]);
      }
      if (!strcmp(sim[n].solver.ConservationCheck,"yes")) {
        printf("Conservation Errors:\n");
        for (int d=0; d<sim[n].solver.nvars; d++) printf("\t%1.16E\n",sim[n].solver.ConservationError[d]);
      }
#ifdef with_librom
      if (sim[n].solver.rom_diff_norms[0] >= 0) {
        printf("Norms of the diff between ROM and PDE solutions for domain %d:\n", n);
        printf("  L1         Norm            : %1.16E\n",sim[n].solver.rom_diff_norms[0]);
        printf("  L2         Norm            : %1.16E\n",sim[n].solver.rom_diff_norms[1]);
        printf("  Linfinity  Norm            : %1.16E\n",sim[n].solver.rom_diff_norms[2]);
      }
#endif

    }

    printf("Solver runtime (in seconds): %1.16E\n",solver_runtime);
    printf("Total  runtime (in seconds): %1.16E\n",main_runtime);
    if (nsims > 1) printf("\n");

    /* Step 0 v8: emit binary validation signature for file-based comparison.
     * Rank-root-only by construction (we are inside `if (!rank)`).  Uses
     * sim[0]'s error values + dt + dims, which are populated by HyPar's
     * existing error computation machinery before SimWriteErrors is called.
     */
    if (nsims > 0) {
      dumpValidationSignatureBin_hypar(sim, nsims);
    }

  }

  return;
}
