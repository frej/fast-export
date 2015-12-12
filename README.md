hg-fast-export.(sh|py) - mercurial to git converter using git-fast-import
=========================================================================

Legal
-----

Most hg-* scripts are licensed under the [MIT license]
(http://www.opensource.org/licenses/mit-license.php) and were written
by Rocco Rutte <pdmef@gmx.net> with hints and help from the git list and
\#mercurial on freenode. hg-reset.py is licensed under GPLv2 since it
copies some code from the mercurial sources.

The current maintainer is Frej Drejhammar <frej.drejhammar@gmail.com>.

Usage
-----

Using hg-fast-export is quite simple for a mercurial repository <repo>:

```
mkdir repo-git # or whatever
cd repo-git
git init
hg-fast-export.sh -r <repo>
```

Please note that hg-fast-export does not automatically check out the
newly imported repository. You probably want to follow up the import
with a `git checkout`-command.

Incremental imports to track hg repos is supported, too.

Using hg-reset it is quite simple within a git repository that is
hg-fast-export'ed from mercurial:

```
hg-reset.sh -R <revision>
```

will give hints on which branches need adjustment for starting over
again.

When a mercurial repository does not use utf-8 for encoding author
strings and commit messages the `-e <encoding>` command line option
can be used to force fast-export to convert incoming meta data from
<encoding> to utf-8. This encoding option is also applied to file names.

In some locales Mercurial uses different encodings for commit messages
and file names. In that case, you can use `--fe <encoding>` command line
option which overrides the -e option for file names.

As mercurial appears to be much less picky about the syntax of the
author information than git, an author mapping file can be given to
hg-fast-export to fix up malformed author strings. The file is
specified using the -A option. The file should contain lines of the
form `FromAuthor=ToAuthor`. The example authors.map below will
translate `User <garbage<user@example.com>` to `User <user@example.com>`.

```
-- Start of authors.map --
User <garbage<user@example.com>=User <user@example.com>
-- End of authors.map --
```

Tag and Branch Naming
---------------------

As Git and Mercurial have differ in what is a valid branch and tag
name the -B and -T options allow a mapping file to be specified to
rename branches and tags (respectively). The syntax of the mapping
file is the same as for the author mapping.

Notes/Limitations
-----------------

hg-fast-export supports multiple branches but only named branches with
exactly one head each. Otherwise commits to the tip of these heads
within the branch will get flattened into merge commits.

As each git-fast-import run creates a new pack file, it may be
required to repack the repository quite often for incremental imports
(especially when importing a small number of changesets per
incremental import).

The way the hg API and remote access protocol is designed it is not
possible to use hg-fast-export on remote repositories
(http/ssh). First clone the repository, then convert it.

Design
------

hg-fast-export.py was designed in a way that doesn't require a 2-pass
mechanism or any prior repository analysis: if just feeds what it
finds into git-fast-import. This also implies that it heavily relies
on strictly linear ordering of changesets from hg, i.e. its
append-only storage model so that changesets hg-fast-export already
saw never get modified.

Submitting Patches
------------------

Please use the issue-tracker at github
https://github.com/frej/fast-export to report bugs and submit
patches.
