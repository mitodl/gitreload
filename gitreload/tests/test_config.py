"""
Unit tests to validate configuration loading
"""
# pylint: disable=import-outside-toplevel

import logging
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
        with self.assertRaisesRegex(ValueError, 'Invalid log level.+'):
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
