SVN = /usr/local/svn
CFLAGS = -I/usr/include/apr-1.0 -I${SVN}/include/subversion-1 -pipe -O2 -std=c99
LDFLAGS = -L${SVN}/lib -lsvn_repos-1

all: svn-fast-export svn-archive

svn-fast-export: svn-fast-export.c
svn-archive: svn-archive.c
