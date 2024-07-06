#!/bin/bash
#
# Copyright (c) 2023 Felipe Contreras
# Copyright (c) 2023 Frej Drejhammar
#
# Check that the file_data_filter is called for removed files.
#

test_description='Smoke test'

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
			  --plugin ../../plugins/rename_file_test_plugin \
			  --plugin dos2unix \
			  --plugin shell_filter_file_contents=../../plugins/id
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
	cd hgrepo &&
	echo "a_file" > a.txt &&
	echo "a_file_to_rename" > b.txt &&
	hg add a.txt b.txt &&
	hg commit -d "2023-03-17 01:00Z" -m "r0"
	)
}

commit1() {
	(
	cd hgrepo &&
	hg remove b.txt &&
	hg commit -d "2023-03-17 02:00Z" -m "r1"
	)
}
make-branch() {
    hg branch "$1"
    FILE=$(echo "$1" | sha1sum | cut -d " " -f 1)
    echo "$1" > $FILE
    hg add $FILE
    hg commit -d "2023-03-17 $2:00Z" -m "Added file in branch $1"
}

setup

test_expect_success 'all in one' '
	test_when_finished "rm -rf hgrepo gitrepo" &&

	(
	hg init hgrepo &&
	commit0 &&
	commit1
	) &&
	git_create gitrepo &&
	git_convert hgrepo gitrepo &&
	git -C gitrepo fast-export --all > actual &&

 	test_cmp "$SHARNESS_TEST_DIRECTORY"/file_data_filter.expected actual
'

test_done
