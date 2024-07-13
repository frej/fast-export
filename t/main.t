#!/bin/bash
#
# Copyright (c) 2023 Felipe Contreras
#

test_description='Main tests'

. "${SHARNESS_TEST_SRCDIR-$(dirname "$0")/sharness}"/sharness.sh || exit 1

check() {
	echo "$3" > expected &&
	git -C "$1" show -q --format='%s' "$2" > actual &&
	test_cmp expected actual
}

git_clone() {
	(
	git init -q "$2" &&
	cd "$2" &&
	git config core.ignoreCase false &&
	hg-fast-export.sh --repo "../$1"
	)
}

setup() {
	cat > "$HOME"/.hgrc <<-EOF
	[ui]
	username = H G Wells <wells@example.com>
	EOF
}

setup

test_expect_success 'basic' '
	test_when_finished "rm -rf hgrepo gitrepo" &&

	(
	hg init hgrepo &&
	cd hgrepo &&
	echo zero > content &&
	hg add content &&
	hg commit -m zero
	) &&

	git_clone hgrepo gitrepo &&
	check gitrepo @ zero
'

test_expect_success 'merge' '
	test_when_finished "rm -rf hgrepo gitrepo" &&

	(
	hg init hgrepo &&
	cd hgrepo &&
	echo a > content &&
	echo a > file1 &&
	hg add content file1 &&
	hg commit -m "origin" &&

	echo b > content &&
	echo b > file2 &&
	hg add file2 &&
	hg rm file1 &&
	hg commit -m "right" &&

	hg update -r0 &&
	echo c > content &&
	hg commit -m "left" &&

	HGMERGE=true hg merge -r1 &&
	hg commit -m "merge"
	) &&

	git_clone hgrepo gitrepo &&

	cat > expected <<-EOF &&
	left
	c
	tree @:

	content
	file2
	EOF

	(
	cd gitrepo
	git show -q --format='%s' @^ &&
	git show @:content &&
	git show @:
	) > actual &&

	test_cmp expected actual
'

test_done
