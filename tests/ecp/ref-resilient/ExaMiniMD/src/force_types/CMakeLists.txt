SET(HEADERS
  force_lj_cell.h
  force_lj_idial_neigh.h
  force_lj_idial_neigh_impl.h
  force_lj_neigh.h
  force_lj_neigh_impl.h)

SET(SOURCES
  force_lj_cell.cpp
  force_lj_idial_neigh.cpp
  force_lj_neigh.cpp)

target_sources(ExaMiniMD PRIVATE ${SOURCES} ${HEADERS})
