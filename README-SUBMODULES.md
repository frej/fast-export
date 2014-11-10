# How to convert Mercurial Repositories with subrepos

**WARNING: This will only work on Linux/MAC or Windows with cygwin**

## Requirements

Please install all the software requirements listed in the
`requirements-submodules.txt` file by running

```
pip install -r requirements-submodules.txt
```

Ideally, do that within a [virtualenv][venv] to isolate these from other Python
packages you may or may not have already installed on your system.

## Convertion example

First you have to convert the sub repository to git using the directory of sub
repo in main repo for -r parameter of hg-fast-expert.sh.

E.g. if you main repo is in directory `/srv/projects/hg-main-repo` and the sub
directory `subrepo` is a subrepo of your main repository then convert the whole
repo with...

### Sub repository

    cd /srv/projects
    mkdir git-subrepo
    cd git-subrepo
    git init
    /path/to/fast-export/hg-fast-export.sh -r /srv/projects/hg-main-repo/subrepo

    git co HEAD
    git remote add origin git@server/repo
    git push origin --all

### Main repository

    cd /srv/projects
    mkdir git-main-repo
    cd git-main-repo
    git init /path/to/fast-export/hg-fast-export.sh -r /srv/projects/hg-main-repo

    git co HEAD
    git submodule init
    git submodule update


## Sub repository is used in more than one repository

It's not necessary to convert the subrepo every time you want to convert the
main repository. Once you have converted a sub-repository once, copy the
`.hg/link2git` file into the sub-repository of any other repository.

E.g. if you main repo is in directory `/srv/projects/hg-main-repo2` and the sub
directory `subrepo` is a subrepo of your main repository then convert the whole
repo with...

    cp /srv/projects/hg-main-repo/subrepo/.hg/link2git /srv/projects/hg-main-repo2/subrepo/.hg/.

    cd /srv/projects
    mkdir git-main-repo2
    cd git-main-repo2
    git init /path/to/fast-export//hg-fast-export.sh -r /srv/projects/hg-main-repo2

    git co HEAD
    git submodule init
    git submodule update


[venv]: http://docs.python-guide.org/en/latest/dev/virtualenvs/#virtualenv
