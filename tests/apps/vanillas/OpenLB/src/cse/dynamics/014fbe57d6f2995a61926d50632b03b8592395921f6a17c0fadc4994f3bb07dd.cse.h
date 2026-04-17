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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SmagorinskyEffectiveOmega<collision::BGK>, forcing::Guo<momenta::ForcedWithStress> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x11 = parameters.template get<descriptors::OMEGA>();
auto x12 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x13 = cell[2] + cell[3];
auto x14 = cell[7] + cell[8];
auto x15 = cell[0] + cell[1] + cell[4] + cell[5] + cell[6] + x13 + x14;
auto x16 = x15 + V{1};
auto x17 = V{1} / (x16);
auto x18 = cell[1] - cell[5];
auto x19 = -cell[6] - cell[7] + x13 + x18;
auto x20 = x17*(x15 + V{1});
auto x21 = -V{0.333333333333333}*cell[0] + V{0.666666666666667}*cell[1] + V{0.666666666666667}*cell[3] + V{0.666666666666667}*cell[5] + V{0.666666666666667}*cell[7];
auto x22 = -cell[3] - cell[4] + x14 + x18;
auto x23 = V{1}*cell[3];
auto x24 = V{1}*cell[1];
auto x25 = x20*(-x10*x19 + x22*x9);
auto x26 = x17*x19*x22;
auto x27 = V{1}*cell[7];
auto x28 = -V{1}*cell[5];
auto x29 = x27 + x28;
auto x30 = V{1} / (V{2.52268963608289}*util::sqrt(x17*((x12)*(x12))*util::sqrt((-x23 + x24 - V{0.5}*x25 - V{1}*x26 - x29)*(V{2}*cell[1] - V{2}*cell[3] + V{2}*cell[5] - V{2}*cell[7] - V{1}*x25 - V{2}*x26) + V{1}*((-V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[4] - V{0.333333333333333}*cell[6] + V{0.666666666666667}*cell[8] + x10*x20*x22 - x17*((x22)*(x22)) + x21)*(-V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[4] - V{0.333333333333333}*cell[6] + V{0.666666666666667}*cell[8] + x10*x20*x22 - x17*((x22)*(x22)) + x21)) + V{1}*((V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[4] + V{0.666666666666667}*cell[6] - V{0.333333333333333}*cell[8] - x17*((x19)*(x19)) - x19*x20*x9 + x21)*(V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[4] + V{0.666666666666667}*cell[6] - V{0.333333333333333}*cell[8] - x17*((x19)*(x19)) - x19*x20*x9 + x21))) + V{0.0392836979096202}/((x11)*(x11))) + V{0.5}/x11);
auto x31 = V{1}*cell[8];
auto x32 = V{1}*cell[4];
auto x33 = V{0.5}*x10 + x17*(-x23 + x24 + x29 + x31 - x32);
auto x34 = ((x33)*(x33));
auto x35 = V{1.5}*x34;
auto x36 = V{0.5}*x9;
auto x37 = V{1}*cell[2] - V{1}*cell[6] + x23 + x24 - x27 + x28;
auto x38 = -x37;
auto x39 = x17*x38 + x36;
auto x40 = x35 + V{-1} + V{1.5}*((x39)*(x39));
auto x41 = V{1} - x30;
auto x42 = V{3}*cell[3];
auto x43 = V{3}*cell[1] - V{3}*cell[5];
auto x44 = V{1.5}*x10 + x17*(-V{3}*cell[4] + V{3}*cell[7] + V{3}*cell[8] - x42 + x43);
auto x45 = x10*x44;
auto x46 = V{1.5}*x9;
auto x47 = V{3}*cell[2] - V{3}*cell[6] - V{3}*cell[7] + x42 + x43;
auto x48 = -x17*x47;
auto x49 = x46 + x48;
auto x50 = V{1} - V{0.5}*x30;
auto x51 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x52 = -x46;
auto x53 = x17*x47;
auto x54 = x17*x37;
auto x55 = x33 - x36;
auto x56 = V{4.5}*cell[3];
auto x57 = V{4.5}*cell[7];
auto x58 = V{4.5}*cell[1] - V{4.5}*cell[5];
auto x59 = V{4.5}*cell[2] - V{4.5}*cell[6] + x56 - x57 + x58;
auto x60 = x17*x59;
auto x61 = V{2.25}*x9;
auto x62 = V{2.25}*x10 + x17*(-V{4.5}*cell[4] + V{4.5}*cell[8] - x56 + x57 + x58);
auto x63 = -x61 + x62;
auto x64 = x36 - x54;
auto x65 = ((x64)*(x64));
auto x66 = -x35 - V{1.5}*x65 + V{1};
auto x67 = x44 + x66;
auto x68 = V{4.5}*x9;
auto x69 = V{9}*cell[3];
auto x70 = V{9}*cell[7];
auto x71 = V{9}*cell[1] - V{9}*cell[5];
auto x72 = V{9}*cell[2] - V{9}*cell[6] + x69 - x70 + x71;
auto x73 = x17*x72;
auto x74 = V{3}*x10;
auto x75 = V{6}*cell[7];
auto x76 = V{6}*cell[3];
auto x77 = V{6}*cell[1] - V{6}*cell[5];
auto x78 = x17*(-V{6}*cell[4] + V{6}*cell[8] + x75 - x76 + x77);
auto x79 = x74 + x78;
auto x80 = x79 + V{3};
auto x81 = V{3}*x9;
auto x82 = x17*(V{6}*cell[2] - V{6}*cell[6] - x75 + x76 + x77);
auto x83 = -x81 + x82;
auto x84 = x83 + V{3};
auto x85 = V{4.5}*x10 + x17*(-V{9}*cell[4] + V{9}*cell[8] - x69 + x70 + x71);
auto x86 = V{0.0277777777777778}*x16;
auto x87 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x88 = -x59;
auto x89 = x17*x88 + x61;
auto x90 = x40 + x49;
auto x91 = V{0.111111111111111}*x16;
auto x92 = x79 + V{-3};
auto x93 = x68 - x73;
auto x94 = x81 - x82;
auto x95 = x85 + V{-3};
auto x96 = x33*x62;
auto x97 = x40 + x44;
auto x98 = x46 - x53;
auto x99 = -x9*x98;
auto x100 = -x60 + x61;
auto x101 = x66 + x98;
auto x102 = x94 + V{3};
auto x0 = V{1}*cell[0]*x41 - V{0.444444444444444}*x16*x50*(x45 + x49*x9) - x30*(x40*(V{0.444444444444444}*cell[0] + V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + V{0.444444444444444}) + V{0.444444444444444});
auto x1 = x24*x41 + x30*(x51*(x52 + x53 + x67 + (x54 + x55)*(x60 + x63)) + V{-0.0277777777777778}) + x50*x86*(x10*(-x68 + x73 + x80) - x9*(x84 + x85));
auto x2 = V{1}*cell[2]*x41 - x30*(x87*(-x39*x89 + x90) + V{0.111111111111111}) - x50*x91*(x45 + x84*x9);
auto x3 = x23*x41 - x30*(x51*(x44 + x90 - (x33 + x39)*(x62 + x89)) + V{0.0277777777777778}) + x50*x86*(x10*(x92 + x93) + x9*(x94 + x95));
auto x4 = -x30*(x87*(-x96 + x97) + V{0.111111111111111}) + x32*x41 + x50*x91*(x10*x92 + x99);
auto x5 = V{1}*cell[5]*x41 - x30*(x51*(-x48 + x52 + x97 - (x17*x38 - x55)*(x17*x88 - x63)) + V{0.0277777777777778}) - x50*x86*(x10*(-x17*x72 + x68 - x74 - x78 + V{3}) - x9*(-x83 - x95));
auto x6 = V{1}*cell[6]*x41 + x30*(x87*(x100*x64 + x101) + V{-0.111111111111111}) - x50*x91*(-x102*x9 + x45);
auto x7 = x27*x41 + x30*(x51*(x101 + x44 + (x100 + x62)*(x33 + x64)) + V{-0.0277777777777778}) + x50*x86*(x10*(x80 + x93) + x9*(x102 + x85));
auto x8 = x30*(x87*(x67 + x96) + V{-0.111111111111111}) + x31*x41 + x50*x91*(x10*x80 + x99);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x16, x34 + x65 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
