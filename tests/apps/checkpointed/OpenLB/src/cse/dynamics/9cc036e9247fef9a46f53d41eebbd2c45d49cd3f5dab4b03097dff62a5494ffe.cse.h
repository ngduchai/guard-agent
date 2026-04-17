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
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SaveVelocity<collision::BGK>, dynamics::DefaultCombination>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, 1>, momenta::RegularizedBoundaryStress<0, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x13 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(1);
auto x11 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x14 = parameters.template get<descriptors::OMEGA>();
auto x9 = x14 + V{-1};
auto x10 = V{0.0740740740740741}*x11;
auto x12 = V{3}*x13;
auto x15 = V{1} / (x11);
auto x16 = cell[0] + cell[4] + V{2}*cell[5] + V{2}*cell[6] + V{2}*cell[7] + cell[8] + V{1};
auto x17 = -x15*x16 + V{1};
auto x18 = x13 + x17;
auto x19 = ((x17)*(x17));
auto x20 = V{1.5}*x19;
auto x21 = x15*(V{3}*cell[0] + V{3}*cell[4] + V{6}*cell[5] + V{6}*cell[6] + V{6}*cell[7] + V{3}*cell[8] + V{3});
auto x22 = ((x13)*(x13));
auto x23 = V{1.5}*x22;
auto x24 = x23 + V{2};
auto x25 = -x21 + x24;
auto x26 = x20 + x25;
auto x27 = x12 + x26 - V{4.5}*((x18)*(x18));
auto x28 = -x12;
auto x29 = V{4.5}*((x13 + x15*x16 - 1)*(x13 + x15*x16 - 1));
auto x30 = -x29;
auto x31 = x28 + x30;
auto x32 = x26 + x31;
auto x33 = V{0.148148148148148}*x11;
auto x34 = V{3}*x19;
auto x35 = x25 - x34;
auto x36 = V{0.444444444444444}*x11;
auto x37 = x23 + V{-1};
auto x38 = x20 + x37;
auto x39 = x36*x38;
auto x40 = ((x17)*(x17));
auto x41 = V{1.5}*x40;
auto x42 = V{3}*x22 + V{1};
auto x43 = -x41 + x42;
auto x44 = x12 + x43;
auto x45 = x10*x44;
auto x46 = x28 + x43;
auto x47 = x10*x46;
auto x48 = V{0.666666666666667}*cell[4] + V{2.66666666666667}*cell[5] + V{1.33333333333333}*cell[6] + V{2.66666666666667}*cell[7] + V{0.666666666666667}*cell[8] + V{0.888888888888889};
auto x49 = V{0.111111111111111}*x11;
auto x50 = -x20;
auto x51 = x42 + x50;
auto x52 = x12 + x51;
auto x53 = x28 + x51;
auto x54 = -x38;
auto x55 = x36*x54;
auto x56 = V{0.222222222222222}*x11;
auto x57 = x21 - x23 + V{-2};
auto x58 = x34 + x57;
auto x59 = V{0.0555555555555555}*x11;
auto x60 = x12 + x29 + x50 + x57;
auto x61 = -x27;
auto x62 = V{1.66533453693773e-16}*cell[4] + V{1.33226762955019e-15}*cell[5] + V{6.66133814775094e-16}*cell[6] + V{8.88178419700125e-16}*cell[7] + V{1.66533453693773e-16}*cell[8] + V{1.11022302462516e-16};
auto x63 = x15*(x49*x52 + x49*x53 + x55 + x56*x58 + x59*x60 + x59*x61 + x62);
auto x64 = x63 + V{-1};
auto x65 = ((x64)*(x64));
auto x66 = V{1.5}*x65;
auto x67 = V{0.444444444444444}*x14*(x11*(x37 + x66) + V{1});
auto x68 = V{0.0231481481481481}*x11;
auto x69 = x41 - V{4.5}*((x18)*(x18));
auto x70 = x12 + x25 + x69;
auto x71 = V{0.0277777777777778}*x11;
auto x72 = x23 + V{-4};
auto x73 = x21 + x72;
auto x74 = V{0.00462962962962963}*x11;
auto x75 = x25 + x31 + x41;
auto x76 = V{0.0185185185185185}*x11;
auto x77 = x25 - V{3}*x40;
auto x78 = V{0.00925925925925926}*x11;
auto x79 = V{0.0833333333333333}*cell[4] + V{0.166666666666667}*cell[6] + V{0.0833333333333333}*cell[8] - x44*x78 - x46*x78 + V{0.0277777777777778};
auto x80 = x76*x77 + x79;
auto x81 = V{0.833333333333333}*cell[5] - V{0.166666666666667}*cell[7];
auto x82 = -x74*x75 + x80 + x81;
auto x83 = V{0.0277777777777778}*x14;
auto x84 = V{1} - x63;
auto x85 = x13 + x84;
auto x86 = V{0.166666666666667}*x11;
auto x87 = V{0.333333333333333}*x11;
auto x88 = x15*(V{4.9960036108132e-16}*cell[4] + V{3.99680288865056e-15}*cell[5] + V{1.99840144432528e-15}*cell[6] + V{2.66453525910038e-15}*cell[7] + V{4.9960036108132e-16}*cell[8] + V{1.33333333333333}*x11*x54 + V{0.666666666666667}*x11*x58 + x52*x87 + x53*x87 + x60*x86 + x61*x86 + V{3.33066907387547e-16});
auto x89 = x66 + x72 + x88;
auto x90 = V{0.0185185185185185}*x11;
auto x91 = -V{0.166666666666667}*cell[4] + V{0.666666666666667}*cell[6] - V{0.166666666666667}*cell[8] + x44*x90 + x46*x90;
auto x92 = V{0.00925925925925926}*x11;
auto x93 = V{0.333333333333333}*cell[5] + V{0.333333333333333}*cell[7] + V{-0.0555555555555555};
auto x94 = x27*x92 + x32*x92 + x93;
auto x95 = x91 + x94;
auto x96 = V{0.111111111111111}*x14;
auto x97 = ((x84)*(x84));
auto x98 = -V{0.166666666666667}*cell[5] + V{0.833333333333333}*cell[7];
auto x99 = -x70*x74 + x80 + x98;
auto x100 = x13 + x64;
auto x101 = V{0.037037037037037}*x11;
auto x102 = V{0.333333333333333}*cell[4] - V{0.333333333333333}*cell[6] + V{0.333333333333333}*cell[8];
auto x103 = -x101*x44 + x102 + x47;
auto x104 = V{0.037037037037037}*x11;
auto x105 = x70*x92 + x75*x92 + x93;
auto x106 = -x104*x77 + x105;
auto x107 = ((-x15*(-x27*x59 - x32*x59 - x35*x56 - x39 + x44*x49 + x46*x49 + x62) + 1)*(-x15*(-x27*x59 - x32*x59 - x35*x56 - x39 + x44*x49 + x46*x49 + x62) + 1));
auto x108 = -V{1.5}*x107 + x42;
auto x109 = V{0.00462962962962963}*x11;
auto x110 = x24 - x88;
auto x111 = x110 + x66;
auto x112 = x11*(x111 + x12 - V{4.5}*((x85)*(x85))) + V{1};
auto x113 = V{0.037037037037037}*x11;
auto x114 = x11*(x110 - V{3}*x65) + V{1};
auto x115 = x11*(x111 + x28 - V{4.5}*((x100)*(x100))) + V{1};
auto x116 = -x101*x46 + x102 + x45;
auto x117 = -x104*x35 + x94;
auto x118 = V{2}*x14 + V{-2};
auto x119 = x35*x76 + x79;
auto x120 = V{0.0555555555555556}*x14;
auto x121 = x42 - V{1.5}*x97;
cell[0] = -x67 + x9*(x10*x27 + x10*x32 + x33*x35 + x39 - x45 - x47 + x48);
cell[1] = -(x83*(x11*(x28 + x89 - V{4.5}*((x85)*(x85))) + V{1}) + x9*(x68*x70 - x71*(x28 + x69 + x73) + x82));
cell[2] = x9*(-V{0.0740740740740741}*x11*x35 + V{0.111111111111111}*x11*(x20 - V{4.5}*x40 + x73) - x95) - x96*(x11*(x89 - V{4.5}*x97) + V{1});
cell[3] = -(x83*(x11*(x12 + x89 - V{4.5}*((x100)*(x100))) + V{1}) + x9*(x68*x75 - x71*(x12 + x30 + x41 + x73) + x99));
cell[4] = -x9*(x103 + x106) + x96*(x11*(x108 + x28) + V{-1});
cell[5] = -x112*x83 - x9*(-x109*x70 + x82);
cell[6] = -x114*x96 - x9*(x105 - x113*x77 + x91);
cell[7] = -x115*x83 - x9*(-x109*x75 + x99);
cell[8] = -x9*(x106 + x116) + x96*(x11*(x108 + x12) + V{-1});
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[0] = V{1}*x15*(-x112*x120 - V{0.222222222222222}*x114*x14 - x115*x120 - x118*(-x113*x35 + x95) - x118*(-x109*x27 + x119 - x32*x74 + x81) - x118*(-x109*x32 + x119 - x27*x74 + x98) + V{0.111111111111111}*x14*(x11*(x12 + x121) + V{-1}) + V{0.111111111111111}*x14*(x11*(x121 + x28) + V{-1}) - x67 - x9*(x103 + x117) - x9*(x116 + x117) + x9*(-x10*x52 - x10*x53 - x10*x60 - x10*x61 - x33*x58 + x48 - x55) + V{1}) + V{-1};
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[1] = x13;
return { x11, V{1}*x107 + x22 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
