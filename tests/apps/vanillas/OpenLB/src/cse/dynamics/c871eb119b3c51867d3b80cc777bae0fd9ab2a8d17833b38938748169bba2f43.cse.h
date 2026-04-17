/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2021-24 Adrian Kummerlaender, Shota Ito
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
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::RLB, dynamics::DefaultCombination>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, 1>, momenta::RegularizedBoundaryStress<0, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x11 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(1);
auto x9 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x12 = parameters.template get<descriptors::OMEGA>();
auto x10 = x12 + V{-1};
auto x13 = V{0.0740740740740741}*x9;
auto x14 = V{3}*x11;
auto x15 = V{1} / (x9);
auto x16 = V{0.111111111111111}*x9;
auto x17 = x15*(cell[0] + cell[4] + V{2}*cell[5] + V{2}*cell[6] + V{2}*cell[7] + cell[8] + V{1});
auto x18 = V{1} - x17;
auto x19 = ((x18)*(x18));
auto x20 = V{1.5}*x19;
auto x21 = -x20;
auto x22 = ((x11)*(x11));
auto x23 = V{3}*x22 + V{1};
auto x24 = x21 + x23;
auto x25 = x14 + x24;
auto x26 = -x14;
auto x27 = x24 + x26;
auto x28 = V{0.444444444444444}*x9;
auto x29 = V{1.5}*x22;
auto x30 = x29 + V{-1};
auto x31 = x20 + x30;
auto x32 = -x31;
auto x33 = V{0.222222222222222}*x9;
auto x34 = V{3}*x19;
auto x35 = x15*(V{3}*cell[0] + V{3}*cell[4] + V{6}*cell[5] + V{6}*cell[6] + V{6}*cell[7] + V{3}*cell[8] + V{3});
auto x36 = -x29 + V{-2};
auto x37 = x35 + x36;
auto x38 = x34 + x37;
auto x39 = V{0.0555555555555555}*x9;
auto x40 = V{4.5}*((x11 + x17 - 1)*(x11 + x17 - 1));
auto x41 = x14 + x21 + x37 + x40;
auto x42 = x29 + V{2};
auto x43 = -x35 + x42;
auto x44 = x20 + x43;
auto x45 = x14 + x44 - V{4.5}*((-x11 - x18)*(-x11 - x18));
auto x46 = -x45;
auto x47 = V{1.66533453693773e-16}*cell[4] + V{1.33226762955019e-15}*cell[5] + V{6.66133814775094e-16}*cell[6] + V{8.88178419700125e-16}*cell[7] + V{1.66533453693773e-16}*cell[8] + V{1.11022302462516e-16};
auto x48 = x15*(x16*x25 + x16*x27 + x28*x32 + x33*x38 + x39*x41 + x39*x46 + x47);
auto x49 = V{1} - x48;
auto x50 = x11 + x49;
auto x51 = x48 + V{-1};
auto x52 = ((x51)*(x51));
auto x53 = V{1.5}*x52;
auto x54 = V{0.166666666666667}*x9;
auto x55 = V{0.333333333333333}*x9;
auto x56 = x15*(V{4.9960036108132e-16}*cell[4] + V{3.99680288865056e-15}*cell[5] + V{1.99840144432528e-15}*cell[6] + V{2.66453525910038e-15}*cell[7] + V{4.9960036108132e-16}*cell[8] + x25*x55 + x27*x55 + V{1.33333333333333}*x32*x9 + V{0.666666666666667}*x38*x9 + x41*x54 + x46*x54 + V{3.33066907387547e-16});
auto x57 = x42 - x56;
auto x58 = x53 + x57;
auto x59 = x14 + x58 - V{4.5}*((x50)*(x50));
auto x60 = x11 + x51;
auto x61 = V{4.5}*((x60)*(x60));
auto x62 = x26 + x58 - x61;
auto x63 = V{3}*x52;
auto x64 = x57 - x63;
auto x65 = V{1.15648231731787e-17}*x9;
auto x66 = x26 - x40 + x44;
auto x67 = -x34 + x43;
auto x68 = x23 - V{1.5}*((x18)*(x18));
auto x69 = x14 + x68;
auto x70 = x26 + x68;
auto x71 = ((x49)*(x49));
auto x72 = x23 - V{1.5}*x71;
auto x73 = x14 + x72;
auto x74 = x26 + x72;
auto x75 = V{0.0277777777777778}*x9;
auto x76 = x29 + x53 + x56 + V{-4};
auto x77 = V{1.01192202765314e-18}*x9;
auto x78 = V{1.87928376564154e-18}*x9;
auto x79 = V{0.0231481481481481}*x9;
auto x80 = -x59;
auto x81 = V{0.00462962962962963}*x9;
auto x82 = -x53;
auto x83 = x36 + x56;
auto x84 = x14 + x61 + x82 + x83;
auto x85 = V{1.73472347597681e-18}*x9;
auto x86 = V{0.00925925925925926}*x9;
auto x87 = x23 + x82;
auto x88 = x14 + x87;
auto x89 = x26 + x87;
auto x90 = x63 + x83;
auto x91 = -V{0.0833333333333334}*cell[4] - V{0.166666666666667}*cell[6] - V{0.0833333333333334}*cell[8] + x25*x85 + x27*x85 + V{4.62592926927149e-18}*x38*x9 + x86*x88 + x86*x89 + V{0.0185185185185185}*x9*x90 + V{-0.0555555555555556};
auto x92 = -x10*(-V{0.833333333333333}*cell[5] + V{0.166666666666667}*cell[7] + x41*x78 + x46*x77 + x79*x80 - x81*x84 + x91) + V{0.0277777777777778};
auto x93 = V{0.333333333333333}*cell[7];
auto x94 = V{0.333333333333334}*cell[5];
auto x95 = V{3.85185988877447e-34}*x9;
auto x96 = V{0.00925925925925926}*x9;
auto x97 = V{1.44560289664734e-18}*x9;
auto x98 = V{0.0185185185185185}*x9;
auto x99 = -x10*(V{0.166666666666667}*cell[4] - V{0.666666666666667}*cell[6] + V{0.166666666666667}*cell[8] + x25*x95 + x27*x95 + V{1.15648231731787e-17}*x38*x9 + x41*x97 + x46*x97 + x80*x96 + x84*x96 - x88*x98 - x89*x98 + V{0.0740740740740741}*x9*x90 - x93 - x94 + V{-0.0555555555555556}) + V{0.111111111111111};
auto x100 = -x10*(V{0.166666666666666}*cell[5] - V{0.833333333333333}*cell[7] + x41*x77 + x46*x78 + x79*x84 - x80*x81 + x91) + V{0.0277777777777778};
auto x101 = ((-x15*(x16*x69 + x16*x70 - x28*x31 - x33*x67 - x39*x45 - x39*x66 + x47) + 1)*(-x15*(x16*x69 + x16*x70 - x28*x31 - x33*x67 - x39*x45 - x39*x66 + x47) + 1));
auto x102 = -V{1.5}*x101 + x23;
auto x103 = x10*(-V{0.333333333333333}*cell[4] + V{0.333333333333333}*cell[6] - V{0.333333333333333}*cell[8] - x45*x97 - x59*x96 - x62*x96 + V{0.037037037037037}*x64*x9 - x66*x97 + V{2.31296463463574e-18}*x67*x9 + V{3.46944695195361e-18}*x69*x9 + V{3.46944695195361e-18}*x70*x9 + V{0.037037037037037}*x73*x9 + V{0.037037037037037}*x74*x9 - x93 - x94 + V{-0.0555555555555556}) + V{-0.111111111111111};
auto x0 = -x10*(-V{0.666666666666667}*cell[4] - V{2.66666666666667}*cell[5] - V{1.33333333333333}*cell[6] - V{2.66666666666667}*cell[7] - V{0.666666666666667}*cell[8] - x13*x59 - x13*x62 - x45*x65 - V{0.148148148148148}*x64*x9 - x65*x66 - V{3.70074341541719e-17}*x67*x9 + V{1.38777878078145e-17}*x69*x9 + V{1.38777878078145e-17}*x70*x9 + V{0.0740740740740741}*x73*x9 + V{0.0740740740740741}*x74*x9 + V{-0.444444444444444}) - x28*(x30 + x53) + V{-0.444444444444444};
auto x1 = -(x75*(x26 + x76 - V{4.5}*((x50)*(x50))) + x92);
auto x2 = -x16*(-V{4.5}*x71 + x76) - x99;
auto x3 = -(x100 + x75*(x14 + x76 - V{4.5}*((x60)*(x60))));
auto x4 = x103 + x16*(x102 + x26);
auto x5 = -x59*x75 - x92;
auto x6 = -x16*x64 - x99;
auto x7 = -x100 - x62*x75;
auto x8 = x103 + x16*(x102 + x14);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x9, V{1}*x101 + x22 };
}
};

}

}

// Generation Info: commit=b4bd9e586b03551d3ae813fd85ba699e369a044b
