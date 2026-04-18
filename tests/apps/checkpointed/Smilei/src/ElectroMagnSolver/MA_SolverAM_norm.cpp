
#include "MA_SolverAM_norm.h"
#include "ElectroMagnAM.h"
#include "cField2D.h"
#include <complex>
#include "dcomplex.h"
#include "Patch.h"
MA_SolverAM_norm::MA_SolverAM_norm( Params &params )
    : SolverAM( params )
{
}

MA_SolverAM_norm::~MA_SolverAM_norm()
{
}

void MA_SolverAM_norm::operator()( ElectroMagn *fields )
{
    const unsigned int nl_p = fields->dimPrim[0];
    const unsigned int nl_d = fields->dimDual[0];
    const unsigned int nr_p = fields->dimPrim[1];
    const unsigned int nr_d = fields->dimDual[1];
    for( unsigned int imode=0 ; imode<Nmode ; imode++ ) {
    
        // Static-cast of the fields_SolverAM_norm.cpp
        cField2D *El = ( static_cast<ElectroMagnAM *>( fields ) )->El_[imode];
        cField2D *Er = ( static_cast<ElectroMagnAM *>( fields ) )->Er_[imode];
        cField2D *Et = ( static_cast<ElectroMagnAM *>( fields ) )->Et_[imode];
        cField2D *Bl = ( static_cast<ElectroMagnAM *>( fields ) )->Bl_[imode];
        cField2D *Br = ( static_cast<ElectroMagnAM *>( fields ) )->Br_[imode];
        cField2D *Bt = ( static_cast<ElectroMagnAM *>( fields ) )->Bt_[imode];
        cField2D *Jl = ( static_cast<ElectroMagnAM *>( fields ) )->Jl_[imode];
        cField2D *Jr = ( static_cast<ElectroMagnAM *>( fields ) )->Jr_[imode];
        cField2D *Jt = ( static_cast<ElectroMagnAM *>( fields ) )->Jt_[imode];
        int j_glob    = ( static_cast<ElectroMagnAM *>( fields ) )->j_glob_;
        bool isYmin = ( static_cast<ElectroMagnAM *>( fields ) )->isYmin;
        int oversize_r = fields->oversize[1];
        
        // Electric field Elr^(d,p)
        for( unsigned int i=0 ; i<nl_d ; i++ ) {
            for( unsigned int j=isYmin*(oversize_r+1) ; j<nr_p ; j++ ) {
                ( *El )( i, j ) += -dt*( *Jl )( i, j )
                                   +                 dt/( ( j_glob+j )*dr )*( ( j+j_glob+0.5 )*( *Bt )( i, j+1 ) - ( j+j_glob-0.5 )*( *Bt )( i, j ) )
                                   +                 Icpx*dt*( double )imode/( ( j_glob+j )*dr )*( *Br )( i, j );
            }
        }
        for( unsigned int i=0 ; i<nl_p ; i++ ) {
            for( unsigned int j=isYmin*(oversize_r+1) ; j<nr_d ; j++ ) {
                ( *Er )( i, j ) += -dt*( *Jr )( i, j )
                                   -                  dt_ov_dl * ( ( *Bt )( i+1, j ) - ( *Bt )( i, j ) )
                                   -                  Icpx*dt*( double )imode/( ( j_glob+j-0.5 )*dr )* ( *Bl )( i, j );
                                   
            }
        }
        for( unsigned int i=0 ;  i<nl_p ; i++ ) {
            for( unsigned int j=isYmin*(oversize_r+1) ; j<nr_p ; j++ ) {
                ( *Et )( i, j ) += -dt*( *Jt )( i, j )
                                   +                  dt_ov_dl * ( ( *Br )( i+1, j ) - ( *Br )( i, j ) )
                                   -                  dt_ov_dr * ( ( *Bl )( i, j+1 ) - ( *Bl )( i, j ) );
            }
        }
        if( isYmin ) { 
            // Conditions on axis
            if( imode==0 ) {
                for( unsigned int i=0 ; i<nl_p  ; i++ ) {
                    ( *Et )( i, oversize_r )=0;
                    ( *Et )( i, oversize_r-1 )=-( *Et )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p  ; i++ ) {
                    ( *Er )( i, oversize_r )= -( *Er )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_d ; i++ ) {
                    ( *El )( i, oversize_r )+= 4.*dt_ov_dr*( *Bt )( i, oversize_r+1 )-dt*( *Jl )( i, oversize_r );
                    ( *El )( i, oversize_r-1 )=( *El )( i, oversize_r+1 );
                }
            } else if( imode==1 ) {
                for( unsigned int i=0 ; i<nl_d  ; i++ ) {
                    ( *El )( i, oversize_r )= 0;
                    ( *El )( i, oversize_r-1 )=-( *El )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p  ; i++ ) {
                    ( *Et )( i, oversize_r )= -( 4.*Icpx*( *Er )( i, oversize_r+1 ) + ( *Et )( i, oversize_r+1 ) )/3.;// div( E mode 1) = 0 on axis.
                    ( *Et )( i, oversize_r-1 )=( *Et )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p ; i++ ) {
                    ( *Er )( i, oversize_r ) = 2.*Icpx*( *Et )( i, oversize_r ) - ( *Er )( i, oversize_r+1 ); // interpolation of Er on axis must be equal to iEt.
                }
            } else { // mode > 1
                for( unsigned int  i=0 ; i<nl_d; i++ ) {
                    ( *El )( i, oversize_r )= 0;
                    ( *El )( i, oversize_r-1 )=-( *El )( i, oversize_r+1 );
                }
                for( unsigned int  i=0 ; i<nl_p; i++ ) {
                    ( *Er )( i, oversize_r )= -( *Er )( i, oversize_r+1 );
                }
                for( unsigned int i=0 ; i<nl_p; i++ ) {
                    ( *Et )( i, oversize_r )= 0;
                    ( *Et )( i, oversize_r-1 )=-( *Et )( i, oversize_r+1 );
                }
            }
        }
    }
}

