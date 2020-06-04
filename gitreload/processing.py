"""
Module for handling the actual processing of requests and
incluydes the workers and import task.
"""

import logging
import multiprocessing
import os
import subprocess

from git import Repo

from gitreload import config

log = logging.getLogger('gitreload')  # pylint: disable=C0103


def import_repo(action_call):
    """
    Import the repository course into the configured edx-platform
    installation.
    """
    os.environ['SERVICE_VARIANT'] = 'lms'
    os.environ['LMS_CFG'] = config.Config.DJANGO_SETTINGS
    cmd = [
        '{0}/bin/python'.format(config.Config.VIRTUAL_ENV),
        'manage.py',
        'lms',
        '--settings={0}'.format(config.Config.DJANGO_SETTINGS),
        'git_add_course',
        action_call.repo_url,
        '--directory_path',
        os.path.join(config.Config.REPODIR, action_call.repo_name),
    ]

    log.info('Beginning import of course repo %s with command %s',
             action_call.repo_name, ' '.join(cmd))
    try:
        import_process = subprocess.check_output(
            cmd,
            cwd=config.Config.EDX_PLATFORM,
            stderr=subprocess.STDOUT,
            timeout=config.Config.SUBPROCESS_TIMEOUT,
        )
    except subprocess.CalledProcessError as exc:
        log.exception('Import command failed with: %s', exc.output)
    except subprocess.TimeoutExpired as exc:
        log.exception('Import command timed out after %s seconds with: %s', exc.timeout, exc.output)
    except OSError as ex:
        log.exception('System or configuration error occurred: %s', str(ex))
    else:
        log.info('Import complete, command output was: %s', import_process)


def git_get_latest(action_call):
    """
    Performs a `git fetch origin`, `git clean -df`,
    and `git reset --hard origin/<repo_branch>`
    on the passed in repo.
    """
    repo = Repo(os.path.join(config.Config.REPODIR, action_call.repo_name))
    # Grab HEAD sha to see if we actually are updating
    orig_head = repo.head.commit.tree.hexsha
    repo.git.fetch('--all')
    repo.head.reset(
        index=True, working_tree=True,
        commit='origin/{0}'.format(repo.git.rev_parse('--abbrev-ref', 'HEAD'))
    )
    repo.git.clean('-xdf')
    new_head = repo.head.commit.tree.hexsha
    if new_head == orig_head:
        log.warning('Attempted update of %s at HEAD %s, but no updates',
                    action_call.repo_name, orig_head)
    else:
        log.info('Updated to latest revision of repo %s. '
                 'Original SHA: %s. Head SHA: %s',
                 action_call.repo_name, orig_head, new_head)


class InvalidGitActionException(Exception):
    """
    Catachable exception for when an invalid
    action is requested in init.
    """


class ActionCall:
    """
    Class structure for passing to processing queue
    """
    ACTION_TYPES = {
        'COURSE_IMPORT': 0,
        'GET_LATEST': 1,
    }

    def __init__(
            self,
            repo_name,
            repo_url,
            action_type,
            **kwargs
    ):
        """Setup class for use in worker"""
        self.repo_name = repo_name
        self.repo_url = repo_url

        if action_type not in list(self.ACTION_TYPES.values()):
            raise InvalidGitActionException(
                'Action must be in ActionCall.ACTION_TYPES'
            )
        self.action_type = action_type
        self.kwargs = kwargs

    @property
    def action_text(self):
        """
        Get the text representation of the action
        """
        action_type = [key for key, value in list(self.ACTION_TYPES.items())
                       if value == self.action_type]
        return action_type[0]

    def __repr__(self):
        """
        String representation of class for use in logs and such
        """
        return ('repo_name: {0.repo_name}, repo_url: {0.repo_url}, '
                'action_type: {0.action_text}, kwargs: {0.kwargs}'.format(
                    self
                ))


class GitAction(multiprocessing.Process):
    """
    Simple queue worker thread. Runs import_repo
    one at a time as they come in using the queue
    """

    EXIT_CODE = 9

    ACTION_COMMANDS = (
        import_repo,
        git_get_latest,
    )

    def __init__(self, queue, thread_num, queued_jobs):
        """
        Build class with needed information to work the queue
        """
        super(GitAction, self).__init__()
        # Make daemon thread so we exit when the program exits
        self.daemon = True

        self.queue = queue
        self.queued_jobs = queued_jobs
        self.thread_num = thread_num

    def run(self):  # pragma: no cover due to multiprocessing
        """
        Infinite queue loop waiting for repos to import
        """
        while True:
            action_call = self.queue.get()
            log.info(
                'Starting GitAction task %s out of %s on thread %s',
                action_call,
                len(self.queued_jobs),
                self.thread_num
            )
            try:
                log.debug('Used %s as index to ACTION_COMMANDS',
                          action_call.action_type)
                self.ACTION_COMMANDS[action_call.action_type](action_call)
            except Exception:  # pylint: disable=W0703
                log.exception('Failed to run command GitAction')
            finally:
                self.queued_jobs.pop()
                self.queue.task_done()
