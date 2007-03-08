hg2git.(sh|py) - mercurial to git converter using git-fast-import

Legal
=====

The scripts are licensed under the GPL version 2 and were written by
Rocco Rutte <pdmef@gmx.net> with hints and help from the git list and
#mercurial on freenode.

Usage
=====

Using it is quite simple for a mercurial repository <repo>:

  mkdir repo-git # or whatever
  cd repo-git
  git init
  hg2git.sh <repo>

Incremental imports to track hg repos is supported, too.

Notes
=====

As each git-fast-import run creates a new pack file, it may be required
to repack the repository quite often for incremental imports (especially
when importing a small number of changesets per incremental import).
