//! HIP CUDA implementation

#ifndef Projector2D4OrderGPUKernelCUDAHIP_H
#define Projector2D4OrderGPUKernelCUDAHIP_H

#if defined( SMILEI_ACCELERATOR_GPU )

#if defined( __HIP__ )
    #include <hip/hip_runtime.h>
#elif defined( __NVCC__ )
    #include <cuda_runtime.h>
    #include <cuda.h>
#endif

#include "Params.h"
#include "gpu.h"



namespace cudahip2d4Order {
//static
void currentDepositionKernel2D4Order( double *__restrict__ host_Jx,
                               double *__restrict__ host_Jy,
                               double *__restrict__ host_Jz,
                               int Jx_size,
                               int Jy_size,
                               int Jz_size,
                               const double *__restrict__ device_particle_position_x,
                               const double *__restrict__ device_particle_position_y,
                               const double *__restrict__ device_particle_momentum_z,
                               const short *__restrict__ device_particle_charge,
                               const double *__restrict__ device_particle_weight,
                               const int *__restrict__ host_bin_index,
                               unsigned int x_dimension_bin_count,
                               unsigned int y_dimension_bin_count,
                               const double *__restrict__ host_invgf_,
                               const int *__restrict__ host_iold_,
                               const double *__restrict__ host_deltaold_,
                               double inv_cell_volume,
                               double dx_inv,
                               double dy_inv,
                               double dx_ov_dt,
                               double dy_ov_dt,
                               int    i_domain_begin,
                               int    j_domain_begin,
                               int    nprimy,
                               int    not_spectral_,
                               bool cell_sorting );

//static 
void currentAndDensityDepositionKernel2D4Order(
                                double *__restrict__ host_Jx,
                                double *__restrict__ host_Jy,
                                double *__restrict__ host_Jz,
                                double *__restrict__ host_rho,
                                int Jx_size,
                                int Jy_size,
                                int Jz_size,
                                int rho_size,
                                const double *__restrict__ device_particle_position_x,
                                const double *__restrict__ device_particle_position_y,
                                const double *__restrict__ device_particle_momentum_z,
                                const short *__restrict__ device_particle_charge,
                                const double *__restrict__ device_particle_weight,
                                const int *__restrict__ host_bin_index,
                                unsigned int x_dimension_bin_count,
                                unsigned int y_dimension_bin_count,
                                const double *__restrict__ host_invgf_,
                                const int *__restrict__ host_iold_,
                                const double *__restrict__ host_deltaold_,
                                double inv_cell_volume,
                                double dx_inv,
                                double dy_inv,
                                double dx_ov_dt,
                                double dy_ov_dt,
                                int    i_domain_begin,
                                int    j_domain_begin,
                                int    nprimy,
                                int    not_spectral_,
                                bool cell_sorting );

    static constexpr double dble_1_ov_384   = 1.0/384.0;
    static constexpr double dble_1_ov_48    = 1.0/48.0;
    static constexpr double dble_1_ov_16    = 1.0/16.0;
    static constexpr double dble_1_ov_12    = 1.0/12.0;
    static constexpr double dble_1_ov_24    = 1.0/24.0;
    static constexpr double dble_19_ov_96   = 19.0/96.0;
    static constexpr double dble_11_ov_24   = 11.0/24.0;
    static constexpr double dble_1_ov_4     = 1.0/4.0;
    static constexpr double dble_1_ov_6     = 1.0/6.0;
    static constexpr double dble_115_ov_192 = 115.0/192.0;
    static constexpr double dble_5_ov_8     = 5.0/8.0;

} // namespace cudahip2d4Order

#endif
#endif

