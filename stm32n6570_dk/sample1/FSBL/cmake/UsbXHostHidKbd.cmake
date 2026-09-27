# USBX Host HID Keyboard（UX_STANDALONE）ソース取り込み
# ミドルウェアは sample1/Middlewares/ST/usbx（Cube FW から必要分を配置）
# 本ファイルは FSBL/CMakeLists.txt から include される前提。

set(_USBX_ROOT
    "${CMAKE_CURRENT_SOURCE_DIR}/../Middlewares/ST/usbx")
set(_USBX_BOARD
    "${CMAKE_CURRENT_SOURCE_DIR}/../board_usb_hid_kbd")

if(NOT EXISTS "${_USBX_ROOT}/common/core/inc/ux_api.h")
    message(FATAL_ERROR "USBX not found at ${_USBX_ROOT}")
endif()

file(GLOB _USBX_CORE_SRC
    "${_USBX_ROOT}/common/core/src/ux_host_*.c"
    "${_USBX_ROOT}/common/core/src/ux_system*.c"
    "${_USBX_ROOT}/common/core/src/ux_utility*.c"
)
file(GLOB _USBX_HID_SRC
    "${_USBX_ROOT}/common/usbx_host_classes/src/ux_host_class_hid*.c"
)
file(GLOB _USBX_HCD_SRC
    "${_USBX_ROOT}/common/usbx_stm32_host_controllers/*.c"
)

# mouse / remote_control は未登録のため除外（リンクサイズ削減）
list(FILTER _USBX_HID_SRC EXCLUDE REGEX "hid_mouse_")
list(FILTER _USBX_HID_SRC EXCLUDE REGEX "hid_remote_control_")
# ThreadX 版 keyboard thread は standalone では不要
list(FILTER _USBX_HID_SRC EXCLUDE REGEX "hid_keyboard_thread\\.c$")
# SETUP バッファ二重解放の修正版を board 側で提供する
list(FILTER _USBX_HCD_SRC EXCLUDE REGEX "ux_hcd_stm32_request_trans_finish\\.c$")

target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    ${_USBX_CORE_SRC}
    ${_USBX_HID_SRC}
    ${_USBX_HCD_SRC}
    ${_USBX_BOARD}/ux_hcd_stm32_request_trans_finish.c
    ${_USBX_BOARD}/board_usb_hid_kbd.c
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    ${_USBX_BOARD}
    ${_USBX_ROOT}/common/core/inc
    ${_USBX_ROOT}/common/usbx_host_classes/inc
    ${_USBX_ROOT}/common/usbx_stm32_host_controllers
    ${_USBX_ROOT}/ports/cortex_m7/gnu/inc
)

target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
    UX_INCLUDE_USER_DEFINE_FILE
)

# USBX は警告が多いので緩和（本体アプリの厳格さは維持）
foreach(_src ${_USBX_CORE_SRC} ${_USBX_HID_SRC} ${_USBX_HCD_SRC}
             ${_USBX_BOARD}/ux_hcd_stm32_request_trans_finish.c)
    set_source_files_properties("${_src}" PROPERTIES
        COMPILE_FLAGS "-Wno-unused-parameter -Wno-sign-compare")
endforeach()
