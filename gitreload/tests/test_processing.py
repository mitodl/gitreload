"""
Tests related to the processing module
"""
# pylint: disable=import-outside-toplevel
import os
import shutil
import subprocess
import mock

from git import Repo

from gitreload.tests.base import GitreloadTestBase, TEST_ROOT


class TestProcessing(GitreloadTestBase):
    """
    Test doing imports and the workers
    """
    # pylint: disable=R0904

    def make_bare_repo(self, repo_name):
        """
        Make a local bare repo suitable.
        """
        # Build out local bare repo, and set course git url to it
        repo_dir = os.path.join(TEST_ROOT, repo_name)
        os.mkdir(repo_dir)
        self.addCleanup(shutil.rmtree, repo_dir)

        bare_repo_dir = '{0}/{1}.git'.format(
            TEST_ROOT,
            repo_name
        )
        os.mkdir(bare_repo_dir)
        self.addCleanup(shutil.rmtree, bare_repo_dir)

        repo = Repo.init(bare_repo_dir, bare=True)
        cloned_repo = repo.clone(repo_dir)

        return cloned_repo

    @mock.patch('gitreload.processing.log')
    def test_import_failure(self, mocked_logging):
        """
        Run an import with bad settings to make sure
        we log and continue so the worker is ready to go again
        """
        # pylint: disable=R0201

        from gitreload.processing import import_repo, ActionCall

        # Call with bad edx-platform path to prevent actual execution
        with mock.patch('gitreload.config.Config.EDX_PLATFORM', '/dev/null'):
            import_repo(ActionCall(
                'NOTREAL', 'NOTREAL',
                ActionCall.ACTION_TYPES['COURSE_IMPORT']
            ))
        mocked_logging.exception.assert_called_with(
            'System or configuration error occurred: %s',
            "[Errno 20] Not a directory: '/dev/null'"
        )

    @mock.patch('gitreload.processing.log')
    def test_command_error_and_input(self, mocked_logging):
        """
        Make sure that if we do have a real command that we get called as
        expected and when it returns errors we grab them and log them
        """
        # pylint: disable=R0201

        from gitreload.processing import import_repo, ActionCall

        # Setup default settings, have mock get called on import,
        # check parameters, and have side_effect raise the right Exception
        with mock.patch('gitreload.config.Config') as mock_config:
            mock_config.configure_mock(
                **{
                    'REPODIR': '/mnt/data/repos',
                    'VIRTUAL_ENV': '/edx/app/edxapp/venvs/edxapp',
                    'DJANGO_SETTINGS': 'aws',
                    'EDX_PLATFORM': '/edx/app/edxapp/edx-platform',
                    'LOG_LEVEL': None,
                    'LINKED_REPOS': {},
                    'ALSO_CLONE_REPOS': {},
                    'NUM_THREADS': 1,
                    'SUBPROCESS_TIMEOUT': 59,
                }
            )
            with mock.patch('subprocess.check_output') as check_output:
                check_output.side_effect = subprocess.CalledProcessError(
                    10, 'test_command', output='Test output'
                )
                import_repo(ActionCall(
                    'NOTREAL', 'NOTREAL',
                    ActionCall.ACTION_TYPES['COURSE_IMPORT']
                ))
                check_output.assert_called_with(
                    ['/edx/app/edxapp/venvs/edxapp/bin/python',
                     'manage.py',
                     'lms',
                     '--settings=aws',
                     'git_add_course',
                     'NOTREAL',
                     '--directory_path',
                     '/mnt/data/repos/NOTREAL'],
                    cwd='/edx/app/edxapp/edx-platform',
                    stderr=-2,
                    timeout=59,
                )

        mocked_logging.exception.assert_called_with(
            'Import command failed with: %s',
            'Test output'
        )

    @mock.patch('gitreload.processing.log')
    def test_command_success(self, mocked_logging):
        """
        Make sure that if we do have a real command that
        when it returns errors we grab them and log them
        """
        # pylint: disable=R0201

        from gitreload.processing import import_repo, ActionCall

        # Have mock get called on import and check parameters and have
        # return raise the right Exception
        with mock.patch('subprocess.check_output') as check_output:
            check_output.return_value = "Test Success"
            import_repo(ActionCall(
                'NOTREAL', 'NOTREAL',
                ActionCall.ACTION_TYPES['COURSE_IMPORT']
            ))

        mocked_logging.info.assert_called_with(
            'Import complete, command output was: %s',
            'Test Success'
        )

    @mock.patch('gitreload.processing.log')
    def test_import_timeout(self, mocked_logging):
        """
        Run an import that raises a timeout
        """
        # pylint: disable=R0201

        from gitreload.processing import import_repo, ActionCall

        # Call with bad edx-platform path to prevent actual execution
        with mock.patch('subprocess.check_output') as check_output:
            check_output.side_effect = subprocess.TimeoutExpired(cmd='ls', output='foooo', timeout=39)
            import_repo(ActionCall(
                'NOTREAL', 'NOTREAL',
                ActionCall.ACTION_TYPES['COURSE_IMPORT']
            ))
        mocked_logging.exception.assert_called_with(
            'Import command timed out after %s seconds with: %s', 39, 'foooo')

    def test_worker_count_and_stop(self):
        """
        Make sure the number of workers started is properly configurable.
        """

        from gitreload.web import start_workers

        workers = start_workers(1)
        self.assertEqual(len(workers), 1)
        self._stop_workers(workers)

        workers = start_workers(5)
        self.assertEqual(len(workers), 5)
        self._stop_workers(workers)

    @mock.patch('gitreload.processing.GitAction.ACTION_COMMANDS')
    def test_queue_workers(self, mocked_import_repo):
        """
        Create workers and submit a task to the queue
        to verify that we are working it.
        """

        from gitreload.processing import ActionCall
        import gitreload.web
        from gitreload.web import start_workers

        test_file = os.path.join(TEST_ROOT, 'test_queue_workers')
        self.addCleanup(os.remove, test_file)

        queue = gitreload.web.queue
        queued_jobs = gitreload.web.queued_jobs
        self.assertEqual(len(queued_jobs), 0)

        action_call = ActionCall(
            'NOTREAL', 'NOTREAL',
            ActionCall.ACTION_TYPES['COURSE_IMPORT']
        )
        queued_jobs.append(action_call)
        queue.put(action_call)
        self.assertEqual(len(queued_jobs), 1)

        self.assertFalse(os.path.isfile(test_file))

        # We have to use a side_effect instead of called
        # because mock doesn't handle multiprocessing well
        # and always states it isn't called when it is
        def mock_effect(*args):  # pragma: no cover due to multiprocessing
            """Write out a file with args on call"""
            with open(test_file, 'w') as arg_file:
                arg_file.write(str(args))
        mocked_import_repo[0].side_effect = mock_effect

        # Fire up the worker to process the queue
        workers = start_workers(1)

        # Wait for item to be processed
        while len(queued_jobs) > 0:  # pylint: disable=len-as-condition
            pass

        # Assert that our side effect worked and was called
        # with the right args
        self.assertTrue(os.path.isfile(test_file))
        with open(test_file, 'r') as arg_file:
            args = arg_file.read()
        self.assertEqual(
            args,
            ('(repo_name: NOTREAL, repo_url: NOTREAL, '
             'action_type: COURSE_IMPORT, kwargs: {},)')
        )
        self._stop_workers(workers)

    def test_invalid_action_call(self):
        """
        Test invalid setup to action call
        """
        from gitreload.processing import ActionCall, InvalidGitActionException

        with self.assertRaises(InvalidGitActionException):
            ActionCall('a', 'b', 'NOTREAL')

    def test_action_call_repr(self):
        """
        Verify ActionCall repr works as expected
        """
        from gitreload.processing import ActionCall
        action_call = ActionCall(
            'a', 'b',
            ActionCall.ACTION_TYPES['COURSE_IMPORT'],
            a='b', b='c'
        )
        self.assertEqual(
            str(action_call),
            ("repo_name: a, repo_url: b, "
             "action_type: COURSE_IMPORT, kwargs: {'a': 'b', 'b': 'c'}")
        )

    @mock.patch('gitreload.processing.log')
    def test_git_get_latest(self, mocked_log):
        """
        Make real repo and validate we can get the newest version
        """
        from gitreload.processing import git_get_latest, ActionCall
        repo_name = 'testit'
        repo = self.make_bare_repo(repo_name)

        # Make a test file and first commit
        test_file = os.path.join(repo.working_tree_dir, 'test.txt')
        open(test_file, 'a').close()
        repo.index.add([test_file])
        repo.index.commit('First Commit')
        repo.git.push('origin', 'master')

        action_call = ActionCall(
            repo_name,
            repo.remotes.origin.url,
            ActionCall.ACTION_TYPES['GET_LATEST']
        )

        with mock.patch('gitreload.config.Config.REPODIR', TEST_ROOT):
            git_get_latest(action_call)

        mocked_log.warning.assert_called_with(
            'Attempted update of %s at HEAD %s, but no updates',
            repo_name, repo.head.commit.tree.hexsha
        )

        # Make a new commit elsewhere, slide the commit back one and make sure
        # we can actually update
        orig_head = repo.head.commit.tree.hexsha
        test_file = os.path.join(repo.working_tree_dir, 'test1.txt')
        open(test_file, 'a').close()
        repo.index.add([test_file])
        repo.index.commit('Second Commit')
        repo.remotes.origin.push()

        repo.head.reset(index=True, commit='HEAD~1', working_tree=True)
        with mock.patch('gitreload.config.Config.REPODIR', TEST_ROOT):
            git_get_latest(action_call)
        mocked_log.info.assert_called_with(
            'Updated to latest revision of repo %s. Original SHA: %s. Head SHA: %s',
            repo_name, orig_head, repo.head.commit.tree.hexsha
        )
