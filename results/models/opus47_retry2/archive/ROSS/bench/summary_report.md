# Validation Summary Report

Generated: 2026-06-07 10:15 UTC

---

## 1. Correctness

**Overall status: ✅ PASS** (4/4 tests passed)

| # | Method | Score | Status | Message |
|---|--------|-------|--------|---------|
| 1 | numeric-tolerance [VeloC, failure-prone] | 2.52904e+11 | ✅ PASS | max_abs_diff=2.529e+11, max_rel_diff=1.456e-02 (atol=5.000e-02, rtol=5.000e-02) |
| 2 | exit_code [VeloC, failure-prone] | 0 | ✅ PASS | exit_code=0 |
| 3 | numeric-tolerance [VeloC, failure-free] | 0 | ✅ PASS | max_abs_diff=0.000e+00, max_rel_diff=0.000e+00 (atol=5.000e-02, rtol=5.000e-02) |
| 4 | exit_code [VeloC, failure-free] | 0 | ✅ PASS | exit_code=0 |

---

## 2. Performance Metrics (Failure-Injection Scenarios)

### Execution Time – VeloC (Resilient) (seconds)

| Scenario | Mean ± Std |
|----------|------------|
| small-once | 57.95 ± 0.03 |

### Resilience Overhead (seconds)

*Total runtime (all attempts) minus baseline (original, failure-free).*
*Includes checkpoint, recovery, and retry costs.*

| Scenario | VeloC (Resilient) |
|----------|---|
| small-once | N/A |

### Checkpoint Storage (MiB)

| Scenario | VeloC (Resilient) |
|----------|---|
| small-once | 1.46 |

### Memory Usage – VeloC (Resilient) (MiB)

| Scenario | Average | Median | P90 | P99 |
|----------|---------|--------|-----|-----|
| small-once | 304.87 | 311.53 | 311.91 | 312.31 |

---

## 3. Plots

### Execution Time (Failure-Injection, Resilient)

![Execution Time (Failure-Injection, Resilient)](plots/execution_time.png)

### Resilience Overhead vs No-Failure Baseline (%)

![Resilience Overhead vs No-Failure Baseline (%)](plots/resilience_overhead.png)

### Resilience Overhead vs No-Failure Baseline (seconds)

![Resilience Overhead vs No-Failure Baseline (seconds)](plots/resilience_overhead_absolute.png)

### Checkpoint Storage Size

![Checkpoint Storage Size](plots/checkpoint_size.png)

### Memory Usage (Avg / Median / P90 / P99)

![Memory Usage (Avg / Median / P90 / P99)](plots/memory_usage.png)

---

*End of report.*
