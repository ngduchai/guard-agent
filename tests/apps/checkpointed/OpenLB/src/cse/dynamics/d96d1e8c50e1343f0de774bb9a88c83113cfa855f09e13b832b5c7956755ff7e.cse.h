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
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::RLB, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<1, -1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<1, -1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x10 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x11 = parameters.template get<descriptors::OMEGA>();
auto x12 = x11 + V{-1};
auto x13 = x10 + V{-1};
auto x14 = V{1} / (x13);
auto x15 = cell[0] + cell[2] + V{2}*cell[3] + V{2}*cell[4] + V{2}*cell[5] + cell[6] + V{1};
auto x16 = x14*x15;
auto x17 = V{3}*x9;
auto x18 = ((x9)*(x9));
auto x19 = V{3}*x18;
auto x20 = ((x10)*(x10));
auto x21 = V{1.5}*x20;
auto x22 = -x21;
auto x23 = x19 + x22 + V{1};
auto x24 = x17 + x23;
auto x25 = V{0.0555555555555555}*x16;
auto x26 = x10 - x9;
auto x27 = V{4.5}*((x26)*(x26));
auto x28 = -x17;
auto x29 = V{3}*x10;
auto x30 = V{1.5}*x18;
auto x31 = x21 + V{-1};
auto x32 = x30 + x31;
auto x33 = x29 + x32;
auto x34 = x28 + x33;
auto x35 = -x27 + x34;
auto x36 = V{0.111111111111111}*x14;
auto x37 = x15*x36;
auto x38 = x17 - x19 + x31;
auto x39 = V{4.5}*((x10 + x9)*(x10 + x9));
auto x40 = x17 + x33 - x39;
auto x41 = -x29;
auto x42 = V{1} - x30;
auto x43 = V{3}*x20 + x42;
auto x44 = x41 + x43;
auto x45 = V{1.66533453693773e-16}*cell[2] + V{1.33226762955019e-15}*cell[3] + V{6.66133814775094e-16}*cell[4] + V{8.88178419700125e-16}*cell[5] + V{1.66533453693773e-16}*cell[6] + V{1.11022302462516e-16};
auto x46 = V{0.444444444444444}*x14*x15*x32 - V{0.222222222222222}*x16*x44 - x24*x37 + x25*x40 + x37*x38 + x45;
auto x47 = x25*x35 + x46;
auto x48 = x24*x47;
auto x49 = x44*x47;
auto x50 = V{0.0277777777777778}*x14;
auto x51 = -V{4.5}*((x26)*(x26));
auto x52 = x17 + x41;
auto x53 = x34 + x51;
auto x54 = x25*x53 + x46;
auto x55 = V{0.00462962962962963}*x14;
auto x56 = x40*x47;
auto x57 = V{0.0833333333333334}*cell[2];
auto x58 = V{0.0833333333333334}*cell[6];
auto x59 = V{0.166666666666667}*cell[4];
auto x60 = -V{1.73472347597681e-18}*x14*x15*x38 - V{0.00925925925925926}*x14*x38*x47 + V{0.00925925925925926}*x14*x48 + V{0.0185185185185185}*x14*x49 + V{1.73472347597681e-18}*x16*x24 + V{4.62592926927149e-18}*x16*x44 + x57 + x58 + x59 + V{0.0555555555555556};
auto x61 = x12*(V{0.166666666666666}*cell[3] - V{0.833333333333333}*cell[5] + V{1.01192202765314e-18}*x14*x15*x35 + V{1.87928376564154e-18}*x14*x15*x40 + V{0.0231481481481481}*x14*x35*x47 - x55*x56 - x60) + V{-0.0277777777777778};
auto x62 = V{0.00925925925925926}*x14;
auto x63 = x35*x47;
auto x64 = V{1.44560289664734e-18}*x16;
auto x65 = V{3.46944695195361e-18}*x16;
auto x66 = V{0.037037037037037}*x14;
auto x67 = -V{0.333333333333334}*cell[3] - V{0.333333333333333}*cell[5] + V{-0.0555555555555556};
auto x68 = -V{0.333333333333333}*cell[2] + V{0.333333333333333}*cell[4] - V{0.333333333333333}*cell[6] + x67;
auto x69 = V{0.833333333333333}*cell[3];
auto x70 = -1/x13;
auto x71 = x15*x70;
auto x72 = V{3.85185988877447e-34}*x71;
auto x73 = x23 + x28;
auto x74 = V{0.111111111111111}*x71;
auto x75 = V{0.0555555555555555}*x71;
auto x76 = x22 + x42;
auto x77 = x27 + x52 + x76;
auto x78 = -x40;
auto x79 = x24*x74 - V{0.444444444444444}*x32*x71 + V{0.222222222222222}*x44*x71 + x45 + x73*x74 + x75*x77 + x75*x78;
auto x80 = x44*x79;
auto x81 = V{0.0185185185185185}*x70;
auto x82 = x24*x79;
auto x83 = x73*x79;
auto x84 = V{0.00925925925925926}*x70;
auto x85 = x77*x79;
auto x86 = x78*x79;
auto x87 = V{1.44560289664734e-18}*x71;
auto x88 = x77*x87 + x78*x87 + x84*x85 + x84*x86;
auto x89 = -x12*(V{0.166666666666667}*cell[2] - V{0.666666666666667}*cell[4] + V{0.166666666666667}*cell[6] + x24*x72 + V{1.15648231731787e-17}*x44*x71 + x67 + V{0.0740740740740741}*x70*x80 + x72*x73 - x81*x82 - x81*x83 + x88) + V{0.111111111111111};
auto x90 = V{3.46944695195361e-18}*x71;
auto x91 = V{0.037037037037037}*x70;
auto x92 = V{1.73472347597681e-18}*x71;
auto x93 = V{0.00925925925925926}*x70;
auto x0 = -x12*(-V{0.666666666666667}*cell[2] - V{2.66666666666667}*cell[3] - V{1.33333333333333}*cell[4] - V{2.66666666666667}*cell[5] - V{0.666666666666667}*cell[6] + V{1.15648231731787e-17}*x14*x15*x35 + V{1.38777878078145e-17}*x14*x15*x38 + V{1.15648231731787e-17}*x14*x15*x40 + V{0.0740740740740741}*x14*x35*x47 + V{0.0740740740740741}*x14*x38*x47 + V{0.0740740740740741}*x14*x40*x47 - V{0.0740740740740741}*x14*x48 - V{0.148148148148148}*x14*x49 - V{1.38777878078145e-17}*x16*x24 - V{3.70074341541719e-17}*x16*x44 + V{-0.444444444444444}) + V{0.444444444444444}*x14*x32*x47 + V{-0.444444444444444};
auto x1 = x50*x54*(x32 + x51 + x52) + x61;
auto x2 = x12*(V{0.037037037037037}*x14*x49 + V{2.31296463463574e-18}*x16*x44 - x24*x65 + x35*x64 + x38*x47*x66 + x38*x65 + x40*x64 - x48*x66 + x56*x62 + x62*x63 + x68) + x36*x38*x54 + V{-0.111111111111111};
auto x3 = x12*(V{0.166666666666667}*cell[5] + V{1.87928376564154e-18}*x14*x15*x35 + V{1.01192202765314e-18}*x14*x15*x40 + V{0.0231481481481481}*x14*x40*x47 - x55*x63 - x60 - x69) + x40*x50*x54 + V{-0.0277777777777778};
auto x4 = -x36*x49 - x89;
auto x5 = x50*x53*x54 + x61;
auto x6 = x12*(x24*x90 - V{2.31296463463574e-18}*x44*x71 + x68 - V{0.037037037037037}*x70*x80 + x73*x90 + x82*x91 + x83*x91 + x88) - x36*x48 + V{-0.111111111111111};
auto x7 = x12*(V{0.166666666666667}*cell[5] + x24*x92 + V{4.62592926927149e-18}*x44*x71 - x57 - x58 - x59 - x69 + V{0.0185185185185185}*x70*x80 - V{0.00462962962962963}*x70*x85 + V{0.0231481481481481}*x70*x86 + V{1.87928376564154e-18}*x71*x77 + V{1.01192202765314e-18}*x71*x78 + x73*x92 + x82*x93 + x83*x93 + V{-0.0555555555555556}) - x47*x50*(x17 + x29 + x39 + x76) + V{-0.0277777777777778};
auto x8 = -x36*x47*(x29 + x43) - x89;
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { -V{1}*x14*x54, x18 + x20 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
