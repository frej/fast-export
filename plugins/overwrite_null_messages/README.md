## Overwrite Null Commit Messages

There are cases (such as when creating a new, empty snippet on bitbucket
before they deprecated mercurial repositories) where you could create a
new repo with a single commit in it, but the message would be null.  Then,
when attempting to convert this repository to a git repo and pushing to 
a new host, the git push would fail with an error like this:

    error: a NUL byte in commit log message not allowed

To get around this, you may provide a string that will be used in place of
a null byte in commit messages.

To use the plugin, add

    --plugin overwrite_null_messages=""

This will use the default commit message `"<empty commit message>"`.

Or to specify a different commit message, you may pass this in at the
command line like so:

    --plugin overwrite_null_messages="use this message instead"
