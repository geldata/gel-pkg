#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s nullglob

if which xcode-select >/dev/null 2>&1; then
	# macOS
	SED="$(which gsed)"
	AWK="$(which gawk)"
	if [[ ! -e $SED ]]; then
		echo "Install gnu-sed with 'brew install gnu-sed'"
		exit 1
	fi
	if [[ ! -e $AWK ]]; then
		echo "Install gnu-awk with 'brew install gawk'"
		exit 1
	fi
else
	SED="$(which sed)"
	AWK="$(which awk)"
fi


generated_warning() {
	cat <<-EOH
		#
		# NOTE: THIS DOCKERFILE IS GENERATED VIA "mkdockerfile.sh"
		#
		# PLEASE DO NOT EDIT IT DIRECTLY.
		#

	EOH
}

template="${1}"
target="${2}"
variant="$(dirname ${target})"
platform="${variant%%-*}"

{ generated_warning; cat "$template"; } > "${target}"

$SED -ri \
	-e '/%%IF VARIANT=.*'"${variant}"'.*%%/,/%%ENDIF%%/ { /%%IF VARIANT=/d; /%%ENDIF%%/d; }' \
	-e '/%%IFNOT VARIANT=.*'"${variant}"'.*%%/,/%%ENDIF%%/d' \
	-e '/%%IF VARIANT=.*%%/,/%%ENDIF%%/d' \
	-e '/%%IFNOT VARIANT=.*%%/,/%%ENDIF%%/ { /%%IFNOT VARIANT=/d; /%%ENDIF%%/d; }' \
	-e 's!^(FROM (\w+)):%%PLACEHOLDER%%!\1:'"${variant#*-}"'!'\
	"${target}"

entrypoint="$(cat entrypoint-${platform}.sh \
				| $SED -r -e 's/\\/\\\\/g' \
				| $SED -r -e 's/\x27/\x27\\\x27\x27/g' \
				| $SED -r -e 's/^(.*)$/\1\\n\\/g' \
				| $SED -r -e 's/&/\\&/g')"
entrypoint_cmd="RUN /bin/echo -e '${entrypoint}' >/entrypoint.sh"

tmp=$(mktemp /tmp/mkdockerfile.XXXXXX)
echo "${entrypoint_cmd}" >"${tmp}"
$AWK -i inplace '@load "readfile"; BEGIN{l = readfile("'"${tmp}"'")}/%%WRITE_ENTRYPOINT%%/{gsub("%%WRITE_ENTRYPOINT%%", l)}1' "${target}"
rm "${tmp}"
