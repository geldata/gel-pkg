#!/usr/bin/env bash

set -ex

: ${GZIP_VERSION:=1.13}

source "${BASH_SOURCE%/*}/_helpers.sh"

GZIP_KEYS=(
    155D3FC500C834486D1EEA677FD9FCCB000BEEEE
)
fetch_keys "${GZIP_KEYS[@]}"

mkdir -p /usr/src/gzip
cd /usr/src

$WGET -O gzip.tar.gz "https://ftp.gnu.org/gnu/gzip/gzip-${GZIP_VERSION}.tar.gz"
$WGET -O gzip.tar.gz.sign "https://ftp.gnu.org/gnu/gzip/gzip-${GZIP_VERSION}.tar.gz.sig"

gpg --batch --verify gzip.tar.gz.sign gzip.tar.gz
rm -f gzip.tar.gz.sign

tar -xzC /usr/src/gzip --strip-components=1 -f gzip.tar.gz
rm -f gzip.tar.gz

cd /usr/src/gzip
./configure \
	--bindir=/usr/local/bin/ \
	--libexecdir=/usr/local/sbin/
make -j $(nproc)
make install
cd /usr/src
rm -rf /usr/src/gzip
