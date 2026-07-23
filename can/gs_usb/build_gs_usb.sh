#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly KERNEL_RELEASE="$(uname -r)"
readonly KERNEL_BUILD="/lib/modules/${KERNEL_RELEASE}/build"
readonly BUILD_DIR="${SCRIPT_DIR}/build/${KERNEL_RELEASE}"
readonly SOURCE_URL="https://raw.githubusercontent.com/gregkh/linux/v5.15.148/drivers/net/can/usb/gs_usb.c"
readonly SOURCE_SHA256="d1ee028fd35e29f1c120577f62d1c3d670731b3b5104f4107278d061a7e5ac06"
readonly MODULE_PATH="${BUILD_DIR}/gs_usb.ko"
readonly INSTALL_PATH="/lib/modules/${KERNEL_RELEASE}/extra/gs_usb.ko"

usage() {
    cat <<'EOF'
Usage: ./build_gs_usb.sh [--build|--install|--uninstall|--clean]

  --build      Download the pinned source and build gs_usb.ko (default)
  --install    Build, install, and load gs_usb.ko (requires sudo)
  --uninstall  Unload and remove the installed module (requires sudo)
  --clean      Remove generated build files for the running kernel
EOF
}

fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

check_environment() {
    [[ "${KERNEL_RELEASE}" == "5.15.148-tegra" ]] || fail \
        "this pinned source was validated only with 5.15.148-tegra; running kernel is ${KERNEL_RELEASE}"
    [[ -f "${KERNEL_BUILD}/Makefile" ]] || fail \
        "kernel headers are missing: ${KERNEL_BUILD}/Makefile"
    [[ -f "${KERNEL_BUILD}/Module.symvers" ]] || fail \
        "kernel symbol versions are missing: ${KERNEL_BUILD}/Module.symvers"

    require_command make
    require_command gcc
    require_command sha256sum
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        fail "curl or wget is required to download gs_usb.c"
    fi
}

download_source() {
    local source_path="${BUILD_DIR}/gs_usb.c"
    local actual_sha256

    mkdir -p "${BUILD_DIR}"
    if [[ ! -f "${source_path}" ]]; then
        printf 'Downloading %s\n' "${SOURCE_URL}"
        if command -v curl >/dev/null 2>&1; then
            curl --fail --location --silent --show-error \
                "${SOURCE_URL}" --output "${source_path}"
        else
            wget --quiet --output-document="${source_path}" "${SOURCE_URL}"
        fi
    fi

    actual_sha256="$(sha256sum "${source_path}" | awk '{print $1}')"
    if [[ "${actual_sha256}" != "${SOURCE_SHA256}" ]]; then
        rm -f "${source_path}"
        fail "source checksum mismatch (expected ${SOURCE_SHA256}, got ${actual_sha256})"
    fi
}

build_module() {
    check_environment
    download_source
    printf 'obj-m += gs_usb.o\n' > "${BUILD_DIR}/Makefile"

    printf 'Building gs_usb for %s\n' "${KERNEL_RELEASE}"
    make -C "${KERNEL_BUILD}" M="${BUILD_DIR}" modules

    [[ -f "${MODULE_PATH}" ]] || fail "build completed without producing ${MODULE_PATH}"
    printf '\nBuilt module: %s\n' "${MODULE_PATH}"
    modinfo "${MODULE_PATH}" | grep -E '^(description|alias|depends|name|vermagic):'
}

install_module() {
    build_module
    printf '\nInstalling %s\n' "${INSTALL_PATH}"
    sudo install -D -m 0644 "${MODULE_PATH}" "${INSTALL_PATH}"
    sudo depmod -a "${KERNEL_RELEASE}"
    sudo modprobe gs_usb

    printf '\nLoaded module:\n'
    lsmod | grep '^gs_usb'
    printf '\nCAN interfaces:\n'
    ip -brief link show type can
    printf '\nUSB topology:\n'
    lsusb -t
}

uninstall_module() {
    if lsmod | grep -q '^gs_usb'; then
        sudo modprobe -r gs_usb
    fi
    if [[ -f "${INSTALL_PATH}" ]]; then
        sudo rm -f -- "${INSTALL_PATH}"
        sudo depmod -a "${KERNEL_RELEASE}"
    fi
    printf 'Removed %s\n' "${INSTALL_PATH}"
}

clean_build() {
    if [[ -d "${BUILD_DIR}" ]]; then
        rm -rf -- "${BUILD_DIR}"
    fi
    printf 'Removed %s\n' "${BUILD_DIR}"
}

action="${1:---build}"
case "${action}" in
    --build)
        build_module
        ;;
    --install)
        install_module
        ;;
    --uninstall)
        uninstall_module
        ;;
    --clean)
        clean_build
        ;;
    --help|-h)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
