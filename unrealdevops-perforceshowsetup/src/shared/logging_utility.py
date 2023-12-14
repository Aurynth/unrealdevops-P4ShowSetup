# Copyright (C) 2023 DNEG - All Rights reserved.
"""
Logging Utility.

This utility's responsibility is to set up the logging for the script.
"""
import datetime
import logging
import os
import tempfile


def set_logger_output_path(logger_output_dir: str, log_locally: bool = False):
    """
    Set the logger outputh path.

    Args:
        logger_output_dir (str): path to the output directory.

        log_locally (bool, optional): a flag to determine whether to log to
            the same working directory where the script was ran from.

    Returns:
        str: The absolute path to the logger output directory.
    """
    output_path = logger_output_dir
    if not log_locally:
        logging.debug("Attempting to retrive local user temp path.")
        output_path = os.sep.join([tempfile.gettempdir(), logger_output_dir])

    if not os.path.isdir(output_path):
        generate_new_logger_output_dir(output_path)

    return output_path


def get_logger_output_path(logger_output_dir: str):
    """
    Get the logger outputh path.

    Args:
        logger_output_dir (str): name of to the output directory.

    Returns:
        str: The absolute path to the logger output directory.
    """
    output_path = logger_output_dir
    if os.path.isdir(output_path):
        return output_path

    logging.debug("Attempting to retrive local user temp path.")
    output_path = os.sep.join([tempfile.gettempdir(), logger_output_dir])

    if os.path.isdir(output_path):
        return output_path

    # Error occurred. Should not hit this ever.
    logging.error("No log output folder found.")
    return None


def generate_new_logger_output_dir(desired_path: str):
    """
    Generate a new logger output directory at the given path.

    Args:
        desired_path (str): Absolute path to the directory to be generated.

    """
    logging.debug("Adding new directory at: %s", desired_path)
    os.makedirs(desired_path)


def initialize_logger(
    desired_log_level: str,
    log_to_file: bool,
    log_output_path: str,
    log_output_filename_suffix: str,
):
    """
    Set the desired logging level for the runtime output.

    Args:
        desired_log_level (str): The default desired log level.
        log_to_file (bool): should we log results to a file?
        log_output_path (str): Where to output the log file to.
        log_output_filename_suffix (str): What output log filename
            suffix to use.

    """
    date_format = "%Y-%m-%d %H:%M:%S"
    log_level = logging.getLevelName(desired_log_level)

    root_logger = logging.getLogger()

    # clear handlers created in obscure root logging.basicConfig() call.
    root_logger.handlers = []
    root_logger.setLevel(logging.DEBUG)

    # Set up the Console Logger to the default level.
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s: %(message)s\n",
        datefmt=date_format,
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)

    # NOTE:Earliest we can start logging to console.
    root_logger.addHandler(console_handler)

    if log_to_file:
        # Set up the file logger in the user's temp folder.
        file_logger_output_path = log_output_path
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_logger_output_name = f"{log_output_filename_suffix}_{timestamp}.txt"
        file_logger_absolute_path = os.sep.join(
            [file_logger_output_path, file_logger_output_name]
        )
        file_logger = logging.FileHandler(file_logger_absolute_path)
        file_logger.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt=(
                "%(asctime)s.%(msecs)03d - " "%(name)s - %(levelname)s: %(message)s\n"
            ),
            datefmt=date_format,
        )
        file_logger.setFormatter(file_formatter)
        root_logger.addHandler(file_logger)
