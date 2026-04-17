/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2012-2016 Mathias J. Krause, Benjamin Förster
 *                2026 Shota Ito
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

#include "optimization/core/controller.h"
#include "optimization/core/serialize.h"
#include "optimization/core/optiCase.h"
#include "optimization/core/projection.h"

#include "optimization/optimizers/optimizer.h"
#include "optimization/optimizers/optimizerBarzilaiBorwein.h"
#include "optimization/optimizers/optimizerConstrainedBFGS.h"
#include "optimization/optimizers/optimizerLineSearch.h"
#include "optimization/optimizers/optimizerLBFGS.h"
#include "optimization/optimizers/optimizerSteepestDecent.h"

#include "optimization/dynamics/discreteDualDynamics.h"
#include "optimization/dynamics/continuousDualDynamics.h"

#include "optimization/primitives/primitives.h"
#include "optimization/core/optimalitySystem.h"

#include "utilities/aDiff.h"
