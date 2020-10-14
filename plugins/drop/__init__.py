from __future__ import print_function

import sys, re


def build_filter(args):
    if re.match(r'([A-Fa-f0-9]{40}(,|$))+$', args):
        return RevisionIdFilter(args.split(','))
    else:
        return DescriptionFilter(args)


def log(fmt, *args):
    print(fmt % args, file=sys.stderr)
    sys.stderr.flush()


class FilterBase(object):
    def __init__(self):
        self.remapped_parents = {}

    def commit_message_filter(self, commit_data):
        rev = commit_data['revision']

        mapping = self.remapped_parents
        parent_revs = [rp for p in commit_data['parents']
                       for rp in mapping.get(p, [p])]

        commit_data['parents'] = parent_revs

        if self.should_drop_commit(commit_data):
            log('Dropping revision %i.', rev)

            self.remapped_parents[rev] = parent_revs

            # Head commits cannot be dropped because they have no
            # children, so detach them to a separate branch.
            commit_data['branch'] = b'dropped-hg-head'
            commit_data['parents'] = []

    def should_drop_commit(self, commit_data):
        return False


class RevisionIdFilter(FilterBase):
    def __init__(self, revision_hash_list):
        super(RevisionIdFilter, self).__init__()
        self.unwanted_hg_hashes = {h.encode('ascii', 'strict')
                                   for h in revision_hash_list}

    def should_drop_commit(self, commit_data):
        return commit_data['hg_hash'] in self.unwanted_hg_hashes


class DescriptionFilter(FilterBase):
    def __init__(self, pattern):
        super(DescriptionFilter, self).__init__()
        self.pattern = re.compile(pattern.encode('ascii', 'strict'))

    def should_drop_commit(self, commit_data):
        return self.pattern.match(commit_data['desc'])
