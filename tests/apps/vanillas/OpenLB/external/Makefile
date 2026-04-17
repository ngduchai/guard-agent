all: lib zlib tinyxml2 gtest
.PHONY: zlib tinyxml2 gtest

lib:
	mkdir -p lib

zlib:
	make -C zlib
	cp zlib/build/libz.a lib/

clean_zlib:
	make -C zlib clean

tinyxml2:
	make -C tinyxml2
	cp tinyxml2/build/libtinyxml2.a lib/

clean_tinyxml2:
	make -C tinyxml2 clean

gtest:
	make -C gtest
	cp gtest/build/libgtest_main.a lib/
	cp gtest/build/libgtest.a lib/

clean_gtest:
	make -C gtest clean

clean: clean_zlib clean_tinyxml2 clean_gtest
	rm -f lib/libz.a lib/libtinyxml2.a lib/libgtest_main.a lib/libgtest.a
