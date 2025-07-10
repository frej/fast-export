#!/bin/bash
#
# Copyright (c) 2023 Felipe Contreras
# Copyright (c) 2025 Günther Nußmüller
#

test_description='Set origin tests'

. "${SHARNESS_TEST_SRCDIR-$(dirname "$0")/sharness}"/sharness.sh || exit 1

check() {
	git -C "$1" fast-export --all > actual
	test_cmp "$SHARNESS_TEST_DIRECTORY"/set_origin.expected actual
}

git_clone() {
	(
	git init -q "$2" &&
	cd "$2" &&
	git config core.ignoreCase false &&
	hg-fast-export.sh --repo "../$1" --origin "$3"
	)
}

setup() {
	cat > "$HOME"/.hgrc <<-EOF
	[ui]
	username = H G Wells <wells@example.com>
	EOF
}

make-branch() {
	hg branch "$1"
	FILE=$(echo "$1" | sha1sum | cut -d " " -f 1)
	echo "$1" > $FILE
	hg add $FILE
	hg commit -d "2023-03-17 $2:00Z" -m "Added file in branch $1"
}

setup

test_expect_success 'basic' '
	test_when_finished "rm -rf hgrepo gitrepo" &&

	(
	hg init hgrepo &&
	cd hgrepo &&
	echo zero > content &&
	hg add content &&
	hg commit -m zero -d "2023-03-17 01:00Z" &&
	make-branch branch1 02 &&
	make-branch branch2 03
	) &&

	git_clone hgrepo gitrepo prefix &&
	check gitrepo
'

test_done
