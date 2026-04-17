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
struct CSE<CombinedRLBdynamics<T, descriptors::D2Q9<FIELDS...>, dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SaveVelocity<collision::BGK>, dynamics::DefaultCombination>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, -1>, momenta::RegularizedBoundaryStress<0, -1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x13 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, -1>::VELOCITY>(1);
auto x11 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x14 = parameters.template get<descriptors::OMEGA>();
auto x9 = x14 + V{-1};
auto x10 = V{0.0740740740740741}*x11;
auto x12 = V{1} / (x11);
auto x15 = x12*(cell[0] + V{2}*cell[1] + V{2}*cell[2] + V{2}*cell[3] + cell[4] + cell[8] + V{1});
auto x16 = V{1} - x15;
auto x17 = x13 + x16;
auto x18 = V{3}*x13;
auto x19 = x12*(V{3}*cell[0] + V{6}*cell[1] + V{6}*cell[2] + V{6}*cell[3] + V{3}*cell[4] + V{3}*cell[8] + V{3});
auto x20 = V{2} - x19;
auto x21 = ((x13)*(x13));
auto x22 = V{1.5}*x21;
auto x23 = ((x16)*(x16));
auto x24 = V{1.5}*x23;
auto x25 = x22 + x24;
auto x26 = x20 + x25;
auto x27 = x18 + x26;
auto x28 = x27 - V{4.5}*((x17)*(x17));
auto x29 = -x18;
auto x30 = V{4.5}*((x13 + x15 - 1)*(x13 + x15 - 1));
auto x31 = -x30;
auto x32 = x26 + x29 + x31;
auto x33 = x26 - V{4.5}*((x16)*(x16));
auto x34 = V{0.444444444444444}*x11;
auto x35 = x22 + V{-1};
auto x36 = x24 + x35;
auto x37 = x34*x36;
auto x38 = V{3}*x21 + V{1};
auto x39 = -x24;
auto x40 = x18 + x39;
auto x41 = x38 + x40;
auto x42 = x10*x41;
auto x43 = x29 + x38;
auto x44 = x39 + x43;
auto x45 = x10*x44;
auto x46 = V{2.66666666666667}*cell[1] + V{1.33333333333333}*cell[2] + V{2.66666666666667}*cell[3] + V{0.666666666666667}*cell[4] + V{0.666666666666667}*cell[8] + x10*x28 + x10*x32 + V{0.148148148148148}*x11*x33 + x37 - x42 - x45 + V{0.888888888888889};
auto x47 = -x36;
auto x48 = V{0.222222222222222}*x11;
auto x49 = -x33;
auto x50 = V{0.0555555555555555}*x11;
auto x51 = x19 - x22 + x30 + x40 + V{-2};
auto x52 = -x28;
auto x53 = V{0.111111111111111}*x11;
auto x54 = V{1.33226762955019e-15}*cell[1] + V{6.66133814775094e-16}*cell[2] + V{8.88178419700125e-16}*cell[3] + V{1.66533453693773e-16}*cell[4] + V{1.66533453693773e-16}*cell[8] + x41*x53 + x44*x53 + V{1.11022302462516e-16};
auto x55 = x12*(x34*x47 + x48*x49 + x50*x51 + x50*x52 + x54);
auto x56 = V{1} - x55;
auto x57 = ((x56)*(x56));
auto x58 = V{1.5}*x57;
auto x59 = V{0.444444444444444}*x14*(x11*(x35 + x58) + V{1});
auto x60 = V{0.00462962962962963}*x11;
auto x61 = V{0.00462962962962963}*x11;
auto x62 = -V{4.5}*((x17)*(x17));
auto x63 = x27 + x62;
auto x64 = x22 - V{3}*x23;
auto x65 = x20 + x64;
auto x66 = V{0.00925925925925926}*x11;
auto x67 = V{0.166666666666667}*cell[2] + V{0.0833333333333333}*cell[4] + V{0.0833333333333333}*cell[8] + V{0.0185185185185185}*x11*x65 - x41*x66 - x44*x66 + V{0.0277777777777778};
auto x68 = V{0.833333333333333}*cell[1] - V{0.166666666666667}*cell[3] - x61*x63 + x67;
auto x69 = -x32*x60 + x68;
auto x70 = V{0.0277777777777778}*x14;
auto x71 = x55 + V{-1};
auto x72 = x13 + x71;
auto x73 = V{0.166666666666667}*x11;
auto x74 = V{0.333333333333333}*x11;
auto x75 = x12*(V{3.99680288865056e-15}*cell[1] + V{1.99840144432528e-15}*cell[2] + V{2.66453525910038e-15}*cell[3] + V{4.9960036108132e-16}*cell[4] + V{4.9960036108132e-16}*cell[8] + V{1.33333333333333}*x11*x47 + V{0.666666666666667}*x11*x49 + x41*x74 + x44*x74 + x51*x73 + x52*x73 + V{3.33066907387547e-16});
auto x76 = x22 + x58 - x75 + V{2};
auto x77 = x11*(x29 + x76 - V{4.5}*((x72)*(x72))) + V{1};
auto x78 = V{0.0185185185185185}*x11;
auto x79 = V{0.00925925925925926}*x11;
auto x80 = V{0.333333333333333}*cell[1] + V{0.333333333333333}*cell[3] + x32*x79 + x63*x79 + V{-0.0555555555555555};
auto x81 = V{0.666666666666667}*cell[2] - V{0.166666666666667}*cell[4] - V{0.166666666666667}*cell[8] + x41*x78 + x44*x78 + x80;
auto x82 = -V{0.037037037037037}*x11*x65 + x81;
auto x83 = V{0.111111111111111}*x14;
auto x84 = x11*(x76 - V{4.5}*((x71)*(x71))) + V{1};
auto x85 = -V{0.166666666666667}*cell[1] + V{0.833333333333333}*cell[3] - x32*x61 + x67;
auto x86 = -x60*x63 + x85;
auto x87 = x13 + x56;
auto x88 = x11*(x18 + x76 - V{4.5}*((x87)*(x87))) + V{1};
auto x89 = V{0.037037037037037}*x11;
auto x90 = -V{0.333333333333333}*cell[2] + V{0.333333333333333}*cell[4] + V{0.333333333333333}*cell[8] - V{0.037037037037037}*x11*x65 + x80;
auto x91 = x9*(-x41*x89 + x45 + x90);
auto x92 = ((-x12*(-x32*x50 - x37 - x48*x65 - x50*x63 + x54) + 1)*(-x12*(-x32*x50 - x37 - x48*x65 - x50*x63 + x54) + 1));
auto x93 = -V{1.5}*x92;
auto x94 = x11*(x43 + x93) + V{-1};
auto x95 = V{0.0231481481481481}*x11;
auto x96 = V{0.0277777777777778}*x11;
auto x97 = x19 + V{-4};
auto x98 = x25 + x97;
auto x99 = x22 + x75 + V{-4};
auto x100 = x58 + x99;
auto x101 = x9*(x42 - x44*x89 + x90);
auto x102 = x11*(x18 + x38 + x93) + V{-1};
auto x103 = V{2}*x14 + V{-2};
auto x104 = V{0.0555555555555556}*x14;
cell[0] = x46*x9 - x59;
cell[1] = -x69*x9 - x70*x77;
cell[2] = -x82*x9 - x83*x84;
cell[3] = -x70*x88 - x86*x9;
cell[4] = x83*x94 - x91;
cell[5] = -(x70*(x11*(x100 + x18 - V{4.5}*((x72)*(x72))) + V{1}) + x9*(x32*x95 + x68 - x96*(x18 + x31 + x98)));
cell[6] = -x83*(x11*(-V{3}*x57 + x99) + V{1}) - x9*(V{0.0740740740740741}*x11*x65 - x53*(x64 + x97) + x81);
cell[7] = -(x70*(x11*(x100 + x29 - V{4.5}*((x87)*(x87))) + V{1}) + x9*(x63*x95 + x85 - x96*(x29 + x62 + x98)));
cell[8] = -x101 + x102*x83;
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[0] = -V{1}*x12*(-x101 + V{0.111111111111111}*x102*x14 - x103*x69 - x103*x82 - x103*x86 - x104*x77 - x104*x88 - V{0.222222222222222}*x14*x84 + V{0.111111111111111}*x14*x94 + x46*x9 - x59 - x91 + V{1}) + V{1};
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[1] = x13;
return { x11, x21 + V{1}*x92 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
