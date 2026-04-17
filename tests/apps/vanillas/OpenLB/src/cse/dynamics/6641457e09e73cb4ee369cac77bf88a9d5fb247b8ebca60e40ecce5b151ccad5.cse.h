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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::ThirdOrder, collision::ParameterFromCell<collision::LES::SMAGORINSKY, collision::SmagorinskyEffectiveOmega<collision::ThirdOrderRLB> > >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x10 = parameters.template get<descriptors::OMEGA>();
auto x9 = cell.template getFieldComponent<olb::collision::LES::SMAGORINSKY>(0);
auto x11 = V{0.5}/x10;
auto x12 = V{0.0277777691819762}/((x10)*(x10));
auto x13 = cell[1] + cell[7];
auto x14 = cell[0] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + x13 + V{1};
auto x15 = V{1} / (x14);
auto x16 = ((x9)*(x9));
auto x17 = -cell[3];
auto x18 = cell[1] - cell[7];
auto x19 = -cell[5];
auto x20 = cell[3] + x19;
auto x21 = cell[2] - cell[6];
auto x22 = x18 + x20 + x21;
auto x23 = -x22;
auto x24 = -cell[4] + cell[8];
auto x25 = x13 + x17 + x19 + x24;
auto x26 = x15*x25;
auto x27 = x23*x26;
auto x28 = cell[5] + x17 + x18 + x27;
auto x29 = V{1}*x15;
auto x30 = ((x22)*(x22));
auto x31 = -V{0.333333333333333}*cell[0] + V{0.666666666666667}*cell[1] + V{0.666666666666667}*cell[3] + V{0.666666666666667}*cell[5] + V{0.666666666666667}*cell[7];
auto x32 = V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[4] + V{0.666666666666667}*cell[6] - V{0.333333333333333}*cell[8] + x31;
auto x33 = -x29*x30 + x32;
auto x34 = ((x25)*(x25));
auto x35 = -V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[4] - V{0.333333333333333}*cell[6] + V{0.666666666666667}*cell[8] - x29*x34 + x31;
auto x36 = V{0.5}*((x33)*(x33)) + V{0.5}*((x35)*(x35));
auto x37 = V{1} - V{1} / (x11 + V{3.00000046417339}*util::sqrt(x12 + x15*x16*util::sqrt(x36 + ((x28)*(x28)))));
auto x38 = V{0.444444444444444}*cell[0];
auto x39 = V{0.666666666666667}*x15;
auto x40 = ((x23)*(x23));
auto x41 = V{1} / ((x14)*(x14));
auto x42 = V{1.5}*x41;
auto x43 = x40*x42;
auto x44 = x34*x42;
auto x45 = x44 + V{-1};
auto x46 = x43 + x45;
auto x47 = x22*x26;
auto x48 = cell[1] - cell[7] - x20 - x47;
auto x49 = V{1} - V{1} / (x11 + V{3.00000046417339}*util::sqrt(x12 + x15*x16*util::sqrt(x36 + ((x48)*(x48)))));
auto x50 = V{0.361111111111111}*cell[1];
auto x51 = V{0.361111111111111}*cell[5];
auto x52 = V{0.138888888888889}*cell[3];
auto x53 = V{0.138888888888889}*cell[7];
auto x54 = x15*x22;
auto x55 = V{0.333334}*x48;
auto x56 = V{0.25}*x47;
auto x57 = V{0.166667}*x26*x33 + V{0.166667}*x35*x54;
auto x58 = V{0.0277777777777778}*cell[2];
auto x59 = V{0.0277777777777778}*cell[4];
auto x60 = V{0.0277777777777778}*cell[6];
auto x61 = V{0.0277777777777778}*cell[8];
auto x62 = V{0.0555555555555556}*cell[0];
auto x63 = V{0.0833333333333333}*x15;
auto x64 = x30*x63;
auto x65 = x34*x63;
auto x66 = x58 + x59 + x60 + x61 - x62 - x64 - x65;
auto x67 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x68 = V{4.5}*x41;
auto x69 = x68*((2*cell[1] - 2*cell[5] + x21 + x24)*(2*cell[1] - 2*cell[5] + x21 + x24));
auto x70 = V{3}*cell[3];
auto x71 = V{3}*cell[7];
auto x72 = V{3}*cell[1] - V{3}*cell[5];
auto x73 = V{3}*cell[2] - V{3}*cell[6] + x70 - x71 + x72;
auto x74 = x15*x73;
auto x75 = V{1} - x44;
auto x76 = x74 + x75;
auto x77 = x30*x42;
auto x78 = -x77;
auto x79 = x15*(-V{3}*cell[4] + V{3}*cell[8] - x70 + x71 + x72);
auto x80 = x78 + x79;
auto x81 = util::pow(x14, -3);
auto x82 = V{6.000012}*x81;
auto x83 = x22*x34*x82 + x25*x30*x82;
auto x84 = V{0.277777777777778}*cell[2];
auto x85 = V{0.277777777777778}*cell[6];
auto x86 = V{0.222222222222222}*cell[4];
auto x87 = V{0.222222222222222}*cell[8];
auto x88 = V{0.166666666666667}*x15;
auto x89 = x34*x88;
auto x90 = V{0.333333333333333}*x15;
auto x91 = V{0.333333}*x26;
auto x92 = x48*x54;
auto x93 = x26*x48;
auto x94 = V{0.111111111111111}*cell[1];
auto x95 = V{0.111111111111111}*cell[3];
auto x96 = V{0.111111111111111}*cell[5];
auto x97 = V{0.111111111111111}*cell[7];
auto x98 = V{0.0555555555555556}*cell[0];
auto x99 = x94 + x95 + x96 + x97 - x98;
auto x100 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x101 = V{3}*x41;
auto x102 = x25*x81;
auto x103 = V{2.999997}*x102;
auto x104 = x22*x81;
auto x105 = V{0.138888888888889}*cell[1];
auto x106 = V{0.138888888888889}*cell[5];
auto x107 = V{0.361111111111111}*cell[3];
auto x108 = V{0.361111111111111}*cell[7];
auto x109 = V{0.5}*x26;
auto x110 = -x29*x40 + x32;
auto x111 = x15*x23;
auto x112 = -x28;
auto x113 = V{1}*x112;
auto x114 = -x58 - x59 - x60 - x61 + x62 + x65;
auto x115 = -x15*x73;
auto x116 = V{2}*cell[3] + cell[4] - V{2}*cell[7] - cell[8] + x21;
auto x117 = V{18}*x102;
auto x118 = x23*x81;
auto x119 = V{0.277777777777778}*cell[4];
auto x120 = V{0.277777777777778}*cell[8];
auto x121 = V{0.222222222222222}*cell[2];
auto x122 = V{0.222222222222222}*cell[6];
auto x123 = x34*x90;
auto x124 = V{0.666667}*x26;
auto x125 = -x79;
auto x126 = x101*x34;
auto x127 = V{6.000003}*x102;
auto x128 = V{0.333334}*x28;
auto x129 = V{1.333334}*x112;
auto x130 = V{0.666666}*x112;
auto x131 = -x94 - x95 - x96 - x97 + x98;
auto x0 = -V{1}*x37*(V{0.888888888888889}*cell[1] + V{0.222222222222222}*cell[2] + V{0.888888888888889}*cell[3] + V{0.222222222222222}*cell[4] + V{0.888888888888889}*cell[5] + V{0.222222222222222}*cell[6] + V{0.888888888888889}*cell[7] + V{0.222222222222222}*cell[8] - x34*x39 - x38 - x39*x40) - x46*(V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + x38 + V{0.444444444444444}) + V{-0.444444444444444};
auto x1 = V{1}*x49*(x26*x55 + x50 + x51 - x52 - x53 + x54*x55 - x56 + x57 + x66) + x67*(x69 + x76 + x80 + x83) + V{-0.0277777777777778};
auto x2 = x100*(x101*x30 + x103*x30 - V{6.000003}*x104*x34 + x76) + V{1}*x49*(-x30*x90 + x33*x91 - V{0.666667}*x35*x54 + x84 + x85 - x86 - x87 + x89 + V{0.666666}*x92 - V{1.333334}*x93 + x99) + V{-0.111111111111111};
auto x3 = -(V{1}*x37*(x105 + x106 - x107 - x108 + x109*x110 + x111*x113 + V{0.5}*x111*x35 + x113*x26 + x114 + V{0.25}*x27 + x40*x63) + x67*(x115 + x117*x40 + V{18}*x118*x34 + x46 - x68*((x116)*(x116)) + x79) + V{0.0277777777777778});
auto x4 = x100*(-V{2.999997}*x104*x34 + x125 + x126 + x127*x30 + x78 + V{1}) + V{1}*x49*(x119 + x120 - x121 - x122 - x123 + x124*x33 + x30*x88 - V{0.333333}*x35*x54 + V{1.333334}*x92 - V{0.666666}*x93 + x99) + V{-0.111111111111111};
auto x5 = -V{1}*x49*(x114 + x128*x26 + x128*x54 - x50 - x51 + x52 + x53 + x56 + x57 + x64) - x67*(x45 - x69 + x74 + x77 + x79 + x83) + V{-0.0277777777777778};
auto x6 = -x100*(-x101*x40 + x103*x40 - x115 + V{6.000003}*x118*x34 + x45) - V{1}*x37*(x110*x91 + x111*x130 + V{0.666667}*x111*x35 + x129*x26 + x131 + x40*x90 - x84 - x85 + x86 + x87 - x89) + V{-0.111111111111111};
auto x7 = V{1}*x49*(-x105 - x106 + x107 + x108 + x109*x33 - V{0.5}*x35*x54 + x56 + x66 + V{1}*x92 - V{1}*x93) + x67*(-V{18}*x104*x34 + x117*x30 + x68*((x116)*(x116)) - x74 + x75 + x80) + V{-0.0277777777777778};
auto x8 = -x100*(V{2.999997}*x118*x34 + x125 - x126 + x127*x40 + x43 + V{-1}) - V{1}*x37*(x110*x124 + x111*x129 + V{0.333333}*x111*x35 - x119 - x120 + x121 + x122 + x123 + x130*x26 + x131 - x40*x88) + V{-0.111111111111111};
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x14, V{1}*x41*(x30 + x34) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
