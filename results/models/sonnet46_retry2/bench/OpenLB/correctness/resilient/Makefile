EXAMPLE = bstep2d
OLB_ROOT := ../../..

# VeloC checkpoint/restart library flags
# These are picked up by rules.mk via EXTRA_LDFLAGS and EXTRA_CXXFLAGS
EXTRA_LDFLAGS  := -L/home/ndhai/usr/lib -lveloc-client -Wl,-rpath,/home/ndhai/usr/lib
EXTRA_CXXFLAGS := -I/home/ndhai/usr/include

include $(OLB_ROOT)/default.mk
