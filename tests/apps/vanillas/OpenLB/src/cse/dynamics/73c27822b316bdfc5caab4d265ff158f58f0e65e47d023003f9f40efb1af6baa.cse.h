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
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::ParameterFromCell<descriptors::OMEGA, collision::BGK>, forcing::Wagner>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, -1>, momenta::RegularizedBoundaryStress<0, -1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x12 = cell.template getFieldComponent<olb::descriptors::SCALAR>(0);
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x15 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, -1>::VELOCITY>(1);
auto x11 = cell.template getFieldComponent<olb::descriptors::OMEGA>(0);
auto x13 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x14 = x10*x15;
auto x16 = V{1} / (x13);
auto x17 = V{0.444444444444444}*x13;
auto x18 = x16*(cell[0] + V{2}*cell[1] + V{2}*cell[2] + V{2}*cell[3] + cell[4] + cell[8] + V{1});
auto x19 = V{1} - x18;
auto x20 = ((x19)*(x19));
auto x21 = V{1.5}*x20;
auto x22 = ((x15)*(x15));
auto x23 = V{1.5}*x22;
auto x24 = x23 + V{-1};
auto x25 = x21 + x24;
auto x26 = -x25;
auto x27 = V{0.222222222222222}*x13;
auto x28 = x16*(V{3}*cell[0] + V{6}*cell[1] + V{6}*cell[2] + V{6}*cell[3] + V{3}*cell[4] + V{3}*cell[8] + V{3});
auto x29 = V{2} - x28;
auto x30 = x21 + x23;
auto x31 = x29 + x30;
auto x32 = x31 - V{4.5}*((x19)*(x19));
auto x33 = -x32;
auto x34 = V{0.0555555555555555}*x13;
auto x35 = V{4.5}*((x15 + x18 - 1)*(x15 + x18 - 1));
auto x36 = V{3}*x15;
auto x37 = -x21;
auto x38 = x36 + x37;
auto x39 = -x23 + x28 + x35 + x38 + V{-2};
auto x40 = x15 + x19;
auto x41 = x31 + x36;
auto x42 = x41 - V{4.5}*((x40)*(x40));
auto x43 = -x42;
auto x44 = V{0.111111111111111}*x13;
auto x45 = V{3}*x22 + V{1};
auto x46 = x38 + x45;
auto x47 = -x36;
auto x48 = x45 + x47;
auto x49 = x37 + x48;
auto x50 = V{1.33226762955019e-15}*cell[1] + V{6.66133814775094e-16}*cell[2] + V{8.88178419700125e-16}*cell[3] + V{1.66533453693773e-16}*cell[4] + V{1.66533453693773e-16}*cell[8] + x44*x46 + x44*x49 + V{1.11022302462516e-16};
auto x51 = x16*(x17*x26 + x27*x33 + x34*x39 + x34*x43 + x50);
auto x52 = V{1} - x51;
auto x53 = V{0.1666665}*x11 + V{-0.666666};
auto x54 = ((x10)*(x10));
auto x55 = ((x9)*(x9));
auto x56 = x11*x12*x16;
auto x57 = x11 + V{-1};
auto x58 = V{0.0740740740740741}*x13;
auto x59 = -x35;
auto x60 = x31 + x47 + x59;
auto x61 = x17*x25;
auto x62 = x46*x58;
auto x63 = x49*x58;
auto x64 = ((x52)*(x52));
auto x65 = V{1.5}*x64;
auto x66 = V{0.0277777777777778}*x9;
auto x67 = V{9}*x15;
auto x68 = V{0.333333333333333}*x13;
auto x69 = V{1.33333333333333}*x13;
auto x70 = V{2.66666666666667}*x13;
auto x71 = V{0.666666666666667}*x13;
auto x72 = V{7.99360577730113e-15}*cell[1] + V{3.99680288865056e-15}*cell[2] + V{5.32907051820075e-15}*cell[3] + V{9.99200722162641e-16}*cell[4] + V{9.99200722162641e-16}*cell[8] + x46*x71 + x49*x71 + V{6.66133814775094e-16};
auto x73 = x16*(x26*x70 + x33*x69 + x39*x68 + x43*x68 + x72) + x67;
auto x74 = V{0.0277777777777778}*x10;
auto x75 = V{6}*x15;
auto x76 = V{1}*x13;
auto x77 = V{0.5}*x13;
auto x78 = x16*(V{1.19904086659517e-14}*cell[1] + V{5.99520433297585e-15}*cell[2] + V{7.99360577730113e-15}*cell[3] + V{1.49880108324396e-15}*cell[4] + V{1.49880108324396e-15}*cell[8] - V{4}*x13*x25 - V{2}*x13*x32 - x42*x77 + x46*x76 + x49*x76 - x60*x77 + V{9.99200722162641e-16});
auto x79 = x75 + x78;
auto x80 = V{0.25}*x10*x9*(V{0.25}*x11 + V{-1});
auto x81 = V{0.02083334375}*x11 + V{-0.083333375};
auto x82 = x54*x81 + x55*x81 - V{0.0138888958333333}*x56;
auto x83 = -x80 + x82;
auto x84 = V{0.00462962962962963}*x13;
auto x85 = V{0.00462962962962963}*x13;
auto x86 = -V{4.5}*((x40)*(x40));
auto x87 = x41 + x86;
auto x88 = -V{3}*x20 + x23;
auto x89 = x29 + x88;
auto x90 = V{0.00925925925925926}*x13;
auto x91 = V{0.166666666666667}*cell[2] + V{0.0833333333333333}*cell[4] + V{0.0833333333333333}*cell[8] + V{0.0185185185185185}*x13*x89 - x46*x90 - x49*x90 + V{0.0277777777777778};
auto x92 = V{0.833333333333333}*cell[1] - V{0.166666666666667}*cell[3] - x85*x87 + x91;
auto x93 = V{0.0277777777777778}*x11;
auto x94 = x51 + V{-1};
auto x95 = x15 + x94;
auto x96 = V{0.166666666666667}*x13;
auto x97 = V{0.333333333333333}*x13;
auto x98 = x16*(V{3.99680288865056e-15}*cell[1] + V{1.99840144432528e-15}*cell[2] + V{2.66453525910038e-15}*cell[3] + V{4.9960036108132e-16}*cell[4] + V{4.9960036108132e-16}*cell[8] + V{1.33333333333333}*x13*x26 + V{0.666666666666667}*x13*x33 + x39*x96 + x43*x96 + x46*x97 + x49*x97 + V{3.33066907387547e-16});
auto x99 = x23 + x65 - x98 + V{2};
auto x100 = V{0.0185185185185185}*x13;
auto x101 = V{0.00925925925925926}*x13;
auto x102 = V{0.333333333333333}*cell[1] + V{0.333333333333333}*cell[3] + x101*x60 + x101*x87 + V{-0.0555555555555555};
auto x103 = V{0.666666666666667}*cell[2] - V{0.166666666666667}*cell[4] - V{0.166666666666667}*cell[8] + x100*x46 + x100*x49 + x102;
auto x104 = V{0.111111111111111}*x9;
auto x105 = -x25*x70 - x60*x68 + x72;
auto x106 = -x16*(x105 - x68*x87 - x69*x89);
auto x107 = V{0.041666625}*x11 + V{-0.1666665};
auto x108 = V{0.083333375}*x11 + V{-0.3333335};
auto x109 = V{0.0138889166666667}*x56;
auto x110 = x107*x54 - x108*x55 + x109 - V{0.333333333333333}*x14;
auto x111 = V{0.111111111111111}*x11;
auto x112 = x75 - x78;
auto x113 = -x16*(x105 - x32*x69 - x42*x68) + x67;
auto x114 = x80 + x82;
auto x115 = -V{0.166666666666667}*cell[1] + V{0.833333333333333}*cell[3] - x60*x85 + x91;
auto x116 = x15 + x52;
auto x117 = V{0.111111111111111}*x10;
auto x118 = -x34*x60 + x50 - x61;
auto x119 = x107*x55 - x108*x54 + x109 - V{0.333333333333333}*x9*(-x16*(x118 - x27*x32 - x34*x42) + V{1});
auto x120 = V{0.037037037037037}*x13;
auto x121 = -V{0.333333333333333}*cell[2] + V{0.333333333333333}*cell[4] + V{0.333333333333333}*cell[8] + x102 - V{0.037037037037037}*x13*x89;
auto x122 = ((-x16*(x118 - x27*x89 - x34*x87) + 1)*(-x16*(x118 - x27*x89 - x34*x87) + 1));
auto x123 = -V{1.5}*x122;
auto x124 = V{0.0231481481481481}*x13;
auto x125 = V{0.0277777777777778}*x13;
auto x126 = x28 + V{-4};
auto x127 = x126 + x30;
auto x128 = x23 + x98 + V{-4};
auto x129 = x128 + x65;
auto x0 = -V{0.444444444444444}*x11*(x13*(x24 + x65) + V{1}) - x13*(V{1.33333333333333}*x14 + V{1.33333333333333}*x52*x9 - x53*x54 - x53*x55 + V{0.111111}*x56) + x57*(V{2.66666666666667}*cell[1] + V{1.33333333333333}*cell[2] + V{2.66666666666667}*cell[3] + V{0.666666666666667}*cell[4] + V{0.666666666666667}*cell[8] + V{0.148148148148148}*x13*x32 + x42*x58 + x58*x60 + x61 - x62 - x63 + V{0.888888888888889});
auto x1 = -(x13*(x66*(x73 + V{-3}) - x74*(x79 + V{-6}) + x83) + x57*(-x60*x84 + x92) + x93*(x13*(x47 + x99 - V{4.5}*((x95)*(x95))) + V{1}));
auto x2 = -(x111*(x13*(x99 - V{4.5}*((x94)*(x94))) + V{1}) - x13*(x104*(x106 + V{3}) + x110) + x57*(x103 - V{0.037037037037037}*x13*x89));
auto x3 = -(x13*(x114 - x66*(x113 + V{3}) - x74*(x112 + V{6})) + x57*(x115 - x84*x87) + x93*(x13*(x36 + x99 - V{4.5}*((x116)*(x116))) + V{1}));
auto x4 = x111*(x13*(x123 + x48) + V{-1}) + x13*(x117*(x75 + V{-3}) + x119) - x57*(-x120*x46 + x121 + x63);
auto x5 = -(x13*(x66*(x73 + V{-9}) - x74*(x79 + V{-12}) + x83) + x57*(x124*x60 - x125*(x127 + x36 + x59) + x92) + x93*(x13*(x129 + x36 - V{4.5}*((x95)*(x95))) + V{1}));
auto x6 = -x111*(x13*(x128 - V{3}*x64) + V{1}) + x13*(x104*(x106 + V{9}) + x110) - x57*(x103 + V{0.0740740740740741}*x13*x89 - x44*(x126 + x88));
auto x7 = -(x13*(x114 - x66*(x113 + V{9}) - x74*(x112 + V{12})) + x57*(x115 + x124*x87 - x125*(x127 + x47 + x86)) + x93*(x13*(x129 + x47 - V{4.5}*((x116)*(x116))) + V{1}));
auto x8 = x111*(x13*(x123 + x36 + x45) + V{-1}) + x13*(x117*(x75 + V{3}) + x119) - x57*(-x120*x49 + x121 + x62);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x13, V{1}*x122 + x22 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
