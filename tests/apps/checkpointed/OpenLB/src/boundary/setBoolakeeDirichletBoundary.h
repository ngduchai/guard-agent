#ifndef BOOLAKEE_DIRICHLET_BOUNDARY_H
#define BOOLAKEE_DIRICHLET_BOUNDARY_H

namespace olb {

// 4. step: Post-processor for Boolakee Dirichlet boundary condition
template <typename T, typename DESCRIPTOR>
class BoolakeeDirichletPostProcessor {
public:
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  int getPriority() const {
    return -1;
  }

  using parameters = meta::list<descriptors::MAGIC_SOLID>;

  template <typename CELL, typename PARAMETERS, typename V = typename CELL::value_t>
  void apply(CELL& cell, PARAMETERS& parameters) any_platform {

    auto magic = parameters.template get<descriptors::MAGIC_SOLID>();
    const V theta     = magic[2];
    const V mu        = magic[3];
    const V lambda    = magic[4];
    const V bulk      = mu + lambda;

    int i, j, oppo;
    V boundaryCoords[2], u_D[2];
    V s_ij;
    V dx_ux, dx_uy, dy_ux, dy_uy;

    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
      const auto localC    = descriptors::c<DESCRIPTOR>(iPop);
      auto neighbor  = cell.neighbor(localC);

      auto q_ij      = neighbor.template getField<descriptors::SOLID_DISTANCE_FIELD>();
      oppo      = descriptors::opposite<DESCRIPTOR>(iPop);
      if (q_ij[oppo] > 0) {

        i = localC[0];
        j = localC[1];

        auto prev_cell       = neighbor.template getField<descriptors::PREVIOUS_CELL>();

        auto boundaryX       = neighbor.template getField<descriptors::BOUNDARY_COORDS_X>();
        auto boundaryY       = neighbor.template getField<descriptors::BOUNDARY_COORDS_Y>();
        boundaryCoords[0] = boundaryX[oppo];
        boundaryCoords[1] = boundaryY[oppo];

        calcU_D<V>(u_D, boundaryCoords);

        auto bared_moments   = neighbor.template getField<descriptors::BARED_MOMENT_VECTOR>();

        dx_ux = -.25 * ((1. / bulk) * bared_moments[3] + (1. / mu) * bared_moments[4]);
        dx_uy = -.25 *   2. / mu    * bared_moments[2];

        dy_ux = -.25 *   2. / mu    * bared_moments[2];
        dy_uy = -.25 * ((1. / bulk) * bared_moments[3] - (1. / mu) * bared_moments[4]);

        // Decide which velocity set to use
        if (i == 0 || j == 0) {
          // V1
          // Zeroth order Eq. 103
          s_ij =           (1. - theta) * (i * u_D[0] + j * u_D[1])
          // First order Eq. 108
               + (1. - theta) * (q_ij[oppo] - 1. / 2.) * (abs(i) * dx_ux + abs(j) * dy_uy);
        } else {
          // V2
          // Zeroth order Eq. 104
          s_ij =           theta / 2. * (i * u_D[0] + j * u_D[1])
          // First order Eq. 109
               + theta / 2. * (q_ij[oppo] - 1. / 2.) * (dx_ux + dy_uy + i * j * (dx_uy + dy_ux));
        }
        // Eq. 93
        cell[iPop] = prev_cell[oppo] + s_ij;
      }
    }
  };

  template <typename V>
  void calcU_D(V (&u_D)[2], const V (&coords)[2]) {
    u_D[0] = 9. / 10000. * sin(2. * M_PI * coords[0] * coords[1]);
    u_D[1] = 7. / 10000. * cos(2. * M_PI * coords[1]) * (coords[0] * coords[0] + 1.);
  };
};


template <typename T, typename DESCRIPTOR>
class BoolakeeDirichletPostProcessorApplication2D {
public:
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  int getPriority() const {
    return -1;
  }

  using parameters = meta::list<descriptors::MAGIC_SOLID>;

  template <typename CELL, typename PARAMETERS, typename V = typename CELL::value_t>
  void apply(CELL& cell, PARAMETERS& parameters) any_platform {

    auto magic = parameters.template get<descriptors::MAGIC_SOLID>();
    const V theta     = magic[2];
    const V mu        = magic[3];
    const V lambda    = magic[4];
    const V bulk      = mu + lambda;

    int i, j, oppo;
    Vector<V,2> localC, oppoC, boundaryCoords, u_D;
    Vector<V,DESCRIPTOR::q> q_ij, prev_cell, boundaryX, boundaryY, bared_moments;
    T s_ij;
    T dx_ux, dx_uy, dy_ux, dy_uy;

    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
      localC    = descriptors::c<DESCRIPTOR>(iPop);
      auto neighbor  = cell.neighbor(localC);

      q_ij      = neighbor.template getField<descriptors::SOLID_DISTANCE_FIELD>();
      oppo      = descriptors::opposite<DESCRIPTOR>(iPop);
      if (q_ij[oppo] > 0) {

        i = localC[0];
        j = localC[1];

        prev_cell       = neighbor.template getField<descriptors::PREVIOUS_CELL>();

        boundaryX       = neighbor.template getField<descriptors::BOUNDARY_COORDS_X>();
        boundaryY       = neighbor.template getField<descriptors::BOUNDARY_COORDS_Y>();
        boundaryCoords  = {boundaryX[oppo], boundaryY[oppo]};

        u_D = {0., 0.};

        bared_moments   = neighbor.template getField<descriptors::BARED_MOMENT_VECTOR>();

        dx_ux = -.25 * ((1. / bulk) * bared_moments[3] + (1. / mu) * bared_moments[4]);
        dx_uy = -.25 *   2. / mu    * bared_moments[2];

        dy_ux = -.25 *   2. / mu    * bared_moments[2];
        dy_uy = -.25 * ((1. / bulk) * bared_moments[3] - (1. / mu) * bared_moments[4]);

        // Decide which velocity set to use
        if (i == 0 || j == 0) {
          // V1
          // Zeroth order Eq. 103
          s_ij =           (1. - theta) * (i * u_D[0] + j * u_D[1])
          // First order Eq. 108
               + (1. - theta) * (q_ij[oppo] - 1. / 2.) * (abs(i) * dx_ux + abs(j) * dy_uy);
        } else {
          // V2
          // Zeroth order Eq. 104
          s_ij =           theta / 2. * (i * u_D[0] + j * u_D[1])
          // First order Eq. 109
               + theta / 2. * (q_ij[oppo] - 1. / 2.) * (dx_ux + dy_uy + i * j * (dx_uy + dy_ux));
        }
        // Eq. 93
        cell[iPop] = prev_cell[oppo] + s_ij;
      }
    }
  };
};

  // Anything
  // 3. step: Iteration over all solid cells
  template <typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeDirichletBoundary( BlockLattice<T,DESCRIPTOR>& block,
                                  BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& bulkIndicator,
                                  IndicatorF<T,DESCRIPTOR::d>& indicatorAnalyticalBoundary,
                                  bool verbose = true)
  {
    OstreamManager clout(std::cout, "BoolakeeDirichletBoundarySetter");
    clout.setMultiOutput(true);

    T dist, qIpop, norm;
    bool hasBoundary;

    const T deltaR = blockGeometry.getDeltaR();
    // for each solid cell: all of its fluid neighbors need population updates
    block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> node) {
      // Check if cell is solid cell
      if (boundaryIndicator(node)) {
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          const auto c = descriptors::c<DESCRIPTOR>(iPop);
          const auto bulk  = node + c;

          if (blockGeometry.isInside(bulk)) {
          // check if neighbor is fluid cell
          if (bulkIndicator(bulk)) {
            // Get coordinates of neighbor node because we need to calculate q_ij
            auto bulkPhysR = blockGeometry.getPhysR(bulk);

            const int oppo = descriptors::opposite<DESCRIPTOR>(iPop);
            const auto oppoC = descriptors::c<DESCRIPTOR>(oppo);
            dist = -1;    // distance to boundary
            qIpop = -1;   // normed distance (Bouzidi distance) to boundary
            norm = deltaR * util::norm<DESCRIPTOR::d>(c);
            hasBoundary = indicatorAnalyticalBoundary.distance(dist, bulkPhysR, oppoC, blockGeometry.getIcGlob());
            exit(1);
            // Check if distance calculation was performed correctly
            if (hasBoundary) {
              qIpop = dist / norm;

              // if distance function returned a dist. not suitable for Bouzidi -> fall-back
              if ((qIpop < 0) || (qIpop > 1)) {
                if (verbose) {
                  clout << "Error, non suitable dist. at lattice: (" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction " << iPop << ". Fall-back to bounce-back." << std::endl;
                }
                // fall-back: half-way bounce back
                qIpop = 0.5;
              }
            }
            // if distance function couldn't compute any distance -> fall-back
            else {
              if (verbose) {
                std::cout << "qIpop: " << qIpop << std::endl;
                std::cout << "dist: " << dist << std::endl;
                clout << "Error, no boundary found at lattice:(" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction: " << iPop << ".Fall-back to bounce-back." << std::endl;
              }
              // fall-back: half-way bounce back
              qIpop = 0.5;
            }
            block.get(bulk).template setFieldComponent<descriptors::SOLID_DISTANCE_FIELD>(oppo, qIpop);

            block.get(bulk).template setFieldComponent<descriptors::CELL_COORDS>(0, bulkPhysR[0]);
            block.get(bulk).template setFieldComponent<descriptors::CELL_COORDS>(1, bulkPhysR[1]);

            Vector<T,2> boundary{
              bulkPhysR[0] + oppoC[0] * qIpop * deltaR,
              bulkPhysR[1] + oppoC[1] * qIpop * deltaR,
            };

            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_X>(oppo, boundary[0]);
            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_Y>(oppo, boundary[1]);
          }
          }
        }
        if (!block.isPadding(node)) {
          block.addPostProcessor(typeid(stage::PostCollide),
                                 node,
                                 meta::id<OPERATOR>{});
        }
      }
    });
  };

  // 2. step
  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeDirichletBoundary(SuperLattice<T, DESCRIPTOR>& sLattice,
                                    FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                                    FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& bulkIndicator,
                                    IndicatorF<T,DESCRIPTOR::d>&                   indicatorAnalyticalBoundary)
  {
    OstreamManager clout(std::cout, "BoolakeeDirichletBoundarySetter");
    auto& load = sLattice.getLoadBalancer();
    for (int iC=0; iC < load.size(); ++iC) {
      setBoolakeeDirichletBoundary<T,DESCRIPTOR, OPERATOR>( sLattice.getBlock(iC),
                                                      ( bulkIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                                        boundaryIndicator->getBlockIndicatorF(iC),
                                                        bulkIndicator->getBlockIndicatorF(iC),
                                                        indicatorAnalyticalBoundary);
    }
    clout.setMultiOutput(false);
  }

  /// 1. Start: Copied from Bouzidi
  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeDirichletBoundary(SuperLattice<T, DESCRIPTOR>& sLattice,
                                    SuperGeometry<T,DESCRIPTOR::d>& superGeometry,
                                    int materialOfSolidObstacle,
                                    IndicatorF<T,DESCRIPTOR::d>& indicatorAnalyticalBoundary,
                                    std::vector<int> bulkMaterials = std::vector<int>(1,1))
  {
    //Getting the indicators by material numbers and calling the superLattice method via the indicators:
    setBoolakeeDirichletBoundary<T,DESCRIPTOR,OPERATOR>(sLattice,
                        FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>(superGeometry.getMaterialIndicator(materialOfSolidObstacle)),
                        FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>(superGeometry.getMaterialIndicator(std::move(bulkMaterials))),
                        indicatorAnalyticalBoundary);
  }


// Ellipse specific
template <typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeDirichletBoundary( BlockLattice<T,DESCRIPTOR>& block,
                                  BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& bulkIndicator,
                                  IndicatorEllipse2D<T>& indicatorAnalyticalBoundary,
                                  bool verbose = true)
  {
    OstreamManager clout(std::cout, "BoolakeeDirichletBoundarySetter");
    clout.setMultiOutput(true);

    int oppo;
    Vector<T, DESCRIPTOR::d> c, oppoC;
    T dist, qIpop, norm;
    bool hasBoundary;

    const T deltaR = blockGeometry.getDeltaR();
    // for each solid cell: all of its fluid neighbors need population updates
    block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> node) {
      // Check if cell is solid cell
      if (boundaryIndicator(node)) {
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          c = descriptors::c<DESCRIPTOR>(iPop);
          Vector<T,DESCRIPTOR::d> bulk(node + c);

          // check if neighbor is fluid cell
          if (bulkIndicator(bulk)) {
            // Get coordinates of neighbor node because we need to calculate q_ij
            olb::Vector<T, DESCRIPTOR::d> physCoords;
            blockGeometry.getPhysR(physCoords, bulk);
            Vector<T,DESCRIPTOR::d> bulkPhysR = {physCoords[0], physCoords[1]};

            oppo = descriptors::opposite<DESCRIPTOR>(iPop);
            oppoC = descriptors::c<DESCRIPTOR>(oppo);
            dist = -1;    // distance to boundary
            qIpop = -1;   // normed distance (Bouzidi distance) to boundary
            norm = deltaR * util::norm<DESCRIPTOR::d>(c);
            hasBoundary = indicatorAnalyticalBoundary.distance(dist, bulkPhysR, oppoC);
            // Check if distance calculation was performed correctly
            if (hasBoundary) {
              qIpop = dist / norm;

              // if distance function returned a dist. not suitable for Bouzidi -> fall-back
              if ((qIpop < 0) || (qIpop > 1)) {
                if (verbose) {
                  // clout << "dist " << qIpop << std::endl;
                  clout << "Error, non suitable dist. at lattice: (" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction " << iPop << ". Fall-back to bounce-back." << std::endl;
                  // exit(1);
                }
                // fall-back: half-way bounce back
                qIpop = 0.5;
              }
            }
            // if distance function couldn't compute any distance -> fall-back
            else {
              if (verbose) {
                clout << "Error, no boundary found at lattice:(" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction: " << iPop << ".Fall-back to bounce-back." << std::endl;
              }
              // fall-back: half-way bounce back
              qIpop = 0.5;
            }
            block.get(bulk).template setFieldComponent<descriptors::SOLID_DISTANCE_FIELD>(oppo, qIpop);

            block.get(bulk).template setFieldComponent<descriptors::CELL_COORDS>(0, bulkPhysR[0]);
            block.get(bulk).template setFieldComponent<descriptors::CELL_COORDS>(1, bulkPhysR[1]);

            Vector<T,2> boundary = {
              bulkPhysR[0] + oppoC[0] * qIpop * deltaR,
              bulkPhysR[1] + oppoC[1] * qIpop * deltaR,
            };

            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_X>(oppo, boundary[0]);
            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_Y>(oppo, boundary[1]);
          }
        }
        block.addPostProcessor(typeid(stage::PostCollide),
        node,
        meta::id<OPERATOR>{});
      }
    });
  };


  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeDirichletBoundary( SuperLattice<T, DESCRIPTOR>& sLattice,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& bulkIndicator,
                                  IndicatorEllipse2D<T>& indicatorAnalyticalBoundary)
  {
    OstreamManager clout(std::cout, "BoolakeeDirichletBoundarySetter");
    auto& load = sLattice.getLoadBalancer();
    for (int iC=0; iC < load.size(); ++iC) {
      setBoolakeeDirichletBoundary<T,DESCRIPTOR, OPERATOR>( sLattice.getBlock(iC),
                                                      ( bulkIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                                        boundaryIndicator->getBlockIndicatorF(iC),
                                                        bulkIndicator->getBlockIndicatorF(iC),
                                                        indicatorAnalyticalBoundary);
    }
    clout.setMultiOutput(false);
  }

// Cuboid specific

template <typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeDirichletBoundary( BlockLattice<T,DESCRIPTOR>& block,
                                  BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& bulkIndicator,
                                  IndicatorCuboid2D<T>& indicatorAnalyticalBoundary,
                                  bool verbose = true)
  {
    OstreamManager clout(std::cout, "BoolakeeDirichletBoundarySetter");
    clout.setMultiOutput(true);

    int oppo;
    Vector<T, DESCRIPTOR::d> c, oppoC;
    T dist, qIpop, norm;
    bool hasBoundary;

    const T deltaR = blockGeometry.getDeltaR();
    // for each solid cell: all of its fluid neighbors need population updates
    block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> node) {
      // Check if cell is solid cell
      if (boundaryIndicator(node)) {
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          c = descriptors::c<DESCRIPTOR>(iPop);
          Vector<T,DESCRIPTOR::d> bulk(node + c);

          // check if neighbor is fluid cell
          if (bulkIndicator(bulk)) {
            // Get coordinates of neighbor node because we need to calculate q_ij
            olb::Vector<T, DESCRIPTOR::d> physCoords;
            blockGeometry.getPhysR(physCoords, bulk);
            Vector<T,DESCRIPTOR::d> bulkPhysR = {physCoords[0], physCoords[1]};

            oppo = descriptors::opposite<DESCRIPTOR>(iPop);
            oppoC = descriptors::c<DESCRIPTOR>(oppo);
            dist = -1;    // distance to boundary
            qIpop = -1;   // normed distance (Bouzidi distance) to boundary
            norm = deltaR * util::norm<DESCRIPTOR::d>(c);
            hasBoundary = indicatorAnalyticalBoundary.distance(dist, bulkPhysR, oppoC, blockGeometry.getIcGlob());
            // Check if distance calculation was performed correctly
            if (hasBoundary) {
              qIpop = dist / norm;

              // if distance function returned a dist. not suitable for Bouzidi -> fall-back
              if ((qIpop < 0) || (qIpop > 1)) {
                if (verbose) {
                  clout << "Error, non suitable dist. at lattice: (" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction " << iPop << ". Fall-back to bounce-back." << std::endl;
                }
                // fall-back: half-way bounce back
                qIpop = 0.5;
              }
            }
            // if distance function couldn't compute any distance -> fall-back
            else {
              if (verbose) {
                clout << "Error, no boundary found at lattice:(" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction: " << iPop << ".Fall-back to bounce-back." << std::endl;
              }
              // fall-back: half-way bounce back
              qIpop = 0.5;
            }
            block.get(bulk).template setFieldComponent<descriptors::SOLID_DISTANCE_FIELD>(oppo, qIpop);

            block.get(bulk).template setFieldComponent<descriptors::CELL_COORDS>(0, bulkPhysR[0]);
            block.get(bulk).template setFieldComponent<descriptors::CELL_COORDS>(1, bulkPhysR[1]);

            Vector<T,2> boundary = {
              bulkPhysR[0] + oppoC[0] * qIpop * deltaR,
              bulkPhysR[1] + oppoC[1] * qIpop * deltaR,
            };

            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_X>(oppo, boundary[0]);
            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_Y>(oppo, boundary[1]);
          }
        }
        block.addPostProcessor(typeid(stage::PostCollide),
        node,
        meta::id<OPERATOR>{});
      }
    });
  };

  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeDirichletBoundary( SuperLattice<T, DESCRIPTOR>& sLattice,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& bulkIndicator,
                                  IndicatorCuboid2D<T>& indicatorAnalyticalBoundary)
  {
    OstreamManager clout(std::cout, "BoolakeeDirichletBoundarySetter");
    auto& load = sLattice.getLoadBalancer();
    for (int iC=0; iC < load.size(); ++iC) {
      setBoolakeeDirichletBoundary<T,DESCRIPTOR, OPERATOR>( sLattice.getBlock(iC),
                                                      ( bulkIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                                        boundaryIndicator->getBlockIndicatorF(iC),
                                                        bulkIndicator->getBlockIndicatorF(iC),
                                                        indicatorAnalyticalBoundary);
    }
    clout.setMultiOutput(false);
  }

};

#endif
