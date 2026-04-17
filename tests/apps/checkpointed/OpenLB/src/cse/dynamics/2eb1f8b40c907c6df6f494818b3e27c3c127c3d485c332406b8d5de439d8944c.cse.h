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
struct CSE<Dual<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Porous<momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq> >, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x11 = cell.template getFieldComponent<olb::descriptors::POROSITY>(0);
auto x14 = cell.template getFieldComponent<olb::opti::DJDF>(0);
auto x15 = cell.template getFieldComponent<olb::opti::DJDF>(1);
auto x16 = cell.template getFieldComponent<olb::opti::DJDF>(2);
auto x17 = cell.template getFieldComponent<olb::opti::DJDF>(3);
auto x18 = cell.template getFieldComponent<olb::opti::DJDF>(4);
auto x19 = cell.template getFieldComponent<olb::opti::DJDF>(5);
auto x20 = cell.template getFieldComponent<olb::opti::DJDF>(6);
auto x21 = cell.template getFieldComponent<olb::opti::DJDF>(7);
auto x22 = cell.template getFieldComponent<olb::opti::DJDF>(8);
auto x23 = cell.template getFieldComponent<olb::opti::F>(0);
auto x24 = cell.template getFieldComponent<olb::opti::F>(1);
auto x25 = cell.template getFieldComponent<olb::opti::F>(2);
auto x26 = cell.template getFieldComponent<olb::opti::F>(3);
auto x27 = cell.template getFieldComponent<olb::opti::F>(4);
auto x28 = cell.template getFieldComponent<olb::opti::F>(5);
auto x29 = cell.template getFieldComponent<olb::opti::F>(6);
auto x30 = cell.template getFieldComponent<olb::opti::F>(7);
auto x31 = cell.template getFieldComponent<olb::opti::F>(8);
auto x32 = parameters.template get<descriptors::OMEGA>();
auto x9 = V{1}*x32 + V{-1};
auto x10 = V{0.0277777777777778}*x32;
auto x12 = x24 - x28;
auto x13 = -x27 + x31;
auto x33 = x12 + x13 - x26 + x30;
auto x34 = x23 + x24 + x25 + x26 + x27 + x28 + x29 + x30 + x31;
auto x35 = x34 + V{1};
auto x36 = x11/x35;
auto x37 = V{3}*x36;
auto x38 = x33*x37;
auto x39 = V{1} / ((x35)*(x35));
auto x40 = V{4.5}*x39;
auto x41 = ((x11)*(x11));
auto x42 = x25 - x29;
auto x43 = x13 + V{2}*x24 - V{2}*x28 + x42;
auto x44 = x12 + x26 - x30 + x42;
auto x45 = -x44;
auto x46 = x37*x45;
auto x47 = V{1.5}*x39;
auto x48 = x41*((x33)*(x33));
auto x49 = x47*x48;
auto x50 = x41*x47*((x45)*(x45)) + V{-1};
auto x51 = x49 + x50;
auto x52 = x46 + x51;
auto x53 = -V{2}*x26 - x27 + V{2}*x30 + x31 - x42;
auto x54 = x40*x41*((x53)*(x53));
auto x55 = -x43;
auto x56 = V{3}*x39;
auto x57 = x48*x56;
auto x58 = x37*x44;
auto x59 = -x58;
auto x60 = V{1} - x49;
auto x61 = x41*((x44)*(x44));
auto x62 = x38 - x47*x61;
auto x63 = x56*x61 + x60;
auto x64 = V{0.0833333333333333}*cell[1];
auto x65 = V{0.0833333333333333}*cell[5];
auto x66 = V{0.25}*x36;
auto x67 = cell[5]*x43*x66;
auto x68 = x33*x36;
auto x69 = V{1}*x68;
auto x70 = cell[1]*x55*x66;
auto x71 = V{1.33333333333333}*cell[0] + V{0.0833333333333333}*cell[1] + V{0.333333333333333}*cell[2] + V{0.0833333333333333}*cell[3] + V{0.333333333333333}*cell[4] + V{0.0833333333333333}*cell[5] + V{0.333333333333333}*cell[6] + V{0.0833333333333333}*cell[7] + V{0.333333333333333}*cell[8];
auto x72 = x53*x66;
auto x73 = cell[3]*x72 - V{0.0833333333333333}*cell[3] + cell[7]*x72 + V{0.0833333333333333}*cell[7];
auto x74 = cell[4]*x69 - V{0.333333333333333}*cell[4] + cell[8]*x69 + V{0.333333333333333}*cell[8] + x64 - x65 + x67 - x68*x71 - x70 + x73;
auto x75 = x34 + V{1};
auto x76 = V{1}*x32*x75;
auto x77 = x36*x44;
auto x78 = V{1}*x77;
auto x79 = -cell[2]*x78 - V{0.333333333333333}*cell[2] - cell[6]*x78 + V{0.333333333333333}*cell[6] - x64 + x65 - x67 + x70 + x71*x77 + x73;
auto x80 = V{0.444444444444444}*cell[0]*x32*x51 + cell[1]*x10*(-x38 - x40*x41*((x43)*(x43)) + x52) - V{0.111111111111111}*cell[2]*x32*(x58 + x63) + cell[3]*x10*(x38 + x52 - x54) + V{0.111111111111111}*cell[4]*x32*(x38 + x50 - x57) + cell[5]*x10*(x38 - x40*x41*((x55)*(x55)) - x46 + x51) - V{0.111111111111111}*cell[6]*x32*(x59 + x63) - V{0.0277777777777778}*cell[7]*x32*(x54 + x59 + x60 + x62) - V{0.111111111111111}*cell[8]*x32*(x57 + x62 + V{1}) - V{1}*x11*x32*x39*x44*x75*x79 + x11*x33*x39*x74*x76;
auto x81 = cell[0]*x9 + x14 + x80;
auto x82 = x36*x76;
auto x83 = x74*x82;
auto x84 = -x83;
auto x85 = x79*x82;
auto x86 = x80 + x85;
auto x87 = cell[1]*x9 + x15 + x84 + x86;
auto x88 = cell[2]*x9 + x16 + x86;
auto x89 = cell[3]*x9 + x17 + x83 + x86;
auto x90 = x80 + x83;
auto x91 = cell[4]*x9 + x18 + x90;
auto x92 = -x85;
auto x93 = cell[5]*x9 + x19 + x90 + x92;
auto x94 = x80 + x92;
auto x95 = cell[6]*x9 + x20 + x94;
auto x96 = cell[7]*x9 + x21 + x84 + x94;
auto x97 = cell[8]*x9 + x22 + x80 + x84;
cell[0] = -x81;
cell[1] = -x87;
cell[2] = -x88;
cell[3] = -x89;
cell[4] = -x91;
cell[5] = -x93;
cell[6] = -x95;
cell[7] = -x96;
cell[8] = -x97;
return { V{1} - x81, ((x81)*(x81)) + ((x87)*(x87)) + ((x88)*(x88)) + ((x89)*(x89)) + ((x91)*(x91)) + ((x93)*(x93)) + ((x95)*(x95)) + ((x96)*(x96)) + ((x97)*(x97)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
