#ifndef SMILEI_PROJECTOR_PROJECTOR2D4ORDERGPU_H
#define SMILEI_PROJECTOR_PROJECTOR2D4ORDERGPU_H

#include "Projector2D.h"

/// Particle to grid projector (~~dual to the grid to particle the interpolator
/// does)
///
/// NOTE: we could have inherited from Projector2D4Order but the interface is final for most of the member functions
///
class Projector2D4OrderGPU : public Projector2D
{
public:
    Projector2D4OrderGPU( Params &parameters, Patch *a_patch );
    ~Projector2D4OrderGPU();

    /// For initialization and diags, doesn't use the standard scheme
    ///
    void basic( double      *rhoj,
                Particles   &particles,
                unsigned int ipart,
                unsigned int type,
                int bin_shift = 0 ) override;

    /// Project global current densities (ionize)
    ///
    void ionizationCurrents( Field      *Jx,
                             Field      *Jy,
                             Field      *Jz,
                             Particles  &particles,
                             int         ipart,
                             LocalFields Jion ) override;

    /// Projection wrapper
    ///
    void currentsAndDensityWrapper( ElectroMagn *EMfields,
                                    Particles   &particles,
                                    SmileiMPI   *smpi,
                                    int          istart,
                                    int          iend,
                                    int          ithread,
                                    bool         diag_flag,
                                    bool         is_spectral,
                                    int          ispec,
                                    int          icell     = 0,
                                    int          ipart_ref = 0 ) override;

    /// Project susceptibility, used as source term in envelope equation
    ///
    void susceptibility( ElectroMagn *EMfields,
                         Particles   &particles,
                         double       species_mass,
                         SmileiMPI   *smpi,
                         int          istart,
                         int          iend,
                         int          ithread,
                         int          icell     = 0,
                         int          ipart_ref = 0 ) override;

protected:
    double dt;
    int    not_spectral_;
    bool cell_sorting_;
    unsigned int x_dimension_bin_count_;
    unsigned int y_dimension_bin_count_;
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

};

#endif
