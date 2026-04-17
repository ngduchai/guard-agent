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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, 1>, momenta::BulkStress, momenta::DefineSeparately>, equilibria::ThirdOrder, collision::ParameterFromCell<collision::LES::SMAGORINSKY, collision::SmagorinskyEffectiveOmega<collision::ThirdOrderRLB> >, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = cell.template getFieldComponent<olb::collision::LES::SMAGORINSKY>(0);
auto x10 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x12 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(1);
auto x13 = parameters.template get<descriptors::OMEGA>();
auto x11 = V{0.5}/x13;
auto x14 = V{0.0277777691819762}/((x13)*(x13));
auto x15 = V{1} / (x10);
auto x16 = ((x9)*(x9));
auto x17 = cell[0] + cell[4] + V{2}*cell[5] + V{2}*cell[6] + V{2}*cell[7] + cell[8] + V{1};
auto x18 = x15*x17;
auto x19 = V{1} - x18;
auto x20 = -x19;
auto x21 = x10*x12;
auto x22 = x20*x21;
auto x23 = cell[1] - cell[3] + cell[5] - cell[7] + x22;
auto x24 = V{1}*x10;
auto x25 = ((x19)*(x19));
auto x26 = V{1}*cell[1] + V{1}*cell[3] + V{1}*cell[5] + V{1}*cell[7] - V{0.333333333333333}*x10 + V{0.333333333333333};
auto x27 = V{1}*cell[2] + V{1}*cell[6] + x26;
auto x28 = -x24*x25 + x27;
auto x29 = ((x12)*(x12));
auto x30 = V{1}*cell[4] + V{1}*cell[8] - x10*x29 + x26;
auto x31 = V{0.5}*((x28)*(x28)) + V{0.5}*((x30)*(x30));
auto x32 = V{1} - V{1} / (x11 + V{3.00000046417339}*util::sqrt(x14 + x15*x16*util::sqrt(x31 + ((x23)*(x23)))));
auto x33 = V{0.444444444444444}*x10;
auto x34 = V{0.666666666666667}*x10;
auto x35 = ((x20)*(x20));
auto x36 = V{1.5}*x29;
auto x37 = V{1.5}*x35;
auto x38 = x37 + V{-1};
auto x39 = V{0.0277777777777778}*x10;
auto x40 = V{3}*x12;
auto x41 = -x40;
auto x42 = x12 + x19;
auto x43 = x29*(V{6.000012}*x15*x17 + V{-6.000012});
auto x44 = V{6.000012}*x12*x35;
auto x45 = x15*(V{3}*cell[0] + V{3}*cell[4] + V{6}*cell[5] + V{6}*cell[6] + V{6}*cell[7] + V{3}*cell[8] + V{3});
auto x46 = x36 + x45 + V{-4};
auto x47 = x37 + x46;
auto x48 = V{0.0833333333333333}*cell[3];
auto x49 = V{0.0833333333333333}*cell[7];
auto x50 = x19*x21;
auto x51 = V{0.25}*x50;
auto x52 = V{0.333334}*x23;
auto x53 = V{0.166667}*x12*x28 + x12*x52 + x19*x52 + x30*(-V{0.166667}*x15*x17 + V{0.166667});
auto x54 = V{0.0833333333333333}*cell[2];
auto x55 = V{0.0833333333333333}*cell[4];
auto x56 = V{0.0833333333333333}*cell[6];
auto x57 = V{0.0833333333333333}*cell[8];
auto x58 = V{0.0555555555555556}*x10;
auto x59 = V{0.0833333333333333}*x10;
auto x60 = x29*x59;
auto x61 = x25*x59;
auto x62 = x54 + x55 + x56 + x57 - x58 - x60 - x61 + V{0.0555555555555556};
auto x63 = V{0.111111111111111}*x10;
auto x64 = V{2.999997}*x12;
auto x65 = cell[1] - cell[3] + cell[5] - cell[7] - x50;
auto x66 = V{1} - V{1} / (x11 + V{3.00000046417339}*util::sqrt(x14 + x15*x16*util::sqrt(x31 + ((x65)*(x65)))));
auto x67 = V{0.333333}*x12*x28;
auto x68 = x19*x65;
auto x69 = x30*(-V{0.666667}*x15*x17 + V{0.666667});
auto x70 = x12*x65;
auto x71 = V{0.166666666666667}*x10;
auto x72 = V{0.333333333333333}*x10;
auto x73 = V{0.166666666666667}*cell[1] + V{0.166666666666667}*cell[3] + V{0.166666666666667}*cell[5] + V{0.166666666666667}*cell[7] - V{0.0555555555555556}*x10 + V{0.0555555555555556};
auto x74 = V{0.333333333333333}*cell[2] - V{0.166666666666667}*cell[4] + V{0.333333333333333}*cell[6] - V{0.166666666666667}*cell[8] - x25*x72 + x29*x71 + x73;
auto x75 = V{0.0833333333333333}*cell[1];
auto x76 = V{0.0833333333333333}*cell[5];
auto x77 = V{0.416666666666667}*cell[3];
auto x78 = V{0.416666666666667}*cell[7];
auto x79 = V{0.5}*x12;
auto x80 = -V{1}*x23;
auto x81 = -x54 - x55 - x56 - x57 + x58 + x60 + V{-0.0555555555555556};
auto x82 = x12 + x18 + V{-1};
auto x83 = V{18}*x12;
auto x84 = V{1.5}*x25;
auto x85 = -V{3}*x29;
auto x86 = V{6.000003}*x12;
auto x87 = V{0.666667}*x12*x28;
auto x88 = x30*(-V{0.333333}*x15*x17 + V{0.333333});
auto x89 = -V{0.166666666666667}*cell[2] + V{0.333333333333333}*cell[4] - V{0.166666666666667}*cell[6] + V{0.333333333333333}*cell[8] + x25*x71 - x29*x72 + x73;
auto x90 = x36 - x45 + V{2};
auto x91 = x12*x23;
auto x92 = x19*x23;
auto x0 = -V{1}*x32*(V{1.33333333333333}*cell[1] + V{0.666666666666667}*cell[2] + V{1.33333333333333}*cell[3] + V{0.666666666666667}*cell[4] + V{1.33333333333333}*cell[5] + V{0.666666666666667}*cell[6] + V{1.33333333333333}*cell[7] + V{0.666666666666667}*cell[8] - x29*x34 - x33 - x34*x35 + V{0.444444444444444}) - x33*(x36 + x38) + V{-0.444444444444444};
auto x1 = -(-V{1}*x32*(V{0.416666666666667}*cell[1] + V{0.416666666666667}*cell[5] - x48 - x49 - x51 + x53 + x62) + x39*(x41 + x43 - x44 + x47 - V{4.5}*((x42)*(x42))) + V{0.0277777777777778});
auto x2 = -x63*(-x25*x64 - V{3}*x25 + x29*(-V{6.000003}*x15*x17 + V{6.000003}) + x46) + V{1}*x66*(x67 + V{0.666666}*x68 - x69 - V{1.333334}*x70 + x74) + V{-0.111111111111111};
auto x3 = -(V{1}*x32*(x12*x80 + x20*x80 + V{0.25}*x22 + x30*(V{0.5}*x15*x17 + V{-0.5}) + x35*x59 + x75 + x76 - x77 - x78 + x79*(-x24*x35 + x27) + x81) + x39*(x29*(V{18}*x15*x17 + V{-18}) + x35*x83 + x40 + x47 - V{4.5}*((x82)*(x82))) + V{0.0277777777777778});
auto x4 = -x63*(-x25*x86 + x29*(-V{2.999997}*x15*x17 + V{2.999997}) + x40 + x84 + x85 + V{-1}) + V{1}*x66*(V{1.333334}*x68 - V{0.666666}*x70 + x87 - x88 + x89) + V{-0.111111111111111};
auto x5 = -(-V{1}*x32*(V{0.416666666666667}*cell[1] + V{0.416666666666667}*cell[5] - x48 - x49 - x51 - x53 - x61 - x81) + x39*(x37 + x40 - x43 + x44 + x90 - V{4.5}*((x42)*(x42))) + V{0.0277777777777778});
auto x6 = V{1}*x32*(-x67 + x69 + x74 + V{1.333334}*x91 - V{0.666666}*x92) - x63*(x29*(V{6.000003}*x15*x17 + V{-6.000003}) + x35*x64 - V{3}*x35 + x90) + V{-0.111111111111111};
auto x7 = -(x39*(-x25*x83 + x29*(-V{18}*x15*x17 + V{18}) + x41 + x84 + x90 - V{4.5}*((x82)*(x82))) - V{1}*x66*(x28*x79 - x30*(-V{0.5}*x15*x17 + V{0.5}) + x51 + x62 + V{1}*x68 - V{1}*x70 - x75 - x76 + x77 + x78) + V{0.0277777777777778});
auto x8 = V{1}*x32*(-x87 + x88 + x89 + V{0.666666}*x91 - V{1.333334}*x92) - x63*(x29*(V{2.999997}*x15*x17 + V{-2.999997}) + x35*x86 + x38 + x41 + x85) + V{-0.111111111111111};
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x10, V{1}*x25 + x29 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
