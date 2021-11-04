#!/bin/bash

set -ex

dest="artifacts"
if [ -n "${PKG_PLATFORM}" ]; then
    dest+="/${PKG_PLATFORM}"
fi
if [ -n "${PKG_PLATFORM_VERSION}" ]; then
    dest+="-${PKG_PLATFORM_VERSION}"
fi

dist='el$releasever'
if [ -n "${PKG_SUBDIST}" ]; then
    dist+=".${PKG_SUBDIST}"
fi

cat <<EOF >/etc/yum.repos.d/edgedb.repo
[edgedb]
name=edgedb
baseurl=https://packages.edgedb.com/rpm/${dist}/
enabled=1
gpgcheck=1
gpgkey=https://packages.edgedb.com/keys/edgedb.asc
EOF

try=1
while [ $try -le 30 ]; do
    yum makecache && yum install --verbose -y edgedb-cli jq && break || true
    try=$(( $try + 1 ))
    echo "Retrying in 10 seconds (try #${try})"
    sleep 10
done

slot=
rpm=
for pack in ${dest}/*.tar; do
    if [ -e "${pack}" ]; then
        slot=$(tar -xOf "${pack}" "build-metadata.json" \
               | jq -r ".version_slot")
        rpm=$(tar -xOf "${pack}" "build-metadata.json" \
              | jq -r ".contents | keys[]" \
              | grep "^edgedb-server.*\\.rpm$")
        if [ -n "${rpm}" ]; then
            break
        fi
    fi
done

if [ -z "${rpm}" ]; then
    echo "${dest} does not seem to contain an edgedb-server .rpm" >&2
    exit 1
fi

if [ -z "${slot}" ]; then
    echo "could not determine version slot from build metadata" >&2
    exit 1
fi

tmpdir=$(mktemp -d)
tar -x -C "${tmpdir}" -f "${pack}" "${rpm}"
yum install -y "${tmpdir}/${rpm}"
rm -rf "${tmpdir}"

if [ "$1" == "bash" ]; then
    echo su edgedb -c \
        "/usr/lib64/edgedb-server-${slot}/bin/python3 \
        -m edb.tools --no-devmode test \
        /usr/share/edgedb-server-${slot}/tests \
        -e cqa_ -e tools_ \
        --verbose"
    exec /bin/bash
else
    if [ -n "${PKG_TEST_JOBS}" ]; then
        dash_j="-j${PKG_TEST_JOBS}"
    else
        dash_j=""
    fi
    su edgedb -c \
        "/usr/lib64/edgedb-server-${slot}/bin/python3 \
        -m edb.tools --no-devmode test \
        /usr/share/edgedb-server-${slot}/tests \
        -e cqa_ -e tools_ \
        --verbose ${dash_j}"
    echo "Success!"
fi
