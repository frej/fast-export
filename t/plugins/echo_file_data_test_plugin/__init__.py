import sys
from mercurial import node

def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, _):
        pass

    def file_data_filter(self,file_data):
        with open('largefile_info.txt', 'a') as f:
            f.write(f"filename: {file_data['filename']}\n")
            f.write(f"data size: {len(file_data['data'])} bytes\n")
            f.write(f"ctx rev: {file_data['file_ctx'].rev()}\n")
            f.write(f"ctx binary: {file_data['file_ctx'].isbinary()}\n")
            f.write(f"is largefile: {file_data.get('is_largefile', False)}\n")
            f.write("\n")