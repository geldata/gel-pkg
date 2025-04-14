#!/usr/bin/env bash

set -ex

: ${CMAKE_VERSION:=3.30.2}

source "${BASH_SOURCE%/*}/_helpers.sh"

CMAKE_KEYS=(
    CBA23971357C2E6590D9EFD3EC8FEF3A7BFB4EDA
)
fetch_keys "${CMAKE_KEYS[@]}"


CMAKE_ARCH=

if getconf GNU_LIBC_VERSION >&/dev/null 2>&1; then
    case "$(arch)" in
    x86_64)
        CMAKE_ARCH='x86_64'
        ;;
    arm64)
        CMAKE_ARCH='aarch64'
        ;;
    aarch64)
        CMAKE_ARCH='aarch64'
        ;;
    esac
fi

mkdir -p /usr/src/cmake
cd /usr/src

_server="https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}"
$WGET "${_server}/cmake-${CMAKE_VERSION}-SHA-256.txt"
$WGET "${_server}/cmake-${CMAKE_VERSION}-SHA-256.txt.asc"

gpg --batch --verify "cmake-${CMAKE_VERSION}-SHA-256.txt.asc" "cmake-${CMAKE_VERSION}-SHA-256.txt"
rm -f "cmake-${CMAKE_VERSION}-SHA-256.txt.asc"

if [ -n "${CMAKE_ARCH}" ]; then
	$WGET "${_server}/cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz"
	grep " cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz\$" "cmake-${CMAKE_VERSION}-SHA-256.txt" | sha256sum -c -
    rm -f "cmake-${CMAKE_VERSION}-SHA-256.txt"

    tar -xzf "cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz" -C /usr/local --strip-components=1 --no-same-owner
    rm -f "cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz"
else
    $WGET "${_server}/cmake-${CMAKE_VERSION}.tar.gz"
    grep " cmake-${CMAKE_VERSION}.tar.gz\$" "cmake-${CMAKE_VERSION}-SHA-256.txt" | sha256sum -c -
    rm -f "cmake-${CMAKE_VERSION}-SHA-256.txt"

    tar -xzf "cmake-${CMAKE_VERSION}.tar.gz" -C /usr/src/cmake --strip-components=1 --no-same-owner
    rm -f "cmake-${CMAKE_VERSION}.tar.gz"

    cd /usr/src/cmake
    ./bootstrap --parallel="$(nproc)"
    make -j "$(nproc)"
    make install
    cd /usr/src
    rm -rf /usr/src/cmake
fi
