## Convert Head to Branch

`fast-export` can only handle one head per branch.  This plugin allows one
to create a new branch from a head by specifying the new branch name and
the first divergent commit for that head.  The revision number for the commit
should be in decimal form.

To use the plugin, add
`--plugin head2branch=name,<rev>`.
