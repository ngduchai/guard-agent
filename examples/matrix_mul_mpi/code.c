#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

#define N 4 // Matrix size (NxN)

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

    if (N % size != 0) {
        if (rank == 0) {
            fprintf(stderr, "Error: N=%d must be divisible by number of MPI processes=%d.\n", N, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    // Number of random generations / test cases
    int T = 1;
    if (argc >= 2) {
        T = atoi(argv[1]);
        if (T <= 0) T = 1;
    }

    const int rows_per_rank = N / size;

    // Arrays of input matrices A and B, and accumulated result matrix.
    // first_input[t] and second_input[t] hold the t-th input matrices.
    double first_input[T][N][N], second_input[T][N][N];
    double results[N][N] = {0.0};

    // Local buffers (rows_per_rank x N)
    double local_A[rows_per_rank][N];
    double local_C[rows_per_rank][N];

    // Scratch matrix on root to gather each pair-wise product.
    double C[N][N];

    // Initialize input matrices on root only; other ranks don't need the full copies.
    if (rank == 0) {
        for (int t = 0; t < T; t++) {
            for (int ii = 0; ii < N; ii++) {
                for (int jj = 0; jj < N; jj++) {
                    first_input[t][ii][jj] = drand01();
                    second_input[t][ii][jj] = drand01();
                }
            }
        }
    }

    for (int t = 0; t < T; t++) {

        // Broadcast B (second_input[t]) to all processes as a full N x N matrix.
        MPI_Bcast(&second_input[t][0][0], N * N, MPI_DOUBLE, 0, MPI_COMM_WORLD);

        // Scatter rows of A (first_input[t]) across ranks.
        MPI_Scatter(&first_input[t][0][0], rows_per_rank * N, MPI_DOUBLE,
                    local_A, rows_per_rank * N, MPI_DOUBLE,
                    0, MPI_COMM_WORLD);

        // Local matrix multiplication
        for (i = 0; i < rows_per_rank; i++) {
            for (j = 0; j < N; j++) {
                double sum = 0.0;
                for (k = 0; k < N; k++) {
                    sum += local_A[i][k] * B[k][j];
                }
                local_C[i][j] = sum;
            }
        }

        // Gather results of this pair-wise multiplication into C on root.
        MPI_Gather(local_C, rows_per_rank * N, MPI_DOUBLE,
                   C, rows_per_rank * N, MPI_DOUBLE,
                   0, MPI_COMM_WORLD);

        // On root, accumulate this pair's product into the global results matrix.
        if (rank == 0) {
            for (int ii = 0; ii < N; ii++) {
                for (int jj = 0; jj < N; jj++) {
                    results[ii][jj] += C[ii][jj];
                }
            }
        }
    }

    // Print the accumulated results matrix on root.
    if (rank == 0) {
        printf("==== Accumulated result over %d matrix pairs ====\n", T);
        for (i = 0; i < N; i++) {
            for (j = 0; j < N; j++) {
                printf("%8.4f ", results[i][j]);
            }
            printf("\n");
        }
        printf("\n");
    }

    MPI_Finalize();
    return 0;
}