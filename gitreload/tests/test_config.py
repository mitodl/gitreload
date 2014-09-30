"""
Unit tests to validate configuration loading
"""
import mock
import os
import unittest

from .base import TEST_ROOT

TEST_NUM_THREADS = 10
TEST_LOG_LEVEL = 'DEBUG'


@mock.patch('gitreload.config.CONFIG_PATHS')
class TestConfiguration(unittest.TestCase):
    """
    Test out configuration defaults, loading json config, etc.
    """
    # pylint: disable=R0904

    DEFAULT_CONFIG_EXPECT = {
        'REPODIR': '/mnt/data/repos',
        'VIRTUAL_ENV': '/edx/app/edxapp/venvs/edxapp',
        'DJANGO_SETTINGS': 'aws',
        'EDX_PLATFORM': '/edx/app/edxapp/edx-platform',
        'LOG_LEVEL': None,
        'LINKED_REPOS': {},
        'ALSO_CLONE_REPOS': {},
        'NUM_THREADS': 1,
    }

    def test_defaults(self, config_path_mock):
        """
        Simply validate that config settings are what we expect above
        """
        config_path_mock.__iter__.return_value = []
        from gitreload.config import get_config
        self.assertEqual(get_config(), self.DEFAULT_CONFIG_EXPECT)

    def test_overrides(self, config_path_mock):
        """
        Load our test config and make sure things are working right
        """
        config_path_mock.__iter__.return_value = [
            os.path.join(TEST_ROOT, 'gr.env.json'),
        ]
        from gitreload.config import get_config
        local_settings = get_config()
        self.assertEqual(local_settings['NUM_THREADS'], TEST_NUM_THREADS)
        self.assertEqual(local_settings['LOG_LEVEL'], TEST_LOG_LEVEL)

    def test_bad_json(self, config_path_mock):
        """
        Load up a bad json file to make sure that we raise and exit
        """
        config_path_mock.__iter__.return_value = [
            os.path.join(TEST_ROOT, 'gr.env.bad.json'),
        ]
        from gitreload.config import get_config
        with self.assertRaisesRegexp(ValueError,
                                     "No JSON object could be decoded"):
            get_config()


class TestLogConfiguration(unittest.TestCase):
    """
    Make sure we are setting up logging like we expect.
    """
    # pylint: disable=R0904

    def test_log_override(self):
        """
        Make sure we can setup logging with our own level
        """
        import logging
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.NOTSET, log_level)

        from gitreload.config import configure_logging
        log_level = configure_logging(logging.INFO)
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)

    @mock.patch.dict('gitreload.config.settings',
                     {'LOG_LEVEL': TEST_LOG_LEVEL})
    def test_config_log_level(self,):
        """
        Patch config and make sure we are setting to it
        """
        import logging
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.NOTSET, log_level)

        from gitreload.config import configure_logging
        log_level = configure_logging()
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, getattr(logging, TEST_LOG_LEVEL))

    @mock.patch.dict('gitreload.config.settings',
                     {'LOG_LEVEL': 'Not a real thing'})
    def test_bad_log_level(self,):
        """
        Set a non-existent log level and make sure we raise properly
        """
        import logging
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.NOTSET, log_level)

        from gitreload.config import configure_logging
        with self.assertRaisesRegexp(ValueError, 'Invalid log level.+'):
            log_level = configure_logging()

    @mock.patch.dict('gitreload.config.settings',
                     {'LOG_LEVEL': None})
    def test_no_log_level(self):
        """
        Make sure we leave things alone if no log level is set.
        """
        import logging
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.NOTSET, log_level)

        from gitreload.config import configure_logging
        log_level = configure_logging()
        self.assertEqual(logging.NOTSET, log_level)

    def test_syslog_devices(self):
        """
        Test syslog address handling and handler
        """
        import logging

        for log_device in ['/dev/log', '/var/run/syslog', '']:
            root_logger = logging.getLogger()
            # Nuke syslog handlers from init
            syslog_handlers = []
            for handler in root_logger.handlers:
                if type(handler) is logging.handlers.SysLogHandler:
                    syslog_handlers.append(handler)
            for handler in syslog_handlers:
                root_logger.removeHandler(handler)

            real_exists = os.path.exists(log_device)

            def mock_effect(*args):
                """Contextual choice of log device."""
                if args[0] == log_device:  # pylint: disable=cell-var-from-loop
                    return True
                return False

            # Call so that it will think /dev/log exists
            with mock.patch('os.path') as os_exists:
                os_exists.exists.side_effect = mock_effect
                from gitreload.config import configure_logging
                if not real_exists and log_device != '':
                    with self.assertRaises(Exception):
                        configure_logging()
                else:
                    configure_logging()
                    syslog_handler = None
                    for handler in root_logger.handlers:
                        if type(handler) is logging.handlers.SysLogHandler:
                            syslog_handler = handler
                    self.assertIsNotNone(syslog_handler)
                    if log_device == '':
                        self.assertEqual(
                            syslog_handler.address, ('127.0.0.1', 514)
                        )
                    else:
                        self.assertEqual(syslog_handler.address, log_device)
