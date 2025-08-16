#!/bin/bash
#
# Copyright (c) 2023 Felipe Contreras
# Copyright (c) 2023 Frej Drejhammar
# Copyright (c) 2025 Günther Nußmüller
#
# Check that plugin invocation works with largefiles.
# This test uses the echo_file_data_test_plugin to verify that the
# file data is passed correctly, including the largefile status.
#

test_description='Largefiles and plugin test'

. "${SHARNESS_TEST_SRCDIR-$(dirname "$0")/sharness}"/sharness.sh || exit 1


git_create() {
	git init -q "$1" &&
	git -C "$1" config core.ignoreCase false
}

git_convert() {
	(
	cd "$2" &&
	hg-fast-export.sh --repo "../$1" \
			  -s --hgtags -n \
			  --plugin ../../plugins/echo_file_data_test_plugin
	)
}

setup() {
	cat > "$HOME"/.hgrc <<-EOF
	[ui]
	username = Grevious Bodily Harmsworth <gbh@example.com>
	[extensions]
	largefiles =
	EOF
}

commit0() {
	(
	cd hgrepo &&
	echo "a_file" > a.txt &&
	echo "large" > b.txt
	hg add a.txt &&
	hg add --large b.txt &&
	hg commit -d "2023-03-17 01:00Z" -m "r0"
	)
}

setup

test_expect_success 'largefile and plugin' '
	test_when_finished "rm -rf hgrepo gitrepo" &&

	(
	hg init hgrepo &&
	commit0
	) &&
	git_create gitrepo &&
	git_convert hgrepo gitrepo &&
	
	git -C gitrepo fast-export --all > actual &&

 	test_cmp "$SHARNESS_TEST_DIRECTORY"/largefile_plugin.expected actual &&
	test_cmp "$SHARNESS_TEST_DIRECTORY"/largefile_plugin_file_info.expected gitrepo/largefile_info.txt
'

test_done
