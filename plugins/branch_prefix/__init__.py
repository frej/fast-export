import sys


def build_filter(args):
    return Filter(args)


class Filter:
    def __init__(self, args):
        args = args.split(',')
        sys.stderr.write(f"args: {args}\n")
        self.prefix = args[0]

    def commit_message_filter(self, commit_data):
        commit_data['branch'] = f"{self.prefix}{commit_data['branch'].decode()}".encode()
