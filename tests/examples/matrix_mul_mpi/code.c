#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

// Random double in [0, 1)
static double drand01(void) {
    return (double)rand() / (double)RAND_MAX;
}

int main(int argc, char** argv) {
    int rank, size;
    int i, j, k;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    // Parse arguments: matrix size N (required), number of pairs T (optional, default 1)
    int N = 4;
    int T = 1;
    if (argc >= 2) {
        N = atoi(argv[1]);
        if (argc >= 3) {
            T = atoi(argv[2]);
        }
    }
    if (N <= 0 || T <= 0) {
        if (rank == 0) {
            fprintf(stderr, "Usage: %s <matrix_size> [num_pairs]\n", argv[0]);
            fprintf(stderr, "  matrix_size: N for NxN matrices (must be > 0 and divisible by number of MPI processes)\n");
            fprintf(stderr, "  num_pairs:   number of matrix pairs to multiply and sum (default 1)\n");
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    if (N % size != 0) {
        if (rank == 0) {
            fprintf(stderr, "Error: N=%d must be divisible by number of MPI processes=%d.\n", N, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    const int rows_per_rank = N / size;

    // Allocate arrays (contiguous layout for variable dimensions)
    double* first_input  = (double*)malloc((size_t)T * N * N * sizeof(double));
    double* second_input = (double*)malloc((size_t)T * N * N * sizeof(double));
    double* results      = (double*)malloc((size_t)N * N * sizeof(double));
    double* local_A      = (double*)malloc((size_t)rows_per_rank * N * sizeof(double));
    double* local_C      = (double*)malloc((size_t)rows_per_rank * N * sizeof(double));
    double* C            = (double*)malloc((size_t)N * N * sizeof(double));

    if (!first_input || !second_input || !results || !local_A || !local_C || !C) {
        if (rank == 0) fprintf(stderr, "Error: allocation failed.\n");
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    for (i = 0; i < N * N; i++) results[i] = 0.0;

    // Initialize input matrices on root only
    if (rank == 0) {
        for (int t = 0; t < T; t++) {
            for (int ii = 0; ii < N; ii++) {
                for (int jj = 0; jj < N; jj++) {
                    first_input[t * N * N + ii * N + jj] = drand01();
                    second_input[t * N * N + ii * N + jj] = drand01();
                }
            }
        }
    }

    for (int t = 0; t < T; t++) {
        double* Bt = second_input + (size_t)t * N * N;

        MPI_Bcast(Bt, N * N, MPI_DOUBLE, 0, MPI_COMM_WORLD);

        MPI_Scatter(first_input + (size_t)t * N * N, rows_per_rank * N, MPI_DOUBLE,
                    local_A, rows_per_rank * N, MPI_DOUBLE,
                    0, MPI_COMM_WORLD);

        for (i = 0; i < rows_per_rank; i++) {
            for (j = 0; j < N; j++) {
                double sum = 0.0;
                for (k = 0; k < N; k++) {
                    sum += local_A[i * N + k] * Bt[k * N + j];
                }
                local_C[i * N + j] = sum;
            }
        }

        MPI_Gather(local_C, rows_per_rank * N, MPI_DOUBLE,
                   C, rows_per_rank * N, MPI_DOUBLE,
                   0, MPI_COMM_WORLD);

        if (rank == 0) {
            for (int ii = 0; ii < N; ii++) {
                for (int jj = 0; jj < N; jj++) {
                    results[ii * N + jj] += C[ii * N + jj];
                }
            }
        }
    }

    if (rank == 0) {
        printf("==== Accumulated result over %d matrix pairs (N=%d) ====\n", T, N);
        for (i = 0; i < N; i++) {
            for (j = 0; j < N; j++) {
                printf("%8.4f ", results[i * N + j]);
            }
            printf("\n");
        }
        printf("\n");
    }

    free(first_input);
    free(second_input);
    free(results);
    free(local_A);
    free(local_C);
    free(C);

    MPI_Finalize();
    return 0;
}
