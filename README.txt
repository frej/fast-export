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

As there's no real config interface to hg2git.py (the worker script),
checkpointing each 1000 changesets is hard-coded. "checkpointing" means
to issue the "checkpoint" command of git-fast-import which then flushes
the current pack file and starts a new one. This is sufficient for the
initial import.

However, per incremental import with fewer than 1000 changesets (read:
most likely always), a new pack file will be created. Every time. As a
consequence, the git repo should be repacked quite often.
