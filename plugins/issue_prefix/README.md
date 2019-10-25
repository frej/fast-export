## Issue Prefix

When migrating to other source code hosting sites, there are cases where a
project maintainer might want to reset their issue tracker and not have old
issue numbers in commit messages referring to the wrong issue.  One way around
this is to prefix issue numbers with some other string.

If migrating to GitHub, this issue prefixing can be paired with GitHub's
autolinking capabilitiy to link back to a different issue tracker:
https://help.github.com/en/github/administering-a-repository/configuring-autolinks-to-reference-external-resources

To use this plugin, add:
`--plugin=issue_prefix=<some_prefix>`

Example:
`--plugin=issue_prefix=BB-`

This will prefix issue numbers with the string `BB-`.  Example: `#123` will
change to `#BB-123`.
