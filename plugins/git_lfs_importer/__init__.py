import pathlib
import hashlib
import pathspec


def build_filter(args):
    with open(args) as f:
        lfs_spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, f)
    return Filter(lfs_spec)


class Filter:
    def __init__(self, lfs_spec):
        self.lfs_spec = lfs_spec

    def file_data_filter(self, file_data):
        """
        file_data: {
            'filename': <str>,
            'file_ctx': <mercurial.filectx or None>,
            'data': <bytes or None>,
            'is_largefile': <bool>
        }

        May be called for deletions (data=None, file_ctx=None).
        """
        filename = file_data.get('filename')
        data = file_data.get('data')

        # Skip deletions or filtered files early
        if data is None or not self.lfs_spec.match_file(filename.decode("utf-8")):
            return

        # Get the file path
        sha256hash = hashlib.sha256(data).hexdigest()
        lfs_path = pathlib.Path(f".git/lfs/objects/{sha256hash[0:2]}/{sha256hash[2:4]}")
        lfs_path.mkdir(parents=True, exist_ok=True)
        lfs_file_path = lfs_path / sha256hash

        # The binary blob is already in LFS
        if not lfs_file_path.is_file():
            (lfs_path / sha256hash).write_bytes(data)

        # Write the LFS pointer
        file_data['data'] = (
            f"version https://git-lfs.github.com/spec/v1\n"
            f"oid sha256:{sha256hash}\n"
            f"size {len(data)}\n"
        ).encode("utf-8")
