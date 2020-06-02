"""
Flask app module for gitreload
"""
import json
import logging
import os
from multiprocessing import JoinableQueue, Manager

from flask import Flask, request, Response
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

from gitreload.config import Config, configure_logging
from gitreload.processing import GitAction, ActionCall


log = logging.getLogger('gitreload')  # pylint: disable=C0103
queue = JoinableQueue()  # pylint: disable=C0103
manager = Manager()  # pylint: disable=C0103
queued_jobs = manager.list([])  # pylint: disable=C0103,E1101

app = Flask('gitreload')  # pylint: disable=C0103


def json_dump_msg(message):
    """
    Convert and return message as json dictionary.
    """
    return json.dumps({'msg': message})


def start_workers(num_threads):
    """
    Function to start the import workers
    """
    local_workers = []
    log.debug('Starting up %s worker(s)', num_threads)
    # Create manager for monitoring queue
    for i in range(num_threads):
        worker_thread = GitAction(queue, i, queued_jobs)
        worker_thread.start()
        local_workers.append(worker_thread)
    return local_workers


def verify_hook():
    """
    This will validate the trigger from github by
    checking for the right event type, that the
    repo is on disk, and that the trigger
    is for the current branch
    """
    # If we are just getting pinged, return a nice message
    if request.headers.get('X-Github-Event') == "ping":
        log.debug('Received ping from github')
        return Response(json_dump_msg('pong')), None

    # If we are receiving anything but a push event then we will just
    # cut out early.
    if request.headers.get('X-Github-Event', '') != "push":
        log.info('Received ignored event %s',
                 request.headers.get('X-Github-Event'))
        return Response(json_dump_msg('We do not handle that event')), None

    log.debug('Received push event from github')

    # Gather payload depending on type returned
    if request.json:
        payload = request.json
        log.debug('Received JSON type hook')
    else:
        payload = json.loads(request.form['payload'])
        log.debug('Received form type hook')
    log.debug('Received payload: %s', payload)

    repo_name = payload['repository']['name']
    owner = payload['repository']['owner']
    log.info('Push event from %s repository owned by %s', repo_name, owner)

    # Check that repo is already checked out as that is our method for
    # validating this repo is good to pull.
    if not os.path.isdir(Config.REPODIR):
        log.critical("Repo directory %s doesn't exist", Config.REPODIR)
        return Response(json_dump_msg('Server configuration issue'), 500), None

    # Get GitPython repo object from disk
    try:
        repo = Repo(os.path.join(Config.REPODIR, repo_name))
    except (InvalidGitRepositoryError, NoSuchPathError, ):
        log.critical('Repository %s (%s) not in list of available '
                     'repositories', repo_name, owner)
        return Response(json_dump_msg('Repository not valid'), 500), None

    log.info('Push event came from repo that has already been cloned, '
             'running ')

    try:
        local_branch = repo.active_branch.path
    except TypeError:
        message = 'Unable to get current branch of checked out repo'
        log.exception(message)
        return Response(json_dump_msg(message), 500), None

    # No sense importing course when the current branch hasn't been updated
    if not local_branch == payload['ref']:
        message = "Branch pushed doesn't match local branch, ignoring"
        log.info(message)
        return Response(json_dump_msg(message)), None

    return repo, repo_name


@app.route('/', methods=['POST'])
@app.route('/gitreload', methods=['POST'])
def hook_receive():
    """
    Post hook receive handler. There is some assumpting of
    security outside this app (e.g. basic authentication).

    If that is not available, we would need to at least do some
    sender information like making sure it is a github.com IP.
    """

    return_value, repo_name = verify_hook()
    if not repo_name:
        return return_value

    log.debug('Local and remote branch match, scheduling action')

    # Go ahead and run the git import script. Use simple thread for now
    # to prevent timeouts.
    action = ActionCall(
        repo_name,
        return_value.remotes.origin.url,
        ActionCall.ACTION_TYPES['COURSE_IMPORT']
    )
    queued_jobs.append(action)
    queue.put(action)

    return json_dump_msg('Added course import task to queue. '
                         'Queue size was {0}'.format(len(queued_jobs)))


@app.route('/update', methods=['POST'])
def update_repo():
    """
    Just updates the repo to the latest head of it's
    current branch
    """

    return_value, repo_name = verify_hook()
    if not repo_name:
        return return_value

    log.debug('Local and remote branch match, doing pull')

    # Go ahead and run the git import script. Use simple thread for now
    # to prevent timeouts.
    action = ActionCall(
        repo_name,
        return_value.remotes.origin.url,
        ActionCall.ACTION_TYPES['GET_LATEST']
    )
    queued_jobs.append(action)
    queue.put(action)

    return json_dump_msg('Added git update task to queue. '
                         'Queue size was {0}'.format(len(queued_jobs)))


@app.route('/queue', methods=['GET'])
def get_queue_length():
    """
    Returns the content of the queue in json
    """
    # Format ActionCall to a dictionary for serializing
    job_list = []
    for item in queued_jobs:
        job_list.append({
            'repo_name': item.repo_name,
            'repo_url': item.repo_url,
            'action': item.action_text
        })
    queue_object = {'queue_length': len(queued_jobs), 'queue': job_list}
    return json.dumps(queue_object)


# Application startup configuration
configure_logging()
workers = start_workers(Config.NUM_THREADS)  # pylint: disable=C0103


# Manual startup overrides (e.g. command line or direct run).
def run_web(host='0.0.0.0', port=5000, log_level=None):
    """
    Stub method for running the built in flask application runner
    """
    # Setup configuration
    configure_logging(log_level)
    if app.debug:
        log.critical('Running in debug mode. '
                     'Do not run this way in production')

    log.info('Starting up self running flask application')
    app.run(host=host, port=port)


if __name__ == '__main__':
    app.debug = True
    run_web(log_level=logging.DEBUG)
