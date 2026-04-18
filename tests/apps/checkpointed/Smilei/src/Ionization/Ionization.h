#ifndef IONIZATION_H
#define IONIZATION_H

#include "Field.h"
#include "Params.h"
#include "Particles.h"
#include "Patch.h"
#include "Projector.h"

using namespace std;

//! Class Ionization: generic class allowing to define Ionization physics
class Ionization
{
public:
    //! Constructor for Ionization
    Ionization(Params &params, Species *species);
    virtual ~Ionization() {};

    //! Overloading of () operator
    virtual void operator()(Particles *, unsigned int, unsigned int, const std::vector<const std::vector<double> *>&, Patch *, Projector *) {};

    Particles new_electrons;
    
    //! Whether the initial charge (of the atom that was ionized) should be saved
    bool save_ion_charge_ = false;
    //! Temporarily contains the initial charge of the atom that was ionized
    std::vector<short> ion_charge_;

protected:
    // Normalization constant from Smilei normalization to/from atomic units
    static constexpr double eV_to_au = 1.0 / 27.2116;
    static constexpr double au_to_mec2 = 27.2116/510.998e3;
    double EC_to_au;
    double au_to_w0;

    double reference_angular_frequency_SI;
    double dt;
    double invdt;
    unsigned int nDim_field;
    unsigned int nDim_particle;
    double ionized_species_invmass;
};

#endif
