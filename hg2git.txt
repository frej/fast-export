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

Design
======

hg2git.py was designed in a way that doesn't require a 2-pass mechanism
or any prior repository analysis: if just feeds what it finds into
git-fast-import. This also implies that it heavily relies on strictly
linear ordering of changesets from hg, i.e. its append-only storage
model so that changesets hg2git already saw never get modified.

Import and SHA stability
========================

Currently it's only supported to map one hg repository to one git
repository. However, all forks of a hg repo can be imported into one git
repo each and then merged together (e.g. as different branches in the
final git repo) since the checksums are stable, i.e. one particular hg
changeset always produces the same git SHA1 checksum.

Todo
====

For incremental imports, handling tags needs to be reworked (maybe):
Right now we assume that once a tag is created, it stays forever and
never changes. However,

  1) tags in hg may be removed
  2) tags may change

I'm not yet sure how to handle this and how this interferes with
non-hg-based tags in git.

The same for branches: They may get removed.

For one-time conversions, everything is fine.
