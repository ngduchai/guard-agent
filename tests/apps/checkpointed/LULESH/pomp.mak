#
# $Id:  $
#
# Description: Makefile for luleshOMP program
#
# $Log:  $
#

TARGET = luleshOMP-perm
VERSION = 1.0
LABEL = V$(subst .,_,$(VERSION))

LDPATH = LD_LIBRARY_PATH=$(HOME)/local/lib

DEFS = -DVERSION=$(VERSION)
#DEFS += $(if $(findstring Windows_NT,$(OS)),-DTIMEOFDAY,-DGETTIME)

#MODULES = 

OBJECTS = $(addsuffix .o,$(TARGET) $(MODULES))
HEADERS = $(addsuffix .h,$(MODULES)) # ticks.h
SOURCES = $(addsuffix .c,$(TARGET) $(MODULES)) $(HEADERS)

ifdef USE_ICC
CC = icpc
CXX = icpc
OMP = -openmp -parallel
else
CC = g++
CXX = g++
OMP = -fopenmp
endif

OPT = -O3
CFLAGS = $(OPT) $(OMP) $(DEFS) -I. -I$(HOME)/local/include
CXXFLAGS = $(OPT) $(OMP) $(DEFS) -I. -I$(HOME)/local/include
COFLAGS = -M

#VAR = $(if $(findstring CYGWIN,$(shell uname -s)),CYG_TRUE,CYG_FALSE)
#LDFLAGS = $(if $(findstring Linux,$(shell uname -s)),-static)
#LDLIBS = $(if $(findstring Linux,$(shell uname -s)),-lrt)
LDFLAGS += $(OMP) -L$(HOME)/local/lib
LDLIBS += -ljemalloc

.PHONY: all
all: $(TARGET)

.PHONY: check
check: $(TARGET)
	$(LDPATH) ./$(TARGET) $(ARG1) $(ARG2)

.PHONY: srun
nprocs=1
srun: $(TARGET)
	$(LDPATH) srun -N$(nprocs) -n$(nprocs) ./$(TARGET) $(ARG1) $(ARG2)

.PHONY: clean distclean
clean distclean:
	$(RM) $(OBJECTS) $(TARGET)$(EXE)

.PHONY: co
co:
	$(CO) $(COFLAGS) $(SOURCES)

.PHONY: snapshot
snapshot:
	rcs -n$(LABEL): -sStab $(SOURCES) $(MAKEFILE_LIST)

.PHONY: vars
vars:
	@echo TARGET: $(TARGET)
	@echo VERSION: $(VERSION)
	@echo LABEL: $(LABEL)
	@echo OBJECTS: $(OBJECTS)
	@echo HEADERS: $(HEADERS)
	@echo SOURCES: $(SOURCES)
	@echo DEFS: $(DEFS)
	@echo LDPATH: $(LDPATH)

$(TARGET): $(OBJECTS)

$(OBJECTS): $(MAKEFILE_LIST) # rebuild if MAKEFILE changes
# establish module specific dependencies
$(TARGET).o: $(HEADERS)
#module.o: module.h
