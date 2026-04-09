#
# $Id:  $
#
# Description: Makefile for luleshMPI program
#
# $Log:  $
#

TARGET = luleshMPI-pscr
VERSION = 1.0
LABEL = V$(subst .,_,$(VERSION))

LDPATH = LD_LIBRARY_PATH=$(HOME)/local/lib

DEFS = -DVERSION=$(VERSION)
#DEFS += -DVIZ_MESH
#DEFS += $(if $(findstring Windows_NT,$(OS)),-DTIMEOFDAY,-DGETTIME)

#MODULES = 

OBJECTS = $(addsuffix .o,$(TARGET) $(MODULES))
HEADERS = $(addsuffix .h,$(MODULES)) # ticks.h
SOURCES = $(addsuffix .c,$(TARGET) $(MODULES)) $(HEADERS)

ifdef USE_ICC
CC = mpiicpc
CXX = mpiicpc
else
CC = mpicxx
CXX = mpicxx
endif

OPT = -O3
CXXFLAGS = $(OPT) $(DEFS) -I. -I$(HOME)/local/include
CXXFLAGS += -I/usr/local/tools/scr-1.1/include
COFLAGS = -M

#VAR = $(if $(findstring CYGWIN,$(shell uname -s)),CYG_TRUE,CYG_FALSE)
#LDFLAGS = $(if $(findstring Linux,$(shell uname -s)),-static)
#LDLIBS = $(if $(findstring Linux,$(shell uname -s)),-lrt)
LDFLAGS += -L$(HOME)/local/lib
LDLIBS += -ljemalloc
#LDLIBS += -lsilo
LDFLAGS += -L/usr/local/tools/scr-1.1/lib -Wl,-rpath,/usr/local/tools/scr-1.1/lib
LDLIBS += -lscr

.PHONY: all
all: $(TARGET)

.PHONY: check
check: $(TARGET)
	$(LDPATH) mpiexec -np 1 ./$(TARGET)

.PHONY: srun
nprocs=8
srun: $(TARGET)
	$(LDPATH) srun -l -N$(nprocs) -n$(nprocs) ./$(TARGET)

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
