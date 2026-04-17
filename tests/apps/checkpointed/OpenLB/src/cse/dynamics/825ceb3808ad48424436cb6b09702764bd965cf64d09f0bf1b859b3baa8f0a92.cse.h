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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 1, -1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{-1};
auto x27 = x22*x25;
auto x28 = -x24;
auto x29 = V{3}*x20;
auto x30 = x29 + V{1};
auto x31 = x28 + x30;
auto x32 = V{0.00925925925925926}*x22;
auto x33 = x31*x32;
auto x34 = V{0.333333333333333}*cell[5] - x33;
auto x35 = V{0.333333333333333}*cell[4];
auto x36 = x25 + x29;
auto x37 = x32*x36 + x35;
auto x38 = V{3}*x21;
auto x39 = x38 + V{1};
auto x40 = x28 + x39;
auto x41 = x32*x40;
auto x42 = V{0.333333333333333}*cell[7] - x41 + V{0.0462962962962963};
auto x43 = V{0.166666666666667}*cell[6];
auto x44 = V{0.166666666666667}*cell[15];
auto x45 = x24 + x39;
auto x46 = V{0.00462962962962963}*x22;
auto x47 = x45*x46;
auto x48 = x25 + x38;
auto x49 = x43 - x44 + x46*x48 + x47;
auto x50 = x23*(V{0.333333333333333}*cell[1] + V{0.0185185185185185}*x27 + x34 + x37 + x42 + x49);
auto x51 = V{0.166666666666667}*cell[2];
auto x52 = x29 + V{-1};
auto x53 = -x52;
auto x54 = -x36;
auto x55 = x30*x32;
auto x56 = x30 + x38;
auto x57 = x32*x56;
auto x58 = V{0.333333333333333}*cell[17] - x57;
auto x59 = V{0.333333333333333}*cell[9];
auto x60 = -x29;
auto x61 = x39 + x60;
auto x62 = x32*x61;
auto x63 = -x59 + x62;
auto x64 = V{0.0555555555555556}*x22;
auto x65 = V{0.0185185185185185}*x22*x39;
auto x66 = x59 - x62;
auto x67 = -x48;
auto x68 = -x43 + x44 + x46*x67 - x47;
auto x69 = V{0.166666666666667}*cell[1];
auto x70 = V{0.166666666666667}*cell[9];
auto x71 = x25*x32;
auto x72 = x46*x61;
auto x73 = -x72;
auto x74 = x69 + x70 + x71 + x73;
auto x75 = V{0.166666666666667}*cell[17];
auto x76 = x46*x56;
auto x77 = -x75 + x76;
auto x78 = V{0.0833333333333333}*cell[6];
auto x79 = V{0.0833333333333333}*cell[15];
auto x80 = -x79;
auto x81 = V{0.00231481481481481}*x22;
auto x82 = x45*x81;
auto x83 = x48*x81;
auto x84 = x40*x46;
auto x85 = V{0.166666666666667}*cell[7] - x84 + V{0.0231481481481481};
auto x86 = x78 + x80 + x82 + x83 + x85;
auto x87 = V{0.0833333333333333}*cell[2];
auto x88 = V{0.0833333333333333}*cell[11];
auto x89 = x30*x46;
auto x90 = x46*x52;
auto x91 = x87 - x88 + x89 + x90;
auto x92 = x23*(x37 + x74 + x77 + x86 + x91);
auto x93 = V{0.0277777777777778}*x22;
auto x94 = x75 - x76;
auto x95 = x69 - x70 + x71 + x72;
auto x96 = -x87 + x88 - x89;
auto x97 = x23*(x34 + x86 - x90 + x94 + x95 + x96);
auto x98 = V{0.166666666666667}*cell[4];
auto x99 = x46*x54 - x98;
auto x100 = V{0.166666666666667}*cell[12];
auto x101 = x32*x39;
auto x102 = -x101;
auto x103 = V{0.166666666666667}*cell[5];
auto x104 = x31*x46;
auto x105 = -x103 + x104;
auto x106 = x100 + x102 + x105;
auto x107 = x36*x46 + x98;
auto x108 = -x104;
auto x109 = x100 + x102 + x103 + x108;
auto x110 = x23*(x107 + x109 + x42 + x74 + x94);
auto x111 = -x78 + x79 - x82 + x85;
auto x112 = x23*(x106 + x107 + x111 + x66 - x83 + x91);
auto x113 = x24 + V{1};
auto x114 = -V{0.333333333333333}*cell[17] + x57;
auto x115 = -V{0.166666666666667}*cell[12] + x101 + x107;
auto x116 = -x38;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x27 - x50 + V{-0.0555555555555556};
cell[2] = x23*(V{0.166666666666667}*cell[11] + x32*x53 + x32*x54 + x34 - x35 - x51 - x55 + x58 + x63) - x52*x64 + V{-0.0555555555555556};
cell[3] = x23*(V{0.333333333333333}*cell[12] + x42 + x58 - x65 + x66 + x68) - x64*(x38 + V{-1}) + V{-0.0555555555555556};
cell[4] = -x36*x93 - x92 + V{-0.0277777777777778};
cell[5] = V{0.0277777777777778}*x22*x31 - x97 + V{-0.0277777777777778};
cell[6] = x23*(x106 - x25*x32 + x68 - x69 + x70 + x73 + x94 + x99) - x48*x93 + V{-0.0277777777777778};
cell[7] = -x110 + V{0.0277777777777778}*x22*x40 + V{-0.0277777777777778};
cell[8] = x23*(x109 + x111 + x46*x53 + x58 + x67*x81 + x96 + x99) - x93*(x38 + x52) + V{-0.0277777777777778};
cell[9] = -x112 + V{0.0277777777777778}*x22*x61 + V{-0.0277777777777778};
cell[10] = x113*x64 + x50 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x30 - x23*(V{0.166666666666667}*cell[11] + V{0.333333333333333}*cell[5] - x114 - x32*x52 - x33 - x37 - x51 - x55 - x66) + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x39 - x23*(V{0.333333333333333}*cell[12] + V{0.333333333333333}*cell[7] - x114 - x41 - x49 - x63 - x65 + V{0.0462962962962963}) + V{-0.0555555555555556};
cell[13] = x92 + x93*(x24 + x30) + V{-0.0277777777777778};
cell[14] = x93*(x113 + x60) + x97 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x45 - x23*(-x103 - x108 - x115 - x49 - x77 - x95) + V{-0.0277777777777778};
cell[16] = x110 + x93*(x113 + x116) + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x56 - x23*(V{0.166666666666667}*cell[7] - x105 - x114 - x115 - x78 - x80 - x82 - x83 - x84 - x91 + V{0.0231481481481481}) + V{-0.0277777777777778};
cell[18] = x112 + x93*(x116 + x30) + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
