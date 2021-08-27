#!/usr/bin/env python2

# Copyright (c) 2007, 2008 Rocco Rutte <pdmef@gmx.net> and others.
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

from mercurial import node
from mercurial.scmutil import revsymbol
from hg2git import setup_repo,fixup_user,get_branch,get_changeset
from hg2git import load_cache,save_cache,get_git_sha1,set_default_branch,set_origin_name
from optparse import OptionParser
import re
import sys
import os
from binascii import hexlify
import pluginloader
PY2 = sys.version_info.major == 2
if PY2:
  str = unicode

if PY2 and sys.platform == "win32":
  # On Windows, sys.stdout is initially opened in text mode, which means that
  # when a LF (\n) character is written to sys.stdout, it will be converted
  # into CRLF (\r\n).  That makes git blow up, so use this platform-specific
  # code to change the mode of sys.stdout to binary.
  import msvcrt
  msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

# silly regex to catch Signed-off-by lines in log message
sob_re=re.compile(b'^Signed-[Oo]ff-[Bb]y: (.+)$')
# insert 'checkpoint' command after this many commits or none at all if 0
cfg_checkpoint_count=0
# write some progress message every this many file contents written
cfg_export_boundary=1000

subrepo_cache={}
submodule_mappings=None

# True if fast export should automatically try to sanitize
# author/branch/tag names.
auto_sanitize = None

stdout_buffer = sys.stdout if PY2 else sys.stdout.buffer
stderr_buffer = sys.stderr if PY2 else sys.stderr.buffer

def gitmode(flags):
  return b'l' in flags and b'120000' or b'x' in flags and b'100755' or b'100644'

def wr_no_nl(msg=b''):
  assert isinstance(msg, bytes)
  if msg:
    stdout_buffer.write(msg)

def wr(msg=b''):
  wr_no_nl(msg)
  stdout_buffer.write(b'\n')
  #map(lambda x: sys.stderr.write('\t[%s]\n' % x),msg.split('\n'))

def checkpoint(count):
  count=count+1
  if cfg_checkpoint_count>0 and count%cfg_checkpoint_count==0:
    stderr_buffer.write(b"Checkpoint after %d commits\n" % count)
    wr(b'checkpoint')
    wr()
  return count

def revnum_to_revref(rev, old_marks):
  """Convert an hg revnum to a git-fast-import rev reference (an SHA1
  or a mark)"""
  return old_marks.get(rev) or b':%d' % (rev+1)

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
    mright=revsymbol(repo,b"%d" %p).manifest()
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

  loglines=logmessage.split(b'\n')
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

def remove_gitmodules(ctx):
  """Removes all submodules of ctx parents"""
  # Removing all submoduies coming from all parents is safe, as the submodules
  # of the current commit will be re-added below. A possible optimization would
  # be to only remove the submodules of the first parent.
  for parent_ctx in ctx.parents():
    for submodule in parent_ctx.substate.keys():
      wr(b'D %s' % submodule)
  wr(b'D .gitmodules')

def refresh_git_submodule(name,subrepo_info):
  wr(b'M 160000 %s %s' % (subrepo_info[1],name))
  stderr_buffer.write(
    b"Adding/updating submodule %s, revision %s\n" % (name, subrepo_info[1])
  )
  return b'[submodule "%s"]\n\tpath = %s\n\turl = %s\n' % (name, name, subrepo_info[0])

def refresh_hg_submodule(name,subrepo_info):
  gitRepoLocation=submodule_mappings[name] + b"/.git"

  # Populate the cache to map mercurial revision to git revision
  if not name in subrepo_cache:
    subrepo_cache[name]=(load_cache(gitRepoLocation+b"/hg2git-mapping"),
                         load_cache(gitRepoLocation+b"/hg2git-marks",
                                    lambda s: int(s)-1))

  (mapping_cache,marks_cache)=subrepo_cache[name]
  subrepo_hash=subrepo_info[1]
  if subrepo_hash in mapping_cache:
    revnum=mapping_cache[subrepo_hash]
    gitSha=marks_cache[int(revnum)]
    wr(b'M 160000 %s %s' % (gitSha,name))
    stderr_buffer.write(
      b"Adding/updating submodule %s, revision %s->%s\n"
      % (name, subrepo_hash, gitSha)
    )
    return b'[submodule "%s"]\n\tpath = %s\n\turl = %s\n' % (name,name,
      submodule_mappings[name])
  else:
    stderr_buffer.write(
      b"Warning: Could not find hg revision %s for %s in git %s\n"
      % (subrepo_hash, name, gitRepoLocation,)
    )
    return b''

def refresh_gitmodules(ctx):
  """Updates list of ctx submodules according to .hgsubstate file"""
  remove_gitmodules(ctx)
  gitmodules=b""
  # Create the .gitmodules file and all submodules
  for name,subrepo_info in ctx.substate.items():
    if subrepo_info[2]==b'git':
      gitmodules+=refresh_git_submodule(name,subrepo_info)
    elif submodule_mappings and name in submodule_mappings:
      gitmodules+=refresh_hg_submodule(name,subrepo_info)

  if len(gitmodules):
    wr(b'M 100644 inline .gitmodules')
    wr(b'data %d' % (len(gitmodules)+1))
    wr(gitmodules)

def export_file_contents(ctx,manifest,files,hgtags,encoding='',plugins={}):
  count=0
  max=len(files)
  is_submodules_refreshed=False
  for file in files:
    if not is_submodules_refreshed and (file==b'.hgsub' or file==b'.hgsubstate'):
      is_submodules_refreshed=True
      refresh_gitmodules(ctx)
    # Skip .hgtags files. They only get us in trouble.
    if not hgtags and file == b".hgtags":
      stderr_buffer.write(b'Skip %s\n' % file)
      continue
    if encoding:
      filename=file.decode(encoding).encode('utf8')
    else:
      filename=file
    if b'.git' in filename.split(b'/'): # Even on Windows, the path separator is / here.
      stderr_buffer.write(
        b'Ignoring file %s which cannot be tracked by git\n' % filename
      )
      continue
    file_ctx=ctx.filectx(file)
    d=file_ctx.data()

    if plugins and plugins['file_data_filters']:
      file_data = {'filename':filename,'file_ctx':file_ctx,'data':d}
      for filter in plugins['file_data_filters']:
        filter(file_data)
      d=file_data['data']
      filename=file_data['filename']
      file_ctx=file_data['file_ctx']

    wr(b'M %s inline %s' % (gitmode(manifest.flags(file)),
                           strip_leading_slash(filename)))
    wr(b'data %d' % len(d)) # had some trouble with size()
    wr(d)
    count+=1
    if count%cfg_export_boundary==0:
      stderr_buffer.write(b'Exported %d/%d files\n' % (count,max))
  if max>cfg_export_boundary:
    stderr_buffer.write(b'Exported %d/%d files\n' % (count,max))

def sanitize_name(name,what="branch", mapping={}):
  """Sanitize input roughly according to git-check-ref-format(1)"""

  # NOTE: Do not update this transform to work around
  # incompatibilities on your platform. If you change it and it starts
  # modifying names which previously were not touched it will break
  # preexisting setups which are doing incremental imports.
  #
  # Fast-export tries to not inflict arbitrary naming policy on the
  # user, instead it aims to provide mechanisms allowing the user to
  # apply their own policy. Therefore do not add a transform which can
  # already be implemented with the -B and -T options to mangle branch
  # and tag names. If you have a source repository where this is too
  # much work to do manually, write a tool that does it for you.
  #

  def dot(name):
    if not name: return name
    if name[0:1] == b'.': return b'_'+name[1:]
    return name

  if not auto_sanitize:
    return mapping.get(name,name)
  n=mapping.get(name,name)
  p=re.compile(b'([[ ~^:?\\\\*]|\.\.)')
  n=p.sub(b'_', n)
  if n[-1:] in (b'/', b'.'): n=n[:-1]+b'_'
  n=b'/'.join([dot(s) for s in n.split(b'/')])
  p=re.compile(b'_+')
  n=p.sub(b'_', n)

  if n!=name:
    stderr_buffer.write(
      b'Warning: sanitized %s [%s] to [%s]\n' % (what.encode(), name, n)
    )
  return n

def strip_leading_slash(filename):
  if filename[0:1] == b'/':
    return filename[1:]
  return filename

def export_commit(ui,repo,revision,old_marks,max,count,authors,
                  branchesmap,sob,brmap,hgtags,encoding='',fn_encoding='',
                  plugins={}):
  def get_branchname(name):
    if name in brmap:
      return brmap[name]
    n=sanitize_name(name, "branch", branchesmap)
    brmap[name]=n
    return n

  (revnode,_,user,(time,timezone),files,desc,branch,extra)=get_changeset(ui,repo,revision,authors,encoding)
  if repo[revnode].hidden():
    return count

  branch=get_branchname(branch)

  parents = [p for p in repo.changelog.parentrevs(revision) if p >= 0]
  author = get_author(desc,user,authors)
  hg_hash=revsymbol(repo,b"%d" % revision).hex()

  if plugins and plugins['commit_message_filters']:
    commit_data = {'branch': branch, 'parents': parents,
                   'author': author, 'desc': desc,
                   'revision': revision, 'hg_hash': hg_hash,
                   'committer': user, 'extra': extra}
    for filter in plugins['commit_message_filters']:
      filter(commit_data)
    branch = commit_data['branch']
    parents = commit_data['parents']
    author = commit_data['author']
    user = commit_data['committer']
    desc = commit_data['desc']

  if len(parents)==0 and revision != 0:
    wr(b'reset refs/heads/%s' % branch)

  wr(b'commit refs/heads/%s' % branch)
  wr(b'mark :%d' % (revision+1))
  if sob:
    wr(b'author %s %d %s' % (author,time,timezone))
  wr(b'committer %s %d %s' % (user,time,timezone))
  wr(b'data %d' % (len(desc)+1)) # wtf?
  wr(desc)
  wr()

  ctx=revsymbol(repo, b"%d" % revision)
  man=ctx.manifest()
  added,changed,removed,type=[],[],[],''

  if len(parents) == 0:
    # first revision: feed in full manifest
    added=man.keys()
    added.sort()
    type='full'
  else:
    wr(b'from %s' % revnum_to_revref(parents[0], old_marks))
    if len(parents) == 1:
      # later non-merge revision: feed in changed manifest
      # if we have exactly one parent, just take the changes from the
      # manifest without expensively comparing checksums
      f=repo.status(parents[0],revnode)
      added,changed,removed=f.added,f.modified,f.removed
      type='simple delta'
    else: # a merge with two parents
      wr(b'merge %s' % revnum_to_revref(parents[1], old_marks))
      # later merge revision: feed in changed manifest
      # for many files comparing checksums is expensive so only do it for
      # merges where we really need it due to hg's revlog logic
      added,changed,removed=get_filechanges(repo,revision,parents,man)
      type='thorough delta'

  stderr_buffer.write(
    b'%s: Exporting %s revision %d/%d with %d/%d/%d added/changed/removed files\n'
    % (branch, type.encode(), revision + 1, max, len(added), len(changed), len(removed))
  )

  for filename in removed:
    if fn_encoding:
      filename=filename.decode(fn_encoding).encode('utf8')
    filename=strip_leading_slash(filename)
    if filename==b'.hgsub':
      remove_gitmodules(ctx)
    wr(b'D %s' % filename)

  export_file_contents(ctx,man,added,hgtags,fn_encoding,plugins)
  export_file_contents(ctx,man,changed,hgtags,fn_encoding,plugins)
  wr()

  return checkpoint(count)

def export_note(ui,repo,revision,count,authors,encoding,is_first):
  (revnode,_,user,(time,timezone),_,_,_,_)=get_changeset(ui,repo,revision,authors,encoding)
  if repo[revnode].hidden():
    return count

  parents = [p for p in repo.changelog.parentrevs(revision) if p >= 0]

  wr(b'commit refs/notes/hg')
  wr(b'committer %s %d %s' % (user,time,timezone))
  wr(b'data 0')
  if is_first:
    wr(b'from refs/notes/hg^0')
  wr(b'N inline :%d' % (revision+1))
  hg_hash=revsymbol(repo,b"%d" % revision).hex()
  wr(b'data %d' % (len(hg_hash)))
  wr_no_nl(hg_hash)
  wr()
  return checkpoint(count)

def export_tags(ui,repo,old_marks,mapping_cache,count,authors,tagsmap):
  l=repo.tagslist()
  for tag,node in l:
    # Remap the branch name
    tag=sanitize_name(tag,"tag",tagsmap)
    # ignore latest revision
    if tag==b'tip': continue
    # ignore tags to nodes that are missing (ie, 'in the future')
    if hexlify(node) not in mapping_cache:
      stderr_buffer.write(b'Tag %s refers to unseen node %s\n' % (tag, hexlify(node)))
      continue

    rev=int(mapping_cache[hexlify(node)])

    ref=revnum_to_revref(rev, old_marks)
    if ref==None:
      stderr_buffer.write(
        b'Failed to find reference for creating tag %s at r%d\n' % (tag, rev)
      )
      continue
    stderr_buffer.write(b'Exporting tag [%s] at [hg r%d] [git %s]\n' % (tag, rev, ref))
    wr(b'reset refs/tags/%s' % tag)
    wr(b'from %s' % ref)
    wr()
    count=checkpoint(count)
  return count

def load_mapping(name, filename, mapping_is_raw):
  raw_regexp=re.compile(b'^([^=]+)[ ]*=[ ]*(.+)$')
  string_regexp=b'"(((\\.)|(\\")|[^"])*)"'
  quoted_regexp=re.compile(b'^'+string_regexp+b'[ ]*=[ ]*'+string_regexp+b'$')

  def parse_raw_line(line):
    m=raw_regexp.match(line)
    if m==None:
      return None
    return (m.group(1).strip(), m.group(2).strip())

  def process_unicode_escape_sequences(s):
    # Replace unicode escape sequences in the otherwise UTF8-encoded bytestring s with
    # the UTF8-encoded characters they represent. We need to do an additional
    # .decode('utf8').encode('unicode-escape') to convert any non-ascii characters into
    # their escape sequences so that the subsequent .decode('unicode-escape') succeeds:
    return s.decode('utf8').encode('unicode-escape').decode('unicode-escape').encode('utf8')

  def parse_quoted_line(line):
    m=quoted_regexp.match(line)
    if m==None:
      return 
    
    return (process_unicode_escape_sequences(m.group(1)),
            process_unicode_escape_sequences(m.group(5)))

  cache={}
  if not os.path.exists(filename):
    sys.stderr.write('Could not open mapping file [%s]\n' % (filename))
    return cache
  f=open(filename,'rb')
  l=0
  a=0
  for line in f.readlines():
    l+=1
    line=line.strip()
    if l==1 and line[0:1]==b'#' and line==b'# quoted-escaped-strings':
      continue
    elif line==b'' or line[0:1]==b'#':
      continue
    m=parse_raw_line(line) if mapping_is_raw else parse_quoted_line(line)
    if m==None:
      sys.stderr.write('Invalid file format in [%s], line %d\n' % (filename,l))
      continue
    # put key:value in cache, key without ^:
    cache[m[0]]=m[1]
    a+=1
  f.close()
  sys.stderr.write('Loaded %d %s\n' % (a, name))
  return cache

def branchtip(repo, heads):
  '''return the tipmost branch head in heads'''
  tip = heads[-1]
  for h in reversed(heads):
    if 'close' not in repo.changelog.read(h)[5]:
      tip = h
      break
  return tip

def verify_heads(ui,repo,cache,force,ignore_unnamed_heads,branchesmap):
  branches={}
  for bn, heads in repo.branchmap().iteritems():
    branches[bn] = branchtip(repo, heads)
  l=[(-repo.changelog.rev(n), n, t) for t, n in branches.items()]
  l.sort()

  # get list of hg's branches to verify, don't take all git has
  for _,_,b in l:
    b=get_branch(b)
    sanitized_name=sanitize_name(b,"branch",branchesmap)
    sha1=get_git_sha1(sanitized_name)
    c=cache.get(sanitized_name)
    if not c and sha1:
      stderr_buffer.write(
        b'Error: Branch [%s] already exists and was not created by hg-fast-export, '
        b'export would overwrite unrelated branch\n' % b)
      if not force: return False
    elif sha1!=c:
      stderr_buffer.write(
        b'Error: Branch [%s] modified outside hg-fast-export:'
        b'\n%s (repo) != %s (cache)\n' % (b, b'<None>' if sha1 is None else sha1, c)
      )
      if not force: return False

  # verify that branch has exactly one head
  t={}
  unnamed_heads=False
  for h in repo.filtered(b'visible').heads():
    (_,_,_,_,_,_,branch,_)=get_changeset(ui,repo,h)
    if t.get(branch,False):
      stderr_buffer.write(
        b'Error: repository has an unnamed head: hg r%d\n'
        % repo.changelog.rev(h)
      )
      unnamed_heads=True
      if not force and not ignore_unnamed_heads: return False
    t[branch]=True
  if unnamed_heads and not force and not ignore_unnamed_heads: return False
  return True

def hg2git(repourl,m,marksfile,mappingfile,headsfile,tipfile,
           authors={},branchesmap={},tagsmap={},
           sob=False,force=False,ignore_unnamed_heads=False,hgtags=False,notes=False,encoding='',fn_encoding='',
           plugins={}):
  def check_cache(filename, contents):
    if len(contents) == 0:
      sys.stderr.write('Warning: %s does not contain any data, this will probably make an incremental import fail\n' % filename)

  _max=int(m)

  old_marks=load_cache(marksfile,lambda s: int(s)-1)
  mapping_cache=load_cache(mappingfile)
  heads_cache=load_cache(headsfile)
  state_cache=load_cache(tipfile)

  if len(state_cache) != 0:
    for (name, data) in [(marksfile, old_marks),
                         (mappingfile, mapping_cache),
                         (headsfile, state_cache)]:
      check_cache(name, data)

  ui,repo=setup_repo(repourl)

  if not verify_heads(ui,repo,heads_cache,force,ignore_unnamed_heads,branchesmap):
    return 1

  try:
    tip=repo.changelog.count()
  except AttributeError:
    tip=len(repo)

  min=int(state_cache.get(b'tip',0))
  max=_max
  if _max<0 or max>tip:
    max=tip

  for rev in range(0,max):
    (revnode,_,_,_,_,_,_,_)=get_changeset(ui,repo,rev,authors)
    if repo[revnode].hidden():
      continue
    mapping_cache[hexlify(revnode)] = b"%d" % rev

  if submodule_mappings:
    # Make sure that all mercurial submodules are registered in the submodule-mappings file
    for rev in range(0,max):
      ctx=revsymbol(repo,b"%d" % rev)
      if ctx.hidden():
        continue
      if ctx.substate:
        for key in ctx.substate:
          if ctx.substate[key][2]=='hg' and key not in submodule_mappings:
            sys.stderr.write("Error: %s not found in submodule-mappings\n" % (key))
            return 1

  c=0
  brmap={}
  for rev in range(min,max):
    c=export_commit(ui,repo,rev,old_marks,max,c,authors,branchesmap,
                    sob,brmap,hgtags,encoding,fn_encoding,
                    plugins)
  if notes:
    for rev in range(min,max):
      c=export_note(ui,repo,rev,c,authors, encoding, rev == min and min != 0)

  state_cache[b'tip']=max
  state_cache[b'repo']=repourl
  save_cache(tipfile,state_cache)
  save_cache(mappingfile,mapping_cache)

  c=export_tags(ui,repo,old_marks,mapping_cache,c,authors,tagsmap)

  sys.stderr.write('Issued %d commands\n' % c)

  return 0

if __name__=='__main__':
  def bail(parser,opt):
    sys.stderr.write('Error: No %s option given\n' % opt)
    parser.print_help()
    sys.exit(2)

  parser=OptionParser()

  parser.add_option("-n", "--no-auto-sanitize",action="store_false",
      dest="auto_sanitize",default=True,
      help="Do not perform built-in (broken in many cases) sanitizing of names")
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
  parser.add_option("-B","--branches",dest="branchesfile",
      help="Read branch map from BRANCHESFILE")
  parser.add_option("-T","--tags",dest="tagsfile",
      help="Read tags map from TAGSFILE")
  parser.add_option("-f","--force",action="store_true",dest="force",
      default=False,help="Ignore validation errors by force, implies --ignore-unnamed-heads")
  parser.add_option("--ignore-unnamed-heads",action="store_true",dest="ignore_unnamed_heads",
      default=False,help="Ignore unnamed head errors")
  parser.add_option("-M","--default-branch",dest="default_branch",
      help="Set the default branch")
  parser.add_option("-o","--origin",dest="origin_name",
      help="use <name> as namespace to track upstream")
  parser.add_option("--hg-hash",action="store_true",dest="notes",
      default=False,help="Annotate commits with the hg hash as git notes in the hg namespace")
  parser.add_option("-e",dest="encoding",
      help="Assume commit and author strings retrieved from Mercurial are encoded in <encoding>")
  parser.add_option("--fe",dest="fn_encoding",
      help="Assume file names from Mercurial are encoded in <filename_encoding>")
  parser.add_option("--mappings-are-raw",dest="raw_mappings", default=False,
      help="Assume mappings are raw <key>=<value> lines")
  parser.add_option("--filter-contents",dest="filter_contents",
      help="Pipe contents of each exported file through FILTER_CONTENTS <file-path> <hg-hash> <is-binary>")
  parser.add_option("--plugin-path", type="string", dest="pluginpath",
      help="Additional search path for plugins ")
  parser.add_option("--plugin", action="append", type="string", dest="plugins",
      help="Add a plugin with the given init string <name=init>")
  parser.add_option("--subrepo-map", type="string", dest="subrepo_map",
      help="Provide a mapping file between the subrepository name and the submodule name")

  (options,args)=parser.parse_args()

  m=-1
  auto_sanitize = options.auto_sanitize
  if options.max!=None: m=options.max

  if options.marksfile==None: bail(parser,'--marks')
  if options.mappingfile==None: bail(parser,'--mapping')
  if options.headsfile==None: bail(parser,'--heads')
  if options.statusfile==None: bail(parser,'--status')
  if options.repourl==None: bail(parser,'--repo')

  if options.subrepo_map:
      if not os.path.exists(options.subrepo_map):
        sys.stderr.write('Subrepo mapping file not found %s\n'
                         % options.subrepo_map)
        sys.exit(1)
      submodule_mappings=load_mapping('subrepo mappings',
                                      options.subrepo_map,False)

  a={}
  if options.authorfile!=None:
    a=load_mapping('authors', options.authorfile, options.raw_mappings)

  b={}
  if options.branchesfile!=None:
    b=load_mapping('branches', options.branchesfile, options.raw_mappings)

  t={}
  if options.tagsfile!=None:
    t=load_mapping('tags', options.tagsfile, options.raw_mappings)

  if options.default_branch!=None:
    set_default_branch(options.default_branch)

  if options.origin_name!=None:
    set_origin_name(options.origin_name)

  encoding=''
  if options.encoding!=None:
    encoding=options.encoding

  fn_encoding=encoding
  if options.fn_encoding!=None:
    fn_encoding=options.fn_encoding

  plugins=[]
  if options.plugins!=None:
    plugins+=options.plugins

  if options.filter_contents!=None:
    plugins+=['shell_filter_file_contents='+options.filter_contents]

  plugins_dict={}
  plugins_dict['commit_message_filters']=[]
  plugins_dict['file_data_filters']=[]

  if plugins and options.pluginpath:
    sys.stderr.write('Using additional plugin path: ' + options.pluginpath + '\n')

  for plugin in plugins:
    split = plugin.split('=')
    name, opts = split[0], '='.join(split[1:])
    i = pluginloader.get_plugin(name,options.pluginpath)
    sys.stderr.write('Loaded plugin ' + i['name'] + ' from path: ' + i['path'] +' with opts: ' + opts + '\n')
    plugin = pluginloader.load_plugin(i).build_filter(opts)
    if hasattr(plugin,'file_data_filter') and callable(plugin.file_data_filter):
      plugins_dict['file_data_filters'].append(plugin.file_data_filter)
    if hasattr(plugin, 'commit_message_filter') and callable(plugin.commit_message_filter):
      plugins_dict['commit_message_filters'].append(plugin.commit_message_filter)

  sys.exit(hg2git(options.repourl,m,options.marksfile,options.mappingfile,
                  options.headsfile, options.statusfile,
                  authors=a,branchesmap=b,tagsmap=t,
                  sob=options.sob,force=options.force,
                  ignore_unnamed_heads=options.ignore_unnamed_heads,
                  hgtags=options.hgtags,
                  notes=options.notes,encoding=encoding,fn_encoding=fn_encoding,
                  plugins=plugins_dict))
