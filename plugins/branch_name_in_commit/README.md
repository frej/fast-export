## Branch Name in Commit Message

Mercurial has a much stronger notion of branches than Git,
and some parties may not wish to lose the branch information
during the migration to Git. You can use this plugin to either
prepend or append the branch name from the mercurial
commit into the commit message in Git.

To use the plugin, add
`--plugin branch_name_in_commit=(start|end)`.
