# Copyright (C) 2023 DNEG - All Rights Reserved.
# pylint:disable=unused-argument,import-outside-toplevel
"""Pytest config fixtures and Base classes."""
import logging
import os
import unittest

import pytest

class BaseUnitTestClass(unittest.TestCase):
    """Test wrapper class to set up and tear down test.

    Purpose of this is to save duplicate coding in any tests that might use a
    test case class. Sub-class from "BaseUnitTestClass"

    You can use the create_patch() method from this class to create your mocked
    objects.

    If testing a PySide2 UI tool, pass in True to use_ui argument to set up
    class for testing with a UI.

    See link below to see where this comes from and it's use case.
    http://stash/projects/RNDVP/repos/unrealdevoptools/browse/ue_devop_tools/tests/test_pv_project_validator.py#31

    Args:
        unittest (unittest.TestCase): unit test class decorator.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the class."""
        super().__init__(*args, **kwargs)
        self._caplog = None
        self._monkeypatch = None
        self.patcher = None
        self.mocked_maya_main_window = None
        self.mocked_window_func = None
        self.mocked_dock_control = None
        self.mocked_delete_ui = None
        self.tool_object = None

    def create_patch(self, name: str, **kwargs):
        """Create a patch and automatically ensure that it gets cleaned up after use.

        Args:
            name (str): The module address of what we are patching.
            **kwargs (Any): keyworded arguments to forward.

        Returns:
            unittest.mock.MagicMock: The generated mock object that was patched.
        """
        self.patcher = unittest.mock.patch(name, **kwargs)
        mocked = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        return mocked

    @pytest.fixture(autouse=True)
    def inject_capture_logging(self, caplog, logging_level=logging.CRITICAL):
        """Inject caplog into the test case to enable asserting logs.

        Args:
            caplog (fixture): pytest fixture to capture log output.
            logging_level(LogLevel): Defaults to logging.CRITICAL.
        """
        self._caplog = caplog
        caplog.set_level(logging_level)

    @pytest.fixture
    def inject_monkeypatch(self, monkeypatch):
        """Inject monkeypatch.

        Args:
            monkeypatch (fixture): A fixture to mock functions.
        """
        self._monkeypatch = monkeypatch

    def find_log_message(self, log_message, log_level=logging.CRITICAL):
        """Search for log message in log records.

        Args:
            log_message (str): Log message to search for.
            log_level (int): Logger level to search message in.

        Returns:
            bool: Return True if log_message was found in log records.
                Otherwise, False.
        """
        log_record = self._caplog.get_records("call")
        for log in log_record:
            if log.levelno == log_level:
                if log_message in log.getMessage():
                    return True

        return False

    def tearDown(self):
        """Close tool's ui object if created."""
        if self.tool_object is not None:
            self.tool_object.close()
