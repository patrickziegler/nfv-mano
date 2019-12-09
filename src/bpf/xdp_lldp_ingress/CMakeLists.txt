cmake_minimum_required(VERSION 3.2)

project(xdp_lldp_ingress C)

set(ARCH "x86")
set(KDIR "${PROJECT_SOURCE_DIR}/../../../extern/linux")

add_library("${PROJECT_NAME}_kern")

target_sources("${PROJECT_NAME}_kern" PRIVATE
    "${PROJECT_SOURCE_DIR}/src/${PROJECT_NAME}_kern.c"
    )

target_include_directories("${PROJECT_NAME}_kern" PRIVATE
    "${PROJECT_SOURCE_DIR}/../bpf_common/include"
    "${KDIR}/include"
    "${KDIR}/include/uapi"
    "${KDIR}/arch/$(ARCH)/include"
    "${KDIR}/arch/$(ARCH)/include/uapi"
    "${KDIR}/arch/$(ARCH)/include/generated"
    "${KDIR}/arch/$(ARCH)/include/generated/uapi"
    "${KDIR}/tools/testing/selftests/bpf"
    "${KDIR}/tools/lib/bpf"  # bpf_helpers.h
    )

add_executable("${PROJECT_NAME}_user")

target_sources("${PROJECT_NAME}_user" PRIVATE
    "src/${PROJECT_NAME}_user.c"
    )

target_include_directories("${PROJECT_NAME}_user" PRIVATE
    "${KDIR}/tools/lib/"
    )
