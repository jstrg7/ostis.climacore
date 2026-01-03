file(GLOB TEST_UTILS_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_LIST_DIR}/utils/*.cpp"
    "${CMAKE_CURRENT_LIST_DIR}/utils/*.hpp")

add_library(example-module-test-utils STATIC ${TEST_UTILS_SOURCES})
target_link_libraries(example-module-test-utils
    LINK_PUBLIC example-module
    LINK_PUBLIC GTest::gtest_main)

target_include_directories(example-module-test-utils
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}
)

if(${SC_CLANG_FORMAT_CODE})
    target_clangformat_setup(example-module-test-utils)
endif()

make_tests_from_folder(${CMAKE_CURRENT_LIST_DIR}/units
    NAME example-module-tests
    DEPENDS sc-machine::sc-builder-lib example-module-test-utils
)

if(${SC_CLANG_FORMAT_CODE})
    target_clangformat_setup(example-module-tests)
endif()
