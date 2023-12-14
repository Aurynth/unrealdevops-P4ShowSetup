# Copyright (C) 2023 DNEG - All Rights Reserved.
"""
P4 Show Setup.

This script is to automate the process of setting up a new show in Perforce.

The steps that will be covered include:
- Setting up the initial Depot.
- Populating the permissions table.
- Adding the permissions groups.
- Creating the streams for the new depot.
"""
from datetime import datetime
import json
import logging
import os
import pathlib

from P4 import P4, P4Exception

from shared import arg_parser_utility

logging.basicConfig(level=logging.DEBUG)
P4 = P4()

class P4ShowSetup:
    """Wrapper class for setting up a show in perforce."""

    def __init__(self, show, json_config):
        """Construct an instance of P4ShowSetup Class.

        Args:
            show (str): the show code.
            json_config (dict): the configurations to follow for setting up the depot.
        """
        self.show = show
        self.json_config = json_config
        self.result = {}

    def validate_show(self):
        """Ensure showcode follows normal conventions.

        Showcode must consist of 2-8 alphanumeric characters. It cannot start with a number.
        It cannot match the name of a reserved path in Windows, nor can it match any other
        name mentioned in the blocklist in dnBuildTools.

        Code taken from showsetup script:
        (http://stash/projects/RND/repos/showsetup-api/browse/src/_showsetupapi/utils/validators.py#19-71)

        Additional validation taken from dnBuildTools:
        (http://stash/projects/TECH/repos/site-scripts/browse/dnBuildTools#23-30)

        """
        # names that we can't call a show
        # mkvfx directories
        precious_names = [
            "CG", "ELEMENT", "ENV", "OUT", "REF", "REI", "SCAN", "SIM", "TEST"
        ]
        # environment variables - #45501
        precious_names.extend(
            ["HOME", "HOST", "LANG", "PATH", "PWD", "SHELL", "TEMP", "TERM", "TMP", "USER"]
        )
        precious_names.extend(["SHOW", "SITE", "SHOT"])
        # show should not be named WEED as we have internal tool named weed (SYS-19820)
        precious_names.extend(["WEED"])

        errors = []

        # Check if show_name is of type str
        if not isinstance(self.show, str):
            errors.append(f"Show code data type invalid: {type(self.show)}")
            return errors

        # Check if show_name is blank
        if not self.show:
            errors.append("Show code can not be empty")
            return errors

        # Check if show starts with number
        if self.show[0].isdigit():
            errors.append("Show code can not start with a number")

        # Check min length >= 2
        if len(self.show) < 2:
            errors.append("Show code length must be at least 2 characters")

        if self.show in precious_names:
            errors.append(self.show + " is a precious name and can not be used as a show code")

        # Check invalid Windows directory names
        if pathlib.PureWindowsPath(self.show).is_reserved():
            errors.append("Show code causes error when creating a directory on Windows")

        return errors

    def create_depot(self):
        """Create the show Perforce Depot.

        Args:
            show (str): Showcode to use as the depot name.

        Returns:
            str: name of the depot that was successfully created..
        """
        logging.info("Creating perforce depot")

        logging.debug("Checking for duplicate depot")
        try:
            if len(P4.run("depots", "-E", self.show)) > 0:
                logging.error("Depot %s already exists. Cancelling process", self.show)
                raise Exception

            depot = P4.run("depot", "-o", self.show)[0]
            depot["Type"] = "stream"
            P4.input = [depot]
            result = P4.run("depot", "-i")
        except P4Exception as error:
            logging.error("There was an error while creating the depot: %s", error)
            raise

        logging.info(result)
        self.result["Depot"] = self.show

    def populate_permissions_table(self):
        """Add the permissions table entries for the show.

        Returns:
            list[str]: List of entires that were successfully added to permissions table.
        """
        date = datetime.today()
        mdy_str = f"{date.month}/{date.day}/{date.year}"
        user = P4.user

        logging.info("Populating permissions table with new permissions")

        logging.debug("Grabbing configurated permissions from json")
        # List of permission table entries
        permissions_entries = []
        for line in self.json_config["permissions"]:
            line = line.replace("{show}", self.show)
            line = line.replace("{user}", user)
            line = line.replace("{mdy_str}", mdy_str)
            permissions_entries.append(line)

        try:
            current_permissions = P4.run("protect", "-o")
            # TODO: save these permissions in a backup file in case of failure. (tjen - 12/8/23)

            # Check that permission table doesn't already contain permissions for the show.
            logging.debug("Checking for duplicate permissions")
            existing_show_permissions = [
                entry for entry in current_permissions[0]["Protections"] if (
                    f"//{self.show}/" in entry
                )
            ]

            if len(existing_show_permissions) > 0:
                logging.error(
                    "Some permissions for this show already exist.\n"
                    "Cancelling process to avoid conflicts. Please verify permissions table."
                )
                raise Exception

            # Find correct place in permission table, alphabetically by show.
            insert_index = 0
            in_editable_block = False
            for index, entry in enumerate(current_permissions[0]["Protections"]):
                if in_editable_block:
                    if entry.startswith("## END OF DEPOT SPECIFIC PERMISSIONS"):
                        in_editable_block = False
                        insert_index = index
                        break
                    # Get showcode from Depot name
                    showcode = entry.split('/')[2]
                    if showcode.upper() > self.show.upper():
                        insert_index = index
                        break
                else:
                    in_editable_block = entry.startswith(
                        "## START OF DEPOT SPECIFIC PERMISSIONS"
                    )

            # if no start block was found, do not insert
            if insert_index == 0:
                logging.error(
                    "Permissions table is missing '## START OF DEPOT SPECIFIC PERMISSIONS'.\n"
                    "Cancelling process to avoid conflicts. Please verify permissions table."
                )
                raise Exception

            for index, new_entry in enumerate(permissions_entries):
                logging.info(new_entry)
                current_permissions[0]["Protections"].insert(insert_index + index, new_entry)
            logging.debug("Loading permissions changes back into permissions table")
            P4.input = current_permissions
            permissions_result = P4.run("protect", "-i")
            logging.info(permissions_result)
            self.result["Permissions"] = permissions_entries
        except Exception as error:
            logging.error("There was an error while adding permissions: %s", error)
            raise

    def create_groups(self):
        """Add permissions groups to perforce that match permissions table entries."""
        date = datetime.today()
        mdy_str = f"{date.month}/{date.day}/{date.year}"
        json_groups = self.json_config["groups"]

        logging.info("Creating new permissions groups")
        # List of permission table entries
        self.result["Groups"] = []
        for grp_name in json_groups:
            grp_settings_dict = json_groups[grp_name]
            grp_name = grp_name.replace("{show}", self.show)
            try:
                logging.info("Creating group: %s", grp_name)
                current_group = P4.run("group", "-o", grp_name)[0]
                # Check that it's not over-writing existing Descriptions or Users.
                if current_group["Description"] == "":
                    current_group["Description"] = f"Created by {P4.user} {mdy_str}"
                if "Users" not in current_group:
                    current_group["Users"] = ["empty"]

                # Add owners to the the External groups.
                logging.debug("Adding owners and users to group %s", grp_name)
                if grp_settings_dict != "empty":
                    for user_grp_type in grp_settings_dict:
                        user_grp_array = grp_settings_dict[user_grp_type]
                        for user_grp in user_grp_array:
                            if "groups" in user_grp:
                                u = P4.run("group", "-o", user_grp["groups"])[0]
                                if "Users" in u:
                                    user_grp = u["Users"]
                            if user_grp_type not in current_group:
                                current_group[user_grp_type] = []
                            for user in user_grp:
                                if user not in current_group[user_grp_type]:
                                    logging.debug(
                                        "Adding %s as %s to group %s",
                                        user,
                                        user_grp_type,
                                        grp_name
                                    )
                                    current_group[user_grp_type].append(user)

                logging.debug("Loading group settings for %s", grp_name)
                P4.input = [current_group]
                permissions_result = P4.run("group", "-i")
                logging.info(permissions_result)
                if permissions_result == [f'Group {grp_name} created']:
                    self.result["Groups"].append(grp_name)
            except Exception as error:
                logging.error("There was an error while adding groups: %s", error)
                raise

    def create_initial_streams(self):
        """Create the default initial streams.

        One main stream, one dev branched off main, incoming, and outgoing streams.

        Returns:
            list[str]: List of streams that were successfully created.
        """
        date = datetime.today()
        mdy_str = f"{date.month}/{date.day}/{date.year}"
        description = f"Created by {P4.user} {mdy_str}"
        self.result["Streams"] = []
        json_streams = self.json_config["streams"]

        logging.info("Setting up streams")
        try:
            for stream in json_streams:
                stream_settings = json_streams[stream]
                stream = stream.replace("{show}", self.show)
                logging.info("Creating stream %s", stream)
                new_stream = P4.run("stream", "-o", stream)[0]
                new_stream["Description"] = description
                new_stream["Type"] = stream_settings["type"]
                if "parent" in stream_settings:
                    new_stream["Parent"] = stream_settings["parent"].replace("{show}", self.show)
                logging.debug("Loading stream settings for %s", stream)
                P4.input = [new_stream]
                result = P4.run("stream", "-i")
                logging.info(result)
                if result == [f"Stream {stream} saved."]:
                    self.result["Streams"].append(stream)

                if "branch" in stream_settings:
                    branch = stream_settings["branch"].replace("{show}", self.show)
                    logging.info("Populating %s with branch contents %s", stream, branch)
                    branch_result = P4.run(
                        "populate",
                        f"{branch}/...",
                        f"{stream}/..."
                    )
                    logging.info(branch_result)
                elif "parent" in stream_settings:
                    parent = stream_settings["parent"].replace("{show}", self.show)
                    logging.info("Populating %s with parent contents %s", stream, parent)
                    parent_result = P4.run(
                        "populate",
                        f"{parent}/...",
                        f"{stream}/..."
                    )
                    logging.info(parent_result)

        except Exception as error:
            logging.error("There was an error when creating the streams: %s", error)
            raise

    def undo_show_setup(self):
        """Reverse the steps that have been taken for show setup in Perforce.

        If any step of the process fails, all steps so far should be reversed.

        Args:
            result (dict): the results from the previous steps. Describes which steps
                succeeded.
        """
        # Remove the streams that were created.
        logging.info("Removing all streams from the depot %s", self.result["Depot"])
        if "Streams" in self.result:
            for stream in self.result["Streams"]:
                stream_result = P4.run("stream", "-d", stream)
                P4.run("stream", "--obliterate", "-y", stream)
                logging.info("Removing stream: %s", stream_result)

        # Remove the groups that have been created.
        logging.info("Removing all groups for the depot %s", self.result["Depot"])
        if "Groups" in self.result:
            for grp in self.result["Groups"]:
                group_result = P4.run("group", f'-d {grp}')
                logging.info("Removing group: %s", group_result)

        # Remove any permissions entries
        # TODO: check against backed-up permissions table. (tjen 12/8/23)
        current_permissions = P4.run("protect", "-o")
        logging.info("Removing all permissions for the depot %s", self.result["Depot"])
        if "Permissions" in self.result:
            for entry in self.result["Permissions"]:
                current_permissions[0]["Protections"].remove(entry)
            P4.input = current_permissions
            permissions_result = P4.run("protect", "-i")
            logging.info("Removing permissions: %s", permissions_result)

        # Remove depot
        if self.result["Depot"]:
            depot_result = P4.run("obliterate", '-y', f'//{self.result["Depot"]}/...')
            print(depot_result)
            depot_result = P4.run("depot", '-d', self.result["Depot"])
            logging.info("Removing depot: %s", depot_result)


def _print_help():
    """
    Print the help information to the screen.

    Returns:
        string: The contents of the help message.
    """
    help_message = (
        """\n
        Dneg's Perforce Show Setup.
        ================================\n\n
        A command line tool to help automate the process of p4 show setup.\n\n
        """
    )

    return help_message


def _setup_parse_arguments():
    """
    Parse the arguments.

    Returns:
        list: a list of arguments.
    """
    logging.info("Parsing Command line Arguments")

    parser = arg_parser_utility.setup_parser(help_message=_print_help())
    parser.add_argument(
        "-s",
        "--show",
        type=str,
        required=True,
        help="Showcode for the show being set up. Must be all CAPS. (required)",
    )
    parser.add_argument(
        "-d",
        "--division",
        nargs='*',
        default=None,
        help="Division of company. Specifies permission groups, and stream structure.",
    )
    return parser


def _setup_p4_instance():
    """Set up the Perforce instance."""
    P4.port = 'rsh:C:\\Program Files\\Perforce\\DVCS\\p4d.exe -i -J off -r "F:\\P4Server\\.p4root"' #"ssl:zroperforce1:1666"
    P4.user = os.getlogin()

    logging.info("Connecting to perforce %s", P4.port)
    try:
        P4.connect()
        logging.info("Successfully connected to perforce %s", P4.port)
        return None
    except P4Exception:
        logging.error("Error connecting to perforce %s", P4.port)
        for error in P4.errors:
            logging.error(error)
        return P4.errors


def _cleanup_p4_instance():
    """Clean up the Perforce instance."""
    logging.info("Disconnecting from perforce server")
    P4.disconnect()


def run_p4_show_setup():
    """Set up show depot, permissions, and streams in Perforce."""
    arg_parser = _setup_parse_arguments()
    args = arg_parser.parse_args()
    json_config = None
    show = args.show
    div = args.division

    # Validate showcode
    user_input_show = input("Please confirm the Show Code: ")
    if user_input_show != show:
        logging.warning(
            "Manual show code confirmation failed: %s does not match %s\nCancelling Process",
            show,
            user_input_show
        )
        return

    logging.info(
        "Retrieving configs from"
        " \\unrealdevops-perforceshowsetup\\src\\config\\show_setup_configs.json"
    )
    try:
        with open('.\\config\\show_setup_configs.json', 'r') as config_file:
            config_data = json.load(config_file)
    except OSError as error:
        logging.warning("Unable to open file show_setup_configs.json: %s", repr(error))
        return

    if "TS" in div:
        logging.info("Perforce depot will be set up using configs for TS (ThreeSixty)")
        json_config = config_data["TS"]
    elif "RE" in div:
        logging.info("Perforce depot will be set up using configs for RE (Redefine)")
        json_config = config_data["RE"]
    elif "VFX" in div:
        logging.info("Perforce depot will be set up using configs for VFX")
        json_config = config_data["VFX"]
    elif "TESTDIV" in div:
        logging.info("Perforce depot will be set up using configs for Testing")
        json_config = config_data["TESTDIV"]
    else:
        logging.info("division not specified")
        user_input_division = input("Please specify a company division TS|RE|[VFX]:")
        if "TS" in user_input_division:
            logging.info(
                "Perforce depot will be set up using configs for TS (ThreeSixty)"
            )
            json_config = config_data["TS"]
        elif "RE" in user_input_division:
            logging.info("Perforce depot will be set up using configs for Redefine")
            json_config = config_data["RE"]
        else:
            logging.info("Perforce depot will be set up using configs for VFX")
            json_config = config_data["VFX"]

    show_setup_instance = P4ShowSetup(show, json_config)

    logging.info("Validating show code against show naming conventions.")
    show_name_errors = show_setup_instance.validate_show()

    if show_name_errors:
        logging.warning("Show code invalid: %s", '; '.join(show_name_errors))
        return
    else:
        logging.info("Showcode %s is valid", show)

    try:
        # Connecting to Perforce
        if _setup_p4_instance() is not None:
            logging.warning("Perforce Connection Setup Failed. Cancelling operation")
            return

        # Creating the depot
        show_setup_instance.create_depot()
        # Populating permissions
        show_setup_instance.populate_permissions_table()
        # Creating groups
        show_setup_instance.create_groups()
        # Creating initial streams
        show_setup_instance.create_initial_streams()
    except P4Exception as error:
        logging.warning(
            "Perforce Show Setup Failed with P4 Exception: %s.", repr(error))
        logging.warning("Removing %s: %s\n" for (key,value) in show_setup_instance.result)
        show_setup_instance.undo_show_setup()
    except (TypeError, AttributeError, KeyError) as error:
        logging.warning(
            "Perforce Show Setup Failed with Exception: %s.", repr(error))
        logging.warning("Removing %s: %s\n" for (key,value) in show_setup_instance.result)
        show_setup_instance.undo_show_setup()

    _cleanup_p4_instance()


if __name__ == "__main__":
    run_p4_show_setup()
