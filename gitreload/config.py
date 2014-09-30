"""
Setup configuration from a json file with defaults
"""
import json
import logging
from logging.handlers import SysLogHandler
import os
import platform

log = logging.getLogger('gitreload')  # pylint: disable=C0103

CONFIG_PATHS = [
    os.environ.get('GITRELOAD_CONFIG', ''),
    os.path.join(os.getcwd(), 'gr.env.json'),
    os.path.join(os.path.expanduser('~'), '.gr.env.json'),
    '/etc/gr.env.json',
]


def configure_logging(level_override=None):
    """
    Set the log level for the application
    """

    # Set up format for default logging
    hostname = platform.node().split('.')[0]
    formatter = ('%(asctime)s %(levelname)s %(process)d [%(name)s] '
                 '%(filename)s:%(lineno)d - '
                 '{hostname}- %(message)s').format(hostname=hostname)

    set_level = level_override

    # Grab config from settings if set, else allow system/language
    # defaults.
    config_log_level = settings.get('LOG_LEVEL', None)
    config_log_int = None

    if config_log_level and not set_level:
        config_log_int = getattr(logging, config_log_level.upper(), None)
        if not isinstance(config_log_int, int):
            raise ValueError('Invalid log level: {0}'.format(config_log_level))
        set_level = config_log_int

    # Set to NotSet if we still aren't set yet
    if not set_level:
        set_level = config_log_int = logging.NOTSET

    # Setup logging with format and level (do setup incase we are
    # main, or change root logger if we aren't.
    logging.basicConfig(level=level_override, format=formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(set_level)

    address = None
    if os.path.exists('/dev/log'):
        address = '/dev/log'
    elif os.path.exists('/var/run/syslog'):
        address = '/var/run/syslog'
    else:
        address = ('127.0.0.1', 514)
    # Add syslog handler before adding formatters
    root_logger.addHandler(
        SysLogHandler(address=address, facility=SysLogHandler.LOG_LOCAL0)
    )

    for handler in root_logger.handlers:
        handler.setFormatter(logging.Formatter(formatter))

    return config_log_int


def get_config():
    """
    Find and load the configuration file values
    """
    conf = {}
    config_file = None
    config = {}

    for conf_path in CONFIG_PATHS:
        if os.path.isfile(conf_path):
            config_file = conf_path
            break
    if config_file:
        with open(config_file) as env_file:
            conf = json.load(env_file)

    config['REPODIR'] = conf.get(
        'REPODIR',
        '/mnt/data/repos'
    )
    config['VIRTUAL_ENV'] = conf.get(
        'VIRTUAL_ENV',
        '/edx/app/edxapp/venvs/edxapp'
    )
    config['DJANGO_SETTINGS'] = conf.get(
        'DJANGO_SETTINGS',
        'aws'
    )
    config['EDX_PLATFORM'] = conf.get(
        'EDX_PLATFORM',
        '/edx/app/edxapp/edx-platform'
    )
    config['LOG_LEVEL'] = conf.get(
        'LOG_LEVEL',
        None
    )
    config['LINKED_REPOS'] = conf.get('LINKED_REPOS', {})
    config['ALSO_CLONE_REPOS'] = conf.get('ALSO_CLONE_REPOS', {})
    config['NUM_THREADS'] = int(conf.get('NUM_THREADS', 1))

    return config

settings = get_config()  # pylint: disable=C0103
