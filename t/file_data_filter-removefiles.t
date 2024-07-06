#!/bin/bash
#
# Copyright (c) 2023 Felipe Contreras
# Copyright (c) 2023 Frej Drejhammar
# Copyright (c) 2024 Stephan Hohe
#
# Check that files that file_data_filter sets to None are removed from repository
#

test_description='Remove files from file_data_filter plugin test'

. "${SHARNESS_TEST_SRCDIR-$(dirname "$0")/sharness}"/sharness.sh || exit 1

check() {
	echo "$3" > expected &&
	git -C "$1" show -q --format='%s' "$2" > actual &&
	test_cmp expected actual
}

git_create() {
	git init -q "$1" &&
	git -C "$1" config core.ignoreCase false
}

git_convert() {
	(
	cd "$2" &&
	hg-fast-export.sh --repo "../$1" \
			  -s --hgtags -n \
			  --plugin ../../plugins/removefiles_test_plugin
	)
}

setup() {
	cat > "$HOME"/.hgrc <<-EOF
	[ui]
	username = Grevious Bodily Harmsworth <gbh@example.com>
	EOF
}

commit0() {
	(
	# Test inital revision with suppressed file
	cd hgrepo &&
	echo "good_a" > good_a.txt &&
	echo "bad_a" > bad_a.txt &&
	hg add good_a.txt bad_a.txt &&
	hg commit -d "2023-03-17 01:00Z" -m "r0"
	)
}

commit1() {
	(
	# Test modifying suppressed file
	# Test adding suppressed file
	cd hgrepo &&
	echo "bad_a_modif" > bad_a.txt &&
	echo "bad_b" > bad_b.txt &&
	hg add bad_b.txt &&
	hg commit -d "2023-03-17 02:00Z" -m "r1"
	)
}

commit2() {
	(
	# Test removing suppressed file
	cd hgrepo &&
	hg rm bad_a.txt &&
	hg commit -d "2023-03-17 03:00Z" -m "r2"
	)
}

setup

test_expect_success 'all in one' '
	test_when_finished "rm -rf hgrepo gitrepo" &&

	(
	hg init hgrepo &&
	commit0 &&
	commit1 &&
	commit2
	) &&
	git_create gitrepo &&
	git_convert hgrepo gitrepo &&
	git -C gitrepo fast-export --all > actual &&

 	test_cmp "$SHARNESS_TEST_DIRECTORY"/file_data_filter-removefiles.expected actual
'

test_done
