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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 1, -1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{1};
auto x27 = V{0.0185185185185185}*x22;
auto x28 = x25*x27;
auto x29 = V{3}*x20;
auto x30 = -x29;
auto x31 = x25 + x30;
auto x32 = V{0.00925925925925926}*x22;
auto x33 = x31*x32;
auto x34 = V{0.333333333333333}*cell[14] - x33 + V{0.037037037037037};
auto x35 = V{3}*x21;
auto x36 = -x35;
auto x37 = x25 + x36;
auto x38 = x32*x37;
auto x39 = V{0.333333333333333}*cell[16] - x38;
auto x40 = V{0.166666666666667}*cell[13];
auto x41 = V{0.166666666666667}*cell[4];
auto x42 = x24 + V{-1};
auto x43 = x29 + x42;
auto x44 = -x43;
auto x45 = V{0.00462962962962963}*x22;
auto x46 = x25 + x29;
auto x47 = x45*x46;
auto x48 = x40 - x41 + x44*x45 - x47;
auto x49 = V{0.166666666666667}*cell[15];
auto x50 = V{0.166666666666667}*cell[6];
auto x51 = x35 + x42;
auto x52 = -x51;
auto x53 = x25 + x35;
auto x54 = x45*x53;
auto x55 = x45*x52 + x49 - x50 - x54;
auto x56 = V{0.0555555555555556}*x22;
auto x57 = V{0.166666666666667}*cell[9];
auto x58 = V{0.166666666666667}*cell[18];
auto x59 = x29 + V{1};
auto x60 = x36 + x59;
auto x61 = x45*x60;
auto x62 = x29 + V{-1};
auto x63 = x35 + V{1};
auto x64 = x30 + x63;
auto x65 = x45*x64;
auto x66 = x35 + x62;
auto x67 = V{0.333333333333333}*cell[8] + x32*x66;
auto x68 = -x40 + x41 + x43*x45 + x47;
auto x69 = x23*(V{0.333333333333333}*cell[2] + x27*x62 + x34 + x57 - x58 + x61 - x65 + x67 + x68);
auto x70 = x35 + V{-1};
auto x71 = x39 + V{0.037037037037037};
auto x72 = x45*x51 - x49 + x50 + x54;
auto x73 = -x57 + x58 - x61 + x65;
auto x74 = x23*(V{0.333333333333333}*cell[3] + x27*x70 + x67 + x71 + x72 + x73);
auto x75 = V{0.00231481481481481}*x22;
auto x76 = V{0.0833333333333333}*cell[15];
auto x77 = V{0.0833333333333333}*cell[6];
auto x78 = x53*x75;
auto x79 = x76 - x77 - x78;
auto x80 = V{0.0833333333333333}*cell[18];
auto x81 = V{0.0833333333333333}*cell[9];
auto x82 = x64*x75;
auto x83 = x60*x75;
auto x84 = x80 - x81 + x82 - x83;
auto x85 = V{0.166666666666667}*cell[2];
auto x86 = x37*x45;
auto x87 = V{0.166666666666667}*cell[16] - x86;
auto x88 = -x85 + x87;
auto x89 = V{0.166666666666667}*cell[10];
auto x90 = x25*x32;
auto x91 = -x90;
auto x92 = V{0.166666666666667}*cell[8];
auto x93 = -x45*x66 + x89 + x91 - x92;
auto x94 = V{0.0277777777777778}*x22;
auto x95 = x51*x75;
auto x96 = x45*x66 + x92;
auto x97 = x89 + x91 + x96;
auto x98 = x32*x62;
auto x99 = x85 + x87 + x98;
auto x100 = -x80 + x81 - x82 + x83;
auto x101 = x23*(x100 + x34 + x79 - x95 + x97 + x99);
auto x102 = -x24;
auto x103 = V{0.166666666666667}*cell[14];
auto x104 = x31*x45;
auto x105 = -x104;
auto x106 = V{0.166666666666667}*cell[3];
auto x107 = V{0.0833333333333333}*cell[13];
auto x108 = V{0.0833333333333333}*cell[4];
auto x109 = x46*x75;
auto x110 = x107 - x108 - x109;
auto x111 = x32*x70;
auto x112 = x103 + x105 + x106 + x111;
auto x113 = x43*x75;
auto x114 = x110 - x113;
auto x115 = x23*(x112 + x114 + x71 + x84 + x97);
auto x116 = -x76 + x77 + x78 + x95;
auto x117 = -x107 + x108 + x109 + x113;
auto x118 = x23*(x112 + x116 + x117 + x67 + x99 + V{0.037037037037037});
auto x119 = -x103 + x104 + x106 + x111;
auto x120 = x23*(x114 + x116 + x119 + x73 + x88 - x98);
auto x121 = -V{0.166666666666667}*cell[10] + x90 + x96;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.333333333333333}*cell[10] - x28 + x34 + x39 + x48 + x55) - x42*x56 + V{-0.0555555555555556};
cell[2] = -x56*x62 - x69 + V{-0.0555555555555556};
cell[3] = -x56*x70 - x74 + V{-0.0555555555555556};
cell[4] = x23*(-x32*x62 + x48 + x52*x75 + x79 + x84 + x88 + x93) - x43*x94 + V{-0.0277777777777778};
cell[5] = x101 + x94*(x102 + x59) + V{-0.0277777777777778};
cell[6] = x23*(x100 + x103 + x105 - x106 + x110 - x32*x70 + x44*x75 + x55 + x93) - x51*x94 + V{-0.0277777777777778};
cell[7] = x115 + x94*(x102 + x63) + V{-0.0277777777777778};
cell[8] = -x118 - x66*x94 + V{-0.0277777777777778};
cell[9] = x120 + x64*x94 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x25 - x23*(V{0.333333333333333}*cell[10] + V{0.333333333333333}*cell[14] + V{0.333333333333333}*cell[16] - x28 - x33 - x38 - x68 - x72 + V{0.037037037037037}) + V{-0.0555555555555556};
cell[11] = x56*x59 + x69 + V{-0.0555555555555556};
cell[12] = x56*x63 + x74 + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x46 - x23*(V{0.166666666666667}*cell[16] - x100 - x116 - x121 - x68 - x85 - x86 - x98) + V{-0.0277777777777778};
cell[14] = -x101 + V{0.0277777777777778}*x22*x31 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x53 - x23*(-x117 - x119 - x121 - x72 - x84) + V{-0.0277777777777778};
cell[16] = -x115 + V{0.0277777777777778}*x22*x37 + V{-0.0277777777777778};
cell[17] = x118 + x94*(x35 + x59) + V{-0.0277777777777778};
cell[18] = -x120 + V{0.0277777777777778}*x22*x60 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
