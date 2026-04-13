CXX = mpicxx
# use -xmic-avx512 instead of -xHost for Intel Xeon Phi platforms
#OPTFLAGS = -O0 -xHost -fopenmp -DPRINT_DIST_STATS -DUSE_MPI_RMA # -DDEBUG_PRINTF #-DPRINT_EXTRA_NEDGES #-DUSE_MPI_RMA -DUSE_MPI_ACCUMULATE #-DUSE_32_BIT_GRAPH #-DDEBUG_PRINTF #-DUSE_MPI_RMA #-DPRINT_LCG_DOUBLE_LOHI_RANDOM_NUMBERS#-DUSE_MPI_RMA #-DPRINT_LCG_DOUBLE_RANDOM_NUMBERS #-DPRINT_RANDOM_XY_COORD
#OPTFLAGS = -O0 -fopenmp -DPRINT_DIST_STATS -DUSE_MPI_RMA -L/g/g90/guo7/mylibs/FTI/lib64/ -lfti # -DDEBUG_PRINTF #-DPRINT_EXTRA_NEDGES #-DUSE_MPI_RMA -DUSE_MPI_ACCUMULATE #-DUSE_32_BIT_GRAPH #-DDEBUG_PRINTF #-DUSE_MPI_RMA #-DPRINT_LCG_DOUBLE_LOHI_RANDOM_NUMBERS#-DUSE_MPI_RMA #-DPRINT_LCG_DOUBLE_RANDOM_NUMBERS #-DPRINT_RANDOM_XY_COORD
OPTFLAGS = -O3 -L$(HOME)/.local/lib -lfti -DTIMER -DPRINT_DIST_STATS
#-DUSE_MPI_SENDRECV
#-DUSE_MPI_COLLECTIVES
# use export ASAN_OPTIONS=verbosity=1 to check ASAN output
#SNTFLAGS = -std=c++11 -fopenmp -fsanitize=address -O1 -fno-omit-frame-pointer
SNTFLAGS = -std=c++11 -O3
CXXFLAGS = -std=c++11 -I$(HOME)/.local/include $(OPTFLAGS)

OBJ = main.o
CPK_OBJ = libcheckpoint/checkpoint.o
TARGET = miniVite

all: $(TARGET)

libcheckpoint/checkpoint.o: libcheckpoint/checkpoint.c
	$(CC) -Ilibcheckpoint -c -o $@ $<

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $^

$(TARGET):  $(OBJ) $(CPK_OBJ)
	$(CXX) $^ $(OPTFLAGS) -o $@

.PHONY: clean

clean:
	rm -rf *~ $(OBJ) $(TARGET) check_* tmp_* *core
