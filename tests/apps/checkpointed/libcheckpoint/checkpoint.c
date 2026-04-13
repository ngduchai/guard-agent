/*
 * checkpoint.c — Thin wrapper around FTI for checkpoint timing.
 *
 * This is intentionally minimal: the actual FTI calls are made directly
 * in the application source (dspl.hpp / main.cpp). This object just
 * provides the shared acc_write_time symbol when compiled as a
 * standalone translation unit.
 */
#include "checkpoint.h"

/* Default definition — overridden by main.cpp in the final link. */
double acc_write_time = 0.0;
