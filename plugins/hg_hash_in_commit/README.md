## HG hash in commit message

This plugin will append the mercurial hash to the end of the git
commit message.  To use the plugin, add to the `hg-fast-export`
command line options:

    --plugin has_hash_in_commit

By default, the hash is prefixed with `hg:`.  Others can be specified
as the only option to the plugin.  For example, the prefix `hg: `
(note the space at the end of the prefix that makes it different from
the default), use:

    --plugin hg_hash_in_commit="hg: "

At the moment, it is not possible to specify an empty prefix as that
is interpreted as using the default value.
