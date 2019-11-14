import sys

def build_filter(args):
    return Filter(args)

class Filter:

    def __init__(self, args):
        args = args.split(',')
        self.branch_name = args[0]
        self.starting_commit = int(args[1])
        self.branch_parents = set()

    def commit_message_filter(self, commit_data):
        rev = commit_data['revision']
        rev_parents = commit_data['parents']
        if (rev == self.starting_commit
            or any(rp in self.branch_parents for rp in rev_parents)
            ):
            self.branch_parents.add(rev)
            commit_data['branch'] = self.branch_name.encode('ascii', 'replace')
            sys.stderr.write('\nchanging r%s to branch %r\n' % (rev, self.branch_name))
            sys.stderr.flush()
