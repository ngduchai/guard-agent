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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::ParameterFromCell<descriptors::OMEGA, collision::BGK>, forcing::Wagner>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x11 = cell.template getFieldComponent<olb::descriptors::OMEGA>(0);
auto x12 = cell.template getFieldComponent<olb::descriptors::SCALAR>(0);
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x13 = x11 + V{-1};
auto x14 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x15 = x14 + V{1};
auto x16 = V{0.666666} - V{0.1666665}*x11;
auto x17 = ((x10)*(x10));
auto x18 = ((x9)*(x9));
auto x19 = V{1} / (x15);
auto x20 = x11*x12*x19;
auto x21 = V{1.33333333333333}*x19;
auto x22 = cell[1] - cell[5];
auto x23 = -cell[4] + cell[8];
auto x24 = -cell[3] + cell[7] + x22 + x23;
auto x25 = x10*x24;
auto x26 = cell[2] - cell[6];
auto x27 = cell[3] - cell[7] + x22 + x26;
auto x28 = -x27;
auto x29 = x14 + V{1};
auto x30 = V{1} / ((x15)*(x15));
auto x31 = V{1.5}*x30;
auto x32 = ((x24)*(x24));
auto x33 = x31*x32;
auto x34 = x31*((x28)*(x28)) + V{-1};
auto x35 = x33 + x34;
auto x36 = V{6}*cell[3];
auto x37 = V{6}*cell[1] - V{6}*cell[5];
auto x38 = V{6}*cell[2] - V{6}*cell[6] - V{6}*cell[7] + x36 + x37;
auto x39 = V{9}*cell[7];
auto x40 = V{9}*cell[3];
auto x41 = V{9}*cell[1] - V{9}*cell[5];
auto x42 = x19*(-V{9}*cell[4] + V{9}*cell[8] + x39 - x40 + x41);
auto x43 = x42 + V{3};
auto x44 = V{0.0277777777777778}*x9;
auto x45 = V{9}*cell[2] - V{9}*cell[6] - x39 + x40 + x41;
auto x46 = x19*x45;
auto x47 = x19*(-V{6}*cell[4] + V{6}*cell[7] + V{6}*cell[8] - x36 + x37);
auto x48 = x47 + V{3};
auto x49 = V{0.0277777777777778}*x10;
auto x50 = V{0.25}*x11 + V{-1};
auto x51 = V{0.25}*x10*x50*x9;
auto x52 = V{0.02083334375}*x11 + V{-0.083333375};
auto x53 = x17*x52 + x18*x52 - V{0.0138888958333333}*x20;
auto x54 = -x51 + x53;
auto x55 = V{3}*cell[3];
auto x56 = V{3}*cell[7];
auto x57 = V{3}*cell[1] - V{3}*cell[5];
auto x58 = V{3}*cell[2] - V{3}*cell[6] + x55 - x56 + x57;
auto x59 = x19*x58;
auto x60 = V{4.5}*x30;
auto x61 = x60*((2*cell[1] - 2*cell[5] + x23 + x26)*(2*cell[1] - 2*cell[5] + x23 + x26));
auto x62 = V{1} - x33;
auto x63 = x19*(-V{3}*cell[4] + V{3}*cell[8] - x55 + x56 + x57);
auto x64 = ((x27)*(x27));
auto x65 = x31*x64;
auto x66 = x63 - x65;
auto x67 = x62 + x66;
auto x68 = x19*x38;
auto x69 = x68 + V{3};
auto x70 = V{0.111111111111111}*x9;
auto x71 = V{0.083333375}*x11 + V{-0.3333335};
auto x72 = V{0.333333333333333}*x19;
auto x73 = -V{0.0138889166666667}*x11*x12*x19 - V{0.1666665}*x17*x50 + x18*x71 + x25*x72;
auto x74 = V{0.111111111111111}*x11;
auto x75 = V{3}*x30;
auto x76 = x62 + x64*x75;
auto x77 = V{3} - x47;
auto x78 = x51 + x53;
auto x79 = V{0.0277777777777778}*x11;
auto x80 = V{2}*cell[3] + cell[4] - V{2}*cell[7] - cell[8] + x26;
auto x81 = V{0.111111111111111}*x10;
auto x82 = -x17*x71 + x18*(V{0.041666625}*x11 + V{-0.1666665}) + V{0.0138889166666667}*x20 + x27*x72*x9;
auto x83 = x32*x75;
auto x84 = x68 + V{-3};
auto x85 = -x59;
auto x0 = -cell[0]*x13 - V{0.444444444444444}*x11*(x29*x35 + V{1}) - x15*(x16*x17 + x16*x18 + V{0.111111}*x20 + x21*x25 + x21*x28*x9);
auto x1 = -cell[1]*x13 + V{0.0277777777777778}*x11*(x29*(x59 + x61 + x67) + V{-1}) - x15*(x44*(x19*x38 + x43) - x49*(x46 + x48) + x54);
auto x2 = -cell[2]*x13 + x15*(-x69*x70 - x73) + x74*(x29*(x59 + x76) + V{-1});
auto x3 = -(cell[3]*x13 + x15*(-x44*(x42 - x69) - x49*(-x46 - x77) + x78) + x79*(x29*(-x19*x58 + x35 - x60*((x80)*(x80)) + x63) + V{1}));
auto x4 = -cell[4]*x13 + x15*(x81*(x47 + V{-3}) + x82) - x74*(x29*(x34 + x63 - x83) + V{1});
auto x5 = -cell[5]*x13 - x15*(-x44*(-x42 - x84) + x49*(-x19*x45 + x77) + x54) - x79*(x29*(x33 + x59 - x61 + x63 + x65 + V{-1}) + V{1});
auto x6 = -cell[6]*x13 + x15*(-x70*x84 - x73) + x74*(x29*(x76 + x85) + V{-1});
auto x7 = -(cell[7]*x13 - V{0.0277777777777778}*x11*(x29*(x60*((x80)*(x80)) + x67 + x85) + V{-1}) + x15*(-x44*(x43 - x68) - x49*(-x46 + x48) + x78));
auto x8 = -cell[8]*x13 + x15*(x48*x81 + x82) + x74*(x29*(x66 + x83 + V{1}) + V{-1});
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x15, V{1}*x30*(x32 + x64) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
