/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Tim Bingert
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

#ifndef BUBBLE_SPAWNER_H
#define BUBBLE_SPAWNER_H

#include "utilities/functorPtr.h"
#include "functors/lattice/indicator/superIndicatorF2D.h"
#include "functors/lattice/indicator/superIndicatorF3D.h"
#include "functors/functors2D.h"
#include "functors/functors3D.h"
// #include <olb.h>

namespace olb {

template <typename T, typename NSDESCRIPTOR, typename ACDESCRIPTOR>
class BubbleSpawner2D {
private:
  T _surfaceTension;
  Vector<T,2> _rhos;
  T _w;
  int _Ny;
  T _spawnTimeFactor = 1.8;
  int _iTfirstSpawn = 100;

public:
  BubbleSpawner2D(T surfaceTension, Vector<T,2> rhos, T w, int Ny)
    : _surfaceTension(surfaceTension), _w(w), _Ny(Ny)
  {
    for (int i = 0; i < 2; ++i) {
      _rhos[i] = rhos[i];
    }
  }

  bool spawnTime(int iT, int spawn_period) const {
    return (iT % spawn_period) == _iTfirstSpawn;
  }

  std::vector<std::vector<T>> spawnLocation(
      T diameter,
      UnitConverter<T, NSDESCRIPTOR> const& converter,
      SuperLattice<T, ACDESCRIPTOR>& sLatticeAC,
      SuperGeometry<T,2>& superGeometry)
  {
    OstreamManager clout(std::cout, "bubbleSpawner");
    sLatticeAC.setProcessingContext(ProcessingContext::Evaluation);

    int rank = 0;
#ifdef PARALLEL_MODE_MPI
    rank = singleton::mpi().getRank();
#endif
    std::vector<T> bubbleContainer;
    size_t bubbleContainerSize = 0;

    T dx = converter.getPhysDeltaX();
    T minX = dx*diameter*T(1);
    T maxX = dx*diameter*T(4);

    if (rank == 0) {
      T minY = dx*(diameter+1);
      T maxY = dx*(_Ny-(diameter+1));
      int n = int((maxY-minY)/dx/(T(1.8)*diameter));

      std::random_device rd;
      std::mt19937 gen(rd());
      std::uniform_real_distribution<T> dist(T(0), T(1));
      std::vector<T> randomNumbers(10*n);
      for (auto& val : randomNumbers) val = dist(gen);

      int a = 0;
      for (int i = 0; i < n; i++) {
        T freeY = 0.;
        bool searching = true;
        while(searching && a<n*10) {
          freeY = randomNumbers[a]*(maxY-minY)+minY;
          searching = false;
          for (int j = 0; j < i; j++) {
            if (util::abs(freeY-bubbleContainer[j]) <= (diameter*dx+diameter*dx)*T(0.9)) {
              searching = true;
              break;
            }
          }
          a++;
        }
        if (freeY != 0 && a < n*10) {
          bubbleContainerSize++;
          bubbleContainer.push_back(freeY);
        }
      }
    }

#ifdef PARALLEL_MODE_MPI
    singleton::mpi().bCast(bubbleContainerSize);
    bubbleContainer.resize(bubbleContainerSize);
    singleton::mpi().bCast(bubbleContainer.data(),bubbleContainerSize);
#endif

    std::vector<std::vector<T>> pos;
    SuperLatticeDensity2D<T,ACDESCRIPTOR> phi(sLatticeAC);

    for (size_t i = 0; i < bubbleContainerSize; i++) {
      int in[2]; T phiAv[1];
      Vector<T,2> origin = {(maxX-minX)/T(2)-dx*diameter/T(2), bubbleContainer[i]-dx*diameter/T(2)*T(1.2)};
      Vector<T,2> extend = {_spawnTimeFactor*diameter*dx, dx*diameter*T(1.2)};
      IndicatorCuboid2D<T> searchZone_( extend, origin );
      SuperIndicatorFfromIndicatorF2D<T> searchZone(searchZone_, superGeometry);
      SuperAverage2D<T,T> PhiAvFinder(phi, searchZone);
      PhiAvFinder(phiAv, in);

      if (phiAv[0] > T(0.95)) {
        pos.push_back({(maxX-minX)/T(2), bubbleContainer[i]});
      }
    }
    return pos;
  }

  void spawnPopulations(
      std::vector<std::vector<T>>& pos, T diameter,
      UnitConverter<T, NSDESCRIPTOR> const& converter,
      SuperLattice<T, NSDESCRIPTOR>& sLatticeNS,
      SuperLattice<T, ACDESCRIPTOR>& sLatticeAC,
      SuperGeometry<T, 2>& superGeometry)
  {
    OstreamManager clout(std::cout, "bubbleSpawner");
    sLatticeAC.setProcessingContext(ProcessingContext::Evaluation);
    sLatticeNS.setProcessingContext(ProcessingContext::Evaluation);

    T dx        = converter.getPhysDeltaX();
    T C_sigma   = converter.getConversionFactorSurfaceTension();
    T C_density = converter.getConversionFactorDensity();
    T C_p       = C_sigma / dx;
    T sigma     = _surfaceTension / C_sigma;

    std::shared_ptr<AnalyticalF2D<T,T>> one = std::make_shared<AnalyticalConst2D<T,T>>(T(1));
    std::shared_ptr<AnalyticalF2D<T,T>> rhov = std::make_shared<AnalyticalConst2D<T,T>>(_rhos[0] / C_density);
    std::shared_ptr<AnalyticalF2D<T,T>> rhol = std::make_shared<AnalyticalConst2D<T,T>>(_rhos[1] / C_density);

    SuperLatticeDensity2D<T,NSDESCRIPTOR>   p_raw(sLatticeNS);
    SuperLatticeVelocity2D<T,NSDESCRIPTOR>  u_ns_raw (sLatticeNS);
    SuperLatticeDensity2D<T,ACDESCRIPTOR>   phi_raw(sLatticeAC);
    SuperLatticeVelocity2D<T,ACDESCRIPTOR>  u_ac_raw (sLatticeAC);

    std::shared_ptr<AnalyticalF2D<T,T>> u_ns = std::make_shared<AnalyticalFfromSuperF2D<T,T>>(u_ns_raw);
    std::shared_ptr<AnalyticalF2D<T,T>> u_ac = std::make_shared<AnalyticalFfromSuperF2D<T,T>>(u_ac_raw);
    std::shared_ptr<AnalyticalF2D<T,T>> p = std::make_shared<AnalyticalFfromSuperF2D<T,T>>(p_raw);
    std::shared_ptr<AnalyticalF2D<T,T>> phi = std::make_shared<AnalyticalFfromSuperF2D<T,T>>(phi_raw);

    std::shared_ptr<IndicatorF2D<T>> bubble_circle =
      std::make_shared<IndicatorCircle2D<T>>(pos[0], dx * diameter / T(2) * T(1.3));
    auto bubble_circles = bubble_circle;

    std::shared_ptr<AnalyticalF2D<T,T>> phi_new_bubble =
      std::make_shared<CircularInterface2D<T>>(pos[0], dx * diameter / T(2), dx * _w, T(1), true);
    std::shared_ptr<AnalyticalF2D<T,T>> phi_new = phi + phi_new_bubble - one;

    std::shared_ptr<AnalyticalF2D<T,T>> bubblePressure =
      std::make_shared<LaplacePressure2D<T>>(pos[0], dx * diameter / T(2), dx * _w, sigma * C_sigma / C_p);
    std::shared_ptr<AnalyticalF2D<T,T>> halfYLPressure = std::make_shared<AnalyticalConst2D<T, T>>(T(2) * sigma / diameter / T(2));
    std::shared_ptr<AnalyticalF2D<T,T>> p_new = p + bubblePressure + halfYLPressure;

    for (size_t i=1; i<pos.size(); i++) {
      auto bubble_circle_loop = std::make_shared<IndicatorCircle2D<T>>(pos[i], dx * diameter / T(2) * T(1.3));
      bubble_circles = bubble_circles + bubble_circle_loop;

      std::shared_ptr<AnalyticalF2D<T,T>> phi_new_bubble_loop =
        std::make_shared<CircularInterface2D<T>>(pos[i], dx * diameter / T(2), dx * _w, T(1), true);
      phi_new = phi_new + phi_new_bubble_loop - one;

      std::shared_ptr<AnalyticalF2D<T,T>> bubblePressure_loop =
        std::make_shared<LaplacePressure2D<T>>(pos[i], dx * diameter / T(2), dx * _w, sigma * C_sigma / C_p);
      p_new = p_new + bubblePressure_loop + halfYLPressure;
    }

    std::shared_ptr<AnalyticalF2D<T,T>> rho = rhov + (rhol - rhov) * phi_new;
    SuperIndicatorFfromIndicatorF2D<T> bubble_ind(bubble_circles, superGeometry);

    auto pop_functor_ns = std::make_shared<IncompressibleEquilibriumPopulations2D<T, NSDESCRIPTOR>>(rho, p_new, u_ns);
    auto pop_functor_ac = std::make_shared<FirstOrderEquilibriumPopulations2D<T, ACDESCRIPTOR>>(phi_new, u_ac);

    sLatticeNS.template defineField<descriptors::POPULATION>(bubble_ind, *pop_functor_ns);
    sLatticeAC.template defineField<descriptors::POPULATION>(bubble_ind, *pop_functor_ac);

    sLatticeAC.setProcessingContext(ProcessingContext::Simulation);
    sLatticeNS.setProcessingContext(ProcessingContext::Simulation);
  }

  T getSpawnTimeFactor() {
    return _spawnTimeFactor;
  }
};


template <typename T, typename NSDESCRIPTOR, typename ACDESCRIPTOR>
class BubbleSpawner3D {
private:
  T _surfaceTension;
  Vector<T,2> _rhos;
  T _w;
  T _spawnTimeFactor = 1.7;
  T _crossSectionArea;
  FunctorPtr<IndicatorCylinder3D<T>> _spawnRegion;
  int _iTfirstSpawn = 100;
  bool tick = 1;

public:
  BubbleSpawner3D(T surfaceTension, Vector<T,2> rhos, T w, T spawnTimeFactor, T crossSectionArea, FunctorPtr<IndicatorCylinder3D<T>>&& spawnRegion)
    : _surfaceTension(surfaceTension), _w(w), _spawnTimeFactor(spawnTimeFactor), _crossSectionArea(crossSectionArea), _spawnRegion(std::move(spawnRegion))
  {
    for (int i = 0; i < 2; ++i) {
      _rhos[i] = rhos[i];
    }
  }

  bool spawnTime(int iT, int spawn_period) const {
    return (iT % spawn_period) == _iTfirstSpawn;
  }

  std::vector<Vector<T,3>> spawnLocationRandom(
      T diameter,
      UnitConverter<T, NSDESCRIPTOR> const& converter,
      SuperLattice<T, ACDESCRIPTOR>& sLatticeAC,
      SuperGeometry<T,3>& superGeometry)
  {
    OstreamManager clout(std::cout, "bubbleSpawner");
    sLatticeAC.setProcessingContext(ProcessingContext::Evaluation);

    int rank = 0;
#ifdef PARALLEL_MODE_MPI
    rank = singleton::mpi().getRank();
#endif
    std::vector<Vector<T,3>> bubbleContainer;
    size_t bubbleContainerSize = 0;

    T dx = converter.getPhysDeltaX();

    if (rank == 0) {
      int n = int(_crossSectionArea/(_spawnTimeFactor*_spawnTimeFactor*diameter*diameter*dx*dx/T(4)));
      std::random_device seed;
      std::mt19937 generator(seed());
      std::uniform_real_distribution<T> distribution(0, 1);
      auto randomness = [&distribution,&generator]() -> T {
        return distribution(generator);
      };

      int a = 0;
      for (int i = 0; i < n; i++) {
        bool searching = true;
        Vector<T,3> freePos{};
        while(searching && a<n*20) {
          freePos = _spawnRegion->getSample(randomness);
          searching = false;
          for (int j = 0; j < i; j++) {
            if (util::norm<3>(freePos-bubbleContainer[j]) <= (diameter*dx+diameter*dx)*T(0.9)) {
              searching = true;
              break;
            }
          }
          a++;
        }
        if (a < n*20) {
          bubbleContainerSize++;
          bubbleContainer.push_back(freePos);
        }
      }
    }

#ifdef PARALLEL_MODE_MPI
    singleton::mpi().bCast(bubbleContainerSize);
    bubbleContainer.resize(bubbleContainerSize);
    for (size_t i = 0; i < bubbleContainerSize; ++i) {
      singleton::mpi().bCast(bubbleContainer[i]);
    }
#endif

    std::vector<Vector<T,3>> pos;
    SuperLatticeDensity3D<T,ACDESCRIPTOR> phi(sLatticeAC);
    T freeDistance = dx*diameter/T(2)*_spawnTimeFactor;

    for (size_t i = 0; i < bubbleContainerSize; i++) {
      int in[3]; T phiAv[1];
      auto candidatePos = bubbleContainer[i];
      Vector<T,3> origin = {candidatePos[0]-freeDistance, candidatePos[1]-freeDistance, candidatePos[2]-freeDistance};
      Vector<T,3> extend = {T(2)*freeDistance, T(2)*freeDistance, T(2)*freeDistance};
      IndicatorCuboid3D<T> searchZone_( extend, origin );
      SuperIndicatorFfromIndicatorF3D<T> searchZone(searchZone_, superGeometry);
      SuperAverage3D<T,T> PhiAvFinder(phi, searchZone);
      PhiAvFinder(phiAv, in);

      if (phiAv[0] > T(0.95)) {
        pos.push_back(candidatePos);
      }
    }
    return pos;
  }

std::vector<Vector<T,3>> spawnLocationStructured(
      T diameter,
      UnitConverter<T, NSDESCRIPTOR> const& converter,
      SuperGeometry<T,3>& superGeometry)
  {
    OstreamManager clout(std::cout, "bubbleSpawner");

    std::vector<Vector<T,3>> bubbleContainer;
    T dx = converter.getPhysDeltaX();

    T radiusInd = _spawnRegion->getRadius();
    Vector<T,3> axis = _spawnRegion->getCenter1() - _spawnRegion->getCenter2();
    Vector<T,3> normal = util::normalize(axis);
    Vector<T,3> center = _spawnRegion->getCenter1() + 0.5*axis;
    T d = _spawnTimeFactor*diameter*dx;

    // Pick arbitrary vector not parallel to n
    Vector<T,3> arbitrary(1.0, 0.0, 0.0);
    if (util::abs(normal[0]) > 0.9) arbitrary = {0.0, 1.0, 0.0};

    // Construct orthonormal basis (u,v) in plane
    Vector<T,3> u{};
    u = util::normalize(crossProduct3D(normal, arbitrary));
    Vector<T,3> v{};
    v = util::normalize(crossProduct3D(normal, u));

    // Row spacing in hex grid
    T row_height = util::sqrt(T(3)) / T(2) * d;
    int n_rows = static_cast<int>(std::ceil(radiusInd / row_height));

    if (tick) {
      // Include center
      //bubbleContainer.push_back(center);

      for (int row = 0; row <= n_rows; ++row) {
        std::vector<T> y_offsets;
        if (row==0){
          y_offsets = { 0 };
        } else{
          y_offsets = { row * row_height, -row * row_height };
        }

        for (T eta : y_offsets) {
          // max x-span for circle condition
          T xi_span = util::sqrt(radiusInd * radiusInd - eta * eta);

          // Shift odd rows by d/2
          T x_shift = (row % 2 == 0) ? 0.0 : d / T(2);

          for (T xi = -xi_span + x_shift; xi <= xi_span; xi += d) {
            // Map (xi, eta) -> 3D
            Vector<T,3> p(
                center[0] + xi * u[0] + eta * v[0],
                center[1] + xi * u[1] + eta * v[1],
                center[2] + xi * u[2] + eta * v[2]
            );
            bubbleContainer.push_back(p);
          }
        }
      }
      tick = !tick;
    } else {
      // --- Apply lattice shift ---
      T xi_shift  = d / T(2);
      T eta_shift = util::sqrt(T(3)) / T(6) * d;

      // Loop through rows
      for (int row = 0; row <= n_rows; ++row) {
        std::vector<T> y_offsets;
        if (row==0){
          y_offsets = { 0 };
        } else{
          y_offsets = { row * row_height, -row * row_height };
        }

        for (T eta : y_offsets) {
          // Apply shift in eta-direction
          T eta_shifted = eta + eta_shift;

          // Circle condition: skip if outside radius
          if (util::abs(eta_shifted) > radiusInd) continue;

          // max x-span for circle condition
          T xi_span = util::sqrt(radiusInd * radiusInd - eta_shifted * eta_shifted);

          for (T xi = -xi_span; xi <= xi_span; xi += d) {
            // Apply shift in xi-direction
            T xi_shifted = xi + xi_shift;

            // Check circle condition
            if (xi_shifted * xi_shifted + eta_shifted * eta_shifted > radiusInd * radiusInd) continue;

            // Map (xi_shifted, eta_shifted) -> 3D
            Vector<T,3> p(
              center[0] + xi_shifted * u[0] + eta_shifted * v[0],
              center[1] + xi_shifted * u[1] + eta_shifted * v[1],
              center[2] + xi_shifted * u[2] + eta_shifted * v[2]
            );
            bubbleContainer.push_back(p);
          }
        }
      }
      tick = !tick;
    }
    return bubbleContainer;
  }

  void spawnPopulations(
      std::vector<Vector<T,3>>& pos, T diameter,
      UnitConverter<T, NSDESCRIPTOR> const& converter,
      SuperLattice<T, NSDESCRIPTOR>& sLatticeNS,
      SuperLattice<T, ACDESCRIPTOR>& sLatticeAC,
      SuperGeometry<T, 3>& superGeometry)
  {
    OstreamManager clout(std::cout, "bubbleSpawner");
    sLatticeAC.setProcessingContext(ProcessingContext::Evaluation);
    sLatticeNS.setProcessingContext(ProcessingContext::Evaluation);

    T dx        = converter.getPhysDeltaX();
    T C_sigma   = converter.getConversionFactorSurfaceTension();
    T C_density = converter.getConversionFactorDensity();
    T C_p       = C_sigma / dx;
    T sigma     = _surfaceTension / C_sigma;

    std::shared_ptr<AnalyticalF3D<T,T>> one = std::make_shared<AnalyticalConst3D<T,T>>(T(1));
    std::shared_ptr<AnalyticalF3D<T,T>> rhov = std::make_shared<AnalyticalConst3D<T,T>>(_rhos[0] / C_density);
    std::shared_ptr<AnalyticalF3D<T,T>> rhol = std::make_shared<AnalyticalConst3D<T,T>>(_rhos[1] / C_density);

    SuperLatticeDensity3D<T,NSDESCRIPTOR>   p_raw(sLatticeNS);
    SuperLatticeVelocity3D<T,NSDESCRIPTOR>  u_ns_raw (sLatticeNS);
    SuperLatticeDensity3D<T,ACDESCRIPTOR>   phi_raw(sLatticeAC);
    SuperLatticeVelocity3D<T,ACDESCRIPTOR>  u_ac_raw (sLatticeAC);

    std::shared_ptr<AnalyticalF3D<T,T>> u_ns = std::make_shared<AnalyticalFfromSuperF3D<T,T>>(u_ns_raw);
    std::shared_ptr<AnalyticalF3D<T,T>> u_ac = std::make_shared<AnalyticalFfromSuperF3D<T,T>>(u_ac_raw);
    std::shared_ptr<AnalyticalF3D<T,T>> p = std::make_shared<AnalyticalFfromSuperF3D<T,T>>(p_raw);
    std::shared_ptr<AnalyticalF3D<T,T>> phi = std::make_shared<AnalyticalFfromSuperF3D<T,T>>(phi_raw);

    std::shared_ptr<IndicatorF3D<T>> bubble_circle =
      std::make_shared<IndicatorSphere3D<T>>(pos[0], dx * diameter / T(2) * T(1.3));
    auto bubble_circles = bubble_circle;

    std::shared_ptr<AnalyticalF3D<T,T>> phi_new_bubble =
      std::make_shared<SphericalInterface3D<T>>(pos[0], dx * diameter / T(2), dx * _w, T(1), true);
    std::shared_ptr<AnalyticalF3D<T,T>> phi_new = phi + phi_new_bubble - one;

    std::shared_ptr<AnalyticalF3D<T,T>> bubblePressure =
      std::make_shared<LaplacePressure3D<T>>(pos[0], dx * diameter / T(2), dx * _w, sigma * C_sigma / C_p);
    std::shared_ptr<AnalyticalF3D<T,T>> halfYLPressure = std::make_shared<AnalyticalConst3D<T,T>>(T(2) * T(2) * sigma / diameter / T(2));
    std::shared_ptr<AnalyticalF3D<T,T>> p_new = p + bubblePressure + halfYLPressure;

    for (size_t i=1; i<pos.size(); i++) {
      auto bubble_circle_loop = std::make_shared<IndicatorSphere3D<T>>(pos[i], dx * diameter / T(2) * T(1.3));
      bubble_circles = bubble_circles + bubble_circle_loop;

      std::shared_ptr<AnalyticalF3D<T,T>> phi_new_bubble_loop =
        std::make_shared<SphericalInterface3D<T>>(pos[i], dx * diameter / T(2), dx * _w, T(1), true);
      phi_new = phi_new + phi_new_bubble_loop - one;

      std::shared_ptr<AnalyticalF3D<T,T>> bubblePressure_loop =
        std::make_shared<LaplacePressure3D<T>>(pos[i], dx * diameter / T(2), dx * _w, sigma * C_sigma / C_p);
      p_new = p_new + bubblePressure_loop + halfYLPressure;
    }

    std::shared_ptr<AnalyticalF3D<T,T>> rho = rhov + (rhol - rhov) * phi_new;
    SuperIndicatorFfromIndicatorF3D<T> bubble_ind(bubble_circles, superGeometry);

    auto pop_functor_ns = std::make_shared<IncompressibleEquilibriumPopulations3D<T, NSDESCRIPTOR>>(rho, p_new, u_ns);
    auto pop_functor_ac = std::make_shared<FirstOrderEquilibriumPopulations3D<T, ACDESCRIPTOR>>(phi_new, u_ac);

    sLatticeNS.template defineField<descriptors::POPULATION>(bubble_ind, *pop_functor_ns);
    sLatticeAC.template defineField<descriptors::POPULATION>(bubble_ind, *pop_functor_ac);

    sLatticeAC.setProcessingContext(ProcessingContext::Simulation);
    sLatticeNS.setProcessingContext(ProcessingContext::Simulation);
  }

  T getSpawnTimeFactor() {
    return _spawnTimeFactor;
  }
};


}

#endif
