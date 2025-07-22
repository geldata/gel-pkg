#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "mkdockerfile.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM debian:buster
# Buster is out of support, point it at archive.debian.org
RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list
RUN /bin/echo -e '#!/bin/bash\n\
\n\
set -ex\n\
\n\
export DEBIAN_FRONTEND=noninteractive\n\
\n\
install_ref="${PKG_INSTALL_REF}"\n\
\n\
if [ -z "${install_ref}" ]; then\n\
    echo ::error "Cannot determine package install ref."\n\
    exit 1\n\
fi\n\
\n\
dist="${PKG_PLATFORM_VERSION}"\n\
components="main"\n\
if [ -n "${PKG_SUBDIST}" ]; then\n\
    components+=" ${PKG_SUBDIST}"\n\
fi\n\
\n\
apt-get update\n\
apt-get install -y curl gnupg apt-transport-https ncurses-bin\n\
curl https://packages.edgedb.com/keys/edgedb.asc | apt-key add -\n\
echo deb https://packages.edgedb.com/apt ${dist} ${components} \\\n\
    >> /etc/apt/sources.list.d/edgedb.list\n\
\n\
if [ "$1" == "bash" ]; then\n\
    exec /bin/bash\n\
fi\n\
\n\
try=1\n\
while [ $try -le 30 ]; do\n\
    apt-get update && apt-get install -y "${install_ref}" && break || true\n\
    try=$(( $try + 1 ))\n\
    echo "Retrying in 30 seconds (try #${try})"\n\
    sleep 30\n\
done\n\
\n\
if [ "${PKG_NAME}" == "gel-cli" ]; then\n\
    gel --help\n\
    gel --version\n\
elif [ "${PKG_NAME}" == "edgedb-cli" ]; then\n\
    edgedb --help\n\
    edgedb --version\n\
elif [ "${PKG_NAME}" == "gel-server" ]; then\n\
    slot="${PKG_VERSION_SLOT}"\n\
\n\
    if [ -z "${slot}" ]; then\n\
        echo ::error "Cannot determine package version slot."\n\
        exit 1\n\
    fi\n\
\n\
    gel-server-${slot} --help\n\
    gel-server-${slot} --version\n\
elif [ "${PKG_NAME}" == "edgedb-server" ]; then\n\
    slot="${PKG_VERSION_SLOT}"\n\
\n\
    if [ -z "${slot}" ]; then\n\
        echo ::error "Cannot determine package version slot."\n\
        exit 1\n\
    fi\n\
\n\
    edgedb-server-${slot} --help\n\
    edgedb-server-${slot} --version\n\
fi\n\' >/entrypoint.sh

RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
