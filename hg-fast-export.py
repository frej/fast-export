#!/usr/bin/env python

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

from mercurial import node
from hg2git import setup_repo,fixup_user,get_branch,get_changeset
from hg2git import load_cache,save_cache,get_git_sha1,set_default_branch,set_origin_name
from optparse import OptionParser
from git import Repo
import re
import sys
import os

if sys.platform == "win32":
  # On Windows, sys.stdout is initially opened in text mode, which means that
  # when a LF (\n) character is written to sys.stdout, it will be converted
  # into CRLF (\r\n).  That makes git blow up, so use this platform-specific
  # code to change the mode of sys.stdout to binary.
  import msvcrt
  msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

# silly regex to catch Signed-off-by lines in log message
sob_re=re.compile('^Signed-[Oo]ff-[Bb]y: (.+)$')
# insert 'checkpoint' command after this many commits or none at all if 0
cfg_checkpoint_count=0
# write some progress message every this many file contents written
cfg_export_boundary=1000

subrepo_cache = {}

def gitmode(flags):
  return 'l' in flags and '120000' or 'x' in flags and '100755' or '100644'

def wr_no_nl(msg=''):
  if msg:
    sys.stdout.write(msg)

def wr(msg=''):
  wr_no_nl(msg)
  sys.stdout.write('\n')
  #map(lambda x: sys.stderr.write('\t[%s]\n' % x),msg.split('\n'))

def checkpoint(count):
  count=count+1
  if cfg_checkpoint_count>0 and count%cfg_checkpoint_count==0:
    sys.stderr.write("Checkpoint after %d commits\n" % count)
    wr('checkpoint')
    wr()
  return count

def revnum_to_revref(rev, old_marks):
  """Convert an hg revnum to a git-fast-import rev reference (an SHA1
  or a mark)"""
  return old_marks.get(rev) or ':%d' % (rev+1)

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
    elif match(dleft[left],right) or gitmode(dleft.flags(left))!=gitmode(dright.flags(left)):
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

def export_file_contents(ctx,manifest,files,hgtags,repourl,revnode,ignoreSub,encoding=''):
  count=0
  max=len(files)
  for file in files:
    # create submodule file istead of .hgsubstate file
    if not ignoreSub and ctx.substate and file == ".hgsubstate":
      smContent=""
      for name in ctx.substate:
        subRepoDir=ctx.substate[name][0]
        linkFileName=repourl+"/"+name+"/.hg/link2git"
        if (os.path.isfile(linkFileName)):
          gitRepoLocation=open(linkFileName, "r").read()
          if not name in subrepo_cache:
            subrepo_cache[name] = load_cache(gitRepoLocation+"/hg2git-revisions")
          gitRepo = Repo(gitRepoLocation)
          smContent += '[submodule "%s"]\n\tpath = %s\n\turl = %s\n' % (name, name, gitRepo.remotes.origin.url)
      wr('M 100644 inline .gitmodules')
      wr('data %d' % (len(smContent)+1))
      wr(smContent)
      # read .hgsubstate file
      data = ctx.filectx(file).data()
      subHashes = {}
      for line in data.split('\n'):
        if line.strip() == "":
          continue
        cols= line.split(' ')
        subHashes[cols[1]]=cols[0]
      for name in ctx.substate:
        if subHashes[name] in subrepo_cache[name]:
          gitSha = subrepo_cache[name][subHashes[name]]
          wr('M 160000 %s %s' % (gitSha, name))
      continue
    # Skip .hgtags files. They only get us in trouble.
    if not hgtags and file == ".hgtags":
      sys.stderr.write('Skip %s\n' % (file))
      continue
    d=ctx.filectx(file).data()
    if encoding:
      filename=file.decode(encoding).encode('utf8')
    else:
      filename=file
    wr('M %s inline %s' % (gitmode(manifest.flags(file)),filename))
    wr('data %d' % len(d)) # had some trouble with size()
    wr(d)
    count+=1
    if count%cfg_export_boundary==0:
      sys.stderr.write('Exported %d/%d files\n' % (count,max))
  if max>cfg_export_boundary:
    sys.stderr.write('Exported %d/%d files\n' % (count,max))

def sanitize_name(name,fixBranch,what="branch"):
  """Sanitize input roughly according to git-check-ref-format(1)"""

  def dot(name):
    if name[0] == '.': return '_'+name[1:]
    return name

  n=name.replace(" ", "_").replace("(", "").replace(")", "")
  p=re.compile('([[ ~^:?\\\\*]|\.\.)')
  n=p.sub('_', n)
  if n[-1] in ('/', '.'): n=n[:-1]+'_'
  n='/'.join(map(dot,n.split('/')))
  p=re.compile('_+')
  n=p.sub('_', n)
  sys.stderr.write('Branch name: [%s]\n' % (n))
  if n!=name:
    sys.stderr.write('Warning: sanitized %s [%s] to [%s]\n' % (what,name,n))

  validCharacters = "[^0-9a-zA-Z\/\.\(\)_-]"
  changed = re.sub(validCharacters, "", n)
  if changed != n:
    sys.stderr.write('Warning: Found invalid characters in branch name %s - [%s|%s]' % (what,name,changed))
    if fixBranch:
      n = changed
      sys.stderr.write(" - changed branch name")
    else:
      sys.stderr.write(" - not changing (use --fix-branchnames to change name)")
  return n

def export_commit(ui,repo,revision,old_marks,max,count,authors,sob,brmap,hgtags,notes,repourl,ignoreSub,fixBranch,encoding=''):
  def get_branchname(name,fixBranch):
    if brmap.has_key(name):
      return brmap[name]
    n=sanitize_name(name,fixBranch)
    brmap[name]=n
    return n

  (revnode,_,user,(time,timezone),files,desc,branch,_)=get_changeset(ui,repo,revision,authors,encoding)

  branch=get_branchname(branch,fixBranch)

  parents = [p for p in repo.changelog.parentrevs(revision) if p >= 0]

  if len(parents)==0 and revision != 0:
    wr('reset refs/heads/%s' % branch)

  wr('commit refs/heads/%s' % branch)
  wr('mark :%d' % (revision+1))
  if sob:
    wr('author %s %d %s' % (get_author(desc,user,authors),time,timezone))
  wr('committer %s %d %s' % (user,time,timezone))
  wr('data %d' % (len(desc)+1)) # wtf?
  wr(desc)
  wr()

  ctx=repo.changectx(str(revision))
  man=ctx.manifest()
  added,changed,removed,type=[],[],[],''

  if len(parents) == 0:
    # first revision: feed in full manifest
    added=man.keys()
    added.sort()
    type='full'
  else:
    wr('from %s' % revnum_to_revref(parents[0], old_marks))
    if len(parents) == 1:
      # later non-merge revision: feed in changed manifest
      # if we have exactly one parent, just take the changes from the
      # manifest without expensively comparing checksums
      f=repo.status(repo.lookup(parents[0]),revnode)[:3]
      added,changed,removed=f[1],f[0],f[2]
      type='simple delta'
    else: # a merge with two parents
      wr('merge %s' % revnum_to_revref(parents[1], old_marks))
      # later merge revision: feed in changed manifest
      # for many files comparing checksums is expensive so only do it for
      # merges where we really need it due to hg's revlog logic
      added,changed,removed=get_filechanges(repo,revision,parents,man)
      type='thorough delta'

  sys.stderr.write('%s: Exporting %s revision %d/%d with %d/%d/%d added/changed/removed files\n' %
      (branch,type,revision+1,max,len(added),len(changed),len(removed)))

  if encoding:
    removed=[r.decode(encoding).encode('utf8') for r in removed]

  map(lambda r: wr('D %s' % r),removed)
  export_file_contents(ctx,man,added,hgtags,repourl,revnode,ignoreSub, encoding)
  export_file_contents(ctx,man,changed,hgtags,repourl,revnode,ignoreSub, encoding)
  wr()

  count=checkpoint(count)
  count=generate_note(user,time,timezone,revision,ctx,count,notes)
  return count

def generate_note(user,time,timezone,revision,ctx,count,notes):
  if not notes:
    return count
  wr('commit refs/notes/hg')
  wr('committer %s %d %s' % (user,time,timezone))
  wr('data 0')
  wr('N inline :%d' % (revision+1))
  hg_hash=ctx.hex()
  wr('data %d' % (len(hg_hash)))
  wr_no_nl(hg_hash)
  wr()
  return checkpoint(count)
  
def export_tags(ui,repo,old_marks,mapping_cache,count,authors):
  l=repo.tagslist()
  for tag,node in l:
    tag=sanitize_name(tag,"tag")
    # ignore latest revision
    if tag=='tip': continue
    # ignore tags to nodes that are missing (ie, 'in the future')
    if node.encode('hex_codec') not in mapping_cache:
      sys.stderr.write('Tag %s refers to unseen node %s\n' % (tag, node.encode('hex_codec')))
      continue

    rev=int(mapping_cache[node.encode('hex_codec')])

    ref=revnum_to_revref(rev, old_marks)
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
  a=0
  lre=re.compile('^([^=]+)[ ]*=[ ]*(.+)$')
  for line in f.readlines():
    l+=1
    line=line.strip()
    if line=='' or line[0]=='#':
      continue
    m=lre.match(line)
    if m==None:
      sys.stderr.write('Invalid file format in [%s], line %d\n' % (filename,l))
      continue
    # put key:value in cache, key without ^:
    cache[m.group(1).strip()]=m.group(2).strip()
    a+=1
  f.close()
  sys.stderr.write('Loaded %d authors\n' % a)
  return cache

def branchtip(repo, heads):
  '''return the tipmost branch head in heads'''
  tip = heads[-1]
  for h in reversed(heads):
    if 'close' not in repo.changelog.read(h)[5]:
      tip = h
      break
  return tip

def verify_heads(ui,repo,cache,force):
  branches={}
  for bn, heads in repo.branchmap().iteritems():
    branches[bn] = branchtip(repo, heads)
  l=[(-repo.changelog.rev(n), n, t) for t, n in branches.items()]
  l.sort()

  # get list of hg's branches to verify, don't take all git has
  for _,_,b in l:
    b=get_branch(b)
    sha1=get_git_sha1(b)
    c=cache.get(b)
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

def verify_subrepo(repourl, ctx, subRepoWarnings):
    for key in ctx.substate:
        subRepoDir=ctx.substate[key][0]
        subRepoType=ctx.substate[key][2]
        linkFileName=repourl+"/"+key+"/.hg/link2git"
        if (subRepoType == "hg" and not os.path.isfile(linkFileName) and not key in subRepoWarnings):
            subRepoWarnings[key]="ERROR: Repository has not converted subrepo in directory '%s'. \n    First convert sub repository and use %s for the -r parameter!\n" % (key, repourl+"/"+key)
        if (subRepoType == "hg" and os.path.isfile(linkFileName)):
            gitRepoLocation=open(linkFileName, "r").read()
            gitRepo = Repo(gitRepoLocation)
            if not gitRepo.remotes and not key+"_remote" in subRepoWarnings:
                subRepoWarnings[key+"_remote"]="ERROR: Sub repo '%s' has no origin remote url!" % key
                continue
            if gitRepo.remotes and not gitRepo.remotes.origin:
                subRepoWarnings[key+"_remote"]="ERROR: Sub repo '%s' has no origin remote url!" % key
    return subRepoWarnings

def hg2git(repourl,m,marksfile,mappingfile,headsfile,tipfile,authors={},sob=False,force=False,hgtags=False,notes=False,ignoreSub=False,fixBranch=False,encoding=''):
  _max=int(m)

  old_marks=load_cache(marksfile,lambda s: int(s)-1)
  mapping_cache=load_cache(mappingfile)
  heads_cache=load_cache(headsfile)
  state_cache=load_cache(tipfile)

  ui,repo=setup_repo(repourl)

  if not verify_heads(ui,repo,heads_cache,force):
    return 1

  try:
    tip=repo.changelog.count()
  except AttributeError:
    tip=len(repo)

  min=int(state_cache.get('tip',0))
  max=_max
  if _max<0 or max>tip:
    max=tip

  subRepoWarnings = {}
  for rev in range(0,max):
    if not ignoreSub:
      # check if repository uses unconverted subrepos
      ctx=repo.changectx(str(rev))
      if (ctx.substate):
        subRepoWarnings=verify_subrepo(repourl, ctx, subRepoWarnings)
    (revnode,_,_,_,_,_,_,_)=get_changeset(ui,repo,rev,authors)
    mapping_cache[revnode.encode('hex_codec')] = str(rev)

  if subRepoWarnings:
    sys.stderr.write("\n")
    for key in subRepoWarnings.keys():
      sys.stderr.write(subRepoWarnings[key])
    sys.stderr.write("\n")
    return 1
  c=0
  brmap={}
  for rev in range(min,max):
    c=export_commit(ui,repo,rev,old_marks,max,c,authors,sob,brmap,hgtags,notes,repourl,ignoreSub,fixBranch,encoding)

  state_cache['tip']=max
  state_cache['repo']=repourl
  save_cache(tipfile,state_cache)
  save_cache(mappingfile,mapping_cache)

  c=export_tags(ui,repo,old_marks,mapping_cache,c,authors)

  sys.stderr.write('Issued %d commands\n' % c)

  return 0

if __name__=='__main__':
  def bail(parser,opt):
    sys.stderr.write('Error: No %s option given\n' % opt)
    parser.print_help()
    sys.exit(2)

  parser=OptionParser()

  parser.add_option("-m","--max",type="int",dest="max",
      help="Maximum hg revision to import")
  parser.add_option("--mapping",dest="mappingfile",
      help="File to read last run's hg-to-git SHA1 mapping")
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
  parser.add_option("--hgtags",action="store_true",dest="hgtags",
      default=False,help="Enable exporting .hgtags files")
  parser.add_option("-A","--authors",dest="authorfile",
      help="Read authormap from AUTHORFILE")
  parser.add_option("-f","--force",action="store_true",dest="force",
      default=False,help="Ignore validation errors by force")
  parser.add_option("-M","--default-branch",dest="default_branch",
      help="Set the default branch")
  parser.add_option("-o","--origin",dest="origin_name",
      help="use <name> as namespace to track upstream")
  parser.add_option("--hg-hash",action="store_true",dest="notes",
      default=False,help="Annotate commits with the hg hash as git notes in the hg namespace")
  parser.add_option("-e",dest="encoding",
      help="Assume commit and author strings retrieved from Mercurial are encoded in <encoding>")
  parser.add_option("--ignore-subrepos",action="store_true",dest="ignore_subrepos",
      default=False,help="Ignore sub repositories")
  parser.add_option("--fix-branchnames",action="store_true",dest="fix_branchnames",
      default=False,help="Fix invalid branch names (removes invalid characters)")
  (options,args)=parser.parse_args()

  m=-1
  if options.max!=None: m=options.max

  if options.marksfile==None: bail(parser,'--marks')
  if options.mappingfile==None: bail(parser,'--mapping')
  if options.headsfile==None: bail(parser,'--heads')
  if options.statusfile==None: bail(parser,'--status')
  if options.repourl==None: bail(parser,'--repo')

  # create file containing dirextory of converted git repository (used to get git revision if this repo is used as a subrepo in other repository)
  linkFile = open(options.repourl + "/.hg/link2git", "w+")
  linkFile.write(options.statusfile.replace("/hg2git-state", ""))
  linkFile.close()

  a={}
  if options.authorfile!=None:
    a=load_authors(options.authorfile)

  if options.default_branch!=None:
    set_default_branch(options.default_branch)

  if options.origin_name!=None:
    set_origin_name(options.origin_name)

  encoding=''
  if options.encoding!=None:
    encoding=options.encoding

  sys.exit(hg2git(options.repourl,m,options.marksfile,options.mappingfile,
                  options.headsfile, options.statusfile,authors=a,
                  sob=options.sob,force=options.force,hgtags=options.hgtags,
                  notes=options.notes,ignoreSub=options.ignore_subrepos, fixBranch=options.fix_branchnames,
                  encoding=encoding))
