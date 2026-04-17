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
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::RLB, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<0, 1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<0, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x10 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x11 = parameters.template get<descriptors::OMEGA>();
auto x9 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x12 = x11 + V{-1};
auto x13 = V{1} / (x9 + V{1});
auto x14 = cell[0] + cell[4] + V{2}*cell[5] + V{2}*cell[6] + V{2}*cell[7] + cell[8] + V{1};
auto x15 = x13*x14;
auto x16 = V{1.38777878078145e-17}*x15;
auto x17 = V{3}*x10;
auto x18 = ((x10)*(x10));
auto x19 = ((x9)*(x9));
auto x20 = V{1.5}*x19;
auto x21 = V{1} - x20;
auto x22 = V{3}*x18 + x21;
auto x23 = x17 + x22;
auto x24 = -x17;
auto x25 = x22 + x24;
auto x26 = V{0.0740740740740741}*x13;
auto x27 = V{0.0555555555555555}*x15;
auto x28 = x10 - x9;
auto x29 = V{4.5}*((x28)*(x28));
auto x30 = V{3}*x9;
auto x31 = V{1.5}*x18;
auto x32 = x31 + V{-1};
auto x33 = x20 + x32;
auto x34 = x17 + x33;
auto x35 = -x30 + x34;
auto x36 = -x29 + x35;
auto x37 = V{0.444444444444444}*x13;
auto x38 = x14*x37;
auto x39 = V{0.111111111111111}*x13;
auto x40 = x14*x39;
auto x41 = V{3}*x19;
auto x42 = x30 - x31;
auto x43 = x41 + x42 + V{1};
auto x44 = V{4.5}*((x10 + x9)*(x10 + x9));
auto x45 = x21 + x42;
auto x46 = x17 + x44 + x45;
auto x47 = V{1.66533453693773e-16}*cell[4] + V{1.33226762955019e-15}*cell[5] + V{6.66133814775094e-16}*cell[6] + V{8.88178419700125e-16}*cell[7] + V{1.66533453693773e-16}*cell[8] + V{0.222222222222222}*x15*x43 + x23*x40 + x25*x40 + x27*x46 + V{1.11022302462516e-16};
auto x48 = -x33*x38 + x47;
auto x49 = -x27*x36 + x48;
auto x50 = x23*x49;
auto x51 = x25*x49;
auto x52 = x46*x49;
auto x53 = x43*x49;
auto x54 = V{1.15648231731787e-17}*x15;
auto x55 = x36*x49;
auto x56 = V{0.0277777777777778}*x13;
auto x57 = -V{4.5}*((x28)*(x28));
auto x58 = V{1.01192202765314e-18}*x15;
auto x59 = x24 + x29 + x45;
auto x60 = V{1.87928376564154e-18}*x15;
auto x61 = V{0.0231481481481481}*x13;
auto x62 = x27*x59 - x33*x38 + x47;
auto x63 = x59*x62;
auto x64 = V{0.00462962962962963}*x13;
auto x65 = x46*x62;
auto x66 = V{0.00925925925925926}*x13;
auto x67 = x23*x62;
auto x68 = x25*x62;
auto x69 = V{0.0185185185185185}*x13;
auto x70 = x43*x62;
auto x71 = V{1.73472347597681e-18}*x15;
auto x72 = -V{0.0833333333333334}*cell[4] - V{0.166666666666667}*cell[6] - V{0.0833333333333334}*cell[8] + V{4.62592926927149e-18}*x15*x43 + x23*x71 + x25*x71 + V{-0.0555555555555556};
auto x73 = x66*x67 + x66*x68 + x69*x70 + x72;
auto x74 = -x12*(-V{0.833333333333333}*cell[5] + V{0.166666666666667}*cell[7] + x46*x60 + x58*x59 + x61*x63 - x64*x65 + x73) + V{0.0277777777777778};
auto x75 = V{0.00925925925925926}*x13;
auto x76 = V{1.44560289664734e-18}*x15;
auto x77 = V{0.0740740740740741}*x13;
auto x78 = V{0.0185185185185185}*x13;
auto x79 = V{0.333333333333333}*cell[7];
auto x80 = V{0.333333333333334}*cell[5];
auto x81 = V{3.85185988877447e-34}*x15;
auto x82 = V{0.166666666666667}*cell[4] - V{0.666666666666667}*cell[6] + V{0.166666666666667}*cell[8] + V{1.15648231731787e-17}*x15*x43 + x23*x81 + x25*x81 + x46*x76 - x79 - x80 + V{-0.0555555555555556};
auto x83 = V{0.166666666666666}*cell[5] - V{0.833333333333333}*cell[7] + x46*x58;
auto x84 = -x27*(x35 + x57) + x48;
auto x85 = x55*x75;
auto x86 = x36*x76;
auto x87 = x12*(-V{0.333333333333333}*cell[4] + V{0.333333333333333}*cell[6] - V{0.333333333333333}*cell[8] + V{3.46944695195361e-18}*x13*x14*x23 + V{3.46944695195361e-18}*x13*x14*x25 + V{1.44560289664734e-18}*x13*x14*x46 + V{0.037037037037037}*x13*x23*x49 + V{0.037037037037037}*x13*x25*x49 + V{0.00925925925925926}*x13*x46*x49 - V{0.037037037037037}*x13*x53 - V{2.31296463463574e-18}*x15*x43 - x79 - x80 - x85 - x86 + V{-0.0555555555555556}) + V{-0.111111111111111};
auto x0 = -x12*(-V{0.666666666666667}*cell[4] - V{2.66666666666667}*cell[5] - V{1.33333333333333}*cell[6] - V{2.66666666666667}*cell[7] - V{0.666666666666667}*cell[8] + V{0.148148148148148}*x13*x53 + V{3.70074341541719e-17}*x15*x43 + x16*x23 + x16*x25 + x26*x50 + x26*x51 + x26*x52 - x26*x55 - x36*x54 + x46*x54 + V{-0.444444444444444}) - x33*x37*x49 + V{-0.444444444444444};
auto x1 = -x49*x56*(x24 + x30 + x33 + x57) - x74;
auto x2 = x12*(x59*x76 + x63*x75 + x65*x75 - x67*x78 - x68*x78 + x70*x77 + x82) - x39*x49*(x30 + x32 - x41) + V{-0.111111111111111};
auto x3 = x12*(x59*x60 + x61*x65 - x63*x64 + x73 + x83) - x49*x56*(x30 + x34 - x44) + V{-0.0277777777777778};
auto x4 = x25*x39*x84 + x87;
auto x5 = -x55*x56 - x74;
auto x6 = x12*(-x50*x78 - x51*x78 + x52*x75 + x53*x77 + x82 - x85 - x86) + x39*x43*x84 + V{-0.111111111111111};
auto x7 = x12*(-x36*x60 + x50*x66 + x51*x66 + x52*x61 + x53*x69 + x55*x64 + x72 + x83) + x46*x56*x84 + V{-0.0277777777777778};
auto x8 = x23*x39*x84 + x87;
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { V{1}*x13*x84, x18 + x19 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
