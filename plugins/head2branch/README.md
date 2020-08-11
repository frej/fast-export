## Convert Head to Branch

`fast-export` can only handle one head per branch. This plugin makes it possible
to create a new branch from a head by specifying the new branch name and
the first divergent commit for that head.

Note: the hg hash must be in the full form, 40 hexadecimal characters.

Note: you must run `fast-export` with `--ignore-unnamed-heads` option,
otherwise, the conversion will fail.

To use the plugin, add the command line flag `--plugin head2branch=name,<hg_hash>`.
The flag can be given multiple times to name more than one head.
