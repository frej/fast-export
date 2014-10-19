# How to convert Mercurial Repositories with subrepos

**WARNING: This will only work on Linux/MAC or Windows with cygwin**

First you have to convert the sub repository to git using directory of sub repo in main repo for -r parameter of
hg-fast-expert.sh.

## Convertion example
e.g. if you main repo is in directory `/srv/projects/hg-main-repo` and the sub directory `subrepo` is a subrepo of your
main repository then convert the whole repo with...

### sub repository

    cd /srv/projects
    mkdir git-subrepo
    cd git-subrepo
    git init
    /path/to/fast-export//hg-fast-export.sh -r /srv/projects/hg-main-repo/subrepo

    git co HEAD
    git remote add origin git@server/repo
    git push origin --all

### main repository

    cd /srv/projects
    mkdir git-main-repo
    cd git-main-repo
    git init /path/to/fast-export//hg-fast-export.sh -r /srv/projects/hg-main-repo

    git co HEAD
    git submodule init
    git submodule update


## Sub repository is used in more than one repository

Its not necessary to convert the subrepo every time convertig a main repository. If you want to use an already converted
subrepo copy only one file from the converted subrepo to the new one.

e.g. if you main repo is in directory `/srv/projects/hg-main-repo2` and the sub directory `subrepo` is a subrepo of your
main repository then convert th whole repo with...

    cp /srv/projects/hg-main-repo/subrepo/.hg/link2git /srv/projects/hg-main-repo2/subrepo/.hg/.

    cd /srv/projects
    mkdir git-main-repo2
    cd git-main-repo2
    git init /path/to/fast-export//hg-fast-export.sh -r /srv/projects/hg-main-repo2

    git co HEAD
    git submodule init
    git submodule update
