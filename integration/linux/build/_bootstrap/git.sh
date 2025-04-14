#!/usr/bin/env bash

set -ex

: ${GIT_VERSION:=2.33.1}

source "${BASH_SOURCE%/*}/_helpers.sh"

GIT_KEYS=(
    E1F036B1FEE7221FC778ECEFB0B5E88696AFE6CB
)
fetch_keys "${GIT_KEYS[@]}"

mkdir -p /usr/src/git
cd /usr/src

$WGET -O git.tar.xz "https://www.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.xz"
$WGET -O git.tar.sign "https://www.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.sign"

# gpg --batch --verify git.tar.sign git.tar.xz
rm -f git.tar.sign

tar -xJC /usr/src/git --strip-components=1 -f git.tar.xz
rm -f git.tar.xz

cd /usr/src/git
make prefix=/usr/local V=1 -j $(nproc) all
make prefix=/usr/local install
cd /usr/src
rm -rf /usr/src/git
