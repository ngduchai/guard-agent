#ifndef INC_check_revent_state_check
#define INC_check_revent_state_check

#include "ross-types.h"
#include <stdbool.h>
#include <stdio.h>

typedef void (*save_lp_snapshot_f) (void * into, void const * from);
typedef void (*clean_lp_snapshot_f) (void * state);
typedef bool (*check_states_f) (void * current_state, void const * before_state);
typedef void (*print_lpstate_f) (FILE *, char const * prefix, void * state);
typedef void (*print_lp_snapshot_f) (FILE *, char const * prefix, void * state);
typedef void (*print_event_f) (FILE *, char const * prefix, void * lp_state, void * event_msg);

/*
 * Interface to implement in order to get tighter control over the
 * SEQUENTIAL_ROLLBACK_CHECK synchronization option.
 *
 * SEQUENTIAL_ROLLBACK_CHECK allows to run check if all reversible
 * computations have been properly implemented. By default, there is
 * no need to use this interface in order to run SEQUENTIAL_ROLLBACK_CHECK.
 *
 * If save_lp is not implemented, then the LP struct will be save into the
 * LP snapshot.
 *
 * Often, it is best to start by implementing print_lp.
 *
 * Only the `lptype` is mandatory, everything else can be NULL or zero.
 */
typedef struct crv_lp_snapshotter {
    tw_lptype * lptype;
    size_t sz_storage; // Size of the LP snapshot to save (can be different from actual LP size)
    save_lp_snapshot_f save_lp; // Copies LP state into LP snapshot
    clean_lp_snapshot_f clean_lp; // Cleans LP snapshot (do not call free). Only needed if saving the snapshot allocated something
    check_states_f check_lps; // Checks if the current LP state is the same as the snapshot state
    print_lpstate_f print_lp; // Prints the state of the LP in a human readable way
    print_lp_snapshot_f print_snapshot; // Prints the state of the LP snapshot in a human readable way
    print_event_f print_event; // Prints the contents of the message the LP processes
} crv_lp_snapshotter;


// Adding LP snapshotter
void crv_add_custom_lp_snapshot(crv_lp_snapshotter *);


/*
 * Internal struct, not to be modified by model developer.
 */
typedef struct crv_lpstate_snapshot_internal {
    void * state;
    tw_rng_stream rng;
    tw_rng_stream core_rng;
    unsigned int triggered_gvt_hook;
} crv_lpstate_snapshot_internal;

size_t crv_init_snapshots(void);
void crv_copy_lpstate(crv_lpstate_snapshot_internal * into, tw_lp const * clp);
void crv_clean_lpstate(crv_lpstate_snapshot_internal * state, tw_lp const * clp);
void crv_check_lpstates(
         tw_lp * clp,
         tw_event * cev,
         crv_lpstate_snapshot_internal const * before_state,
         char const * before_msg,
         char const * after_msg
);

#endif
