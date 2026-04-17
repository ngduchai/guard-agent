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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, forcing::Guo<momenta::ForcedWithStress> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x11 = parameters.template get<descriptors::OMEGA>();
auto x12 = x11 + V{-1};
auto x13 = V{0.5}*x11 + V{-1};
auto x14 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x15 = x14 + V{1};
auto x16 = V{1} / (x15);
auto x17 = V{3}*cell[3];
auto x18 = V{3}*cell[1] - V{3}*cell[5];
auto x19 = V{1.5}*x10 + x16*(-V{3}*cell[4] + V{3}*cell[7] + V{3}*cell[8] - x17 + x18);
auto x20 = x10*x19;
auto x21 = V{1.5}*x9;
auto x22 = V{3}*cell[2] - V{3}*cell[6] - V{3}*cell[7] + x17 + x18;
auto x23 = -x16*x22;
auto x24 = x21 + x23;
auto x25 = x24*x9;
auto x26 = x14 + V{1};
auto x27 = V{1}*cell[3];
auto x28 = V{1}*cell[1] - V{1}*cell[5];
auto x29 = V{0.5}*x10 + x16*(-V{1}*cell[4] + V{1}*cell[7] + V{1}*cell[8] - x27 + x28);
auto x30 = ((x29)*(x29));
auto x31 = V{1.5}*x30;
auto x32 = V{0.5}*x9;
auto x33 = V{1}*cell[2] - V{1}*cell[6] - V{1}*cell[7] + x27 + x28;
auto x34 = -x33;
auto x35 = x16*x34 + x32;
auto x36 = x31 + V{-1} + V{1.5}*((x35)*(x35));
auto x37 = V{4.5}*x9;
auto x38 = V{9}*cell[3];
auto x39 = V{9}*cell[7];
auto x40 = V{9}*cell[1] - V{9}*cell[5];
auto x41 = V{9}*cell[2] - V{9}*cell[6] + x38 - x39 + x40;
auto x42 = x16*x41;
auto x43 = V{3}*x10;
auto x44 = V{6}*cell[3];
auto x45 = V{6}*cell[1] - V{6}*cell[5];
auto x46 = x16*(-V{6}*cell[4] + V{6}*cell[7] + V{6}*cell[8] - x44 + x45);
auto x47 = x43 + x46;
auto x48 = x47 + V{3};
auto x49 = V{6}*cell[2] - V{6}*cell[6] - V{6}*cell[7] + x44 + x45;
auto x50 = V{3}*x9;
auto x51 = -x50;
auto x52 = x51 + V{3};
auto x53 = V{4.5}*x10 + x16*(-V{9}*cell[4] + V{9}*cell[8] - x38 + x39 + x40);
auto x54 = x13*x15;
auto x55 = V{0.0277777777777778}*x54;
auto x56 = -x21;
auto x57 = x16*x22;
auto x58 = x16*x33;
auto x59 = x29 - x32;
auto x60 = V{4.5}*cell[3];
auto x61 = V{4.5}*cell[7];
auto x62 = V{4.5}*cell[1] - V{4.5}*cell[5];
auto x63 = V{4.5}*cell[2] - V{4.5}*cell[6] + x60 - x61 + x62;
auto x64 = x16*x63;
auto x65 = V{2.25}*x9;
auto x66 = V{2.25}*x10 + x16*(-V{4.5}*cell[4] + V{4.5}*cell[8] - x60 + x61 + x62);
auto x67 = -x65 + x66;
auto x68 = x32 - x58;
auto x69 = ((x68)*(x68));
auto x70 = -x31 - V{1.5}*x69 + V{1};
auto x71 = x19 + x70;
auto x72 = x16*x49;
auto x73 = V{0.111111111111111}*x54;
auto x74 = V{0.111111111111111}*x11;
auto x75 = -x63;
auto x76 = x16*x75 + x65;
auto x77 = x24 + x36;
auto x78 = x47 + V{-3};
auto x79 = x37 - x42;
auto x80 = x50 - x72;
auto x81 = x53 + V{-3};
auto x82 = V{0.0277777777777778}*x11;
auto x83 = -x25;
auto x84 = x29*x66;
auto x85 = x19 + x36;
auto x86 = x80 + V{3};
auto x87 = -x64 + x65;
auto x88 = x21 - x57 + x70;
auto x0 = -cell[0]*x12 - V{0.444444444444444}*x11*(x26*x36 + V{1}) + V{0.444444444444444}*x13*x15*(x20 + x25);
auto x1 = -cell[1]*x12 + V{0.0277777777777778}*x11*(x26*(x56 + x57 + x71 + (x58 + x59)*(x64 + x67)) + V{-1}) - x55*(x10*(-x37 + x42 + x48) - x9*(x16*x49 + x52 + x53));
auto x2 = -cell[2]*x12 - x73*(-x20 + x9*(-x52 - x72)) - x74*(x26*(-x35*x76 + x77) + V{1});
auto x3 = -cell[3]*x12 - x55*(x10*(x78 + x79) + x9*(x80 + x81)) - x82*(x26*(x19 + x77 - (x29 + x35)*(x66 + x76)) + V{1});
auto x4 = -cell[4]*x12 - x73*(x10*x78 + x83) - x74*(x26*(-x84 + x85) + V{1});
auto x5 = -cell[5]*x12 - x55*(-x10*(-x16*x41 + x37 - x43 - x46 + V{3}) + x9*(-x51 - x72 - x81)) - x82*(x26*(-x23 + x56 + x85 - (x16*x34 - x59)*(x16*x75 - x67)) + V{1});
auto x6 = -cell[6]*x12 + V{0.111111111111111}*x11*(x26*(x68*x87 + x88) + V{-1}) - x73*(-x20 + x86*x9);
auto x7 = -cell[7]*x12 + V{0.0277777777777778}*x11*(x26*(x19 + x88 + (x29 + x68)*(x66 + x87)) + V{-1}) - x55*(x10*(x48 + x79) + x9*(x53 + x86));
auto x8 = -cell[8]*x12 + V{0.111111111111111}*x11*(x26*(x71 + x84) + V{-1}) - x73*(x10*x48 + x83);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x15, x30 + x69 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
