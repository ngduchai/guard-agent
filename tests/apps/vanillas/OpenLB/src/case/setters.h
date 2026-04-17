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

#ifndef CASE_SETTERS_H
#define CASE_SETTERS_H

#include <concepts>

namespace olb {

namespace fields {

template <typename FIELD, typename T, typename DESCRIPTOR, typename FUNCTOR>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
         FUNCTOR& fieldF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  sLattice.template defineField<FIELD>(std::move(domainI), fieldF);
}

template <typename FIELD, typename T, typename DESCRIPTOR, typename FUNCTOR>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
         FUNCTOR& fieldF)
  requires std::derived_from<FUNCTOR, SuperF<DESCRIPTOR::d,T,T>>
{
  sLattice.template defineField<FIELD>(std::move(domainI), fieldF);
}

template <typename FIELD, typename T, typename DESCRIPTOR, typename VALUE>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
         VALUE fieldD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  AnalyticalConst<DESCRIPTOR::d,T,T> fieldF(fieldD);
  sLattice.template defineField<FIELD>(std::move(domainI), fieldF);
}

template <typename FIELD, typename T, typename DESCRIPTOR, typename VALUE>
void setVelocity(SuperLattice<T,DESCRIPTOR>& sLattice,
                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                 VALUE fieldD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  AnalyticalConst<DESCRIPTOR::d,T,T> fieldF(sLattice.getUnitConverter().getLatticeVelocity(fieldD));
  sLattice.template defineField<FIELD>(std::move(domainI), fieldF);
}

}

namespace momenta {

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setDensity(SuperLattice<T,DESCRIPTOR>& sLattice,
                FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                FUNCTOR& densityF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  const auto& converter = sLattice.getUnitConverter();
  AnalyticCalcMultiplication<DESCRIPTOR::d,T,T> scaledDensityF(1/converter.getConversionFactorDensity(),
                                                               densityF);
  sLattice.defineRho(std::move(domainI), scaledDensityF);
}

template <typename T, typename DESCRIPTOR, typename VALUE>
void setDensity(SuperLattice<T,DESCRIPTOR>& sLattice,
                FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                VALUE densityD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  AnalyticalConst<DESCRIPTOR::d,T,T> densityF(densityD);
  setDensity(sLattice, std::move(domainI), densityF);
}

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setElectricPotential(SuperLattice<T,DESCRIPTOR>& sLattice,
                          FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                          FUNCTOR& densityF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  setDensity<T,DESCRIPTOR>(sLattice, std::move(domainI), densityF);
}

template <typename T, typename DESCRIPTOR, typename VALUE>
void setElectricPotential(SuperLattice<T,DESCRIPTOR>& sLattice,
                          FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                          VALUE densityD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  setDensity<T,DESCRIPTOR,VALUE>(sLattice, std::move(domainI), densityD);
}

template <typename T, typename DESCRIPTOR>
void setPressure(SuperLattice<T,DESCRIPTOR>& sLattice,
                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                 AnalyticalF<DESCRIPTOR::d,T,T>& pressureF)
{
  const auto& converter = sLattice.getUnitConverter();
  AnalyticalFfromCallableF<DESCRIPTOR::d,T,T> latticeDensityFromPhysPressureF([&](Vector<T,3> physR)
                                                                               -> Vector<T,1> {
    T p{};
    pressureF(&p, physR.data());
    return converter.getLatticeDensityFromPhysPressure(p);
  });

  sLattice.defineRho(std::move(domainI), latticeDensityFromPhysPressureF);
}

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setIncompressiblePressure(SuperLattice<T,DESCRIPTOR>& sLattice,
                                FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                                FUNCTOR& pressureF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  const auto& converter = sLattice.getUnitConverter();
  AnalyticCalcMultiplication<DESCRIPTOR::d,T,T> scaledPressureF(1/converter.getConversionFactorPressure(),
                                                               pressureF);
  sLattice.defineRho(std::move(domainI), scaledPressureF);
}

template <typename T, typename DESCRIPTOR, typename VALUE>
void setPressure(SuperLattice<T,DESCRIPTOR>& sLattice,
                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                 VALUE pressureD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  AnalyticalConst<DESCRIPTOR::d,T,T> pressureF(pressureD);
  setPressure(sLattice, std::move(domainI), pressureF);
}

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setConcentration(SuperLattice<T,DESCRIPTOR>& sLattice,
                      FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                      FUNCTOR& concentrationF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  setDensity<T,DESCRIPTOR>(sLattice, std::move(domainI), concentrationF);
}

template <typename T, typename DESCRIPTOR, typename VALUE>
void setConcentration(SuperLattice<T,DESCRIPTOR>& sLattice,
                      FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                      VALUE concentrationD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  setDensity<T,DESCRIPTOR,VALUE>(sLattice, std::move(domainI), concentrationD);
}

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setVelocity(SuperLattice<T,DESCRIPTOR>& sLattice,
                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                 FUNCTOR& velocityF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  const auto& converter = sLattice.getUnitConverter();
  AnalyticCalcMultiplication<DESCRIPTOR::d,T,T> scaledVelocityF(1/converter.getConversionFactorVelocity(),
                                                                velocityF);
  sLattice.defineU(std::move(domainI), scaledVelocityF);
}

template <typename T, typename DESCRIPTOR, typename VALUE>
void setVelocity(SuperLattice<T,DESCRIPTOR>& sLattice,
                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                 VALUE velocityD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  AnalyticalConst<DESCRIPTOR::d,T,T> velocityF(velocityD);
  setVelocity(sLattice, std::move(domainI), velocityF);
}

template <typename T, typename DESCRIPTOR>
void setPressureAndVelocity(SuperLattice<T,DESCRIPTOR>& sLattice,
                            FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                            AnalyticalF<DESCRIPTOR::d,T,T>& pressureF,
                            AnalyticalF<DESCRIPTOR::d,T,T>& velocityF)
{
  const auto& converter = sLattice.getUnitConverter();
  AnalyticalFfromCallableF<DESCRIPTOR::d,T,T> latticeDensityFromPhysPressureF([&](Vector<T,3> physR)
                                                                               -> Vector<T,1> {
    T p{};
    pressureF(&p, physR.data());
    return converter.getLatticeDensityFromPhysPressure(p);
  });
  AnalyticCalcMultiplication<DESCRIPTOR::d,T,T> scaledVelocityF(1/converter.getConversionFactorVelocity(),
                                                                velocityF);

  sLattice.defineRhoU(std::move(domainI), latticeDensityFromPhysPressureF, scaledVelocityF);
}

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setTemperature(SuperLattice<T,DESCRIPTOR>& sLattice,
                    FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                    FUNCTOR& temperatureF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  const auto& converter = sLattice.getUnitConverter();
  AnalyticCalcMinus<DESCRIPTOR::d,T,T> relativeTemperatureF(temperatureF, converter.getCharPhysLowTemperature());
  AnalyticCalcMultiplication<DESCRIPTOR::d,T,T> scaledTemperatureF(1/converter.getConversionFactorTemperature(),
                                                               relativeTemperatureF);
  AnalyticCalcPlus<DESCRIPTOR::d,T,T> latticeTemperatureF(scaledTemperatureF, 0.5);
  sLattice.defineRho(std::move(domainI), latticeTemperatureF);
}

template <typename T, typename DESCRIPTOR, typename VALUE>
void setTemperature(SuperLattice<T,DESCRIPTOR>& sLattice,
                    FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                    VALUE temperatureD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  AnalyticalConst<DESCRIPTOR::d,T,T> temperatureF(temperatureD);
  setTemperature(sLattice, std::move(domainI), temperatureF);
}

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setHeatFlux(SuperLattice<T,DESCRIPTOR>& sLattice,
                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                 FUNCTOR& heatFluxF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  const auto& converter = sLattice.getUnitConverter();

  AnalyticalFfromCallableF<DESCRIPTOR::d, T, T> heatFluxL([&](Vector<T, DESCRIPTOR::d> physR) -> Vector<T, DESCRIPTOR::d> {
    Vector<T, DESCRIPTOR::d> heatFluxToLattice;
    heatFluxF(heatFluxToLattice.data(), physR.data());
    T convFactor = converter.getLatticeSpecificHeatCapacity(converter.getPhysSpecificHeatCapacity()) * (converter.getLatticeThermalRelaxationTime() - 0.5) / converter.getLatticeThermalRelaxationTime();
    return Vector<T,DESCRIPTOR::d>([&](int iD) -> T {
      return converter.getLatticeHeatFlux(heatFluxToLattice[iD]) / convFactor;
    });
  });

  sLattice.defineU(std::move(domainI), heatFluxL);
}

template <typename T, typename DESCRIPTOR, typename VALUE>
void setHeatFlux(SuperLattice<T,DESCRIPTOR>& sLattice,
                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                 VALUE heatFluxD)
  requires std::constructible_from<AnalyticalConst<DESCRIPTOR::d,T,T>, VALUE>
{
  Vector<T,DESCRIPTOR::d> heatFluxV = Vector<T,DESCRIPTOR::d>(heatFluxD);
  AnalyticalConst<DESCRIPTOR::d,T,T> heatFluxF((heatFluxV));
  setHeatFlux(sLattice, std::move(domainI), heatFluxF);
}

template <typename T, typename DESCRIPTOR, typename FUNCTOR>
void setOrderParameter(SuperLattice<T,DESCRIPTOR>& sLattice,
                                FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                                FUNCTOR& orderParameterF)
  requires std::derived_from<FUNCTOR, AnalyticalF<DESCRIPTOR::d,T,T>>
{
  sLattice.defineRho(std::move(domainI), orderParameterF);
}

}

namespace equilibria {

template <typename T, typename DESCRIPTOR>
void setPressureAndVelocity(SuperLattice<T,DESCRIPTOR>& sLattice,
                            FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
                            AnalyticalF<DESCRIPTOR::d,T,T>& pressureF,
                            AnalyticalF<DESCRIPTOR::d,T,T>& velocityF)
{
  const auto& converter = sLattice.getUnitConverter();
  AnalyticalFfromCallableF<DESCRIPTOR::d,T,T> latticeDensityFromPhysPressureF([&](Vector<T,3> physR)
                                                                               -> Vector<T,1> {
    T p{};
    pressureF(&p, physR.data());
    return converter.getLatticeDensityFromPhysPressure(p);
  });
  AnalyticCalcMultiplication<DESCRIPTOR::d,T,T> scaledVelocityF(1/converter.getConversionFactorVelocity(),
                                                                velocityF);

  sLattice.iniEquilibrium(std::move(domainI),
                          latticeDensityFromPhysPressureF,
                          scaledVelocityF);
}

}

namespace dynamics {

template <typename T, typename DESCRIPTOR, typename ID>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI,
         ID&& dynamics)
  requires std::constructible_from<DynamicsPromise<T,DESCRIPTOR>, ID>
{
  sLattice.defineDynamics(std::move(domainI), std::move(dynamics));
}

template <template<typename...> typename DYNAMICS, typename T, typename DESCRIPTOR>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI)
{
  set(sLattice, std::move(domainI), meta::id<DYNAMICS<T,DESCRIPTOR>>{});
}

template <typename DYNAMICS, typename T, typename DESCRIPTOR>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& domainI)
{
  set(sLattice, std::move(domainI), meta::id<DYNAMICS>{});
}

template <template<typename...> typename DYNAMICS, typename T, typename DESCRIPTOR>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         SuperGeometry<T,DESCRIPTOR::d>& sGeometry,
         int material)
{
  set(sLattice,
      sGeometry.getMaterialIndicator(material),
      meta::id<DYNAMICS<T,DESCRIPTOR>>{});
}

template <typename DYNAMICS, typename T, typename DESCRIPTOR>
void set(SuperLattice<T,DESCRIPTOR>& sLattice,
         SuperGeometry<T,DESCRIPTOR::d>& sGeometry,
         int material)
{
  set(sLattice,
      sGeometry.getMaterialIndicator(material),
      meta::id<DYNAMICS>{});
}

}

}

#endif
