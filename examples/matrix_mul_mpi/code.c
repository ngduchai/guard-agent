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

    // Matrices
    double A[N][N], B[N][N], C[N][N];

    // Local buffers (rows_per_rank x N)
    double local_A[rows_per_rank][N];
    double local_C[rows_per_rank][N];

    for (int t = 0; t < T; t++) {

        // Root initializes matrices randomly for each test case
        if (rank == 0) {
            // Deterministic seed per test case (change if you want non-deterministic)
            srand(1234 + t);

            for (i = 0; i < N; i++) {
                for (j = 0; j < N; j++) {
                    A[i][j] = drand01();
                    B[i][j] = drand01();
                    C[i][j] = 0.0;
                }
            }
        }

        // Broadcast B to all processes (new B every test case)
        MPI_Bcast(B, N * N, MPI_DOUBLE, 0, MPI_COMM_WORLD);

        // Scatter rows of A (new A every test case)
        MPI_Scatter(A, rows_per_rank * N, MPI_DOUBLE,
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

        // Gather results into C on root
        MPI_Gather(local_C, rows_per_rank * N, MPI_DOUBLE,
                   C, rows_per_rank * N, MPI_DOUBLE,
                   0, MPI_COMM_WORLD);

        // Print result for each test case (optional)
        if (rank == 0) {
            printf("==== Test case %d / %d ====\n", t + 1, T);
            printf("Result Matrix C:\n");
            for (i = 0; i < N; i++) {
                for (j = 0; j < N; j++) {
                    printf("%8.4f ", C[i][j]);
                }
                printf("\n");
            }
            printf("\n");
        }
    }

    MPI_Finalize();
    return 0;
}