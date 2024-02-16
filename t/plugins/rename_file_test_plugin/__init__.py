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
        if file_data['filename'] == b'b.txt':
            file_data['filename'] = b'c.txt'
