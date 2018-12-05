def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, args):
        if not args in ['start','end']:
            raise Exception('Cannot have branch name anywhere but start and end')
        self.pos = args

    def commit_message_filter(self,commit_data):
        if self.pos == 'start':
            commit_data['desc'] = commit_data['branch'] + '\n' + commit_data['desc']
        if self.pos == 'end':
            commit_data['desc'] = commit_data['desc'] + '\n' + commit_data['branch']
