#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "mkdockerfile.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM ubuntu:oracular
RUN /bin/echo -e '#!/bin/bash\n\
\n\
set -ex\n\
\n\
dest="artifacts"\n\
if [ -n "${PKG_PLATFORM}" ]; then\n\
    dest+="/${PKG_PLATFORM}"\n\
fi\n\
if [ -n "${PKG_PLATFORM_VERSION}" ]; then\n\
    dest+="-${PKG_PLATFORM_VERSION}"\n\
fi\n\
\n\
dist="${PKG_PLATFORM_VERSION}"\n\
\n\
export DEBIAN_FRONTEND="noninteractive"\n\
\n\
apt-get update\n\
apt-get install -y curl gnupg apt-transport-https jq\n\
\n\
mkdir -p /usr/local/share/keyrings\n\
curl --proto '\''=https'\'' --tlsv1.2 -sSf \\\n\
    -o /usr/local/share/keyrings/gel-keyring.gpg \\\n\
    https://packages.geldata.com/keys/gel-keyring.gpg\n\
echo deb [signed-by=/usr/local/share/keyrings/gel-keyring.gpg] \\\n\
    https://packages.geldata.com/apt "${dist}" main \\\n\
    > "/etc/apt/sources.list.d/gel.list"\n\
if [ -n "${PKG_SUBDIST}" ]; then\n\
    echo deb [signed-by=/usr/local/share/keyrings/gel-keyring.gpg] \\\n\
        https://packages.geldata.com/apt "${dist}" "${PKG_SUBDIST}" \\\n\
        > "/etc/apt/sources.list.d/gel-${PKG_SUBDIST}.list"\n\
fi\n\
\n\
try=1\n\
while [ $try -le 30 ]; do\n\
    apt-get update && apt-get install -y gel-cli && break || true\n\
    try=$(( $try + 1 ))\n\
    echo "Retrying in 10 seconds (try #${try})" >&2\n\
    sleep 10\n\
done\n\
\n\
if ! type gel >/dev/null; then\n\
    echo "could not install gel-cli" >&2\n\
    exit $s\n\
fi\n\
\n\
if ! type edgedb; then\n\
    ln -s gel /usr/bin/edgedb\n\
fi\n\
\n\
slot=\n\
deb=\n\
for pack in ${dest}/*.tar; do\n\
    if [ -e "${pack}" ]; then\n\
        slot=$(tar -xOf "${pack}" "build-metadata.json" \\\n\
               | jq -r ".version_slot")\n\
        deb=$(tar -xOf "${pack}" "build-metadata.json" \\\n\
              | jq -r ".contents | keys[]" \\\n\
              | grep "^gel-server.*\\.deb$" \\\n\
              || true)\n\
        if [ -n "${deb}" ]; then\n\
            break\n\
        fi\n\
        deb=$(tar -xOf "${pack}" "build-metadata.json" \\\n\
              | jq -r ".contents | keys[]" \\\n\
              | grep "^edgedb-server.*\\.deb$" \\\n\
              || true)\n\
        if [ -n "${deb}" ]; then\n\
            break\n\
        fi\n\
    fi\n\
done\n\
\n\
if [ -z "${deb}" ]; then\n\
    echo "${dest} does not seem to contain an {edgedb|gel}-server .deb" >&2\n\
    exit 1\n\
fi\n\
\n\
if [ -z "${slot}" ]; then\n\
    echo "could not determine version slot from build metadata" >&2\n\
    exit 1\n\
fi\n\
\n\
machine=$(uname -m)\n\
tmpdir=$(mktemp -d)\n\
tar -x -C "${tmpdir}" -f "${pack}" "${deb}"\n\
apt-get install -y "${tmpdir}/${deb}"\n\
rm -rf "${tmpdir}"\n\
\n\
if [[ $deb == *gel-server* ]]; then\n\
    user="gel"\n\
    server="gel-server-${slot}"\n\
else\n\
    user="edgedb"\n\
    server="edgedb-server-${slot}"\n\
fi\n\
\n\
"$server" --version\n\
\n\
if [ -n "${PKG_TEST_JOBS}" ]; then\n\
    dash_j="-j${PKG_TEST_JOBS}"\n\
else\n\
    dash_j=""\n\
fi\n\
\n\
cmd="/usr/lib/${machine}-linux-gnu/${server}/bin/python3 \\\n\
     -m edb.tools --no-devmode test \\\n\
     /usr/share/${server}/tests \\\n\
     -e cqa_ -e tools_ \\\n\
     --verbose ${dash_j}"\n\
\n\
if [ "$1" == "bash" ]; then\n\
    echo su "$user" -c "$cmd"\n\
    exec /bin/bash\n\
else\n\
    su "$user" -c "$cmd"\n\
    echo "Success!"\n\
fi\n\' >/entrypoint.sh

RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
