#ifndef IONIZATIONTUNNELENVELOPEAVERAGED_H
#define IONIZATIONTUNNELENVELOPEAVERAGED_H

#include <vector>

#include "IonizationTunnel.h"

class Particles;

//! calculate the particle tunnel ionization
class IonizationTunnelEnvelopeAveraged : public IonizationTunnel
{

public:
    //! Constructor for IonizationTunnelEnvelope: with no input argument
    IonizationTunnelEnvelopeAveraged( Params &params, Species *species );

    double ellipticity_,cos_phi_,sin_phi_;
    double phi_env_;

protected:
    void computeIonizationCurrents(unsigned int, unsigned int, unsigned int, const ElectricFields&, const SimulationContext&) override;
    void createNewElectrons(unsigned int ipart, unsigned int Z, unsigned int k_times, const ElectricFields& E, const SimulationContext& context) override;
    ElectricFields calculateElectricFields(const vector<const vector<double>*>& Epart, unsigned int ipart) override;
    double ionizationRate(unsigned int Z, const ElectricFields& E) override;

private:
    std::vector<double> Ip_times2_to_minus3ov4_;
};

#endif
