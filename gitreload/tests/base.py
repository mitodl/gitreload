"""
Define a base classes for testing
"""
# pylint: disable=import-outside-toplevel
import os
from multiprocessing import JoinableQueue
import unittest

TEST_ROOT = os.path.join(os.path.dirname(__file__), 'data')


class GitreloadTestBase(unittest.TestCase):
    """
    Base class for common functionality needed across modules to be
    tested.
    """
    # pylint: disable=R0904

    def setUp(self):
        """
        Terminate any worker processes that may be running as a side
        effect of startup.
        """
        import gitreload.web
        self._stop_workers(gitreload.web.workers)

    def _stop_workers(self, workers):
        """
        This will stop an array of workers
        and assert they are dead.
        """
        for worker in workers:
            worker.terminate()
            worker.join()
        # asser that they are dead
        for worker in workers:
            self.assertFalse(worker.is_alive())
        # Recreate queue to correct corruption from terminate()
        import gitreload.web
        gitreload.web.queue = JoinableQueue()
