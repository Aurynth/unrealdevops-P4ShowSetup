# pylint: disable=W0212
"""Unit tests to check existing file system has no PR blocking errors."""
import logging
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

GLOBAL_IGNORE = [
    ".bzr",
    ".eggs",
    ".git",
    ".hg",
    ".nox",
    ".pytest_cache",
    ".svn",
    ".tox",
    ".venv",
    ".vscode",
    "__pycache__",
    "_archive",
    "artifacts",
    "venv",
    r"\*.egg",
    r"\*_dev\*",
]

RE_PYTHON_SHEBANG = re.compile(rb"^#!.*\b(?:dn)?python-?[23w]?\b")
REGEX = re.compile(f'(?:{"|".join(GLOBAL_IGNORE)})')


def _is_python_file(file_path):
    """Check if the file path is a python source file.

    This will catch both *.py files and extension-less files with a python
    shebang.

    Args:
        file_path (str): A path to a file

    Returns:
        bool: True if the file path points to a python file, False otherwise.
    """

    def has_python_shebang(file_path):
        with open(file_path, "rb") as file_:
            line = file_.readline(100)
        return bool(RE_PYTHON_SHEBANG.match(line))

    _, ext = os.path.splitext(file_path)

    return ext.lower() == ".py" or (not ext and has_python_shebang(file_path))


def _find_python_files(path):
    """Search for python files from a list of files and directories.

    This will crawl directories recursively. Files given explicitly will be
    considered python files, and always returned in the list of results.

    Args:
        path (str): path to directory to be searched for python files.

    Returns:
        bool: whether the path provided contains python files.
    """
    for dir_path, _, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dir_path, filename)
            if _is_python_file(file_path):
                return True

    return False


def _get_filtered_python_files(path: str):
    py_files = set()

    if os.path.isfile(path):
        py_files.add(path)
    else:
        for dir_path, directories, filenames in os.walk(path):
            for directory in directories:
                directory_path = os.path.join(dir_path, directory)
                if not any(re.findall(REGEX, directory_path)):
                    nested_files = _get_filtered_python_files(directory_path)
                    py_files.update(nested_files)
                else:
                    logging.info("Ignoring: %s", directory_path)
            for filename in filenames:
                file_path = os.path.join(dir_path, filename)
                if not any(re.findall(REGEX, file_path)) and _is_python_file(file_path):
                    py_files.add(file_path)
                else:
                    logging.debug("Ignoring: %s", file_path)

    logging.debug("Files to test: %s", py_files)
    return list(sorted(py_files))


def _pipe_lint(path: str, target_executable: str):
    """Triggers the lint subprocess.

    Args:
        path (str): _description_
        target_executable (str): _description_
    """
    command = [target_executable, "--mode=black", path]
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)

    except subprocess.CalledProcessError:
        return False
    return True


def _get_path_to_executable(current_directory, target_executable):
    # Set the default script path to match what is running our current script.
    scripts_path = os.path.dirname(sys.executable)

    # Check if there is a virtual environment being used.
    if os.path.exists(current_directory + os.sep + ".venv"):
        scripts_path = os.path.join(current_directory, ".venv", "Scripts")
    elif os.path.exists(current_directory + os.sep + "venv"):
        scripts_path = os.path.join(current_directory, "venv", "Scripts")

    # Now detect if the path that we are using to run things has the required
    # executables installed.
    if os.path.exists(os.path.join(scripts_path, target_executable)):
        logging.debug("Found Target executable at: %s", target_executable)
        return os.path.join(scripts_path, target_executable)

    logging.error("Could not find target executable.")
    return None


def test_no_linter_errors():
    """Test if this repository has no linter errors."""
    assert sys.executable, "Python executable not found."

    main_directory = str(Path(__file__).parent.parent.parent)
    assert os.path.isdir(main_directory)
    assert os.path.exists(
        main_directory + os.sep + "setup.py"
    ), "Could not deduce root directory during test run."

    pipe_lint_path = _get_path_to_executable(main_directory, "pipe-lint.exe")

    assert pipe_lint_path is not None, "Failed to find required pipe-lint.exe"

    # This is to be absorbed into the pipe-lint functionality in the future.
    regex_group = f'(?:{"|".join(GLOBAL_IGNORE)})'
    regex = re.compile(regex_group)

    file_errors = set()

    for dir_path, _, filenames in os.walk(main_directory):
        for filename in filenames:
            file_path = os.path.join(dir_path, filename)

            if _is_python_file(file_path) and not any(re.findall(regex, file_path)):
                if not _pipe_lint(file_path, pipe_lint_path):
                    file_errors.add(file_path)

    assert not any(
        file_errors
    ), "Found pipe-lint errors in the following files: " + "\t\n".join(file_errors)


def _run_black(path: str, target_executable: str):
    """Triggers the black subprocess.

    Args:
        path (str): _description_
        target_executable (str): _description_
    """
    exclude_pattern = "|".join(GLOBAL_IGNORE)
    command = [
        target_executable,
        "--check",
        f'--extend-exclude="{exclude_pattern}"',
        path,
    ]
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)

    except subprocess.CalledProcessError:
        return False
    return True


def test_black_compliant_repo():
    """Tests if this repo is compliant with black."""
    assert sys.executable, "Python executable not found."

    main_directory = str(Path(__file__).parent.parent.parent)
    assert os.path.isdir(main_directory)
    assert os.path.exists(
        main_directory + os.sep + "setup.py"
    ), "Could not deduce root directory during test run."

    black_path = _get_path_to_executable(main_directory, "black.exe")

    assert black_path is not None, "Failed to find required black.exe"

    regex_group = f'(?:{"|".join(GLOBAL_IGNORE)})'
    regex = re.compile(regex_group)

    file_errors = set()
    for dir_path, _, filenames in os.walk(main_directory):
        for filename in filenames:
            file_path = os.path.join(dir_path, filename)
            if _is_python_file(file_path) and not any(re.findall(regex, file_path)):
                if not _run_black(file_path, black_path):
                    file_errors.add(file_path)

    assert not any(
        file_errors
    ), "Found black errors in the following files: " + "\t\n".join(file_errors)


@pytest.mark.skip(
    reason="Force run if you wish to see the list of "
    "files which require black + pipe-lint compliance"
)
def test_return_target_files():
    """Get the files from the repo that are to be black + pipe-lint compliant."""
    regex_group = f'(?:{"|".join(GLOBAL_IGNORE)})'
    regex = re.compile(regex_group)

    main_directory = os.getcwd()

    files = set()
    for dir_path, _, filenames in os.walk(main_directory):
        for filename in filenames:
            file_path = os.path.join(dir_path, filename)
            if _is_python_file(file_path) and not any(re.findall(regex, file_path)):
                files.add(file_path)

    output = "\n".join(files)
    logging.error(output)  # noqa - Intended print
