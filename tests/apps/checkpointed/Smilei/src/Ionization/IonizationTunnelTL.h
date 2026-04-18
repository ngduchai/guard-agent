#ifndef IONIZATIONTUNNELTL_H
#define IONIZATIONTUNNELTL_H

#include <cmath>
#include <vector>

#include "IonizationTunnel.h"
#include "Particles.h"
#include "Species.h"
#include "Tools.h"


class Particles;

class IonizationTunnelTL : public IonizationTunnel
{
   public:
    IonizationTunnelTL(Params &params, Species *species) : IonizationTunnel(params, species) {
        DEBUG("Creating the Tunnel Ionizaton class");
        double cst;
        // species->ionization_tl_parameter_ is double Varies from 6 to 9. This is the alpha parameter in Tong-Lin
        // exponential, see Eq. (6) in [M F Ciappina and S V Popruzhenko 2020 Laser Phys. Lett. 17 025301 2020].
        double ionization_tl_parameter = species->ionization_tl_parameter_;
        lambda_tunnel_.resize(atomic_number_);

        for (unsigned int Z = 0; Z < atomic_number_; Z++) {
            DEBUG("Z : " << Z);
            cst = ((double)Z + 1.0) * sqrt(2.0 / potential_[Z]);
            lambda_tunnel_[Z] = ionization_tl_parameter * cst * cst / gamma_tunnel_[Z];
        }

        DEBUG("Finished Creating the Tunnel Ionizaton class");
    };
  
   protected:
    double ionizationRate(unsigned int Z, const ElectricFields& E) override {
        return IonizationTunnel::ionizationRate(Z, E) * exp(-E.abs*lambda_tunnel_[Z]);
    };

   private:
    std::vector<double> lambda_tunnel_;
};

#endif
