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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 2, -1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{-1};
auto x27 = x22*x25;
auto x28 = -x24;
auto x29 = V{3}*x21;
auto x30 = x29 + V{1};
auto x31 = x28 + x30;
auto x32 = V{0.00925925925925926}*x22;
auto x33 = x31*x32;
auto x34 = V{0.333333333333333}*cell[7] - x33;
auto x35 = V{0.333333333333333}*cell[6];
auto x36 = x25 + x29;
auto x37 = x32*x36 + x35;
auto x38 = V{3}*x20;
auto x39 = x38 + V{1};
auto x40 = x28 + x39;
auto x41 = x32*x40;
auto x42 = V{0.333333333333333}*cell[5] - x41;
auto x43 = V{0.166666666666667}*cell[4];
auto x44 = V{0.166666666666667}*cell[13];
auto x45 = x24 + x39;
auto x46 = V{0.00462962962962963}*x22;
auto x47 = x45*x46;
auto x48 = x25 + x38;
auto x49 = x43 - x44 + x46*x48 + x47;
auto x50 = x23*(V{0.333333333333333}*cell[1] + V{0.0185185185185185}*x27 + x34 + x37 + x42 + x49 + V{0.0462962962962963});
auto x51 = -x48;
auto x52 = V{0.0185185185185185}*x22*x39;
auto x53 = x29 + x39;
auto x54 = x32*x53;
auto x55 = V{0.333333333333333}*cell[17] - x54;
auto x56 = V{0.333333333333333}*cell[18];
auto x57 = -x29;
auto x58 = x39 + x57;
auto x59 = x32*x58;
auto x60 = x56 - x59;
auto x61 = x42 + V{0.0462962962962963};
auto x62 = x38 + V{-1};
auto x63 = V{0.0555555555555556}*x22;
auto x64 = V{0.166666666666667}*cell[3];
auto x65 = x29 + V{-1};
auto x66 = -x65;
auto x67 = -x36;
auto x68 = x30*x32;
auto x69 = -x56 + x59;
auto x70 = V{0.166666666666667}*cell[7];
auto x71 = x31*x46;
auto x72 = -x71;
auto x73 = V{0.166666666666667}*cell[17];
auto x74 = x46*x53;
auto x75 = -x73 + x74;
auto x76 = V{0.166666666666667}*cell[11];
auto x77 = x32*x39;
auto x78 = V{0.166666666666667}*cell[6];
auto x79 = x36*x46 + x78;
auto x80 = -x76 + x77 + x79;
auto x81 = V{0.166666666666667}*cell[1];
auto x82 = x25*x32;
auto x83 = V{0.166666666666667}*cell[18];
auto x84 = x46*x58;
auto x85 = x81 + x82 - x83 + x84;
auto x86 = x23*(x49 + x70 + x72 + x75 + x80 + x85 + V{4.62592926927149e-18});
auto x87 = V{0.0277777777777778}*x22;
auto x88 = x81 + x82 + x83 - x84;
auto x89 = x73 - x74;
auto x90 = -x77;
auto x91 = x70 + x72 + x76 + x90;
auto x92 = x23*(x61 + x79 + x88 + x89 + x91);
auto x93 = V{0.0833333333333333}*cell[3];
auto x94 = V{0.0833333333333333}*cell[12];
auto x95 = -x94;
auto x96 = x30*x46;
auto x97 = x46*x65;
auto x98 = x40*x46;
auto x99 = V{0.166666666666667}*cell[5] - x98;
auto x100 = x93 + x95 + x96 + x97 + x99;
auto x101 = V{0.0833333333333333}*cell[4];
auto x102 = V{0.0833333333333333}*cell[13];
auto x103 = -x102;
auto x104 = V{0.00231481481481481}*x22;
auto x105 = x104*x45;
auto x106 = x104*x48;
auto x107 = x101 + x103 + x105 + x106 + V{0.0231481481481482};
auto x108 = x23*(x100 + x107 + x37 + x75 + x88);
auto x109 = -x93 + x94 - x96 + x99;
auto x110 = x23*(x107 + x109 + x34 + x85 + x89 - x97);
auto x111 = -x101 + x102 - x105 + V{0.0231481481481481};
auto x112 = -x70 + x71;
auto x113 = x23*(x100 - x106 + x111 + x112 + x60 + x76 + x79 + x90);
auto x114 = -x38;
auto x115 = x24 + V{1};
auto x116 = -V{0.333333333333333}*cell[17] + x54;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x27 - x50 + V{-0.0555555555555556};
cell[2] = x23*(V{0.333333333333333}*cell[11] - x43 + x44 + x46*x51 - x47 - x52 + x55 + x60 + x61) - x62*x63 + V{-0.0555555555555556};
cell[3] = x23*(V{0.166666666666667}*cell[12] + x32*x66 + x32*x67 + x34 - x35 + x55 - x64 - x68 + x69) - x63*x65 + V{-0.0555555555555556};
cell[4] = -x48*x87 - x86 + V{-0.0277777777777778};
cell[5] = V{0.0277777777777778}*x22*x40 - x92 + V{-0.0277777777777778};
cell[6] = -x108 - x36*x87 + V{-0.0277777777777778};
cell[7] = -x110 + V{0.0277777777777778}*x22*x31 + V{-0.0277777777777778};
cell[8] = x23*(x104*x51 + x109 + x111 + x46*x66 + x46*x67 + x55 - x78 + x91) - x87*(x29 + x62) + V{-0.0277777777777778};
cell[9] = x113 + x87*(x114 + x30) + V{-0.0277777777777778};
cell[10] = x115*x63 + x50 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x39 - x23*(V{0.333333333333333}*cell[11] + V{0.333333333333333}*cell[5] - x116 - x41 - x49 - x52 - x69 + V{0.0462962962962963}) + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x30 - x23*(V{0.166666666666667}*cell[12] + V{0.333333333333333}*cell[7] - x116 - x32*x65 - x33 - x37 - x60 - x64 - x68) + V{-0.0555555555555556};
cell[13] = x45*x87 + x86 + V{-0.0277777777777778};
cell[14] = x87*(x114 + x115) + x92 + V{-0.0277777777777778};
cell[15] = x108 + x87*(x24 + x30) + V{-0.0277777777777778};
cell[16] = x110 + x87*(x115 + x57) + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x53 - x23*(V{0.166666666666667}*cell[5] - x101 - x103 - x105 - x106 - x112 - x116 - x80 - x93 - x95 - x96 - x97 - x98 + V{0.0231481481481481}) + V{-0.0277777777777778};
cell[18] = -x113 + V{0.0277777777777778}*x22*x58 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
