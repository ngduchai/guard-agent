EXAMPLE = bstep2d
OLB_ROOT := ../../..
include $(OLB_ROOT)/default.mk

# VeloC resilience library: headers in /home/ndhai/usr/include and
# the client shared object in /home/ndhai/usr/lib (libveloc-client.so).
# We append to CXXFLAGS and LDFLAGS AFTER default.mk so that config.mk's
# overriding assignments (CXXFLAGS := ..., LDFLAGS := ...) do not strip
# these flags. Make evaluates recipe variables lazily, so additions made
# after the include still take effect at compile/link time.
VELOC_PREFIX := /home/ndhai/usr
CXXFLAGS    += -I$(VELOC_PREFIX)/include
LDFLAGS     += -L$(VELOC_PREFIX)/lib -Wl,-rpath,$(VELOC_PREFIX)/lib -lveloc-client
