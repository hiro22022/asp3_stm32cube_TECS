cmake_minimum_required(VERSION 3.22)

#
# This file is generated only once,
# and is not re-generated if converter is called multiple times.
#
# User is free to modify the file as much as necessary
#

# N6 FSBL は Secure 実行（-mcmse）必須。ツールチェーン未指定の cmake だと
# ホスト gcc になり SAU 等の TrustZone 周辺が未定義になる。
if(NOT CMAKE_TOOLCHAIN_FILE)
    set(CMAKE_TOOLCHAIN_FILE
        "${CMAKE_CURRENT_LIST_DIR}/../gcc-arm-none-eabi.cmake"
        CACHE FILEPATH "ARM GCC toolchain" FORCE)
endif()

# Setup compiler settings
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# Define the build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug")
endif()

message("Build type: " ${CMAKE_BUILD_TYPE})

# Enable compile command to ease indexing with e.g. clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

# Compiler options
set(STM32_MCU_FLAGS  "-mcpu=cortex-m55 -mfpu=fpv5-d16 -mfloat-abi=hard -mcmse " )

#Linker options
set(STM32_LINKER_SCRIPT STM32N657XX_AXISRAM2_fsbl.ld)
set(STM32_LINKER_OPTION  )

# Set the project name
set(CMAKE_PROJECT_NAME N6570DK_FSBL)
project(${CMAKE_PROJECT_NAME})

# Create an executable object type
add_executable(${CMAKE_PROJECT_NAME})

# Include mx-generated
include("mx-generated.cmake")


# In order to use CMake for cross-compiling
set(CMAKE_CXX_COMPILER_FORCED "true")

# Add project symbols (macros)
target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined symbols
)

# Enable CMake support for ASM and C languages
enable_language(C ASM)

# Add include paths
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined include paths
)

# Add sources to executable
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user sources here
)

# Link directories setup
target_link_directories(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined library search paths
)

# Add linked libraries
target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE
    # Add user defined libraries
)

# Remove wrong libob.a library dependency when using cpp files
list(REMOVE_ITEM CMAKE_C_IMPLICIT_LINK_LIBRARIES ob)

# Validate that STM32CubeMX code is compatible with C standard
if((CMAKE_C_STANDARD EQUAL 90) OR (CMAKE_C_STANDARD EQUAL 99))
    message(ERROR "Generated code requires C11 or higher")
endif()

# ===== TOPPERS/ASP3 Core 取り込み（submodule＋ライブラリ専用モード） =====
# FSBL/ が CMAKE_SOURCE_DIR なので asp3/ への相対は 3 段上．
set(ASP3_TARGET stm32n6570_dk)
include(../../../asp3/asp3_stm32cube.cmake)

option(ASP3_ENABLE_TECS "Build with TECS generator (tecsgen + CDL)" OFF)
if(ASP3_ENABLE_TECS)
    set(ASP3_OMIT_TECS OFF CACHE BOOL "Use plain-C syssvc (skip tecsgen)" FORCE)
endif()

if(NOT DEFINED ASP3_APPLDIR)
    set(ASP3_APPLDIR  ${ASP3_CORE_DIR}/sample)
    set(ASP3_APPLNAME sample1)
endif()

if(ASP3_ENABLE_TECS)
    include(${ASP3_STM32_DIR}/cmake/Asp3Tecs.cmake)
    asp3_tecs_setup_paths()
    if(NOT DEFINED ASP3_APPL_CDL)
        set(ASP3_APPL_CDL ${ASP3_STM32_DIR}/sample/sample1.cdl)
    endif()
    asp3_tecs_configure("${ASP3_APPL_CDL}" "${CMAKE_BINARY_DIR}/generated")
endif()

set(ASP3_LIBRARY_ONLY ON CACHE BOOL "build asp3 as library only" FORCE)
add_subdirectory(${ASP3_CORE_DIR} asp3)

target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    ${ASP3_APPLDIR}/${ASP3_APPLNAME}.c
    ${ASP3_EXTRA_APP_C_FILES}
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    ${ASP3_APPLDIR}
)

target_link_libraries(${CMAKE_PROJECT_NAME}
    asp3
)

if(ASP3_ENABLE_TECS)
    asp3_tecs_clear_omit_tecs()
    asp3_tecs_apply_manifest(${CMAKE_PROJECT_NAME})
    asp3_tecs_add_support_sources(${CMAKE_PROJECT_NAME})
else()
    asp3_add_syssvc(${CMAKE_PROJECT_NAME})
endif()
asp3_set_stm32_options(${CMAKE_PROJECT_NAME})









