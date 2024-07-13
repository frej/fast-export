#!/bin/bash
#
# Copyright (c) 2023 Felipe Contreras
# Copyright (c) 2023 Frej Drejhammar
#
# Smoke test used to sanity test changes to fast-export.
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
			  -B "$SHARNESS_TEST_DIRECTORY"/smoke-test.branchmap \
			  -T "$SHARNESS_TEST_DIRECTORY"/smoke-test.tagsmap
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
	echo "r0-a" > a.txt &&
	echo "r0-b" > b.txt &&
	hg add a.txt b.txt &&
	hg commit -d "2023-03-17 01:00Z" -m "r0" &&
	hg bookmark bm0
	)
}

commit1() {
	(
	cd hgrepo &&
	echo "r1-c" > c.txt &&
	echo "r1-d" > d.txt &&
	hg branch mainline &&
	hg add c.txt d.txt &&
	hg commit -d "2023-03-17 02:00Z" -m "r1" &&
	hg tag -d "2023-03-17 02:10Z" "2019 Spring R2"
	)
}

commit2() {
	(
	cd hgrepo &&
	echo "r2-e" > e.txt &&
	echo "r2-f" > f.txt &&
	hg add e.txt f.txt &&
	hg commit -d "2023-03-17 03:00Z" -m "r2" &&
	hg bookmark bm1
	)
}

commit3() {
	(
	cd hgrepo &&
	echo "r2-e" > g.txt &&
	echo "r2-f" > h.txt &&
	hg add g.txt h.txt &&
	hg commit -d "2023-03-17 04:00Z" -u "badly-formed-user" -m "r3"
	)
}

commit_rest() {
	(
	cd hgrepo &&

	hg branch feature &&
	echo "feature-a" > feature-a.txt &&
	echo "feature-b" > feature-b.txt &&
	hg add feature-a.txt feature-b.txt &&
	hg commit -d "2023-03-17 05:00Z" -m "feature" &&
	hg bookmark bm2 &&

	# Now create strangely named branches
	make-branch "a?" 06 &&
	make-branch "a/" 07 &&
	make-branch "a/b" 08 &&
	make-branch "a/?" 09 &&
	make-branch "?a" 10 &&
	make-branch "a." 11 &&
	make-branch "a.b" 12 &&
	make-branch ".a" 13 &&
	make-branch "/" 14 &&
	make-branch "___3" 15 &&
	make-branch "__2" 16 &&
	make-branch "_1" 17 &&
	make-branch "Feature- 12V Vac \"Venom\"" 18 &&
	make-branch "åäö" 19 &&

	hg bookmark bm-for-the-rest
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
	commit1 &&
	commit2 &&
	commit3 &&
	commit_rest
	) &&
	git_create gitrepo &&
	git_convert hgrepo gitrepo &&
	git -C gitrepo fast-export --all > actual &&

 	test_cmp "$SHARNESS_TEST_DIRECTORY"/smoke-test.expected actual
'

test_expect_success 'incremental' '
	test_when_finished "rm -rf hgrepo gitrepo" &&

	hg init hgrepo &&
	commit0 &&
	git_create gitrepo &&
	git_convert hgrepo gitrepo &&
	commit1 &&
	git_convert hgrepo gitrepo &&
	commit2 &&
	commit3 &&
	git_convert hgrepo gitrepo &&
	commit_rest &&
	git_convert hgrepo gitrepo &&
	git -C gitrepo fast-export --all > actual &&

 	test_cmp "$SHARNESS_TEST_DIRECTORY"/smoke-test.expected actual
'

test_done
