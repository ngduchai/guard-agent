/*
 * checkpoint.h — Thin wrapper around FTI for checkpoint timing.
 *
 * Provides acc_write_time tracking used by miniVite and other
 * FTI-checkpointed applications.
 */
#ifndef LIBCHECKPOINT_CHECKPOINT_H
#define LIBCHECKPOINT_CHECKPOINT_H

#ifdef __cplusplus
extern "C" {
#endif

/* Accumulated checkpoint write time (seconds), defined in main.cpp */
extern double acc_write_time;

#ifdef __cplusplus
}
#endif

#endif /* LIBCHECKPOINT_CHECKPOINT_H */
