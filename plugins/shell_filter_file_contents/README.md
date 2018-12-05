## Shell Script File Filter

This plugin uses shell scripts in order to perform filtering of files.
If your preferred scripting is done via shell, this tool is for you.
Be noted, though, that this method can cause an order of magnitude slow
down. For small repositories, this wont be an issue.

To use the plugin, add
`--plugin shell_filter_file_contents=path/to/shell/script.sh`.
The filter script is supplied to the plugin option after the plugin name,
which is in turned passed to the plugin initialization. hg-fast-export
runs the filter for each exported file, pipes its content to the filter's
standard input, and uses the filter's standard output in place
of the file's original content. An example use of this feature
is to convert line endings in text files from CRLF to git's preferred LF,
although this task is faster performed using the native plugin.

The script is called with the following syntax:
`FILTER_CONTENTS <file-path> <hg-hash> <is-binary>`

```
-- Start of crlf-filter.sh --
#!/bin/sh
# $1 = pathname of exported file relative to the root of the repo
# $2 = Mercurial's hash of the file
# $3 = "1" if Mercurial reports the file as binary, otherwise "0"

if [ "$3" == "1" ]; then cat; else dos2unix; fi
-- End of crlf-filter.sh --
```
