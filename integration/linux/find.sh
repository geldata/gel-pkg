#!/usr/bin/env bash
# This script is needed for macOS support.

if [[ $BASH_VERSION =~ ^[3] ]]; then
    echo "Install a newer Bash version with 'brew install bash'" >&2
    exit 1
fi

if which xcode-select >/dev/null 2>&1; then
	# macOS
	FIND="$(which gfind)"
	if [[ ! -e $FIND ]]; then
		echo "Install gnu-find with 'brew install findutils'" >&2
		exit 1
	fi
else
    FIND="$(which find)"
fi

$FIND . -maxdepth 1 -mindepth 1 -type d ! -name "_keys" ! -name "_bootstrap" -printf '%P\n'
