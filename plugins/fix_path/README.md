## Fix pathnames

Pathnames in hg repositories can be of the form /folder//subfolder/...
this results in a crash with the following message:
```
fatal: Empty path component found in input
```
See [github issue](https://github.com/frej/fast-export/issues/240)

To use the plugin, add

    --plugin fix_path
