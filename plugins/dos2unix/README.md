## Dos2unix filter

This plugin converts CRLF line ending to LF in text files in the repo.
It is recommended that you have a .gitattributes file that maintains
the usage of LF endings going forward, for after you have converted your
repository.

To use the plugin, add
`--plugin dos2unix`.
