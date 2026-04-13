FROM ubuntu:noble

LABEL Description="Palabos Docker image, based on ubuntu:noble " maintainer="orestis.malaspinas@hesge.ch" Version="0.3"

RUN sed -i'' 's/archive.ubuntu.com/ch.archive.ubuntu.com/' /etc/apt/sources.list 
RUN apt update && apt dist-upgrade -y
ENV TZ=Europe/Zurich
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt install -y g++ clang clang-format-14 ccache cmake python3 make libopenmpi-dev libhdf5-dev libhdf5-mpi-dev doxygen imagemagick wget gpg && update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN ln -s /usr/bin/clang-format-14 /usr/bin/clang-format
RUN apt install -y libtbb-dev

# # download the key to system keyring
# RUN wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB \
# | gpg --dearmor | tee /usr/share/keyrings/oneapi-archive-keyring.gpg > /dev/null
#
# # add signed entry to apt sources and configure the APT client to use Intel repository:
# RUN echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main" | tee /etc/apt/sources.list.d/oneAPI.list
# RUN apt update && apt dist-upgrade -y
# RUN apt install -y intel-tbb
