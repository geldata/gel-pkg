#!/usr/bin/env bash

set -ex

: ${NODE_VERSION:=16.16.0}

source "${BASH_SOURCE%/*}/_helpers.sh"

NODE_KEYS=(
    4ED778F539E3634C779C87C6D7062848A1AB005C
    141F07595B7B3FFE74309A937405533BE57C7D57
    94AE36675C464D64BAFA68DD7434390BDBE9B9C5
    74F12602B6F1C4E913FAA37AD3A89613643B6201
    71DCFD284A79C3B38668286BC97EC7A07EDE3FC1
    8FCCA13FEF1D0C2E91008E09770F7A9A5AE15600
    C4F0DFFF4E8C1A8236409D08E73BC641CC11F4C8
    C82FA3AE1CBEDC6BE46B9360C43CEC45C17AB93C
    DD8F2338BAE7501E3DD5AC78C273792F7D83545D
    A48C2BEE680E841632CD4E44F07496B3EB3C1762
    108F52B48DB57BB0CC439B2997B01419BD92F80A
    B9E2F5981AA6E0CD28160D9FF13993A75599653C
)
fetch_keys "${NODE_KEYS[@]}"

if getconf GNU_LIBC_VERSION 2>&1 >/dev/null; then
    libc="glibc"
elif ldd --version 2>&1 | grep musl >/dev/null; then
    libc="musl"
else
    libc=""
fi

node_server=

case "$libc" in
    glibc)
        node_server="https://nodejs.org/dist/v${NODE_VERSION}"
        case "$(arch)" in
            x86_64)
                NODE_ARCH='x64'
                ;;
            arm64)
                NODE_ARCH='arm64'
                ;;
            aarch64)
                NODE_ARCH='arm64'
                ;;
            *)
                echo "unsupported architecture"
                exit 1
                ;;
        esac
        ;;
    musl)
        node_server="https://unofficial-builds.nodejs.org/download/release/v${NODE_VERSION}/"
        case "$(arch)" in
            x86_64)
                NODE_ARCH='x64-musl'
                ;;
            *)
                echo "unsupported architecture"
                exit 1
                ;;
        esac
        ;;
    *)
        echo "unsupported libc"
        exit 1
        ;;
esac

$WGET "${node_server}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz"
$WGET "${node_server}/SHASUMS256.txt.asc"

gpg --batch --decrypt --output SHASUMS256.txt SHASUMS256.txt.asc
grep " node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz\$" SHASUMS256.txt | sha256sum -c -
tar -xJf "node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" -C /usr/local --strip-components=1 --no-same-owner
rm "node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" SHASUMS256.txt.asc SHASUMS256.txt

ln -s /usr/local/bin/node /usr/local/bin/nodejs
