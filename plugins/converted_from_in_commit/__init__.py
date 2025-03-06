def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, args):
        pass

    def commit_message_filter(self, commit_data):
        cvt = commit_data['extra'].get(b'convert_revision')
        if cvt is not None:
            commit_data['desc'] = (
                    commit_data['desc'] + b'\n\nConverted From: ' + cvt 
            )

