#include "Ionization.h"

#include "Species.h"

using namespace std;

Ionization::Ionization(Params &params, Species *species)
{
    reference_angular_frequency_SI = params.reference_angular_frequency_SI;

    dt = params.timestep;
    invdt = 1. / dt;
    nDim_field = params.nDim_field;
    nDim_particle = params.nDim_particle;
    ionized_species_invmass = 1. / species->mass_;

    EC_to_au   = 3.314742578e-15 * reference_angular_frequency_SI; // hbar omega / (me c^2 alpha^3)
    au_to_w0   = 4.134137172e+16 / reference_angular_frequency_SI; // alpha^2 me c^2 / (hbar omega)
}

