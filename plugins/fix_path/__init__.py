def build_filter(args):
    return Filter()

class Filter:

    def file_data_filter(self, file_data):
        filename = file_data['filename']
        if '//' in filename:
            file_data['filename'] = filename.replace("//", "/")
