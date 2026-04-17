# Comparison Report: art_simple


|                        | **Baseline (no guard-agent)** | **With guard-agent** |
| ---------------------- | ----------------------------- | -------------------- |
| **Correctness**        | not run                       | 2/2 passed           |
| Min SSIM score         | —                             | 1.000000             |
| **Evaluation metrics** |                               |                      |
| Rounds (iterations)    | 5                             | 1                    |
| Total elapsed time     | 37.5m                         | 4.5m                 |
| Wall-clock time        | 37.5m                         | 4.5m                 |
| Total tokens           | 3.8M                          | 1.2M                 |
| Input tokens           | 3.8M                          | 1.2M                 |
| Output tokens          | 29.1K                         | 6.0K                 |
| Final result           | **FAIL**                      | PASS                 |
| **Code changes**       |                               |                      |
| Files modified/added   | 2                             | 5                    |
| Lines added            | +66                           | +1805                |
| Lines removed          | -1                            | -0                   |
| **VeloC API coverage** |                               |                      |
| Header include         | yes                           | yes                  |
| Init/get_client        | yes                           | yes                  |
| Mem_protect            | yes                           | yes                  |
| Checkpoint             | yes                           | yes                  |
| Restart/Restart_test   | yes                           | yes                  |
| Finalize               | **MISSING**                   | yes                  |
| veloc.cfg file         | yes                           | yes                  |


## Correctness Details


| Test                        | Baseline (no guard-agent) | With guard-agent |
| --------------------------- | ------------------------- | ---------------- |
| ssim [VeloC, failure-prone] | —                         | PASS (1.000000)  |
| ssim [VeloC, failure-free]  | —                         | PASS (1.000000)  |


## Files changed by Baseline (no guard-agent)

- `main.cc`: +62 / -1
- `veloc.cfg` (new): +4 / -0

## Files changed by With guard-agent

- `main.cc`: +37 / -0
- `build/CMakeFiles/3.28.3/CompilerIdC/CMakeCCompilerId.c` (new): +880 / -0
- `build/CMakeFiles/3.28.3/CompilerIdCXX/CMakeCXXCompilerId.cpp` (new): +869 / -0
- `build/CMakeFiles/hdf5/cmake_hdf5_test.c` (new): +15 / -0
- `veloc.cfg` (new): +4 / -0

## Per-Iteration Breakdown

### Baseline (no guard-agent)


| Iter | OpenCode time | Validation time | Total  | Tokens  | Passed |
| ---- | ------------- | --------------- | ------ | ------- | ------ |
| 1    | 410.6s        | 113.1s          | 523.7s | 1361.0K | FAIL   |
| 2    | 138.4s        | 116.0s          | 254.4s | 453.7K  | FAIL   |
| 3    | 482.8s        | 127.1s          | 609.9s | 628.7K  | FAIL   |
| 4    | 259.5s        | 126.6s          | 386.1s | 1075.9K | FAIL   |
| 5    | 347.8s        | 125.6s          | 473.4s | 269.6K  | FAIL   |


### With guard-agent


| Iter | OpenCode time | Validation time | Total  | Tokens  | Passed |
| ---- | ------------- | --------------- | ------ | ------- | ------ |
| 1    | 167.5s        | 99.9s           | 267.5s | 1159.5K | PASS   |


