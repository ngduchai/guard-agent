#include "IonizationTunnelEnvelopeAveraged.h"

#include <cmath>

#include "Particles.h"
#include "Species.h"

using namespace std;


IonizationTunnelEnvelopeAveraged::IonizationTunnelEnvelopeAveraged( Params &params, Species *species ) : IonizationTunnel( params, species )
{
    DEBUG( "Creating the Tunnel Envelope Ionizaton Averaged class" );

    Ip_times2_to_minus3ov4_.resize( atomic_number_+1 );
    
    for( unsigned int Z=0 ; Z<atomic_number_ ; Z++ ) {
        DEBUG( "Z : " << Z );
        Ip_times2_to_minus3ov4_[Z] = 1.0 / sqrt(sqrt((2.*potential_[Z] * 2.*potential_[Z] * 2.*potential_[Z]))); // (2I_p)^{-3/4}
    }
    
    ellipticity_         = params.envelope_ellipticity;
    
    cos_phi_             = cos(params.envelope_polarization_phi);
    sin_phi_             = sin(params.envelope_polarization_phi);
    
    DEBUG( "Finished Creating the Tunnel Envelope Ionizaton Averaged class" );
    
}


ElectricFields IonizationTunnelEnvelopeAveraged::calculateElectricFields(const vector<const vector<double>*>& Epart, unsigned int ipart) {
    ElectricFields E;
    int nparts = Epart[0]->size() / 3;

    E.x = (*Epart[0])[ipart];
    E.y = (*Epart[0])[nparts+ipart];
    E.z = (*Epart[0])[2*nparts+ipart];
    double E_env = (*Epart[1])[ipart];
    double Ex_env = (*Epart[2])[ipart];
    phi_env_ = (*Epart[3])[ipart];

    // Absolute value of the electric field |E_plasma| (from the plasma) normalized in atomic units
    double E_sq    = (EC_to_au * EC_to_au) * ( E.x*E.x + E.y*E.y + E.z*E.z );

    // Laser envelope electric field normalized in atomic units, using both transverse and longitudinal components:
    // |E_envelope|^2 = |Env_E|^2 + |Env_Ex|^2
    double EnvE_sq = (EC_to_au * EC_to_au) * ( E_env*E_env + Ex_env*Ex_env );

    // Effective electric field for ionization:
    // |E| = sqrt(|E_plasma|^2+|E_envelope|^2)
    E.abs = sqrt(E_sq+EnvE_sq);
    E.inv = 1/E.abs;
 
    return E;
}

double IonizationTunnelEnvelopeAveraged::ionizationRate(unsigned int Z, const ElectricFields& E)
{
    double coeff_ellipticity__in_ionization_rate;

    double delta = gamma_tunnel_[Z] / E.abs;

    // Corrections on averaged ionization rate given by the polarization ellipticity_  
    if( ellipticity_==0. ){ // linear polarization
        coeff_ellipticity__in_ionization_rate = sqrt((3./M_PI)/delta*2.);
    } else if( ellipticity_==1. ){ // circular polarization
        // for circular polarization, the ionization rate is unchanged
        coeff_ellipticity__in_ionization_rate = 1.; 
    } else {
        ERROR("ellipticity_ not in {0,1}")
    }

    return coeff_ellipticity__in_ionization_rate * IonizationTunnel::ionizationRate(Z, E);
}

void IonizationTunnelEnvelopeAveraged::computeIonizationCurrents(unsigned int, unsigned int, unsigned int, const ElectricFields&, const SimulationContext&) 
{
    // ---- Ionization ion current cannot be computed with the envelope ionization model
}

void IonizationTunnelEnvelopeAveraged::createNewElectrons(unsigned int ipart, unsigned int Z, unsigned int k_times, const ElectricFields& E, const SimulationContext& context)
{
    double Aabs, p_perp; 
    if( k_times !=0 ) {
        // loop on all the ionization levels that have been ionized for this ion:
        // each level creates an electron
        for( unsigned int ionized_level = 0; ionized_level < k_times ; ionized_level++){
            
            new_electrons.createParticle();
            //new_electrons.initialize( new_electrons.size()+1, new_electrons.dimension() );
            int idNew = new_electrons.size() - 1;

            // The new electron is in the same position of the atom where it originated from
            for( unsigned int i=0; i<new_electrons.dimension(); i++ ) {
                new_electrons.position( i, idNew )=context.particles->position( i, ipart );
            }
            for( unsigned int i=0; i<3; i++ ) {
                new_electrons.momentum( i, idNew ) = context.particles->momentum( i, ipart )*ionized_species_invmass;
            }

       
            // ----  Initialise the momentum, weight and charge of the new electron

            if (ellipticity_==0.){ // linear polarization

                double rand_gaussian  = context.patch->rand_->normal();

                Aabs    = sqrt(2. * phi_env_ ); // envelope of the laser vector potential component along the polarization direction
            
                // recreate gaussian distribution with rms momentum spread for linear polarization, estimated by C.B. Schroeder
                // C. B. Schroeder et al., Phys. Rev. ST Accel. Beams 17, 2014, first part of Eqs. 7,10
                double Ip_times2_power_minus3ov4 = Ip_times2_to_minus3ov4_[Z+ionized_level];
                p_perp = rand_gaussian * Aabs * sqrt(1.5*E.abs) * Ip_times2_power_minus3ov4;

                // add the transverse momentum p_perp to obtain a gaussian distribution
                // in the momentum in the polarization direction p_perp, following Schroeder's result
                new_electrons.momentum( 1, idNew ) += p_perp*cos_phi_;
                new_electrons.momentum( 2, idNew ) += p_perp*sin_phi_;

                // initialize px to take into account the average drift <px>=A^2/4 and the px=|p_perp|^2/2 relation
                // Note: the agreement in the phase space between envelope and standard laser simulation will be seen only after the passage of the ionizing laser
                new_electrons.momentum( 0, idNew ) += Aabs*Aabs/4. + p_perp*p_perp/2.;

            } else if (ellipticity_==1.){ // circular polarization

                // extract a random angle between 0 and 2pi, and assign p_perp = eA
                double rand_times_2pi = context.patch->rand_->uniform_2pi(); // from uniform distribution between [0,2pi]
            
                Aabs    = sqrt(2. * phi_env_ );

                p_perp = Aabs;   // in circular polarization it corresponds to a0/sqrt(2)
                new_electrons.momentum( 1, idNew ) += p_perp*cos(rand_times_2pi)/sqrt(2);
                new_electrons.momentum( 2, idNew ) += p_perp*sin(rand_times_2pi)/sqrt(2);
 
                // initialize px to take into account the average drift <px>=A^2/4 and the px=|p_perp|^2/2 result
                // Note: the agreement in the phase space between envelope and standard laser simulation will be seen only after the passage of the ionizing laser
                new_electrons.momentum( 0, idNew ) += Aabs*Aabs/2.;
        
            }

            if( save_ion_charge_ ) {
                ion_charge_.push_back( context.particles->charge( ipart ) );
            }
            
            // weight and charge of the new electron
            new_electrons.weight( idNew )= context.particles->weight( ipart );
            new_electrons.charge( idNew )= -1;

        } // end loop on electrons to create

        // Increase the charge of the ion particle
        context.particles->charge( ipart ) += k_times;
    } // end if electrons are created
}
