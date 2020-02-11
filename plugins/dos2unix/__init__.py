def build_filter(args):
    return Filter(args)

class Filter():
    def __init__(self, args):
        pass

    def file_data_filter(self,file_data):
        file_ctx = file_data['file_ctx']
        if not file_ctx.isbinary():
            file_data['data'] = file_data['data'].replace(b'\r\n', b'\n')
