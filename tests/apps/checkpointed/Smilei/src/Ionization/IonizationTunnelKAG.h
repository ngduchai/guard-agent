#ifndef IONIZATIONTUNNELKAG_H
#define IONIZATIONTUNNELKAG_H

#include <cmath>

#include "IonizationTunnel.h"
#include "IonizationTables.h"
#include "Particles.h"
#include "Species.h"

class Particles;

class IonizationTunnelKAG : public IonizationTunnel
{
   public:
    IonizationTunnelKAG(Params &params, Species *species) : IonizationTunnel(params, species) {};

   protected:
    double ionizationRate(unsigned int Z, const ElectricFields& E) override {
        constexpr double IH = 13.598434005136;
        double ratio_of_IPs = IH / IonizationTables::ionization_energy(atomic_number_, Z);

        double BSI_rate_quadratic = 2.4 * (E.abs * E.abs) * ratio_of_IPs * ratio_of_IPs * au_to_w0;
        double BSI_rate_linear = 0.8 * E.abs * sqrt(ratio_of_IPs) * au_to_w0;
        double Tunnel_rate = IonizationTunnel::ionizationRate(Z, E);

        if (BSI_rate_quadratic >= BSI_rate_linear) {
            return BSI_rate_linear;
        } else if (Tunnel_rate >= BSI_rate_quadratic) {
            return BSI_rate_quadratic;
        } else {
            return Tunnel_rate;
        }
    };
};

#endif
