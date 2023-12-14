# Copyright (C) 2023 DNEG - All Rights reserved.
"""
Parser Module.

This module set ups the argument parsing functionality.
"""
import argparse


def setup_parser(bare: bool = False, help_message: str = None):
    """
    Parser constructor.

    Adds all the parser commands that the command line allows along with their
        usage information.

    Args:
        bare (bool, optional): A flag that determines if we should avoid
            adding the default parser options from being generated.
        help_message (str, optional): The contents with which to override the
            auto-generated help message from arguments provided to the parser.

    Returns:
        argparse.ArgumentParser: The argument parser object that will be handling
            command line arguments received.

    """
    parser = argparse.ArgumentParser(
        usage=help_message, formatter_class=argparse.RawTextHelpFormatter
    )

    if not bare:
        choices = ["INFO", "DEBUG", "WARNING", "ERROR", "FATAL"]
        parser.add_argument(
            "-l",
            "--loglevel",
            help=(
                "Change the default logging level presented to the user.\n"
                "Defaults to `INFO` level for the console logger. The text \n"
                "file log generated captures all logging levels.\n\n"
            ),
            type=str,
            choices=choices,
            default=choices[0],
        )

        parser.add_argument(
            "--open-logs-folder",
            help=(
                "Opens an file manager window to the location where the \n"
                "logs are stored for previous executions of this script. \n"
                "Unless the `--local-log` flag was used during the \n"
                "execution of the command, the output log of can be found \n"
                "under: \n"
                "\t\t`%%TEMP%%/UnrealPluginBuilder`\n\n"
            ),
            action="store_true",
            default=None,
            dest="open_logs_folder",
        )

        parser.add_argument(
            "--local-log",
            help=(
                "Forces the system to output the log to the current working\n"
                "directory under a folder named `UnrealPluginBuilder`\n\n"
            ),
            action="store_true",
            default=False,
            dest="log_locally",
        )

    return parser
