#!/usr/bin/env nix
#!nix --extra-experimental-features nix-command --extra-experimental-features flakes develop ../.#env-gcc-openmpi-cuda --command bash

rm -f config.mk

export CUDA_ARCH=86

make
make -j4 \
     examples/laminar/powerLaw2d/ \
     examples/laminar/poiseuille2d/ \
     examples/laminar/poiseuille3d/ \
     examples/laminar/bstep2d/ \
     examples/laminar/bstep3d/ \
     examples/laminar/cylinder2d/ \
     examples/laminar/cylinder3d/ \
     examples/laminar/cavity2d/ \
     examples/laminar/cavity3d/ \
     examples/laminar/cavity3dBenchmark/ \
     examples/pdeSolverEoc/poiseuille2dEoc/ \
     examples/pdeSolverEoc/poiseuille3dEoc/ \
     examples/pdeSolverEoc/cylinder2dEoc/ \
     examples/pdeSolverEoc/cylinder3dEoc/ \
     examples/turbulence/nozzle3d/ \
     examples/turbulence/venturi3d/ \
     examples/turbulence/tgv3d/ \
     examples/turbulence/aorta3d/ \
     examples/freeSurface/breakingDam2d/ \
     examples/freeSurface/breakingDam3d/ \
     examples/freeSurface/deepFallingDrop2d/ \
     examples/freeSurface/fallingDrop2d/ \
     examples/freeSurface/fallingDrop3d/ \
     examples/freeSurface/rayleighInstability3d/ \
     examples/advectionDiffusionReaction/advectionDiffusion1d/ \
     examples/advectionDiffusionReaction/advectionDiffusion2d/ \
     examples/advectionDiffusionReaction/advectionDiffusion3d/ \
     examples/multiComponent/airBubbleCoalescence3d/ \
     examples/multiComponent/binaryShearFlow2d/ \
     examples/multiComponent/contactAngle2d/ \
     examples/multiComponent/contactAngle3d/ \
     examples/multiComponent/fourRollMill2d/ \
     examples/multiComponent/microFluidics2d/ \
     examples/multiComponent/phaseSeparation2d/ \
     examples/multiComponent/phaseSeparation3d/ \
     examples/multiComponent/rayleighTaylor2d/ \
     examples/multiComponent/rayleighTaylor3d/ \
     examples/multiComponent/waterAirFlatInterface2d/ \
     examples/multiComponent/youngLaplace2d/ \
     examples/multiComponent/youngLaplace3d/ \
     examples/thermal/rayleighBenard2d/ \
     examples/thermal/rayleighBenard3d/ \
     examples/thermal/squareCavity2d/ \
     examples/thermal/squareCavity3d/ \
     examples/particles/bifurcation3d/eulerEuler/ \
     examples/fsi/rigidValve2d \
     examples/gridRefinement/cellCentered/cylinder2d \
     examples/gridRefinement/cellCentered/sphere3d \
     examples/gridRefinement/vertexCentered/cylinder2d \
     examples/gridRefinement/vertexCentered/sphere3d
