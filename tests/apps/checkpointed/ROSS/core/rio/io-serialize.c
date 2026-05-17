#include "ross.h"

size_t io_lp_serialize (tw_lp *lp, void *buffer) {
    int i, j;

    io_lp_store tmp;

    tmp.gid = lp->gid;
    for (i = 0; i < g_tw_nRNG_per_lp; i++) {
        for (j = 0; j < 4; j++) {
            tmp.rng[j] = lp->rng->Ig[j];
            tmp.rng[j+4] = lp->rng->Lg[j];
            tmp.rng[j+8] = lp->rng->Cg[j];
        }
#ifdef RAND_NORMAL
        tmp.tw_normal_u1 = lp->rng->tw_normal_u1;
        tmp.tw_normal_u2 = lp->rng->tw_normal_u2;
        tmp.tw_normal_flipflop = lp->rng->tw_normal_flipflop;
#endif
    }
    tmp.critical_path = lp->critical_path;

    memcpy(buffer, &tmp, sizeof(io_lp_store));
    return sizeof(io_lp_store);
}

size_t io_lp_deserialize (tw_lp *lp, void *buffer) {
    int i, j;

    io_lp_store tmp;
    memcpy(&tmp, buffer, sizeof(io_lp_store));

    lp->gid = tmp.gid;

    for (i = 0; i < g_tw_nRNG_per_lp; i++) {
        for (j = 0; j < 4; j++) {
            lp->rng->Ig[j] = tmp.rng[j];
            lp->rng->Lg[j] = tmp.rng[j+4];
            lp->rng->Cg[j] = tmp.rng[j+8];
        }
#ifdef RAND_NORMAL
        lp->rng->tw_normal_u1 = tmp.tw_normal_u1;
        lp->rng->tw_normal_u2 = tmp.tw_normal_u2;
        lp->rng->tw_normal_flipflop = tmp.tw_normal_flipflop;
#endif
    }
    lp->critical_path = tmp.critical_path;

    return sizeof(io_lp_store);
}

size_t io_event_serialize (tw_event *e, void *buffer) {
    io_event_store tmp;

    memcpy(&(tmp.cv), &(e->cv), sizeof(tw_bf));
    tmp.critical_path = e->critical_path;
    // guard-agent 2026-05-08: events drained from pe->pq carry real
    // tw_lp* pointers, not the gid bit-cast that the original RIO
    // path produced via io_load_events.  Use the explicit ->dest_lpid
    // field (always a tw_lpid, set on send) so we serialize the gid
    // regardless of which path the event came from.
    tmp.dest_lp = e->dest_lpid;
    tmp.src_lp = e->src_lp->gid;
    // guard-agent 2026-05-08: store recv_ts as-is.  The original
    // `e->recv_ts - g_tw_ts_end` offset assumed the load run would
    // restart at simulated time 0 with events relative-to-end; that's
    // never compensated for on the read side, so the loaded events
    // landed at negative recv_ts and the simulator skipped them.
    tmp.recv_ts = e->recv_ts;
    tmp.event_id = e->event_id;
    tmp.send_pe = e->send_pe;
#ifdef USE_RAND_TIEBREAKER
    tmp.sig = e->sig;
#endif

    memcpy(buffer, &tmp, sizeof(io_event_store));
    return sizeof(io_event_store);
}

size_t io_event_deserialize (tw_event *e, void *buffer) {
    io_event_store tmp;
    memcpy(&tmp, buffer, sizeof(io_event_store));
    e->critical_path = tmp.critical_path;

    memcpy(&(e->cv), &(tmp.cv), sizeof(tw_bf));
    e->dest_lp = (tw_lp *) tmp.dest_lp; // ROSS HACK: e->dest_lp is GID for a bit
    //undo pointer to GID conversion
    if (g_tw_mapping == LINEAR) {
        e->src_lp = g_tw_lp[((tw_lpid)tmp.src_lp) - g_tw_lp_offset];
    } else if (g_tw_mapping == CUSTOM) {
        e->src_lp = g_tw_custom_lp_global_to_local_map((tw_lpid)tmp.src_lp);
    } else {
        tw_error(TW_LOC, "RIO ERROR: Unsupported mapping");
    }
    e->recv_ts = tmp.recv_ts;
    // guard-agent 2026-05-08: restore framework identity fields so the
    // restored event is unique inside the priority queue.
    e->event_id = tmp.event_id;
    e->send_pe = tmp.send_pe;
#ifdef USE_RAND_TIEBREAKER
    e->sig = tmp.sig;
#endif
    return sizeof(io_event_store);
}
