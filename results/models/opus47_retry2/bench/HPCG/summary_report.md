# Validation Summary Report

Generated: 2026-06-06 21:49 UTC

---

## 1. Correctness

**Overall status: ✅ PASS** (4/4 tests passed)

| # | Method | Score | Status | Message |
|---|--------|-------|--------|---------|
| 1 | numeric-tolerance [VeloC, failure-prone] | 5.28972e-38 | ✅ PASS | max_abs_diff=5.290e-38, max_rel_diff=3.919e-15 (atol=1.000e-12, rtol=1.000e-12) |
| 2 | exit_code [VeloC, failure-prone] | 0 | ✅ PASS | exit_code=0 |
| 3 | numeric-tolerance [VeloC, failure-free] | 5.28972e-38 | ✅ PASS | max_abs_diff=5.290e-38, max_rel_diff=3.919e-15 (atol=1.000e-12, rtol=1.000e-12) |
| 4 | exit_code [VeloC, failure-free] | 0 | ✅ PASS | exit_code=0 |

---

## 2. Performance Metrics (Failure-Injection Scenarios)

### Execution Time – VeloC (Resilient) (seconds)

| Scenario | Mean ± Std |
|----------|------------|
| small-once | 54.09 ± 0.07 |

### Resilience Overhead (seconds)

*Total runtime (all attempts) minus baseline (original, failure-free).*
*Includes checkpoint, recovery, and retry costs.*

| Scenario | VeloC (Resilient) |
|----------|---|
| small-once | N/A |

### Checkpoint Storage (MiB)

| Scenario | VeloC (Resilient) |
|----------|---|
| small-once | 2.03 |

### Memory Usage – VeloC (Resilient) (MiB)

| Scenario | Average | Median | P90 | P99 |
|----------|---------|--------|-----|-----|
| small-once | 195.90 | 201.58 | 201.69 | 201.70 |

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
