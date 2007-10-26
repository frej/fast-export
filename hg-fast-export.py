#!/usr/bin/env python

# Copyright (c) 2007 Rocco Rutte <pdmef@gmx.net>
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

from mercurial import repo,hg,cmdutil,util,ui,revlog,node
from hg2git import setup_repo,fixup_user,get_branch,get_changeset,load_cache,save_cache,get_git_sha1
from tempfile import mkstemp
from optparse import OptionParser
import re
import sys
import os

# silly regex to catch Signed-off-by lines in log message
sob_re=re.compile('^Signed-[Oo]ff-[Bb]y: (.+)$')
# insert 'checkpoint' command after this many commits or none at all if 0
cfg_checkpoint_count=0
# write some progress message every this many file contents written
cfg_export_boundary=1000

def gitmode(x):
  return x and '100755' or '100644'

def wr(msg=''):
  if msg == None:
    msg = ''
  print msg
  #map(lambda x: sys.stderr.write('\t[%s]\n' % x),msg.split('\n'))

def checkpoint(count):
  count=count+1
  if cfg_checkpoint_count>0 and count%cfg_checkpoint_count==0:
    sys.stderr.write("Checkpoint after %d commits\n" % count)
    wr('checkpoint')
    wr()
  return count

def get_parent_mark(parent,marks):
  """Get the mark for some parent.
  If we saw it in the current session, return :%d syntax and
  otherwise the SHA1 from the cache."""
  return marks.get(str(parent),':%d' % (parent+1))

def file_mismatch(f1,f2):
  """See if two revisions of a file are not equal."""
  return node.hex(f1)!=node.hex(f2)

def split_dict(dleft,dright,l=[],c=[],r=[],match=file_mismatch):
  """Loop over our repository and find all changed and missing files."""
  for left in dleft.keys():
    right=dright.get(left,None)
    if right==None:
      # we have the file but our parent hasn't: add to left set
      l.append(left)
    elif match(dleft[left],right):
      # we have it but checksums mismatch: add to center set
      c.append(left)
  for right in dright.keys():
    left=dleft.get(right,None)
    if left==None:
      # if parent has file but we don't: add to right set
      r.append(right)
    # change is already handled when comparing child against parent
  return l,c,r

def get_filechanges(repo,revision,parents,mleft):
  """Given some repository and revision, find all changed/deleted files."""
  l,c,r=[],[],[]
  for p in parents:
    if p<0: continue
    mright=repo.changectx(p).manifest()
    l,c,r=split_dict(mleft,mright,l,c,r)
  l.sort()
  c.sort()
  r.sort()
  return l,c,r

def get_author(logmessage,committer,authors):
  """As git distincts between author and committer of a patch, try to
  extract author by detecting Signed-off-by lines.

  This walks from the end of the log message towards the top skipping
  empty lines. Upon the first non-empty line, it walks all Signed-off-by
  lines upwards to find the first one. For that (if found), it extracts
  authorship information the usual way (authors table, cleaning, etc.)

  If no Signed-off-by line is found, this defaults to the committer.

  This may sound stupid (and it somehow is), but in log messages we
  accidentially may have lines in the middle starting with
  "Signed-off-by: foo" and thus matching our detection regex. Prevent
  that."""

  loglines=logmessage.split('\n')
  i=len(loglines)
  # from tail walk to top skipping empty lines
  while i>=0:
    i-=1
    if len(loglines[i].strip())==0: continue
    break
  if i>=0:
    # walk further upwards to find first sob line, store in 'first'
    first=None
    while i>=0:
      m=sob_re.match(loglines[i])
      if m==None: break
      first=m
      i-=1
    # if the last non-empty line matches our Signed-Off-by regex: extract username
    if first!=None:
      r=fixup_user(first.group(1),authors)
      return r
  return committer

def export_file_contents(ctx,manifest,files):
  count=0
  max=len(files)
  for file in files:
    d=ctx.filectx(file).data()
    wr('M %s inline %s' % (gitmode(manifest.execf(file)),file))
    wr('data %d' % len(d)) # had some trouble with size()
    wr(d)
    count+=1
    if count%cfg_export_boundary==0:
      sys.stderr.write('Exported %d/%d files\n' % (count,max))
  if max>cfg_export_boundary:
    sys.stderr.write('Exported %d/%d files\n' % (count,max))

def is_merge(parents):
  c=0
  for parent in parents:
    if parent>=0:
      c+=1
  return c>1

def sanitize_name(name,what="branch"):
  """Sanitize input roughly according to git-check-ref-format(1)"""

  def dot(name):
    if name[0] == '.': return '_'+name[1:]
    return name

  n=name
  p=re.compile('([[ ^:?*]|\.\.)')
  n=p.sub('_', n)
  if n[-1] == '/': n=n[:-1]+'_'
  n='/'.join(map(dot,n.split('/')))
  p=re.compile('_+')
  n=p.sub('_', n)

  if n!=name:
    sys.stderr.write('Warning: sanitized %s [%s] to [%s]\n' % (what,name,n))
  return n

def export_commit(ui,repo,revision,marks,heads,last,max,count,authors,sob,brmap):
  def get_branchname(name):
    if brmap.has_key(name):
      return brmap[name]
    n=sanitize_name(name)
    brmap[name]=n
    return n

  (revnode,_,user,(time,timezone),files,desc,branch,_)=get_changeset(ui,repo,revision,authors)
  parents=repo.changelog.parentrevs(revision)

  branch=get_branchname(branch)

  wr('commit refs/heads/%s' % branch)
  wr('mark :%d' % (revision+1))
  if sob:
    wr('author %s %d %s' % (get_author(desc,user,authors),time,timezone))
  wr('committer %s %d %s' % (user,time,timezone))
  wr('data %d' % (len(desc)+1)) # wtf?
  wr(desc)
  wr()

  pidx1, pidx2 = 0, 1
  if parents[0] < parents[1]:
    pidx1, pidx2 = 1, 0

  src=heads.get(branch,'')
  link=''
  if src!='':
    # if we have a cached head, this is an incremental import: initialize it
    # and kill reference so we won't init it again
    wr('from %s' % src)
    heads[branch]=''
    sys.stderr.write('%s: Initializing to parent [%s]\n' %
        (branch,src))
    link=src # avoid making a merge commit for incremental import
  elif link=='' and not heads.has_key(branch) and revision>0:
    # newly created branch and not the first one: connect to parent
    tmp=get_parent_mark(parents[0],marks)
    wr('from %s' % tmp)
    sys.stderr.write('%s: Link new branch to parent [%s]\n' %
        (branch,tmp))
    link=tmp # avoid making a merge commit for branch fork
  elif last.get(branch,revision) != parents[pidx1] and parents[pidx1] > 0 and revision > 0:
    pm=get_parent_mark(parents[pidx1],marks)
    sys.stderr.write('%s: Placing commit [r%d] in branch [%s] on top of [r%d]\n' %
        (branch,revision,branch,parents[pidx1]));
    wr('from %s' % pm)

  if parents[pidx2] > 0:
    pm=get_parent_mark(parents[pidx2],marks)
    sys.stderr.write('%s: Merging with parent [%s] from [r%d]\n' %
        (branch,pm,parents[pidx2]))
    wr('merge %s' % pm)

  last[branch]=revision
  heads[branch]=''
  # we need this later to write out tags
  marks[str(revision)]=':%d'%(revision+1)

  ctx=repo.changectx(str(revision))
  man=ctx.manifest()
  added,changed,removed,type=[],[],[],''

  if revision==0:
    # first revision: feed in full manifest
    added=man.keys()
    added.sort()
    type='full'
  elif is_merge(parents):
    # later merge revision: feed in changed manifest
    # for many files comparing checksums is expensive so only do it for
    # merges where we really need it due to hg's revlog logic
    added,changed,removed=get_filechanges(repo,revision,parents,man)
    type='thorough delta'
  else:
    # later non-merge revision: feed in changed manifest
    # if we have exactly one parent, just take the changes from the
    # manifest without expensively comparing checksums
    f=repo.status(repo.lookup(parents[0]),revnode)[:3]
    added,changed,removed=f[1],f[0],f[2]
    type='simple delta'

  sys.stderr.write('%s: Exporting %s revision %d/%d with %d/%d/%d added/changed/removed files\n' %
      (branch,type,revision+1,max,len(added),len(changed),len(removed)))

  map(lambda r: wr('D %s' % r),removed)
  export_file_contents(ctx,man,added)
  export_file_contents(ctx,man,changed)
  wr()

  return checkpoint(count)

def export_tags(ui,repo,marks_cache,start,end,count,authors):
  l=repo.tagslist()
  for tag,node in l:
    tag=sanitize_name(tag,"tag")
    # ignore latest revision
    if tag=='tip': continue
    rev=repo.changelog.rev(node)
    # ignore those tags not in our import range
    if rev<start or rev>=end: continue

    ref=get_parent_mark(rev,marks_cache)
    if ref==None:
      sys.stderr.write('Failed to find reference for creating tag'
          ' %s at r%d\n' % (tag,rev))
      continue
    sys.stderr.write('Exporting tag [%s] at [hg r%d] [git %s]\n' % (tag,rev,ref))
    wr('reset refs/tags/%s' % tag)
    wr('from %s' % ref)
    wr()
    count=checkpoint(count)
  return count

def load_authors(filename):
  cache={}
  if not os.path.exists(filename):
    return cache
  f=open(filename,'r')
  l=0
  lre=re.compile('^([^=]+)[ ]*=[ ]*(.+)$')
  for line in f.readlines():
    l+=1
    m=lre.match(line)
    if m==None:
      sys.stderr.write('Invalid file format in [%s], line %d\n' % (filename,l))
      continue
    # put key:value in cache, key without ^:
    cache[m.group(1).strip()]=m.group(2).strip()
  f.close()
  sys.stderr.write('Loaded %d authors\n' % l)
  return cache

def verify_heads(ui,repo,cache,force):
  branches=repo.branchtags()
  l=[(-repo.changelog.rev(n), n, t) for t, n in branches.items()]
  l.sort()

  # get list of hg's branches to verify, don't take all git has
  for _,_,b in l:
    b=get_branch(b)
    sha1=get_git_sha1(b)
    c=cache.get(b)
    if sha1!=None and c!=None:
      sys.stderr.write('Verifying branch [%s]\n' % b)
    if sha1!=c:
      sys.stderr.write('Error: Branch [%s] modified outside hg-fast-export:'
        '\n%s (repo) != %s (cache)\n' % (b,sha1,c))
      if not force: return False

  # verify that branch has exactly one head
  t={}
  for h in repo.heads():
    (_,_,_,_,_,_,branch,_)=get_changeset(ui,repo,h)
    if t.get(branch,False):
      sys.stderr.write('Error: repository has at least one unnamed head: hg r%s\n' %
          repo.changelog.rev(h))
      if not force: return False
    t[branch]=True

  return True

def mangle_mark(mark):
  return str(int(mark)-1)

def hg2git(repourl,m,marksfile,headsfile,tipfile,authors={},sob=False,force=False):
  _max=int(m)

  marks_cache=load_cache(marksfile,mangle_mark)
  heads_cache=load_cache(headsfile)
  state_cache=load_cache(tipfile)

  ui,repo=setup_repo(repourl)

  if not verify_heads(ui,repo,heads_cache,force):
    return 1

  tip=repo.changelog.count()

  min=int(state_cache.get('tip',0))
  max=_max
  if _max<0 or max>tip:
    max=tip

  c=0
  last={}
  brmap={}
  for rev in range(min,max):
    c=export_commit(ui,repo,rev,marks_cache,heads_cache,last,max,c,authors,sob,brmap)

  c=export_tags(ui,repo,marks_cache,min,max,c,authors)

  sys.stderr.write('Issued %d commands\n' % c)

  state_cache['tip']=max
  state_cache['repo']=repourl
  save_cache(tipfile,state_cache)

  return 0

if __name__=='__main__':
  def bail(parser,opt):
    sys.stderr.write('Error: No %s option given\n' % opt)
    parser.print_help()
    sys.exit(2)

  parser=OptionParser()

  parser.add_option("-m","--max",type="int",dest="max",
      help="Maximum hg revision to import")
  parser.add_option("--marks",dest="marksfile",
      help="File to read git-fast-import's marks from")
  parser.add_option("--heads",dest="headsfile",
      help="File to read last run's git heads from")
  parser.add_option("--status",dest="statusfile",
      help="File to read status from")
  parser.add_option("-r","--repo",dest="repourl",
      help="URL of repo to import")
  parser.add_option("-s",action="store_true",dest="sob",
      default=False,help="Enable parsing Signed-off-by lines")
  parser.add_option("-A","--authors",dest="authorfile",
      help="Read authormap from AUTHORFILE")
  parser.add_option("-f","--force",action="store_true",dest="force",
      default=False,help="Ignore validation errors by force")

  (options,args)=parser.parse_args()

  m=-1
  if options.max!=None: m=options.max

  if options.marksfile==None: bail(parser,'--marks')
  if options.headsfile==None: bail(parser,'--heads')
  if options.statusfile==None: bail(parser,'--status')
  if options.repourl==None: bail(parser,'--repo')

  a={}
  if options.authorfile!=None:
    a=load_authors(options.authorfile)

  sys.exit(hg2git(options.repourl,m,options.marksfile,options.headsfile,
    options.statusfile,authors=a,sob=options.sob,force=options.force))
