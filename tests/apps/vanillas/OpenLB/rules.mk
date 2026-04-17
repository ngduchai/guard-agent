###########################################################################
## conditional settings

OLB_RELEASE := 1.8r1

GIT_VERSION := $(shell if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git describe --always --tags --dirty; fi)
ifneq ($(strip $(GIT_VERSION)),)
	CXXFLAGS += -DOLB_VERSION=\"$(GIT_VERSION)\"
else
	CXXFLAGS += -DOLB_VERSION=\"$(OLB_RELEASE)\"
endif

# Select std::thread foundation for use in thread pool / async job system
ifdef THREAD_POOL
ifeq ($(THREAD_POOL), PTHREAD)
	CXXFLAGS += -pthread
	LDFLAGS += -lpthread
endif
# Default to pthread
else
	CXXFLAGS += -pthread
	LDFLAGS += -lpthread
endif

ifeq ($(PARALLEL_MODE), MPI)
	CXXFLAGS += -DPARALLEL_MODE_MPI $(MPIFLAGS)
	PARALLEL_FLAGS := -DPARALLEL_MODE_MPI $(MPIFLAGS)
	LDFLAGS  := $(MPIFLAGS) $(LDFLAGS)
endif

ifeq ($(PARALLEL_MODE), OMP)
	CXXFLAGS += -DPARALLEL_MODE_OMP $(OMPFLAGS)
	PARALLEL_FLAGS := -DPARALLEL_MODE_OMP $(OMPFLAGS)
	LDFLAGS  := $(OMPFLAGS) $(LDFLAGS)
endif

ifeq ($(PARALLEL_MODE), HYBRID)
	CXXFLAGS += -DPARALLEL_MODE_OMP -DPARALLEL_MODE_MPI $(OMPFLAGS) $(MPIFLAGS)
	PARALLEL_FLAGS := -DPARALLEL_MODE_OMP -DPARALLEL_MODE_MPI $(OMPFLAGS) $(MPIFLAGS)
	LDFLAGS  := $(MPIFLAGS) $(OMPFLAGS) $(LDFLAGS)
endif

LDFLAGS += $(EXTRA_LDFLAGS)

FILTERED_FEATURES := $(FEATURES)

ifneq ($(filter EMSCRIPTEN,$(FEATURES)),) # Check if EMSCRIPTEN is in FEATURES
	AR := emar
else
	AR := ar
endif

ifneq ($(filter DISABLE_CSE,$(FILTERED_FEATURES)),)
	CXXFLAGS += -DDISABLE_CSE
	FILTERED_FEATURES := $(filter-out DISABLE_CSE,$(FILTERED_FEATURES))
endif

ifneq ($(filter CPU_SIMD,$(PLATFORMS)),)
	LDFLAGS += -lrt
endif

LDFLAGS += -lz -ltinyxml2
LDFLAGS += $(if $(filter $(FEATURES), OPENBLAS),-lopenblas)
LDFLAGS += $(if $(filter $(FEATURES), VDB),-lopenvdb -ltbb)

ifneq ($(filter PROJ,$(FEATURES)),)
	LDFLAGS += -lproj
endif


ifneq ($(filter VTK,$(FEATURES)),)
	ifdef VTK_VERSION
		VTK_VERSION := -$(VTK_VERSION)
	endif
	LDFLAGS += $(if $(filter $(FEATURES), VTK),-lvtkIOLegacy$(VTK_VERSION) -lvtkCommonCore$(VTK_VERSION) -lvtkCommonExecutionModel$(VTK_VERSION) -lvtkCommonDataModel$(VTK_VERSION) -lvtkIOCore$(VTK_VERSION) -lvtkIOXML$(VTK_VERSION) -lvtksys$(VTK_VERSION) -lvtkFiltersCore$(VTK_VERSION) -lvtkImagingCore$(VTK_VERSION) -lvtkIOParallelXML$(VTK_VERSION))
endif

ifneq ($(filter PRECICE,$(FEATURES)),)
	LDFLAGS += -lprecice
endif

ifneq ($(filter GPU_CUDA,$(PLATFORMS)),)
## | CUDA Architecture | Version    |
## |-------------------+------------|
## | Fermi             | 20         |
## | Kepler            | 30, 35, 37 |
## | Maxwell           | 50, 52, 53 |
## | Pascal            | 60, 61, 62 |
## | Volta             | 70, 72     |
## | Turing            | 75         |
## | Ampere            | 80, 86, 87 |
## | Ada Lovelace      | 89         |
## | Hopper            | 90         |
## | Blackwell         | 100        |
	CUDA_ARCH ?= 75
	# Remove spaces from user-defined CUDA_ARCH (otherwise the `--generate-code` flag is messed up)
	CUDA_ARCH := $(strip $(CUDA_ARCH))

	CUDA_LDFLAGS += -lcuda -lcudadevrt -lcudart

	ifndef CUDA_CXXFLAGS
		CUDA_CXXFLAGS := -O3 -std=c++20
	endif

	CUDA_CXXFLAGS += --generate-code=arch=compute_$(CUDA_ARCH),code=[compute_$(CUDA_ARCH),sm_$(CUDA_ARCH)]
	CUDA_CXXFLAGS += --extended-lambda --expt-relaxed-constexpr
	# Enable relocatable device code (only needed for mixed mode but speeds up non-mixed compilation significantly)
	CUDA_CXXFLAGS += -rdc=true
	# Hide some distracting warnings on calling device host functions from host
	CUDA_CXXFLAGS += -Xcudafe "--diag_suppress=implicit_return_from_non_void_function --display_error_number --diag_suppress=20014 --diag_suppress=20011"

	ifndef CUDA_CXX
		CXXFLAGS += --forward-unknown-to-host-compiler -x cu
		CXXFLAGS += $(CUDA_CXXFLAGS)
		LDFLAGS += $(CUDA_LDFLAGS)
	endif
endif

#  HIP compiling
ifneq ($(filter GPU_HIP,$(PLATFORMS)),)

	HIP_PLATFORM := $(strip $(HIP_PLATFORM))
	
	ifndef HIP_CXXFLAGS
		HIP_CXXFLAGS := -O3 -std=c++20
	endif

	ifeq ($(HIP_PLATFORM),nvidia)
		CUDA_ARCH ?= 75
		CUDA_ARCH := $(strip $(CUDA_ARCH))

		HIP_CXXFLAGS += --generate-code=arch=compute_$(CUDA_ARCH),code=[compute_$(CUDA_ARCH),sm_$(CUDA_ARCH)]
		HIP_CXXFLAGS += --extended-lambda --expt-relaxed-constexpr
		HIP_CXXFLAGS += -rdc=true
		HIP_CXXFLAGS += -Xcudafe "--diag_suppress=implicit_return_from_non_void_function --display_error_number --diag_suppress=20014 --diag_suppress=20011"
		HIP_CXXFLAGS += -I$(ROCM_PATH)/include -I$(ROCM_PATH)/hip/include

		HIP_LDFLAGS  += -lcuda -lcudadevrt -lcudart --generate-code=arch=compute_$(CUDA_ARCH),code=[compute_$(CUDA_ARCH),sm_$(CUDA_ARCH)]

		ifndef HIP_CXX
			HIP_CXXFLAGS += --forward-unknown-to-host-compiler -x cu 
		endif

	else # amd
		HIP_ARCH	 ?= native
		HIP_ARCH     := $(strip $(HIP_ARCH))	
		HIP_CXXFLAGS += --offload-arch=$(HIP_ARCH)
		HIP_CXXFLAGS += -Wno-vla-cxx-extension -Wno-deprecated-non-prototype
	endif


	ifndef HIP_CXX
		CXXFLAGS += $(HIP_CXXFLAGS)
		LDFLAGS  += $(HIP_LDFLAGS)
	endif
endif

PLATFORM_FLAGS := $(foreach platform,$(PLATFORMS),-DPLATFORM_$(platform))
FEATURE_FLAGS := $(foreach feature,$(FILTERED_FEATURES),-DFEATURE_$(feature))

CXXFLAGS += $(PLATFORM_FLAGS)
CXXFLAGS += $(FEATURE_FLAGS)

ifdef FLOATING_POINT_TYPE
	CXXFLAGS += -DDEFAULT_FLOATING_POINT_TYPE=$(FLOATING_POINT_TYPE)
endif
