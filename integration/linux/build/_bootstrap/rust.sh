#!/usr/bin/env bash

set -ex

: ${RUST_VERSION:=1.82.0}

cd /usr/src
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- \
    -y --no-modify-path --profile default \
    --default-toolchain "$RUST_VERSION"

chmod -R a+w "$RUSTUP_HOME" "$CARGO_HOME"

# Make everything use it.
toolchain="$(rustup show active-toolchain | cut -f1 -d' ')"
echo export RUSTUP_TOOLCHAIN="$toolchain" > /etc/profile.d/99-rustup-toolchain-override.sh
