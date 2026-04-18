#include "IonizationTunnel.h"
#include "IonizationTables.h"
#include "Tools.h"
#include "Particles.h"
#include "Species.h"

IonizationTunnel::IonizationTunnel(Params &params, Species *species) : Ionization(params, species)
{
    DEBUG("Creating the Tunnel Ionizaton class");
    double abs_m         = 0;
    double g_factor      = 1;
    double Anl           = 4.;  // the initial value is set to 4 on purpose, 
                                // as A_nl = 4*C_nl^2, where C_nl are 
                                // the Hartree coefficients; C_nl is set 
                                // to 1 for a neutral atom
    double Blm           = 1.;
    std::string tunneling_model = species->ionization_model_;

    // Ionization potential & quantum numbers (all in atomic units 1 au = 27.2116 eV)
    atomic_number_ = species->atomic_number_;
    potential_.resize(atomic_number_);
    azimuthal_quantum_number_.resize(atomic_number_);

    alpha_tunnel_.resize(atomic_number_);
    beta_tunnel_.resize(atomic_number_);
    gamma_tunnel_.resize(atomic_number_);

    for (unsigned int Z = 0; Z < atomic_number_; Z++) {
        DEBUG("Z : " << Z);

        if (tunneling_model == "tunnel_full_PPT") {
            abs_m = abs(IonizationTables::magnetic_atomic_number(atomic_number_, Z));
            g_factor = IonizationTables::magnetic_degeneracy_atomic_number(atomic_number_, Z);
        } 

        potential_[Z] = IonizationTables::ionization_energy(atomic_number_, Z) * eV_to_au;
        azimuthal_quantum_number_[Z] = IonizationTables::azimuthal_atomic_number(atomic_number_, Z);

        DEBUG("potential_: " << potential_[Z] << " Az.q.num: " << azimuthal_quantum_number_[Z]);

        Blm      = ( 2.*azimuthal_quantum_number_[Z]+1.0 ) * \
                   tgamma(azimuthal_quantum_number_[Z]+abs_m+1) / \
                   ( pow( 2, abs_m )*tgamma(abs_m+1)*tgamma(azimuthal_quantum_number_[Z]-abs_m+1) );

        double cst = ((double)Z + 1.0) * sqrt(2.0 / potential_[Z]);
        if(tunneling_model == "tunnel") {
            Anl = pow( 2, cst+1.0 ) / \
                ( cst*tgamma( cst ) );
        } else if ( Z>0 ) {
            Anl = pow( 2, cst+1.0 ) / \
                                ( cst*tgamma( cst/2.0+azimuthal_quantum_number_[Z]+1 )*tgamma( cst/2.0-azimuthal_quantum_number_[Z]) );
        }

        alpha_tunnel_[Z] = cst - 1.0 - abs_m;
        beta_tunnel_[Z] = g_factor*Anl*Blm * potential_[Z] * au_to_w0;
        gamma_tunnel_[Z] = 2.0 * sqrt(2.0 * potential_[Z] * 2.0 * potential_[Z] * 2.0 * potential_[Z]);
    }

    DEBUG("Finished Creating the Tunnel Ionizaton class");
}

void IonizationTunnel::operator()(Particles *particles, unsigned int ipart_min, unsigned int ipart_max,
                                                const vector<const vector<double>*>& Epart, Patch *patch, Projector *Proj)
{
    unsigned int Z, Zp1, newZ, k_times;
    double ran_p, Mult, D_sum, P_sum, Pint_tunnel;
    vector<double> IonizRate_tunnel(atomic_number_), Dnom_tunnel(atomic_number_);
    ElectricFields E;
    SimulationContext context { particles, patch, Proj };

    for (unsigned int ipart = ipart_min; ipart < ipart_max; ipart++) {
        // Current charge state of the ion
        Z = (unsigned int)(particles->charge(ipart));

        // If ion already fully ionized then skip
        if (Z == atomic_number_) {
            continue;
        }

        // Absolute value of the electric field normalized in atomic units
        E = calculateElectricFields(Epart, ipart);
        if (E.abs < 1e-10) {
            continue;
        }
        E.inv = 1/E.abs;

        // --------------------------------
        // Start of the Monte-Carlo routine
        // --------------------------------

        ran_p = patch->rand_->uniform();
        IonizRate_tunnel[Z] = ionizationRate(Z, E);

        // k_times will give the nb of ionization events
        k_times = 0;
        Zp1 = Z + 1;

        if (Zp1 == atomic_number_) {
            // if ionization of the last electron: single ionization
            // -----------------------------------------------------
            if (ran_p < 1.0 - exp(-IonizRate_tunnel[Z] * dt)) {
                k_times = 1;
            }

        } else {
            // else : multiple ionization can occur in one time-step
            //        partial & final ionization are decoupled (see Nuter Phys.
            //        Plasmas)
            // -------------------------------------------------------------------------

            // initialization
            Mult = 1.0;
            Dnom_tunnel[0] = 1.0;
            Pint_tunnel = exp(-IonizRate_tunnel[Z] * dt);  // cummulative prob.

            // multiple ionization loop while Pint_tunnel < ran_p and still partial
            // ionization
            while ((Pint_tunnel < ran_p) and (k_times < atomic_number_ - Zp1)) {
                newZ = Zp1 + k_times;
                IonizRate_tunnel[newZ] = ionizationRate(newZ, E);
                D_sum = 0.0;
                P_sum = 0.0;
                Mult *= IonizRate_tunnel[Z + k_times];
                for (unsigned int i = 0; i < k_times + 1; i++) {
                    Dnom_tunnel[i] = Dnom_tunnel[i] / (IonizRate_tunnel[newZ] - IonizRate_tunnel[Z + i]);
                    D_sum += Dnom_tunnel[i];
                    P_sum += exp(-IonizRate_tunnel[Z + i] * dt) * Dnom_tunnel[i];
                }
                Dnom_tunnel[k_times + 1] = -D_sum;
                P_sum = P_sum + Dnom_tunnel[k_times + 1] * exp(-IonizRate_tunnel[newZ] * dt);
                Pint_tunnel = Pint_tunnel + P_sum * Mult;

                k_times++;
            }  // END while

            // final ionization (of last electron)
            if (((1.0 - Pint_tunnel) > ran_p) && (k_times == atomic_number_ - Zp1)) {
                k_times++;
            }
        }  // END Multiple ionization routine

        computeIonizationCurrents(ipart, Z, k_times, E, context);
        createNewElectrons(ipart, Z, k_times, E, context);

    }  // Loop on particles
}

ElectricFields IonizationTunnel::calculateElectricFields(const vector<const vector<double>*>& Epart, unsigned int ipart)
{
    ElectricFields E;
    int nparts = Epart[0]->size() / 3;

    E.x = (*Epart[0])[ipart];
    E.y = (*Epart[0])[nparts+ipart];
    E.z = (*Epart[0])[2*nparts+ipart];
    E.abs = EC_to_au * sqrt(E.x*E.x + E.y*E.y + E.z*E.z);
    return E;
}

void IonizationTunnel::computeIonizationCurrents(unsigned int ipart, unsigned int Z, unsigned int k_times, const ElectricFields& E, const SimulationContext& context) 
{
    if (context.patch->EMfields->Jx_ != NULL) {  // For the moment ionization current is
                                         // not accounted for in AM geometry
        double TotalIonizPot = 0.0;
        for (unsigned int i=0; i<k_times; i++) {
            TotalIonizPot += potential_[Z+i];
        }

        double factorJion_0 = au_to_mec2 * EC_to_au * EC_to_au * invdt;
        double factorJion = factorJion_0 * E.inv * E.inv;
        factorJion *= TotalIonizPot;

        LocalFields Jion;
        Jion.x = factorJion * E.x;
        Jion.y = factorJion * E.y;
        Jion.z = factorJion * E.z;

        context.Proj->ionizationCurrents(context.patch->EMfields->Jx_, context.patch->EMfields->Jy_, context.patch->EMfields->Jz_, *(context.particles), ipart, Jion);
    }
}

void IonizationTunnel::createNewElectrons(unsigned int ipart, unsigned int, unsigned int k_times, const ElectricFields&, const SimulationContext& context)
{
    if (k_times != 0) {
        new_electrons.createParticle();
        int idNew = new_electrons.size() - 1;
        for (unsigned int i = 0; i < new_electrons.dimension(); i++) {
            new_electrons.position(i, idNew) = context.particles->position(i, ipart);
        }
        for (unsigned int i = 0; i < 3; i++) {
            new_electrons.momentum(i, idNew) = context.particles->momentum(i, ipart) * ionized_species_invmass;
        }
        new_electrons.weight(idNew) = double(k_times) * context.particles->weight(ipart);
        new_electrons.charge(idNew) = -1;

        if (save_ion_charge_) {
            ion_charge_.push_back(context.particles->charge(ipart));
        }

        // Increase the charge of the particle
        context.particles->charge(ipart) += k_times;
    }
}


double IonizationTunnel::ionizationRate(unsigned int Z, const ElectricFields& E)
{
    double delta = gamma_tunnel_[Z] / E.abs;
    return beta_tunnel_[Z] * exp(-delta * one_third_ + alpha_tunnel_[Z] * log(delta));
}

