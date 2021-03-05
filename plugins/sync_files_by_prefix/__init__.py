def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, args):
        self.prefixes = args.split(",")

    def file_data_filter(self,file_data):
        filename = file_data['filename']
        file_data["drop_file"] = not any([ filename.startswith(x) for x in self.prefixes ])
