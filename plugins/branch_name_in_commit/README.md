## Branch Name in Commit Message

Mercurial has a much stronger notion of branches than Git,
and some parties may not wish to lose the branch information
during the migration to Git. You can use this plugin to either
prepend or append the branch name from the mercurial
commit into the commit message in Git.

Valid arguments are:

- `start`: write the branch name at the start of the commit
- `end`: write the branch name at the end of the commit
- `sameline`: if `start` specified, put a colon and a space
  after the branch name, such that the commit message reads
  `branch_name: first line of commit message`. Otherwise, the
  branch name is on the first line of the commit message by itself.
- `skipmaster`: Don't write the branch name if the branch is `master`.

To use the plugin, add
`--plugin branch_name_in_commit=<comma_separated_list_of_args>`.
