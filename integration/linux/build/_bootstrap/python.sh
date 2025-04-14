#!/usr/bin/env bash

set -ex

: ${PYTHON_VERSION:=3.12.9}
: ${PYTHON_PIP_VERSION:=25.0.1}

source "${BASH_SOURCE%/*}/_helpers.sh"

PYTHON_KEYS=(
    E3FF2839C048B25C084DEBE9B26995E310250568
    a035c8c19219ba821ecea86b64e628f8d684696d
    7169605F62C751356D054A26A821E680E5FA6305
)
fetch_keys "${PYTHON_KEYS[@]}"

mkdir -p /usr/src/python
cd /usr/src

$WGET -O python.tar.xz \
    "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz"
$WGET -O python.tar.xz.asc \
    "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz.asc"

gpg --batch --verify python.tar.xz.asc python.tar.xz
rm -f python.tar.xz.asc

tar -xJC /usr/src/python --strip-components=1 -f python.tar.xz
rm -f python.tar.xz

cd /usr/src/python

config_args=(
    --build="$(gcc -dumpmachine)" \
    --enable-shared \
    --with-system-expat \
    --with-system-ffi \
    --without-ensurepip \
)

if [ -n "$PYTHON_LOCAL_OPENSSL" ]; then
    config_args+=(
        --with-openssl="/usr/local/openssl"
        --with-openssl-rpath="/usr/local/openssl/lib"
    )
fi

./configure "${config_args[@]}"
make -j "$(nproc)"
make install

find /usr/local -depth \
    \( \
        \( -type d -a \( -name test -o -name tests \) \) \
        -o \
        \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
    \) -exec rm -rf '{}' +

cd /usr/src
rm -rf /usr/src/python

cd /usr/local/bin
ln -sf python3 python
ln -sf python3-config python-config

cd /usr/src
$WGET -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
python get-pip.py \
    --disable-pip-version-check \
    "pip==$PYTHON_PIP_VERSION"

find /usr/local -depth \
    \( \
        \( -type d -a \( -name test -o -name tests \) \) \
        -o \
        \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
    \) -exec rm -rf '{}' +

rm -f get-pip.py
