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

curl -fsSLO --compressed "https://yarnpkg.com/downloads/${YARN_VERSION}/yarn-v${YARN_VERSION}.tar.gz"
curl -fsSLO --compressed "https://yarnpkg.com/downloads/${YARN_VERSION}/yarn-v${YARN_VERSION}.tar.gz.asc"

gpg --batch --verify "yarn-v${YARN_VERSION}.tar.gz.asc" "yarn-v${YARN_VERSION}.tar.gz"
rm "yarn-v${YARN_VERSION}.tar.gz.asc"

tar -xzC /usr/src/yarn --strip-components=1 -f "yarn-v${YARN_VERSION}.tar.gz"
rm -f "yarn-v${YARN_VERSION}.tar.gz"

ln -s /usr/src/yarn/bin/yarn /usr/local/bin/yarn
ln -s /usr/src/yarn/bin/yarnpkg /usr/local/bin/yarnpkg
