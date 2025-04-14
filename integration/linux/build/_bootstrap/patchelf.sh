#!/usr/bin/env bash

set -ex

: ${PATCHELF_VERSION:=0.13}

mkdir -p /usr/src/patchelf
cd /usr/src

$WGET -O patchelf.tar.bz2 "https://github.com/NixOS/patchelf/releases/download/${PATCHELF_VERSION}/patchelf-${PATCHELF_VERSION}.tar.bz2"

tar -xjC /usr/src/patchelf --strip-components=1 -f patchelf.tar.bz2
rm -f patchelf.tar.bz2

cd /usr/src/patchelf
./configure
make -j $(nproc)
make install
cd /usr/src
rm -rf /usr/src/patchelf
