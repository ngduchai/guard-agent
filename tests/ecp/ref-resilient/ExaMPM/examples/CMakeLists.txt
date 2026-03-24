add_executable( DamBreak dam_break.cpp )
target_link_libraries( DamBreak PRIVATE exampm)
target_include_directories( DamBreak PRIVATE ${VELOC_DIR}/include )
target_link_directories( DamBreak PRIVATE ${VELOC_DIR}/lib )
target_link_libraries( DamBreak PRIVATE veloc-client )
set_target_properties( DamBreak PROPERTIES
    INSTALL_RPATH "${VELOC_DIR}/lib"
    BUILD_WITH_INSTALL_RPATH TRUE )

add_executable( FreeFall free_fall.cpp )
target_link_libraries( FreeFall PRIVATE exampm)
target_include_directories( FreeFall PRIVATE ${VELOC_DIR}/include )
target_link_directories( FreeFall PRIVATE ${VELOC_DIR}/lib )
target_link_libraries( FreeFall PRIVATE veloc-client )
set_target_properties( FreeFall PROPERTIES
    INSTALL_RPATH "${VELOC_DIR}/lib"
    BUILD_WITH_INSTALL_RPATH TRUE )

install(TARGETS DamBreak FreeFall DESTINATION ${CMAKE_INSTALL_BINDIR})
