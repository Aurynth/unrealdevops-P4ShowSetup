# Copyright (C) 2023 DNEG - All Rights reserved.
"""Handle calling external processes outside of git."""
import logging
import subprocess


def trigger_subprocess(command: str, dry_run: bool = False):
    """
    Trigger  an external subprocess command.

    Args:
        command (string): The command to be trigger by the subprocess.
        dry_run (bool, optional): Flag to forego triggering the command if
            desired.

    Returns:
        bool: Value determining wether the command failed.
        string: The command's output if any.

    """
    logging.info("Triggering external command: %s", command)
    if dry_run:
        return (True, command)
    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            shell=True,
        )

        result = output.decode(encoding="utf-8", errors="ignore")
        result = result.rstrip()
        logging.debug("Command Response:\n%s", result)
        return (True, result)
    except subprocess.CalledProcessError as ex:
        return (False, ex)


def trigger_subprocess_with_output(command: str, dry_run: bool = False):
    """
    Trigger  an external subprocess command.

    Args:
        command (string): The command to be trigger by the subprocess.
        dry_run (bool, optional): Flag to forego triggering the command if
            desired.

    Returns:
        bool: Value determining wether the command failed.
        list: List containing all lines in he command's output if any.

    """
    logging.info("Triggering external command: %s", command)
    if dry_run:
        return (True, command)
    try:
        with subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ) as process:
            final_output = []

            while True:
                output = process.stdout.readline().decode(
                    encoding="utf-8",
                    errors="ignore",
                )
                if output == "" and process.poll() is not None:
                    break
                if output:
                    output = output.rstrip()
                    print(output.strip())  # noqa: T201 - Intended print
                    final_output.append(output)

            logging.debug("Command Response:\n%s", repr(final_output))
            return (True, final_output)
    except subprocess.CalledProcessError as ex:
        return (False, ex)
