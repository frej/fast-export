hg-fast-export.sh - mercurial to git converter using git-fast-import
=========================================================================

Legal
-----

Most hg-* scripts are licensed under the [MIT license] and were written
by Rocco Rutte <pdmef@gmx.net> with hints and help from the git list and
\#mercurial on freenode. hg-reset.py is licensed under GPLv2 since it
copies some code from the mercurial sources.

The current maintainer is Frej Drejhammar <frej.drejhammar@gmail.com>.

[MIT license]: http://www.opensource.org/licenses/mit-license.php

Support
-------

If you have problems with hg-fast-export or have found a bug, please
create an issue at the [github issue tracker]. Before creating a new
issue, check that your problem has not already been addressed in an
already closed issue. Do not contact the maintainer directly unless
you want to report a security bug. That way the next person having the
same problem can benefit from the time spent solving the problem the
first time.

[github issue tracker]: https://github.com/frej/fast-export/issues

System Requirements
-------------------

This project depends on Python 2.7 or 3.5+, and the Mercurial >= 4.6
package (>= 5.2, if Python 3.5+). If Python is not installed, install
it before proceeding. The Mercurial package can be installed with `pip
install mercurial`.

On windows the bash that comes with "Git for Windows" is known to work
well.

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
sequences understood by the python `unicode_escape` encoding are
supported; strings are otherwise assumed to be UTF8-encoded.
(Versions of fast-export prior to v171002 had a different syntax, the
old syntax can be enabled by the flag `--mappings-are-raw`.)

The example authors.map below will translate `User
<garbage<tab><user@example.com>` to `User <user@example.com>`.

```
-- Start of authors.map --
"User <garbage\t<user@example.com>"="User <user@example.com>"
-- End of authors.map --
```

If you have many Mercurial repositories, Chris J Billington's
[hg-export-tool] allows you to batch convert them.

Tag and Branch Naming
---------------------

As Git and Mercurial have differ in what is a valid branch and tag
name the -B and -T options allow a mapping file to be specified to
rename branches and tags (respectively). The syntax of the mapping
file is the same as for the author mapping.

When the -B and -T flags are used, you will probably want to use the
-n flag to disable the built-in (broken in many cases) sanitizing of
branch/tag names. In the future -n will become the default, but in
order to not break existing incremental conversions, the default
remains with the old behavior.

By default, the `default` mercurial branch is renamed to the `master` 
branch on git. If your mercurial repo contains both `default` and 
`master` branches, you'll need to override this behavior. Use
`-M <newName>` to specify what name to give the `default` branch.

Content filtering
-----------------

hg-fast-export supports filtering the content of exported files.
The filter is supplied to the --filter-contents option. hg-fast-export
runs the filter for each exported file, pipes its content to the filter's
standard input, and uses the filter's standard output in place
of the file's original content. The prototypical use of this feature
is to convert line endings in text files from CRLF to git's preferred LF:

```
-- Start of crlf-filter.sh --
#!/bin/sh
# $1 = pathname of exported file relative to the root of the repo
# $2 = Mercurial's hash of the file
# $3 = "1" if Mercurial reports the file as binary, otherwise "0"

if [ "$3" == "1" ]; then cat; else dos2unix -q; fi
# -q option in call to dos2unix allows to avoid returning an
# error code when handling non-ascii based text files (like UTF-16
# encoded text files)
-- End of crlf-filter.sh --
```


Plugins
-----------------

hg-fast-export supports plugins to manipulate the file data and commit
metadata. The plugins are enabled with the --plugin option. The value
of said option is a plugin name (by folder in the plugins directory),
and optionally, and equals-sign followed by an initialization string.

There is a readme accompanying each of the bundled plugins, with a
description of the usage. To create a new plugin, one must simply
add a new folder under the `plugins` directory, with the name of the
new plugin. Inside, there must be an `__init__.py` file, which contains
at a minimum:

```
def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, args):
        pass
        #Or don't pass, if you want to do some init code here
```

Beyond the boilerplate initialization, you can see the two different
defined filter methods in the [dos2unix](./plugins/dos2unix) and
[branch_name_in_commit](./plugins/branch_name_in_commit) plugins.

```
commit_data = {'branch': branch, 'parents': parents, 'author': author, 'desc': desc, 'revision': revision, 'hg_hash': hg_hash, 'committer': 'committer', 'extra': extra}

def commit_message_filter(self,commit_data):
```
The `commit_message_filter` method is called for each commit, after parsing
from hg, but before outputting to git. The dictionary `commit_data` contains the
above attributes about the commit, and can be modified by any filter. The
values in the dictionary after filters have been run are used to create the git
commit.

```
file_data = {'filename':filename,'file_ctx':file_ctx,'d':d}

def file_data_filter(self,file_data):
```
The `file_data_filter` method is called for each file within each commit.
The dictionary `file_data` contains the above attributes about the file, and
can be modified by any filter. `file_ctx` is the filecontext from the
mercurial python library.  After all filters have been run, the values
are used to add the file to the git commit.

Submodules
----------
See README-SUBMODULES.md for how to convert subrepositories into git
submodules.

Notes/Limitations
-----------------

hg-fast-export supports multiple branches but only named branches with
exactly one head each. Otherwise commits to the tip of these heads
within the branch will get flattened into merge commits. There are a
few options to deal with this:
1. Chris J Billington's [hg-export-tool] can help you to handle branches with
   duplicate heads.
2. Use the [head2branch plugin](./plugins/head2branch) to create a new named
   branch from an unnamed head.
3. You can ignore unnamed heads with the `--ignore-unnamed-heads` option, which
   is appropriate in situations such as the extra heads being close commits
   (abandoned, unmerged changes).

hg-fast-export will ignore any files or directories tracked by mercurial
called `.git`, and will print a warning if it encounters one. Git cannot
track such files or directories. This is not to be confused with submodules,
which are described in README-SUBMODULES.md.

As each git-fast-import run creates a new pack file, it may be
required to repack the repository quite often for incremental imports
(especially when importing a small number of changesets per
incremental import).

The way the hg API and remote access protocol is designed it is not
possible to use hg-fast-export on remote repositories
(http/ssh). First clone the repository, then convert it.

Design
------

hg-fast-export was designed in a way that doesn't require a 2-pass
mechanism or any prior repository analysis: it just feeds what it
finds into git-fast-import. This also implies that it heavily relies
on strictly linear ordering of changesets from hg, i.e. its
append-only storage model so that changesets hg-fast-export already
saw never get modified.

Submitting Patches
------------------

Please create a pull request at
[Github](https://github.com/frej/fast-export/pulls) to submit patches.

When submitting a patch make sure the commits in your pull request:

* Have good commit messages

  Please read Chris Beams' blog post [How to Write a Git Commit
  Message](https://chris.beams.io/posts/git-commit/) on how to write a
  good commit message. Although the article recommends at most 50
  characters for the subject, up to 72 characters are frequently
  accepted for fast-export.

* Adhere to good [commit
hygiene](http://www.ericbmerritt.com/2011/09/21/commit-hygiene-and-git.html)

  When developing a pull request for hg-fast-export, base your work on
  the current `master` branch and rebase your work if it no longer can
  be merged into the current `master` without conflicts. Never merge
  `master` into your development branch, rebase if your work needs
  updates from `master`.

  When a pull request is modified due to review feedback, please
  incorporate the changes into the proper commit. A good reference on
  how to modify history is in the [Pro Git book, Section
  7.6](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History).

Please do not submit a pull request if you are not willing to spend
the time required to address review comments or revise the patch until
it follows the guidelines above. A _take it or leave it_ approach to
contributing wastes both your and the maintainer's time.

Frequent Problems
=================

* git fast-import crashes with: `error: cannot lock ref 'refs/heads/...`

  Branch names in git behave as file names (as they are just files and
  sub-directories under `refs/heads/`, and a path cannot name both a
  file and a directory, i.e. the branches `a` and `a/b` can never
  exist at the same time in a git repo.

  Use a mapping file to rename the troublesome branch names.

* `Branch [<branch-name>] modified outside hg-fast-export` but I have
  not touched the repo!

  If you are running fast-export on a case-preserving but
  case-insensitive file system (Windows and OSX), this will make git
  treat `A` and `a` as the same branch. The solution is to use a
  mapping file to rename branches which only differ in case.

* My mapping file does not seem to work when I rename the branch `git
  fast-import` crashes on!

  fast-export (imperfectly) mangles branch names it thinks won't be
  valid. The mechanism cannot be removed as it would break already
  existing incremental imports that expects it. When fast export
  mangles a name, it prints out a warning of the form `Warning:
  sanitized branch [<unmangled>] to [<mangled>]`. If `git fast-import`
  crashes on `<mangled>`, you need to put `<unmangled>` into the
  mapping file.

* fast-import mangles valid git branch names which I have remapped!

  Use the `-n` flag to hg-fast-export.sh.

* `git status` reports that all files are scheduled for deletion after
  the initial conversion.

  By design fast export does not touch your working directory, so to
  git it looks like you have deleted all files, when in fact they have
  never been checked out. Just do a checkout of the branch you want.

* `Error: repository has at least one unnamed head: hg r<N>`

  By design, hg-fast-export cannot deal with extra heads on a branch.
  There are a few options depending on whether the extra heads are
  in-use/open or normally closed. See [Notes/Limitations](#noteslimitations)
  section for more details.

[hg-export-tool]: https://github.com/chrisjbillington/hg-export-tool
