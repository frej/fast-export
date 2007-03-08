#!/bin/sh

ROOT="`dirname $0`"
REPO=""
MAX="-1"
PFX="hg2git"
SFX_MARKS="marks"
SFX_HEADS="heads"
SFX_STATE="state"
QUIET=""

USAGE="[-m <max>] [--quiet] [<repo>]"
LONG_USAGE="Import hg repository <repo> up to either tip or <max>
If <repo> is omitted, use last hg repository as obtained from state file,
GIT_DIR/$PFX-$SFX_STATE by default."

. git-sh-setup
cd_to_toplevel

while case "$#" in 0) break ;; esac
do
  case "$1" in
    -m)
      shift
      MAX="$1"
      ;;
    --q|--qu|--qui|--quie|--quiet)
      QUIET="--quiet"
      ;;
    -*)
      usage
      ;;
    *)
      break
      ;;
  esac
  shift
done

# for convenience: get default repo from state file
if [ "$#" != 1 -a -f "$GIT_DIR/$PFX-$SFX_STATE" ] ; then
  REPO="`egrep '^:repo ' "$GIT_DIR/$PFX-$SFX_STATE" | cut -d ' ' -f 2`"
  echo "Using last hg repository \"$REPO\""
fi

if [ x"$REPO" = x ] ; then
  if [ "$#" != 1 ] ; then
    usage
    exit 1
  else
    REPO="$1"
  fi
fi

# make sure we have a marks cache
if [ ! -f "$GIT_DIR/$PFX-$SFX_MARKS" ] ; then
  touch "$GIT_DIR/$PFX-$SFX_MARKS"
fi

GIT_DIR="$GIT_DIR" python "$ROOT/hg2git.py" \
  "$REPO" \
  "$MAX" \
  "$GIT_DIR/$PFX-$SFX_MARKS" \
  "$GIT_DIR/$PFX-$SFX_HEADS" \
  "$GIT_DIR/$PFX-$SFX_STATE" \
| git-fast-import $QUIET --export-marks="$GIT_DIR/$PFX-$SFX_MARKS.tmp" \
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
  id="`git-rev-parse $head`"
  echo ":$head $id"
done > "$GIT_DIR/$PFX-$SFX_HEADS"

# check diff with color:
# ( for i in `find . -type f | grep -v '\.git'` ; do diff -u $i $REPO/$i ; done | cdiff ) | less -r
