#include "phold.h"
#include "network-mpi.h"  /* tw_net_statistics — not pulled in via ross.h umbrella */


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

	/* Step 0 v9 (2026-05-24): emit STATE-derived binary validation
	 * signature.  Replaces v8 config-only schema (which made the comparator
	 * tautological — every slot was a g_tw_* config global populated before
	 * tw_run() and never mutated by it, so a resilient implementation that
	 * skipped tw_run() entirely could pass the comparator byte-identically).
	 *
	 * Per-rank stats are first aggregated locally via tw_get_stats(), then
	 * MPI-reduced across the partition via tw_net_statistics() (collective —
	 * ALL ranks must call it; see core/network-mpi.c:696-747).  After the
	 * reduce, g_tw_pe->stats holds globally-summed event counters on
	 * masternode (rank 0) only.  The 17-element s_net_events block carries
	 * s_nevent_processed/s_e_rbs/s_rb_total via a single MPI_Reduce with
	 * MPI_SUM (see ross-types.h:117-170 for struct layout).
	 *
	 * Schema (48 bytes, slot-compatible with v8):
	 *   [0] (double)s_nevent_processed   global-SUM events committed
	 *   [1] (double)s_e_rbs              global-SUM events rolled back
	 *   [2] (double)s_rb_total           global-SUM total rollbacks issued
	 *   [3] (double)g_tw_gvt_done        completed GVT computations
	 *                                    (per-rank counter, deterministic
	 *                                    across ranks for fixed seed/cfg)
	 *   [4] g_tw_lookahead               config sanity marker
	 *   [5] (double)g_tw_synchronization_protocol  config sanity marker
	 *
	 * Comparator: tests/apps/configs/ROSS.yaml comparison.method =
	 * numeric-tolerance, tolerance=1e-12.  Slots [0..2] react to RNG-driven
	 * event-distribution shifts (e.g. --mean= perturbation propagates into
	 * commit/rollback counts); a cold-replayed (re-seeded or zero-init)
	 * resilient run produces different event traces and diverges on these
	 * slots.  Bit-exact under correctly-resumed replay (same seed → same
	 * deterministic event order → same counts).
	 */
	{
		tw_statistics s;
		memset(&s, 0, sizeof(s));
		tw_get_stats(g_tw_pe, &s);
		tw_net_statistics(g_tw_pe, &s);  /* collective: all ranks */
		if (g_tw_mynode == 0) {
			double sig_buf[6];
			sig_buf[0] = (double)g_tw_pe->stats.s_nevent_processed;
			sig_buf[1] = (double)g_tw_pe->stats.s_e_rbs;
			sig_buf[2] = (double)g_tw_pe->stats.s_rb_total;
			sig_buf[3] = (double)g_tw_gvt_done;
			sig_buf[4] = g_tw_lookahead;
			sig_buf[5] = (double)g_tw_synchronization_protocol;
			FILE* sig_f = fopen("validation_output.bin", "wb");
			if (sig_f) {
				fwrite(sig_buf, sizeof(double), 6, sig_f);
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
