/**
 *
 * @file pztrsm.c
 *
 * @copyright 2009-2015 The University of Tennessee and The University of
 *                      Tennessee Research Foundation. All rights reserved.
 * @copyright 2012-2025 Bordeaux INP, CNRS (LaBRI UMR 5800), Inria,
 *                      Univ. Bordeaux. All rights reserved.
 *
 ***
 *
 * @brief Chameleon ztrsm parallel algorithm
 *
 * @version 1.4.0
 * @comment This file has been automatically generated
 *          from Plasma 2.5.0 for CHAMELEON 0.9.2
 * @author Jakub Kurzak
 * @author Hatem Ltaief
 * @author Mathieu Faverge
 * @author Emmanuel Agullo
 * @author Cedric Castagnede
 * @author Florent Pruvost
 * @date 2025-12-19
 * @precisions normal z -> s d c
 *
 */
#include "control/common.h"

#define A(m,n) A,  m,  n
#define B(m,n) B,  m,  n
/**
 *  Parallel tile triangular solve - dynamic scheduling
 */
void chameleon_pztrsm( cham_side_t side, cham_uplo_t uplo, cham_trans_t trans, cham_diag_t diag,
                       CHAMELEON_Complex64_t alpha, CHAM_desc_t *A, CHAM_desc_t *B,
                       RUNTIME_sequence_t *sequence, RUNTIME_request_t *request )
{
    CHAM_context_t *chamctxt;
    RUNTIME_option_t options;

    int k, m, n;
    int tempkm, tempkn, tempmm, tempnn;

    CHAMELEON_Complex64_t zone       = (CHAMELEON_Complex64_t) 1.0;
    CHAMELEON_Complex64_t mzone      = (CHAMELEON_Complex64_t)-1.0;
    CHAMELEON_Complex64_t minvalpha  = (CHAMELEON_Complex64_t)-1.0 / alpha;
    CHAMELEON_Complex64_t lalpha;

    chamctxt = chameleon_context_self();
    if (sequence->status != CHAMELEON_SUCCESS) {
        return;
    }
    RUNTIME_options_init(&options, chamctxt, sequence, request);
    /*
     *  ChamLeft / ChamUpper / ChamNoTrans
     */
    if (side == ChamLeft) {
        if (uplo == ChamUpper) {
            if (trans == ChamNoTrans) {
                for (k = 0; k < B->mt; k++) {
                    tempkm = B->get_blkdim( B, B->mt-1-k, DIM_m, B->m );
                    lalpha = k == 0 ? alpha : zone;
                    for (n = 0; n < B->nt; n++) {
                        tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempkm, tempnn, A->mb,
                            lalpha, A(B->mt-1-k, B->mt-1-k),  /* lda * tempkm */
                                    B(B->mt-1-k,        n)); /* ldb * tempnn */
                    }
                    chameleon_data_flush( sequence, A(B->mt-1-k, B->mt-1-k), request->flush );
                    for (m = k+1; m < B->mt; m++) {
                        for (n = 0; n < B->nt; n++) {
                            tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                            INSERT_TASK_zgemm(
                                &options,
                                ChamNoTrans, ChamNoTrans,
                                B->mb, tempnn, tempkm, A->mb,
                                mzone,  A(B->mt-1-m, B->mt-1-k),
                                        B(B->mt-1-k, n       ),
                                lalpha, B(B->mt-1-m, n       ));
                        }
                        chameleon_data_flush( sequence, A(B->mt-1-m, B->mt-1-k), request->flush );
                    }
                    for (n = 0; n < B->nt; n++) {
                        chameleon_data_flush( sequence, B(B->mt-1-k, n), request->flush );
                    }
                }
            }
            /*
             *  ChamLeft / ChamUpper / Cham[Conj]Trans
             */
            else {
                for (k = 0; k < B->mt; k++) {
                    tempkm = B->get_blkdim( B, k, DIM_m, B->m );
                    lalpha = k == 0 ? alpha : zone;
                    for (n = 0; n < B->nt; n++) {
                        tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempkm, tempnn, A->mb,
                            lalpha, A(k, k),
                                    B(k, n));
                    }
                    chameleon_data_flush( sequence, A(k, k), request->flush );
                    for (m = k+1; m < B->mt; m++) {
                        tempmm = B->get_blkdim( B, m, DIM_m, B->m );
                        for (n = 0; n < B->nt; n++) {
                            tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                            INSERT_TASK_zgemm(
                                &options,
                                trans, ChamNoTrans,
                                tempmm, tempnn, B->mb, A->mb,
                                mzone,  A(k, m),
                                        B(k, n),
                                lalpha, B(m, n));
                        }
                        chameleon_data_flush( sequence, A(k, m), request->flush );
                    }
                    for (n = 0; n < B->nt; n++) {
                        chameleon_data_flush( sequence, B(k, n), request->flush );
                    }

                }
            }
        }
        /*
         *  ChamLeft / ChamLower / ChamNoTrans
         */
        else {
            if (trans == ChamNoTrans) {
                for (k = 0; k < B->mt; k++) {
                    tempkm = B->get_blkdim( B, k, DIM_m, B->m );
                    lalpha = k == 0 ? alpha : zone;
                    for (n = 0; n < B->nt; n++) {
                        tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempkm, tempnn, A->mb,
                            lalpha, A(k, k),
                                    B(k, n));
                    }
                    chameleon_data_flush( sequence, A(k, k), request->flush );
                    for (m = k+1; m < B->mt; m++) {
                        tempmm = B->get_blkdim( B, m, DIM_m, B->m );
                        for (n = 0; n < B->nt; n++) {
                            tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                            INSERT_TASK_zgemm(
                                &options,
                                ChamNoTrans, ChamNoTrans,
                                tempmm, tempnn, B->mb, A->mb,
                                mzone,  A(m, k),
                                        B(k, n),
                                lalpha, B(m, n));
                        }
                        chameleon_data_flush( sequence, A(m, k), request->flush );
                    }
                    for (n = 0; n < B->nt; n++) {
                        chameleon_data_flush( sequence, B(k, n), request->flush );
                    }
                }
            }
            /*
             *  ChamLeft / ChamLower / Cham[Conj]Trans
             */
            else {
                for (k = 0; k < B->mt; k++) {
                    tempkm = B->get_blkdim( B, B->mt-1-k, DIM_m, B->m );
                    lalpha = k == 0 ? alpha : zone;
                    for (n = 0; n < B->nt; n++) {
                        tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempkm, tempnn, A->mb,
                            lalpha, A(B->mt-1-k, B->mt-1-k),
                                    B(B->mt-1-k,        n));
                    }
                    chameleon_data_flush( sequence, A(B->mt-1-k, B->mt-1-k), request->flush );
                    for (m = k+1; m < B->mt; m++) {
                        for (n = 0; n < B->nt; n++) {
                            tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                            INSERT_TASK_zgemm(
                                &options,
                                trans, ChamNoTrans,
                                B->mb, tempnn, tempkm, A->mb,
                                mzone,  A(B->mt-1-k, B->mt-1-m),
                                        B(B->mt-1-k, n       ),
                                lalpha, B(B->mt-1-m, n       ));
                        }
                        chameleon_data_flush( sequence, A(B->mt-1-k, B->mt-1-m), request->flush );
                    }
                    for (n = 0; n < B->nt; n++) {
                        chameleon_data_flush( sequence, B(B->mt-1-k, n), request->flush );
                    }
                }
            }
        }
    }
    /*
     *  ChamRight / ChamUpper / ChamNoTrans
     */
    else {
        if (uplo == ChamUpper) {
            if (trans == ChamNoTrans) {
                for (k = 0; k < B->nt; k++) {
                    tempkn = B->get_blkdim( B, k, DIM_n, B->n );
                    lalpha = k == 0 ? alpha : zone;
                    for (m = 0; m < B->mt; m++) {
                        tempmm = B->get_blkdim( B, m, DIM_m, B->m );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempmm, tempkn, A->mb,
                            lalpha, A(k, k),  /* lda * tempkn */
                                    B(m, k)); /* ldb * tempkn */
                    }
                    chameleon_data_flush( sequence, A(k, k), request->flush );
                    for (m = 0; m < B->mt; m++) {
                        tempmm = B->get_blkdim( B, m, DIM_m, B->m );
                        for (n = k+1; n < B->nt; n++) {
                            tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                            INSERT_TASK_zgemm(
                                &options,
                                ChamNoTrans, ChamNoTrans,
                                tempmm, tempnn, B->mb, A->mb,
                                mzone,  B(m, k),  /* ldb * B->mb   */
                                        A(k, n),  /* lda * tempnn */
                                lalpha, B(m, n)); /* ldb * tempnn */
                        }
                        chameleon_data_flush( sequence, B(m, k), request->flush );
                    }
                    for (n = k+1; n < B->nt; n++) {
                        chameleon_data_flush( sequence, A(k, n), request->flush );
                    }
                }
            }
            /*
             *  ChamRight / ChamUpper / Cham[Conj]Trans
             */
            else {
                for (k = 0; k < B->nt; k++) {
                    tempkn = B->get_blkdim( B, B->nt-1-k, DIM_n, B->n );
                    for (m = 0; m < B->mt; m++) {
                        tempmm = B->get_blkdim( B, m, DIM_m, B->m );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempmm, tempkn, A->mb,
                            alpha, A(B->nt-1-k, B->nt-1-k),  /* lda * tempkn */
                                   B(       m, B->nt-1-k)); /* ldb * tempkn */
                        chameleon_data_flush( sequence, A(B->nt-1-k, B->nt-1-k), request->flush );

                        for (n = k+1; n < B->nt; n++) {
                            INSERT_TASK_zgemm(
                                &options,
                                ChamNoTrans, trans,
                                tempmm, B->nb, tempkn, A->mb,
                                minvalpha, B(m,        B->nt-1-k),  /* ldb  * tempkn */
                                           A(B->nt-1-n, B->nt-1-k), /* A->mb * tempkn (Never last row) */
                                zone,      B(m,        B->nt-1-n)); /* ldb  * B->nb   */
                        }
                        chameleon_data_flush( sequence, B(m,        B->nt-1-k), request->flush );
                    }
                    for (n = k+1; n < B->nt; n++) {
                        chameleon_data_flush( sequence, A(B->nt-1-n, B->nt-1-k), request->flush );
                    }
                }
            }
        }
        /*
         *  ChamRight / ChamLower / ChamNoTrans
         */
        else {
            if (trans == ChamNoTrans) {
                for (k = 0; k < B->nt; k++) {
                    tempkn = B->get_blkdim( B, B->nt-1-k, DIM_n, B->n );
                    lalpha = k == 0 ? alpha : zone;
                    for (m = 0; m < B->mt; m++) {
                        tempmm = B->get_blkdim( B, m, DIM_m, B->m );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempmm, tempkn, A->mb,
                            lalpha, A(B->nt-1-k, B->nt-1-k),  /* lda * tempkn */
                                    B(       m, B->nt-1-k)); /* ldb * tempkn */
                        chameleon_data_flush( sequence, A(B->nt-1-k, B->nt-1-k), request->flush );

                        for (n = k+1; n < B->nt; n++) {
                            INSERT_TASK_zgemm(
                                &options,
                                ChamNoTrans, ChamNoTrans,
                                tempmm, B->nb, tempkn, A->mb,
                                mzone,  B(m,        B->nt-1-k),  /* ldb * tempkn */
                                        A(B->nt-1-k, B->nt-1-n),  /* lda * B->nb   */
                                lalpha, B(m,        B->nt-1-n)); /* ldb * B->nb   */
                        }
                        chameleon_data_flush( sequence, B(m,        B->nt-1-k), request->flush );
                    }
                    for (n = k+1; n < B->nt; n++) {
                        chameleon_data_flush( sequence, A(B->nt-1-k, B->nt-1-n), request->flush );
                    }
                }
            }
            /*
             *  ChamRight / ChamLower / Cham[Conj]Trans
             */
            else {
                for (k = 0; k < B->nt; k++) {
                    tempkn = B->get_blkdim( B, k, DIM_n, B->n );
                    for (m = 0; m < B->mt; m++) {
                        tempmm = B->get_blkdim( B, m, DIM_m, B->m );
                        INSERT_TASK_ztrsm(
                            &options,
                            side, uplo, trans, diag,
                            tempmm, tempkn, A->mb,
                            alpha, A(k, k),  /* lda * tempkn */
                                   B(m, k)); /* ldb * tempkn */
                        chameleon_data_flush( sequence, A(k, k), request->flush );

                        for (n = k+1; n < B->nt; n++) {
                            tempnn = B->get_blkdim( B, n, DIM_n, B->n );
                            INSERT_TASK_zgemm(
                                &options,
                                ChamNoTrans, trans,
                                tempmm, tempnn, B->mb, A->mb,
                                minvalpha, B(m, k),  /* ldb  * tempkn */
                                           A(n, k), /* ldan * tempkn */
                                zone,      B(m, n)); /* ldb  * tempnn */
                        }
                        chameleon_data_flush( sequence, B(m, k), request->flush );
                    }
                    for (n = k+1; n < B->nt; n++) {
                        chameleon_data_flush( sequence, A(n, k), request->flush );
                    }

                }
            }
        }
    }
    RUNTIME_options_finalize(&options, chamctxt);
}
