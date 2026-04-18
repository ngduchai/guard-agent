#include "CollisionalIonization.h"

#include "Collisions.h"
#include "Species.h"
#include "Patch.h"
#include "IonizationTables.h"

#include <cmath>


using namespace std;

// Coefficients used for energy interpolation
// The list of energies has to be in logarithmic scale,
//  with Emin=1eV, Emax=10MeV and npoints=100.
const int    CollisionalIonization::npoints = 100;
const double CollisionalIonization::npointsm1 = ( double )( npoints-1 );
const double CollisionalIonization::a1 = 510998.9 ; // = me*c^2/Emin
const double CollisionalIonization::a2 = 6.142165 ; // = (npoints-1) / ln( Emax/Emin )

// Constructor
CollisionalIonization::CollisionalIonization( int Z, Params *params, int ionization_electrons, Particles* particles )
{
    atomic_number = Z;
    rate .resize( Z );
    irate.resize( Z );
    prob .resize( Z );
    ionization_electrons_ = ionization_electrons;
    if( params ) {
        new_electrons.initialize( 0, *particles );
    }
    if( Z>0 ) {
        dataBaseIndex = createDatabase( params->reference_angular_frequency_SI );
    }
}

// Cloning Constructor
CollisionalIonization::CollisionalIonization( CollisionalIonization *CI )
{
    atomic_number = CI->atomic_number;
    rate .resize( atomic_number );
    irate.resize( atomic_number );
    prob .resize( atomic_number );
    ionization_electrons_ = CI->ionization_electrons_;
    new_electrons.initialize( 0, CI->new_electrons );
    
    dataBaseIndex = CI->dataBaseIndex;
}

// Static members
vector<int> CollisionalIonization::DB_Z;
vector<double> CollisionalIonization::DB_crossSection;
vector<double> CollisionalIonization::DB_transferredEnergy;
vector<double> CollisionalIonization::DB_lostEnergy;

// Initializes the databases (by patch master only)
unsigned int CollisionalIonization::createDatabase( double reference_angular_frequency_SI )
{
    size_t offset = 0;
    
    // Leave if the database already exists with same atomic number
    for( unsigned int i=0; i<DB_Z.size(); i++ ) {
        if( atomic_number == DB_Z[i] ) {
            return i;
        }
        offset += DB_Z[i] * npoints;
    }
    
    // Otherwise, create the arrays:
    // For each ionization state, calculate the tables of integrated cross-sections
    // Pérez et al., Phys. Plasmas 19, 083104 (2012)
    DB_crossSection     .resize( offset + atomic_number * npoints, 0. );
    DB_transferredEnergy.resize( offset + atomic_number * npoints, 0. );
    DB_lostEnergy       .resize( offset + atomic_number * npoints, 0. );
    vector<double> &cs = DB_crossSection; // cross section
    vector<double> &te = DB_transferredEnergy; // transferred energy
    vector<double> &le = DB_lostEnergy; // lost energy
    double e, ep, bp, up, ep2, betae2, betab2, betau2, s0, A1, A2, A3, sk, wk, ek;
    int N; // occupation number
    double normalization = 2.81794e-15 * reference_angular_frequency_SI / ( 2.*299792458. ); // r_e omega / 2c
    for( int Zstar=0; Zstar<atomic_number; Zstar++ ) { // For each ionization state
        for( int i=0; i<npoints; i++ ) { // For each incident electron energy
            size_t loc = offset + Zstar * npoints + i; // location in the database
            ep = exp( double( i )/a2 ) / a1; // = incident electron energy
            N = 1;
            for( int k=0; k<atomic_number-Zstar; k++ ) { // For each orbital
                bp = IonizationTables::binding_energy( atomic_number, Zstar, k );
                // If next orbital is on same level, then continue directly to next
                if( k<atomic_number-Zstar-1 && bp == IonizationTables::binding_energy( atomic_number, Zstar, k+1 ) ) {
                    N++;
                    continue;
                }
                // If electron energy below the ionization energy, then skip to next level
                e = ep/bp;
                if( e>1. ) {
                    up = bp; // we assume up=bp because we don't have exact tables
                    betae2 = 1. - 1./( ( 1.+ep )*( 1.+ep ) );
                    betab2 = 1. - 1./( ( 1.+bp )*( 1.+bp ) );
                    betau2 = 1. - 1./( ( 1.+up )*( 1.+up ) );
                    s0 = normalization * N /( bp * ( betae2 + betab2 + betau2 ) );
                    ep2 = 1./( 1.+ep*0.5 );
                    ep2 *= ep2;
                    A1 = ( 1.+2.*ep )/( 1.+e )*ep2;
                    A2 = ( e-1. )*bp*bp*0.5*ep2;
                    A3 = log( betae2/( 1.-betae2 ) ) - betae2 - log( 2.*bp );
                    sk = s0*( 0.5*A3*( 1.-1./( e*e ) ) + 1. - 1./e + A2 - A1*log( e ) );
                    wk = s0 * ( 0.5*A3*( e-1. )*( e-1. )/e/( e+1. )  + 2.*log( 0.5*( e+1. ) ) - log( e )
                                + 0.25*A2*( e-1. ) - A1*( e*log( e )-( e+1. )*log( 0.5*( e+1. ) ) ) );
                    ek = wk + sk;
                    // Sum these data to the total ones
                    cs[loc] += sk;
                    te[loc] += wk * bp;
                    le[loc] += ek * bp;
                }
                // Reset occupation number for next level
                N = 1;
            }
            // The transferred and lost energies are averages over the orbitals
            if( cs[loc]>0. ) {
                te[loc] /= cs[loc];
                le[loc] /= cs[loc];
            }
        }
    }
    
    // Add the new arrays to the static database
    DB_Z.push_back( atomic_number );
    
    return offset;
}


// Finish the ionization (moves new electrons in place)
void CollisionalIonization::finish( Params &params, Patch *patch, std::vector<Diagnostic *> &localDiags, bool, std::vector<unsigned int>, std::vector<unsigned int>, int itime )
{
    patch->vecSpecies[ionization_electrons_]->importParticles( params, patch, new_electrons, localDiags, ( itime + 0.5 ) * params.timestep );
}
