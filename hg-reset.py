#!/usr/bin/env python

# Copyright (c) 2007 Rocco Rutte <pdmef@gmx.net>
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

from mercurial import repo,hg,cmdutil,util,ui,revlog,node
from hg2git import setup_repo,load_cache,get_changeset
from optparse import OptionParser
import sys

def heads(ui,repo,start=None,stop=None,max=None):
  if start is None:
    start = node.nullid
  if stop is None:
    stop = []
  if max is None:
    max = repo.changelog.count()
  stoprevs = dict.fromkeys([repo.changelog.rev(n) for n in stop])
  startrev = repo.changelog.rev(start)
  reachable = {startrev: 1}
  heads = {startrev: 1}

  parentrevs = repo.changelog.parentrevs
  for r in xrange(startrev + 1, max):
    for p in parentrevs(r):
      if p in reachable:
        if r not in stoprevs:
          reachable[r] = 1
        heads[r] = 1
      if p in heads and p not in stoprevs:
        del heads[p]

  return [(repo.changelog.node(r),str(r)) for r in heads]

def get_branches(ui,repo,heads_cache,marks_cache,max):
  h=heads(ui,repo,max=max)
  old=dict.fromkeys(heads_cache)
  r=[]
  for node,rev in h:
    _,_,user,(_,_),_,desc,branch,_=get_changeset(ui,repo,rev)
    del old[branch]
    r.append([branch,marks_cache.get(str(int(rev)+1)),rev,desc.split('\n')[0],user])
  r.sort()
  return old,r

if __name__=='__main__':
  def bail(parser,opt):
    sys.stderr.write('Error: No option %s given\n' % opt)
    parser.print_help()
    sys.exit(2)

  parser=OptionParser()

  parser.add_option("--marks",dest="marksfile",
      help="File to read git-fast-import's marks from")
  parser.add_option("--heads",dest="headsfile",
      help="File to read last run's git heads from")
  parser.add_option("--status",dest="statusfile",
      help="File to read status from")
  parser.add_option("-r","--repo",dest="repourl",
      help="URL of repo to import")
  parser.add_option("-R","--revision",type=int,dest="revision",
      help="Revision to reset to")

  (options,args)=parser.parse_args()

  if options.marksfile==None: bail(parser,'--marks option')
  if options.headsfile==None: bail(parser,'--heads option')
  if options.statusfile==None: bail(parser,'--status option')
  if options.repourl==None: bail(parser,'--repo option')
  if options.revision==None: bail(parser,'-R/--revision')

  heads_cache=load_cache(options.headsfile)
  marks_cache=load_cache(options.marksfile)
  state_cache=load_cache(options.statusfile)

  l=int(state_cache.get('tip',options.revision))
  if options.revision+1>l:
    sys.stderr.write('Revision is beyond last revision imported: %d>%d\n' % (options.revision,l))
    sys.exit(1)

  ui,repo=setup_repo(options.repourl)
  stale,changed=get_branches(ui,repo,heads_cache,marks_cache,options.revision+1)

  print "Possibly stale branches:"
  map(lambda b: sys.stdout.write('\t%s\n' % b),stale.keys())

  print "Reset branches in '%s' to:" % options.headsfile
  map(lambda b: sys.stdout.write('\t:%s %s\n\t\t(r%s: %s: %s)\n' % (b[0],b[1],b[2],b[4],b[3])),changed)

  print "Reset ':tip' in '%s' to '%d'" % (options.statusfile,options.revision)
