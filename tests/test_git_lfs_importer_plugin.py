import sys

sys.path.append("./plugins")

import hashlib
import pathlib
import time
import unittest
import tempfile
import os
import pathspec

from git_lfs_importer import Filter, build_filter


class TestGitLfsImporterPlugin(unittest.TestCase):
    def setUp(self):
        # create an isolated temp dir and chdir into it for each test
        self._orig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self._tmpdir.name)
        os.chdir(self.tmp_path)

    def tearDown(self):
        # restore cwd and cleanup
        os.chdir(self._orig_cwd)
        self._tmpdir.cleanup()

    def empty_spec(self):
        return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, [])

    # --------------------------------------------------------
    # GIVEN-WHEN-THEN TESTS for Filter.file_data_filter
    # --------------------------------------------------------

    def test_skips_deletions(self):
        flt = Filter(self.empty_spec())
        file_data = {"filename": b"file.txt", "data": None}

        flt.file_data_filter(file_data)

        self.assertIsNone(file_data["data"])
        self.assertFalse((self.tmp_path / ".git").exists())

    def test_skips_files_that_do_not_match_spec(self):
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ["*.bin"])
        flt = Filter(spec)
        original = b"not matched"
        file_data = {"filename": b"file.txt", "data": original}

        flt.file_data_filter(file_data)

        self.assertEqual(file_data["data"], original)
        self.assertFalse((self.tmp_path / ".git").exists())

    def test_converts_only_matched_files_to_lfs_pointer(self):
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ["*.bin"])
        flt = Filter(spec)
        data = b"hello world"
        sha = hashlib.sha256(data).hexdigest()
        expected_pointer = (
            f"version https://git-lfs.github.com/spec/v1\n"
            f"oid sha256:{sha}\n"
            f"size {len(data)}\n"
        ).encode("utf-8")
        file_data = {"filename": b"payload.bin", "data": data}

        flt.file_data_filter(file_data)

        self.assertEqual(file_data["data"], expected_pointer)
        lfs_file = pathlib.Path(".git/lfs/objects") / sha[:2] / sha[2:4] / sha
        self.assertTrue(lfs_file.is_file())
        self.assertEqual(lfs_file.read_bytes(), data)

    def test_does_not_convert_unmatched_directory(self):
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ["assets/**"])
        flt = Filter(spec)
        data = b"outside directory"
        file_data = {"filename": b"src/images/logo.png", "data": data}

        flt.file_data_filter(file_data)

        self.assertEqual(file_data["data"], data)
        self.assertFalse((self.tmp_path / ".git").exists())

    def test_converts_matched_directory(self):
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ["assets/**"])
        flt = Filter(spec)
        data = b"inside directory"
        sha = hashlib.sha256(data).hexdigest()
        file_data = {"filename": b"assets/images/logo.png", "data": data}

        flt.file_data_filter(file_data)

        self.assertIn(b"version https://git-lfs.github.com/spec/v1", file_data["data"])
        lfs_file = pathlib.Path(".git/lfs/objects") / sha[:2] / sha[2:4] / sha
        self.assertTrue(lfs_file.is_file())
        self.assertEqual(lfs_file.read_bytes(), data)

    def test_does_not_overwrite_existing_blob(self):
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ["*.bin"])
        flt = Filter(spec)
        data = b"abc"
        sha = hashlib.sha256(data).hexdigest()
        lfs_dir = pathlib.Path(".git/lfs/objects") / sha[:2] / sha[2:4]
        lfs_dir.mkdir(parents=True, exist_ok=True)
        lfs_file = lfs_dir / sha
        lfs_file.write_bytes(data)
        before_mtime = lfs_file.stat().st_mtime_ns
        time.sleep(0.01)  # Ensure timestamp difference

        file_data = {"filename": b"abc.bin", "data": data}

        flt.file_data_filter(file_data)

        expected_pointer_prefix = b"version https://git-lfs.github.com/spec/v1"
        self.assertTrue(file_data["data"].startswith(expected_pointer_prefix))
        after_mtime = lfs_file.stat().st_mtime_ns
        self.assertEqual(after_mtime, before_mtime)

    def test_empty_file_converted_when_matched(self):
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ["*.bin"])
        flt = Filter(spec)
        data = b""
        sha = hashlib.sha256(data).hexdigest()
        file_data = {"filename": b"empty.bin", "data": data}

        flt.file_data_filter(file_data)

        self.assertIn(b"size 0", file_data["data"])
        lfs_file = pathlib.Path(".git/lfs/objects") / sha[:2] / sha[2:4] / sha
        self.assertTrue(lfs_file.is_file())
        self.assertEqual(lfs_file.read_bytes(), data)

    # --------------------------------------------------------
    # Optional: GIVEN-WHEN-THEN for build_filter
    # --------------------------------------------------------

    def test_build_filter_reads_patterns_file(self):
        patterns_file = self.tmp_path / "lfs_patterns.txt"
        patterns_file.write_text("*.bin\nassets/**\n", encoding="utf-8")

        flt = build_filter(str(patterns_file))

        data_match = b"match me"
        sha_match = hashlib.sha256(data_match).hexdigest()
        fd_match = {"filename": b"assets/payload.bin", "data": data_match}
        flt.file_data_filter(fd_match)
        self.assertIn(b"oid sha256:", fd_match["data"])
        lfs_file = pathlib.Path(".git/lfs/objects") / sha_match[:2] / sha_match[2:4] / sha_match
        self.assertTrue(lfs_file.is_file())

        data_skip = b"skip me"
        fd_skip = {"filename": b"docs/readme.md", "data": data_skip}
        flt.file_data_filter(fd_skip)
        self.assertEqual(fd_skip["data"], data_skip)
