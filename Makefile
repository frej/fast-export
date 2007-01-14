SVN = /usr/local/svn
CFLAGS = -I/usr/include/apr-1.0 -I${SVN}/include/subversion-1 -pipe -g3 -std=c99
LDFLAGS = -L${SVN}/lib -lsvn_repos-1

svn-fast-export: svn-fast-export.c
