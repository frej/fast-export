def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, args):
        args = {arg: True for arg in args.split(',')}
        self.start = args.pop('start', False)
        self.end = args.pop('end', False)
        self.sameline = args.pop('sameline', False)
        self.skip_master = args.pop('skipmaster', False)

        if self.sameline and not self.start:
            raise ValueError("sameline option only allowed if 'start' given")
        if args:
            raise ValueError("Unknown args: " + ','.join(args))

    def commit_message_filter(self, commit_data):
        if not (self.skip_master and commit_data['branch'] == b'master'):
            if self.start:
                sep = b': ' if self.sameline else b'\n'
                commit_data['desc'] = commit_data['branch'] + sep + commit_data['desc']
            if self.end:
                commit_data['desc'] = (
                    commit_data['desc'] + b'\n' + commit_data['branch']
                )
