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
struct CSE<dynamics::Tuple<T, descriptors::D2Q5<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::FirstOrder, collision::OmegaFromCellTauEff<collision::BGK>, AdvectionDiffusionExternalVelocityCollision>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x5 = cell.template getFieldComponent<olb::descriptors::TAU_EFF>(0);
auto x6 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x7 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x8 = V{1} / (x5);
auto x9 = V{1} - V{1}*x8;
auto x10 = V{3}*x6;
auto x11 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4];
auto x12 = V{0.166666666666667}*x11 + V{0.166666666666667};
auto x13 = V{3}*x7;
auto x0 = cell[0]*x9 + x8*(V{0.333333333333333}*cell[0] + V{0.333333333333333}*cell[1] + V{0.333333333333333}*cell[2] + V{0.333333333333333}*cell[3] + V{0.333333333333333}*cell[4]);
auto x1 = cell[1]*x9 - x8*(x12*(x10 + V{-1}) + V{0.166666666666667});
auto x2 = cell[2]*x9 - x8*(x12*(x13 + V{-1}) + V{0.166666666666667});
auto x3 = cell[3]*x9 + x8*(x12*(x10 + V{1}) + V{-0.166666666666667});
auto x4 = cell[4]*x9 + x8*(x12*(x13 + V{1}) + V{-0.166666666666667});
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
return { x11 + V{1}, ((x6)*(x6)) + ((x7)*(x7)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
