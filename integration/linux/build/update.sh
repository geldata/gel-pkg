#!/usr/bin/env bash
#
# Copyright (c) 2014-2015 Docker, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -Eeuo pipefail
shopt -s nullglob

if which xcode-select >/dev/null 2>&1; then
	# macOS
	SED="$(which gsed)"
	JQ="$(which jq)"
	READLINK="$(which greadlink)"
	AWK="$(which gawk)"
	if [[ ! -e $SED ]]; then
		echo "Install gnu-sed with 'brew install gnu-sed'"
		exit 1
	fi
	if [[ ! -e $JQ ]]; then
		echo "Install jq with 'brew install jq'"
		exit 1
	fi
	if [[ ! -e $READLINK ]]; then
		echo "Install gnu-readlink with 'brew install coreutils'"
		exit 1
	fi
	if [[ ! -e $AWK ]]; then
		echo "Install gnu-awk with 'brew install gawk'"
		exit 1
	fi
else
	SED="$(which sed)"
	JQ="$(which jq)"
	READLINK="$(which readlink)"
	AWK="$(which awk)"
fi


cd "$(dirname "$($READLINK -f "$BASH_SOURCE")")"

tools=(
	"cmake"
	"gcc"
	"git"
	"go"
	"meson"
	"ninja"
	"node"
	"npm"
	"patchelf"
	"pkg-config"
	"python3"
	"rustc"
	"tar"
	"yarn"
)

generated_warning() {
	cat <<-EOH
		#
		# NOTE: THIS DOCKERFILE IS GENERATED VIA "update.sh"
		#
		# PLEASE DO NOT EDIT IT DIRECTLY.
		#

	EOH
}

scripts=$(mktemp /tmp/dockerfile-update.XXXXXX)
function tmpfile_cleanup {
  rm -f "$scripts" >&2
}
trap tmpfile_cleanup EXIT

embed_script() {
	local source_file=$1
	local target=$2
	local source_dir=$(dirname "$source_file")
	local source_name="${source_file%.*}"
	source_name="${source_name^^}"
	local placeholder="%%${source_name//\//_}%%"
	local source
	local source_cmd

	source="$(cat "$source_file" \
					| $SED -r -e 's/\\/\\\\/g' \
					| $SED -r -e 's/\x27/\x27\\\x27\x27/g' \
					| $SED -r -e 's/^(.*)$/\1\\n\\/g' \
					| $SED -r -e 's/&/\\&/g')"
	embed_cmd="RUN mkdir -p '${source_dir}'; /bin/echo -e '${source}' >/${source_file}; chmod +x /${source_file}"
	echo "${embed_cmd}" >>"${scripts}"
}

template="${1}"
target="${2}"
variant="$(dirname ${target})"
variant="${variant#*-}"

{ generated_warning; cat "${template}"; } > "${target}"

$SED -ri \
	-e '/%%IF VARIANT=.*'"${variant}"'.*%%/,/%%ENDIF%%/ { /%%IF VARIANT=/d; /%%ENDIF%%/d; }' \
	-e '/%%IFNOT VARIANT=.*'"${variant}"'.*%%/,/%%ENDIF%%/d' \
	-e '/%%IF VARIANT=.*%%/,/%%ENDIF%%/d' \
	-e '/%%IFNOT VARIANT=.*%%/,/%%ENDIF%%/ { /%%IFNOT VARIANT=/d; /%%ENDIF%%/d; }' \
	-e 's!^(FROM (\$\{DOCKER_ARCH\}?buildpack-deps)):%%PLACEHOLDER%%!\1:'"${variant}"'!' \
	-e 's!^(FROM (\$\{DOCKER_ARCH\}?\w+)):%%PLACEHOLDER%%!\1:'"${variant}"'!'\
	"${target}"

embed_script entrypoint.sh "$target"

for bootstrap in $(ls _bootstrap/*.sh | sort); do
	embed_script "$bootstrap" "$target"
done

$AWK -i inplace '@load "readfile"; BEGIN{l = readfile("'"${scripts}"'")}/%%SCRIPTS%%/{gsub("%%SCRIPTS%%", l)}1' "${target}"

echo "RUN rm -rf /_bootstrap" >> "$target"

check="RUN set -ex"
for tool in "${tools[@]}"; do
	case "$tool" in
		go) cmd="go version" ;;
		*) cmd="${tool} --version" ;;
	esac

	check+=" && ${cmd}"
done

echo "$check" >> "$target"
