#Pipe contents of each exported file through FILTER_CONTENTS <file-path> <hg-hash> <is-binary>"
import subprocess
import shlex
import sys
from mercurial import node

def build_filter(args):
    return Filter(args)

class Filter:
    def __init__(self, args):
        self.filter_contents = shlex.split(args)

    def file_data_filter(self,file_data):
        d = file_data['data']
        file_ctx = file_data['file_ctx']
        filename = file_data['filename']
        filter_cmd = self.filter_contents + [filename, node.hex(file_ctx.filenode()), '1' if file_ctx.isbinary() else '0']
        try:
            filter_proc = subprocess.Popen(filter_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            d, _ = filter_proc.communicate(d)
        except:
            sys.stderr.write('Running filter-contents %s:\n' % filter_cmd)
            raise
        filter_ret = filter_proc.poll()
        if filter_ret:
            raise subprocess.CalledProcessError(filter_ret, filter_cmd)
        file_data['data'] = d
