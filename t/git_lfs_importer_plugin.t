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

test_expect_success 'git_lfs_importer converts matched binary files to LFS pointers and pointers are properly smudged when checkouting' '
	test_when_finished "rm -rf hgrepo gitrepo lfs-patterns.txt" &&

	# 1. Create source Mercurial repository with binary files
	(
	hg init hgrepo &&
	cd hgrepo &&
	echo "regular text file" > readme.txt &&
	echo "binary payload" > payload.bin &&
	hg add readme.txt payload.bin &&
	hg commit -m "initial commit with binary"
	) &&

	# 2. Prepare destination git repo with LFS setup
	mkdir gitrepo &&
	(
	cd gitrepo &&
	git init -q &&
	git config core.ignoreCase false &&
	git lfs install --local &&

	cat > .gitattributes <<-EOF &&
	*.bin filter=lfs diff=lfs merge=lfs -text
	EOF

	git add .gitattributes &&
	git commit -q -m "Initialize Git LFS configuration"
	) &&

	FIRST_HASH=$(git -C gitrepo rev-parse HEAD) &&

	# 3. Create LFS patterns file
	cat > lfs-patterns.txt <<-EOF &&
	*.bin
	EOF

	# 4. Run hg-fast-export with git_lfs_importer plugin
	(
	cd gitrepo &&
	hg-fast-export.sh \
		-r "../hgrepo" \
		--plugin "git_lfs_importer=../lfs-patterns.txt" \
		--first-commit-hash "$FIRST_HASH" --force
	) &&

	# 5. Verify conversion: payload.bin should be an LFS pointer
	git -C gitrepo show HEAD:payload.bin > lfs_pointer.txt &&
	grep -q "version https://git-lfs.github.com/spec/v1" lfs_pointer.txt &&
	grep -q "oid sha256:" lfs_pointer.txt &&
	grep -q "size" lfs_pointer.txt &&

	# 6. Verify non-matched file is unchanged
	git -C gitrepo show HEAD:readme.txt > readme_check.txt &&
	test "$(cat readme_check.txt)" = "regular text file" &&

	# 7. Make sure the LFS pointer file is unsmeared when checked out
	git -C gitrepo reset --hard HEAD &&
	ls gitrepo &&
	test "$(cat gitrepo/payload.bin)" = "binary payload"
'

test_expect_success 'git_lfs_importer skips files not matching patterns' '
	test_when_finished "rm -rf hgrepo gitrepo lfs-patterns.txt" &&

	# 1. Create source with various files
	(
	hg init hgrepo &&
	cd hgrepo &&
	echo "text" > file.txt &&
	echo "data" > file.dat &&
	echo "iso content" > image.iso &&
	hg add . &&
	hg commit -m "multiple files"
	) &&

	# 2. Prepare git repo with LFS
	mkdir gitrepo &&
	(
	cd gitrepo &&
	git init -q &&
	git config core.ignoreCase false &&
	git lfs install --local &&

	cat > .gitattributes <<-EOF &&
	*.iso filter=lfs diff=lfs merge=lfs -text
	EOF

	git add .gitattributes &&
	git commit -q -m "Initialize Git LFS configuration"
	) &&

	FIRST_HASH=$(git -C gitrepo rev-parse HEAD) &&

	# 3. Only .iso files should be converted
	cat > lfs-patterns.txt <<-EOF &&
	*.iso
	EOF

	(
	cd gitrepo &&
	hg-fast-export.sh \
		-r "../hgrepo" \
		--plugin "git_lfs_importer=../lfs-patterns.txt" \
		--first-commit-hash "$FIRST_HASH" --force
	) &&

	# 4. Verify .iso is LFS pointer
	git -C gitrepo show HEAD:image.iso | grep -q "oid sha256:" &&

	# 5. Verify .txt and .dat are unchanged
	test "$(git -C gitrepo show HEAD:file.txt)" = "text" &&
	test "$(git -C gitrepo show HEAD:file.dat)" = "data"
'

test_expect_success 'git_lfs_importer handles directory patterns' '
	test_when_finished "rm -rf hgrepo gitrepo lfs-patterns.txt" &&

	# 1. Create repo with files in directory
	(
	hg init hgrepo &&
	cd hgrepo &&
	mkdir -p assets/images &&
	echo "logo data" > assets/images/logo.bin &&
	echo "regular" > readme.txt &&
	hg add . &&
	hg commit -m "files in directories"
	) &&

	# 2. Prepare git repo
	mkdir gitrepo &&
	(
	cd gitrepo &&
	git init -q &&
	git config core.ignoreCase false &&
	git lfs install --local &&

	cat > .gitattributes <<-EOF &&
	assets/** filter=lfs diff=lfs merge=lfs -text
	EOF

	git add .gitattributes &&
	git commit -q -m "Initialize Git LFS configuration"
	) &&

	FIRST_HASH=$(git -C gitrepo rev-parse HEAD) &&

	# 3. Match directory pattern
	cat > lfs-patterns.txt <<-EOF &&
	assets/**
	EOF

	(
	cd gitrepo &&
	hg-fast-export.sh \
		-r "../hgrepo" \
		--plugin "git_lfs_importer=../lfs-patterns.txt" \
		--first-commit-hash "$FIRST_HASH" --force
	) &&

	# 4. Verify directory file is converted
	git -C gitrepo show HEAD:assets/images/logo.bin | grep -q "oid sha256:" &&

	# 5. Verify file outside directory is unchanged
	test "$(git -C gitrepo show HEAD:readme.txt)" = "regular"
'

test_done
