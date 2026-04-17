GTEST_DIR := .

GTEST_OBJDIR := ./build

GTEST_CPPFLAGS := $(CPPFLAGS) -isystem $(GTEST_DIR)/include -DGTEST_HAS_PTHREAD=0

# Flags passed to the C++ compiler.
GTEST_CXXFLAGS := $(CXXFLAGS) -g

# All Google Test headers.  Usually you shouldn't change this
# definition.
GTEST_HEADERS = $(GTEST_DIR)/include/gtest/*.h \
                $(GTEST_DIR)/include/gtest/internal/*.h

GTEST_SRCS_ = $(GTEST_DIR)/src/*.cc $(GTEST_DIR)/src/*.h $(GTEST_HEADERS)

all: $(GTEST_OBJDIR) $(GTEST_OBJDIR)/libgtest_main.a $(GTEST_OBJDIR)/libgtest.a

$(GTEST_OBJDIR):
	mkdir -p $(GTEST_OBJDIR)

$(GTEST_OBJDIR)/gtest-all.o : $(GTEST_SRCS_)
	$(CXX) $(GTEST_CPPFLAGS) -I$(GTEST_DIR) $(GTEST_CXXFLAGS) -c \
            $(GTEST_DIR)/src/gtest-all.cc -o $(GTEST_OBJDIR)/gtest-all.o

$(GTEST_OBJDIR)/gtest_main.o : $(GTEST_SRCS_)
	$(CXX) $(GTEST_CPPFLAGS) -I$(GTEST_DIR) $(GTEST_CXXFLAGS) -c \
            $(GTEST_DIR)/src/gtest_main.cc -o $(GTEST_OBJDIR)/gtest_main.o

$(GTEST_OBJDIR)/gtest.o : $(GTEST_SRCS_)
	$(CXX) $(GTEST_CPPFLAGS) -I$(GTEST_DIR) $(GTEST_CXXFLAGS) -c \
            $(GTEST_DIR)/src/gtest.cc -o $(GTEST_OBJDIR)/gtest.o

$(GTEST_OBJDIR)/libgtest_main.a :  $(GTEST_OBJDIR)/gtest-all.o $(GTEST_OBJDIR)/gtest_main.o
	$(AR) $(ARFLAGS) $@ $^

$(GTEST_OBJDIR)/libgtest.a : $(GTEST_OBJDIR)/gtest-all.o $(GTEST_OBJDIR)/gtest.o
	$(AR) $(ARFLAGS) $@ $^

clean:
	@rm $(GTEST_OBJDIR)/libgtest_main.a &> /dev/null || true
	@rm $(GTEST_OBJDIR)/libgtest.a &> /dev/null || true
	@rm $(GTEST_OBJDIR)/*.o &> /dev/null || true
