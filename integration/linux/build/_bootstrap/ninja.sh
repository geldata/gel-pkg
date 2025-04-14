#!/usr/bin/env bash

set -ex

: ${NINJA_VERSION:=1.12.1}

mkdir -p /usr/src/ninja
cd /usr/src
$WGET -O ninja.tar.gz "https://github.com/ninja-build/ninja/archive/refs/tags/v${NINJA_VERSION}.tar.gz"
tar -xzC /usr/src/ninja --strip-components=1 -f ninja.tar.gz
rm ninja.tar.gz
cd /usr/src/ninja
./configure.py --bootstrap --verbose
cp -a ./ninja /usr/local/bin/ninja
cd /usr/src
rm -rf /usr/src/ninja
