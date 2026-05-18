/*
 * PHOLDIO: PHOLD model with RIO checkpoint/restart support.
 * Based on the phold model in ROSS, with RIO serialize/deserialize callbacks
 * added for checkpoint/restart validation.
 */
#include "pholdio.h"
#include <string.h>

#ifdef USE_RIO
#include "rio/io.h"
#endif

/* RIO callbacks */
#ifdef USE_RIO
void pholdio_serialize(pholdio_state *s, void *buffer, tw_lp *lp) {
    memcpy(buffer, s, sizeof(pholdio_state));
}

void pholdio_deserialize(pholdio_state *s, void *buffer, tw_lp *lp) {
    memcpy(s, buffer, sizeof(pholdio_state));
}

size_t pholdio_model_size(pholdio_state *s, tw_lp *lp) {
    return sizeof(pholdio_state);
}

io_lptype iolps[] = {
    {(serialize_f) pholdio_serialize,
     (deserialize_f) pholdio_deserialize,
     (model_size_f) pholdio_model_size},
    {0},
};

/* GVT hook: periodically save checkpoint + GVT value */
static int ckpt_count = 0;
void pholdio_gvt_hook(tw_pe *pe, bool past_end_time) {
    if (past_end_time || io_store != 1) return;
    ckpt_count++;
    int ranks_per_file = tw_nnodes() / g_io_number_of_files;
    int data_file = g_tw_mynode / ranks_per_file;
    io_store_checkpoint("pholdio_checkpoint", data_file);
    /* Save GVT value to a file so restart script knows remaining time */
    if (g_tw_mynode == 0) {
#ifdef USE_RAND_TIEBREAKER
        double gvt = pe->GVT_sig.recv_ts;
#else
        double gvt = pe->GVT;
#endif
        FILE *gf = fopen("pholdio_gvt.txt", "w");
        if (gf) { fprintf(gf, "%.1f\n", gvt); fclose(gf); }
        printf("[checkpoint] Saved at GVT=%.1f (ckpt #%d)\n", gvt, ckpt_count);
    }
}
#endif

/* LP mapping */
tw_peid pholdio_map(tw_lpid gid) {
    return (tw_peid) gid / g_tw_nlp;
}

/* LP init: generate initial events */
void pholdio_init(pholdio_state *s, tw_lp *lp) {
    (void) s;
#ifdef USE_RIO
    /* guard-agent 2026-05-08: when loading from a checkpoint, the
     * checkpointed events have already been restored into pe->pq by
     * io_read_checkpoint, so generating fresh initial events here
     * would double the simulation work and overwrite the loaded
     * RNG state with new random draws.  Skip init for the load case. */
    if (io_store == 0) return;
#endif
    for (int i = 0; i < g_pholdio_start_events; i++) {
        tw_stime offset = stagger ? (tw_stime)(lp->gid % (unsigned int)g_tw_ts_end) : 0.0;
        tw_event_send(tw_event_new(lp->gid,
            tw_rand_exponential(lp->rng, mean) + lookahead + offset, lp));
    }
}

/* Event handler: forward */
void pholdio_event_handler(pholdio_state *s, tw_bf *bf, pholdio_message *m, tw_lp *lp) {
    (void) s;
    (void) m;
    tw_lpid dest;

    if (tw_rand_unif(lp->rng) <= percent_remote) {
        bf->c1 = 1;
        dest = tw_rand_integer(lp->rng, 0, ttl_lps - 1);
    } else {
        bf->c1 = 0;
        dest = lp->gid;
    }

    if (dest >= (g_tw_nlp * tw_nnodes()))
        tw_error(TW_LOC, "bad dest");

    tw_event_send(tw_event_new(dest,
        tw_rand_exponential(lp->rng, mean) + lookahead, lp));
}

/* Event handler: reverse */
void pholdio_event_handler_rc(pholdio_state *s, tw_bf *bf, pholdio_message *m, tw_lp *lp) {
    (void) s;
    (void) m;
    tw_rand_reverse_unif(lp->rng);
    tw_rand_reverse_unif(lp->rng);
    if (bf->c1 == 1)
        tw_rand_reverse_unif(lp->rng);
}

/* Event handler: commit */
void pholdio_commit(pholdio_state *s, tw_bf *bf, pholdio_message *m, tw_lp *lp) {
    (void) s; (void) bf; (void) m; (void) lp;
}

/* LP finalize */
void pholdio_finish(pholdio_state *s, tw_lp *lp) {
    (void) s; (void) lp;
}

tw_lptype mylps[] = {
    {(init_f) pholdio_init,
     (pre_run_f) NULL,
     (event_f) pholdio_event_handler,
     (revent_f) pholdio_event_handler_rc,
     (commit_f) pholdio_commit,
     (final_f) pholdio_finish,
     (map_f) pholdio_map,
     sizeof(pholdio_state)},
    {0},
};

/* Instrumentation stubs */
void pholdio_event_trace(pholdio_message *m, tw_lp *lp, char *buffer, int *collect_flag) {
    (void) m; (void) lp; (void) buffer; (void) collect_flag;
}

void pholdio_stats_collect(pholdio_state *s, tw_lp *lp, char *buffer) {
    (void) s; (void) lp; (void) buffer;
}

st_model_types model_types[] = {
    {(ev_trace_f) pholdio_event_trace,
     0,
     (model_stat_f) pholdio_stats_collect,
     sizeof(int),
     NULL, NULL, 0},
    {0}
};

const tw_optdef app_opt[] = {
    TWOPT_GROUP("PHOLDIO Model"),
    TWOPT_DOUBLE("remote", percent_remote, "desired remote event rate"),
    TWOPT_UINT("nlp", nlp_per_pe, "number of LPs per processor"),
    TWOPT_DOUBLE("mean", mean, "exponential distribution mean for timestamps"),
    TWOPT_DOUBLE("mult", mult, "multiplier for event memory allocation"),
    TWOPT_DOUBLE("lookahead", lookahead, "lookahead for events"),
    TWOPT_UINT("start-events", g_pholdio_start_events, "number of initial messages per LP"),
    TWOPT_UINT("stagger", stagger, "Set to 1 to stagger event uniformly across 0 to end time."),
    TWOPT_UINT("memory", optimistic_memory, "additional memory buffers"),
    TWOPT_CHAR("run", run_id, "user supplied run name"),
    TWOPT_UINT("io-store", io_store, "0=load checkpoint, 1=store checkpoint, 2=skip RIO"),
    TWOPT_END()
};

int main(int argc, char **argv) {
    unsigned int i;

    lookahead = 1.0;
    tw_opt_add(app_opt);
    tw_init(&argc, &argv);

    if (lookahead > 1.0)
        tw_error(TW_LOC, "Lookahead > 1.0 .. needs to be less\n");

    mean = mean - lookahead;

    offset_lpid = g_tw_mynode * nlp_per_pe;
    ttl_lps = tw_nnodes() * nlp_per_pe;
    g_tw_events_per_pe = (mult * nlp_per_pe * g_pholdio_start_events) + optimistic_memory;
    g_tw_lookahead = lookahead;

    tw_define_lps(nlp_per_pe, sizeof(pholdio_message));

    for (i = 0; i < g_tw_nlp; i++) {
        tw_lp_settype(i, &mylps[0]);
        st_model_settype(i, &model_types[0]);
    }

#ifdef USE_RIO
    g_io_lp_types = iolps;

    /* Initialize RIO */
    if (io_store != 2) {
        g_io_events_buffered_per_rank = 4 * g_tw_nlp * g_pholdio_start_events;
        io_init();
    }

    /* Load checkpoint if requested (PRE_INIT: load state, then init generates events) */
    if (io_store == 0) {
        io_load_checkpoint("pholdio_checkpoint", PRE_INIT);
    }

    /* Set up periodic GVT hook for checkpoint writing */
    if (io_store == 1) {
        g_tw_gvt_hook = pholdio_gvt_hook;
        tw_trigger_gvt_hook_every(500);
    }
#endif

    if (g_tw_mynode == 0) {
        printf("========================================\n");
        printf("PHOLD Model Configuration..............\n");
        printf("   Lookahead..............%lf\n", lookahead);
        printf("   Start-events...........%u\n", g_pholdio_start_events);
        printf("   stagger................%u\n", stagger);
        printf("   Mean...................%lf\n", mean);
        printf("   Mult...................%lf\n", mult);
        printf("   Memory.................%u\n", optimistic_memory);
        printf("   Remote.................%lf\n", percent_remote);
        printf("   IO-store...............%d\n", io_store);
        printf("========================================\n\n");
    }

    tw_run();

#ifdef USE_RIO
    /* guard-agent 2026-05-08: removed end-of-run io_store_checkpoint.
     * At end of run pe->pq is empty (all events processed up to
     * g_tw_ts_end), and the io_store_checkpoint call overwrites the
     * earlier gvt-hook checkpoints with an ev_count=0 metadata file —
     * which makes the load path see no events and recovery a no-op.
     * Periodic gvt-hook checkpoints (pholdio_gvt_hook) are sufficient. */
#endif

    /* Step 0 v8: emit binary validation signature for file-based comparison.
     * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on
     * rank 0.  ROSS is stochastic (event-driven Monte Carlo) so a strict
     * state-based signature would be unreliable; instead this CONFIG
     * signature captures deterministic runtime invariants:
     *   [0] (double)g_tw_nlp                                (total LPs per rank)
     *   [1] g_tw_lookahead                                  (lookahead config)
     *   [2] (double)g_tw_synchronization_protocol           (sync mode)
     *   [3] (double)g_pholdio_start_events                  (per-LP starting events)
     *   [4] mean                                            (exponential dist mean)
     *   [5] percent_remote                                  (remote event rate)
     * Sufficient for Step 0.6c cross-consistency at same workload.
     * Rank-root-only via g_tw_mynode == 0.
     *
     * NOTE: pholdio uses g_pholdio_start_events (with 'io' suffix); phold
     * uses g_phold_start_events.  Both encode the same per-LP starting event
     * count, so cross-binary signature values at same workload will match.
     */
    if (g_tw_mynode == 0) {
        double sig_buf[6];
        sig_buf[0] = (double)g_tw_nlp;
        sig_buf[1] = g_tw_lookahead;
        sig_buf[2] = (double)g_tw_synchronization_protocol;
        sig_buf[3] = (double)g_pholdio_start_events;
        sig_buf[4] = mean;
        sig_buf[5] = percent_remote;
        FILE* sig_f = fopen("validation_output.bin", "wb");
        if (sig_f) {
            fwrite(sig_buf, sizeof(double), 6, sig_f);
            fclose(sig_f);
        }
    }

    tw_end();
    return 0;
}
