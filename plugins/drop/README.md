## Drop commits from output

To use the plugin, add the command line flag `--plugin drop=<spec>`.
The flag can be given multiple times to drop more than one commit.

The <spec> value can be either

 - a comma-separated list of hg hashes in the full form (40
   hexadecimal characters) to drop the corresponding changesets, or

 - a regular expression pattern to drop all changesets with matching
   descriptions.
