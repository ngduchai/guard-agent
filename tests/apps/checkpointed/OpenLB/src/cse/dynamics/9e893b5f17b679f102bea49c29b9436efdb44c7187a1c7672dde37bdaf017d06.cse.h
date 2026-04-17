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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::ThirdOrder, collision::SmagorinskyEffectiveOmega<collision::ThirdOrderRLB>, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x10 = parameters.template get<descriptors::OMEGA>();
auto x11 = V{0.444444444444444}*cell[0];
auto x12 = cell[1] + cell[7];
auto x13 = cell[0] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + x12 + V{1};
auto x14 = V{1} / ((x13)*(x13));
auto x15 = V{1.5}*x14;
auto x16 = cell[1] - cell[7];
auto x17 = -cell[5];
auto x18 = cell[3] + x17;
auto x19 = cell[2] - cell[6];
auto x20 = x16 + x18 + x19;
auto x21 = -x20;
auto x22 = ((x21)*(x21));
auto x23 = x15*x22;
auto x24 = -cell[3];
auto x25 = -cell[4] + cell[8];
auto x26 = x12 + x17 + x24 + x25;
auto x27 = ((x26)*(x26));
auto x28 = x15*x27;
auto x29 = x28 + V{-1};
auto x30 = x23 + x29;
auto x31 = V{0.5}/x10;
auto x32 = V{0.0277777691819762}/((x10)*(x10));
auto x33 = V{1} / (x13);
auto x34 = ((x9)*(x9));
auto x35 = x26*x33;
auto x36 = x21*x35;
auto x37 = cell[5] + x16 + x24 + x36;
auto x38 = V{1}*x33;
auto x39 = ((x20)*(x20));
auto x40 = -V{0.333333333333333}*cell[0] + V{0.666666666666667}*cell[1] + V{0.666666666666667}*cell[3] + V{0.666666666666667}*cell[5] + V{0.666666666666667}*cell[7];
auto x41 = V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[4] + V{0.666666666666667}*cell[6] - V{0.333333333333333}*cell[8] + x40;
auto x42 = -x38*x39 + x41;
auto x43 = -V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[4] - V{0.333333333333333}*cell[6] + V{0.666666666666667}*cell[8] - x27*x38 + x40;
auto x44 = V{0.5}*((x42)*(x42)) + V{0.5}*((x43)*(x43));
auto x45 = V{1} - V{1} / (x31 + V{3.00000046417339}*util::sqrt(x32 + x33*x34*util::sqrt(x44 + ((x37)*(x37)))));
auto x46 = V{0.666666666666667}*x33;
auto x47 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x48 = V{4.5}*x14;
auto x49 = x48*((2*cell[1] - 2*cell[5] + x19 + x25)*(2*cell[1] - 2*cell[5] + x19 + x25));
auto x50 = V{3}*cell[3];
auto x51 = V{3}*cell[7];
auto x52 = V{3}*cell[1] - V{3}*cell[5];
auto x53 = V{3}*cell[2] - V{3}*cell[6] + x50 - x51 + x52;
auto x54 = x33*x53;
auto x55 = V{1} - x28;
auto x56 = x54 + x55;
auto x57 = x15*x39;
auto x58 = -x57;
auto x59 = x33*(-V{3}*cell[4] + V{3}*cell[8] - x50 + x51 + x52);
auto x60 = x58 + x59;
auto x61 = util::pow(x13, -3);
auto x62 = V{6.000012}*x61;
auto x63 = x20*x27*x62 + x26*x39*x62;
auto x64 = x20*x35;
auto x65 = cell[1] - cell[7] - x18 - x64;
auto x66 = V{1} - V{1} / (x31 + V{3.00000046417339}*util::sqrt(x32 + x33*x34*util::sqrt(x44 + ((x65)*(x65)))));
auto x67 = V{0.361111111111111}*cell[1];
auto x68 = V{0.361111111111111}*cell[5];
auto x69 = V{0.138888888888889}*cell[3];
auto x70 = V{0.138888888888889}*cell[7];
auto x71 = x20*x33;
auto x72 = V{0.333334}*x65;
auto x73 = V{0.25}*x64;
auto x74 = V{0.166667}*x35*x42 + V{0.166667}*x43*x71;
auto x75 = V{0.0277777777777778}*cell[2];
auto x76 = V{0.0277777777777778}*cell[4];
auto x77 = V{0.0277777777777778}*cell[6];
auto x78 = V{0.0277777777777778}*cell[8];
auto x79 = V{0.0555555555555556}*cell[0];
auto x80 = V{0.0833333333333333}*x33;
auto x81 = x39*x80;
auto x82 = x27*x80;
auto x83 = x75 + x76 + x77 + x78 - x79 - x81 - x82;
auto x84 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x85 = V{3}*x14;
auto x86 = x26*x61;
auto x87 = V{2.999997}*x86;
auto x88 = x20*x61;
auto x89 = V{0.277777777777778}*cell[2];
auto x90 = V{0.277777777777778}*cell[6];
auto x91 = V{0.222222222222222}*cell[4];
auto x92 = V{0.222222222222222}*cell[8];
auto x93 = V{0.166666666666667}*x33;
auto x94 = x27*x93;
auto x95 = V{0.333333333333333}*x33;
auto x96 = V{0.333333}*x35;
auto x97 = x65*x71;
auto x98 = x35*x65;
auto x99 = V{0.111111111111111}*cell[1];
auto x100 = V{0.111111111111111}*cell[3];
auto x101 = V{0.111111111111111}*cell[5];
auto x102 = V{0.111111111111111}*cell[7];
auto x103 = V{0.0555555555555556}*cell[0];
auto x104 = x100 + x101 + x102 - x103 + x99;
auto x105 = -x33*x53;
auto x106 = V{2}*cell[3] + cell[4] - V{2}*cell[7] - cell[8] + x19;
auto x107 = V{18}*x86;
auto x108 = x21*x61;
auto x109 = V{0.138888888888889}*cell[1];
auto x110 = V{0.138888888888889}*cell[5];
auto x111 = V{0.361111111111111}*cell[3];
auto x112 = V{0.361111111111111}*cell[7];
auto x113 = V{0.5}*x35;
auto x114 = -x22*x38 + x41;
auto x115 = x21*x33;
auto x116 = -x37;
auto x117 = V{1}*x116;
auto x118 = -x75 - x76 - x77 - x78 + x79 + x82;
auto x119 = x27*x85;
auto x120 = -x59;
auto x121 = V{6.000003}*x86;
auto x122 = V{0.277777777777778}*cell[4];
auto x123 = V{0.277777777777778}*cell[8];
auto x124 = V{0.222222222222222}*cell[2];
auto x125 = V{0.222222222222222}*cell[6];
auto x126 = x27*x95;
auto x127 = V{0.666667}*x35;
auto x128 = V{0.333334}*x37;
auto x129 = V{1.333334}*x116;
auto x130 = V{0.666666}*x116;
auto x131 = -x100 - x101 - x102 + x103 - x99;
auto x0 = -x30*(V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + x11 + V{0.444444444444444}) - V{1}*x45*(V{0.888888888888889}*cell[1] + V{0.222222222222222}*cell[2] + V{0.888888888888889}*cell[3] + V{0.222222222222222}*cell[4] + V{0.888888888888889}*cell[5] + V{0.222222222222222}*cell[6] + V{0.888888888888889}*cell[7] + V{0.222222222222222}*cell[8] - x11 - x22*x46 - x27*x46) + V{-0.444444444444444};
auto x1 = x47*(x49 + x56 + x60 + x63) + V{1}*x66*(x35*x72 + x67 + x68 - x69 - x70 + x71*x72 - x73 + x74 + x83) + V{-0.0277777777777778};
auto x2 = V{1}*x66*(x104 - x39*x95 + x42*x96 - V{0.666667}*x43*x71 + x89 + x90 - x91 - x92 + x94 + V{0.666666}*x97 - V{1.333334}*x98) + x84*(-V{6.000003}*x27*x88 + x39*x85 + x39*x87 + x56) + V{-0.111111111111111};
auto x3 = -(V{1}*x45*(x109 + x110 - x111 - x112 + x113*x114 + x115*x117 + V{0.5}*x115*x43 + x117*x35 + x118 + x22*x80 + V{0.25}*x36) + x47*(x105 + x107*x22 + V{18}*x108*x27 + x30 - x48*((x106)*(x106)) + x59) + V{0.0277777777777778});
auto x4 = V{1}*x66*(x104 + x122 + x123 - x124 - x125 - x126 + x127*x42 + x39*x93 - V{0.333333}*x43*x71 + V{1.333334}*x97 - V{0.666666}*x98) + x84*(x119 + x120 + x121*x39 - V{2.999997}*x27*x88 + x58 + V{1}) + V{-0.111111111111111};
auto x5 = -x47*(x29 - x49 + x54 + x57 + x59 + x63) - V{1}*x66*(x118 + x128*x35 + x128*x71 - x67 - x68 + x69 + x70 + x73 + x74 + x81) + V{-0.0277777777777778};
auto x6 = -V{1}*x45*(x114*x96 + x115*x130 + V{0.666667}*x115*x43 + x129*x35 + x131 + x22*x95 - x89 - x90 + x91 + x92 - x94) - x84*(-x105 + V{6.000003}*x108*x27 - x22*x85 + x22*x87 + x29) + V{-0.111111111111111};
auto x7 = x47*(x107*x39 - V{18}*x27*x88 + x48*((x106)*(x106)) - x54 + x55 + x60) + V{1}*x66*(-x109 - x110 + x111 + x112 + x113*x42 - V{0.5}*x43*x71 + x73 + x83 + V{1}*x97 - V{1}*x98) + V{-0.0277777777777778};
auto x8 = -V{1}*x45*(x114*x127 + x115*x129 + V{0.333333}*x115*x43 - x122 - x123 + x124 + x125 + x126 + x130*x35 + x131 - x22*x93) - x84*(V{2.999997}*x108*x27 - x119 + x120 + x121*x22 + x23 + V{-1}) + V{-0.111111111111111};
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x13, V{1}*x14*(x27 + x39) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
