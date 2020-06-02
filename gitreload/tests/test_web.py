"""
Test out the flask Web application
"""
# pylint: disable=import-outside-toplevel
import json
import os
import shutil
import tempfile

import mock
from git import Repo

import gitreload.web
from gitreload.tests.base import GitreloadTestBase


class TestWebApplication(GitreloadTestBase):
    """
    Tests for excercising the flask application
    """
    # pylint: disable=e1103,r0904

    HOOK_COURSE_URL = '/'
    HOOK_GET_LATEST_URL = '/update'
    QUEUE_URL = '/queue'

    def setUp(self):
        """
        grab application test client
        """
        super(TestWebApplication, self).setUp()
        # pylint:  disable=C0103
        self.client = gitreload.web.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)

    @classmethod
    def _make_payload(cls, repo_name, branch='master'):
        """
        This will return a gitreload parseable subset of a full
        github payload.
        """
        return json.dumps({
            'ref': 'refs/heads/{0}'.format(branch),
            'repository': {
                'name': repo_name,
                'owner': {
                    "name": "testuser",
                    "email": "testuser@example.com",
                },
            },
        })

    @classmethod
    def get_json_msg(cls, json_string):
        """
        Pulls out the msg term in json dict
        """
        return json.loads(json_string)['msg']

    def _make_repo(self, name):
        """
        Create a course like repo that gets nuked on teardown
        """
        repo = Repo.init(os.path.join(self.tmpdir, name), bare=False)
        repo.create_remote('origin', 'http://example.com/test/test.git')
        return repo

    def test_json_response(self):
        """
        Make sure we are getting the json we expect
        """
        from gitreload.web import json_dump_msg
        json_dump = json_dump_msg('Test')
        self.assertEqual(json.loads(json_dump), {'msg':  'Test'})

    def test_queue_status_page(self):
        """
        Make sure the queue status page is working.
        """
        from gitreload.processing import ActionCall

        response = self.client.get(self.QUEUE_URL)
        self.assertEqual(response.status_code, 200)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['queue_length'], 0)

        # Add an action call item and make sure it comes through
        queued_jobs = gitreload.web.queued_jobs
        queued_jobs.append(ActionCall(
            'testing',
            'http://example.com/testing.git',
            ActionCall.ACTION_TYPES['COURSE_IMPORT']
        ))
        response = self.client.get(self.QUEUE_URL)
        json_data = json.loads(response.data)
        self.assertEqual(json_data['queue_length'], 1)
        self.assertEqual(
            json_data['queue'],
            [{
                'repo_name': 'testing',
                'repo_url': 'http://example.com/testing.git',
                'action': 'COURSE_IMPORT'
            }])
        # Clean up queue
        queued_jobs.pop()

    def test_hook_only_post(self):
        """
        Test various methods to make sure we only respond on POST
        """
        self.assertEqual(
            self.client.get(self.HOOK_COURSE_URL).status_code, 405
        )
        self.assertEqual(
            self.client.delete(self.HOOK_COURSE_URL).status_code, 405
        )
        self.assertEqual(
            self.client.head(self.HOOK_COURSE_URL).status_code, 405
        )
        self.assertNotEqual(
            self.client.post(self.HOOK_COURSE_URL).status_code, 405
        )

    def test_git_ping(self):
        """
        Send a simulated github ping request and expect pong.
        """
        response = self.client.post(self.HOOK_COURSE_URL,
                                    headers={'X-Github-Event': 'ping'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_json_msg(response.data), 'pong')

    def test_bad_event(self):
        """
        Send a unhandled (not push) event to make sure we handle them well.
        """
        response = self.client.post(self.HOOK_COURSE_URL,
                                    headers={'X-Github-Event': 'explode'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_json_msg(response.data),
                         'We do not handle that event')

    def test_bad_push(self):
        """
        I don't really care about handling bad push dictionaries nicely,
        test that out here.
        """
        response = self.client.post(self.HOOK_COURSE_URL,
                                    data={'payload': 'what'},
                                    headers={'X-Github-Event': 'push'})
        self.assertEqual(response.status_code, 500)

    @mock.patch('gitreload.config.Config.REPODIR', '/dev/null')
    def test_bad_repodir(self):
        """
        Test that a bad repodir is handled right
        """
        response = self.client.post(
            self.HOOK_COURSE_URL,
            data={'payload': self._make_payload('test')},
            headers={'X-Github-Event': 'push'}
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.get_json_msg(response.data),
                         'Server configuration issue')

    def test_missing_repo(self):
        """
        Test to confirm that we don't want to clone repos that haven't
        already been checked out.
        """
        with mock.patch('gitreload.config.Config.REPODIR', self.tmpdir):
            response = self.client.post(
                self.HOOK_COURSE_URL,
                data={
                    'payload': self._make_payload('notathing')
                },
                headers={'X-Github-Event': 'push'}
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            self.get_json_msg(response.data),
            "Repository not valid"
        )

    def test_bad_repo_state(self):
        """
        Move repo to headless state and make sure we handle that well.
        """
        test_file = 'text.txt'
        repo = self._make_repo('test')

        with open(os.path.join(repo.working_dir, test_file), 'w') as test_f:
            test_f.write('Hello')
        repo.index.add([test_file])
        commit = repo.index.commit('test commit')
        repo.git.checkout(commit.hexsha)

        with mock.patch('gitreload.config.Config.REPODIR', self.tmpdir):
            response = self.client.post(
                self.HOOK_COURSE_URL,
                data={
                    'payload': self._make_payload('test')
                },
                headers={'X-Github-Event': 'push'}
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            self.get_json_msg(response.data),
            "Unable to get current branch of checked out repo"
        )

    def test_wrong_branch(self):
        """
        Fire event to the wrong branch to make sure we ignore it.
        """
        repo_name = 'test'
        self._make_repo(repo_name)

        with mock.patch('gitreload.config.Config.REPODIR', self.tmpdir):
            response = self.client.post(
                self.HOOK_COURSE_URL,
                data={
                    'payload': self._make_payload(repo_name, 'feature_branch')
                },
                headers={'X-Github-Event': 'push'}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_json_msg(response.data),
                         "Branch pushed doesn't match local branch, ignoring")

    def test_queue_put(self):
        """
        Send correct request with right branch and make sure the queue
        picks it up.
        """
        repo_name = 'test'
        self._make_repo(repo_name)

        self.assertEqual(len(gitreload.web.queued_jobs), 0)

        with mock.patch('gitreload.config.Config.REPODIR', self.tmpdir):
            response = self.client.post(
                self.HOOK_COURSE_URL,
                data={
                    'payload': self._make_payload(repo_name, 'master')
                },
                headers={'X-Github-Event': 'push'}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_json_msg(response.data),
                         'Added course import task to queue. Queue size was 1')

        # Make sure queue has item and then "process" it
        self.assertEqual(len(gitreload.web.queued_jobs), 1)
        # Go ahead and timeout in case the test is bad
        gitreload.web.queue.get(timeout=1)
        gitreload.web.queued_jobs.pop()
        gitreload.web.queue.task_done()
        self.assertEqual(len(gitreload.web.queued_jobs), 0)

    def test_full_json_content_type(self):
        """
        Test that a request sent as json type is handled along with form
        type
        """
        repo_name = 'test'
        self._make_repo(repo_name)

        self.assertEqual(len(gitreload.web.queued_jobs), 0)

        with mock.patch('gitreload.config.Config.REPODIR', self.tmpdir):
            response = self.client.post(
                self.HOOK_COURSE_URL,
                data=self._make_payload(repo_name, 'master'),
                headers={
                    'X-Github-Event': 'push',
                    'Content-Type': 'application/json'
                }
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_json_msg(response.data),
                         'Added course import task to queue. Queue size was 1')

        # Make sure queue has item and then "process" it
        self.assertEqual(len(gitreload.web.queued_jobs), 1)
        # Go ahead and timeout in case the test is bad
        gitreload.web.queue.get(timeout=1)
        gitreload.web.queued_jobs.pop()
        gitreload.web.queue.task_done()
        self.assertEqual(len(gitreload.web.queued_jobs), 0)

        response = self.client.post(
            self.HOOK_COURSE_URL,
            data=self._make_payload('test'),
            headers={
                'X-Github-Event': 'push',
                'Content-Type': 'application/json'
            }
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.get_json_msg(response.data),
                         'Server configuration issue')

    def test_update_repo(self):
        """
        Send correct request with right branch and make sure the queue
        picks it up.
        """
        repo_name = 'test'
        self._make_repo(repo_name)

        self.assertEqual(len(gitreload.web.queued_jobs), 0)

        with mock.patch('gitreload.config.Config.REPODIR', self.tmpdir):
            response = self.client.post(
                self.HOOK_GET_LATEST_URL,
                data={
                    'payload': self._make_payload(repo_name, 'master')
                },
                headers={'X-Github-Event': 'push'}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_json_msg(response.data),
                         'Added git update task to queue. Queue size was 1')

        # Make sure queue has item and then "process" it
        self.assertEqual(len(gitreload.web.queued_jobs), 1)
        # Go ahead and timeout in case the test is bad
        gitreload.web.queue.get(timeout=1)
        gitreload.web.queued_jobs.pop()
        gitreload.web.queue.task_done()

    def test_update_verified(self):
        """
        Validate with simple test that update is protected
        by same git hook validation code that course import is.
        """
        with mock.patch('gitreload.config.Config.REPODIR', self.tmpdir):
            response = self.client.post(
                self.HOOK_GET_LATEST_URL,
                data={
                    'payload': self._make_payload('notathing')
                },
                headers={'X-Github-Event': 'push'}
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            self.get_json_msg(response.data),
            "Repository not valid"
        )
