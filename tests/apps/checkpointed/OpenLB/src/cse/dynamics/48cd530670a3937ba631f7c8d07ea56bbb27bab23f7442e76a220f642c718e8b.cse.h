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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::OmegaFromCellTauEff<collision::BGK>, forcing::Guo<momenta::Forced> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x11 = cell.template getFieldComponent<olb::descriptors::TAU_EFF>(0);
auto x12 = V{1} / (x11);
auto x13 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8] + V{1};
auto x14 = V{1} / (x13);
auto x15 = V{1}*cell[7];
auto x16 = V{1}*cell[8];
auto x17 = V{1}*cell[3];
auto x18 = V{1}*cell[4];
auto x19 = V{1}*cell[1];
auto x20 = -V{1}*cell[5] + x19;
auto x21 = V{0.5}*x10 + x14*(x15 + x16 - x17 - x18 + x20);
auto x22 = ((x21)*(x21));
auto x23 = V{1.5}*x22;
auto x24 = V{0.5}*x9;
auto x25 = V{1}*cell[2] - V{1}*cell[6] - V{1}*cell[7] + x17 + x20;
auto x26 = -x25;
auto x27 = x14*x26 + x24;
auto x28 = x23 + V{-1} + V{1.5}*((x27)*(x27));
auto x29 = V{1} - x12;
auto x30 = V{3}*cell[3];
auto x31 = V{3}*cell[1] - V{3}*cell[5];
auto x32 = V{1.5}*x10 + x14*(-V{3}*cell[4] + V{3}*cell[7] + V{3}*cell[8] - x30 + x31);
auto x33 = x10*x32;
auto x34 = V{1.5}*x9;
auto x35 = V{3}*cell[2] - V{3}*cell[6] - V{3}*cell[7] + x30 + x31;
auto x36 = -x14*x35;
auto x37 = x34 + x36;
auto x38 = x13*(V{1} - V{0.5}*x12);
auto x39 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x40 = -x34;
auto x41 = x14*x35;
auto x42 = x14*x25;
auto x43 = x21 - x24;
auto x44 = V{4.5}*cell[3];
auto x45 = V{4.5}*cell[7];
auto x46 = V{4.5}*cell[1] - V{4.5}*cell[5];
auto x47 = V{4.5}*cell[2] - V{4.5}*cell[6] + x44 - x45 + x46;
auto x48 = x14*x47;
auto x49 = V{2.25}*x9;
auto x50 = V{2.25}*x10 + x14*(-V{4.5}*cell[4] + V{4.5}*cell[8] - x44 + x45 + x46);
auto x51 = -x49 + x50;
auto x52 = x24 - x42;
auto x53 = ((x52)*(x52));
auto x54 = -x23 - V{1.5}*x53 + V{1};
auto x55 = x32 + x54;
auto x56 = V{4.5}*x9;
auto x57 = V{9}*cell[3];
auto x58 = V{9}*cell[7];
auto x59 = V{9}*cell[1] - V{9}*cell[5];
auto x60 = V{9}*cell[2] - V{9}*cell[6] + x57 - x58 + x59;
auto x61 = x14*x60;
auto x62 = V{3}*x10;
auto x63 = V{6}*cell[7];
auto x64 = V{6}*cell[3];
auto x65 = V{6}*cell[1] - V{6}*cell[5];
auto x66 = x14*(-V{6}*cell[4] + V{6}*cell[8] + x63 - x64 + x65);
auto x67 = x62 + x66;
auto x68 = x67 + V{3};
auto x69 = V{3}*x9;
auto x70 = x14*(V{6}*cell[2] - V{6}*cell[6] - x63 + x64 + x65);
auto x71 = -x69 + x70;
auto x72 = x71 + V{3};
auto x73 = V{4.5}*x10 + x14*(-V{9}*cell[4] + V{9}*cell[8] - x57 + x58 + x59);
auto x74 = V{0.0277777777777778}*x38;
auto x75 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x76 = -x47;
auto x77 = x14*x76 + x49;
auto x78 = x28 + x37;
auto x79 = V{0.111111111111111}*x38;
auto x80 = x67 + V{-3};
auto x81 = x56 - x61;
auto x82 = x69 - x70;
auto x83 = x73 + V{-3};
auto x84 = x21*x50;
auto x85 = x28 + x32;
auto x86 = x34 - x41;
auto x87 = -x86*x9;
auto x88 = -x48 + x49;
auto x89 = x54 + x86;
auto x90 = x82 + V{3};
auto x0 = V{1}*cell[0]*x29 - x12*(x28*(V{0.444444444444444}*cell[0] + V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + V{0.444444444444444}) + V{0.444444444444444}) - V{0.444444444444444}*x38*(x33 + x37*x9);
auto x1 = x12*(x39*(x40 + x41 + x55 + (x42 + x43)*(x48 + x51)) + V{-0.0277777777777778}) + x19*x29 + x74*(x10*(-x56 + x61 + x68) - x9*(x72 + x73));
auto x2 = V{1}*cell[2]*x29 - x12*(x75*(-x27*x77 + x78) + V{0.111111111111111}) - x79*(x33 + x72*x9);
auto x3 = -x12*(x39*(x32 + x78 - (x21 + x27)*(x50 + x77)) + V{0.0277777777777778}) + x17*x29 + x74*(x10*(x80 + x81) + x9*(x82 + x83));
auto x4 = -x12*(x75*(-x84 + x85) + V{0.111111111111111}) + x18*x29 + x79*(x10*x80 + x87);
auto x5 = V{1}*cell[5]*x29 - x12*(x39*(-x36 + x40 + x85 - (x14*x26 - x43)*(x14*x76 - x51)) + V{0.0277777777777778}) - x74*(x10*(-x14*x60 + x56 - x62 - x66 + V{3}) - x9*(-x71 - x83));
auto x6 = V{1}*cell[6]*x29 + x12*(x75*(x52*x88 + x89) + V{-0.111111111111111}) - x79*(x33 - x9*x90);
auto x7 = x12*(x39*(x32 + x89 + (x21 + x52)*(x50 + x88)) + V{-0.0277777777777778}) + x15*x29 + x74*(x10*(x68 + x81) + x9*(x73 + x90));
auto x8 = x12*(x75*(x55 + x84) + V{-0.111111111111111}) + x16*x29 + x79*(x10*x68 + x87);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x13, x22 + x53 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
