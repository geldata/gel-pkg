#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "mkdockerfile.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM ubuntu:oracular

ENV container docker

STOPSIGNAL SIGRTMIN+3

RUN apt-get update && apt-get install -y --no-install-recommends systemd \
	&& rm -rf /var/lib/apt/lists/*

RUN /bin/echo -e '#!/bin/bash\n\
\n\
set -Exeuo pipefail\n\
\n\
env -0 | while IFS="=" read -r -d "" n v; do printf "%s=\\"%s\\"\\n" "$n" "$v"; done >/usr/local/env.txt\n\
\n\
cat >/usr/local/bin/script.sh <<'\''EOF'\''\n\
set -xeuo pipefail\n\
\n\
function finish() {\n\
    /bin/systemctl exit $?\n\
}\n\
\n\
trap finish 0\n\
\n\
export DEBIAN_FRONTEND=noninteractive\n\
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
apt-get update\n\
curl https://packages.edgedb.com/keys/edgedb.asc | apt-key add -\n\
echo deb https://packages.edgedb.com/apt "${dist}" "${PKG_SUBDIST:-main}" \\\n\
    >> /etc/apt/sources.list.d/edgedb.list\n\
\n\
try=1\n\
while [ $try -le 30 ]; do\n\
    apt-get update && apt-get install -y edgedb-cli && break || true\n\
    try=$(( $try + 1 ))\n\
    echo "Retrying in 10 seconds (try #${try})"\n\
    sleep 10\n\
done\n\
\n\
slot=\n\
deb=\n\
for pack in ${dest}/*.tar; do\n\
    if [ -e "${pack}" ]; then\n\
        slot=$(tar -xOf "${pack}" "build-metadata.json" \\\n\
               | jq -r ".version_slot")\n\
        deb=$(tar -xOf "${pack}" "build-metadata.json" \\\n\
              | jq -r ".contents | keys[]" \\\n\
              | grep "^edgedb-server.*\\.deb$")\n\
        if [ -n "${deb}" ]; then\n\
            break\n\
        fi\n\
    fi\n\
done\n\
\n\
if [ -z "${deb}" ]; then\n\
    echo "${dest} does not seem to contain an edgedb-server .deb" >&2\n\
    exit 1\n\
fi\n\
\n\
if [ -z "${slot}" ]; then\n\
    echo "could not determine version slot from build metadata" >&2\n\
    exit 1\n\
fi\n\
\n\
tmpdir=$(mktemp -d)\n\
tar -x -C "${tmpdir}" -f "${pack}" "${deb}"\n\
apt-get install -y "${tmpdir}/${deb}"\n\
rm -rf "${tmpdir}"\n\
\n\
systemctl enable --now edgedb-server-${slot} \\\n\
    || (journalctl -u edgedb-server-${slot} && exit 1)\n\
\n\
ls -al /var/run/edgedb/\n\
\n\
python="/usr/lib/x86_64-linux-gnu/edgedb-server-${slot}/bin/python3"\n\
[[ "$(edgedb --admin -P5656 query '\''SELECT 1 + 3;'\'')" == *4* ]] || exit 1\n\
echo "Success!"\n\
\n\
EOF\n\
\n\
chmod +x /usr/local/bin/script.sh\n\
\n\
cat >/etc/systemd/system/script.service <<EOF\n\
[Unit]\n\
Description=Main Script\n\
After=syslog.target\n\
After=network.target\n\
\n\
[Service]\n\
Type=oneshot\n\
EnvironmentFile=/usr/local/env.txt\n\
ExecStart=/bin/bash /usr/local/bin/script.sh\n\
StandardOutput=journal+console\n\
StandardError=inherit\n\
\n\
[Install]\n\
WantedBy=multi-user.target\n\
EOF\n\
\n\
systemctl enable script.service\n\
exec /lib/systemd/systemd --unit=script.service\n\' >/entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
