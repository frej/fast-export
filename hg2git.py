#!/usr/bin/env python2

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

from mercurial import hg,util,ui,templatefilters
from mercurial import error as hgerror
from mercurial.scmutil import revsymbol,binnode

import re
import os
import sys
import subprocess

# default git branch name
cfg_master='master'
# default origin name
origin_name=''
# silly regex to see if user field has email address
user_re=re.compile('([^<]+) (<[^>]*>)$')
# silly regex to clean out user names
user_clean_re=re.compile('^["]([^"]+)["]$')

def set_default_branch(name):
  global cfg_master
  cfg_master = name

def set_origin_name(name):
  global origin_name
  origin_name = name

def setup_repo(url):
  try:
    myui=ui.ui(interactive=False)
  except TypeError:
    myui=ui.ui()
    myui.setconfig('ui', 'interactive', 'off')
  return myui,hg.repository(myui,url)

def fixup_user(user,authors):
  user=user.strip("\"")
  if authors!=None:
    # if we have an authors table, try to get mapping
    # by defaulting to the current value of 'user'
    user=authors.get(user,user)
  name,mail,m='','',user_re.match(user)
  if m==None:
    # if we don't have 'Name <mail>' syntax, extract name
    # and mail from hg helpers. this seems to work pretty well.
    # if email doesn't contain @, replace it with devnull@localhost
    name=templatefilters.person(user)
    mail='<%s>' % templatefilters.email(user)
    if '@' not in mail:
      mail = '<devnull@localhost>'
  else:
    # if we have 'Name <mail>' syntax, everything is fine :)
    name,mail=m.group(1),m.group(2)

  # remove any silly quoting from username
  m2=user_clean_re.match(name)
  if m2!=None:
    name=m2.group(1)
  return '%s %s' % (name,mail)

def get_branch(name):
  # 'HEAD' is the result of a bug in mutt's cvs->hg conversion,
  # other CVS imports may need it, too
  if name=='HEAD' or name=='default' or name=='':
    name=cfg_master
  if origin_name:
    return origin_name + '/' + name
  return name

def get_changeset(ui,repo,revision,authors={},encoding=''):
  # Starting with Mercurial 4.6 lookup no longer accepts raw hashes
  # for lookups. Work around it by changing our behaviour depending on
  # how it fails
  try:
    node=repo.lookup(revision)
  except hgerror.ProgrammingError:
    node=binnode(revsymbol(repo,str(revision))) # We were given a numeric rev
  except hgerror.RepoLookupError:
    node=revision # We got a raw hash
  (manifest,user,(time,timezone),files,desc,extra)=repo.changelog.read(node)
  if encoding:
    user=user.decode(encoding).encode('utf8')
    desc=desc.decode(encoding).encode('utf8')
  tz="%+03d%02d" % (-timezone / 3600, ((-timezone % 3600) / 60))
  branch=get_branch(extra.get('branch','master'))
  return (node,manifest,fixup_user(user,authors),(time,tz),files,desc,branch,extra)

def mangle_key(key):
  return key

def load_cache(filename,get_key=mangle_key):
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
    cache[get_key(fields[0][1:])]=fields[1].split('\n')[0]
  f.close()
  return cache

def save_cache(filename,cache):
  f=open(filename,'w+')
  map(lambda x: f.write(':%s %s\n' % (str(x),str(cache.get(x)))),cache.keys())
  f.close()

def get_git_sha1(name,type='heads'):
  try:
    # use git-rev-parse to support packed refs
    ref="refs/%s/%s" % (type,name)
    l=subprocess.check_output(["git", "rev-parse", "--verify", "--quiet", ref])
    if l == None or len(l) == 0:
      return None
    return l[0:40]
  except subprocess.CalledProcessError:
    return None
