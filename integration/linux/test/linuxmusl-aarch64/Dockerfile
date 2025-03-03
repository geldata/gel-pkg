#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "mkdockerfile.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

ARG DOCKER_ARCH=
FROM ${DOCKER_ARCH}alpine:3.16 AS builder

ENV CURL_VERSION 7.84.0
ENV JQ_VERSION fa6a2ff6888f27648c703688f1a973588406d92a

RUN apk add --no-cache \
    busybox-static \
    curl \
    coreutils \
    build-base \
    clang \
    openssl-dev \
    nghttp2-dev \
    nghttp2-static \
    libssh2-dev \
    libssh2-static \
    openssl-libs-static \
    zlib-static \
    autoconf \
    automake \
    libtool \
    linux-headers \
    bison \
    flex \
    git

RUN set -ex \
    \
    && mkdir /build \
    && cp /bin/busybox.static /build/busybox \
    && cd /tmp \
	&& curl --proto '=https' --tlsv1.2 -sSfL \
        "https://curl.haxx.se/download/curl-${CURL_VERSION}.tar.gz" \
        -o curl.tar.gz \
	&& mkdir -p /usr/src/curl \
	&& tar -xzC /usr/src/curl --strip-components=1 -f curl.tar.gz \
	&& rm curl.tar.gz \
	&& cd /usr/src/curl \
    && env CC="clang" LDFLAGS="-static -all-static" PKG_CONFIG="pkg-config --static" \
        ./configure \
            --disable-shared --enable-static --disable-ldap \
            --enable-ipv6 --enable-unix-sockets --with-ssl --with-libssh2 \
    && make -j "$(nproc)" \
    && cp src/curl /build/curl \
    && cd /tmp \
	&& mkdir -p /usr/src/jq \
    && git clone --recursive https://github.com/stedolan/jq /usr/src/jq \
    && cd /usr/src/jq \
    && git reset --hard "${JQ_VERSION}" \
    && autoreconf -fi \
    && ./configure --with-oniguruma=builtin --disable-valgrind --enable-all-static \
    && make LDFLAGS=-all-static -j "$(nproc)" \
    && cp jq /build/jq \
    && chmod +x /build/jq \
    && file /build/busybox \
    && file /build/jq \
    && file /build/curl

FROM ${DOCKER_ARCH}golang:1.17-alpine3.15 AS golang
ENV GOSU_VERSION 1.14
ENV CGO_ENABLED 0
RUN set -ex \
	\
    && apk add --no-cache curl \
    && cd /tmp \
	&& curl --proto '=https' --tlsv1.2 -sSfL "https://github.com/tianon/gosu/archive/refs/tags/${GOSU_VERSION}.tar.gz" -o gosu.tar.gz \
	&& mkdir -p /go/src/github.com/tianon/gosu \
	&& tar -xzC /go/src/github.com/tianon/gosu --strip-components=1 -f gosu.tar.gz \
	&& rm gosu.tar.gz \
	&& cd /go/src/github.com/tianon/gosu \
    && go mod download \
    && go mod verify \
    && go build -v -ldflags '-d -s -w' -o /bin/gosu \
    && chmod +x /bin/gosu

FROM ${DOCKER_ARCH}alpine:3.16 AS musl
RUN apk add --no-cache tar \
    && apk info -L musl | tail -n +2 > "/tmp/contents" \
    && tar \
        --directory=/ \
        --create \
        --no-recursion \
        --sparse \
        --no-seek \
        --files-from=/tmp/contents \
        --file=/tmp/musl.tar

FROM scratch
COPY --from=builder /build/busybox /bin/busybox
COPY --from=builder /build/jq /bin/jq
COPY --from=builder /build/curl /bin/curl
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=golang /bin/gosu /bin/gosu
COPY --from=musl /tmp/musl.tar /tmp/musl.tar

RUN ["/bin/busybox", "--install", "-s", "/bin/"]
RUN ["/bin/tar", "xvf", "/tmp/musl.tar", "-C", "/"]
RUN ["/bin/rm", "/tmp/musl.tar"]
RUN /bin/echo -e '#!/bin/sh\n\
\n\
set -ex\n\
\n\
dest="artifacts"\n\
if [ -n "${PKG_PLATFORM}" ]; then\n\
    dest="${dest}/${PKG_PLATFORM}"\n\
fi\n\
if [ -n "${PKG_PLATFORM_LIBC}" ]; then\n\
    dest="${dest}${PKG_PLATFORM_LIBC}"\n\
fi\n\
if [ -n "${PKG_PLATFORM_VERSION}" ]; then\n\
    dest="${dest}-${PKG_PLATFORM_VERSION}"\n\
fi\n\
if [ -n "${PKG_TEST_JOBS}" ]; then\n\
    dash_j="-j${PKG_TEST_JOBS}"\n\
else\n\
    dash_j=""\n\
fi\n\
\n\
machine=$(uname -m)\n\
cliurl="https://packages.edgedb.com/dist/${machine}-unknown-linux-musl/edgedb-cli"\n\
\n\
try=1\n\
while [ $try -le 5 ]; do\n\
    curl --proto '\''=https'\'' --tlsv1.2 -sSfL "$cliurl" -o /bin/edgedb && break || true\n\
    try=$(( $try + 1 ))\n\
    echo "Retrying in 10 seconds (try #${try})"\n\
    sleep 10\n\
done\n\
\n\
chmod +x /bin/edgedb\n\
\n\
tarball=\n\
for pack in ${dest}/*.tar; do\n\
    if [ -e "${pack}" ]; then\n\
        tarball=$(tar -xOf "${pack}" "build-metadata.json" \\\n\
                  | jq -r ".installrefs[]" \\\n\
                  | grep ".tar.gz$")\n\
        if [ -n "${tarball}" ]; then\n\
            break\n\
        fi\n\
    fi\n\
done\n\
\n\
if [ -z "${tarball}" ]; then\n\
    echo "${dest} does not contain a valid build tarball" >&2\n\
    exit 1\n\
fi\n\
\n\
mkdir /edgedb\n\
chmod 1777 /tmp\n\
tar -xOf "${pack}" "${tarball}" | tar -xzf- --strip-components=1 -C "/edgedb/"\n\
touch /etc/group\n\
addgroup edgedb\n\
touch /etc/passwd\n\
adduser -G edgedb -H -D edgedb\n\
\n\
if [ "$1" == "bash" ]; then\n\
    exec /bin/sh\n\
fi\n\
\n\
exec gosu edgedb:edgedb /edgedb/bin/python3 \\\n\
    -m edb.tools --no-devmode test \\\n\
    /edgedb/share/tests \\\n\
    -e cqa_ -e tools_ \\\n\
    --verbose ${dash_j}\n\' >/entrypoint.sh

RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
