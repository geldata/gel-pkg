#!/usr/bin/env bash

set -ex

: ${PKGCONF_VERSION:=2.3.0}

mkdir -p /usr/src/pkgconf
cd /usr/src
$WGET -O pkgconf.tar.xz "https://distfiles.ariadne.space/pkgconf/pkgconf-${PKGCONF_VERSION}.tar.xz"
tar -xJC /usr/src/pkgconf --strip-components=1 -f pkgconf.tar.xz
rm pkgconf.tar.xz
cd /usr/src/pkgconf
./configure
make -j $(nproc)
make install
cd /usr/src
rm -rf /usr/src/pkgconf
ln -sf /usr/local/bin/pkgconf /usr/bin/pkg-config
