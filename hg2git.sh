#!/bin/sh

USAGE='[-m max] repo'
LONG_USAGE='Import hg repository <repo> up to either tip or <max>'
ROOT="`dirname $0`"
REPO=""
MAX="-1"
PFX="hg2git"
SFX_MARKS="marks"
SFX_HEADS="heads"
SFX_STATE="state"

. git-sh-setup
cd_to_toplevel

while case "$#" in 0) break ;; esac
do
  case "$1" in
    -m)
      shift
      MAX="$1"
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

if [ "$#" != 1 ] ; then
  usage
  exit 1
fi

REPO="$1"

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
| git-fast-import --export-marks="$GIT_DIR/$PFX-$SFX_MARKS.tmp" \
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
for head in `ls "$GIT_DIR/refs/heads"` ; do
  id="`git-rev-parse $head`"
  echo ":$head $id"
done > "$GIT_DIR/$PFX-$SFX_HEADS"

# check diff with color:
# ( for i in `find . -type f | grep -v '\.git'` ; do diff -u $i $REPO/$i ; done | cdiff ) | less -r
