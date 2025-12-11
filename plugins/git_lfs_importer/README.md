# git_lfs_importer Plugin

This plugin automatically converts matching files to use Git LFS
(Large File Storage) during the Mercurial to Git conversion process.

## Overview

The git_lfs_importer plugin intercepts file data during the hg-fast-export
process and converts files matching specified patterns into Git LFS pointers.
This allows you to seamlessly migrate a Mercurial repository to Git while
simultaneously adopting LFS for large files.

Why use git_lfs_importer?
For large repositories, traditional migration requires two sequential,
long-running steps:

 1. Full history conversion from Mercurial to Git.
 2. Full history rewrite using git lfs import.

This two-step process can take hours or even days for massive
monorepos (e.g., 100GiB+).

This plugin eliminates the second, time-consuming history rewrite. It performs
the LFS conversion incrementally (Just-In-Time). During the initial export, the
plugin identifies large files and immediately writes LFS pointers into the Git
history. This results in significantly faster conversions and allows for
efficient incremental imports of new changesets.

## Prerequisites

### Dependencies

This plugin requires the `pathspec` package:

```bash
pip install pathspec
```

### Git Repository Setup

The destination Git repository must be pre-initialized with:

1. A `.gitattributes` file configured for LFS tracking
2. Git LFS properly installed and initialized

Example `.gitattributes`:
```
*.bin filter=lfs diff=lfs merge=lfs -text
*.iso filter=lfs diff=lfs merge=lfs -text
large_files/** filter=lfs diff=lfs merge=lfs -text
```

## Usage

### Step 1: Create the Destination Git Repository

```bash
# Create a new git repository
git init my-repo
cd my-repo

# Initialize Git LFS
git lfs install

# Create and commit a .gitattributes file
cat > .gitattributes << EOF
*.bin binary diff=lfs merge=lfs -text
*.iso binary diff=lfs merge=lfs -text
EOF
git add .gitattributes
git commit -m "Initialize Git LFS configuration"

# Get the commit hash (needed for --first-commit-hash)
git rev-parse HEAD
```

### Step 2: Create an LFS Specification File

Create a file (e.g., `lfs-spec.txt`) listing the patterns of files to convert
to LFS. This uses gitignore-style glob patterns:

```
*.bin
*.iso
*.tar.gz
large_files/**
*.mp4
```

### Step 3: Run hg-fast-export with the Plugin

```bash
hg-fast-export.sh \
  -r <mercurial-repo-path> \
  --plugin git_lfs_importer=lfs-spec.txt \
  --first-commit-hash <git-commit-hash> \
  --force
```

Replace `<git-commit-hash>` with the hash obtained from Step 1.

## How It Works

1. **Pattern Matching**: Files are matched against patterns in the
   LFS specification file using gitignore-style matching
2. **File Processing**: For each matching file:
   - Calculates SHA256 hash of the file content
   - Stores the actual file content in `.git/lfs/objects/<hash-prefix>/<hash>`
   - Replaces the file data with an LFS pointer containing:
     - LFS version specification
     - SHA256 hash of the original content
     - Original file size
3. **Git Fast-Import**: The LFS pointer is committed instead of the actual
   file content

## Important Notes

### First Commit Hash Requirement

The `--first-commit-hash` option must be provided with the Git commit hash that
contains your `.gitattributes` file. This allows the plugin to chain from the
existing Git history rather than creating a completely new history.

### Deletions

The plugin safely handles file deletions (data=None) and does not process them.

### Large Files and Largefiles

If the Mercurial repository uses Mercurial's largefiles extension, those files
are already converted to their original content before reaching this plugin,
allowing the plugin to apply LFS conversion if they match the patterns.

## Example Workflow

```bash
# Configuration variables
HG_REPO=/path/to/mercurial/repo
GIT_DIR_NAME=my-project-git
LFS_PATTERN_FILE=../lfs-patterns.txt

# 1. Prepare destination git repo
mkdir "$GIT_DIR_NAME"
cd "$GIT_DIR_NAME"
git init
git lfs install

# Create .gitattributes
cat > .gitattributes << EOF
*.bin filter=lfs diff=lfs merge=lfs -text
*.iso filter=lfs diff=lfs merge=lfs -text
EOF

git add .gitattributes
git commit -m "Add LFS configuration"
FIRST_HASH=$(git rev-parse HEAD)

# 2. Create LFS patterns file
cat > "$LFS_PATTERN_FILE" << EOF
*.bin
*.iso
build/artifacts/**
EOF

# 3. Run conversion
/path/to/hg-fast-export.sh \
  -r "$HG_REPO" \
  --plugin "git_lfs_importer=$LFS_PATTERN_FILE" \
  --first-commit-hash $FIRST_HASH \
  --force

# 4. Verify
git log --oneline
git lfs ls-files
```

## Troubleshooting

### LFS Files Not Tracked
Verify that:
- The `.gitattributes` file exists in the destination repository
- Patterns in `.gitattributes` match the files being converted
- `git lfs install` was run in the repository

### "pathspec" Module Not Found
Install the required dependency:
```bash
pip install pathspec
```

### Conversion Fails at Import
Ensure the `--first-commit-hash` value is:
- A valid commit hash in the destination repository
- From a commit that exists before the conversion starts
- The hash of the commit containing `.gitattributes`


### Force Requirement

You only need to pass the `--force` option when converting the *first*
Mercurial commit into a non-empty Git repository. By default, `hg-fast-export`
prevents importing Mercurial commits onto a non-empty Git repo to avoid
creating conflicting histories. Passing `--force` overrides that safety check
and allows the exporter to write the LFS pointer objects and integrate the
converted data with the existing Git history.

If you are doing an incremental conversion (i.e., running the script a second
time to import new changesets into an already converted repository),
the --force flag is not required.

Omitting `--force` when attempting to import the first Mercurial commit into a
non-empty repository will cause the importer to refuse the operation.

## See Also

- [Git LFS Documentation](https://git-lfs.github.com/)
- [gitignore Pattern Format](https://git-scm.com/docs/gitignore)
- [hg-fast-export Documentation](../README.md)
