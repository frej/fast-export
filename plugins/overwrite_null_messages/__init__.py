def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, args):
        if args == '':
            message = b'<empty commit message>'
        else:
            message = args.encode('utf8')
        self.message = message

    def commit_message_filter(self,commit_data):
        # Only write the commit message if the recorded commit
        # message is null.
        if commit_data['desc'] == b'\x00':
            commit_data['desc'] = self.message
