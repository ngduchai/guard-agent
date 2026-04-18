#ifndef IONIZATIONTUNNEL_H
#define IONIZATIONTUNNEL_H

#include <cmath>
#include <vector>

#include "Ionization.h"

class Particles;
class Species;

struct ElectricFields {
    double x;
    double y;
    double z;
    double inv;
    double abs;
};

class IonizationTunnel : public Ionization
{
   public:
    IonizationTunnel(Params &params, Species *species);

    void operator()(Particles *, unsigned int, unsigned int, const vector<const vector<double>*>&, Patch *, Projector *) override;

   protected:
    struct SimulationContext {
        Particles *particles;
        Patch *patch;
        Projector *Proj;
    };

    virtual void computeIonizationCurrents(unsigned int ipart, unsigned int Z, unsigned int k_times, const ElectricFields& E, const SimulationContext& context);;
    virtual void createNewElectrons(unsigned int ipart, unsigned int Z, unsigned int k_times, const ElectricFields&, const SimulationContext& context);
    virtual ElectricFields calculateElectricFields(const vector<const vector<double>*>& Epart, unsigned int ipart);
    virtual double ionizationRate(unsigned int Z, const ElectricFields& E);

    static constexpr double one_third_ = 1. / 3.;
    unsigned int atomic_number_;
    std::vector<double> potential_, azimuthal_quantum_number_;
    std::vector<double> alpha_tunnel_, beta_tunnel_, gamma_tunnel_;
};

#endif
