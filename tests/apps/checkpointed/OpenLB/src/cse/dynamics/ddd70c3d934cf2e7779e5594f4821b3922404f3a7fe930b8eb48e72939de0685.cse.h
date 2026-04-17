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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SmagorinskyEffectiveOmega<collision::BGK>, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x10 = parameters.template get<descriptors::OMEGA>();
auto x11 = cell[1] + cell[7];
auto x12 = cell[0] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + x11 + V{1};
auto x13 = V{1} / (x12);
auto x14 = -cell[5];
auto x15 = cell[3] + x14;
auto x16 = cell[2] - cell[6];
auto x17 = cell[1] - cell[7] + x15 + x16;
auto x18 = -cell[4] + cell[8];
auto x19 = -cell[3] + x11 + x14 + x18;
auto x20 = V{1}*x13;
auto x21 = ((x19)*(x19));
auto x22 = -V{0.333333333333333}*cell[0] + V{0.666666666666667}*cell[1] + V{0.666666666666667}*cell[3] + V{0.666666666666667}*cell[5] + V{0.666666666666667}*cell[7];
auto x23 = ((x17)*(x17));
auto x24 = V{1} / (V{3.00000046417339}*util::sqrt(x13*((x9)*(x9))*util::sqrt(((cell[1] - cell[7] - x13*x17*x19 - x15)*(cell[1] - cell[7] - x13*x17*x19 - x15)) + V{0.5}*((-V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[4] - V{0.333333333333333}*cell[6] + V{0.666666666666667}*cell[8] - x20*x21 + x22)*(-V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[4] - V{0.333333333333333}*cell[6] + V{0.666666666666667}*cell[8] - x20*x21 + x22)) + V{0.5}*((V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[4] + V{0.666666666666667}*cell[6] - V{0.333333333333333}*cell[8] - x20*x23 + x22)*(V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[4] + V{0.666666666666667}*cell[6] - V{0.333333333333333}*cell[8] - x20*x23 + x22))) + V{0.0277777691819762}/((x10)*(x10))) + V{0.5}/x10);
auto x25 = V{1} - x24;
auto x26 = V{1} / ((x12)*(x12));
auto x27 = V{1.5}*x26;
auto x28 = x21*x27;
auto x29 = x27*((x17)*(x17)) + V{-1};
auto x30 = x28 + x29;
auto x31 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x32 = V{3}*cell[3];
auto x33 = V{3}*cell[7];
auto x34 = V{3}*cell[1] - V{3}*cell[5];
auto x35 = V{3}*cell[2] - V{3}*cell[6] + x32 - x33 + x34;
auto x36 = x13*x35;
auto x37 = V{4.5}*x26;
auto x38 = x37*((2*cell[1] - 2*cell[5] + x16 + x18)*(2*cell[1] - 2*cell[5] + x16 + x18));
auto x39 = V{1} - x28;
auto x40 = x13*(-V{3}*cell[4] + V{3}*cell[8] - x32 + x33 + x34);
auto x41 = x23*x27;
auto x42 = x40 - x41;
auto x43 = x39 + x42;
auto x44 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x45 = V{3}*x26;
auto x46 = x23*x45 + x39;
auto x47 = V{2}*cell[3] + cell[4] - V{2}*cell[7] - cell[8] + x16;
auto x48 = x21*x45;
auto x49 = -x36;
auto x0 = V{1}*cell[0]*x25 - x24*(x30*(V{0.444444444444444}*cell[0] + V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + V{0.444444444444444}) + V{0.444444444444444});
auto x1 = V{1}*cell[1]*x25 + x24*(x31*(x36 + x38 + x43) + V{-0.0277777777777778});
auto x2 = V{1}*cell[2]*x25 + x24*(x44*(x36 + x46) + V{-0.111111111111111});
auto x3 = V{1}*cell[3]*x25 - x24*(x31*(-x13*x35 + x30 - x37*((x47)*(x47)) + x40) + V{0.0277777777777778});
auto x4 = V{1}*cell[4]*x25 - x24*(x44*(x29 + x40 - x48) + V{0.111111111111111});
auto x5 = V{1}*cell[5]*x25 - x24*(x31*(x28 + x36 - x38 + x40 + x41 + V{-1}) + V{0.0277777777777778});
auto x6 = V{1}*cell[6]*x25 + x24*(x44*(x46 + x49) + V{-0.111111111111111});
auto x7 = V{1}*cell[7]*x25 + x24*(x31*(x37*((x47)*(x47)) + x43 + x49) + V{-0.0277777777777778});
auto x8 = V{1}*cell[8]*x25 + x24*(x44*(x42 + x48 + V{1}) + V{-0.111111111111111});
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x12, V{1}*x26*(x21 + x23) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
