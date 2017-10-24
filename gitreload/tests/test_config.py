"""
Unit tests to validate configuration loading
"""
import logging
import os
import unittest
import mock

TEST_NUM_THREADS = 10
TEST_LOG_LEVEL = 'DEBUG'


class TestLogConfiguration(unittest.TestCase):
    """
    Make sure we are setting up logging like we expect.
    """
    # pylint: disable=R0904

    def setUp(self):
        """
        Set up method
        """
        # reset the log level before each test
        logger = logging.getLogger()
        logger.setLevel(logging.WARNING)

    def test_log_override(self):
        """
        Make sure we can setup logging with our own level
        """
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.WARNING, log_level)

        from gitreload.config import configure_logging
        log_level = configure_logging(logging.INFO)
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)

    @mock.patch('gitreload.config.Config.LOG_LEVEL', TEST_LOG_LEVEL)
    def test_config_log_level(self,):
        """
        Patch config and make sure we are setting to it
        """
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.WARNING, log_level)

        from gitreload.config import configure_logging
        log_level = configure_logging()
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, getattr(logging, TEST_LOG_LEVEL))

    @mock.patch('gitreload.config.Config.LOG_LEVEL', 'Not a real thing')
    def test_bad_log_level(self,):
        """
        Set a non-existent log level and make sure we raise properly
        """
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.WARNING, log_level)

        from gitreload.config import configure_logging
        with self.assertRaisesRegexp(ValueError, 'Invalid log level.+'):
            log_level = configure_logging()

    @mock.patch('gitreload.config.Config.LOG_LEVEL', None)
    def test_no_log_level(self):
        """
        Make sure we leave things alone if no log level is set.
        """
        root_logger = logging.getLogger()
        log_level = root_logger.level
        self.assertEqual(logging.WARNING, log_level)

        from gitreload.config import configure_logging
        log_level = configure_logging()
        self.assertEqual(logging.NOTSET, log_level)

    def test_syslog_devices(self):
        """
        Test syslog address handling and handler
        """

        for log_device in ['/dev/log', '/var/run/syslog', '']:
            root_logger = logging.getLogger()
            # Nuke syslog handlers from init
            syslog_handlers = []
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.SysLogHandler):
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
                        if isinstance(handler, logging.handlers.SysLogHandler):
                            syslog_handler = handler
                    self.assertIsNotNone(syslog_handler)
                    if log_device == '':
                        self.assertEqual(
                            syslog_handler.address, ('127.0.0.1', 514)
                        )
                    else:
                        self.assertEqual(syslog_handler.address, log_device)
