#!/bin/bash
#
# Copyright (c) 2025
#

test_description='git_lfs_importer plugin integration tests'

. "${SHARNESS_TEST_SRCDIR-$(dirname "$0")/sharness}"/sharness.sh || exit 1

setup() {
	cat > "$HOME"/.hgrc <<-EOF
	[ui]
	username = Test User <test@example.com>
	EOF

    # Git config for the destination repo commits
    git config --global user.email "test@example.com"
    git config --global user.name "Test User"
}

setup

test_expect_success 'Mercurial history is imported over the provided commit' '
	test_when_finished "rm -rf hgrepo gitrepo lfs-patterns.txt" &&

	# 1. Create source Mercurial repository with binary files
	(
	hg init hgrepo &&
	cd hgrepo &&
	echo "regular text file" > readme.txt &&
	hg add readme.txt &&
	hg commit -m "initial commit"
	) &&

	# 2. Prepare destination git repo with LFS setup
	mkdir gitrepo &&
	(
	cd gitrepo &&
	git init -q &&
	git config core.ignoreCase false &&
	git lfs install --local &&
	git switch --create master &&

	cat > .gitattributes <<-EOF &&
	* -text
	EOF

	git add .gitattributes &&
	git commit -q -m "Initialize Git configuration"
	) &&

	FIRST_HASH=$(git -C gitrepo rev-parse HEAD) &&

	# 3. Run hg-fast-export
	(
	cd gitrepo &&
	hg-fast-export.sh \
		-r "../hgrepo" \
		--first-commit-hash "$FIRST_HASH" --force \
		-M master
	) &&

	# 4. Verify git file is still present
	git -C gitrepo show HEAD:.gitattributes > gitattributes_check.txt &&
	test "$(cat gitattributes_check.txt)" = "* -text" &&

	# 5. Verify hg file is imported
	git -C gitrepo show HEAD:readme.txt > readme_check.txt &&
	test "$(cat readme_check.txt)" = "regular text file"
'

test_expect_success 'Mercurial history has priority over git' '
	test_when_finished "rm -rf hgrepo gitrepo lfs-patterns.txt" &&

	# 1. Create source Mercurial repository with binary files
	(
	hg init hgrepo &&
	cd hgrepo &&
	echo "hg readme file" > readme.txt &&
	hg add readme.txt &&
	hg commit -m "initial commit"
	) &&

	# 2. Prepare destination git repo with LFS setup
	mkdir gitrepo &&
	(
	cd gitrepo &&
	git init -q &&
	git config core.ignoreCase false &&
	git lfs install --local &&
	git switch --create master &&

	cat > readme.txt <<-EOF &&
	git readme file
	EOF

	git add readme.txt &&
	git commit -q -m "Initialize Git readme file"
	) &&

	FIRST_HASH=$(git -C gitrepo rev-parse HEAD) &&

	# 3. Run hg-fast-export
	(
	cd gitrepo &&
	hg-fast-export.sh \
		-r "../hgrepo" \
		--first-commit-hash "$FIRST_HASH" --force \
		-M master
	) &&

	# 5. Verify hg file is imported
	git -C gitrepo show HEAD:readme.txt > readme_check.txt &&
	test "$(cat readme_check.txt)" = "hg readme file"
'

test_done
