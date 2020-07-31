import sys

def build_filter(args):
    return Filter(args)

class Filter:

    def __init__(self, args):
        args = args.split(',')
        self.branch_name = args[0].encode('ascii', 'replace')
        self.starting_commit_hash = args[1].encode('ascii', 'strict')
        self.branch_parents = set()

    def commit_message_filter(self, commit_data):
        hg_hash = commit_data['hg_hash']
        rev = commit_data['revision']
        rev_parents = commit_data['parents']
        if (hg_hash == self.starting_commit_hash
            or any(rp in self.branch_parents for rp in rev_parents)
            ):
            self.branch_parents.add(rev)
            commit_data['branch'] = self.branch_name
            sys.stderr.write('\nchanging r%s to branch %r\n' % (rev, self.branch_name))
            sys.stderr.flush()
