#!/bin/sh

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

ROOT="`dirname $0`"
REPO=""
PFX="hg2git"
SFX_MARKS="marks"
SFX_MAPPING="mapping"
SFX_HEADS="heads"
SFX_STATE="state"
QUIET=""
PYTHON=${PYTHON:-python}

USAGE="[-r <repo>] -R <rev>"
LONG_USAGE="Print SHA1s of latest changes per branch up to <rev> useful
to reset import and restart at <rev>.
If <repo> is omitted, use last hg repository as obtained from state file,
GIT_DIR/$PFX-$SFX_STATE by default.

Options:
	-R	Hg revision to reset to
	-r	Mercurial repository to use
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

GIT_DIR="$GIT_DIR" $PYTHON "$ROOT/hg-reset.py" \
  --repo "$REPO" \
  --marks "$GIT_DIR/$PFX-$SFX_MARKS" \
  --mapping "$GIT_DIR/$PFX-$SFX_MAPPING" \
  --heads "$GIT_DIR/$PFX-$SFX_HEADS" \
  --status "$GIT_DIR/$PFX-$SFX_STATE" \
  "$@"

exit $?
