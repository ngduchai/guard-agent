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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::MovingPorousMomentumCombinationNoWM<momenta::BulkMomentum>, momenta::BulkStress, momenta::DefineToNEq>, equilibria::ThirdOrder, collision::SmagorinskyEffectiveOmega<collision::ThirdOrderRLB> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x13 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x12 = parameters.template get<descriptors::OMEGA>();
auto x11 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x10 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x9 = cell.template getFieldComponent<olb::descriptors::POROSITY>(0);
auto x14 = V{0.5}/x12;
auto x15 = V{0.0277777691819762}/((x12)*(x12));
auto x16 = cell[1] + cell[7] + cell[8];
auto x17 = cell[0] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + x16;
auto x18 = x17 + V{1};
auto x19 = V{1} / (x18);
auto x20 = ((x13)*(x13));
auto x21 = x9 + V{-1};
auto x22 = x10*x21;
auto x23 = cell[1] - cell[7];
auto x24 = -cell[5];
auto x25 = cell[3] + x24;
auto x26 = cell[2] - cell[6] + x23 + x25;
auto x27 = x19*x9;
auto x28 = x26*x27;
auto x29 = x22 + V{1}*x28;
auto x30 = ((x29)*(x29));
auto x31 = -V{0.333333333333333}*cell[0] + V{0.666666666666667}*cell[1] + V{0.666666666666667}*cell[3] + V{0.666666666666667}*cell[5] + V{0.666666666666667}*cell[7];
auto x32 = V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[4] + V{0.666666666666667}*cell[6] - V{0.333333333333333}*cell[8] + x31;
auto x33 = -x18*x30 + x32;
auto x34 = V{0.5}*((x33)*(x33));
auto x35 = x11*x21;
auto x36 = -cell[3];
auto x37 = -cell[4] + x16 + x24 + x36;
auto x38 = -V{1}*x19*x37*x9 + x35;
auto x39 = -x38;
auto x40 = ((x39)*(x39));
auto x41 = -V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[4] - V{0.333333333333333}*cell[6] + V{0.666666666666667}*cell[8] + x31;
auto x42 = -x18*x40 + x41;
auto x43 = -x21;
auto x44 = x10*x43;
auto x45 = -x26;
auto x46 = x27*x45;
auto x47 = x44 + V{1}*x46;
auto x48 = x11*x43;
auto x49 = x27*x37;
auto x50 = x48 + V{1}*x49;
auto x51 = x18*x47*x50;
auto x52 = V{1}*cell[1];
auto x53 = V{1}*cell[5];
auto x54 = V{1}*cell[3];
auto x55 = V{1}*cell[7];
auto x56 = x51 + x52 + x53 - x54 - x55;
auto x57 = V{1} - V{1} / (x14 + V{3.00000046417339}*util::sqrt(x15 + x19*x20*util::sqrt(x34 + x56*(cell[5] + x23 + x36 + x51) + V{0.5}*((x42)*(x42)))));
auto x58 = V{0.444444444444444}*cell[0];
auto x59 = V{0.666666666666667}*cell[0] + V{0.666666666666667}*cell[1] + V{0.666666666666667}*cell[2] + V{0.666666666666667}*cell[3] + V{0.666666666666667}*cell[4] + V{0.666666666666667}*cell[5] + V{0.666666666666667}*cell[6] + V{0.666666666666667}*cell[7] + V{0.666666666666667}*cell[8] + V{0.666666666666667};
auto x60 = ((x47)*(x47));
auto x61 = ((x50)*(x50));
auto x62 = V{1.5}*x60 + V{1.5}*x61 + V{-1};
auto x63 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x64 = -x49;
auto x65 = x44 + x46;
auto x66 = V{3}*x48;
auto x67 = V{6.000012}*x19*x37*x9;
auto x68 = V{3}*x49;
auto x69 = -x68;
auto x70 = V{3}*x44 + V{3}*x46 + x62;
auto x71 = V{0.166667}*x10*x21 + V{0.166667}*x19*x26*x9;
auto x72 = x22 + x28;
auto x73 = V{0.333334}*x56;
auto x74 = x35 + x64;
auto x75 = -x74;
auto x76 = x18*x29;
auto x77 = x39*x76;
auto x78 = V{0.25}*x77;
auto x79 = V{0.0277777777777778}*cell[2];
auto x80 = V{0.0277777777777778}*cell[4];
auto x81 = V{0.0277777777777778}*cell[6];
auto x82 = V{0.0277777777777778}*cell[8];
auto x83 = V{0.0555555555555556}*cell[0];
auto x84 = -x83;
auto x85 = V{0.0833333333333333}*cell[0] + V{0.0833333333333333}*cell[1] + V{0.0833333333333333}*cell[2] + V{0.0833333333333333}*cell[3] + V{0.0833333333333333}*cell[4] + V{0.0833333333333333}*cell[5] + V{0.0833333333333333}*cell[6] + V{0.0833333333333333}*cell[7] + V{0.0833333333333333}*cell[8] + V{0.0833333333333333};
auto x86 = -x30*x85;
auto x87 = -x40*x85 + x79 + x80 + x81 + x82 + x84 + x86;
auto x88 = V{0.361111111111111}*cell[1] - V{0.138888888888889}*cell[3] + V{0.361111111111111}*cell[5] - V{0.138888888888889}*cell[7];
auto x89 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x90 = V{2.999997}*x19*x37*x9;
auto x91 = V{0.277777777777778}*cell[2];
auto x92 = V{0.277777777777778}*cell[6];
auto x93 = V{0.222222222222222}*cell[4];
auto x94 = V{0.222222222222222}*cell[8];
auto x95 = V{0.333333}*x19*x37*x9;
auto x96 = x56*x72;
auto x97 = V{0.166666666666667}*cell[0] + V{0.166666666666667}*cell[1] + V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[3] + V{0.166666666666667}*cell[4] + V{0.166666666666667}*cell[5] + V{0.166666666666667}*cell[6] + V{0.166666666666667}*cell[7] + V{0.166666666666667}*cell[8] + V{0.166666666666667};
auto x98 = x56*x75;
auto x99 = V{0.333333333333333}*cell[0] + V{0.333333333333333}*cell[1] + V{0.333333333333333}*cell[2] + V{0.333333333333333}*cell[3] + V{0.333333333333333}*cell[4] + V{0.333333333333333}*cell[5] + V{0.333333333333333}*cell[6] + V{0.333333333333333}*cell[7] + V{0.333333333333333}*cell[8] + V{0.333333333333333};
auto x100 = V{0.111111111111111}*cell[1];
auto x101 = V{0.111111111111111}*cell[3];
auto x102 = V{0.111111111111111}*cell[5];
auto x103 = V{0.111111111111111}*cell[7];
auto x104 = V{0.0555555555555556}*cell[0];
auto x105 = x100 + x101 + x102 + x103 - x104;
auto x106 = V{0.361111111111111}*cell[3];
auto x107 = V{0.361111111111111}*cell[7];
auto x108 = -x18*x61 + x41;
auto x109 = V{0.5}*x19*x37*x9;
auto x110 = -x18*x60 + x32;
auto x111 = -x56;
auto x112 = V{1}*x111;
auto x113 = x48 + x49;
auto x114 = V{18}*x19*x37*x9;
auto x115 = x66 + x68;
auto x116 = V{6.000003}*x19*x37*x9;
auto x117 = V{0.277777777777778}*cell[4];
auto x118 = V{0.277777777777778}*cell[8];
auto x119 = V{0.222222222222222}*cell[2];
auto x120 = V{0.222222222222222}*cell[6];
auto x121 = V{0.666667}*x19*x37*x9;
auto x122 = V{1.5}*x30;
auto x123 = V{1.5}*x40;
auto x124 = x122 + x123 + V{3}*x22 + V{3}*x28 + V{-1};
auto x125 = V{3}*x35;
auto x126 = -x125 + x68;
auto x127 = ((x38)*(x38));
auto x128 = -x127*x18 + x41;
auto x129 = x52 + x53 - x54 - x55 - x77;
auto x130 = V{1} - V{1} / (x14 + V{3.00000046417339}*util::sqrt(x15 + x19*x20*util::sqrt(x129*(cell[1] - cell[7] - x25 - x77) + x34 + V{0.5}*((x128)*(x128)))));
auto x131 = V{0.333334}*x129;
auto x132 = V{1.333334}*x111;
auto x133 = V{0.666666}*x111;
auto x134 = -x100 - x101 - x102 - x103 + x104;
auto x135 = x17 + V{1};
auto x0 = -V{1}*x57*(V{0.888888888888889}*cell[1] + V{0.222222222222222}*cell[2] + V{0.888888888888889}*cell[3] + V{0.222222222222222}*cell[4] + V{0.888888888888889}*cell[5] + V{0.222222222222222}*cell[6] + V{0.888888888888889}*cell[7] + V{0.222222222222222}*cell[8] - x58 - x59*x60 - x59*x61) - x62*(V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + x58 + V{0.444444444444444}) + V{-0.444444444444444};
auto x1 = -(-V{1}*x57*(x33*(-V{0.166667}*x11*x21 + V{0.166667}*x19*x37*x9) + x42*x71 + x72*x73 + x73*x75 - x78 + x87 + x88) + x63*(-x60*(V{6.000012}*x11*x43 + x67) + x61*(V{6.000012}*x10*x43 + V{6.000012}*x19*x45*x9) - x66 + x69 + x70 - V{4.5}*((x11*x43 - x64 - x65)*(x11*x43 - x64 - x65))) + V{0.0277777777777778});
auto x2 = -(-V{1}*x57*(x105 - x30*x99 + x33*(-V{0.333333}*x11*x21 + x95) + x40*x97 - x42*(V{0.666667}*x10*x21 + V{0.666667}*x19*x26*x9) + x91 + x92 - x93 - x94 + V{0.666666}*x96 - V{1.333334}*x98) + x89*(-x60*(V{2.999997}*x11*x43 + x90) - x61*(V{6.000003}*x10*x43 + V{6.000003}*x19*x45*x9) + x70 - V{4.5}*((x65)*(x65))) + V{0.111111111111111});
auto x3 = -(V{1}*x57*(V{0.138888888888889}*cell[1] + V{0.138888888888889}*cell[5] - x106 - x107 + x108*(V{0.5}*x10*x43 + V{0.5}*x19*x45*x9) + x110*(x109 + V{0.5}*x11*x43) + x112*x113 + x112*x65 + V{0.25}*x51 + x60*x85 + x61*x85 - x79 - x80 - x81 - x82 + x83) + x63*(x115 + x60*(V{18}*x11*x43 + x114) + x61*(V{18}*x10*x43 + V{18}*x19*x45*x9) + x70 - V{4.5}*((x113 + x65)*(x113 + x65))) + V{0.0277777777777778});
auto x4 = -(-V{1}*x57*(x105 + x117 + x118 - x119 - x120 + x30*x97 + x33*(-V{0.666667}*x11*x21 + x121) - x40*x99 - x42*(V{0.333333}*x10*x21 + V{0.333333}*x19*x26*x9) + V{1.333334}*x96 - V{0.666666}*x98) + x89*(x115 - x60*(V{6.000003}*x11*x43 + x116) - x61*(V{2.999997}*x10*x43 + V{2.999997}*x19*x45*x9) + x62 - V{4.5}*((x113)*(x113))) + V{0.111111111111111});
auto x5 = -(-V{1}*x130*(-x127*x85 - x128*x71 - x131*x72 + x131*x74 + x33*(V{0.166667}*x11*x21 - V{0.166667}*x19*x37*x9) + V{0.25}*x38*x76 + x79 + x80 + x81 + x82 + x84 + x86 + x88) + x63*(x124 + x126 + x30*(-V{6.000012}*x11*x21 + x67) + x40*(V{6.000012}*x10*x21 + V{6.000012}*x19*x26*x9) - V{4.5}*((x35 - x49 - x72)*(x35 - x49 - x72))) + V{0.0277777777777778});
auto x6 = -(V{0.111111111111111}*x135*(x124 - V{6.000003}*x29*x40 + x30*(-V{2.999997}*x11*x21 + x90) - V{4.5}*((x72)*(x72))) + V{1}*x57*(x108*(V{0.666667}*x10*x43 + V{0.666667}*x19*x45*x9) + x110*(V{0.333333}*x11*x43 + x95) + x113*x132 + x133*x65 + x134 + x60*x99 - x61*x97 - x91 - x92 + x93 + x94) + V{0.111111111111111});
auto x7 = -(V{1}*x130*(V{0.138888888888889}*cell[1] + V{0.138888888888889}*cell[5] - x106 - x107 + V{0.5}*x29*x42 - x33*(x109 - V{0.5}*x11*x21) + V{1}*x56*x75 - x78 - x87 - V{1}*x96) + x63*(x124 + x125 - x30*(-V{18}*x11*x21 + x114) + x40*(V{18}*x10*x21 + V{18}*x19*x26*x9) + x69 - V{4.5}*((-x72 - x74)*(-x72 - x74))) + V{0.0277777777777778});
auto x8 = -(-V{0.111111111111111}*x135*(-x122 - x123 + x126 - x30*(-V{6.000003}*x11*x21 + x116) + x40*(V{2.999997}*x10*x21 + V{2.999997}*x19*x26*x9) + V{1} + V{4.5}*((x75)*(x75))) + V{1}*x57*(x108*(V{0.333333}*x10*x43 + V{0.333333}*x19*x45*x9) + x110*(V{0.666667}*x11*x43 + x121) + x113*x133 - x117 - x118 + x119 + x120 + x132*x65 + x134 - x60*x97 + x61*x99) + V{0.111111111111111});
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x18, x127 + x30 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
