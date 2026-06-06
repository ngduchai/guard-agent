EXAMPLE = bstep2d
OLB_ROOT := ../../..
include $(OLB_ROOT)/default.mk

# VeloC checkpoint/restart support: link against libveloc-client and add
# the VeloC header search path. These flags MUST be appended AFTER the
# include of default.mk because config.mk uses `:=` assignment which
# would otherwise wipe out any prior CXXFLAGS/LDFLAGS settings. By using
# `+=` after the include they survive into the recipes defined inside
# default.single.mk (which uses $(CXXFLAGS) for compile and $(LDFLAGS)
# for link).
VELOC_PREFIX ?= /home/ndhai/usr
CXXFLAGS += -I$(VELOC_PREFIX)/include
LDFLAGS  += -L$(VELOC_PREFIX)/lib -Wl,-rpath,$(VELOC_PREFIX)/lib -lveloc-client
