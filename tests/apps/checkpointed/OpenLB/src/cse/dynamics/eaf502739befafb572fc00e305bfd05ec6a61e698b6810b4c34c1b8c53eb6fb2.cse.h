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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SaveVelocity<collision::BGK>, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x11 = parameters.template get<descriptors::OMEGA>();
auto x9 = x11 + V{-1};
auto x10 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x12 = x10 + V{1};
auto x13 = x10 + V{1};
auto x14 = V{1} / ((x13)*(x13));
auto x15 = V{1.5}*x14;
auto x16 = cell[1] - cell[5];
auto x17 = -cell[4] + cell[8];
auto x18 = ((-cell[3] + cell[7] + x16 + x17)*(-cell[3] + cell[7] + x16 + x17));
auto x19 = x15*x18;
auto x20 = cell[2] - cell[6];
auto x21 = cell[3] - cell[7] + x16 + x20;
auto x22 = x15*((x21)*(x21)) + V{-1};
auto x23 = x19 + x22;
auto x24 = cell[0]*x9 + V{0.444444444444444}*x11*(x12*x23 + V{1});
auto x25 = cell[1]*x9;
auto x26 = V{0.0277777777777778}*x11;
auto x27 = V{4.5}*x14;
auto x28 = V{2}*cell[1] - V{2}*cell[5] + x17 + x20;
auto x29 = V{1} / (x13);
auto x30 = V{3}*cell[3];
auto x31 = V{3}*cell[7];
auto x32 = V{3}*cell[1] - V{3}*cell[5];
auto x33 = V{3}*cell[2] - V{3}*cell[6] + x30 - x31 + x32;
auto x34 = x29*x33;
auto x35 = V{1} - x19;
auto x36 = x29*(-V{3}*cell[4] + V{3}*cell[8] - x30 + x31 + x32);
auto x37 = ((x21)*(x21));
auto x38 = x15*x37;
auto x39 = x36 - x38;
auto x40 = x35 + x39;
auto x41 = x34 + x40;
auto x42 = x26*(x12*(x27*((x28)*(x28)) + x41) + V{-1});
auto x43 = cell[2]*x9;
auto x44 = V{0.111111111111111}*x11;
auto x45 = V{3}*x14;
auto x46 = x35 + x37*x45;
auto x47 = x12*(x34 + x46) + V{-1};
auto x48 = cell[3]*x9;
auto x49 = V{2}*cell[3] + cell[4] - V{2}*cell[7] - cell[8] + x20;
auto x50 = x27*((x49)*(x49));
auto x51 = x26*(x12*(x23 - x29*x33 + x36 - x50) + V{1});
auto x52 = x48 + x51;
auto x53 = cell[4]*x9;
auto x54 = x18*x45;
auto x55 = x44*(x12*(x22 + x36 - x54) + V{1});
auto x56 = x53 + x55;
auto x57 = cell[5]*x9;
auto x58 = ((x28)*(x28));
auto x59 = -V{4.5}*x14*x58 + x19 + x34 + x36 + x38 + V{-1};
auto x60 = x26*(-x12*x59 + V{-1});
auto x61 = cell[6]*x9;
auto x62 = -x34;
auto x63 = x44*(x12*(x46 + x62) + V{-1});
auto x64 = cell[7]*x9;
auto x65 = x40 + x62;
auto x66 = x26*(x12*(x50 + x65) + V{-1});
auto x67 = cell[8]*x9;
auto x68 = x44*(x12*(x39 + x54 + V{1}) + V{-1});
auto x69 = -V{0.111111111111111}*x11*x47;
auto x70 = -V{1} / (-V{0.0277777777777778}*x11*(x12*(x27*x58 + x41) + V{-1}) - V{0.0277777777777778}*x11*(x12*(x27*((x49)*(x49)) + x65) + V{-1}) + x24 + x25 + x26*(x12*x59 + V{1}) + x43 + x52 + x56 + x57 + x61 - x63 + x64 + x67 - x68 + x69 + V{-1});
auto x71 = V{1}*x25;
auto x72 = V{1}*x57;
auto x73 = -V{1}*cell[7]*x9 + V{1}*x48 + x51 + x66;
cell[0] = -x24;
cell[1] = -x25 + x42;
cell[2] = -x43 + x44*x47;
cell[3] = -x52;
cell[4] = -x56;
cell[5] = -x57 + x60;
cell[6] = -x61 + x63;
cell[7] = -x64 + x66;
cell[8] = -x67 + x68;
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[0] = -x70*(V{1}*cell[6]*x9 + x42 - V{1}*x43 - x60 - x63 - x69 - x71 + x72 - x73);
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[1] = -x70*(V{1}*cell[8]*x9 - x42 - V{1}*x53 - x55 + x60 - x68 + x71 - x72 - x73);
return { x13, V{1}*x14*(x18 + x37) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
