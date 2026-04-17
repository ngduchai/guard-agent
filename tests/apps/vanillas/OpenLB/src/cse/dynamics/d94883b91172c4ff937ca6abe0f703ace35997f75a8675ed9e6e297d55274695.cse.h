/*  This file is part of the OpenLB library
 *
 *  Copyright (C) Adrian Kummerlaender, Shota Ito
 *  E-mail contact: info@openlb.net
 *  The most recent release of OpenLB can be downloaded at
 *  <http://www.openlb.net/>
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; either version 2
 *  of the License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public
 *  License along with this program; if not, write to the Free
 *  Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 *  Boston, MA  02110-1301, USA.
*/

/*  ========================================================
 *  ==  WARNING: This is an automatically generated file, ==
 *  ==                  do not modify.                    ==
 *  ========================================================
 */

#pragma once


namespace olb {

namespace dynamics {

template <typename T, typename... FIELDS>
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::RLB, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<1, 1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<1, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x11 = parameters.template get<descriptors::OMEGA>();
auto x10 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x9 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x12 = x11 + V{-1};
auto x13 = V{1} / (x10 + V{1});
auto x14 = cell[0] + V{2}*cell[1] + cell[2] + cell[6] + V{2}*cell[7] + V{2}*cell[8] + V{1};
auto x15 = x13*x14;
auto x16 = V{3}*x9;
auto x17 = ((x9)*(x9));
auto x18 = V{3}*x17;
auto x19 = ((x10)*(x10));
auto x20 = V{1.5}*x19;
auto x21 = x20 + V{-1};
auto x22 = x16 - x18 + x21;
auto x23 = V{3}*x10;
auto x24 = -x23;
auto x25 = x10 - x9;
auto x26 = V{4.5}*((x25)*(x25));
auto x27 = V{1.5}*x17;
auto x28 = x21 + x27;
auto x29 = x16 + x28;
auto x30 = x24 - x26 + x29;
auto x31 = V{0.0740740740740741}*x13;
auto x32 = V{0.111111111111111}*x13;
auto x33 = x14*x32;
auto x34 = V{0.444444444444444}*x13;
auto x35 = x14*x34;
auto x36 = V{0.0555555555555555}*x15;
auto x37 = V{1} - x20;
auto x38 = x18 + x37;
auto x39 = x16 + x38;
auto x40 = -x27;
auto x41 = x23 + x40;
auto x42 = V{3}*x19 + V{1};
auto x43 = x41 + x42;
auto x44 = V{4.5}*((x10 + x9)*(x10 + x9));
auto x45 = x37 + x41;
auto x46 = x16 + x44 + x45;
auto x47 = V{8.88178419700125e-16}*cell[1] + V{1.66533453693773e-16}*cell[2] + V{1.66533453693773e-16}*cell[6] + V{8.88178419700125e-16}*cell[7] + V{2.22044604925031e-16}*cell[8] + V{0.222222222222222}*x15*x43 + x33*x39 + x36*x46 + V{1.11022302462516e-16};
auto x48 = -x22*x33 - x28*x35 - x30*x36 + x47;
auto x49 = x22*x48;
auto x50 = x30*x48;
auto x51 = V{0.0277777777777778}*x13;
auto x52 = V{1.73472347597681e-18}*x15;
auto x53 = V{0.0231481481481481}*x13;
auto x54 = -x16;
auto x55 = x26 + x45 + x54;
auto x56 = x38 + x54;
auto x57 = -x28*x35 + x33*x56 + x36*x55 + x47;
auto x58 = x55*x57;
auto x59 = V{8.67361737988404e-19}*x15;
auto x60 = V{0.00462962962962963}*x13;
auto x61 = x46*x57;
auto x62 = V{0.00925925925925926}*x13;
auto x63 = x39*x57;
auto x64 = x56*x57;
auto x65 = V{0.0185185185185185}*x13;
auto x66 = x43*x57;
auto x67 = -V{0.0833333333333334}*cell[2] - V{0.0833333333333334}*cell[6] - V{0.166666666666667}*cell[8] + V{4.62592926927149e-18}*x15*x43 + x39*x52 + V{-0.0555555555555556};
auto x68 = x52*x56 + x62*x63 + x62*x64 + x65*x66 + x67;
auto x69 = -x12*(-V{0.833333333333333}*cell[1] + V{0.166666666666667}*cell[7] + x46*x52 + x53*x58 + x55*x59 - x60*x61 + x68) + V{0.0277777777777778};
auto x70 = V{0.333333333333333}*cell[7];
auto x71 = -x70;
auto x72 = V{0.333333333333334}*cell[1];
auto x73 = V{0.333333333333333}*cell[2];
auto x74 = V{0.333333333333333}*cell[6];
auto x75 = V{1.73472347597681e-18}*x15;
auto x76 = V{0.00925925925925926}*x13;
auto x77 = V{3.46944695195361e-18}*x15;
auto x78 = V{0.037037037037037}*x13;
auto x79 = V{0.037037037037037}*x13;
auto x80 = V{2.31296463463574e-18}*x15*x43;
auto x81 = V{0.166666666666667}*cell[1] - V{0.833333333333333}*cell[7] + x46*x59;
auto x82 = V{3.85185988877447e-34}*x15;
auto x83 = V{0.0185185185185185}*x13;
auto x84 = V{8.67361737988404e-19}*x15;
auto x85 = x46*x48;
auto x86 = x43*x48;
auto x87 = x39*x48;
auto x88 = x50*x76;
auto x89 = x12*(-V{0.333333333333333}*cell[1] + V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[6] - V{0.666666666666667}*cell[8] + V{0.0740740740740741}*x13*x86 + V{1.15648231731787e-17}*x15*x43 - x22*x82 - x30*x84 + x39*x82 + x46*x84 + x49*x83 + x71 + x76*x85 - x83*x87 - x88 + V{-0.0555555555555556}) + V{-0.111111111111111};
auto x0 = -x12*(-V{2.66666666666667}*cell[1] - V{0.666666666666667}*cell[2] - V{0.666666666666667}*cell[6] - V{2.66666666666667}*cell[7] - V{1.33333333333333}*cell[8] + V{1.38777878078145e-17}*x13*x14*x39 + V{3.70074341541719e-17}*x13*x14*x43 + V{1.04083408558608e-17}*x13*x14*x46 + V{0.0740740740740741}*x13*x39*x48 + V{0.148148148148148}*x13*x43*x48 + V{0.0740740740740741}*x13*x46*x48 - V{1.38777878078145e-17}*x15*x22 - V{1.04083408558608e-17}*x15*x30 - x31*x49 - x31*x50 + V{-0.444444444444445}) - x28*x34*x48 + V{-0.444444444444444};
auto x1 = -x50*x51 - x69;
auto x2 = x12*(V{0.333333333333333}*cell[8] + x39*x77 + x46*x75 + x55*x75 + x56*x77 + x58*x76 + x61*x76 + x63*x78 + x64*x78 - x66*x79 + x71 - x72 - x73 - x74 - x80 + V{-0.0555555555555556}) - x32*x49 + V{-0.111111111111111};
auto x3 = x12*(x52*x55 + x53*x61 - x58*x60 + x68 + x81) - x48*x51*(x23 + x29 - x44) + V{-0.0277777777777778};
auto x4 = x32*x48*(x24 + x40 + x42) + x89;
auto x5 = -(x48*x51*(x23 + x28 + x54 - V{4.5}*((x25)*(x25))) + x69);
auto x6 = x12*(V{0.333333333333333}*cell[8] + V{3.46944695195361e-18}*x13*x14*x39 + V{1.73472347597681e-18}*x13*x14*x46 + V{0.037037037037037}*x13*x39*x48 + V{0.00925925925925926}*x13*x46*x48 - x22*x77 - x30*x75 - x49*x78 - x70 - x72 - x73 - x74 - x79*x86 - x80 - x88 + V{-0.0555555555555556}) + x32*x87 + V{-0.111111111111111};
auto x7 = x12*(-x22*x52 - x30*x52 - x49*x62 + x50*x60 + x53*x85 + x62*x87 + x65*x86 + x67 + x81) + x51*x85 + V{-0.0277777777777778};
auto x8 = x32*x86 + x89;
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { V{1}*x13*x48, x17 + x19 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
