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
struct CSE<CombinedAdvectionDiffusionRLBdynamics<T, descriptors::D3Q7<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q7<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::HeatFluxBoundaryDensity<1, 1>, momenta::FixedVelocityMomentumAD, momenta::NoStress, momenta::DefineToEq> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x10 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumAD::VELOCITY>(0);
auto x9 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x11 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumAD::VELOCITY>(1);
auto x8 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x12 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumAD::VELOCITY>(2);
auto x13 = parameters.template get<descriptors::OMEGA>();
auto x7 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x14 = V{1} / (x8 + V{1});
auto x15 = V{0.0625}*x14;
auto x16 = V{4}*x7;
auto x17 = x16 + V{1};
auto x18 = cell[0] + cell[1] + cell[3] + cell[4] + V{2}*cell[5] + cell[6] - x11 + V{1};
auto x19 = -x18;
auto x20 = V{0.03125}*x14*x19;
auto x21 = V{4}*x8;
auto x22 = x21 + V{1};
auto x23 = V{4}*x9;
auto x24 = x23 + V{1};
auto x25 = x16 + V{-1};
auto x26 = x21 + V{-1};
auto x27 = x23 + V{-1};
auto x28 = x13 + V{-1};
auto x29 = x15*x18;
auto x30 = -x25;
auto x31 = V{0.015625}*x18;
auto x32 = -x26;
auto x33 = -x27;
auto x34 = V{0.03125}*cell[0] + V{0.03125}*cell[1] + V{0.03125}*cell[3] + V{0.03125}*cell[4] + V{0.0625}*cell[5] + V{0.03125}*cell[6] - V{0.03125}*x11 + V{0.03125};
auto x35 = V{0.5}*x14*(x17*x31 + x22*x31 + x24*x31 + x30*x31 + x31*x32 + x31*x33 + x34);
auto x36 = V{0.015625}*x19;
auto x37 = -x17*x36 - x22*x36 - x24*x36 + x25*x36 + x26*x36 + x27*x36 + x34;
auto x38 = x14*x37;
auto x39 = x25*x38;
auto x40 = x26*x38;
auto x41 = x27*x38;
auto x42 = x15*x19;
auto x43 = V{0.125}*x19;
auto x0 = -x11*x15 + V{0.03125}*x14*x19*x25 + V{0.03125}*x14*x19*x26 + V{0.03125}*x14*x19*x27 + x14*(V{0.0625}*cell[0] + V{0.0625}*cell[1] + V{0.0625}*cell[3] + V{0.0625}*cell[4] + V{0.125}*cell[5] + V{0.0625}*cell[6] + V{0.0625}) - x17*x20 - x20*x22 - x20*x24 + V{-0.25};
auto x1 = x28*(V{0.5}*x10 + x17*x29 - x17*x35 - x29*x30 + x30*x35) - x39 + V{-0.125};
auto x2 = x28*(V{0.5}*x11 + x22*x29 - x22*x35 - x29*x32 + x32*x35) - x40 + V{-0.125};
auto x3 = x28*(V{0.5}*x12 + x24*x29 - x24*x35 - x29*x33 + x33*x35) - x41 + V{-0.125};
auto x4 = x14*x17*x37 - x28*(V{0.5}*x10 - x15*x19*x25 - V{0.5}*x17*x38 - x17*x42 - V{0.5}*x39) + V{-0.125};
auto x5 = x14*x22*x37 - x28*(V{0.5}*x11 - V{0.5}*x22*x38 - x22*x42 - x26*x42 - V{0.5}*x40) + V{-0.125};
auto x6 = x14*x24*x37 - x28*(V{0.5}*x12 - V{0.5}*x24*x38 - x24*x42 - x27*x42 - V{0.5}*x41) + V{-0.125};
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
return { x14*(V{0.25}*cell[0] + V{0.25}*cell[1] + V{0.25}*cell[3] + V{0.25}*cell[4] + V{0.5}*cell[5] + V{0.25}*cell[6] - V{0.25}*x11 - x17*x43 - x22*x43 - x24*x43 + x25*x43 + x26*x43 + x27*x43 + V{0.25}), ((x7)*(x7)) + ((x8)*(x8)) + ((x9)*(x9)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
