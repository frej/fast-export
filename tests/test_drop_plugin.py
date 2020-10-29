import sys, os, subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase
from pathlib import Path


class CommitDropTest(TestCase):
    def test_drop_single_commit_by_hash(self):
        hash1 = self.create_commit('commit 1')
        self.create_commit('commit 2')

        self.drop(hash1)

        self.assertEqual(['commit 2'], self.git.log())

    def test_drop_commits_by_desc(self):
        self.create_commit('commit 1 is good')
        self.create_commit('commit 2 is bad')
        self.create_commit('commit 3 is good')
        self.create_commit('commit 4 is bad')

        self.drop('.*bad')

        expected = ['commit 1 is good', 'commit 3 is good']
        self.assertEqual(expected, self.git.log())

    def test_drop_sequential_commits_in_single_plugin_instance(self):
        self.create_commit('commit 1')
        hash2 = self.create_commit('commit 2')
        hash3 = self.create_commit('commit 3')
        hash4 = self.create_commit('commit 4')
        self.create_commit('commit 5')

        self.drop(','.join((hash2, hash3, hash4)))

        expected = ['commit 1', 'commit 5']
        self.assertEqual(expected, self.git.log())

    def test_drop_sequential_commits_in_multiple_plugin_instances(self):
        self.create_commit('commit 1')
        hash2 = self.create_commit('commit 2')
        hash3 = self.create_commit('commit 3')
        hash4 = self.create_commit('commit 4')
        self.create_commit('commit 5')

        self.drop(hash2, hash3, hash4)

        expected = ['commit 1', 'commit 5']
        self.assertEqual(expected, self.git.log())

    def test_drop_nonsequential_commits(self):
        self.create_commit('commit 1')
        hash2 = self.create_commit('commit 2')
        self.create_commit('commit 3')
        hash4 = self.create_commit('commit 4')

        self.drop(','.join((hash2, hash4)))

        expected = ['commit 1', 'commit 3']
        self.assertEqual(expected, self.git.log())

    def test_drop_head(self):
        self.create_commit('first')
        self.create_commit('middle')
        hash_last = self.create_commit('last')

        self.drop(hash_last)

        self.assertEqual(['first', 'middle'], self.git.log())

    def test_drop_merge_commit(self):
        initial_hash = self.create_commit('initial')
        self.create_commit('branch A')
        self.hg.checkout(initial_hash)
        self.create_commit('branch B')
        self.hg.merge()
        merge_hash = self.create_commit('merge to drop')
        self.create_commit('last')

        self.drop(merge_hash)

        expected_commits = ['initial', 'branch A', 'branch B', 'last']
        self.assertEqual(expected_commits, self.git.log())
        self.assertEqual(['branch B', 'branch A'], self.git_parents('last'))

    def test_drop_different_commits_in_multiple_plugin_instances(self):
        self.create_commit('good commit')
        bad_hash = self.create_commit('bad commit')
        self.create_commit('awful commit')
        self.create_commit('another good commit')

        self.drop('^awful.*', bad_hash)

        expected = ['good commit', 'another good commit']
        self.assertEqual(expected, self.git.log())

    def test_drop_same_commit_in_multiple_plugin_instances(self):
        self.create_commit('good commit')
        bad_hash = self.create_commit('bad commit')
        self.create_commit('another good commit')

        self.drop('^bad.*', bad_hash)

        expected = ['good commit', 'another good commit']
        self.assertEqual(expected, self.git.log())

    def setUp(self):
        self.tempdir = TemporaryDirectory()

        self.hg = HgDriver(Path(self.tempdir.name) / 'hgrepo')
        self.hg.init()

        self.git = GitDriver(Path(self.tempdir.name) / 'gitrepo')
        self.git.init()

        self.export = ExportDriver(self.hg.repodir, self.git.repodir)

    def tearDown(self):
        self.tempdir.cleanup()

    def create_commit(self, message):
        self.write_file_data('Data for %r.' % message)
        return self.hg.commit(message)

    def write_file_data(self, data, filename='test_file.txt'):
        path = self.hg.repodir / filename
        with path.open('w') as f:
            print(data, file=f)

    def drop(self, *spec):
        self.export.run_with_drop(*spec)

    def git_parents(self, message):
        matches = self.git.grep_log(message)
        if len(matches) != 1:
            raise Exception('No unique commit with message %r.' % message)
        subject, parents = self.git.details(matches[0])
        return [self.git.details(p)[0] for p in parents]


class ExportDriver:
    def __init__(self, sourcedir, targetdir, *, quiet=True):
        self.sourcedir = Path(sourcedir)
        self.targetdir = Path(targetdir)
        self.quiet = quiet
        self.python_executable = str(
            Path.cwd() / os.environ.get('PYTHON', sys.executable))
        self.script = Path(__file__).parent / '../hg-fast-export.sh'

    def run_with_drop(self, *plugin_args):
        cmd = [self.script, '-r', str(self.sourcedir)]
        for arg in plugin_args:
            cmd.extend(['--plugin', 'drop=' + arg])
        output = subprocess.DEVNULL if self.quiet else None
        subprocess.run(cmd, check=True, cwd=str(self.targetdir),
                       env={'PYTHON': self.python_executable},
                       stdout=output, stderr=output)


class HgDriver:
    def __init__(self, repodir):
        self.repodir = Path(repodir)

    def init(self):
        self.repodir.mkdir()
        self.run_command('init')

    def commit(self, message):
        self.run_command('commit', '-A', '-m', message)
        return self.run_command('id', '--id', '--debug').strip()

    def log(self):
        output = self.run_command('log', '-T', '{desc}\n')
        commits = output.strip().splitlines()
        commits.reverse()
        return commits

    def checkout(self, rev):
        self.run_command('checkout', '-r', rev)

    def merge(self):
        self.run_command('merge', '--tool', ':local')

    def run_command(self, *args):
        p = subprocess.run(('hg', '-yq') + args,
                           cwd=str(self.repodir),
                           check=True,
                           text=True,
                           capture_output=True)
        return p.stdout


class GitDriver:
    def __init__(self, repodir):
        self.repodir = Path(repodir)

    def init(self):
        self.repodir.mkdir()
        self.run_command('init')

    def log(self):
        output = self.run_command('log', '--format=%s', '--reverse')
        return output.strip().splitlines()

    def grep_log(self, pattern):
        output = self.run_command('log', '--format=%H',
                                  '-F', '--grep', pattern)
        return output.strip().splitlines()

    def details(self, commit_hash):
        fmt = '%s%n%P'
        output = self.run_command('show', '-s', '--format=' + fmt,
                                  commit_hash)
        subject, parents = output.splitlines()
        return subject, parents.split()

    def run_command(self, *args):
        p = subprocess.run(('git', '--no-pager') + args,
                           cwd=str(self.repodir),
                           check=True,
                           text=True,
                           capture_output=True)
        return p.stdout
