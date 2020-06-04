"""
Setup configuration from a json file with defaults
"""
import logging
import os
import platform
from logging.handlers import RotatingFileHandler
from pathlib import Path

log = logging.getLogger('gitreload')  # pylint: disable=C0103

MINUTE = 60  # seconds


class Config:
    """
    Configuration for the app
    """
    REPODIR = os.environ.get('REPODIR', '/mnt/data/repos')
    VIRTUAL_ENV = os.environ.get('VIRTUAL_ENV', '/edx/app/edxapp/venvs/edxapp')
    DJANGO_SETTINGS = os.environ.get('DJANGO_SETTINGS', 'production')
    EDX_PLATFORM = os.environ.get('EDX_PLATFORM', '/edx/app/edxapp/edx-platform')
    LINKED_REPOS = os.environ.get('LINKED_REPOS', {})
    ALSO_CLONE_REPOS = os.environ.get('ALSO_CLONE_REPOS', {})
    NUM_THREADS = int(os.environ.get('NUM_THREADS', 1))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', None)
    HOSTNAME = platform.node().split('.')[0]
    LOG_FORMATTER = ('%(asctime)s %(levelname)s %(process)d [%(name)s] '
                     '%(filename)s:%(lineno)d - '
                     '{hostname}- %(message)s').format(hostname=HOSTNAME)
    LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH', '')
    SUBPROCESS_TIMEOUT = int(os.environ.get('SUBPROCESS_TIMEOUT_MINUTES', 60)) * MINUTE


def configure_logging(level_override=None, config=Config):
    """
    Set the log level for the application
    """

    set_level = level_override

    # Grab config from settings if set, else allow system/language defaults.
    config_log_level = config.LOG_LEVEL
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
    logging.basicConfig(level=level_override, format=config.LOG_FORMATTER)
    root_logger = logging.getLogger()
    root_logger.setLevel(set_level)

    address = None
    if config.LOG_FILE_PATH:
        address = config.LOG_FILE_PATH
    elif Path('/dev/log').is_file():
        address = '/dev/log'

    if address:
        root_logger.addHandler(
            RotatingFileHandler(address, maxBytes=1048576, backupCount=10)
        )

    for handler in root_logger.handlers:
        handler.setFormatter(logging.Formatter(config.LOG_FORMATTER))

    return config_log_int
