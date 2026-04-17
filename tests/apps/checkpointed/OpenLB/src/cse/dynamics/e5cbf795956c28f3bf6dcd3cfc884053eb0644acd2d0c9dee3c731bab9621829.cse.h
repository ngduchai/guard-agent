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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, guoZhao::GuoZhaoSecondOrder, collision::BGK, guoZhao::GuoZhaoForcing<momenta::GuoZhaoForced> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = cell.template getFieldComponent<olb::descriptors::BODY_FORCE>(0);
auto x15 = cell.template getFieldComponent<olb::descriptors::NU>(0);
auto x14 = cell.template getFieldComponent<olb::descriptors::K>(0);
auto x11 = cell.template getFieldComponent<olb::descriptors::EPSILON>(0);
auto x10 = cell.template getFieldComponent<olb::descriptors::BODY_FORCE>(1);
auto x16 = parameters.template get<descriptors::OMEGA>();
auto x12 = x16 + V{-1};
auto x13 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x17 = x13 + V{1};
auto x18 = V{1} / (x11);
auto x19 = V{0.5}*x11;
auto x20 = x15/x14;
auto x21 = x19*x20 + V{1};
auto x22 = util::sqrt(((x21)*(x21)));
auto x23 = V{1} / ((x21 + x22)*(x21 + x22));
auto x24 = x13 + V{1};
auto x25 = V{1} / (x24);
auto x26 = V{1}*cell[7];
auto x27 = V{1}*cell[3];
auto x28 = V{1}*cell[1] - V{1}*cell[5];
auto x29 = -V{1}*cell[4] + V{1}*cell[8] + x26 - x27 + x28;
auto x30 = x25*x29;
auto x31 = x10*x19 + x30;
auto x32 = ((x31)*(x31));
auto x33 = V{6}*x32;
auto x34 = V{1}*cell[2] - V{1}*cell[6] - x26 + x27 + x28;
auto x35 = x25*x34;
auto x36 = x19*x9;
auto x37 = -x35 + x36;
auto x38 = ((x37)*(x37));
auto x39 = -x18*x23*(x33 + V{6}*x38) + V{1};
auto x40 = x24*(V{0.5}*x16 + V{-1});
auto x41 = V{1} / (V{0.25}*x11*x20 + V{0.5}*x22 + V{0.5});
auto x42 = V{1}*x20;
auto x43 = x10 - x31*x41*x42;
auto x44 = -x37*x41*x42 + x9;
auto x45 = V{1.5}*x11;
auto x46 = x45*x9;
auto x47 = -V{3}*x35 + x46;
auto x48 = x41*x47;
auto x49 = V{18}*x18;
auto x50 = x31 - x36;
auto x51 = x10*x45 + V{3}*x30;
auto x52 = x41*x51;
auto x53 = x39 + x52;
auto x54 = V{0.0277777777777778}*x40;
auto x55 = x41*x51;
auto x56 = -x55;
auto x57 = V{3}*x11;
auto x58 = V{9}*x35;
auto x59 = V{4.5}*x11;
auto x60 = x59*x9;
auto x61 = x10*x59 + V{9}*x30;
auto x62 = -x60 + x61;
auto x63 = x41*(x58 + x62) + x57;
auto x64 = -x25*x34;
auto x65 = x46 + V{3}*x64;
auto x66 = x41*x65;
auto x67 = V{0.111111111111111}*x16;
auto x68 = x36 + x64;
auto x69 = ((x68)*(x68));
auto x70 = x18*x23*(x33 + V{6}*x69) + V{-1};
auto x71 = x41*x65 + x70;
auto x72 = -x58 + x60;
auto x73 = x57 + x66;
auto x74 = -x41*x43*(V{0.166666666666667}*x10*x11 + V{0.333333333333333}*x25*x29);
auto x75 = V{9}*x64;
auto x76 = -x41*(x60 + x61 + x75);
auto x77 = x55 + x57;
auto x78 = x23*x32*x49;
auto x79 = -x41*x44*(V{0.166666666666667}*x11*x9 - V{0.333333333333333}*x25*x34);
auto x80 = x39 + x48;
auto x81 = x41*(x62 - x75);
auto x82 = x41*x47;
auto x83 = x57 - x82;
auto x84 = x41*(x61 + x72);
auto x85 = x56 + x57;
auto x0 = -cell[0]*x12 + V{0.444444444444444}*x16*(x17*x39 + V{-1}) + V{1.33333333333333}*x40*x41*(x31*x43 + x37*x44);
auto x1 = -(cell[1]*x12 - V{0.0277777777777778}*x16*(x17*(x23*x49*((x35 + x50)*(x35 + x50)) - x48 + x53) + V{-1}) + x54*(x43*(x56 + x63) - x44*(x63 + x66)));
auto x2 = -cell[2]*x12 - x40*(V{0.111111111111111}*x44*(x41*x72 - x73) + x74) - x67*(x17*(-x23*x49*x69 + x71) + V{1});
auto x3 = -(cell[3]*x12 + V{0.0277777777777778}*x16*(x17*(-x23*x49*((x31 + x68)*(x31 + x68)) + x52 + x71) + V{1}) + x54*(x43*(-x76 - x77) + x44*(-x73 - x76)));
auto x4 = -cell[4]*x12 - x40*(V{0.111111111111111}*x43*(x41*x61 - x77) + x79) - x67*(x17*(x52 + x70 - x78) + V{1});
auto x5 = -(cell[5]*x12 - V{0.0277777777777778}*x16*(x17*(x23*x49*((x50 - x64)*(x50 - x64)) - x52 + x80) + V{-1}) + x54*(x43*(-x77 + x81) + x44*(x57 - x81 - x82)));
auto x6 = -cell[6]*x12 + V{0.111111111111111}*x16*(x17*(x23*x38*x49 + x80) + V{-1}) - x40*(V{0.111111111111111}*x44*(x41*x72 + x83) + x74);
auto x7 = -(cell[7]*x12 - V{0.0277777777777778}*x16*(x17*(x23*x49*((x31 + x37)*(x31 + x37)) + x52 + x80) + V{-1}) + x54*(x43*(x84 + x85) + x44*(x83 + x84)));
auto x8 = -cell[8]*x12 + V{0.111111111111111}*x16*(x17*(x53 + x78) + V{-1}) - x40*(V{0.111111111111111}*x43*(x41*x61 + x85) + x79);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x24, V{4}*x23*(x32 + x38) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
