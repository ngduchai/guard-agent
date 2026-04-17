#ifndef BOOLAKEE_NEUMANN_BOUNDARY_H
#define BOOLAKEE_NEUMANN_BOUNDARY_H

namespace olb {

  template <typename T, typename DESCRIPTOR>
  class BoolakeeNeumannPostProcessor {
    public:

    static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;
      using parameters = meta::list<descriptors::NEUMANN_SOLID_C,descriptors::MAGIC_SOLID>;

      int getPriority() const {
        return 0;
      }

      template <typename CELL, typename PARAMETERS, typename V = typename CELL::value_t>
      void apply(CELL& cell, PARAMETERS& parameters) any_platform
      {

        V pi = std::numbers::pi_v<double>;
        auto tmp = parameters.template get<descriptors::NEUMANN_SOLID_C>();
        V constants[3] {tmp[0], tmp[1], tmp[2]};
        auto magic = parameters.template get<descriptors::MAGIC_SOLID>();

        V dx = magic[0];
        V dt = magic[1];
        V mu = magic[3];
        V lambda = magic[4];
        V kappa = magic[5];
        V bulk = mu + lambda;
        // V epsilon = dx;

        int i, j, zeta, dim, oppo;
        V nx, ny;
        V s_ij, Tx, Ty, sum, weight, boundaryX, boundaryY;

        V latticeFactor = dt / (kappa * dx);

        // Iterate over all directions
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          auto c = descriptors::c<DESCRIPTOR>(iPop);
          oppo = descriptors::opposite<DESCRIPTOR>(iPop);
          auto neighbor = cell.neighbor(c);
          auto q_ij = neighbor.template getField<descriptors::SOLID_DISTANCE_FIELD>();
          if (q_ij[oppo] > 0) {
            i = c[0];
            j = c[1];
            boundaryX = neighbor.template getField<descriptors::BOUNDARY_COORDS_X>()[oppo];
            boundaryY = neighbor.template getField<descriptors::BOUNDARY_COORDS_Y>()[oppo];

            nx = neighbor.template getField<descriptors::NEUMANN_SOLID_NORMAL_X>()[oppo];
            ny = neighbor.template getField<descriptors::NEUMANN_SOLID_NORMAL_Y>()[oppo];

            if (util::abs(ny) > util::abs(nx))
            {
              zeta = 1;
            }
            else
            {
              zeta = -1;
            }

            // Calc stress components at boundary in lattice units
            // Eq. 68 to 70
            /*
            */
            V sigma_xx = latticeFactor * ((bulk + mu) * 0.0018*pi*boundaryY*util::cos(2*pi* boundaryX * boundaryY) + (bulk - mu) * -0.0014*pi*(boundaryX * boundaryX + 1)*util::sin(2*pi*boundaryY));

            V sigma_xy = latticeFactor * (mu * (0.0014*boundaryX*util::cos(2*pi*boundaryY) + 0.0018*pi*boundaryX*util::cos(2*pi*boundaryX*boundaryY)));

            V sigma_yx = sigma_xy;

            V sigma_yy = latticeFactor * ((bulk - mu) * 0.0018*pi*boundaryY*util::cos(2*pi* boundaryX * boundaryY) + (bulk + mu) * -0.0014*pi*(boundaryX * boundaryX + 1)*util::sin(2*pi*boundaryY));

            V stress_tensor[4] = {sigma_xx, sigma_xy, sigma_yx, sigma_yy};
            // V stress_tensor[4] = {0., 0., 0., 0.};
            // V params[2] = {mu, lambda};
            // calcStress(stress_tensor, latticeFactor, boundaryCoords, params);

            // Eq. 113
            Tx = stress_tensor[0] * nx + stress_tensor[1] * ny;
            Ty = stress_tensor[2] * nx + stress_tensor[3] * ny;

            sum = 0.;
            for (int k = -1; k <= 1; k += 1)
            {
              for (int l = -1; l <= 1; l += 1)
              {
                if (k != 0 || l != 0)
                {
                  findDim(dim, k, l);
                  calcWeight<V>(weight, i, j, k, l, zeta, nx, ny, constants);
                  sum = sum + (weight * neighbor[dim]);
                }
              }
            }
            s_ij = 0;
            if (i == 0 || j == 0)
            {
              firstOrderSourceNu1<V>(s_ij, i, j, Tx, Ty);
            }
            else
            {
              firstOrderSourceNu2<V>(s_ij, i, j, Tx, Ty, zeta);
            }
            cell[iPop] = sum + s_ij;
          }
          else
          {
            cell[iPop] = NAN;
          }
        }
    };

    template <typename V>
    void calcWeight(V& weight, const int i, const int j, const int k, const int l, const int zeta, const V& nx, const V& ny, V constants[3])// const Vector<T, 3>& c)
    {
      // Kronecker Delta
      int theta_ij;
      if (i == -k && j == -l)
      {
        theta_ij = 1;
      }
      else
      {
        theta_ij = 0;
      }

      // Decide which velocity set to use
      if (i == 0 || j == 0)
      {
        // V1
        weight = -util::abs(k) * util::abs(l) * (1 + i * nx + j * ny) * constants[0]
               - k * l * (i * ny + j * nx) * constants[1]
               - (util::abs(k) * (1 - util::abs(l)) * (util::abs(i) + i * nx) + util::abs(l) * (1 - util::abs(k)) * (util::abs(j) + j * ny)) * constants[2]
               - theta_ij;
      }
      else
      {

        // V2
        weight = -1. / 2. * util::abs(k) * util::abs(l) * ((1 + zeta) / 2. * i * nx + (1 - zeta) / 2. * j * ny) * constants[0]
               - 1. / 2. * k * l * (i * j + (1 + zeta) / 2. * i * ny + (1 - zeta) / 2. * j * nx) * constants[1]
               - 1. / 2. * (  util::abs(k) * (1 - util::abs(l)) * (1 + zeta) / 2. * i * nx
                            + util::abs(l) * (1 - util::abs(k)) * (1 - zeta) / 2. * j * ny) * constants[2]
               - theta_ij;
      }
    };

    template <typename V>
    void calcStress(V (&sigma)[4], const V& latticeFactor, const V (&coords)[2], const V (&params)[2])
    {
      T x = coords[0];
      T y = coords[1];
      T mu = params[0];
      T lambda = params[1];
      sigma[0] = latticeFactor * ((2. * mu + lambda) * 0.0018 * M_PI * y * util::cos(2. * M_PI * x * y) + lambda * -0.0014 * M_PI * (x * x + 1.) * util::sin(2 * M_PI * y));
      sigma[1] = latticeFactor * (mu * (0.0018 * M_PI * x * util::cos(2 * M_PI * x * y) + 0.0014 * x * util::cos(2 * M_PI     * y)));
      sigma[2] = latticeFactor * (mu * (0.0018 * M_PI * x * util::cos(2 * M_PI * x * y) + 0.0014 * x * util::cos(2 * M_PI     * y)));
      sigma[3] = latticeFactor * ((2. * mu + lambda) * -0.0014 * M_PI * (x * x + 1.) * util::sin(2 * M_PI * y) + lambda * 0.0018 * M_PI * y * util::cos(2. * M_PI * x * y));
    };

    // Eq. 147
    template <typename V>
    void firstOrderSourceNu1(V& sTerm, const int i, const int j, const V& Tx, const V& Ty)
    {
      sTerm = (i * Tx + j * Ty);
    };


    // Eq. 148
    template <typename V>
    void firstOrderSourceNu2(V& sTerm, const int i, const int j, const V& Tx, const V& Ty, const int zeta)
    {
     sTerm = 1. / 4. * (i * Tx * (1 + zeta) + j * Ty * (1 - zeta));
    };

    void findDim(int& dim, const int i, const int j)
    {
      for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop)
      {
        Vector<int, 2> c = descriptors::c<DESCRIPTOR>(iPop);
        if (i == c[0] && j == c[1])
        {
          dim = iPop;
          return;
        }
      }
    };
  };


  template <typename T, typename DESCRIPTOR>
  class BoolakeeNeumannPostProcessorApplication2D {
    public:
      static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

      using parameters = meta::list<descriptors::NEUMANN_SOLID_C, descriptors::MAGIC_SOLID>;

      int getPriority() const {
        return -1;
      }

      template <typename CELL, typename PARAMETERS, typename V = typename CELL::value_t>
      void apply(CELL& cell, PARAMETERS& parameters) any_platform {

        auto tmp = parameters.template get<descriptors::NEUMANN_SOLID_C>();
        V constants[3] {tmp[0], tmp[1], tmp[2]};
        auto magic = parameters.template get<descriptors::MAGIC_SOLID>();

        V dx = magic[0];
        V dt = magic[1];
        V theta = magic[2];
        V mu = magic[3];
        V lambda = magic[4];
        V kappa = magic[5];
        V bulk = mu + lambda;

        int i, j, zeta, dim, oppo;
        V nx, ny;
        V s_ij, a_ijkl, Tx, Ty, sum, epsilon, weight, boundaryX, boundaryY;

        V latticeFactor = dt / (kappa * dx);

        // Iterate over all directions
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          auto c = descriptors::c<DESCRIPTOR>(iPop);
          oppo = descriptors::opposite<DESCRIPTOR>(iPop);
          auto neighbor = cell.neighbor(c);
          auto q_ij = neighbor.template getField<descriptors::SOLID_DISTANCE_FIELD>();
          if (q_ij[oppo] > 0) {
            i = c[0];
            j = c[1];

            nx = neighbor.template getField<descriptors::NEUMANN_SOLID_NORMAL_X>()[oppo];
            ny = neighbor.template getField<descriptors::NEUMANN_SOLID_NORMAL_Y>()[oppo];

            if (util::abs(ny) > util::abs(nx))
            {
              zeta = 1;
            }
            else
            {
              zeta = -1;
            }

            // Eq. 113
            auto cellCoords = neighbor.template getField<descriptors::CELL_COORDS>();
            if (cellCoords[0] <= dx) {
              Tx = latticeFactor * 0.00001;
              Ty = latticeFactor * 0.;
            }
            else
            {
              Tx = 0.;
              Ty = 0.;
            }


            sum = 0.;
            for (int k = -1; k <= 1; k += 1)
            {
              for (int l = -1; l <= 1; l += 1)
              {
                if (k != 0 || l != 0)
                {
                  findDim(dim, k, l);
                  calcWeight<V>(weight, i, j, k, l, zeta, nx, ny, constants);
                  sum += (weight * neighbor[dim]);
                }
              }
            }
            s_ij = 0;
            if (i == 0 || j == 0)
            {
              firstOrderSourceNu1<V>(s_ij, i, j, Tx, Ty);
            }
            else
            {
              firstOrderSourceNu2<V>(s_ij, i, j, Tx, Ty, zeta);
            }
            cell[iPop] = sum + s_ij;
          }
        }
    };

    template <typename V>
    void calcWeight(V& weight, const int& i, const int& j, const int& k, const int& l, const int& zeta, const V& nx, const V& ny, const V constants[3])
    {
      // Kronecker Delta
      int theta_ij;
      if (i == -k && j == -l)
      {
        theta_ij = 1;
      }
      else
      {
        theta_ij = 0;
      }

      // Decide which velocity set to use
      if (i == 0 || j == 0)
      {
        // V1
        weight = - util::abs(k) * util::abs(l) * (1 + i * nx + j * ny) * constants[0]
                 - k * l * (i * ny + j * nx) * constants[1]
                 - (util::abs(k) * (1 - util::abs(l)) * (util::abs(i) + i * nx) + util::abs(l) * (1 - util::abs(k)) * (util::abs(j) + j * ny)) * constants[2]
                 - theta_ij;
      }
      else
      {
        // V2
        weight = - 1. / 2. * util::abs(k) * util::abs(l) * ((1 + zeta) / 2. * i * nx + (1 - zeta) / 2. * j * ny) * constants[0]
                 - 1. / 2. * k * l * (i * j + (1 + zeta) / 2. * i * ny + (1 - zeta) / 2. * j * nx) * constants[1]
                 - 1. / 2. * (  util::abs(k) * (1 - util::abs(l)) * (1 + zeta) / 2. * i * nx
                              + util::abs(l) * (1 - util::abs(k)) * (1 - zeta) / 2. * j * ny) * constants[2]
                 - theta_ij;
      }
    };

    // Eq. 147
    template <typename V>
    void firstOrderSourceNu1(V& sTerm, const int& i, const int& j, const V& Tx, const V& Ty)
    {
      sTerm = (i * Tx + j * Ty);
    };

    // Eq. 148
    template <typename V>
    void firstOrderSourceNu2(V& sTerm, const int& i, const int& j, const V& Tx, const V& Ty, const int& zeta)
    {
      sTerm = 1. / 4. * (i * Tx * (1 + zeta) + j * Ty * (1 - zeta));
    };

    void findDim(int& dim, const int& i, const int& j)
    {
      for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop)
      {
        Vector<T, 2> c = descriptors::c<DESCRIPTOR>(iPop);
        if (i == c[0] && j == c[1])
        {
          dim = iPop;
          return;
        }
      }
    };
  };


  // Cuboid
  /// Set Boolakee Neumann boundary on indicated cells of block lattice
  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary(BlockLattice<T,DESCRIPTOR>& block,
                                  BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& bulkIndicator,
                                  IndicatorCuboid2D<T>& indicatorAnalyticalBoundary,
                                  bool outward,
                                  bool verbose = true)
  {
    OstreamManager clout(std::cout, "BoolakeeNeumannBoundarySetter");
    clout.setMultiOutput(true);

    const T deltaR = blockGeometry.getDeltaR();
    // for each solid cell: all of its fluid neighbors need population updates
    block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> node) {
      // Check if cell is solid cell
      if (boundaryIndicator(node)) {
        T nodeCoords[DESCRIPTOR::d] { };
        blockGeometry.getPhysR(nodeCoords, node);
        block.get(node).template setFieldComponent<descriptors::CELL_COORDS>(0, nodeCoords[0]);
        block.get(node).template setFieldComponent<descriptors::CELL_COORDS>(1, nodeCoords[1]);
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          Vector<T,DESCRIPTOR::d> bulk(node + descriptors::c<DESCRIPTOR>(iPop));
          const auto c = descriptors::c<DESCRIPTOR>(iPop);
          const auto oppo = descriptors::opposite<DESCRIPTOR>(iPop);
          Vector<T, 2> oppoC = descriptors::c<DESCRIPTOR>(oppo);

          olb::Vector<T, DESCRIPTOR::d> physCoords;
          blockGeometry.getPhysR(physCoords, bulk);
          Vector<T,2> bulkPhysR = {physCoords[0], physCoords[1]};
          // check if neighbor is fluid cell
          if (bulkIndicator(bulk)) {
            Vector<T, 2> normal;
            T dist = -1;    // distance to boundary
            T qIpop = -1;   // normed distance to boundary
            const T norm = deltaR * util::norm<DESCRIPTOR::d>(c);
            bool hasBoundary = indicatorAnalyticalBoundary.distance(dist, bulkPhysR, oppoC, blockGeometry.getIcGlob());

            // Check if distance calculation was performed correctly
            if (hasBoundary) {
              qIpop = dist / norm;

              // if distance function returned a dist. -> fall-back
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
              bulkPhysR[1] + oppoC[1] * qIpop * deltaR
            };

            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_X>(oppo, boundary[0]);
            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_Y>(oppo, boundary[1]);

            // Set normal vector
            bool hasNormal = indicatorAnalyticalBoundary.normal(normal, boundary);
            if (! hasNormal) {
              if (verbose) {
                std::cout << "Normal not found at lattice:(" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction: " << iPop << ". Fall-back to normal [0 0]." << std::endl;
              }
              normal[0] = 0;
              normal[1] = 0;
            }
            if (! outward) {
              normal[0] = -1 * normal[0];
              normal[1] = -1 * normal[1];
            }
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_X>(oppo, normal[0]);
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_Y>(oppo, normal[1]);
          }
        }
        block.addPostProcessor(typeid(stage::PostCollide),
        node,
        meta::id<OPERATOR>{});
      }

    });
  };


  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary( SuperLattice<T, DESCRIPTOR>& sLattice,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& bulkIndicator,
                                  IndicatorCuboid2D<T>& indicatorAnalyticalBoundary,
                                  bool outward = true)
  {
    OstreamManager clout(std::cout, "SolidNeumannBoundarySetter");
    auto& load = sLattice.getLoadBalancer();
    for (int iC=0; iC < load.size(); ++iC) {
      setBoolakeeNeumannBoundary<T,DESCRIPTOR,OPERATOR>( sLattice.getBlock(iC),
                                                ( bulkIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                                boundaryIndicator->getBlockIndicatorF(iC),
                                                bulkIndicator->getBlockIndicatorF(iC),
                                                indicatorAnalyticalBoundary,
                                                outward);
    }
    clout.setMultiOutput(false);
  }


  // Ellipse
   /// Set Boolakee Neumann boundary on indicated cells of block lattice
  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary(BlockLattice<T,DESCRIPTOR>& block,
                          BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                          BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                          BlockIndicatorF<T,DESCRIPTOR::d>& bulkIndicator,
                          IndicatorEllipse2D<T>& indicatorAnalyticalBoundary,
                          bool outward,
                          bool verbose = true)
  {
    OstreamManager clout(std::cout, "BoolakeeNeumannBoundarySetter");
    clout.setMultiOutput(true);

    const T deltaR = blockGeometry.getDeltaR();
    // for each solid cell: all of its fluid neighbors need population updates
    block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> node) {
      // Check if cell is solid cell
      if (boundaryIndicator(node)) {
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          Vector<T,DESCRIPTOR::d> bulk(node + descriptors::c<DESCRIPTOR>(iPop));
          const auto c = descriptors::c<DESCRIPTOR>(iPop);
          const auto oppo = descriptors::opposite<DESCRIPTOR>(iPop);
          Vector<T, 2> oppoC = descriptors::c<DESCRIPTOR>(oppo);

          olb::Vector<T, DESCRIPTOR::d> physCoords;
          blockGeometry.getPhysR(physCoords, bulk);
          Vector<T,DESCRIPTOR::d> bulkPhysR = {physCoords[0], physCoords[1]};
          // check if neighbor is fluid cell
          if (bulkIndicator(bulk)) {
            Vector<T, 2> normal;
            T dist = -1;    // distance to boundary
            T qIpop = -1;   // normed distance to boundary
            const T norm = deltaR * util::norm<DESCRIPTOR::d>(descriptors::c<DESCRIPTOR>(iPop));
            bool hasBoundary = indicatorAnalyticalBoundary.distance(dist, bulkPhysR, oppoC, blockGeometry.getIcGlob());
            // Check if distance calculation was performed correctly
            if (hasBoundary) {
              qIpop = dist / norm;

              // if distance function returned a dist. -> fall-back
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
              bulkPhysR[1] + oppoC[1] * qIpop * deltaR
            };

            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_X>(oppo, boundary[0]);
            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_Y>(oppo, boundary[1]);

            // Set normal vector
            bool hasNormal = indicatorAnalyticalBoundary.normal(normal, boundary);
            if (! hasNormal) {
              if (verbose) {
                std::cout << "Normal not found at lattice:(" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction: " << iPop << ". Fall-back to normal [0 0]." << std::endl;
              }
              normal[0] = 0;
              normal[1] = 0;
            }
            if (! outward) {
              normal[0] = -1 * normal[0];
              normal[1] = -1 * normal[1];
            }
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_X>(oppo, normal[0]);
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_Y>(oppo, normal[1]);
          }
        }
        block.addPostProcessor(typeid(stage::PostCollide),
        node,
        meta::id<OPERATOR>{});
      }

    });
  };


  // Ellipse
  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary( SuperLattice<T, DESCRIPTOR>& sLattice,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& bulkIndicator,
                                  IndicatorEllipse2D<T>& indicatorAnalyticalBoundary,
                                  bool outward = true)
  {
    OstreamManager clout(std::cout, "SolidNeumannBoundarySetter");
    auto& load = sLattice.getLoadBalancer();
    for (int iC=0; iC < load.size(); ++iC) {
      setBoolakeeNeumannBoundary<T,DESCRIPTOR, OPERATOR>( sLattice.getBlock(iC),
                                                ( bulkIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                                boundaryIndicator->getBlockIndicatorF(iC),
                                                bulkIndicator->getBlockIndicatorF(iC),
                                                indicatorAnalyticalBoundary,
                                                outward);
    }
    clout.setMultiOutput(false);
  }



// Circle
  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary(BlockLattice<T,DESCRIPTOR>& block,
                          BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                          BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                          BlockIndicatorF<T,DESCRIPTOR::d>& bulkIndicator,
                          IndicatorCircle2D<T>& indicatorAnalyticalBoundary,
                          bool outward,
                          bool verbose = true)
  {
    OstreamManager clout(std::cout, "BoolakeeNeumannBoundarySetter");
    clout.setMultiOutput(true);

    const T deltaR = blockGeometry.getDeltaR();
    // for each solid cell: all of its fluid neighbors need population updates
    block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> node) {
      // Check if cell is solid cell
      if (boundaryIndicator(node)) {
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          Vector<T,DESCRIPTOR::d> bulk(node + descriptors::c<DESCRIPTOR>(iPop));
          const auto c = descriptors::c<DESCRIPTOR>(iPop);
          const auto oppo = descriptors::opposite<DESCRIPTOR>(iPop);
          Vector<T, 2> oppoC = descriptors::c<DESCRIPTOR>(oppo);

          olb::Vector<T, DESCRIPTOR::d> physCoords;
          blockGeometry.getPhysR(physCoords, bulk);
          Vector<T,DESCRIPTOR::d> bulkPhysR = {physCoords[0], physCoords[1]};
          // check if neighbor is fluid cell
          if (bulkIndicator(bulk)) {
            Vector<T, 2> normal;
            T dist = -1;    // distance to boundary
            T qIpop = -1;   // normed distance to boundary
            const T norm = deltaR * util::norm<DESCRIPTOR::d>(descriptors::c<DESCRIPTOR>(iPop));
            bool hasBoundary = indicatorAnalyticalBoundary.distance(dist, bulkPhysR, oppoC, blockGeometry.getIcGlob());
            // Check if distance calculation was performed correctly
            if (hasBoundary) {
              qIpop = dist / norm;

              // if distance function returned a dist. -> fall-back
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
              bulkPhysR[1] + oppoC[1] * qIpop * deltaR
            };

            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_X>(oppo, boundary[0]);
            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_Y>(oppo, boundary[1]);

            // Set normal vector

            bool hasNormal = indicatorAnalyticalBoundary.normal(normal, bulkPhysR, oppoC);
            if (! hasNormal) {
              if (verbose) {
                std::cout << "Normal not found at lattice:(" << bulk << "), physical: (" << blockGeometry.getPhysR(bulk) << "), direction: " << iPop << ". Fall-back to normal [0 0]." << std::endl;
              }
              normal[0] = 0;
              normal[1] = 0;
            }
            if (! outward) {
              normal[0] = -1 * normal[0];
              normal[1] = -1 * normal[1];
            }
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_X>(oppo, normal[0]);
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_Y>(oppo, normal[1]);
          }
        }
        block.addPostProcessor(typeid(stage::PostCollide),
        node,
        meta::id<OPERATOR>{});
      }

    });
  };

  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary( SuperLattice<T, DESCRIPTOR>& sLattice,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                                  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& bulkIndicator,
                                  IndicatorCircle2D<T>& indicatorAnalyticalBoundary,
                                  bool outward)
  {
    OstreamManager clout(std::cout, "SolidNeumannBoundarySetter");
    auto& load = sLattice.getLoadBalancer();
    for (int iC=0; iC < load.size(); ++iC) {
      setBoolakeeNeumannBoundary<T,DESCRIPTOR, OPERATOR>( sLattice.getBlock(iC),
                                                ( bulkIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                                boundaryIndicator->getBlockIndicatorF(iC),
                                                bulkIndicator->getBlockIndicatorF(iC),
                                                indicatorAnalyticalBoundary,
                                                outward);
    }
    clout.setMultiOutput(false);
  }


// Anything
  template <typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary( BlockLattice<T,DESCRIPTOR>& block,
                                  BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                                  BlockIndicatorF<T,DESCRIPTOR::d>& bulkIndicator,
                                  IndicatorF<T,DESCRIPTOR::d>& indicatorAnalyticalBoundary,
                                  bool outward,
                                  bool verbose = true)
  {
    OstreamManager clout(std::cout, "BoolakeeNeumannBoundarySetter");
    clout.setMultiOutput(true);

    const T deltaR = blockGeometry.getDeltaR();
    // for each solid cell: all of its fluid neighbors need population updates
    block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> node) {
      // Check if cell is solid cell
      if (boundaryIndicator(node)) {
        for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
          Vector<T,DESCRIPTOR::d> bulk(node + descriptors::c<DESCRIPTOR>(iPop));
          const auto c = descriptors::c<DESCRIPTOR>(iPop);
          const auto oppo = descriptors::opposite<DESCRIPTOR>(iPop);
          Vector<T, 2> oppoC = descriptors::c<DESCRIPTOR>(oppo);

          olb::Vector<T, DESCRIPTOR::d> physCoords;
          blockGeometry.getPhysR(physCoords, bulk);
          Vector<T,DESCRIPTOR::d> bulkPhysR = {physCoords[0], physCoords[1]};
          // check if neighbor is fluid cell

          if (blockGeometry.isInside(bulk)) {
          if (bulkIndicator(bulk)) {
            Vector<T, 2> normal;
            T dist = -1;    // distance to boundary
            T qIpop = -1;   // normed distance to boundary
            const T norm = deltaR * util::norm<DESCRIPTOR::d>(descriptors::c<DESCRIPTOR>(iPop));
            bool hasBoundary = indicatorAnalyticalBoundary.distance(dist, bulkPhysR, oppoC, blockGeometry.getIcGlob());
            // Check if distance calculation was performed correctly
            if (hasBoundary) {
              qIpop = dist / norm;

              // if distance function returned a dist. -> fall-back
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
              bulkPhysR[1] + oppoC[1] * qIpop * deltaR
            };

            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_X>(oppo, boundary[0]);
            block.get(bulk).template setFieldComponent<descriptors::BOUNDARY_COORDS_Y>(oppo, boundary[1]);

            // Set normal vector
            indicatorAnalyticalBoundary.normal(normal, bulkPhysR, oppoC);
            if (! outward) {
              normal[0] = -normal[0];
              normal[1] = -normal[1];
            }
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_X>(oppo, normal[0]);
            block.get(bulk).template setFieldComponent<descriptors::NEUMANN_SOLID_NORMAL_Y>(oppo, normal[1]);
          }
        }
        }
        block.addPostProcessor(typeid(stage::PostCollide),
        node,
        meta::id<OPERATOR>{});
      }

    });
  };

template<typename T, typename DESCRIPTOR, typename OPERATOR>
void setBoolakeeNeumannBoundary( SuperLattice<T, DESCRIPTOR>& sLattice,
                                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                                 FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& bulkIndicator,
                                 IndicatorF<T,DESCRIPTOR::d>&                   indicatorAnalyticalBoundary,
                                 bool outward)
  {
    OstreamManager clout(std::cout, "SolidNeumannBoundarySetter");
    auto& load = sLattice.getLoadBalancer();
    for (int iC=0; iC < load.size(); ++iC) {
      setBoolakeeNeumannBoundary<T,DESCRIPTOR, OPERATOR>( sLattice.getBlock(iC),
                                                        ( bulkIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                                        boundaryIndicator->getBlockIndicatorF(iC),
                                                        bulkIndicator->getBlockIndicatorF(iC),
                                                        indicatorAnalyticalBoundary,
                                                        outward);
    }
    clout.setMultiOutput(false);
  }

  template<typename T, typename DESCRIPTOR, typename OPERATOR>
  void setBoolakeeNeumannBoundary(SuperLattice<T, DESCRIPTOR>& sLattice,
                                    SuperGeometry<T,DESCRIPTOR::d>& superGeometry,
                                    int materialOfSolidObstacle,
                                    IndicatorF<T,DESCRIPTOR::d>& indicatorAnalyticalBoundary,
                                    bool outward,
                                    std::vector<int> bulkMaterials = std::vector<int>(1,1))
  {
    //Getting the indicators by material numbers and calling the superLattice method via the indicators:
    setBoolakeeNeumannBoundary<T,DESCRIPTOR,OPERATOR>(sLattice,
                                                      FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>(superGeometry.getMaterialIndicator(materialOfSolidObstacle)),
                                                      FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>(superGeometry.getMaterialIndicator(std::move(bulkMaterials))),
                                                      indicatorAnalyticalBoundary,
                                                      outward);
  }
};

#endif
