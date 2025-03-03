#!/bin/bash

set -eEx

dest="artifacts"
if [ -n "${PKG_PLATFORM}" ]; then
    dest="${dest}/${PKG_PLATFORM}"
fi
if [ -n "${PKG_PLATFORM_VERSION}" ]; then
    dest="${dest}-${PKG_PLATFORM_VERSION}"
fi
if [ -n "${PKG_TEST_JOBS}" ]; then
    dash_j="-j${PKG_TEST_JOBS}"
else
    dash_j=""
fi

cliurl="https://packages.edgedb.com/dist/${PKG_PLATFORM_VERSION}-apple-darwin"

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

workdir=$(mktemp -d)

function finally {
  rm -rf "$workdir"
}
trap finally EXIT ERR

mkdir "${workdir}/bin"
curl --proto '=https' --tlsv1.2 -sSfL  -o "${workdir}/bin/edgedb" \
    "${cliurl}/edgedb-cli"
chmod +x "${workdir}/bin/edgedb"

gtar -xOf "${pack}" "${tarball}" | gtar -xzf- --strip-components=1 -C "$workdir"

if [ "$1" == "bash" ]; then
    cd "$workdir"
    exec /bin/bash
fi

export PATH="${workdir}/bin/:${PATH}"

test_dir="${workdir}/share/tests"
if [ -n "${PKG_TEST_FILES}" ]; then
    # ${PKG_TEST_FILES} is specificaly used outside the quote so that it
    # can contain a glob.
    file_arg=$(cd "$test_dir" && realpath $PKG_TEST_FILES)
else
    file_arg="$test_dir"
fi

"${workdir}/bin/python3" \
    -m edb.tools --no-devmode test \
    ${file_arg} \
    -e cqa_ -e tools_ \
    --verbose ${dash_j}
