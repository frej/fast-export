#!/usr/bin/python
#
# svn-fast-export.py
# ----------
#  Walk through each revision of a local Subversion repository and export it
#  in a stream that git-fast-import can consume.
#
# Author: Chris Lee <clee@kde.org>
# License: MIT <http://www.opensource.org/licenses/mit-license.php>

trunk_path = '/trunk/'
branches_path = '/branches/'
tags_path = '/tags/'

first_rev = 1
final_rev = 0

import gc, sys, os.path
from optparse import OptionParser
from time import sleep, mktime, localtime, strftime, strptime
from svn.fs import svn_fs_dir_entries, svn_fs_file_length, svn_fs_file_contents, svn_fs_is_dir, svn_fs_revision_root, svn_fs_youngest_rev, svn_fs_revision_proplist, svn_fs_revision_prop, svn_fs_paths_changed
from svn.core import svn_pool_create, svn_pool_clear, svn_pool_destroy, svn_stream_read, svn_stream_for_stdout, svn_stream_copy, svn_stream_close, run_app
from svn.repos import svn_repos_open, svn_repos_fs

ct_short = ['M', 'A', 'D', 'R', 'X']

def dump_file_blob(root, full_path, pool):
    stream_length = svn_fs_file_length(root, full_path, pool)
    stream = svn_fs_file_contents(root, full_path, pool)
    sys.stdout.write("data %s\n" % stream_length)
    sys.stdout.flush()
    ostream = svn_stream_for_stdout(pool)
    svn_stream_copy(stream, ostream, pool)
    svn_stream_close(ostream)
    sys.stdout.write("\n")


def export_revision(rev, repo, fs, pool):
    sys.stderr.write("Exporting revision %s... " % rev)

    revpool = svn_pool_create(pool)
    svn_pool_clear(revpool)

    # Open a root object representing the youngest (HEAD) revision.
    root = svn_fs_revision_root(fs, rev, revpool)

    # And the list of what changed in this revision.
    changes = svn_fs_paths_changed(root, revpool)

    i = 1
    marks = {}
    file_changes = []

    for path, change_type in changes.iteritems():
        c_t = ct_short[change_type.change_kind]
        if svn_fs_is_dir(root, path, revpool):
            continue

        if not path.startswith(trunk_path):
            # We don't handle branches. Or tags. Yet.
            pass
        else:
            if c_t == 'D':
                file_changes.append("D %s" % path.replace(trunk_path, ''))
            else:
                marks[i] = path.replace(trunk_path, '')
                file_changes.append("M 644 :%s %s" % (i, marks[i]))
                sys.stdout.write("blob\nmark :%s\n" % i)
                dump_file_blob(root, path, revpool)
                i += 1

    # Get the commit author and message
    props = svn_fs_revision_proplist(fs, rev, revpool)

    # Do the recursive crawl.
    if props.has_key('svn:author'):
        author = "%s <%s@localhost>" % (props['svn:author'], props['svn:author'])
    else:
        author = 'nobody <nobody@localhost>'

    if len(file_changes) == 0:
        svn_pool_destroy(revpool)
        sys.stderr.write("skipping.\n")
        return

    svndate = props['svn:date'][0:-8]
    commit_time = mktime(strptime(svndate, '%Y-%m-%dT%H:%M:%S'))
    sys.stdout.write("commit refs/heads/master\n")
    sys.stdout.write("committer %s %s -0000\n" % (author, int(commit_time)))
    sys.stdout.write("data %s\n" % len(props['svn:log']))
    sys.stdout.write(props['svn:log'])
    sys.stdout.write("\n")
    sys.stdout.write('\n'.join(file_changes))
    sys.stdout.write("\n\n")

    svn_pool_destroy(revpool)

    sys.stderr.write("done!\n")

    #if rev % 1000 == 0:
    #    sys.stderr.write("gc: %s objects\n" % len(gc.get_objects()))
    #    sleep(5)


def crawl_revisions(pool, repos_path):
    """Open the repository at REPOS_PATH, and recursively crawl all its
    revisions."""
    global final_rev

    # Open the repository at REPOS_PATH, and get a reference to its
    # versioning filesystem.
    repos_obj = svn_repos_open(repos_path, pool)
    fs_obj = svn_repos_fs(repos_obj)

    # Query the current youngest revision.
    youngest_rev = svn_fs_youngest_rev(fs_obj, pool)


    first_rev = 1
    if final_rev == 0:
        final_rev = youngest_rev
    for rev in xrange(first_rev, final_rev + 1):
        export_revision(rev, repos_obj, fs_obj, pool)


if __name__ == '__main__':
    usage = '%prog [options] REPOS_PATH'
    parser = OptionParser()
    parser.set_usage(usage)
    parser.add_option('-f', '--final-rev', help='Final revision to import', 
                      dest='final_rev', metavar='FINAL_REV', type='int')
    parser.add_option('-t', '--trunk-path', help='Path in repo to /trunk',
                      dest='trunk_path', metavar='TRUNK_PATH')
    parser.add_option('-b', '--branches-path', help='Path in repo to /branches',
                      dest='branches_path', metavar='BRANCHES_PATH')
    parser.add_option('-T', '--tags-path', help='Path in repo to /tags',
                      dest='tags_path', metavar='TAGS_PATH')
    (options, args) = parser.parse_args()

    if options.trunk_path != None:
        trunk_path = options.trunk_path
    if options.branches_path != None:
        branches_path = options.branches_path
    if options.tags_path != None:
        tags_path = options.tags_path
    if options.final_rev != None:
        final_rev = options.final_rev

    if len(args) != 1:
        parser.print_help()
        sys.exit(2)

    # Canonicalize (enough for Subversion, at least) the repository path.
    repos_path = os.path.normpath(args[0])
    if repos_path == '.': 
        repos_path = ''

    # Call the app-wrapper, which takes care of APR initialization/shutdown
    # and the creation and cleanup of our top-level memory pool.
    run_app(crawl_revisions, repos_path)
