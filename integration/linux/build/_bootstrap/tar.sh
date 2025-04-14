#!/usr/bin/env bash

set -ex

: ${TAR_VERSION:=1.35}

source "${BASH_SOURCE%/*}/_helpers.sh"

TAR_KEYS=(
    7E3792A9D8ACF7D633BC1588ED97E90E62AA7E34
    325F650C4C2B6AD58807327A3602B07F55D0C732
)
fetch_keys "${TAR_KEYS[@]}"

mkdir -p /usr/src/tar
cd /usr/src

$WGET -O tar.tar.xz "https://ftp.gnu.org/gnu/tar/tar-${TAR_VERSION}.tar.xz"
$WGET -O tar.tar.xz.sign "https://ftp.gnu.org/gnu/tar/tar-${TAR_VERSION}.tar.xz.sig"

gpg --batch --verify tar.tar.xz.sign tar.tar.xz
rm -f tar.tar.xz.sign

tar -xJC /usr/src/tar --strip-components=1 -f tar.tar.xz
rm -f tar.tar.xz

cd /usr/src/tar
env FORCE_UNSAFE_CONFIGURE=1 ./configure \
	--bindir=/usr/local/bin/ \
	--libexecdir=/usr/local/sbin/
make -j $(nproc)
make install
cd /usr/src
rm -rf /usr/src/tar
