OLB_ROOT := ../..
include ../default.mk

BENCH_OBJ_DIR := build/obj
BENCH_DEP_DIR := build/dep

BENCH_CPP_FILES := $(shell find . -name '*.cpp')
BENCH_TARGETS := $(patsubst %.cpp, %, $(BENCH_CPP_FILES))

BENCHS := $(notdir $(basename $(BENCH_TARGETS)))
RUNBENCHS := $(addprefix run-,$(notdir $(basename $(BENCH_TARGETS))))

all: $(RUNBENCHS)

build: $(BENCHS)

CLEAN_TARGETS :=

CXXFLAGS += -I.

define runBenchmark
$(1) : $(2)
	$(2)

.PHONY: $(1)
endef

define compileBenchmark
$(BENCH_OBJ_DIR)/$(1).o : $(1).cpp $(SHARED_BENCH_HEADER)
	@echo $$@
	mkdir -p $$(dir $$@)
	$(CXX) $(CXXFLAGS) -DPATH='"$$(realpath $$(dir $$<))/"' -c $$< -o $$@

$(BENCH_DEP_DIR)/$(1).d : $(1).cpp
	@mkdir -p $$(dir $$@)
	@sh -ec '$(CXX) -M $(CXXFLAGS) $$< \
	    | sed -e "s!$(notdir $(1)).o!$(BENCH_OBJ_DIR)/$(1).o!1" > $$@;'

include $(wildcard $(BENCH_DEP_DIR)/$(1).d)
endef

define targetBenchmark
$(1) : $(2)
endef

define linkBenchmark
$(1) : $(BENCH_OBJ_DIR)/$(1).o $(BENCH_DEP_DIR)/$(1).d
	$(CXX) $$< $(LDFLAGS) -lgtest_main -lgtest -o $(1)

clean-$(1):
	@rm -f $(1) &> /dev/null || true
	@rm -f $(BENCH_OBJ_DIR)/$(1).o &> /dev/null || true
	@rm -f $(BENCH_DEP_DIR)/$(1).d &> /dev/null || true

CLEAN_TARGETS += clean-$(1)
endef

$(foreach test,$(BENCH_TARGETS), \
    $(eval $(call linkBenchmark,$(test))))

$(foreach test,$(BENCH_TARGETS), \
    $(eval $(call compileBenchmark,$(test))))

$(foreach test,$(BENCH_TARGETS), \
    $(eval $(call targetBenchmark,$(notdir $(basename $(test))),$(test))))

$(foreach test,$(BENCH_TARGETS), \
    $(eval $(call runBenchmark,run-$(notdir $(basename $(test))),$(test))))

clean: $(CLEAN_TARGETS)
	@rm -f $(BENCH_TARGETS) &> /dev/null || true

.PHONY: clean
