# Makefile for Quicksilver — VeloC-resilient build
#
# This Makefile is identical to the original except for the addition of
# VeloC compile/link flags.
#
# VeloC is installed at VELOC_DIR (default: /home/ndhai/usr).
# Override on the command line:  make VELOC_DIR=/path/to/veloc

SHELL = /bin/bash

# ---------------------------------------------------------------------------
# VeloC installation directory
# ---------------------------------------------------------------------------
VELOC_DIR ?= /home/ndhai/usr

VELOC_CPPFLAGS = -DHAVE_VELOC -I$(VELOC_DIR)/include
# Note: -l flags MUST come after object files in the link command.
# We put them in VELOC_LDLIBS (appended after objects) rather than LDFLAGS.
VELOC_LDFLAGS  = -L$(VELOC_DIR)/lib -Wl,-rpath,$(VELOC_DIR)/lib
VELOC_LDLIBS   = -lveloc-client

###############################################################################
### GCC -- with MPI and OpenMP
###############################################################################
OPENMP_FLAGS = -DHAVE_OPENMP -fopenmp
OPENMP_LDFLAGS = -fopenmp
MPI_FLAGS = -DHAVE_MPI
OPTFLAGS = -g -O2

CXX=mpicxx
# -include portability.hh ensures uint64_t is available in all translation units
CXXFLAGS = -std=c++11 $(OPTFLAGS) -include portability.hh
CPPFLAGS = $(MPI_FLAGS) $(OPENMP_FLAGS) $(VELOC_CPPFLAGS)
LDFLAGS = $(OPENMP_LDFLAGS) $(VELOC_LDFLAGS)
LDLIBS  = $(VELOC_LDLIBS)

################################################################################
### Below here, it is pitch black.                                           ###
### You are likely to be eaten by a grue.                                    ###
################################################################################

GITVERS := "$(shell git log -n 1 |  grep Date   | awk -F " " '{print $$6 "-" $$3 "-" $$4 "-" $$5}')"
GITHASH := "$(shell git log -n 1 |  grep commit | awk -F " " '{print $$2}')"

Quicksilver_EXE=qs

# clear all suffixes
.SUFFIXES:
# list only those that we use 
.SUFFIXES: .cc .o

.PHONY: DEFAULT clean distclean depend

# For development purposes, what is working now.
SOURCES= \
    CollisionEvent.cc \
    CoralBenchmark.cc \
    CycleTracking.cc \
    DecompositionObject.cc \
    DirectionCosine.cc \
	EnergySpectrum.cc \
    GlobalFccGrid.cc \
    GridAssignmentObject.cc \
    InputBlock.cc \
    MCT.cc \
    MC_Adjacent_Facet.cc \
    MC_Base_Particle.cc \
    MC_Domain.cc \
    MC_Facet_Crossing_Event.cc \
    MC_Fast_Timer.cc \
    MC_Load_Particle.cc \
    MC_Location.cc \
    MC_Particle_Buffer.cc \
    MC_RNG_State.cc \
    MC_Segment_Outcome.cc \
    MC_SourceNow.cc \
    MacroscopicCrossSection.cc \
    MeshPartition.cc \
    MonteCarlo.cc \
    MpiCommObject.cc \
    NuclearData.cc \
    Parameters.cc \
    ParticleVault.cc \
    ParticleVaultContainer.cc \
    PopulationControl.cc \
    SendQueue.cc \
    SharedMemoryCommObject.cc \
    Tallies.cc \
    cmdLineParser.cc \
    cudaFunctions.cc \
    initMC.cc \
    main.cc \
    parseUtils.cc \
    utils.cc \
    utilsMpi.cc 

CC_OBJECTS=$(SOURCES:.cc=.o)

DEFAULT: ${Quicksilver_EXE}

git_hash.hh:
	echo "#define GIT_HASH \"$(GITHASH)\" "> git_hash.hh

git_vers.hh:
	echo "#define GIT_VERS \"$(GITVERS)\" "> git_vers.hh

%.o: %.cc
	${CXX} ${CPPFLAGS} ${CXXFLAGS} -c $< -o $@

# Note: LDLIBS comes AFTER objects so the linker resolves symbols correctly
${Quicksilver_EXE}: git_hash.hh git_vers.hh ${CC_OBJECTS}  
	${CXX} ${CXXFLAGS} ${LDFLAGS} -o ${Quicksilver_EXE} ${CC_OBJECTS} ${LDLIBS}

clean:
	rm -f *.o git_hash.hh git_vers.hh .depend load.map *.core *.optrpt

distclean: clean
	rm -f ${Quicksilver_EXE}   .depend.bak
	rm -rf html latex vtune*

.depend: $(SOURCES)
	@touch .depend
	@$(MAKE) --no-print-directory depend

depend:
	@echo "Rebuilding dependencies..."
	@makedepend -f .depend -Y. --$(CXXFLAGS) $(CPPFLAGS)-- $(SOURCES) 2> /dev/null

-include .depend
