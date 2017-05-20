#!/bin/sh

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

READLINK="readlink"
if command -v greadlink > /dev/null; then
  READLINK="greadlink" # Prefer greadlink over readlink
fi
ROOT="$(dirname "$($READLINK -f "$(which "$0")")")"
REPO=""
PFX="hg2git"
SFX_MAPPING="mapping"
SFX_MARKS="marks"
SFX_HEADS="heads"
SFX_STATE="state"
GFI_OPTS=""
PYTHON=${PYTHON:-python}

USAGE="[--quiet] [-r <repo>] [--force] [-m <max>] [-s] [--hgtags] [-A <file>] [-B <file>] [-T <file>] [-M <name>] [-o <name>] [--hg-hash] [-e <encoding>]"
LONG_USAGE="Import hg repository <repo> up to either tip or <max>
If <repo> is omitted, use last hg repository as obtained from state file,
GIT_DIR/$PFX-$SFX_STATE by default.

Note: The argument order matters.

Options:
	--quiet   Passed to git-fast-import(1)
	-r <repo> Mercurial repository to import
	--force   Ignore validation errors when converting, and pass --force
	          to git-fast-import(1)
	-m <max>  Maximum revision to import
	-s        Enable parsing Signed-off-by lines
	--hgtags  Enable exporting .hgtags files
	-A <file> Read author map from file
	          (Same as in git-svnimport(1) and git-cvsimport(1))
	-B <file> Read branch map from file
	-T <file> Read tags map from file
	-M <name> Set the default branch name (defaults to 'master')
	-o <name> Use <name> as branch namespace to track upstream (eg 'origin')
	--hg-hash Annotate commits with the hg hash as git notes in the
                  hg namespace.
	-e <encoding> Assume commit and author strings retrieved from 
	              Mercurial are encoded in <encoding>
	--fe <filename_encoding> Assume filenames from Mercurial are encoded 
	                         in <filename_encoding>
"
case "$1" in
    -h|--help)
      echo "usage: $(basename "$0") $USAGE"
      echo ""
      echo "$LONG_USAGE"
      exit 0
esac

IS_BARE=$(git rev-parse --is-bare-repository) \
    || (echo "Could not find git repo" ; exit 1)
if test "z$IS_BARE" != ztrue; then
   # This is not a bare repo, cd to the toplevel
   TOPLEVEL=$(git rev-parse --show-toplevel) \
       || (echo "Could not find git repo toplevel" ; exit 1)
   cd $TOPLEVEL || exit 1
fi
GIT_DIR=$(git rev-parse --git-dir) || (echo "Could not find git repo" ; exit 1)


IGNORECASEWARN=""
IGNORECASE=`git config core.ignoreCase`
if [ "true" = "$IGNORECASE" ]; then
    IGNORECASEWARN="true"
fi;


while case "$#" in 0) break ;; esac
do
  case "$1" in
    -r|--r|--re|--rep|--repo)
      shift
      REPO="$1"
      ;;
    --q|--qu|--qui|--quie|--quiet)
      GFI_OPTS="$GFI_OPTS --quiet"
      ;;
    --force)
      # pass --force to git-fast-import and hg-fast-export.py
      GFI_OPTS="$GFI_OPTS --force"
      IGNORECASEWARN="";
      break
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

if [ ! -z "$IGNORECASEWARN" ]; then
    echo "Error: The option core.ignoreCase is set to true in the git"
    echo "repository. This will produce empty changesets for renames that just"
    echo "change the case of the file name."
    echo "Use --force to skip this check or change the option with"
    echo "git config core.ignoreCase false"
    exit 1
fi;

# Make a backup copy of each state file
for i in $SFX_STATE $SFX_MARKS $SFX_MAPPING $SFX_HEADS ; do
    if [ -f "$GIT_DIR/$PFX-$i" ] ; then
	cp "$GIT_DIR/$PFX-$i" "$GIT_DIR/$PFX-$i~"
    fi
done

# for convenience: get default repo from state file
if [ x"$REPO" = x -a -f "$GIT_DIR/$PFX-$SFX_STATE" ] ; then
  REPO="`grep '^:repo ' "$GIT_DIR/$PFX-$SFX_STATE" | cut -d ' ' -f 2`"
  echo "Using last hg repository \"$REPO\""
fi

if [  -z "$REPO" ]; then
    echo "no repo given, use -r flag"
    exit 1
fi

# make sure we have a marks cache
if [ ! -f "$GIT_DIR/$PFX-$SFX_MARKS" ] ; then
  touch "$GIT_DIR/$PFX-$SFX_MARKS"
fi

# cleanup on exit
trap 'rm -f "$GIT_DIR/$PFX-$SFX_MARKS.old" "$GIT_DIR/$PFX-$SFX_MARKS.tmp"' 0

_err1=
_err2=
exec 3>&1
{ read -r _err1 || :; read -r _err2 || :; } <<-EOT
$(
  exec 4>&3 3>&1 1>&4 4>&-
  {
    _e1=0
    GIT_DIR="$GIT_DIR" $PYTHON "$ROOT/hg-fast-export.py" \
      --repo "$REPO" \
      --marks "$GIT_DIR/$PFX-$SFX_MARKS" \
      --mapping "$GIT_DIR/$PFX-$SFX_MAPPING" \
      --heads "$GIT_DIR/$PFX-$SFX_HEADS" \
      --status "$GIT_DIR/$PFX-$SFX_STATE" \
      "$@" 3>&- || _e1=$?
    echo $_e1 >&3
  } | \
  {
    _e2=0
    git fast-import $GFI_OPTS --export-marks="$GIT_DIR/$PFX-$SFX_MARKS.tmp" 3>&- || _e2=$?
    echo $_e2 >&3
  }
)
EOT
exec 3>&-
[ "$_err1" = 0 -a "$_err2" = 0 ] || exit 1

# move recent marks cache out of the way...
if [ -f "$GIT_DIR/$PFX-$SFX_MARKS" ] ; then
  mv "$GIT_DIR/$PFX-$SFX_MARKS" "$GIT_DIR/$PFX-$SFX_MARKS.old"
else
  touch "$GIT_DIR/$PFX-$SFX_MARKS.old"
fi

# ...to create a new merged one
cat "$GIT_DIR/$PFX-$SFX_MARKS.old" "$GIT_DIR/$PFX-$SFX_MARKS.tmp" \
| uniq > "$GIT_DIR/$PFX-$SFX_MARKS"

# save SHA1s of current heads for incremental imports
# and connectivity (plus sanity checking)
for head in `git branch | sed 's#^..##'` ; do
  id="`git rev-parse refs/heads/$head`"
  echo ":$head $id"
done > "$GIT_DIR/$PFX-$SFX_HEADS"

# check diff with color:
# ( for i in `find . -type f | grep -v '\.git'` ; do diff -u $i $REPO/$i ; done | cdiff ) | less -r
