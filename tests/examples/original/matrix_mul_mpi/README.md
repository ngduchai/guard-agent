# Matrix multiplication (MPI)

Brief MPI example: multiplies pairs of N×N matrices in parallel and prints the accumulated result.

- **Arguments:** `matrix_size` (N for N×N matrices), `num_pairs` (T, optional, default 1). The program computes the sum of all T products and prints that accumulated matrix on rank 0.
- **Parallelism:** Rows of the first matrix are distributed across MPI ranks; the second matrix is broadcast; each rank computes its rows of the product, then results are gathered to rank 0.

**Requirements:** An MPI implementation (e.g. Open MPI, MPICH) and CMake 3.9+.

---

## Build

From this directory:

```bash
mkdir build && cd build
cmake ..
make
```

The executable is `build/matrix_mul_mpi`.

---

## Execution

Run with your MPI launcher. The number of processes must divide N.

```bash
# Usage: matrix_mul_mpi <matrix_size> [num_pairs]
# Defaults: matrix_size=4, num_pairs=1 if omitted

# 4x4 matrices, 1 pair (default)
mpirun -np 2 ./matrix_mul_mpi 4

# 8x8 matrices, 3 pairs
mpirun -np 2 ./matrix_mul_mpi 8 3

# 4x4, 5 pairs
mpirun -np 4 ./matrix_mul_mpi 4 5
```

If `N % (number of processes) != 0` or arguments are invalid, the program prints an error and exits.
