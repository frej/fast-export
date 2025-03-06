## Convert Revision in Commit Message

When converting a Mercurial repository, you may first convert it
from an original source before migrating it to Git.
This can be useful, for example, to remove old, irrelevant history.
To preserve original commit hashes during this process,
you can enable the `saverev` flag:
```
hg convert --config hg.convert.saverev=True ...
```

After such a conversion, the original hashes are
stored in `["extra"]["convert_revision"]`.
This plugin extracts those hashes and appends them to commit messages.
The resulting commit messages will look like this:
```
<original message>

Converted From: <convert_revision>
```

To use the plugin, add `--plugin converted_from_in_commit`.

