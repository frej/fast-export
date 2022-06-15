#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright 2022 David Miguel Susano Pinto
##
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:
##
## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


class HgHashInCommitFilter:
    def __init__(self, prefix=b"hg:"):
        self._prefix = prefix

    def commit_message_filter(self, commit_data):
        assert "hg_hash" in commit_data and "desc" in commit_data

        new_paragraph = b"\n\n"
        commit_data['desc'] += (new_paragraph
                                + self._prefix
                                + commit_data["hg_hash"])


def build_filter(opts):
    # FIXME: having an empty prefix is not supported.
    #
    # opts is the string that comes after the plugin name in the
    # command line arguments to fast-export:
    #
    # Use default prefix ("hg:") and opts will be the empty string:
    #
    #    --plugin hg_hash_in_commit
    #
    # Uses prefix "hg: " (opts is "hg: ").  Note the use of quotes
    # which are required for the space at the end to be included in
    # the prefix:
    #
    #    --plugin hg_hash_in_commit="hg: "
    #
    # The way options for plugins are handled makes it tricky to pass
    # an empty option value, i.e., how can one set prefix to the empty
    # string while keeping a default prefix value?

    if not opts:
        args = []
    else:
        args = [opts.encode()]
    return HgHashInCommitFilter(*args)
