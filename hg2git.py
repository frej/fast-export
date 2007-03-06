#!/usr/bin/env python

# Copyright (c) 2007 Rocco Rutte <pdmef@gmx.net>
# License: GPLv2

"""hg2git.py - A mercurial-to-git filter for git-fast-import(1)
Usage: hg2git.py <hg repo url> <marks file> <heads file> <tip file>
"""

from mercurial import repo,hg,cmdutil,util,ui,revlog
from tempfile import mkstemp
import re
import sys
import os

# silly regex to see if user field has email address
user_re=re.compile('[^<]+ <[^>]+>$')
# git branch for hg's default 'HEAD' branch
cfg_master='master'
# insert 'checkpoint' command after this many commits
cfg_checkpoint_count=1000

def usage(ret):
  sys.stderr.write(__doc__)
  return ret

def setup_repo(url):
  myui=ui.ui()
  return myui,hg.repository(myui,url)

def get_changeset(ui,repo,revision):
  def get_branch(name):
    if name=='HEAD':
      name=cfg_master
    return name
  def fixup_user(user):
    if user_re.match(user)==None:
      if '@' not in user:
        return user+' <none@none>'
      return user+' <'+user+'>'
    return user
  node=repo.lookup(revision)
  (manifest,user,(time,timezone),files,desc,extra)=repo.changelog.read(node)
  tz="%+03d%02d" % (-timezone / 3600, ((-timezone % 3600) / 60))
  branch=get_branch(extra.get('branch','master'))
  return (manifest,fixup_user(user),(time,tz),files,desc,branch,extra)

def gitmode(x):
  return x and '100755' or '100644'

def wr(msg=''):
  print msg
  #map(lambda x: sys.stderr.write('\t[%s]\n' % x),msg.split('\n'))

def checkpoint(count):
  count=count+1
  if count%cfg_checkpoint_count==0:
    sys.stderr.write("Checkpoint after %d commits\n" % count)
    wr('checkpoint')
    wr()
  return count

def get_parent_mark(parent,marks):
  p=marks.get(str(parent),None)
  if p==None:
    # if we didn't see parent previously, assume we saw it in this run
    p=':%d' % (parent+1)
  return p

def export_commit(ui,repo,revision,marks,heads,last,max,count):
  sys.stderr.write('Exporting revision %d (tip %d) as [:%d]\n' % (revision,max,revision+1))

  (_,user,(time,timezone),files,desc,branch,_)=get_changeset(ui,repo,revision)
  parents=repo.changelog.parentrevs(revision)

  # we need this later to write out tags
  marks[str(revision)]=':%d'%(revision+1)

  wr('commit refs/heads/%s' % branch)
  wr('mark :%d' % (revision+1))
  wr('committer %s %d %s' % (user,time,timezone))
  wr('data %d' % (len(desc)+1)) # wtf?
  wr(desc)
  wr()

  src=heads.get(branch,'')
  link=''
  if src!='':
    # if we have a cached head, this is an incremental import: initialize it
    # and kill reference so we won't init it again
    wr('from %s' % src)
    heads[branch]=''
    sys.stderr.write('Initializing branch [%s] to parent [%s]\n' %
        (branch,src))
    link=src # avoid making a merge commit for incremental import
  elif not heads.has_key(branch) and revision>0:
    # newly created branch and not the first one: connect to parent
    tmp=get_parent_mark(parents[0],marks)
    wr('from %s' % tmp)
    sys.stderr.write('Link new branch [%s] to parent [%s]\n' %
        (branch,tmp))
    link=tmp # avoid making a merge commit for branch fork

  if parents:
    l=last.get(branch,revision)
    for p in parents:
      # 1) as this commit implicitely is the child of the most recent
      #    commit of this branch, ignore this parent
      # 2) ignore nonexistent parents
      # 3) merge otherwise
      if p==l or p==revision or p<0:
        continue
      tmp=get_parent_mark(p,marks)
      # if we fork off a branch, don't merge via 'merge' as we have
      # 'from' already above
      if tmp==link:
        continue
      sys.stderr.write('Merging branch [%s] with parent [%s] from [r%d]\n' %
          (branch,tmp,p))
      wr('merge %s' % tmp)

  last[branch]=revision
  heads[branch]=''

  # just wipe the branch clean, all full manifest contents
  wr('deleteall')

  ctx=repo.changectx(str(revision))
  man=ctx.manifest()

  #for f in man.keys():
  #  fctx=ctx.filectx(f)
  #  d=fctx.data()
  #  wr('M %s inline %s' % (gitmode(man.execf(f)),f))
  #  wr('data %d' % len(d)) # had some trouble with size()
  #  wr(d)

  for fctx in ctx.filectxs():
    f=fctx.path()
    d=fctx.data()
    wr('M %s inline %s' % (gitmode(man.execf(f)),f))
    wr('data %d' % len(d)) # had some trouble with size()
    wr(d)

  wr()
  return checkpoint(count)

def export_tags(ui,repo,cache,count):
  l=repo.tagslist()
  for tag,node in l:
    if tag=='tip':
      continue
    rev=repo.changelog.rev(node)
    ref=cache.get(str(rev),None)
    if ref==None:
      sys.stderr.write('Failed to find reference for creating tag'
          ' %s at r%d\n' % (tag,rev))
      continue
    (_,user,(time,timezone),_,desc,branch,_)=get_changeset(ui,repo,rev)
    sys.stderr.write('Exporting tag [%s] at [hg r%d] [git %s]\n' % (tag,rev,ref))
    wr('tag %s' % tag)
    wr('from %s' % ref)
    wr('tagger %s %d %s' % (user,time,timezone))
    msg='hg2git created tag %s for hg revision %d on branch %s on (summary):\n\t%s' % (tag,
        rev,branch,desc.split('\n')[0])
    wr('data %d' % (len(msg)+1))
    wr(msg)
    wr()
    count=checkpoint(count)
  return count

def load_cache(filename):
  cache={}
  if not os.path.exists(filename):
    return cache
  f=open(filename,'r')
  l=0
  for line in f.readlines():
    l+=1
    fields=line.split(' ')
    if fields==None or not len(fields)==2 or fields[0][0]!=':':
      sys.stderr.write('Invalid file format in [%s], line %d\n' % (filename,l))
      continue
    # put key:value in cache, key without ^:
    cache[fields[0][1:]]=fields[1].split('\n')[0]
  f.close()
  return cache

def save_cache(filename,cache):
  f=open(filename,'w+')
  map(lambda x: f.write(':%s %s\n' % (str(x),str(cache.get(x)))),cache.keys())
  f.close()

def verify_heads(ui,repo,cache):
  def getsha1(branch):
    f=open(os.getenv('GIT_DIR','/dev/null')+'/refs/heads/'+branch)
    sha1=f.readlines()[0].split('\n')[0]
    f.close()
    return sha1

  for b in cache.keys():
    sys.stderr.write('Verifying branch [%s]\n' % b)
    sha1=getsha1(b)
    c=cache.get(b)
    if sha1!=c:
      sys.stderr.write('Warning: Branch [%s] modified outside hg2git:'
        '\n%s (repo) != %s (cache)\n' % (b,sha1,c))
  return True

if __name__=='__main__':
  if len(sys.argv)!=6: sys.exit(usage(1))
  repourl,m,marksfile,headsfile,tipfile=sys.argv[1:]
  _max=int(m)

  marks_cache=load_cache(marksfile)
  heads_cache=load_cache(headsfile)
  state_cache=load_cache(tipfile)

  ui,repo=setup_repo(repourl)

  if not verify_heads(ui,repo,heads_cache):
    sys.exit(1)

  tip=repo.changelog.count()

  min=int(state_cache.get('tip',0))
  max=_max
  if _max<0:
    max=tip

  c=int(state_cache.get('count',0))
  last={}
  for rev in range(min,max):
    c=export_commit(ui,repo,rev,marks_cache,heads_cache,last,tip,c)

  c=export_tags(ui,repo,marks_cache,c)

  state_cache['tip']=max
  state_cache['count']=c
  state_cache['repo']=repourl
  save_cache(tipfile,state_cache)
