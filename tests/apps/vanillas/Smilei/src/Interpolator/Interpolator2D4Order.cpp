#include "Interpolator2D4Order.h"

#include <cmath>
#include <iostream>

#include "ElectroMagn.h"
#include "Field2D.h"
#include "Particles.h"

using namespace std;


// ---------------------------------------------------------------------------------------------------------------------
// Creator for Interpolator2D4Order
// ---------------------------------------------------------------------------------------------------------------------
Interpolator2D4Order::Interpolator2D4Order( Params &params, Patch *patch ) : Interpolator2D( patch )
{

    d_inv_[0] = 1.0/params.cell_length[0];
    d_inv_[1] = 1.0/params.cell_length[1];

    //double defined for use in coefficients
    dble_1_ov_384 = 1.0/384.0;
    dble_1_ov_48 = 1.0/48.0;
    dble_1_ov_16 = 1.0/16.0;
    dble_1_ov_12 = 1.0/12.0;
    dble_1_ov_24 = 1.0/24.0;
    dble_19_ov_96 = 19.0/96.0;
    dble_11_ov_24 = 11.0/24.0;
    dble_1_ov_4 = 1.0/4.0;
    dble_1_ov_6 = 1.0/6.0;
    dble_115_ov_192 = 115.0/192.0;
    dble_5_ov_8 = 5.0/8.0;

}


// ---------------------------------------------------------------------------------------------------------------------
// 2nd Order Interpolation of the fields at a the particle position (3 nodes are used)
// ---------------------------------------------------------------------------------------------------------------------
void Interpolator2D4Order::fields( ElectroMagn *EMfields, Particles &particles, int ipart, int nparts, double *ELoc, double *BLoc )
{
    // Static cast of the electromagnetic fields
    Field2D *Ex2D = static_cast<Field2D *>( EMfields->Ex_ );
    Field2D *Ey2D = static_cast<Field2D *>( EMfields->Ey_ );
    Field2D *Ez2D = static_cast<Field2D *>( EMfields->Ez_ );
    Field2D *Bx2D = static_cast<Field2D *>( EMfields->Bx_m );
    Field2D *By2D = static_cast<Field2D *>( EMfields->By_m );
    Field2D *Bz2D = static_cast<Field2D *>( EMfields->Bz_m );

    // Normalized particle position
    double xpn = particles.position( 0, ipart )*d_inv_[0];
    double ypn = particles.position( 1, ipart )*d_inv_[1];
    // Calculate coeffs
    int idx_p[2], idx_d[2];
    double delta_p[2];
    double coeffxp[5], coeffyp[5];
    double coeffxd[5], coeffyd[5];
    coeffs( xpn, ypn, idx_p, idx_d, coeffxp, coeffyp, coeffxd, coeffyd, delta_p );

    // Interpolation of Ex^(d,p)
    *( ELoc+0*nparts ) = compute( &coeffxd[2], &coeffyp[2], Ex2D, idx_d[0], idx_p[1] );
    // Interpolation of Ey^(p,d)
    *( ELoc+1*nparts ) = compute( &coeffxp[2], &coeffyd[2], Ey2D, idx_p[0], idx_d[1] );
    // Interpolation of Ez^(p,p)
    *( ELoc+2*nparts ) = compute( &coeffxp[2], &coeffyp[2], Ez2D, idx_p[0], idx_p[1] );
    // Interpolation of Bx^(p,d)
    *( BLoc+0*nparts ) = compute( &coeffxp[2], &coeffyd[2], Bx2D, idx_p[0], idx_d[1] );
    // Interpolation of By^(d,p)
    *( BLoc+1*nparts ) = compute( &coeffxd[2], &coeffyp[2], By2D, idx_d[0], idx_p[1] );
    // Interpolation of Bz^(d,d)
    *( BLoc+2*nparts ) = compute( &coeffxd[2], &coeffyd[2], Bz2D, idx_d[0], idx_d[1] );
} // END Interpolator2D4Order

void Interpolator2D4Order::fieldsAndCurrents( ElectroMagn *EMfields, Particles &particles, SmileiMPI *smpi, int *istart, int *, int ithread, LocalFields *JLoc, double *RhoLoc )
{

    int ipart = *istart;

    double *ELoc = &( smpi->dynamics_Epart[ithread][ipart] );
    double *BLoc = &( smpi->dynamics_Bpart[ithread][ipart] );

    // Interpolate E, B
    // Compute coefficient for ipart position
    // Static cast of the electromagnetic fields
    Field2D *Ex2D = static_cast<Field2D *>( EMfields->Ex_ );
    Field2D *Ey2D = static_cast<Field2D *>( EMfields->Ey_ );
    Field2D *Ez2D = static_cast<Field2D *>( EMfields->Ez_ );
    Field2D *Bx2D = static_cast<Field2D *>( EMfields->Bx_m );
    Field2D *By2D = static_cast<Field2D *>( EMfields->By_m );
    Field2D *Bz2D = static_cast<Field2D *>( EMfields->Bz_m );
    Field2D *Jx2D = static_cast<Field2D *>( EMfields->Jx_ );
    Field2D *Jy2D = static_cast<Field2D *>( EMfields->Jy_ );
    Field2D *Jz2D = static_cast<Field2D *>( EMfields->Jz_ );
    Field2D *Rho2D= static_cast<Field2D *>( EMfields->rho_ );

    // Normalized particle position
    double xpn = particles.position( 0, ipart )*d_inv_[0];
    double ypn = particles.position( 1, ipart )*d_inv_[1];
    // Calculate coeffs
    int idx_p[2], idx_d[2];
    double delta_p[2];
    double coeffxp[5], coeffyp[5];
    double coeffxd[5], coeffyd[5];
    coeffs( xpn, ypn, idx_p, idx_d, coeffxp, coeffyp, coeffxd, coeffyd, delta_p );

    int nparts( particles.numberOfParticles() );

    // Interpolation of Ex^(d,p)
    *( ELoc+0*nparts ) =  compute( &coeffxd[2], &coeffyp[2], Ex2D, idx_d[0], idx_p[1] );
    // Interpolation of Ey^(p,d)
    *( ELoc+1*nparts ) = compute( &coeffxp[2], &coeffyd[2], Ey2D, idx_p[0], idx_d[1] );
    // Interpolation of Ez^(p,p)
    *( ELoc+2*nparts ) = compute( &coeffxp[2], &coeffyp[2], Ez2D, idx_p[0], idx_p[1] );
    // Interpolation of Bx^(p,d)
    *( BLoc+0*nparts ) = compute( &coeffxp[2], &coeffyd[2], Bx2D, idx_p[0], idx_d[1] );
    // Interpolation of By^(d,p)
    *( BLoc+1*nparts ) = compute( &coeffxd[2], &coeffyp[2], By2D, idx_d[0], idx_p[1] );
    // Interpolation of Bz^(d,d)
    *( BLoc+2*nparts ) = compute( &coeffxd[2], &coeffyd[2], Bz2D, idx_d[0], idx_d[1] );
    // Interpolation of Jx^(d,p)
    JLoc->x = compute( &coeffxd[2], &coeffyp[2], Jx2D, idx_d[0], idx_p[1] );
    // Interpolation of Ey^(p,d)
    JLoc->y = compute( &coeffxp[2], &coeffyd[2], Jy2D, idx_p[0], idx_d[1] );
    // Interpolation of Ez^(p,p)
    JLoc->z = compute( &coeffxp[2], &coeffyp[2], Jz2D, idx_p[0], idx_p[1] );
    // Interpolation of Rho^(p,p)
    ( *RhoLoc ) = compute( &coeffxp[2], &coeffyp[2], Rho2D, idx_p[0], idx_p[1] );
}

//! Interpolator on another field than the basic ones
void Interpolator2D4Order::oneField( Field **field, Particles &particles, int *istart, int *iend, double *FieldLoc, double *, double *, double * )
{
    Field2D *F = static_cast<Field2D *>( *field );
    int idx_p[2], idx_d[2];
    double delta_p[2];
    double coeffxp[5], coeffyp[5];
    double coeffxd[5], coeffyd[5];
    double *coeffx = F->isDual( 0 ) ? &coeffxd[2] : &coeffxp[2];
    double *coeffy = F->isDual( 1 ) ? &coeffyd[2] : &coeffyp[2];
    int *i = F->isDual( 0 ) ? &idx_d[0] : &idx_p[0];
    int *j = F->isDual( 1 ) ? &idx_d[1] : &idx_p[1];

    for( int ipart=*istart ; ipart<*iend; ipart++ ) {
        double xpn = particles.position( 0, ipart )*d_inv_[0];
        double ypn = particles.position( 1, ipart )*d_inv_[1];
        coeffs( xpn, ypn, idx_p, idx_d, coeffxp, coeffyp, coeffxd, coeffyd, delta_p );
        FieldLoc[ipart] = compute( coeffx, coeffy, F, *i, *j );
    }
}

void Interpolator2D4Order::fieldsWrapper( ElectroMagn *EMfields,
                                          Particles &particles,
                                          SmileiMPI *smpi,
                                          int *istart,
                                          int *iend,
                                          int ithread,
                                          unsigned int,
                                          int )
{
    double *const __restrict__ ELoc  = smpi->dynamics_Epart[ithread].data();
    double *const __restrict__ BLoc  = smpi->dynamics_Bpart[ithread].data();

    int    *const __restrict__ iold  = smpi->dynamics_iold[ithread].data();
    double *const __restrict__ delta = smpi->dynamics_deltaold[ithread].data();

    const double *const __restrict__ position_x = particles.getPtrPosition( 0 );
    const double *const __restrict__ position_y = particles.getPtrPosition( 1 );

    const double *const __restrict__ Ex2D = static_cast<Field2D *>( EMfields->Ex_ )->data();
    const double *const __restrict__ Ey2D = static_cast<Field2D *>( EMfields->Ey_ )->data();
    const double *const __restrict__ Ez2D = static_cast<Field2D *>( EMfields->Ez_ )->data();
    const double *const __restrict__ Bx2D = static_cast<Field2D *>( EMfields->Bx_m )->data();
    const double *const __restrict__ By2D = static_cast<Field2D *>( EMfields->By_m )->data();
    const double *const __restrict__ Bz2D = static_cast<Field2D *>( EMfields->Bz_m )->data();

#if defined(SMILEI_ACCELERATOR_GPU_OACC)    
    const int sizeofEx = EMfields->Ex_->size();
    const int sizeofEy = EMfields->Ey_->size();
    const int sizeofEz = EMfields->Ez_->size();
    const int sizeofBx = EMfields->Bx_m->size();
    const int sizeofBy = EMfields->By_m->size();
    const int sizeofBz = EMfields->Bz_m->size();
#endif

    // Definition of grid size ny_p and ny_d as in 2nd order ???
    const int ny_p = EMfields->By_m->dims_[1]; // primary_grid_size_in_y

    //Loop on bin particles
    const int nparts = particles.numberOfParticles();

    // La definition de ces deux variables intermediaires est elle bien necessaire ?
    const int first_index = *istart;
    const int last_index  = *iend;

#if defined( SMILEI_ACCELERATOR_GPU_OMP )

    #pragma omp target map( to :                                                   \
                              i_domain_begin, j_domain_begin,                      \
                              dble_1_ov_384  ,\
                              dble_1_ov_48   ,\
                              dble_1_ov_16   ,\
                              dble_1_ov_12   ,\
                              dble_1_ov_24   ,\
                              dble_19_ov_96  ,\
                              dble_11_ov_24  ,\
                              dble_1_ov_4    ,\
                              dble_1_ov_6    ,\
                              dble_115_ov_192,\
                              dble_5_ov_8     \
                          )                     \
        is_device_ptr /* map */ ( /* to: */                                        \
                                  position_x /* [first_index:npart_range_size] */, \
                                  position_y /* [first_index:npart_range_size] */ )
    #pragma omp teams distribute parallel for
#elif defined(SMILEI_ACCELERATOR_GPU_OACC)
    #pragma acc enter data create(this)
    #pragma acc update device(this)
    size_t interpolation_range_size = ( last_index + 1 * nparts ) - first_index;
    #pragma acc parallel present(ELoc [first_index:interpolation_range_size],\
                                 BLoc [first_index:interpolation_range_size],\
                                 iold [first_index:interpolation_range_size],\
                                 delta [first_index:interpolation_range_size],\
                                 Ex2D [0:sizeofEx],\
                                 Ey2D [0:sizeofEy],\
                                 Ez2D [0:sizeofEz],\
                                 Bx2D [0:sizeofBx],\
                                 By2D [0:sizeofBy],\
                                 Bz2D [0:sizeofBz])\
    deviceptr(position_x, position_y)              \
    copyin(d_inv_[0:2])
    #pragma acc loop gang worker vector
#endif
    for( int ipart = first_index; ipart < last_index; ipart++ ) {

        // Normalized particle position
        const double xpn = position_x[ipart] * d_inv_[0];
        const double ypn = position_y[ipart] * d_inv_[1];

        // Coeffs
        int idx_p[2], idx_d[2];
        double delta_p[2];
        double coeffxp[5], coeffyp[5];
        double coeffxd[5], coeffyd[5];
        coeffs( xpn, ypn, idx_p, idx_d, coeffxp, coeffyp, coeffxd, coeffyd, delta_p );

        // Interpolation of Ex^(d,p)
        ELoc[0*nparts+ipart] = compute( &coeffxd[2], &coeffyp[2], Ex2D, idx_d[0], idx_p[1], ny_p );
        // Interpolation of Ey^(p,d)
        ELoc[1*nparts+ipart] = compute( &coeffxp[2], &coeffyd[2], Ey2D, idx_p[0], idx_d[1], ny_p+1 );
        // Interpolation of Ez^(p,p)
        ELoc[2*nparts+ipart] = compute( &coeffxp[2], &coeffyp[2], Ez2D, idx_p[0], idx_p[1], ny_p );
        // Interpolation of Bx^(p,d)
        BLoc[0*nparts+ipart] = compute( &coeffxp[2], &coeffyd[2], Bx2D, idx_p[0], idx_d[1], ny_p+1 );
        // Interpolation of By^(d,p)
        BLoc[1*nparts+ipart] = compute( &coeffxd[2], &coeffyp[2], By2D, idx_d[0], idx_p[1], ny_p );
        // Interpolation of Bz^(d,d)
        BLoc[2*nparts+ipart] = compute( &coeffxd[2], &coeffyd[2], Bz2D, idx_d[0], idx_d[1], ny_p+1 );

        //Buffering of iol and delta
        iold[0*nparts+ipart]  = idx_p[0];
        iold[1*nparts+ipart]  = idx_p[1];
        delta[0*nparts+ipart] = delta_p[0];
        delta[1*nparts+ipart] = delta_p[1];

    }
    #if defined(SMILEI_ACCELERATOR_GPU_OACC)
        #pragma acc exit data delete(this)
    #endif


}

// -----------------------------------------------------------------------------
//! Interpolator specific to tracked particles. A selection of particles may be provided
// -----------------------------------------------------------------------------
void Interpolator2D4Order::fieldsSelection( ElectroMagn *EMfields, Particles &particles, double *buffer, int offset, vector<unsigned int> *selection )
{
    if( selection ) {

        int nsel_tot = selection->size();
        for( int isel=0 ; isel<nsel_tot; isel++ ) {
            fields( EMfields, particles, ( *selection )[isel], offset, buffer+isel, buffer+isel+3*offset );
        }

    } else {

        int npart_tot = particles.numberOfParticles();
        for( int ipart=0 ; ipart<npart_tot; ipart++ ) {
            fields( EMfields, particles, ipart, offset, buffer+ipart, buffer+ipart+3*offset );
        }

    }
}


void Interpolator2D4Order::fieldsAndEnvelope( ElectroMagn *, Particles &, SmileiMPI *, int *, int *, int, int )
{
    ERROR( "Projection and interpolation for the envelope model are implemented only for interpolation_order = 2" );
}


void Interpolator2D4Order::timeCenteredEnvelope( ElectroMagn *, Particles &, SmileiMPI *, int *, int *, int, int )
{
    ERROR( "Projection and interpolation for the envelope model are implemented only for interpolation_order = 2" );
}

// probes like diagnostic !
void Interpolator2D4Order::envelopeAndSusceptibility( ElectroMagn *, Particles &, int, double *, double *, double *, double * )
{
    ERROR( "Projection and interpolation for the envelope model are implemented only for interpolation_order = 2" );
}
