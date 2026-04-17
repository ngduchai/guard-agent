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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SmagorinskyEffectiveOmega<collision::BGK>, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x20 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell[15] + cell[17];
auto x22 = cell[12] + x21;
auto x23 = cell[11] + cell[18];
auto x24 = cell[10] + cell[14] + cell[16];
auto x25 = cell[2] + cell[8] + cell[9];
auto x26 = cell[13] + cell[3];
auto x27 = cell[0] + cell[1] + cell[4] + cell[5] + cell[6] + cell[7] + x22 + x23 + x24 + x25 + x26 + V{1};
auto x28 = V{1} / (x27);
auto x29 = cell[13] + cell[17];
auto x30 = -cell[8];
auto x31 = -cell[2];
auto x32 = -cell[9];
auto x33 = x23 + x30 + x31 + x32;
auto x34 = -cell[4];
auto x35 = cell[5] + x34;
auto x36 = -cell[14] + x35;
auto x37 = x29 + x33 + x36;
auto x38 = cell[13] + cell[15];
auto x39 = -cell[6];
auto x40 = -cell[1];
auto x41 = -cell[7];
auto x42 = x39 + x40 + x41;
auto x43 = -cell[5] + x34;
auto x44 = x24 + x38 + x42 + x43;
auto x45 = x28*x44;
auto x46 = -cell[18];
auto x47 = -cell[3];
auto x48 = cell[9] + x30;
auto x49 = x46 + x47 + x48;
auto x50 = cell[7] + x39;
auto x51 = -cell[16] + x50;
auto x52 = x22 + x49 + x51;
auto x53 = -cell[15] + cell[16];
auto x54 = -cell[17];
auto x55 = cell[18] + x54;
auto x56 = V{0.333333333333333}*cell[0];
auto x57 = V{0.333333333333333}*cell[17];
auto x58 = V{0.333333333333333}*cell[18];
auto x59 = V{0.333333333333333}*cell[8];
auto x60 = V{0.333333333333333}*cell[9];
auto x61 = V{1}*x28;
auto x62 = ((x44)*(x44));
auto x63 = V{0.333333333333333}*cell[11];
auto x64 = V{0.333333333333333}*cell[2];
auto x65 = -V{0.666666666666667}*cell[15] - V{0.666666666666667}*cell[16] - V{0.666666666666667}*cell[6] - V{0.666666666666667}*cell[7] + x63 + x64;
auto x66 = V{0.333333333333333}*cell[12];
auto x67 = V{0.333333333333333}*cell[3];
auto x68 = -V{0.666666666666667}*cell[13] - V{0.666666666666667}*cell[14] - V{0.666666666666667}*cell[4] - V{0.666666666666667}*cell[5] + x66 + x67;
auto x69 = V{0.333333333333333}*cell[15];
auto x70 = V{0.333333333333333}*cell[16];
auto x71 = V{0.333333333333333}*cell[6];
auto x72 = V{0.333333333333333}*cell[7];
auto x73 = ((x37)*(x37));
auto x74 = V{0.333333333333333}*cell[10];
auto x75 = V{0.333333333333333}*cell[1];
auto x76 = -V{0.666666666666667}*cell[17] - V{0.666666666666667}*cell[18] - V{0.666666666666667}*cell[8] - V{0.666666666666667}*cell[9] + x56 + x74 + x75;
auto x77 = V{0.333333333333333}*cell[13];
auto x78 = V{0.333333333333333}*cell[14];
auto x79 = V{0.333333333333333}*cell[4];
auto x80 = V{0.333333333333333}*cell[5];
auto x81 = ((x52)*(x52));
auto x82 = V{1} / (V{3.00000046417339}*util::sqrt(x28*((x19)*(x19))*util::sqrt(((x45*x52 + x50 + x53)*(x45*x52 + x50 + x53)) + ((x28*x37*x52 + x48 + x55)*(x28*x37*x52 + x48 + x55)) + ((-cell[13] + cell[14] + x35 + x37*x45)*(-cell[13] + cell[14] + x35 + x37*x45)) + V{0.5}*((-V{0.666666666666667}*cell[11] - V{0.666666666666667}*cell[2] + x61*x73 + x68 + x69 + x70 + x71 + x72 + x76)*(-V{0.666666666666667}*cell[11] - V{0.666666666666667}*cell[2] + x61*x73 + x68 + x69 + x70 + x71 + x72 + x76)) + V{0.5}*((-V{0.666666666666667}*cell[12] - V{0.666666666666667}*cell[3] + x61*x81 + x65 + x76 + x77 + x78 + x79 + x80)*(-V{0.666666666666667}*cell[12] - V{0.666666666666667}*cell[3] + x61*x81 + x65 + x76 + x77 + x78 + x79 + x80)) + V{0.5}*((-V{0.666666666666667}*cell[10] - V{0.666666666666667}*cell[1] + x56 + x57 + x58 + x59 + x60 + x61*x62 + x65 + x68)*(-V{0.666666666666667}*cell[10] - V{0.666666666666667}*cell[1] + x56 + x57 + x58 + x59 + x60 + x61*x62 + x65 + x68))) + V{0.0277777691819762}/((x20)*(x20))) + V{0.5}/x20);
auto x83 = V{1} - x82;
auto x84 = V{1} / ((x27)*(x27));
auto x85 = V{1.5}*x84;
auto x86 = x62*x85;
auto x87 = x73*x85;
auto x88 = x81*x85;
auto x89 = x87 + x88 + V{-1};
auto x90 = x86 + x89;
auto x91 = V{0.0555555555555556}*cell[0] + V{0.0555555555555556}*cell[10] + V{0.0555555555555556}*cell[11] + V{0.0555555555555556}*cell[12] + V{0.0555555555555556}*cell[13] + V{0.0555555555555556}*cell[14] + V{0.0555555555555556}*cell[15] + V{0.0555555555555556}*cell[16] + V{0.0555555555555556}*cell[17] + V{0.0555555555555556}*cell[18] + V{0.0555555555555556}*cell[1] + V{0.0555555555555556}*cell[2] + V{0.0555555555555556}*cell[3] + V{0.0555555555555556}*cell[4] + V{0.0555555555555556}*cell[5] + V{0.0555555555555556}*cell[6] + V{0.0555555555555556}*cell[7] + V{0.0555555555555556}*cell[8] + V{0.0555555555555556}*cell[9] + V{0.0555555555555556};
auto x92 = V{3}*x84;
auto x93 = x62*x92;
auto x94 = V{3}*cell[14];
auto x95 = V{3}*cell[16];
auto x96 = V{3}*cell[5];
auto x97 = V{3}*cell[7];
auto x98 = V{3}*cell[13] - V{3}*cell[4];
auto x99 = V{3}*cell[15] - V{3}*cell[6];
auto x100 = x28*(V{3}*cell[10] - V{3}*cell[1] + x94 + x95 - x96 - x97 + x98 + x99);
auto x101 = -x87;
auto x102 = V{1} - x88;
auto x103 = x101 + x102;
auto x104 = x100 + x103;
auto x105 = x73*x92;
auto x106 = V{3}*cell[18];
auto x107 = V{3}*cell[9];
auto x108 = V{3}*cell[17] - V{3}*cell[8];
auto x109 = x28*(V{3}*cell[11] - V{3}*cell[2] + x106 - x107 + x108 - x94 + x96 + x98);
auto x110 = -x86;
auto x111 = x109 + x110;
auto x112 = x81*x92;
auto x113 = x28*(V{3}*cell[12] - V{3}*cell[3] - x106 + x107 + x108 - x95 + x97 + x99);
auto x114 = x110 + x113;
auto x115 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[10] + V{0.0277777777777778}*cell[11] + V{0.0277777777777778}*cell[12] + V{0.0277777777777778}*cell[13] + V{0.0277777777777778}*cell[14] + V{0.0277777777777778}*cell[15] + V{0.0277777777777778}*cell[16] + V{0.0277777777777778}*cell[17] + V{0.0277777777777778}*cell[18] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778}*cell[9] + V{0.0277777777777778};
auto x116 = V{4.5}*x84;
auto x117 = cell[10] + cell[16] + x42;
auto x118 = x116*((2*cell[13] - 2*cell[4] + x117 + x21 + x33)*(2*cell[13] - 2*cell[4] + x117 + x21 + x33));
auto x119 = -cell[11] + V{2}*cell[14] + cell[15] - V{2}*cell[5] + x117 + x25 + x46 + x54;
auto x120 = -x100 + x90;
auto x121 = cell[10] + cell[14] + x40 + x43;
auto x122 = x116*((cell[12] + 2*cell[15] - 2*cell[6] + x121 + x29 + x49)*(cell[12] + 2*cell[15] - 2*cell[6] + x121 + x29 + x49));
auto x123 = -cell[12] + x26;
auto x124 = V{2}*cell[16] - V{2}*cell[7] + cell[8] + x121 + x123 + x32 + x55;
auto x125 = cell[11] + x31 + x36;
auto x126 = x116*((cell[12] + 2*cell[17] - 2*cell[8] + x125 + x38 + x47 + x51)*(cell[12] + 2*cell[17] - 2*cell[8] + x125 + x38 + x47 + x51));
auto x127 = V{2}*cell[18] + cell[6] - V{2}*cell[9] + x123 + x125 + x41 + x53;
auto x128 = -x109 + x90;
auto x129 = x86 + V{-1};
auto x130 = x100 + x90;
auto x131 = -x113;
auto x132 = x109 + x90;
auto x0 = V{1}*cell[0]*x83 - x82*(x90*(x56 + x57 + x58 + x59 + x60 + x63 + x64 + x66 + x67 + x69 + x70 + x71 + x72 + x74 + x75 + x77 + x78 + x79 + x80 + V{0.333333333333333}) + V{0.333333333333333});
auto x1 = V{1}*cell[10]*x83 + x82*(x91*(x104 + x93) + V{-0.0555555555555556});
auto x2 = V{1}*cell[11]*x83 + x82*(x91*(x102 + x105 + x111) + V{-0.0555555555555556});
auto x3 = V{1}*cell[12]*x83 + x82*(x91*(x101 + x112 + x114 + V{1}) + V{-0.0555555555555556});
auto x4 = V{1}*cell[13]*x83 + x82*(x115*(x104 + x111 + x118) + V{-0.0277777777777778});
auto x5 = V{1}*cell[14]*x83 - x82*(x115*(x109 - x116*((x119)*(x119)) + x120) + V{0.0277777777777778});
auto x6 = V{1}*cell[15]*x83 + x82*(x115*(x104 + x114 + x122) + V{-0.0277777777777778});
auto x7 = V{1}*cell[16]*x83 - x82*(x115*(x113 - x116*((x124)*(x124)) + x120) + V{0.0277777777777778});
auto x8 = V{1}*cell[17]*x83 + x82*(x115*(x103 + x111 + x113 + x126) + V{-0.0277777777777778});
auto x9 = V{1}*cell[18]*x83 - x82*(x115*(x113 - x116*((x127)*(x127)) + x128) + V{0.0277777777777778});
auto x10 = V{1}*cell[1]*x83 - x82*(x91*(x100 + x89 - x93) + V{0.0555555555555556});
auto x11 = V{1}*cell[2]*x83 - x82*(x91*(-x105 + x109 + x129 + x88) + V{0.0555555555555556});
auto x12 = V{1}*cell[3]*x83 - x82*(x91*(-x112 + x113 + x129 + x87) + V{0.0555555555555556});
auto x13 = V{1}*cell[4]*x83 - x82*(x115*(x109 - x118 + x130) + V{0.0277777777777778});
auto x14 = V{1}*cell[5]*x83 - x82*(x115*(x100 - x116*((x119)*(x119)) + x128) + V{0.0277777777777778});
auto x15 = V{1}*cell[6]*x83 - x82*(x115*(x113 - x122 + x130) + V{0.0277777777777778});
auto x16 = V{1}*cell[7]*x83 - x82*(x115*(-x116*((x124)*(x124)) + x130 + x131) + V{0.0277777777777778});
auto x17 = V{1}*cell[8]*x83 - x82*(x115*(x113 - x126 + x132) + V{0.0277777777777778});
auto x18 = V{1}*cell[9]*x83 - x82*(x115*(-x116*((x127)*(x127)) + x131 + x132) + V{0.0277777777777778});
cell[0] = x0;
cell[10] = x1;
cell[11] = x2;
cell[12] = x3;
cell[13] = x4;
cell[14] = x5;
cell[15] = x6;
cell[16] = x7;
cell[17] = x8;
cell[18] = x9;
cell[1] = x10;
cell[2] = x11;
cell[3] = x12;
cell[4] = x13;
cell[5] = x14;
cell[6] = x15;
cell[7] = x16;
cell[8] = x17;
cell[9] = x18;
return { x27, V{1}*x84*(x62 + x73 + x81) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
