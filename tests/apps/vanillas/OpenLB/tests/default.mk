# Include config.mk environment (optional)
-include $(OLB_ROOT)/config.mk

include $(OLB_ROOT)/rules.mk

INCLUDE_DIRS := $(OLB_ROOT)/src

ifneq ($(USE_EMBEDDED_DEPENDENCIES), OFF)
INCLUDE_DIRS += \
	$(OLB_ROOT)/external/zlib \
	$(OLB_ROOT)/external/tinyxml2 \
	$(OLB_ROOT)/external/gtest/include

LDFLAGS := -L$(OLB_ROOT)/external/lib $(LDFLAGS)
endif

CXXFLAGS += -I$(subst $(EMPTY) $(EMPTY), -I,$(INCLUDE_DIRS))
CXXFLAGS += -DGTEST_HAS_PTHREAD=0

LDFLAGS += -L$(OLB_ROOT)/build/lib -lolbcore
