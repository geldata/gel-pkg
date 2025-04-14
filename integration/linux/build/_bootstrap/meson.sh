#!/usr/bin/env bash

set -ex

: ${MESON_VERSION:=1.5.2}

mkdir -p /usr/src/meson
cd /usr/src
$WGET -O meson.tar.gz "https://github.com/mesonbuild/meson/releases/download/${MESON_VERSION}/meson-${MESON_VERSION}.tar.gz"
mkdir -p /usr/src/meson
tar -xzC /usr/src/meson --strip-components=1 -f meson.tar.gz
rm meson.tar.gz
printf '#!/usr/bin/env bash\nexec python3 /usr/src/meson/meson.py "${@}"' > /usr/local/bin/meson
chmod +x "/usr/local/bin/meson"
