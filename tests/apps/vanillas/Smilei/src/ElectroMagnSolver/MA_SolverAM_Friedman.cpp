
#include "MA_SolverAM_Friedman.h"
#include "ElectroMagnAM.h"
#include "cField2D.h"
#include <complex>
#include "dcomplex.h"
#include "Patch.h"
MA_SolverAM_Friedman::MA_SolverAM_Friedman( Params &params )
    : SolverAM( params )
{
    ftheta = params.Friedman_theta;
    alpha  = 1.-0.5*ftheta+0.5*ftheta*ftheta;
    beta   = ftheta*( 1.-0.5*ftheta );
    delta  = 0.5*ftheta*( 1.-ftheta )*( 1.-ftheta );
}

MA_SolverAM_Friedman::~MA_SolverAM_Friedman()
{
}

void MA_SolverAM_Friedman::operator()( ElectroMagn *fields )
{
    const unsigned int nl_p = fields->dimPrim[0];
    const unsigned int nl_d = fields->dimDual[0];
    const unsigned int nr_p = fields->dimPrim[1];
    const unsigned int nr_d = fields->dimDual[1];
    for( unsigned int imode=0 ; imode<Nmode ; imode++ ) {

        // Static-cast of the fields_SolverAM_norm.cpp
        cField2D *El    = ( static_cast<ElectroMagnAM *>( fields ) )->El_[imode];
        cField2D *Er    = ( static_cast<ElectroMagnAM *>( fields ) )->Er_[imode];
        cField2D *Et    = ( static_cast<ElectroMagnAM *>( fields ) )->Et_[imode];
        cField2D *Bl    = ( static_cast<ElectroMagnAM *>( fields ) )->Bl_[imode];
        cField2D *Br    = ( static_cast<ElectroMagnAM *>( fields ) )->Br_[imode];
        cField2D *Bt    = ( static_cast<ElectroMagnAM *>( fields ) )->Bt_[imode];
        cField2D *Jl    = ( static_cast<ElectroMagnAM *>( fields ) )->Jl_[imode];
        cField2D *Jr    = ( static_cast<ElectroMagnAM *>( fields ) )->Jr_[imode];
        cField2D *Jt    = ( static_cast<ElectroMagnAM *>( fields ) )->Jt_[imode];

        cField2D *El_f  = static_cast<cField2D *>( fields->filter_->El_[imode][0] );
        cField2D *Er_f  = static_cast<cField2D *>( fields->filter_->Er_[imode][0] );
        cField2D *Et_f  = static_cast<cField2D *>( fields->filter_->Et_[imode][0] );
        cField2D *El_m1 = static_cast<cField2D *>( fields->filter_->El_[imode][1] );
        cField2D *Er_m1 = static_cast<cField2D *>( fields->filter_->Er_[imode][1] );
        cField2D *Et_m1 = static_cast<cField2D *>( fields->filter_->Et_[imode][1] );
        cField2D *El_m2 = static_cast<cField2D *>( fields->filter_->El_[imode][2] );
        cField2D *Er_m2 = static_cast<cField2D *>( fields->filter_->Er_[imode][2] );
        cField2D *Et_m2 = static_cast<cField2D *>( fields->filter_->Et_[imode][2] );

        int j_glob    = ( static_cast<ElectroMagnAM *>( fields ) )->j_glob_;
        bool isYmin = ( static_cast<ElectroMagnAM *>( fields ) )->isYmin;
        int oversize_r = fields->oversize[1];

        std::complex<double> adv = 0.;
        // Electric field Elr^(d,p)
        for( unsigned int i=0 ; i<nl_d ; i++ ) {
            for( unsigned int j=isYmin*(oversize_r+1) ; j<nr_p ; j++ ) {

                adv                = -dt*( *Jl )( i, j )
                                     +dt/( ( j_glob+j )*dr )*( ( j+j_glob+0.5 )*( *Bt )( i, j+1 ) - ( j+j_glob-0.5 )*( *Bt )( i, j ) )
                                     +Icpx*dt*( double )imode/( ( j_glob+j )*dr )*( *Br )( i, j );
                // advance electric field
                ( *El )( i, j )   += adv;
                // compute the time-filtered field
                ( *El_f )( i, j )  = alpha*( *El )( i, j ) + beta*adv + delta*( ( *El_m1 )( i, j )+ftheta*( *El_m2 )( i, j ) );
                // update Ex_m2 and Ex_m1
                ( *El_m2 )( i, j ) = ( *El_m1 )( i, j ) - ftheta*( *El_m2 )( i, j );
                ( *El_m1 )( i, j ) = ( *El )( i, j )  - adv;

            }
        }
        for( unsigned int i=0 ; i<nl_p ; i++ ) {
            for( unsigned int j=isYmin*(oversize_r+1) ; j<nr_d ; j++ ) {

                adv                = -dt*( *Jr )( i, j )
                                     -dt_ov_dl * ( ( *Bt )( i+1, j ) - ( *Bt )( i, j ) )
                                     -Icpx*dt*( double )imode/( ( j_glob+j-0.5 )*dr )* ( *Bl )( i, j );
                // advance electric field
                ( *Er )( i, j )   += adv;
                // compute the time-filtered field
                ( *Er_f )( i, j )  = alpha*( *Er )( i, j ) + beta*adv + delta*( ( *Er_m1 )( i, j )+ftheta*( *Er_m2 )( i, j ) );
                // update Ex_m2 and Ex_m1
                ( *Er_m2 )( i, j ) = ( *Er_m1 )( i, j ) - ftheta*( *Er_m2 )( i, j );
                ( *Er_m1 )( i, j ) = ( *Er )( i, j )  - adv;

            }
        }
        for( unsigned int i=0 ;  i<nl_p ; i++ ) {
            for( unsigned int j=isYmin*(oversize_r+1) ; j<nr_p ; j++ ) {
                adv                = -dt*( *Jt )( i, j )
                                     +dt_ov_dl * ( ( *Br )( i+1, j ) - ( *Br )( i, j ) )
                                     -dt_ov_dr * ( ( *Bl )( i, j+1 ) - ( *Bl )( i, j ) );
                // advance electric field
                ( *Et )( i, j )     += adv;
                // compute the time-filtered field
                ( *Et_f )( i, j )    = alpha*( *Et )( i, j ) + beta*adv + delta*( ( *Et_m1 )( i, j )+ftheta*( *Et_m2 )( i, j ) );
                // update Ex_m2 and Ex_m1
                ( *Et_m2 )( i, j )   = ( *Et_m1 )( i, j ) - ftheta*( *Et_m2 )( i, j );
                ( *Et_m1 )( i, j )   = ( *Et )( i, j )  - adv;
            }
        }
        if( isYmin ) {
            // Conditions on axis
            if( imode==0 ) {
                for( unsigned int i=0 ; i<nl_p  ; i++ ) {
                    ( *Et    )( i, oversize_r )  =0;
                    ( *Et    )( i, oversize_r-1 )=-( *Et )( i, oversize_r+1 );

                    ( *Et_f  )( i, oversize_r )  =0;
                    ( *Et_f  )( i, oversize_r-1 )=-( *Et_f )( i, oversize_r+1 );

                    ( *Et_m1 )( i, oversize_r )  =0;
                    ( *Et_m1 )( i, oversize_r-1 )=-( *Et_m1 )( i, oversize_r+1 );

                    ( *Et_m2 )( i, oversize_r )  =0;
                    ( *Et_m2 )( i, oversize_r-1 )=-( *Et_m2 )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p  ; i++ ) {
                    //( *Er )( i, oversize_r+1 )= ( *Er )( i, oversize_r+2 ) / 9.;
                    ( *Er    )( i, oversize_r )  = -( *Er    )( i, oversize_r+1 );

                    ( *Er_f  )( i, oversize_r )  = -( *Er_f  )( i, oversize_r+1 );

                    ( *Er_m1 )( i, oversize_r )  = -( *Er_m1 )( i, oversize_r+1 );

                    ( *Er_m2 )( i, oversize_r )  = -( *Er_m2 )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_d ; i++ ) {
                    adv                 = 4.*dt_ov_dr*( *Bt )( i, oversize_r+1 )-dt*( *Jl )( i, oversize_r );
                    // advance electric field
                    ( *El )( i, oversize_r )    += adv;
                    // compute the time-filtered field
                    ( *El_f )( i, oversize_r )   = alpha*( *El )( i, oversize_r ) + beta*adv + delta*( ( *El_m1 )( i, oversize_r )+ftheta*( *El_m2 )( i, oversize_r ) );
                    // update Ex_m2 and Ex_m1
                    ( *El_m2 )( i, oversize_r )  = ( *El_m1 )( i, oversize_r ) - ftheta*( *El_m2 )( i, oversize_r );
                    ( *El_m1 )( i, oversize_r )  = ( *El )( i, oversize_r )  - adv;

                    ( *El    )( i, oversize_r-1 )=( *El    )( i, oversize_r+1 );
                    ( *El_f  )( i, oversize_r-1 )=( *El_f  )( i, oversize_r+1 );
                    ( *El_m1 )( i, oversize_r-1 )=( *El_m1 )( i, oversize_r+1 );
                    ( *El_m2 )( i, oversize_r-1 )=( *El_m2 )( i, oversize_r+1 );
                }
            } else if( imode==1 ) {
                for( unsigned int i=0 ; i<nl_d  ; i++ ) {
                    ( *El    )( i, oversize_r )  = 0;
                    ( *El    )( i, oversize_r-1 )=-( *El )( i, oversize_r+1 );

                    ( *El_f  )( i, oversize_r )  = 0;
                    ( *El_f  )( i, oversize_r-1 )=-( *El_f )( i, oversize_r+1 );

                    ( *El_m1 )( i, oversize_r )  = 0;
                    ( *El_m1 )( i, oversize_r-1 )=-( *El_m1 )( i, oversize_r+1 );

                    ( *El_m2 )( i, oversize_r )  = 0;
                    ( *El_m2 )( i, oversize_r-1 )=-( *El_m2 )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p  ; i++ ) {
                    ( *Et )( i, oversize_r )= -( 4.*Icpx*( *Er )( i, oversize_r+1 ) + ( *Et )( i, oversize_r+1 ) )/3.;// div( E mode 1) = 0 on axis.
                    ( *Et    )( i, oversize_r-1 )=( *Et )( i, oversize_r+1 );

                    ( *Et_f )( i, oversize_r )= -( 4.*Icpx*( *Er_f )( i, oversize_r+1 ) + ( *Et_f )( i, oversize_r+1 ) )/3.;// div( E mode 1) = 0 on axis.
                    ( *Et_f  )( i, oversize_r-1 )=( *Et_f )( i, oversize_r+1 );

                    ( *Et_m1)( i, oversize_r )= -( 4.*Icpx*( *Er_m1)( i, oversize_r+1 ) + ( *Et_m1)( i, oversize_r+1 ) )/3.;// div( E mode 1) = 0 on axis.
                    ( *Et_m1 )( i, oversize_r-1 )=( *Et_m1 )( i, oversize_r+1 );

                    ( *Et_m2)( i, oversize_r )= -( 4.*Icpx*( *Er_m2)( i, oversize_r+1 ) + ( *Et_m2)( i, oversize_r+1 ) )/3.;// div( E mode 1) = 0 on axis.
                    ( *Et_m2 )( i, oversize_r-1 )=( *Et_m2 )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p ; i++ ) {
                    ( *Er    )( i, oversize_r )  =2.*Icpx*( *Et    )( i, oversize_r )-( *Er    )( i, oversize_r+1 );

                    ( *Er_f  )( i, oversize_r )  =2.*Icpx*( *Et_f  )( i, oversize_r )-( *Er_f  )( i, oversize_r+1 );

                    ( *Er_m1 )( i, oversize_r )  =2.*Icpx*( *Et_m1 )( i, oversize_r )-( *Er_m1 )( i, oversize_r+1 );

                    ( *Er_m2 )( i, oversize_r )  =2.*Icpx*( *Et_m2 )( i, oversize_r )-( *Er_m2 )( i, oversize_r+1 );
                }
            } else { // mode > 1
                for( unsigned int  i=0 ; i<nl_d; i++ ) {
                    ( *El    )( i, oversize_r )  = 0;
                    ( *El    )( i, oversize_r-1 )=-( *El )( i, oversize_r+1 );

                    ( *El_f  )( i, oversize_r )  = 0;
                    ( *El_f  )( i, oversize_r-1 )=-( *El_f )( i, oversize_r+1 );

                    ( *El_m1 )( i, oversize_r )  = 0;
                    ( *El_m1 )( i, oversize_r-1 )=-( *El_m1 )( i, oversize_r+1 );

                    ( *El_m2 )( i, oversize_r )  = 0;
                    ( *El_m2 )( i, oversize_r-1 )=-( *El_m2 )( i, oversize_r+1 );
                }
                for( unsigned int  i=0 ; i<nl_p; i++ ) {
                    ( *Er    )( i, oversize_r+1 )=  ( *Er    )( i, oversize_r+2 ) / 9.;
                    ( *Er    )( i, oversize_r   )= -( *Er    )( i, oversize_r+1 );

                    ( *Er_f  )( i, oversize_r+1 )=  ( *Er_f  )( i, oversize_r+2 ) / 9.;
                    ( *Er_f  )( i, oversize_r   )= -( *Er_f  )( i, oversize_r+1 );

                    ( *Er_m1 )( i, oversize_r+1 )=  ( *Er_m1 )( i, oversize_r+2 ) / 9.;
                    ( *Er_m1 )( i, oversize_r   )= -( *Er_m1 )( i, oversize_r+1 );

                    ( *Er_m2 )( i, oversize_r+1 )=  ( *Er_m2 )( i, oversize_r+2 ) / 9.;
                    ( *Er_m2 )( i, oversize_r   )= -( *Er_m2 )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p; i++ ) {
                    ( *Et    )( i, oversize_r   )= 0;
                    ( *Et    )( i, oversize_r-1 )=-( *Et )( i, oversize_r+1 );

                    ( *Et_f  )( i, oversize_r   )= 0;
                    ( *Et_f  )( i, oversize_r-1 )=-( *Et_f )( i, oversize_r+1 );

                    ( *Et_m1 )( i, oversize_r   )= 0;
                    ( *Et_m1 )( i, oversize_r-1 )=-( *Et_m2 )( i, oversize_r+1 );

                    ( *Et_m2 )( i, oversize_r   )= 0;
                    ( *Et_m2 )( i, oversize_r-1 )=-( *Et_m2 )( i, oversize_r+1 );
                }
            }
        }
    }
}
