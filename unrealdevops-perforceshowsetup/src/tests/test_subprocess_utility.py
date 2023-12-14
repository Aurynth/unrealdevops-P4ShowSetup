# pylint: disable=W0212
"""Unit tests for the subprocess utility module."""
import pytest

from shared import subprocess_utility as test_target


def test_silent_subprocess(mocker):
    """Test that trigger_subprocess performs the correct calls."""
    mocked_function = mocker.patch(
        "src.shared.subprocess_utility.trigger_subprocess",
        wraps=test_target.trigger_subprocess,
    )
    mocked_subprocess = mocker.patch(
        "src.shared.subprocess_utility.subprocess.check_output",
        return_value=b"test\r\n",
    )

    # Test that the system correctly triggers a simple subprocess
    (success, response) = test_target.trigger_subprocess("echo test")
    mocked_function.assert_called_once()
    mocked_subprocess.assert_called_once()
    assert success is True
    assert response == "test"

    # Reset things.
    mocked_function.reset_mock()
    mocked_subprocess.reset_mock()

    # Add a failure side-effect to mimic a broken process
    mocked_subprocess.side_effect = test_target.subprocess.CalledProcessError(
        -1, "fail"
    )

    (success, response) = test_target.trigger_subprocess("echo test")
    mocked_function.assert_called_once()
    mocked_subprocess.assert_called_once()
    assert success is False
    assert response.args[0] == -1


def test_verbose_subprocess(mocker):
    """Test that trigger_subprocess_with_output performs the correct calls."""
    mocked_function = mocker.patch(
        "src.shared.subprocess_utility.trigger_subprocess_with_output",
        wraps=test_target.trigger_subprocess_with_output,
    )
    mocked_subprocess = mocker.patch(
        "src.shared.subprocess_utility.subprocess.Popen",
        wraps=test_target.subprocess.Popen,
    )

    # Test that the system correctly triggers a simple subprocess
    (success, response) = test_target.trigger_subprocess_with_output("echo test")
    mocked_function.assert_called_once()
    mocked_subprocess.assert_called_once()
    assert success is True
    assert response == ["test"]

    # Reset things.
    mocked_function.reset_mock()
    mocked_subprocess.reset_mock()
    mocked_subprocess.side_effect = test_target.subprocess.CalledProcessError(
        -1, "fail"
    )

    # Add a failure side-effect to mimic a broken process
    (success, response) = test_target.trigger_subprocess_with_output("echo test")
    mocked_function.assert_called_once()
    mocked_subprocess.assert_called_once()
    assert success is False
    assert response.args[0] == -1


def test_trigger_subprocess_args():
    """Test that trigger_subprocess throws errors when given bad data."""
    with pytest.raises(TypeError):
        test_target.trigger_subprocess(None)


def test_dry_runs():
    """Test that we receive an echo of the command upon triggering a dry_run."""
    command = "echo nothing"

    assert (True, command) == test_target.trigger_subprocess(command, dry_run=True)

    assert (True, command) == test_target.trigger_subprocess_with_output(
        command, dry_run=True
    )
