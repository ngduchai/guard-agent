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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::FixedVelocityMomentum, momenta::BulkStress, momenta::DefineUSeparately>, equilibria::SecondOrder, collision::BGK, forcing::MCGuo<momenta::Identity> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x20 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::FORCE>(2);
auto x23 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x25 = parameters.template get<descriptors::OMEGA>();
auto x24 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x22 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x26 = x25 + V{-1};
auto x27 = cell[0] + cell[10] + cell[11] + cell[12] + cell[13] + cell[14] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8] + cell[9];
auto x28 = x27 + V{1};
auto x29 = ((x22)*(x22));
auto x30 = V{1.5}*x29;
auto x31 = ((x23)*(x23));
auto x32 = V{1.5}*x31;
auto x33 = ((x24)*(x24));
auto x34 = V{1.5}*x33;
auto x35 = x32 + x34 + V{-1};
auto x36 = x30 + x35;
auto x37 = V{0.5}*x25 + V{-1};
auto x38 = x19*x22;
auto x39 = x20*x23;
auto x40 = x21*x24;
auto x41 = x27 + V{1};
auto x42 = V{0.0555555555555556}*x25;
auto x43 = V{3}*x22;
auto x44 = V{3}*x29;
auto x45 = V{6}*x22;
auto x46 = x45 + V{-3};
auto x47 = V{3}*x39;
auto x48 = V{3}*x40;
auto x49 = x47 + x48;
auto x50 = V{3}*x23;
auto x51 = V{3}*x31;
auto x52 = x30 + V{-1};
auto x53 = V{6}*x23;
auto x54 = x53 + V{-3};
auto x55 = V{3}*x38;
auto x56 = x48 + x55;
auto x57 = V{3}*x24;
auto x58 = V{3}*x33;
auto x59 = V{6}*x24;
auto x60 = x59 + V{-3};
auto x61 = x47 + x55;
auto x62 = V{0.0277777777777778}*x25;
auto x63 = V{4.5}*((x22 + x23)*(x22 + x23));
auto x64 = x36 + x43;
auto x65 = V{9}*x23;
auto x66 = V{9}*x22;
auto x67 = -x48;
auto x68 = x37*x41;
auto x69 = V{0.0277777777777778}*x68;
auto x70 = -x50;
auto x71 = x22 - x23;
auto x72 = V{3} - x45;
auto x73 = -x66;
auto x74 = x53 + V{3};
auto x75 = V{4.5}*((x22 + x24)*(x22 + x24));
auto x76 = V{9}*x24;
auto x77 = -x47;
auto x78 = -x57;
auto x79 = -x24;
auto x80 = x22 + x79;
auto x81 = x59 + V{3};
auto x82 = V{4.5}*((x23 + x24)*(x23 + x24));
auto x83 = x36 + x50;
auto x84 = -x55;
auto x85 = x23 + x79;
auto x86 = V{3} - x53;
auto x87 = -x65;
auto x88 = -x32;
auto x89 = V{1} - x34;
auto x90 = x88 + x89;
auto x91 = x43 + x90;
auto x92 = x45 + V{3};
auto x93 = V{0.0555555555555556}*x68;
auto x94 = -x30;
auto x95 = x50 + x94;
auto x96 = x57 + x94;
auto x97 = -x43;
auto x98 = x36 + x57;
auto x99 = V{3} - x59;
auto x100 = -x76;
auto x0 = -cell[0]*x26 - V{0.333333333333333}*x25*(x28*x36 + V{1}) + V{1}*x37*x41*(x38 + x39 + x40);
auto x1 = -cell[1]*x26 + V{0.0555555555555556}*x37*x41*(-x19*x46 + x49) - x42*(x28*(x35 + x43 - x44) + V{1});
auto x2 = -cell[2]*x26 + V{0.0555555555555556}*x37*x41*(-x20*x54 + x56) - x42*(x28*(x34 + x50 - x51 + x52) + V{1});
auto x3 = -cell[3]*x26 + V{0.0555555555555556}*x37*x41*(-x21*x60 + x61) - x42*(x28*(x32 + x52 + x57 - x58) + V{1});
auto x4 = -cell[4]*x26 - x62*(x28*(x50 - x63 + x64) + V{1}) - x69*(x19*(x46 + x65) + x20*(x54 + x66) + x67);
auto x5 = -(cell[5]*x26 + x62*(x28*(x64 + x70 - V{4.5}*((x71)*(x71))) + V{1}) + x69*(-x19*(x65 + x72) + x20*(x73 + x74) - x48));
auto x6 = -cell[6]*x26 - x62*(x28*(x57 + x64 - x75) + V{1}) - x69*(x19*(x46 + x76) + x21*(x60 + x66) + x77);
auto x7 = -(cell[7]*x26 + x62*(x28*(x64 + x78 - V{4.5}*((x80)*(x80))) + V{1}) + x69*(-x19*(x72 + x76) + x21*(x73 + x81) - x47));
auto x8 = -cell[8]*x26 - x62*(x28*(x57 - x82 + x83) + V{1}) - x69*(x20*(x54 + x76) + x21*(x60 + x65) + x84);
auto x9 = -(cell[9]*x26 + x62*(x28*(x78 + x83 - V{4.5}*((x85)*(x85))) + V{1}) + x69*(-x20*(x76 + x86) + x21*(x81 + x87) - x55));
auto x10 = -cell[10]*x26 + x42*(x28*(x44 + x91) + V{-1}) + x93*(-x19*x92 + x49);
auto x11 = -cell[11]*x26 + x42*(x28*(x51 + x89 + x95) + V{-1}) + x93*(-x20*x74 + x56);
auto x12 = -cell[12]*x26 + x42*(x28*(x58 + x88 + x96 + V{1}) + V{-1}) + x93*(-x21*x81 + x61);
auto x13 = -cell[13]*x26 + V{0.0277777777777778}*x25*(x28*(x63 + x91 + x95) + V{-1}) - x69*(x19*(x65 + x92) + x20*(x66 + x74) + x67);
auto x14 = -(cell[14]*x26 + x62*(x28*(x83 + x97 - V{4.5}*((x71)*(x71))) + V{1}) + x69*(x19*(x87 + x92) - x20*(x66 + x86) - x48));
auto x15 = -cell[15]*x26 + V{0.0277777777777778}*x25*(x28*(x75 + x91 + x96) + V{-1}) - x69*(x19*(x76 + x92) + x21*(x66 + x81) + x77);
auto x16 = -(cell[16]*x26 + x62*(x28*(x97 + x98 - V{4.5}*((x80)*(x80))) + V{1}) + x69*(x19*(x100 + x92) - x21*(x66 + x99) - x47));
auto x17 = -cell[17]*x26 + V{0.0277777777777778}*x25*(x28*(x57 + x82 + x90 + x95) + V{-1}) - x69*(x20*(x74 + x76) + x21*(x65 + x81) + x84);
auto x18 = -(cell[18]*x26 + x62*(x28*(x70 + x98 - V{4.5}*((x85)*(x85))) + V{1}) + x69*(x20*(x100 + x74) - x21*(x65 + x99) - x55));
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
return { x41, x29 + x31 + x33 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
