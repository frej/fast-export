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

if [ -z "${PYTHON}" ]; then
    # $PYTHON is not set, so we try to find a working python with mercurial:
    for python_cmd in python2 python python3; do
        if command -v $python_cmd > /dev/null; then
            $python_cmd -c 'import mercurial' 2> /dev/null
            if [ $? -eq 0 ]; then
                PYTHON=$python_cmd
                break
            fi
        fi
    done
fi
if [ -z "${PYTHON}" ]; then
    echo "Could not find a python interpreter with the mercurial module available. " \
        "Please use the 'PYTHON'environment variable to specify the interpreter to use."
    exit 1
fi

USAGE="[-r <repo>] -R <rev>"
LONG_USAGE="Print SHA1s of latest changes per branch up to <rev> useful
to reset import and restart at <rev>.
If <repo> is omitted, use last hg repository as obtained from state file,
GIT_DIR/$PFX-$SFX_STATE by default.

Options:
	-R	Hg revision to reset to
	-r	Mercurial repository to use
"

IS_BARE=$(git rev-parse --is-bare-repository) \
    || (echo "Could not find git repo" ; exit 1)
if test "z$IS_BARE" != ztrue; then
   # This is not a bare repo, cd to the toplevel
   TOPLEVEL=$(git rev-parse --show-toplevel) \
       || (echo "Could not find git repo toplevel" ; exit 1)
   cd $TOPLEVEL || exit 1
fi
GIT_DIR=$(git rev-parse --git-dir) || (echo "Could not find git repo" ; exit 1)

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
  REPO="`grep '^:repo ' "$GIT_DIR/$PFX-$SFX_STATE" | cut -d ' ' -f 2`"
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
