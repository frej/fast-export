#!/bin/sh

# Copyright (c) 2007 Rocco Rutte <pdmef@gmx.net>
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

ROOT="`dirname $0`"
REPO=""
PFX="hg2git"
SFX_MARKS="marks"
SFX_HEADS="heads"
SFX_STATE="state"
QUIET=""
PYTHON=${PYTHON:-python}

USAGE="[--quiet] [-r <repo>] [-m <max>] [-s] [-A <file>]"
LONG_USAGE="Import hg repository <repo> up to either tip or <max>
If <repo> is omitted, use last hg repository as obtained from state file,
GIT_DIR/$PFX-$SFX_STATE by default.

Note: The argument order matters.

Options:
	-m	Maximum revision to import
	--quiet	Passed to git-fast-import(1)
	-s	Enable parsing Signed-off-by lines
	-A	Read author map from file
		(Same as in git-svnimport(1) and git-cvsimport(1))
	-r	Mercurial repository to import
"

. "$(git --exec-path)/git-sh-setup"
cd_to_toplevel

while case "$#" in 0) break ;; esac
do
  case "$1" in
    -r|--r|--re|--rep|--repo)
      shift
      REPO="$1"
      ;;
    --q|--qu|--qui|--quie|--quiet)
      QUIET="--quiet"
      ;;
    -*)
      # pass any other options down to hg2git.py
      break
      ;;
    *)
      break
      ;;
  esac
  shift
done

# for convenience: get default repo from state file
if [ x"$REPO" = x -a -f "$GIT_DIR/$PFX-$SFX_STATE" ] ; then
  REPO="`egrep '^:repo ' "$GIT_DIR/$PFX-$SFX_STATE" | cut -d ' ' -f 2`"
  echo "Using last hg repository \"$REPO\""
fi

# make sure we have a marks cache
if [ ! -f "$GIT_DIR/$PFX-$SFX_MARKS" ] ; then
  touch "$GIT_DIR/$PFX-$SFX_MARKS"
fi

GIT_DIR="$GIT_DIR" $PYTHON "$ROOT/hg-fast-export.py" \
  --repo "$REPO" \
  --marks "$GIT_DIR/$PFX-$SFX_MARKS" \
  --heads "$GIT_DIR/$PFX-$SFX_HEADS" \
  --status "$GIT_DIR/$PFX-$SFX_STATE" \
  "$@" \
| git fast-import $QUIET --export-marks="$GIT_DIR/$PFX-$SFX_MARKS.tmp" \
|| die 'Git fast-import failed'

# move recent marks cache out of the way...
if [ -f "$GIT_DIR/$PFX-$SFX_MARKS" ] ; then
  mv "$GIT_DIR/$PFX-$SFX_MARKS" "$GIT_DIR/$PFX-$SFX_MARKS.old"
else
  touch "$GIT_DIR/$PFX-$SFX_MARKS.old"
fi

# ...to create a new merged one
cat "$GIT_DIR/$PFX-$SFX_MARKS.old" "$GIT_DIR/$PFX-$SFX_MARKS.tmp" \
| uniq > "$GIT_DIR/$PFX-$SFX_MARKS"

# cleanup
rm -rf "$GIT_DIR/$PFX-$SFX_MARKS.old" "$GIT_DIR/$PFX-$SFX_MARKS.tmp"

# save SHA1s of current heads for incremental imports
# and connectivity (plus sanity checking)
for head in `git branch | sed 's#^..##'` ; do
  id="`git rev-parse $head`"
  echo ":$head $id"
done > "$GIT_DIR/$PFX-$SFX_HEADS"

# check diff with color:
# ( for i in `find . -type f | grep -v '\.git'` ; do diff -u $i $REPO/$i ; done | cdiff ) | less -r
