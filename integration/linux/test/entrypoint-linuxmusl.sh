#!/bin/sh

set -ex

dest="artifacts"
if [ -n "${PKG_PLATFORM}" ]; then
    dest="${dest}/${PKG_PLATFORM}"
fi
if [ -n "${PKG_PLATFORM_LIBC}" ]; then
    dest="${dest}${PKG_PLATFORM_LIBC}"
fi
if [ -n "${PKG_PLATFORM_VERSION}" ]; then
    dest="${dest}-${PKG_PLATFORM_VERSION}"
fi
if [ -n "${PKG_TEST_JOBS}" ]; then
    dash_j="-j${PKG_TEST_JOBS}"
else
    dash_j=""
fi

machine=$(uname -m)
cliurl="https://packages.geldata.com/dist/${machine}-unknown-linux-musl/gel-cli"

try=1
while [ $try -le 5 ]; do
    curl --proto '=https' --tlsv1.2 -sSfL "$cliurl" -o /bin/gel && break || true
    try=$(( $try + 1 ))
    echo "Retrying in 10 seconds (try #${try})"
    sleep 10
done

chmod +x /bin/gel
ln -s gel /bin/edgedb

tarball=
for pack in ${dest}/*.tar; do
    if [ -e "${pack}" ]; then
        tarball=$(tar -xOf "${pack}" "build-metadata.json" \
                  | jq -r ".installrefs[]" \
                  | grep ".tar.gz$")
        if [ -n "${tarball}" ]; then
            break
        fi
    fi
done

if [ -z "${tarball}" ]; then
    echo "${dest} does not contain a valid build tarball" >&2
    exit 1
fi

mkdir /gel
chmod 1777 /tmp
tar -xOf "${pack}" "${tarball}" | tar -xzf- --strip-components=1 -C "/gel/"
touch /etc/group
addgroup gel
touch /etc/passwd
adduser -G gel -H -D gel

if [ "$1" == "bash" ]; then
    exec /bin/sh
fi

exec gosu gel:gel /gel/bin/python3 \
    -m edb.tools --no-devmode test \
    /gel/share/tests \
    -e cqa_ -e tools_ \
    --verbose ${dash_j}
