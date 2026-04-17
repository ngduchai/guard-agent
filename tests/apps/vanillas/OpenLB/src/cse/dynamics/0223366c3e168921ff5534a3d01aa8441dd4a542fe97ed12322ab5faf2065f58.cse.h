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
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::ParameterFromCell<descriptors::OMEGA, collision::BGK>, forcing::Wagner>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, 1>, momenta::RegularizedBoundaryStress<0, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x13 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x15 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(1);
auto x11 = cell.template getFieldComponent<olb::descriptors::OMEGA>(0);
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x12 = cell.template getFieldComponent<olb::descriptors::SCALAR>(0);
auto x14 = V{0.1666665}*x11 + V{-0.666666};
auto x16 = ((x10)*(x10));
auto x17 = ((x9)*(x9));
auto x18 = V{1} / (x13);
auto x19 = V{0.444444444444444}*x13;
auto x20 = cell[0] + cell[4] + V{2}*cell[5] + V{2}*cell[6] + V{2}*cell[7] + cell[8] + V{1};
auto x21 = -x18*x20 + V{1};
auto x22 = ((x21)*(x21));
auto x23 = V{1.5}*x22;
auto x24 = ((x15)*(x15));
auto x25 = V{1.5}*x24;
auto x26 = x25 + V{-1};
auto x27 = x23 + x26;
auto x28 = x19*x27;
auto x29 = V{0.222222222222222}*x13;
auto x30 = V{3}*x22;
auto x31 = x18*(V{3}*cell[0] + V{3}*cell[4] + V{6}*cell[5] + V{6}*cell[6] + V{6}*cell[7] + V{3}*cell[8] + V{3});
auto x32 = x25 + V{2};
auto x33 = -x31 + x32;
auto x34 = -x30 + x33;
auto x35 = V{0.0555555555555555}*x13;
auto x36 = V{3}*x15;
auto x37 = x15 + x21;
auto x38 = x23 + x33;
auto x39 = x36 + x38 - V{4.5}*((x37)*(x37));
auto x40 = -x36;
auto x41 = V{4.5}*((x15 + x18*x20 - 1)*(x15 + x18*x20 - 1));
auto x42 = -x41;
auto x43 = x40 + x42;
auto x44 = x38 + x43;
auto x45 = V{0.111111111111111}*x13;
auto x46 = ((x21)*(x21));
auto x47 = V{1.5}*x46;
auto x48 = V{3}*x24 + V{1};
auto x49 = -x47 + x48;
auto x50 = x36 + x49;
auto x51 = x40 + x49;
auto x52 = V{1.66533453693773e-16}*cell[4] + V{1.33226762955019e-15}*cell[5] + V{6.66133814775094e-16}*cell[6] + V{8.88178419700125e-16}*cell[7] + V{1.66533453693773e-16}*cell[8] + V{1.11022302462516e-16};
auto x53 = x45*x50 + x45*x51 + x52;
auto x54 = -x18*(-x28 - x29*x34 - x35*x39 - x35*x44 + x53) + V{1};
auto x55 = x11 + V{-1};
auto x56 = V{0.0740740740740741}*x13;
auto x57 = x50*x56;
auto x58 = x51*x56;
auto x59 = -x23;
auto x60 = x48 + x59;
auto x61 = x36 + x60;
auto x62 = x40 + x60;
auto x63 = -x27;
auto x64 = -x25 + x31 + V{-2};
auto x65 = x30 + x64;
auto x66 = x36 + x41 + x59 + x64;
auto x67 = -x39;
auto x68 = x18*(x19*x63 + x29*x65 + x35*x66 + x35*x67 + x45*x61 + x45*x62 + x52);
auto x69 = x68 + V{-1};
auto x70 = ((x69)*(x69));
auto x71 = V{1.5}*x70;
auto x72 = V{0.0277777777777778}*x9;
auto x73 = V{9}*x15;
auto x74 = V{0.333333333333333}*x13;
auto x75 = V{1.33333333333333}*x13;
auto x76 = V{0.666666666666667}*x13;
auto x77 = V{2.66666666666667}*x13;
auto x78 = V{9.99200722162641e-16}*cell[4] + V{7.99360577730113e-15}*cell[5] + V{3.99680288865056e-15}*cell[6] + V{5.32907051820075e-15}*cell[7] + V{9.99200722162641e-16}*cell[8] + V{6.66133814775094e-16};
auto x79 = -x18*(x61*x76 + x62*x76 + x63*x77 + x65*x75 + x66*x74 + x67*x74 + x78);
auto x80 = x79 + V{9};
auto x81 = V{0.0277777777777778}*x10;
auto x82 = V{6}*x15;
auto x83 = V{1}*x13;
auto x84 = V{0.5}*x13;
auto x85 = x18*(V{1.49880108324396e-15}*cell[4] + V{1.19904086659517e-14}*cell[5] + V{5.99520433297585e-15}*cell[6] + V{7.99360577730113e-15}*cell[7] + V{1.49880108324396e-15}*cell[8] - V{4}*x13*x27 - V{2}*x13*x34 - x39*x84 - x44*x84 + x50*x83 + x51*x83 + V{9.99200722162641e-16});
auto x86 = x82 - x85;
auto x87 = V{0.25}*x10*x9*(V{0.25}*x11 + V{-1});
auto x88 = V{0.02083334375}*x11 + V{-0.083333375};
auto x89 = x11*x12*x18;
auto x90 = x16*x88 + x17*x88 - V{0.0138888958333333}*x89;
auto x91 = -x87 + x90;
auto x92 = V{0.0231481481481481}*x13;
auto x93 = x47 - V{4.5}*((x37)*(x37));
auto x94 = x33 + x36 + x93;
auto x95 = V{0.0277777777777778}*x13;
auto x96 = x25 + V{-4};
auto x97 = x31 + x96;
auto x98 = V{0.00462962962962963}*x13;
auto x99 = x33 + x43 + x47;
auto x100 = x33 - V{3}*x46;
auto x101 = V{0.00925925925925926}*x13;
auto x102 = V{0.0833333333333333}*cell[4] + V{0.166666666666667}*cell[6] + V{0.0833333333333333}*cell[8] + V{0.0185185185185185}*x100*x13 - x101*x50 - x101*x51 + V{0.0277777777777778};
auto x103 = V{0.833333333333333}*cell[5] - V{0.166666666666667}*cell[7] + x102 - x98*x99;
auto x104 = V{0.0277777777777778}*x11;
auto x105 = V{1} - x68;
auto x106 = x105 + x15;
auto x107 = V{0.166666666666667}*x13;
auto x108 = V{0.333333333333333}*x13;
auto x109 = x18*(V{4.9960036108132e-16}*cell[4] + V{3.99680288865056e-15}*cell[5] + V{1.99840144432528e-15}*cell[6] + V{2.66453525910038e-15}*cell[7] + V{4.9960036108132e-16}*cell[8] + x107*x66 + x107*x67 + x108*x61 + x108*x62 + V{1.33333333333333}*x13*x63 + V{0.666666666666667}*x13*x65 + V{3.33066907387547e-16});
auto x110 = x109 + x71 + x96;
auto x111 = V{0.111111111111111}*x9;
auto x112 = V{0.083333375}*x11 + V{-0.3333335};
auto x113 = V{0.041666625}*x11 + V{-0.1666665};
auto x114 = V{0.0138889166666667}*x89;
auto x115 = V{0.333333333333333}*x10*x15 + x112*x17 - x113*x16 - x114;
auto x116 = V{0.00925925925925926}*x13;
auto x117 = V{0.333333333333333}*cell[5] + V{0.333333333333333}*cell[7] + V{-0.0555555555555555};
auto x118 = V{0.0185185185185185}*x13;
auto x119 = -V{0.166666666666667}*cell[4] + V{0.666666666666667}*cell[6] - V{0.166666666666667}*cell[8] + x118*x50 + x118*x51;
auto x120 = V{0.111111111111111}*x11;
auto x121 = x82 + x85;
auto x122 = x18*(-x27*x77 - x34*x75 - x39*x74 - x44*x74 + x50*x76 + x51*x76 + x78) + x73;
auto x123 = x87 + x90;
auto x124 = -V{0.166666666666667}*cell[5] + V{0.833333333333333}*cell[7] + x102 - x94*x98;
auto x125 = x15 + x69;
auto x126 = V{0.111111111111111}*x10;
auto x127 = -x112*x16 + x113*x17 + x114 + V{0.333333333333333}*x9*(-x18*(-x100*x29 - x19*(x26 + x47) - x35*x94 - x35*x99 + x53) + V{1});
auto x128 = V{0.037037037037037}*x13;
auto x129 = x116*x94 + x116*x99 + x117;
auto x130 = V{0.333333333333333}*cell[4] - V{0.333333333333333}*cell[6] + V{0.333333333333333}*cell[8] - V{0.037037037037037}*x100*x13 + x129;
auto x131 = ((x54)*(x54));
auto x132 = -V{1.5}*x131 + x48;
auto x133 = x79 + V{3};
auto x134 = V{0.00462962962962963}*x13;
auto x135 = -x109 + x32;
auto x136 = x135 + x71;
auto x0 = -V{0.444444444444444}*x11*(x13*(x26 + x71) + V{1}) - x13*(V{1.33333333333333}*x10*x15 + V{0.111111}*x11*x12*x18 - x14*x16 - x14*x17 - V{1.33333333333333}*x54*x9) + x55*(V{0.666666666666667}*cell[4] + V{2.66666666666667}*cell[5] + V{1.33333333333333}*cell[6] + V{2.66666666666667}*cell[7] + V{0.666666666666667}*cell[8] + V{0.148148148148148}*x13*x34 + x28 + x39*x56 + x44*x56 - x57 - x58 + V{0.888888888888889});
auto x1 = -(x104*(x13*(x110 + x40 - V{4.5}*((x106)*(x106))) + V{1}) + x13*(x72*(x73 + x80) - x81*(x86 + V{12}) + x91) + x55*(x103 + x92*x94 - x95*(x40 + x93 + x97)));
auto x2 = -(x120*(x13*(x110 - V{4.5}*((x105)*(x105))) + V{1}) + x13*(x111*x80 + x115) - x55*(-x116*x39 - x116*x44 - x117 - x119 - V{0.0740740740740741}*x13*x34 + V{0.111111111111111}*x13*(x23 - V{4.5}*x46 + x97)));
auto x3 = -(x104*(x13*(x110 + x36 - V{4.5}*((x125)*(x125))) + V{1}) + x13*(x123 - x72*(x122 + V{-9}) - x81*(x121 + V{-12})) + x55*(x124 + x92*x99 - x95*(x36 + x42 + x47 + x97)));
auto x4 = x120*(x13*(x132 + x40) + V{-1}) + x13*(x126*(x82 + V{-3}) + x127) - x55*(-x128*x50 + x130 + x58);
auto x5 = -(x104*(x13*(x136 + x36 - V{4.5}*((x106)*(x106))) + V{1}) + x13*(x72*(x133 + x73) - x81*(x86 + V{6}) + x91) + x55*(x103 - x134*x94));
auto x6 = -x120*(x13*(x135 - V{3}*x70) + V{1}) - x13*(x111*x133 + x115) - x55*(-V{0.037037037037037}*x100*x13 + x119 + x129);
auto x7 = -(x104*(x13*(x136 + x40 - V{4.5}*((x125)*(x125))) + V{1}) + x13*(x123 - x72*(x122 + V{-3}) - x81*(x121 + V{-6})) + x55*(x124 - x134*x99));
auto x8 = x120*(x13*(x132 + x36) + V{-1}) + x13*(x126*(x82 + V{3}) + x127) - x55*(-x128*x51 + x130 + x57);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x13, V{1}*x131 + x24 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
