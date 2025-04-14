#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "update.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

ARG DOCKER_ARCH=
FROM ${DOCKER_ARCH}centos:7

ENTRYPOINT ["/entrypoint.sh"]

ENV LANG C

ENV PATH /usr/local/bin:/usr/local/cargo/bin:/usr/local/go/bin:$PATH
ENV LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/lib"
ENV RUSTUP_HOME /usr/local/rustup
ENV CARGO_HOME /usr/local/cargo

ENV OPENSSL_VERSION 1.1.1w
ENV PYTHON_LOCAL_OPENSSL 1

# rpm on centos 7 iterates over all fds up to the limit, which is
# extremely slow. Force it to be small with ulimit.
#
# We need to disable the mirrorlist and explicitly set up a
# baseurl. Switch to the archive.kernel.org mirror while we are at it.
RUN ulimit -n 1024 \
	&& echo precedence ::ffff:0:0/96 100 >> /etc/gai.conf \
    && sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-* \
    && sed -i 's|# \?baseurl=http://mirror.centos.org|baseurl=https://archive.kernel.org/centos-vault/|g' /etc/yum.repos.d/CentOS-* \
    && yum update -y \
	&& yum install -y \
		bison \
		bzip2 \
		bzip2-devel \
		ca-certificates \
		curl-devel \
		expat-devel \
		file \
		flex \
		gcc \
		gcc-c++ \
		gdbm-devel \
		gettext \
		libffi-devel \
		libuuid-devel \
		make \
		ncurses-devel \
		openssl-devel \
		patch \
		perl-Data-Dumper \
		perl-Getopt-Long \
		perl-IPC-Cmd \
		readline-devel \
		sqlite-devel \
		sudo \
		tcl \
		unzip \
		wget \
		xz \
		xz-devel \
		zip \
		zlib-devel \
		zstd

# aarch64 images somehow don't have the en_US locale
RUN localedef -f UTF-8 -i en_US en_US.UTF-8

# wget option defaults for bootstrap
ENV WGET="wget --no-verbose --secure-protocol=TLSv1_2 --continue"

RUN mkdir -p '.'; /bin/echo -e '#!/bin/bash\n\
\n\
set -Exeo pipefail\n\
\n\
: "${CARGO_HOME:=$HOME/.cargo}"\n\
: "${PYTHON:=python}"\n\
\n\
mkdir -p ~/.cache/cargo/{git,registry}\n\
mkdir -p "$CARGO_HOME"\n\
rm -rf "${CARGO_HOME}"/{git,registry}\n\
ln -s ~/.cache/cargo/registry "${CARGO_HOME}/registry"\n\
ln -s ~/.cache/cargo/git "${CARGO_HOME}/git"\n\
\n\
extraopts=\n\
if [ -n "${SRC_REF}" ]; then\n\
    extraopts+=" --source-ref=${SRC_REF}"\n\
fi\n\
\n\
if [ -n "${BUILD_IS_RELEASE}" ]; then\n\
    extraopts+=" --release"\n\
fi\n\
\n\
if [ -n "${PKG_REVISION}" ]; then\n\
    if [ "${PKG_REVISION}" = "<current-date>" ]; then\n\
        PKG_REVISION="$(date --utc +%Y%m%d%H%M)"\n\
    fi\n\
    extraopts+=" --pkg-revision=${PKG_REVISION}"\n\
fi\n\
\n\
if [ -n "${PKG_SUBDIST}" ]; then\n\
    extraopts+=" --pkg-subdist=${PKG_SUBDIST}"\n\
fi\n\
\n\
if [ -n "${PKG_TAGS}" ]; then\n\
    extraopts+=" --pkg-tags=${PKG_TAGS}"\n\
fi\n\
\n\
if [ -n "${PKG_COMPRESSION}" ]; then\n\
    extraopts+=" --pkg-compression=${PKG_COMPRESSION}"\n\
fi\n\
\n\
if [ -n "${EXTRA_OPTIMIZATIONS}" ]; then\n\
    extraopts+=" --extra-optimizations"\n\
fi\n\
\n\
if [ -n "${DEBUG_SYMBOLS}" ]; then\n\
    extraopts+=" --build-debug"\n\
fi\n\
\n\
if [ -n "${BUILD_GENERIC}" ]; then\n\
    extraopts+=" --generic"\n\
fi\n\
\n\
if [ -n "${PKG_BUILD_JOBS}" ]; then\n\
    extraopts+=" --jobs=${PKG_BUILD_JOBS}"\n\
fi\n\
\n\
dest="artifacts"\n\
if [ -n "${PKG_PLATFORM}" ]; then\n\
    dest+="/${PKG_PLATFORM}"\n\
fi\n\
if [ -n "${PKG_PLATFORM_LIBC}" ]; then\n\
    dest+="${PKG_PLATFORM_LIBC}"\n\
    extraopts+=" --libc=${PKG_PLATFORM_LIBC}"\n\
fi\n\
if [ -n "${PKG_PLATFORM_VERSION}" ]; then\n\
    dest+="-${PKG_PLATFORM_VERSION}"\n\
fi\n\
if [ -n "${PKG_PLATFORM_ARCH}" ]; then\n\
    extraopts+=" --arch=${PKG_PLATFORM_ARCH}"\n\
fi\n\
\n\
if [ -z "${PACKAGE}" ]; then\n\
    PACKAGE="edgedbpkg.edgedb:EdgeDB"\n\
fi\n\
\n\
if [ -z "${VIRTUAL_ENV}"]; then\n\
    mkdir -p "/var/lib/metapkg/venv"\n\
    ${PYTHON} -m venv "/var/lib/metapkg/venv"\n\
    source "/var/lib/metapkg/venv/bin/activate"\n\
    PYTHON="python"\n\
    ${PYTHON} -m pip install -U pip setuptools wheel\n\
fi\n\
\n\
${PYTHON} -m pip install -U git+https://github.com/geldata/gel-pkg\n\
\n\
if [ -n "${METAPKG_PATH}" ]; then\n\
    p=$(${PYTHON} -c '\''import metapkg;print(metapkg.__path__[0])'\'')\n\
    rm -rf "${p}"\n\
    ln -s "${METAPKG_PATH}" "${p}"\n\
    ls -al "${p}"\n\
fi\n\
\n\
if [ "$1" == "bash" ] || [ "${GET_SHELL}" == "true" ]; then\n\
    echo ${PYTHON} -m metapkg build --dest="${dest}" ${extraopts} "${PACKAGE}"\n\
    exec /bin/bash\n\
else\n\
    ${PYTHON} -m metapkg build -vvv --dest="${dest}" ${extraopts} "${PACKAGE}"\n\
    ls -al "${dest}"\n\
fi\n\' >/entrypoint.sh; chmod +x /entrypoint.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e 'function fetch_keys() {\n\
    for key in "${@}"; do\n\
        gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "$key" \\\n\
        || gpg --batch --keyserver pgp.mit.edu --recv-keys "$key" \\\n\
        || gpg --batch --keyserver keyserver.pgp.com --recv-keys "$key" \\\n\
        || gpg --batch --keyserver keys.openpgp.org --recv-keys "$key"\n\
    done\n\
}\n\' >/_bootstrap/_helpers.sh; chmod +x /_bootstrap/_helpers.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${CMAKE_VERSION:=3.30.2}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
CMAKE_KEYS=(\n\
    CBA23971357C2E6590D9EFD3EC8FEF3A7BFB4EDA\n\
)\n\
fetch_keys "${CMAKE_KEYS[@]}"\n\
\n\
\n\
CMAKE_ARCH=\n\
\n\
if getconf GNU_LIBC_VERSION >&/dev/null 2>&1; then\n\
    case "$(arch)" in\n\
    x86_64)\n\
        CMAKE_ARCH='\''x86_64'\''\n\
        ;;\n\
    arm64)\n\
        CMAKE_ARCH='\''aarch64'\''\n\
        ;;\n\
    aarch64)\n\
        CMAKE_ARCH='\''aarch64'\''\n\
        ;;\n\
    esac\n\
fi\n\
\n\
mkdir -p /usr/src/cmake\n\
cd /usr/src\n\
\n\
_server="https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}"\n\
$WGET "${_server}/cmake-${CMAKE_VERSION}-SHA-256.txt"\n\
$WGET "${_server}/cmake-${CMAKE_VERSION}-SHA-256.txt.asc"\n\
\n\
gpg --batch --verify "cmake-${CMAKE_VERSION}-SHA-256.txt.asc" "cmake-${CMAKE_VERSION}-SHA-256.txt"\n\
rm -f "cmake-${CMAKE_VERSION}-SHA-256.txt.asc"\n\
\n\
if [ -n "${CMAKE_ARCH}" ]; then\n\
	$WGET "${_server}/cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz"\n\
	grep " cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz\\$" "cmake-${CMAKE_VERSION}-SHA-256.txt" | sha256sum -c -\n\
    rm -f "cmake-${CMAKE_VERSION}-SHA-256.txt"\n\
\n\
    tar -xzf "cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz" -C /usr/local --strip-components=1 --no-same-owner\n\
    rm -f "cmake-${CMAKE_VERSION}-linux-${CMAKE_ARCH}.tar.gz"\n\
else\n\
    $WGET "${_server}/cmake-${CMAKE_VERSION}.tar.gz"\n\
    grep " cmake-${CMAKE_VERSION}.tar.gz\\$" "cmake-${CMAKE_VERSION}-SHA-256.txt" | sha256sum -c -\n\
    rm -f "cmake-${CMAKE_VERSION}-SHA-256.txt"\n\
\n\
    tar -xzf "cmake-${CMAKE_VERSION}.tar.gz" -C /usr/src/cmake --strip-components=1 --no-same-owner\n\
    rm -f "cmake-${CMAKE_VERSION}.tar.gz"\n\
\n\
    cd /usr/src/cmake\n\
    ./bootstrap --parallel="$(nproc)"\n\
    make -j "$(nproc)"\n\
    make install\n\
    cd /usr/src\n\
    rm -rf /usr/src/cmake\n\
fi\n\' >/_bootstrap/cmake.sh; chmod +x /_bootstrap/cmake.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${GIT_VERSION:=2.33.1}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
GIT_KEYS=(\n\
    E1F036B1FEE7221FC778ECEFB0B5E88696AFE6CB\n\
)\n\
fetch_keys "${GIT_KEYS[@]}"\n\
\n\
mkdir -p /usr/src/git\n\
cd /usr/src\n\
\n\
$WGET -O git.tar.xz "https://www.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.xz"\n\
$WGET -O git.tar.sign "https://www.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.sign"\n\
\n\
# gpg --batch --verify git.tar.sign git.tar.xz\n\
rm -f git.tar.sign\n\
\n\
tar -xJC /usr/src/git --strip-components=1 -f git.tar.xz\n\
rm -f git.tar.xz\n\
\n\
cd /usr/src/git\n\
make prefix=/usr/local V=1 -j $(nproc) all\n\
make prefix=/usr/local install\n\
cd /usr/src\n\
rm -rf /usr/src/git\n\' >/_bootstrap/git.sh; chmod +x /_bootstrap/git.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${GO_VERSION:=1.23.1}\n\
\n\
case "$(arch)" in\n\
    x86_64)\n\
        GO_ARCH='\''amd64'\''\n\
        ;;\n\
    arm64)\n\
        GO_ARCH='\''arm64'\''\n\
        ;;\n\
    aarch64)\n\
        GO_ARCH='\''arm64'\''\n\
        ;;\n\
    *)\n\
        echo "unsupported architecture"\n\
        exit 1\n\
        ;;\n\
esac\n\
\n\
cd /usr/src\n\
curl --proto '\''=https'\'' --tlsv1.2 -sSfL \\\n\
	"https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz" -o go.tgz\n\
\n\
tar -C /usr/local -xzf go.tgz\n\
rm go.tgz\n\' >/_bootstrap/go.sh; chmod +x /_bootstrap/go.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${GZIP_VERSION:=1.13}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
GZIP_KEYS=(\n\
    155D3FC500C834486D1EEA677FD9FCCB000BEEEE\n\
)\n\
fetch_keys "${GZIP_KEYS[@]}"\n\
\n\
mkdir -p /usr/src/gzip\n\
cd /usr/src\n\
\n\
$WGET -O gzip.tar.gz "https://ftp.gnu.org/gnu/gzip/gzip-${GZIP_VERSION}.tar.gz"\n\
$WGET -O gzip.tar.gz.sign "https://ftp.gnu.org/gnu/gzip/gzip-${GZIP_VERSION}.tar.gz.sig"\n\
\n\
gpg --batch --verify gzip.tar.gz.sign gzip.tar.gz\n\
rm -f gzip.tar.gz.sign\n\
\n\
tar -xzC /usr/src/gzip --strip-components=1 -f gzip.tar.gz\n\
rm -f gzip.tar.gz\n\
\n\
cd /usr/src/gzip\n\
./configure \\\n\
	--bindir=/usr/local/bin/ \\\n\
	--libexecdir=/usr/local/sbin/\n\
make -j $(nproc)\n\
make install\n\
cd /usr/src\n\
rm -rf /usr/src/gzip\n\' >/_bootstrap/gzip.sh; chmod +x /_bootstrap/gzip.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${MESON_VERSION:=1.5.2}\n\
\n\
mkdir -p /usr/src/meson\n\
cd /usr/src\n\
$WGET -O meson.tar.gz "https://github.com/mesonbuild/meson/releases/download/${MESON_VERSION}/meson-${MESON_VERSION}.tar.gz"\n\
mkdir -p /usr/src/meson\n\
tar -xzC /usr/src/meson --strip-components=1 -f meson.tar.gz\n\
rm meson.tar.gz\n\
printf '\''#!/usr/bin/env bash\\nexec python3 /usr/src/meson/meson.py "${@}"'\'' > /usr/local/bin/meson\n\
chmod +x "/usr/local/bin/meson"\n\' >/_bootstrap/meson.sh; chmod +x /_bootstrap/meson.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${NINJA_VERSION:=1.12.1}\n\
\n\
mkdir -p /usr/src/ninja\n\
cd /usr/src\n\
$WGET -O ninja.tar.gz "https://github.com/ninja-build/ninja/archive/refs/tags/v${NINJA_VERSION}.tar.gz"\n\
tar -xzC /usr/src/ninja --strip-components=1 -f ninja.tar.gz\n\
rm ninja.tar.gz\n\
cd /usr/src/ninja\n\
./configure.py --bootstrap --verbose\n\
cp -a ./ninja /usr/local/bin/ninja\n\
cd /usr/src\n\
rm -rf /usr/src/ninja\n\' >/_bootstrap/ninja.sh; chmod +x /_bootstrap/ninja.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${NODE_VERSION:=16.16.0}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
NODE_KEYS=(\n\
    4ED778F539E3634C779C87C6D7062848A1AB005C\n\
    141F07595B7B3FFE74309A937405533BE57C7D57\n\
    94AE36675C464D64BAFA68DD7434390BDBE9B9C5\n\
    74F12602B6F1C4E913FAA37AD3A89613643B6201\n\
    71DCFD284A79C3B38668286BC97EC7A07EDE3FC1\n\
    8FCCA13FEF1D0C2E91008E09770F7A9A5AE15600\n\
    C4F0DFFF4E8C1A8236409D08E73BC641CC11F4C8\n\
    C82FA3AE1CBEDC6BE46B9360C43CEC45C17AB93C\n\
    DD8F2338BAE7501E3DD5AC78C273792F7D83545D\n\
    A48C2BEE680E841632CD4E44F07496B3EB3C1762\n\
    108F52B48DB57BB0CC439B2997B01419BD92F80A\n\
    B9E2F5981AA6E0CD28160D9FF13993A75599653C\n\
)\n\
fetch_keys "${NODE_KEYS[@]}"\n\
\n\
if getconf GNU_LIBC_VERSION 2>&1 >/dev/null; then\n\
    libc="glibc"\n\
elif ldd --version 2>&1 | grep musl >/dev/null; then\n\
    libc="musl"\n\
else\n\
    libc=""\n\
fi\n\
\n\
node_server=\n\
\n\
case "$libc" in\n\
    glibc)\n\
        node_server="https://nodejs.org/dist/v${NODE_VERSION}"\n\
        case "$(arch)" in\n\
            x86_64)\n\
                NODE_ARCH='\''x64'\''\n\
                ;;\n\
            arm64)\n\
                NODE_ARCH='\''arm64'\''\n\
                ;;\n\
            aarch64)\n\
                NODE_ARCH='\''arm64'\''\n\
                ;;\n\
            *)\n\
                echo "unsupported architecture"\n\
                exit 1\n\
                ;;\n\
        esac\n\
        ;;\n\
    musl)\n\
        node_server="https://unofficial-builds.nodejs.org/download/release/v${NODE_VERSION}/"\n\
        case "$(arch)" in\n\
            x86_64)\n\
                NODE_ARCH='\''x64-musl'\''\n\
                ;;\n\
            *)\n\
                echo "unsupported architecture"\n\
                exit 1\n\
                ;;\n\
        esac\n\
        ;;\n\
    *)\n\
        echo "unsupported libc"\n\
        exit 1\n\
        ;;\n\
esac\n\
\n\
$WGET "${node_server}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz"\n\
$WGET "${node_server}/SHASUMS256.txt.asc"\n\
\n\
gpg --batch --decrypt --output SHASUMS256.txt SHASUMS256.txt.asc\n\
grep " node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz\\$" SHASUMS256.txt | sha256sum -c -\n\
tar -xJf "node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" -C /usr/local --strip-components=1 --no-same-owner\n\
rm "node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" SHASUMS256.txt.asc SHASUMS256.txt\n\
\n\
ln -s /usr/local/bin/node /usr/local/bin/nodejs\n\' >/_bootstrap/node.sh; chmod +x /_bootstrap/node.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${OPENSSL_VERSION:=3.3.2}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
OPENSSL_KEYS=(\n\
    BA5473A2B0587B07FB27CF2D216094DFD0CB81EF\n\
    EFC0A467D613CB83C7ED6D30D894E2CE8B3D79F5\n\
)\n\
fetch_keys "${OPENSSL_KEYS[@]}"\n\
\n\
mkdir -p /usr/src/openssl\n\
cd /usr/src\n\
\n\
if [[ $OPENSSL_VERSION == 1.* ]]; then\n\
    $WGET -O openssl.tar.gz "https://github.com/openssl/openssl/releases/download/OpenSSL_${OPENSSL_VERSION//./_}/openssl-${OPENSSL_VERSION}.tar.gz"\n\
    $WGET -O openssl.tar.gz.asc "https://github.com/openssl/openssl/releases/download/OpenSSL_${OPENSSL_VERSION//./_}/openssl-${OPENSSL_VERSION}.tar.gz.asc"\n\
else\n\
    $WGET -O openssl.tar.gz "https://github.com/openssl/openssl/releases/download/openssl-${OPENSSL_VERSION}/openssl-${OPENSSL_VERSION}.tar.gz"\n\
    $WGET -O openssl.tar.gz.asc "https://github.com/openssl/openssl/releases/download/openssl-${OPENSSL_VERSION}/openssl-${OPENSSL_VERSION}.tar.gz.asc"\n\
fi\n\
\n\
gpg --batch --verify openssl.tar.gz.asc openssl.tar.gz\n\
rm -f openssl.tar.gz.asc\n\
\n\
tar -xzC /usr/src/openssl --strip-components=1 -f openssl.tar.gz\n\
rm -f openssl.tar.gz\n\
\n\
cd /usr/src/openssl\n\
\n\
./config \\\n\
    --prefix="/usr/local/openssl" \\\n\
    --openssldir="/usr/local/openssl/etc/ssl" \\\n\
    --libdir="/usr/local/openssl/lib" \\\n\
    "no-ssl3" \\\n\
    "shared"\n\
\n\
make -j "$(nproc)"\n\
make -j "$(nproc)" install_sw\n\
cd /usr/src\n\
rm -rf /usr/src/openssl\n\
\n\
mkdir -p /usr/local/openssl/etc/ssl/\n\
curl -fSSLo /usr/local/openssl/etc/ssl/cert.pem \\\n\
    "https://raw.githubusercontent.com/certifi/python-certifi/refs/heads/master/certifi/cacert.pem"\n\' >/_bootstrap/openssl.sh; chmod +x /_bootstrap/openssl.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${PATCHELF_VERSION:=0.13}\n\
\n\
mkdir -p /usr/src/patchelf\n\
cd /usr/src\n\
\n\
$WGET -O patchelf.tar.bz2 "https://github.com/NixOS/patchelf/releases/download/${PATCHELF_VERSION}/patchelf-${PATCHELF_VERSION}.tar.bz2"\n\
\n\
tar -xjC /usr/src/patchelf --strip-components=1 -f patchelf.tar.bz2\n\
rm -f patchelf.tar.bz2\n\
\n\
cd /usr/src/patchelf\n\
./configure\n\
make -j $(nproc)\n\
make install\n\
cd /usr/src\n\
rm -rf /usr/src/patchelf\n\' >/_bootstrap/patchelf.sh; chmod +x /_bootstrap/patchelf.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${PKGCONF_VERSION:=2.3.0}\n\
\n\
mkdir -p /usr/src/pkgconf\n\
cd /usr/src\n\
$WGET -O pkgconf.tar.xz "https://distfiles.ariadne.space/pkgconf/pkgconf-${PKGCONF_VERSION}.tar.xz"\n\
tar -xJC /usr/src/pkgconf --strip-components=1 -f pkgconf.tar.xz\n\
rm pkgconf.tar.xz\n\
cd /usr/src/pkgconf\n\
./configure\n\
make -j $(nproc)\n\
make install\n\
cd /usr/src\n\
rm -rf /usr/src/pkgconf\n\
ln -sf /usr/local/bin/pkgconf /usr/bin/pkg-config\n\' >/_bootstrap/pkgconf.sh; chmod +x /_bootstrap/pkgconf.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${PYTHON_VERSION:=3.12.9}\n\
: ${PYTHON_PIP_VERSION:=25.0.1}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
PYTHON_KEYS=(\n\
    E3FF2839C048B25C084DEBE9B26995E310250568\n\
    a035c8c19219ba821ecea86b64e628f8d684696d\n\
    7169605F62C751356D054A26A821E680E5FA6305\n\
)\n\
fetch_keys "${PYTHON_KEYS[@]}"\n\
\n\
mkdir -p /usr/src/python\n\
cd /usr/src\n\
\n\
$WGET -O python.tar.xz \\\n\
    "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz"\n\
$WGET -O python.tar.xz.asc \\\n\
    "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz.asc"\n\
\n\
gpg --batch --verify python.tar.xz.asc python.tar.xz\n\
rm -f python.tar.xz.asc\n\
\n\
tar -xJC /usr/src/python --strip-components=1 -f python.tar.xz\n\
rm -f python.tar.xz\n\
\n\
cd /usr/src/python\n\
\n\
config_args=(\n\
    --build="$(gcc -dumpmachine)" \\\n\
    --enable-shared \\\n\
    --with-system-expat \\\n\
    --with-system-ffi \\\n\
    --without-ensurepip \\\n\
)\n\
\n\
if [ -n "$PYTHON_LOCAL_OPENSSL" ]; then\n\
    config_args+=(\n\
        --with-openssl="/usr/local/openssl"\n\
        --with-openssl-rpath="/usr/local/openssl/lib"\n\
    )\n\
fi\n\
\n\
./configure "${config_args[@]}"\n\
make -j "$(nproc)"\n\
make install\n\
\n\
find /usr/local -depth \\\n\
    \\( \\\n\
        \\( -type d -a \\( -name test -o -name tests \\) \\) \\\n\
        -o \\\n\
        \\( -type f -a \\( -name '\''*.pyc'\'' -o -name '\''*.pyo'\'' \\) \\) \\\n\
    \\) -exec rm -rf '\''{}'\'' +\n\
\n\
cd /usr/src\n\
rm -rf /usr/src/python\n\
\n\
cd /usr/local/bin\n\
ln -sf python3 python\n\
ln -sf python3-config python-config\n\
\n\
cd /usr/src\n\
$WGET -O get-pip.py '\''https://bootstrap.pypa.io/get-pip.py'\''\n\
python get-pip.py \\\n\
    --disable-pip-version-check \\\n\
    "pip==$PYTHON_PIP_VERSION"\n\
\n\
find /usr/local -depth \\\n\
    \\( \\\n\
        \\( -type d -a \\( -name test -o -name tests \\) \\) \\\n\
        -o \\\n\
        \\( -type f -a \\( -name '\''*.pyc'\'' -o -name '\''*.pyo'\'' \\) \\) \\\n\
    \\) -exec rm -rf '\''{}'\'' +\n\
\n\
rm -f get-pip.py\n\' >/_bootstrap/python.sh; chmod +x /_bootstrap/python.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${RUST_VERSION:=1.85.0}\n\
\n\
cd /usr/src\n\
curl --proto '\''=https'\'' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- \\\n\
    -y --no-modify-path --profile default \\\n\
    --default-toolchain "$RUST_VERSION"\n\
\n\
chmod -R a+w "$RUSTUP_HOME" "$CARGO_HOME"\n\
\n\
# Make everything use it.\n\
toolchain="$(rustup show active-toolchain | cut -f1 -d'\'' '\'')"\n\
echo export RUSTUP_TOOLCHAIN="$toolchain" > /etc/profile.d/99-rustup-toolchain-override.sh\n\' >/_bootstrap/rust.sh; chmod +x /_bootstrap/rust.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${TAR_VERSION:=1.35}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
TAR_KEYS=(\n\
    7E3792A9D8ACF7D633BC1588ED97E90E62AA7E34\n\
    325F650C4C2B6AD58807327A3602B07F55D0C732\n\
)\n\
fetch_keys "${TAR_KEYS[@]}"\n\
\n\
mkdir -p /usr/src/tar\n\
cd /usr/src\n\
\n\
$WGET -O tar.tar.xz "https://ftp.gnu.org/gnu/tar/tar-${TAR_VERSION}.tar.xz"\n\
$WGET -O tar.tar.xz.sign "https://ftp.gnu.org/gnu/tar/tar-${TAR_VERSION}.tar.xz.sig"\n\
\n\
gpg --batch --verify tar.tar.xz.sign tar.tar.xz\n\
rm -f tar.tar.xz.sign\n\
\n\
tar -xJC /usr/src/tar --strip-components=1 -f tar.tar.xz\n\
rm -f tar.tar.xz\n\
\n\
cd /usr/src/tar\n\
env FORCE_UNSAFE_CONFIGURE=1 ./configure \\\n\
	--bindir=/usr/local/bin/ \\\n\
	--libexecdir=/usr/local/sbin/\n\
make -j $(nproc)\n\
make install\n\
cd /usr/src\n\
rm -rf /usr/src/tar\n\' >/_bootstrap/tar.sh; chmod +x /_bootstrap/tar.sh
RUN mkdir -p '_bootstrap'; /bin/echo -e '#!/usr/bin/env bash\n\
\n\
set -ex\n\
\n\
: ${YARN_VERSION:=1.22.19}\n\
\n\
source "${BASH_SOURCE%/*}/_helpers.sh"\n\
\n\
YARN_KEYS=(\n\
    6A010C5166006599AA17F08146C2130DFD2497F5\n\
)\n\
fetch_keys "${YARN_KEYS[@]}"\n\
\n\
mkdir -p /usr/src/yarn\n\
cd /usr/src\n\
\n\
$WGET -O yarn.tar.gz "https://yarnpkg.com/downloads/${YARN_VERSION}/yarn-v${YARN_VERSION}.tar.gz"\n\
$WGET -O yarn.tar.gz.asc "https://yarnpkg.com/downloads/${YARN_VERSION}/yarn-v${YARN_VERSION}.tar.gz.asc"\n\
\n\
gpg --batch --verify "yarn.tar.gz.asc" "yarn.tar.gz"\n\
rm "yarn.tar.gz.asc"\n\
\n\
tar -xzC /usr/src/yarn --strip-components=1 -f "yarn.tar.gz"\n\
rm -f "yarn.tar.gz"\n\
\n\
ln -s /usr/src/yarn/bin/yarn /usr/local/bin/yarn\n\
ln -s /usr/src/yarn/bin/yarnpkg /usr/local/bin/yarnpkg\n\' >/_bootstrap/yarn.sh; chmod +x /_bootstrap/yarn.sh


RUN set -ex \
	&& /_bootstrap/openssl.sh \
	&& /_bootstrap/python.sh \
	&& /_bootstrap/git.sh \
	&& /_bootstrap/patchelf.sh \
	&& /_bootstrap/tar.sh \
	&& /_bootstrap/pkgconf.sh \
	&& /_bootstrap/rust.sh \
	&& /_bootstrap/node.sh \
	&& /_bootstrap/yarn.sh \
	&& /_bootstrap/go.sh \
	&& /_bootstrap/meson.sh \
	&& /_bootstrap/ninja.sh \
	&& /_bootstrap/cmake.sh
RUN rm -rf /_bootstrap
RUN set -ex && cmake --version && gcc --version && git --version && go version && meson --version && ninja --version && node --version && npm --version && patchelf --version && pkg-config --version && python3 --version && rustc --version && tar --version && yarn --version
