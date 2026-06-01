# Validation Summary Report

Generated: 2026-05-31 02:53 UTC

---

## 1. Correctness

**Overall status: ✅ PASS** (4/4 tests passed)

| # | Method | Score | Status | Message |
|---|--------|-------|--------|---------|
| 1 | numeric-tolerance [VeloC, failure-prone] | 1.43051e-06 | ✅ PASS | max_abs_diff=1.431e-06, max_rel_diff=1.276e-15 (atol=1.000e-04, rtol=1.000e-04) |
| 2 | exit_code [VeloC, failure-prone] | 0 | ✅ PASS | exit_code=0 |
| 3 | numeric-tolerance [VeloC, failure-free] | 5.72205e-06 | ✅ PASS | max_abs_diff=5.722e-06, max_rel_diff=1.500e-15 (atol=1.000e-04, rtol=1.000e-04) |
| 4 | exit_code [VeloC, failure-free] | 0 | ✅ PASS | exit_code=0 |

---

## 2. Performance Metrics (Failure-Injection Scenarios)

### Execution Time – VeloC (Resilient) (seconds)

| Scenario | Mean ± Std |
|----------|------------|
| small-once | 84.08 ± 0.04 |

### Resilience Overhead (seconds)

*Total runtime (all attempts) minus baseline (original, failure-free).*
*Includes checkpoint, recovery, and retry costs.*

| Scenario | VeloC (Resilient) |
|----------|---|
| small-once | N/A |

### Checkpoint Storage (MiB)

| Scenario | VeloC (Resilient) |
|----------|---|
| small-once | 333.75 |

### Memory Usage – VeloC (Resilient) (MiB)

| Scenario | Average | Median | P90 | P99 |
|----------|---------|--------|-----|-----|
| small-once | 183.14 | 187.67 | 201.19 | 204.74 |

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
