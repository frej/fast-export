SVN ?= /usr/local/svn
APR_INCLUDES ?= /usr/include/apr-1.0
CFLAGS += -I${APR_INCLUDES} -I${SVN}/include/subversion-1 -pipe -O2 -std=c99
LDFLAGS += -L${SVN}/lib -lsvn_fs-1 -lsvn_repos-1

all: svn-fast-export svn-archive

svn-fast-export: svn-fast-export.c
svn-archive: svn-archive.c

.PHONY: clean

clean:
	rm -rf svn-fast-export svn-archive
