#
#  TECS (tecsgen) integration for ASP3 + STM32Cube CMake builds.
#
#  configure 時に tecsgen を実行し、生成された CMakeLists.tecsgen.cmake
#  （ソース一覧マニフェスト）を include する。Makefile.tecsgen は使わない。
#
#  前提変数（asp3_stm32cube.cmake および呼び出し側で設定）:
#    ASP3_STM32_DIR, ASP3_CORE_DIR, ASP3_TARGET_DIR
#    ASP3_TECSGEN_DIR, ASP3_TECS_KERNEL_DIR
#

if(NOT DEFINED ASP3_TECSGEN_DIR)
    get_filename_component(ASP3_TECSGEN_DIR
        "${ASP3_STM32_DIR}/../tecsgen" ABSOLUTE)
endif()
if(NOT DEFINED ASP3_TECS_KERNEL_DIR)
    set(ASP3_TECS_KERNEL_DIR "${ASP3_STM32_DIR}/tecs_kernel")
endif()

#  マニフェストが ${ASP3_SRCDIR}/<celltype>.c を参照するためのルート。
#  セル実装は syssvc/・tecs_kernel/・target/・chip に散在するので、
#  apply 時に複数ディレクトリを探索する。
if(NOT DEFINED ASP3_SRCDIR)
    set(ASP3_SRCDIR "${ASP3_STM32_DIR}")
endif()

function(asp3_tecs_run_generator)
    set(options "")
    set(oneValueArgs CDL_FILE GEN_DIR)
    set(multiValueArgs INCLUDE_DIRS COMPILE_DEFINITIONS)
    cmake_parse_arguments(TECS "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    if(NOT TECS_CDL_FILE)
        message(FATAL_ERROR "asp3_tecs_run_generator: CDL_FILE is required")
    endif()
    if(NOT TECS_GEN_DIR)
        message(FATAL_ERROR "asp3_tecs_run_generator: GEN_DIR is required")
    endif()
    if(NOT EXISTS "${TECS_CDL_FILE}")
        message(FATAL_ERROR "asp3_tecs_run_generator: CDL not found: ${TECS_CDL_FILE}")
    endif()
    if(NOT EXISTS "${ASP3_TECSGEN_DIR}/tecsgen.rb")
        message(FATAL_ERROR
            "tecsgen.rb not found: ${ASP3_TECSGEN_DIR}/tecsgen.rb")
    endif()

    find_program(RUBY_EXECUTABLE ruby REQUIRED)

    file(MAKE_DIRECTORY "${TECS_GEN_DIR}")

    set(_tecs_includes "")
    foreach(_inc ${TECS_INCLUDE_DIRS})
        list(APPEND _tecs_includes "-I${_inc}")
    endforeach()

    set(_tecs_defs "")
    foreach(_def ${TECS_COMPILE_DEFINITIONS})
        # ジェネレータ式は tecsgen の CPP に渡せない
        if(NOT _def MATCHES "^\\$<")
            list(APPEND _tecs_defs "-D${_def}")
        endif()
    endforeach()

    set(_cpp_cmd
        "${CMAKE_C_COMPILER}"
        ${_tecs_defs}
        ${_tecs_includes}
        -DTECSGEN
        -E
    )
    string(REPLACE ";" " " _cpp_cmd_str "${_cpp_cmd}")

    set(_tecsgen_cmd
        ${RUBY_EXECUTABLE}
        "${ASP3_TECSGEN_DIR}/tecsgen.rb"
        "${TECS_CDL_FILE}"
        -R ${_tecs_includes}
        --cpp "${_cpp_cmd_str}"
        -g "${TECS_GEN_DIR}"
    )

    message(STATUS "Running tecsgen: ${TECS_CDL_FILE}")
    execute_process(
        COMMAND ${_tecsgen_cmd}
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
        RESULT_VARIABLE _tecsgen_result
        OUTPUT_VARIABLE _tecsgen_out
        ERROR_VARIABLE _tecsgen_err
    )
    if(NOT _tecsgen_result EQUAL 0)
        message(FATAL_ERROR "tecsgen failed:\n${_tecsgen_out}\n${_tecsgen_err}")
    endif()

    set(_manifest "${TECS_GEN_DIR}/CMakeLists.tecsgen.cmake")
    if(NOT EXISTS "${_manifest}")
        message(FATAL_ERROR "tecsgen did not produce ${_manifest}")
    endif()
    if(NOT EXISTS "${TECS_GEN_DIR}/tecsgen.cfg")
        message(FATAL_ERROR "tecsgen did not produce ${TECS_GEN_DIR}/tecsgen.cfg")
    endif()
endfunction()

function(_asp3_tecs_resolve_source src out_var)
    if(IS_ABSOLUTE "${src}")
        set(${out_var} "${src}" PARENT_SCOPE)
        return()
    endif()
    if(src MATCHES "^\\$\\{TECS_GEN_DIR\\}/" OR src MATCHES "^\\$\\(GEN_DIR\\)/")
        string(REGEX REPLACE "^\\$\\{TECS_GEN_DIR\\}/" "" _rel "${src}")
        string(REGEX REPLACE "^\\$\\(GEN_DIR\\)/" "" _rel "${_rel}")
        set(${out_var} "${TECS_GEN_DIR}/${_rel}" PARENT_SCOPE)
        return()
    endif()

    #  同名セル（tUsart.c 等）がチップごとに存在するので、
    #  現ターゲットの CHIPDIR だけを探索する（H5 を先に探すと N6 が潰れる）。
    set(_search
        "${TECS_GEN_DIR}"
        "${ASP3_STM32_DIR}"
        "${ASP3_STM32_DIR}/syssvc"
        "${ASP3_TECS_KERNEL_DIR}"
        "${ASP3_TARGET_DIR}"
    )
    if(ASP3_TECS_CHIPDIR)
        list(APPEND _search "${ASP3_TECS_CHIPDIR}")
    endif()
    list(APPEND _search
        "${ASP3_CORE_DIR}"
        "${ASP3_CORE_DIR}/syssvc"
        "${ASP3_SRCDIR}"
    )
    foreach(_dir ${TECS_INCLUDE_DIRS})
        list(APPEND _search "${_dir}")
    endforeach()

    foreach(_dir ${_search})
        if(EXISTS "${_dir}/${src}")
            set(${out_var} "${_dir}/${src}" PARENT_SCOPE)
            return()
        endif()
    endforeach()

    # 見つからなくても生成物・後続探索のためパスを返す
    set(${out_var} "${ASP3_SRCDIR}/${src}" PARENT_SCOPE)
endfunction()

function(asp3_tecs_apply_manifest target)
    if(NOT TARGET ${target})
        message(FATAL_ERROR "asp3_tecs_apply_manifest: target ${target} not found")
    endif()

    set(_all_tecs_sources
        ${TECS_TECSGEN_SOURCES}
        ${TECS_PLUGIN_TECSGEN_SOURCES}
        ${TECS_PLUGIN_CELLTYPE_SOURCES}
        ${TECS_CELLTYPE_SOURCES}
        ${TECS_PLUGIN_EXTRA_SOURCES}
    )

    foreach(_src ${_all_tecs_sources})
        _asp3_tecs_resolve_source("${_src}" _resolved)
        if(NOT EXISTS "${_resolved}")
            message(WARNING "TECS source not found (may be generated later): ${_src} -> ${_resolved}")
        endif()
        target_sources(${target} PRIVATE "${_resolved}")
    endforeach()

    target_include_directories(${target} PRIVATE
        ${TECS_INCLUDE_DIRS}
        ${ASP3_TECS_KERNEL_DIR}
        ${TECS_GEN_DIR}
    )
    if(TECS_COMPILE_DEFINITIONS)
        target_compile_definitions(${target} PRIVATE ${TECS_COMPILE_DEFINITIONS})
    endif()

    if(TECS_LINK_OPTIONS)
        target_link_options(${target} PRIVATE ${TECS_LINK_OPTIONS})
    endif()
endfunction()

#  asp3_core が PUBLIC で付ける TOPPERS_OMIT_TECS を取り除く。
#  submodule 未改修時のワークアラウンド。option(ASP3_OMIT_TECS) が入れば不要。
function(asp3_tecs_clear_omit_tecs)
    foreach(_tgt asp3 cfg1_out)
        if(NOT TARGET ${_tgt})
            continue()
        endif()
        foreach(_prop COMPILE_DEFINITIONS INTERFACE_COMPILE_DEFINITIONS)
            get_target_property(_defs ${_tgt} ${_prop})
            if(_defs AND NOT _defs STREQUAL "_defs-NOTFOUND")
                list(REMOVE_ITEM _defs TOPPERS_OMIT_TECS)
                set_property(TARGET ${_tgt} PROPERTY ${_prop} "${_defs}")
            endif()
        endforeach()
    endforeach()
endfunction()

function(asp3_tecs_add_support_sources target)
    target_sources(${target} PRIVATE
        ${ASP3_TECS_KERNEL_DIR}/init_tecs.c
        ${ASP3_CORE_DIR}/library/log_output.c
        ${ASP3_CORE_DIR}/library/vasyslog.c
        ${ASP3_CORE_DIR}/library/t_perror.c
        ${ASP3_CORE_DIR}/library/strerror.c
    )
    target_include_directories(${target} PRIVATE
        ${ASP3_TECS_KERNEL_DIR}
        ${ASP3_STM32_DIR}/syssvc
        ${TECS_GEN_DIR}
    )
endfunction()

function(asp3_tecs_configure cdl_file gen_dir)
    if(NOT ASP3_TECS_INCLUDE_DIRS)
        message(FATAL_ERROR
            "asp3_tecs_configure: ASP3_TECS_INCLUDE_DIRS is empty")
    endif()

    asp3_tecs_run_generator(
        CDL_FILE "${cdl_file}"
        GEN_DIR "${gen_dir}"
        INCLUDE_DIRS ${ASP3_TECS_INCLUDE_DIRS}
        COMPILE_DEFINITIONS ${ASP3_TECS_COMPILE_DEFINITIONS}
    )

    set(TECS_GEN_DIR "${gen_dir}" CACHE INTERNAL "TECS generated file directory")
    include("${gen_dir}/CMakeLists.tecsgen.cmake")

    # include() は function スコープに set するため、呼び出し元へ戻す
    set(TECS_IMPORT_CDLS "${TECS_IMPORT_CDLS}" PARENT_SCOPE)
    set(TECS_TECSGEN_SOURCES "${TECS_TECSGEN_SOURCES}" PARENT_SCOPE)
    set(TECS_PLUGIN_TECSGEN_SOURCES "${TECS_PLUGIN_TECSGEN_SOURCES}" PARENT_SCOPE)
    set(TECS_PLUGIN_CELLTYPE_SOURCES "${TECS_PLUGIN_CELLTYPE_SOURCES}" PARENT_SCOPE)
    set(TECS_CELLTYPE_SOURCES "${TECS_CELLTYPE_SOURCES}" PARENT_SCOPE)
    set(TECS_PLUGIN_EXTRA_SOURCES "${TECS_PLUGIN_EXTRA_SOURCES}" PARENT_SCOPE)
    set(TECS_INCLUDE_DIRS "${TECS_INCLUDE_DIRS}" PARENT_SCOPE)
    set(TECS_COMPILE_DEFINITIONS "${TECS_COMPILE_DEFINITIONS}" PARENT_SCOPE)
    set(TECS_LINK_OPTIONS "${TECS_LINK_OPTIONS}" PARENT_SCOPE)

    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${cdl_file}")
    foreach(_cdl ${TECS_IMPORT_CDLS})
        if(EXISTS "${_cdl}")
            set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_cdl}")
        endif()
    endforeach()
endfunction()
