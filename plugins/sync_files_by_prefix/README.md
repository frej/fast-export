## Whitelist files and folders

To use the plugin, add the command line flag `--plugin file_prefix_whitelist=<prefixes>`.
<prefixes> is a comma separated list of prefixes. Files with a path that doesn't start
with any of the prefixes will be discarded. This can create empty commits.

Examples for prefixes:
 - "src/": This prefix whitelists everything under the src folder.
 - "src": This prefix whitelists every file or folder beginning with "src"
 - "a,b": This prefix whitelists every file beginning either with "a" or "b"
