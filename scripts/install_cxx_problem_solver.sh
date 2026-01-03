#!/usr/bin/env bash
set -eo pipefail

# Constants
SC_MACHINE_VERSION="0.10.5"
SC_MACHINE_DESTINATION_DIR="install/sc-machine"

SCL_MACHINE_VERSION="0.3.2"
SCL_MACHINE_DESTINATION_DIR="install/scl-machine"

SCP_MACHINE_VERSION="0.1.2"
SCP_MACHINE_DESTINATION_DIR="install/scp-machine"

PS_COMMON_LIB_VERSION="0.1.1"
PS_COMMON_LIB_DESTINATION_DIR="install/ps-common-lib"

FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_VERSION="0.1.0"
FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_DESTINATION_DIR="install/fixed-search-strategy-template-processing-module"

get_archive_name() {
    local os_name=$(uname -s)
    case "$os_name" in
        Linux)
            echo "$1-$2-Linux.tar.gz"
            ;;
        Darwin)
            echo "$1-$2-Darwin.tar.gz"
            ;;
        *)
            echo "Unsupported operating system: $os_name"
            exit 1
            ;;
    esac
}

download_archive() {
    local url="$1"
    echo "Downloading ${url}..."
    if ! curl -LO "${url}"; then
        echo "Error downloading ${url}"
        exit 1
    fi
}

extract_archive() {
    local archive="$1"
    local destination_dir="$2"
    echo "Creating directory ${destination_dir} and extracting files..."
    mkdir -p "${destination_dir}" && tar -xvzf "${archive}" -C "${destination_dir}" --strip-components 1
}

cleanup() {
    local archive="$1"
    local destination_dir="$2"
    echo "Cleaning up..."
    rm -f "${archive}"
    rm -rf "${destination_dir}/include"
}

SC_MACHINE_ARCHIVE=$(get_archive_name "sc-machine" "${SC_MACHINE_VERSION}")
SC_MACHINE_URL="https://github.com/ostis-ai/sc-machine/releases/download/${SC_MACHINE_VERSION}/${SC_MACHINE_ARCHIVE}"

download_archive "${SC_MACHINE_URL}"
extract_archive "${SC_MACHINE_ARCHIVE}" "${SC_MACHINE_DESTINATION_DIR}"
cleanup "${SC_MACHINE_ARCHIVE}" "${SC_MACHINE_DESTINATION_DIR}"

SCL_MACHINE_ARCHIVE=$(get_archive_name "scl-machine" "${SCL_MACHINE_VERSION}")
SCL_MACHINE_URL="https://github.com/ostis-ai/scl-machine/releases/download/${SCL_MACHINE_VERSION}/${SCL_MACHINE_ARCHIVE}"

download_archive "${SCL_MACHINE_URL}"
extract_archive "${SCL_MACHINE_ARCHIVE}" "${SCL_MACHINE_DESTINATION_DIR}"
cleanup "${SCL_MACHINE_ARCHIVE}" "${SCL_MACHINE_DESTINATION_DIR}"

SCP_MACHINE_ARCHIVE=$(get_archive_name "scp-machine" "${SCP_MACHINE_VERSION}")
SCP_MACHINE_URL="https://github.com/ostis-ai/scp-machine/releases/download/${SCP_MACHINE_VERSION}/${SCP_MACHINE_ARCHIVE}"

download_archive "${SCP_MACHINE_URL}"
extract_archive "${SCP_MACHINE_ARCHIVE}" "${SCP_MACHINE_DESTINATION_DIR}"
cleanup "${SCP_MACHINE_ARCHIVE}" "${SCP_MACHINE_DESTINATION_DIR}"

PS_COMMON_LIB_ARCHIVE=$(get_archive_name "ps-common-lib" "${PS_COMMON_LIB_VERSION}")
PS_COMMON_LIB_URL="https://github.com/ostis-ai/ostis-ps-lib/releases/download/${PS_COMMON_LIB_VERSION}/${PS_COMMON_LIB_ARCHIVE}"

download_archive "${PS_COMMON_LIB_URL}"
extract_archive "${PS_COMMON_LIB_ARCHIVE}" "${PS_COMMON_LIB_DESTINATION_DIR}"
cleanup "${PS_COMMON_LIB_ARCHIVE}" "${PS_COMMON_LIB_DESTINATION_DIR}"

FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_ARCHIVE=$(get_archive_name "fixed-search-strategy-template-processing-module" "${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_VERSION}")
FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_URL="https://github.com/ostis-ai/ostis-ps-lib/releases/download/${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_VERSION}/${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_ARCHIVE}"

download_archive "${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_URL}"
extract_archive "${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_ARCHIVE}" "${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_DESTINATION_DIR}"
cleanup "${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_ARCHIVE}" "${FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE_DESTINATION_DIR}"

echo "Installation complete!"
