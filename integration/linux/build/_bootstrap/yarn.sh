#!/usr/bin/env bash

set -ex

: ${YARN_VERSION:=1.22.19}

source "${BASH_SOURCE%/*}/_helpers.sh"

YARN_KEYS=(
    6A010C5166006599AA17F08146C2130DFD2497F5
)
fetch_keys "${YARN_KEYS[@]}"

mkdir -p /usr/src/yarn
cd /usr/src

$WGET -O yarn.tar.gz "https://yarnpkg.com/downloads/${YARN_VERSION}/yarn-v${YARN_VERSION}.tar.gz"
$WGET -O yarn.tar.gz.asc "https://yarnpkg.com/downloads/${YARN_VERSION}/yarn-v${YARN_VERSION}.tar.gz.asc"

gpg --batch --verify "yarn.tar.gz.asc" "yarn.tar.gz"
rm "yarn.tar.gz.asc"

tar -xzC /usr/src/yarn --strip-components=1 -f "yarn.tar.gz"
rm -f "yarn.tar.gz"

ln -s /usr/src/yarn/bin/yarn /usr/local/bin/yarn
ln -s /usr/src/yarn/bin/yarnpkg /usr/local/bin/yarnpkg
