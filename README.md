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

Support
-------

If you have problems with hg-fast-export or have found a bug, please
create an issue at the [github issue tracker]
(https://github.com/frej/fast-export/issues). Before creating a new
issue, check that your problem has not already been addressed in an
already closed issue. Do not contact the maintainer directly unless
you want to report a security bug. That way the next person having the
same problem can benefit from the time spent solving the problem the
first time.

System Requirements
-------------------

This project depends on Python 2.7 and the Mercurial 4.6 package. If
Python is not installed, install it before proceeding. The Mercurial
package can be installed with `pip install mercurial`.

If you're on Windows, run the following commands in git bash (Git for
Windows).

Usage
-----

Using hg-fast-export is quite simple for a mercurial repository <repo>:

```
mkdir repo-git # or whatever
cd repo-git
git init
hg-fast-export.sh -r <local-repo>
git checkout HEAD
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
form `"<key>"="<value>"`. Inside the key and value strings, all escape
sequences understood by the python `string_escape` encoding are
supported. (Versions of fast-export prior to v171002 had a different
syntax, the old syntax can be enabled by the flag
`--mappings-are-raw`.)

The example authors.map below will translate `User
<garbage<tab><user@example.com>` to `User <user@example.com>`.

```
-- Start of authors.map --
"User <garbage\t<user@example.com>"="User <user@example.com>"
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
