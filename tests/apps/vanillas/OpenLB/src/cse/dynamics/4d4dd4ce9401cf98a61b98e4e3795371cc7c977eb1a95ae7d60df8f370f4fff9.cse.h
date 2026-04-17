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
struct CSE<SpongeLayerDynamics<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x23 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x22 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x24 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::descriptors::DENSITY>(0);
auto x19 = cell.template getFieldComponent<olb::descriptors::DAMPING>(0);
auto x25 = cell[10] + cell[14];
auto x26 = cell[12] + cell[7];
auto x27 = cell[0] + cell[11] + cell[13] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + cell[9] + x25 + x26;
auto x28 = x27 + V{1};
auto x29 = V{1} / ((x28)*(x28));
auto x30 = V{1.5}*x29;
auto x31 = -cell[4];
auto x32 = cell[13] + x31;
auto x33 = -cell[6];
auto x34 = cell[15] + x33;
auto x35 = x32 + x34;
auto x36 = -cell[1];
auto x37 = -cell[7];
auto x38 = cell[16] + x37;
auto x39 = x36 + x38;
auto x40 = -cell[5];
auto x41 = x25 + x40;
auto x42 = ((x35 + x39 + x41)*(x35 + x39 + x41));
auto x43 = x30*x42;
auto x44 = -cell[8];
auto x45 = cell[17] + x44;
auto x46 = x32 + x45;
auto x47 = -cell[9];
auto x48 = cell[18] + x47;
auto x49 = -cell[2];
auto x50 = -cell[14];
auto x51 = cell[11] + cell[5] + x49 + x50;
auto x52 = ((x46 + x48 + x51)*(x46 + x48 + x51));
auto x53 = x30*x52;
auto x54 = x34 + x45;
auto x55 = -cell[3];
auto x56 = -cell[18];
auto x57 = cell[9] + x56;
auto x58 = x55 + x57;
auto x59 = -cell[16];
auto x60 = x26 + x59;
auto x61 = ((x54 + x58 + x60)*(x54 + x58 + x60));
auto x62 = x30*x61;
auto x63 = x53 + x62 + V{-1};
auto x64 = x43 + x63;
auto x65 = ((x21)*(x21));
auto x66 = V{1.5}*x65;
auto x67 = ((x22)*(x22));
auto x68 = V{1.5}*x67;
auto x69 = ((x23)*(x23));
auto x70 = V{1.5}*x69;
auto x71 = x68 + x70 + V{-1};
auto x72 = x66 + x71;
auto x73 = x27 + V{1};
auto x74 = V{0.0555555555555556}*cell[0] + V{0.0555555555555556}*cell[10] + V{0.0555555555555556}*cell[11] + V{0.0555555555555556}*cell[12] + V{0.0555555555555556}*cell[13] + V{0.0555555555555556}*cell[14] + V{0.0555555555555556}*cell[15] + V{0.0555555555555556}*cell[16] + V{0.0555555555555556}*cell[17] + V{0.0555555555555556}*cell[18] + V{0.0555555555555556}*cell[1] + V{0.0555555555555556}*cell[2] + V{0.0555555555555556}*cell[3] + V{0.0555555555555556}*cell[4] + V{0.0555555555555556}*cell[5] + V{0.0555555555555556}*cell[6] + V{0.0555555555555556}*cell[7] + V{0.0555555555555556}*cell[8] + V{0.0555555555555556}*cell[9] + V{0.0555555555555556};
auto x75 = V{1} / (x28);
auto x76 = V{3}*cell[14];
auto x77 = V{3}*cell[16];
auto x78 = V{3}*cell[5];
auto x79 = V{3}*cell[7];
auto x80 = V{3}*cell[13] - V{3}*cell[4];
auto x81 = V{3}*cell[15] - V{3}*cell[6];
auto x82 = x75*(V{3}*cell[10] - V{3}*cell[1] + x76 + x77 - x78 - x79 + x80 + x81);
auto x83 = V{3}*x29;
auto x84 = x42*x83;
auto x85 = x63 + x82 - x84;
auto x86 = V{0.0555555555555556}*x19;
auto x87 = V{3}*x21;
auto x88 = V{3}*x65;
auto x89 = V{3}*cell[18];
auto x90 = V{3}*cell[9];
auto x91 = V{3}*cell[17] - V{3}*cell[8];
auto x92 = x75*(V{3}*cell[11] - V{3}*cell[2] - x76 + x78 + x80 + x89 - x90 + x91);
auto x93 = x52*x83;
auto x94 = x43 + V{-1};
auto x95 = x62 + x92 - x93 + x94;
auto x96 = V{3}*x22;
auto x97 = V{3}*x67;
auto x98 = x66 + V{-1};
auto x99 = x75*(V{3}*cell[12] - V{3}*cell[3] - x77 + x79 + x81 - x89 + x90 + x91);
auto x100 = x61*x83;
auto x101 = -x100 + x53 + x94 + x99;
auto x102 = V{3}*x23;
auto x103 = V{3}*x69;
auto x104 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[10] + V{0.0277777777777778}*cell[11] + V{0.0277777777777778}*cell[12] + V{0.0277777777777778}*cell[13] + V{0.0277777777777778}*cell[14] + V{0.0277777777777778}*cell[15] + V{0.0277777777777778}*cell[16] + V{0.0277777777777778}*cell[17] + V{0.0277777777777778}*cell[18] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778}*cell[9] + V{0.0277777777777778};
auto x105 = V{4.5}*x29;
auto x106 = cell[10] + x39;
auto x107 = x105*((cell[11] + 2*cell[13] - 2*cell[4] + x106 + x48 + x49 + x54)*(cell[11] + 2*cell[13] - 2*cell[4] + x106 + x48 + x49 + x54));
auto x108 = x64 + x82;
auto x109 = -x107 + x108 + x92;
auto x110 = V{0.0277777777777778}*x19;
auto x111 = V{4.5}*((x21 + x22)*(x21 + x22));
auto x112 = x72 + x87;
auto x113 = -x92;
auto x114 = -cell[17] + cell[8];
auto x115 = -cell[11] + V{2}*cell[14] + cell[2] - V{2}*cell[5] + x106 + x114 + x34 + x57;
auto x116 = -x105*((x115)*(x115)) + x108 + x113;
auto x117 = -x96;
auto x118 = x21 - x22;
auto x119 = x36 + x41;
auto x120 = x105*((cell[12] + 2*cell[15] - 2*cell[6] + x119 + x46 + x58)*(cell[12] + 2*cell[15] - 2*cell[6] + x119 + x46 + x58));
auto x121 = x108 - x120 + x99;
auto x122 = V{4.5}*((x21 + x23)*(x21 + x23));
auto x123 = -x99;
auto x124 = -cell[12] + cell[3] + x32;
auto x125 = V{2}*cell[16] - V{2}*cell[7] + x114 + x119 + x124 + x48;
auto x126 = -x105*((x125)*(x125)) + x108 + x123;
auto x127 = -x102;
auto x128 = -x23;
auto x129 = x128 + x21;
auto x130 = x105*((2*cell[17] - 2*cell[8] + x35 + x51 + x55 + x60)*(2*cell[17] - 2*cell[8] + x35 + x51 + x55 + x60));
auto x131 = x64 + x92;
auto x132 = -x130 + x131 + x99;
auto x133 = V{4.5}*((x22 + x23)*(x22 + x23));
auto x134 = x72 + x96;
auto x135 = -cell[15] + V{2}*cell[18] + cell[6] - V{2}*cell[9] + x124 + x38 + x51;
auto x136 = -x105*((x135)*(x135)) + x123 + x131;
auto x137 = x128 + x22;
auto x138 = -x53;
auto x139 = V{1} - x62;
auto x140 = x138 + x139;
auto x141 = x140 + x82;
auto x142 = x141 + x84;
auto x143 = -x68;
auto x144 = V{1} - x70;
auto x145 = x143 + x144;
auto x146 = x145 + x87;
auto x147 = -x43;
auto x148 = x147 + x92;
auto x149 = x139 + x148 + x93;
auto x150 = -x66;
auto x151 = x150 + x96;
auto x152 = x147 + x99;
auto x153 = x100 + x138 + x152 + V{1};
auto x154 = x102 + x150;
auto x155 = x107 + x141 + x148;
auto x156 = -x82;
auto x157 = -x105*((x115)*(x115)) + x131 + x156;
auto x158 = -x87;
auto x159 = x120 + x141 + x152;
auto x160 = x64 + x99;
auto x161 = -x105*((x125)*(x125)) + x156 + x160;
auto x162 = x102 + x72;
auto x163 = x130 + x140 + x148 + x99;
auto x164 = -x105*((x135)*(x135)) + x113 + x160;
auto x0 = cell[0] - V{0.333333333333333}*x19*(x20*x72 - x64*x73) - x24*(cell[0] + x64*(V{0.333333333333333}*cell[0] + V{0.333333333333333}*cell[10] + V{0.333333333333333}*cell[11] + V{0.333333333333333}*cell[12] + V{0.333333333333333}*cell[13] + V{0.333333333333333}*cell[14] + V{0.333333333333333}*cell[15] + V{0.333333333333333}*cell[16] + V{0.333333333333333}*cell[17] + V{0.333333333333333}*cell[18] + V{0.333333333333333}*cell[1] + V{0.333333333333333}*cell[2] + V{0.333333333333333}*cell[3] + V{0.333333333333333}*cell[4] + V{0.333333333333333}*cell[5] + V{0.333333333333333}*cell[6] + V{0.333333333333333}*cell[7] + V{0.333333333333333}*cell[8] + V{0.333333333333333}*cell[9] + V{0.333333333333333}) + V{0.333333333333333});
auto x1 = -x24*(cell[1] + x74*x85 + V{0.0555555555555556}) - x36 - x86*(x20*(x71 + x87 - x88) - x73*x85);
auto x2 = -x24*(cell[2] + x74*x95 + V{0.0555555555555556}) - x49 - x86*(x20*(x70 + x96 - x97 + x98) - x73*x95);
auto x3 = -x24*(cell[3] + x101*x74 + V{0.0555555555555556}) - x55 - x86*(-x101*x73 + x20*(x102 - x103 + x68 + x98));
auto x4 = -x110*(-x109*x73 + x20*(-x111 + x112 + x96)) - x24*(cell[4] + x104*x109 + V{0.0277777777777778}) - x31;
auto x5 = -(x110*(-x116*x73 + x20*(x112 + x117 - V{4.5}*((x118)*(x118)))) + x24*(cell[5] + x104*x116 + V{0.0277777777777778}) + x40);
auto x6 = -x110*(-x121*x73 + x20*(x102 + x112 - x122)) - x24*(cell[6] + x104*x121 + V{0.0277777777777778}) - x33;
auto x7 = -(x110*(-x126*x73 + x20*(x112 + x127 - V{4.5}*((x129)*(x129)))) + x24*(cell[7] + x104*x126 + V{0.0277777777777778}) + x37);
auto x8 = -x110*(-x132*x73 + x20*(x102 - x133 + x134)) - x24*(cell[8] + x104*x132 + V{0.0277777777777778}) - x44;
auto x9 = -(x110*(-x136*x73 + x20*(x127 + x134 - V{4.5}*((x137)*(x137)))) + x24*(cell[9] + x104*x136 + V{0.0277777777777778}) + x47);
auto x10 = cell[10] - x24*(cell[10] - x142*x74 + V{0.0555555555555556}) + x86*(-x142*x73 + x20*(x146 + x88));
auto x11 = cell[11] - x24*(cell[11] - x149*x74 + V{0.0555555555555556}) + x86*(-x149*x73 + x20*(x144 + x151 + x97));
auto x12 = cell[12] - x24*(cell[12] - x153*x74 + V{0.0555555555555556}) + x86*(-x153*x73 + x20*(x103 + x143 + x154 + V{1}));
auto x13 = cell[13] + x110*(-x155*x73 + x20*(x111 + x146 + x151)) - x24*(cell[13] - x104*x155 + V{0.0277777777777778});
auto x14 = -(x110*(-x157*x73 + x20*(x134 + x158 - V{4.5}*((x118)*(x118)))) + x24*(cell[14] + x104*x157 + V{0.0277777777777778}) + x50);
auto x15 = cell[15] + x110*(-x159*x73 + x20*(x122 + x146 + x154)) - x24*(cell[15] - x104*x159 + V{0.0277777777777778});
auto x16 = -(x110*(-x161*x73 + x20*(x158 + x162 - V{4.5}*((x129)*(x129)))) + x24*(cell[16] + x104*x161 + V{0.0277777777777778}) + x59);
auto x17 = cell[17] + x110*(-x163*x73 + x20*(x102 + x133 + x145 + x151)) - x24*(cell[17] - x104*x163 + V{0.0277777777777778});
auto x18 = -(x110*(-x164*x73 + x20*(x117 + x162 - V{4.5}*((x137)*(x137)))) + x24*(cell[18] + x104*x164 + V{0.0277777777777778}) + x56);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
cell[9] = x9;
cell[10] = x10;
cell[11] = x11;
cell[12] = x12;
cell[13] = x13;
cell[14] = x14;
cell[15] = x15;
cell[16] = x16;
cell[17] = x17;
cell[18] = x18;
return { x28, V{1}*x29*(x42 + x52 + x61) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
