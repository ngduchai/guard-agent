#include "phold.h"
#include "network-mpi.h"  /* tw_net_statistics — not pulled in via ross.h umbrella */
#include <mpi.h>
#include <stdint.h>


tw_peid
phold_map(tw_lpid gid)
{
	return (tw_peid) gid / g_tw_nlp;
}

void
phold_init(phold_state * s, tw_lp * lp)
{
    (void) s;
	int              i;

	if( stagger )
	  {
	    for (i = 0; i < g_phold_start_events; i++)
	      {
		tw_event_send(
			      tw_event_new(lp->gid,
					   tw_rand_exponential(lp->rng, mean) + lookahead + (tw_stime)(lp->gid % (unsigned int)g_tw_ts_end),
					   lp));
	      }
	  }
	else
	  {
	    for (i = 0; i < g_phold_start_events; i++)
	      {
		tw_event_send(
			      tw_event_new(lp->gid,
					   tw_rand_exponential(lp->rng, mean) + lookahead,
					   lp));
	      }
	  }
}

void
phold_pre_run(phold_state * s, tw_lp * lp)
{
    (void) s;
    tw_lpid	 dest;

	if(tw_rand_unif(lp->rng) <= percent_remote)
	{
		dest = tw_rand_integer(lp->rng, 0, ttl_lps - 1);
	} else
	{
		dest = lp->gid;
	}

	if(dest >= (g_tw_nlp * tw_nnodes()))
		tw_error(TW_LOC, "bad dest");

	tw_event_send(tw_event_new(dest, tw_rand_exponential(lp->rng, mean) + lookahead, lp));
}

void
phold_event_handler(phold_state * s, tw_bf * bf, phold_message * m, tw_lp * lp)
{
    (void) s;
    (void) m;
	tw_lpid	 dest;

	if(tw_rand_unif(lp->rng) <= percent_remote)
	{
		bf->c1 = 1;
		dest = tw_rand_integer(lp->rng, 0, ttl_lps - 1);
		// Makes PHOLD non-deterministic across processors! Don't uncomment
		/* dest += offset_lpid; */
		/* if(dest >= ttl_lps) */
		/* 	dest -= ttl_lps; */
	} else
	{
		bf->c1 = 0;
		dest = lp->gid;
	}

	if(dest >= (g_tw_nlp * tw_nnodes()))
		tw_error(TW_LOC, "bad dest");

	tw_event_send(tw_event_new(dest, tw_rand_exponential(lp->rng, mean) + lookahead, lp));
}

void
phold_event_handler_rc(phold_state * s, tw_bf * bf, phold_message * m, tw_lp * lp)
{
    (void) s;
    (void) m;
	tw_rand_reverse_unif(lp->rng);
	tw_rand_reverse_unif(lp->rng);

	if(bf->c1 == 1)
		tw_rand_reverse_unif(lp->rng);
}

void phold_commit(phold_state * s, tw_bf * bf, phold_message * m, tw_lp * lp)
{
    (void) s;
    (void) bf;
    (void) m;
    (void) lp;
}

void
phold_finish(phold_state * s, tw_lp * lp)
{
    (void) s;
    (void) lp;
}

tw_lptype       mylps[] = {
	{(init_f) phold_init,
     /* (pre_run_f) phold_pre_run, */
     (pre_run_f) NULL,
	 (event_f) phold_event_handler,
	 (revent_f) phold_event_handler_rc,
	 (commit_f) phold_commit,
	 (final_f) phold_finish,
	 (map_f) phold_map,
	sizeof(phold_state)},
	{0},
};

void event_trace(phold_message *m, tw_lp *lp, char *buffer, int *collect_flag)
{
    (void) m;
    (void) lp;
    (void) buffer;
    (void) collect_flag;
    return;
}

void phold_stats_collect(phold_state *s, tw_lp *lp, char *buffer)
{
    (void) s;
    (void) lp;
    (void) buffer;
    return;
}

st_model_types model_types[] = {
    {(ev_trace_f) event_trace,
     0,
    (model_stat_f) phold_stats_collect,
    sizeof(int),
    NULL, //(sample_event_f)
    NULL, //(sample_revent_f)
    0},
    {0}
};

const tw_optdef app_opt[] =
{
	TWOPT_GROUP("PHOLD Model"),
	TWOPT_DOUBLE("remote", percent_remote, "desired remote event rate"),
	TWOPT_UINT("nlp", nlp_per_pe, "number of LPs per processor"),
	TWOPT_DOUBLE("mean", mean, "exponential distribution mean for timestamps"),
	TWOPT_DOUBLE("mult", mult, "multiplier for event memory allocation"),
	TWOPT_DOUBLE("lookahead", lookahead, "lookahead for events"),
	TWOPT_UINT("start-events", g_phold_start_events, "number of initial messages per LP"),
	TWOPT_UINT("stagger", stagger, "Set to 1 to stagger event uniformly across 0 to end time."),
	TWOPT_UINT("memory", optimistic_memory, "additional memory buffers"),
	TWOPT_CHAR("run", run_id, "user supplied run name"),
	TWOPT_END()
};

/* Definitions to help debug the reversible handler */
struct phold_state_snapshot {
    long int saved_dummy_data;
};

void save_state(struct phold_state_snapshot * into, struct phold_state const * from) {
    into->saved_dummy_data = from->dummy_state;
}

void clean_state(struct phold_state_snapshot * into) {
    // Nothing to do
}

void print_state(FILE * out, char const * prefix, struct phold_state * state) {
    fprintf(out, "%sstruct phold_state {\n  dummy_state = %ld\n}\n", prefix, state->dummy_state);
}

void print_state_saved(FILE * out, char const * prefix, struct phold_state_snapshot * state) {
    fprintf(out, "%sstruct phold_state_snapshot {\n  saved_dummy_data = %ld\n}\n", prefix, state->saved_dummy_data);
}

void print_event(FILE * out, char const * prefix, struct phold_state * state, struct phold_message * message) {
    fprintf(out, "%sstruct phold_message {\n  dummy_data = %ld\n}\n", prefix, message->dummy_data);
}

bool check_state(struct phold_state * before, struct phold_state * after) {
    return before->dummy_state == after->dummy_state;
}
/* End of definitions */

int
main(int argc, char **argv)
{

#ifdef TEST_COMM_ROSS
    // Init outside of ROSS
    MPI_Init(&argc, &argv);
    // Split COMM_WORLD in half even/odd
    int mpi_rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &mpi_rank);
    MPI_Comm split_comm;
    MPI_Comm_split(MPI_COMM_WORLD, mpi_rank%2, mpi_rank, &split_comm);
    if(mpi_rank%2 == 1){
        // tests should catch any MPI_COMM_WORLD collectives
        MPI_Finalize();
        return 0;
    }
    // Allows ROSS to function as normal
    tw_comm_set(split_comm);
#endif

	unsigned int i;

	// set a min lookahead of 1.0
	lookahead = 1.0;
	tw_opt_add(app_opt);
	tw_init(&argc, &argv);

#ifdef USE_DAMARIS
    if(g_st_ross_rank)
    { // only ross ranks should run code between here and tw_run()
#endif
	if( lookahead > 1.0 )
	  tw_error(TW_LOC, "Lookahead > 1.0 .. needs to be less\n");

	//reset mean based on lookahead
        mean = mean - lookahead;

	offset_lpid = g_tw_mynode * nlp_per_pe;
	ttl_lps = tw_nnodes() * nlp_per_pe;
	g_tw_events_per_pe = (mult * nlp_per_pe * g_phold_start_events) +
				optimistic_memory;
	//g_tw_rng_default = TW_FALSE;
	g_tw_lookahead = lookahead;

	tw_define_lps(nlp_per_pe, sizeof(phold_message));

	for(i = 0; i < g_tw_nlp; i++)
    {
		tw_lp_settype(i, &mylps[0]);
        st_model_settype(i, &model_types[0]);
    }

    // Defining all functions for snapshotter (used to test proper
    // implementation of event reversing handler).
    // This serves as documentation for them.
    crv_lp_snapshotter phold_chkptr = {
        .lptype = &mylps[0],
        .sz_storage = sizeof(struct phold_state_snapshot),
        .save_lp = (save_lp_snapshot_f) save_state, // Can be null
        .clean_lp = (clean_lp_snapshot_f) clean_state, // Can be null
        .check_lps = (check_states_f) check_state, // Can be null
        .print_lp = (print_lpstate_f) print_state,
        .print_snapshot = (print_lp_snapshot_f) print_state_saved,
        .print_event = (print_event_f) print_event,
    };
    crv_add_custom_lp_snapshot(&phold_chkptr);

        if( g_tw_mynode == 0 )
	  {
	    printf("========================================\n");
	    printf("PHOLD Model Configuration..............\n");
	    printf("   Lookahead..............%lf\n", lookahead);
	    printf("   Start-events...........%u\n", g_phold_start_events);
	    printf("   stagger................%u\n", stagger);
	    printf("   Mean...................%lf\n", mean);
	    printf("   Mult...................%lf\n", mult);
	    printf("   Memory.................%u\n", optimistic_memory);
	    printf("   Remote.................%lf\n", percent_remote);
	    printf("========================================\n\n");
	  }

	tw_run();
#ifdef USE_DAMARIS
    } // end if(g_st_ross_rank)
#endif

	/* Step 0 v9.5 (2026-05-25): per-LP RNG state fingerprint.
	 *
	 * v9.4 derived its signature from pe->stats counters (s_net_events,
	 * s_nsend_net_remote).  Those are engine instrumentation — RIO
	 * (the RIO reference's checkpoint subsystem) does NOT persist them
	 * (core/rio/io-serialize.c touches only pe->stats.s_rio_load).
	 * After a failure-injected recovery, pe->stats restarts from zero
	 * and reports only post-checkpoint work, even though the simulation
	 * itself completes correctly.  This made the failure-injected leg
	 * spuriously FAIL on a working RIO restore.
	 *
	 * v9.5 derives the signature from the simulation's actual output
	 * state: per-LP CLCG4 RNG Cg[4] vectors.  Properties:
	 *   - RIO DOES checkpoint Cg/Lg/Ig (core/rio/io-serialize.c:11-13)
	 *     and restore them on load (lines 37-39) — so failure-injected
	 *     recovery produces bit-identical Cg as a clean run.
	 *   - tw_rand_reverse_unif (core/rand-clcg4.c:460-483) reverses
	 *     each draw on rollback, so optimistic speculation does not
	 *     leak into the committed-only final Cg.
	 *   - Cold-replay (skipped tw_run()) leaves Cg = Ig (initial sub-
	 *     seeds), differing from the clean-run sums by many orders of
	 *     magnitude on every slot.
	 *   - Perturbing --rng-seed1 changes every LP's initial Ig, which
	 *     changes the trajectory of every Cg → sum shifts detectably.
	 *
	 * Schema (32 bytes):
	 *   [0..3] (double) global SUM across all LPs on all ranks of
	 *                   lp->rng->Cg[j] for j = 0..3.
	 *   Per-rank int64_t local sums → MPI_Reduce(MPI_SUM) to rank 0
	 *   → cast to double.
	 *
	 * Overflow: 16,000 LPs (4000 nlp x 4 ranks) x INT32_MAX ~ 3.4e13,
	 *   safely under INT64_MAX (~9.2e18) and within double's exact-
	 *   integer range (2^53 ~ 9e15).
	 */
	{
		int64_t local_rng_sum[4] = {0, 0, 0, 0};
		for (unsigned int i = 0; i < g_tw_nlp; i++) {
			tw_lp *lp = g_tw_lp[i];
			if (lp && lp->rng) {
				for (int j = 0; j < 4; j++) {
					local_rng_sum[j] += (int64_t)lp->rng->Cg[j];
				}
			}
		}
		int64_t global_rng_sum[4] = {0, 0, 0, 0};
		MPI_Reduce(local_rng_sum, global_rng_sum, 4, MPI_INT64_T,
		           MPI_SUM, 0, MPI_COMM_WORLD);
		if (g_tw_mynode == 0) {
			double sig_buf[4];
			for (int j = 0; j < 4; j++) {
				sig_buf[j] = (double)global_rng_sum[j];
			}
			FILE* sig_f = fopen("validation_output.bin", "wb");
			if (sig_f) {
				fwrite(sig_buf, sizeof(double), 4, sig_f);
				fclose(sig_f);
			}
		}
	}

	tw_end();

#ifdef TEST_COMM_ROSS
	MPI_Finalize();
#endif

	return 0;
}
