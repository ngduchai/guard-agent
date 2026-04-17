/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender
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

#ifndef REFINEMENT_VERTEX_CENTERED_H
#define REFINEMENT_VERTEX_CENTERED_H

namespace olb {

namespace refinement {

/// Proxy class for accessing coarse cells co-incident to fine cells in vertex-centered refinement
template <typename CELL>
class VertexCenteredCoarseCell {
private:
  CELL _cell;
  LatticeR<CELL::descriptor_t::d> _fineLatticeR;

public:
  using value_t = typename CELL::value_t;
  using descriptor_t = typename CELL::descriptor_t;

  VertexCenteredCoarseCell(CELL&& cell, const LatticeR<CELL::descriptor_t::d>& fineLatticeR) any_platform
  : _cell{std::move(cell)}
  , _fineLatticeR{fineLatticeR}
  {
    _cell.setLatticeR(_fineLatticeR / 2);
  }

  VertexCenteredCoarseCell(const CELL& cell, const LatticeR<CELL::descriptor_t::d>& fineLatticeR) any_platform
  : _cell{cell}
  , _fineLatticeR{fineLatticeR}
  {
    _cell.setLatticeR(_fineLatticeR / 2);
  }

  VertexCenteredCoarseCell(const VertexCenteredCoarseCell& rhs) any_platform
  : _cell(rhs._cell)
  , _fineLatticeR(rhs._fineLatticeR)
  { }

  /// Returns true iff present fine location is co-incident with a coarse cell
  operator bool() const any_platform {
    using DESCRIPTOR = typename CELL::descriptor_t;
    bool coIncident = true;
    for (unsigned iD=0; iD < DESCRIPTOR::d; ++iD) {
      coIncident &= !(_fineLatticeR[iD] & 1);
    }
    return coIncident;
  }

  /// Return reference to coarse cell (only well defined if isCoIncident)
  CELL& operator*() any_platform {
    return _cell;
  }

  /// Return neighbor along fine offset
  VertexCenteredCoarseCell neighbor(LatticeR<descriptor_t::d> offset) any_platform {
    return VertexCenteredCoarseCell{_cell, _fineLatticeR + offset};
  }

};

}

}

#endif
