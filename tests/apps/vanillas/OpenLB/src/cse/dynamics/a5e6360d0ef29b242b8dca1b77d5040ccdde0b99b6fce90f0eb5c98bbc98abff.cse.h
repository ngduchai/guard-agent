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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::FixedVelocityMomentum, momenta::BulkStress, momenta::DefineUSeparately>, equilibria::SecondOrder, collision::BGK, forcing::MCGuo<momenta::Identity> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x12 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x11 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x13 = parameters.template get<descriptors::OMEGA>();
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x14 = x13 + V{-1};
auto x15 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x16 = x15 + V{1};
auto x17 = ((x12)*(x12));
auto x18 = V{1.5}*x17;
auto x19 = ((x11)*(x11));
auto x20 = V{1.5}*x19;
auto x21 = x20 + V{-1};
auto x22 = x18 + x21;
auto x23 = V{0.5}*x13 + V{-1};
auto x24 = x10*x12;
auto x25 = x11*x9;
auto x26 = x15 + V{1};
auto x27 = V{0.0277777777777778}*x13;
auto x28 = V{3}*x12;
auto x29 = x11 - x12;
auto x30 = V{3}*x11;
auto x31 = x22 + x30;
auto x32 = V{9}*x11;
auto x33 = V{6}*x12;
auto x34 = x33 + V{3};
auto x35 = V{9}*x12;
auto x36 = V{6}*x11;
auto x37 = x23*x26;
auto x38 = V{0.0277777777777778}*x37;
auto x39 = V{0.111111111111111}*x13;
auto x40 = -x30;
auto x41 = V{1} - x18;
auto x42 = V{3}*x19 + x41;
auto x43 = x36 + V{-3};
auto x44 = V{3}*x24;
auto x45 = V{0.111111111111111}*x37;
auto x46 = V{4.5}*((x11 + x12)*(x11 + x12));
auto x47 = x33 + V{-3};
auto x48 = V{3}*x17;
auto x49 = -V{3}*x25;
auto x50 = x36 + V{3};
auto x51 = -x20 + x28;
auto x0 = -cell[0]*x14 - V{0.444444444444444}*x13*(x16*x22 + V{1}) + V{1.33333333333333}*x23*x26*(x24 + x25);
auto x1 = -(cell[1]*x14 + x27*(x16*(-x28 + x31 - V{4.5}*((x29)*(x29))) + V{1}) + x38*(x10*(-x32 + x34) - x9*(x35 - x36 + V{3})));
auto x2 = -cell[2]*x14 + x39*(x16*(x40 + x42) + V{-1}) + x45*(-x43*x9 + x44);
auto x3 = -cell[3]*x14 - x27*(x16*(x28 + x31 - x46) + V{1}) - x38*(x10*(x32 + x47) + x9*(x35 + x43));
auto x4 = -cell[4]*x14 - x39*(x16*(x21 + x28 - x48) + V{1}) - x45*(x10*x47 + x49);
auto x5 = -(cell[5]*x14 + x27*(x16*(x22 + x28 + x40 - V{4.5}*((x29)*(x29))) + V{1}) + x38*(-x10*(x32 - x33 + V{3}) + x9*(-x35 + x50)));
auto x6 = -cell[6]*x14 + x39*(x16*(x30 + x42) + V{-1}) + x45*(x44 - x50*x9);
auto x7 = -cell[7]*x14 + V{0.0277777777777778}*x13*(x16*(x30 + x41 + x46 + x51) + V{-1}) - x38*(x10*(x32 + x34) + x9*(x35 + x50));
auto x8 = -cell[8]*x14 + V{0.111111111111111}*x13*(x16*(x48 + x51 + V{1}) + V{-1}) - x45*(x10*x34 + x49);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x26, x17 + x19 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
