# Copyright (C) 2023 DNEG. All Rights Reserved.
"""Test file for p4_show_setup.py."""

from datetime import datetime
import json
import logging
import os
import pytest
from unittest.mock import patch, call

from parameterized import parameterized
# Import cmds for use in mocked functions. pylint: disable=unused-import
from P4 import P4, P4Exception  # noqa

# pylint: enable=unused-import

import p4_show_setup as p4ss
from shared import arg_parser_utility
from .conftest import BaseUnitTestClass

class TestP4ShowSetup(BaseUnitTestClass):
    """Test wrapper class to test P4ShowSetup.

    Args:
        BaseUnitTestClass: unit test class decorator.
    """

    def setUp(self):
        """Run setup function before each test."""
        # Set up common variables.
        self.user = os.getlogin()
        self.date = datetime.today()
        self.mdy_str = f"{self.date.month}/{self.date.day}/{self.date.year}"

        # Set up test json.
        try:
            with open('.\\config\\show_setup_configs.json', 'r') as config_file:
                config_data = json.load(config_file)
        except OSError as error:
            logging.warning("Unable to open file show_setup_configs.json: %s", error)

        self.json_config = config_data["TESTDIV"]

        # Set up mocking functions.
        self.mock_p4_run = self.create_patch("tests.test_p4_show_setup.P4.run")
        self.mock_error = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.error"
        )
        self.mock_warning = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.warning"
        )
        self.mock_info = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.info"
        )
        self.mock_debug = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.debug"
        )


    def test_init_success(self):
        """Test the __init__ function of P4ShowSetup."""
        show_setup_instance = p4ss.P4ShowSetup("TESTDPT", self.json_config)
        assert show_setup_instance.show == "TESTDPT"
        assert show_setup_instance.json_config == self.json_config
        assert show_setup_instance.result == {}

# Ignore use of protected functions for testing. pylint: disable=W0212
    @parameterized.expand([
        [123, "Show code data type invalid: <class 'int'>"],
        ["", "Show code can not be empty"],
        ["1FOO", "Show code can not start with a number"],
        ["F", "Show code length must be at least 2 characters"],
        ["TEST", "TEST is a precious name and can not be used as a show code"]
    ])
    def test_validate_show_fails(self, showcode, err_msg):
        """Test a variety of invalid showcodes.

        Args:
            showcode (various): invalid show code.
            err_msg (str): expected message to print.
        """
        show_setup_instance = p4ss.P4ShowSetup(showcode, self.json_config)
        assert show_setup_instance.validate_show() == [err_msg]

    def test_validate_show_success(self):
        """Test a valid showcode."""
        show_setup_instance = p4ss.P4ShowSetup("FOO", self.json_config)
        assert not show_setup_instance.validate_show()

    def test_create_depot_success(self):
        """Test successful creation of show depot."""
        show = "TESTDEPOT"
        user = "tester"
        self.mock_p4_run.side_effect = [[],
            [{
                'Depot': show,
                'Owner': user,
                'Date': '2023/07/27 17:04:32',
                'Description': f'Created by {user}.\n',
                'Type': 'local',
                'Address': 'local',
                'Suffix': '.p4s',
                'StreamDepth': f'//{show}/1',
                'Map': f'{show}/...'
            }],
            [f'Depot {show} saved.']
        ]
        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        show_setup_instance.create_depot()
        assert show_setup_instance.result == {"Depot": show}
        assert self.mock_p4_run.call_count == 3
        run_calls = [
            call("depots", "-E", show),
            call("depot", "-o", show),
            call("depot", "-i")
        ]
        self.mock_p4_run.assert_has_calls(run_calls)
        info_calls = [
            call("Creating perforce depot"),
            call(["Depot TESTDEPOT saved."])
        ]
        self.mock_info.assert_has_calls(info_calls)
        self.mock_debug.assert_called_once_with("Checking for duplicate depot")
        self.mock_error.assert_not_called()

    def test_create_depot_fails_dupl(self):
        """Test creating a duplicate depot fails."""
        show = "TESTDUPL"
        self.mock_p4_run.return_value = [show]
        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        with pytest.raises(Exception):
            show_setup_instance.create_depot()
        assert show_setup_instance.result == {}
        self.mock_p4_run.assert_called_once_with("depots", "-E", show)
        self.mock_info.assert_called_once_with("Creating perforce depot")
        self.mock_debug.assert_called_once_with("Checking for duplicate depot")
        self.mock_error.assert_called_once_with(
            "Depot %s already exists. Cancelling process", show
        )

    def test_create_depot_fails_p4(self):
        """Test creating a duplicate depot fails."""
        show = "TESTDEPOT"
        self.mock_p4_run.side_effect = P4Exception("error")
        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        with pytest.raises(P4Exception):
            show_setup_instance.create_depot()
        assert show_setup_instance.result == {}
        self.mock_p4_run.assert_called_once_with("depots", "-E", show)
        self.mock_info.assert_called_once_with("Creating perforce depot")
        self.mock_debug.assert_called_once_with("Checking for duplicate depot")
        self.mock_error.assert_called_once()

    @parameterized.expand([
        [[{
            "Protections": [
                "write group line1 10.* //line1/*-dev/...## Internal content",
                "write group line2 10.* //line2/*-dev/...## Internal content",
                "## START OF DEPOT SPECIFIC PERMISSIONS",
                "write group line3 10.* //line3/*-dev/...## Internal content",
                "## END OF DEPOT SPECIFIC PERMISSIONS",
                "write group line4 10.* //line4/*-dev/...## Internal content",
            ]
        }]],
    ])
    def test_populate_perms_success(self, curr_permissions):
        """Test populating the permissions table successfully.

        Args:
            curr_permissions (dict): existing permissions table to add to.
        """
        self.mock_p4_run.return_value = curr_permissions
        show = "TESTPERMS"
        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)

        expected_permissions = []

        for line in self.json_config["permissions"]:
            expected_permissions.append(
                ((line.replace("{show}", show)).replace("{user}", self.user)).replace("{mdy_str}", self.mdy_str)
            )

        show_setup_instance.populate_permissions_table()
        self.mock_warning.assert_not_called()
        assert show_setup_instance.result == {"Permissions": expected_permissions}
        self.mock_p4_run.assert_any_call("protect", "-o")
        self.mock_p4_run.assert_any_call("protect", "-i")
        self.mock_info.assert_any_call("Populating permissions table with new permissions")
        assert self.mock_info.call_count == 2 + len(expected_permissions)
        debug_calls = [
            call("Grabbing configurated permissions from json"),
            call("Checking for duplicate permissions"),
            call("Loading permissions changes back into permissions table")
        ]
        self.mock_debug.assert_has_calls(debug_calls)
        self.mock_error.assert_not_called()

    @parameterized.expand([
        [[{
            "Protections": [
                "line1",
                "line2"
                "line3",
                "## END OF DEPOT SPECIFIC PERMISSIONS",
                "line4",
            ]
        }], "Permissions table is missing '## START OF DEPOT SPECIFIC PERMISSIONS'.\n"
            "Cancelling process to avoid conflicts. Please verify permissions table."],
        [[{
            "Protections": [
                "line1",
                "line2"
                "## START OF DEPOT SPECIFIC PERMISSIONS",
                "write group GroupName 10.* //TESTPERMS/*-dev/...##",
                "## END OF DEPOT SPECIFIC PERMISSIONS",
                "line4",
            ]
        }], "Some permissions for this show already exist.\n"
            "Cancelling process to avoid conflicts. Please verify permissions table."],
    ])
    def test_populate_permissions_fails(self, curr_permissions, warning_msg):
        """Test adding permissions to table fails.

        Args:
            curr_permissions (dict): existing permissions table.
            warning_msg (str): expected message to print.
        """
        self.mock_p4_run.side_effect = [curr_permissions]
        show = "TESTPERMS"

        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        with pytest.raises(Exception):
            show_setup_instance.populate_permissions_table()
        assert show_setup_instance.result == {}

        self.mock_p4_run.assert_called_once_with("protect", "-o")
        self.mock_info.assert_called_once_with("Populating permissions table with new permissions")
        debug_calls = [
            call("Grabbing configurated permissions from json"),
            call("Checking for duplicate permissions")
        ]
        self.mock_debug.assert_has_calls(debug_calls)
        self.mock_error.assert_any_call(warning_msg)
        assert self.mock_error.call_count == 2

    def test_populate_perms_fails_p4(self):
        """Test adding permissions to table fails.

        Args:
            curr_permissions (dict): existing permissions table.
            warning_msg (str): expected message to print.
        """
        self.mock_p4_run.side_effect = P4Exception("error")
        show = "TESTPERMS"

        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        with pytest.raises(Exception):
            show_setup_instance.populate_permissions_table()
        assert show_setup_instance.result == {}

        self.mock_p4_run.assert_called_once_with("protect", "-o")
        self.mock_info.assert_called_once_with("Populating permissions table with new permissions")
        self.mock_debug.assert_called_once_with("Grabbing configurated permissions from json")
        self.mock_error.assert_called_once()

    def test_create_groups_success(self):
        """Test adding groups."""
        show = "TESTGROUPS"
        self.mock_p4_run.side_effect = [
            [{'Group': show, 'Description': ''}],
            [f"Group {show} created"],
            [{'Group': f'{show}-External', 'Description': ''}],
            [{'Group': 'dnegvp_volume', 'Users': ['tjen', 'empty']}],
            [f"Group {show}-External created"],
            [{'Group': f'{show}-Main', 'Description': ''}],
            [{'Group': 'dnegvp_volume', 'Users': ['tjen', 'empty']}],
            [f"Group {show}-Main created"],
            [{'Group': f'{show}-Main-External', 'Description': ''}],
            [f"Group {show}-Main-External created"],
        ]
        expected_groups = [key.replace("{show}", show) for key in self.json_config["groups"]]
        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        show_setup_instance.create_groups()
        assert show_setup_instance.result == {"Groups": expected_groups}
        assert self.mock_p4_run.call_count == 10
        assert self.mock_info.call_count == 1 + (2 * len(expected_groups))
        assert self.mock_debug.call_count == 1 + (4 * len(expected_groups)) + 2 + 3 + 6
        self.mock_error.assert_not_called()

    def test_create_groups_duplicate(self):
        """Test adding groups where some groups were already created."""
        show = "TESTGROUPS"
        empty_description = "Default description"
        self.mock_p4_run.side_effect = [
            [{'Group': show, 'Description': ''}],
            [f"Group {show} updated"],
            [{'Group': f'{show}-External', 'Description': empty_description}],
            [{'Group': 'dnegvp_volume', 'Users': ['tjen', 'empty']}],
            [f"Group {show}-External created"],
            [{'Group': f'{show}-Main', 'Description': ''}],
            [{'Group': 'dnegvp_volume', 'Users': ['tjen', 'empty']}],
            [f"Group {show}-Main updated"],
            [{'Group': f'{show}-Main-External', 'Description': ''}],
            [f"Group {show}-Main-External created"],
        ]

        expected_groups = [f'{show}-External', f'{show}-Main-External']
        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        show_setup_instance.create_groups()
        assert show_setup_instance.result == {"Groups": expected_groups}
        assert self.mock_p4_run.call_count == 10
        assert self.mock_info.call_count == 1 + (2 * len(self.json_config["groups"]))
        assert self.mock_debug.call_count == 1 + (4 * len(self.json_config["groups"])) + 2 + 3 + 6
        self.mock_error.assert_not_called()

    def test_create_groups_exception(self):
        """Test adding some groups then fails with exception."""
        show = "TESTGROUPS"
        user = ["test_user"]
        empty_description = "Default description"
        self.mock_p4_run.side_effect = [
            [{'Group': show, 'Description': empty_description}],
            [f"Group {show} created"],
            [{'Group': f'{show}-External', 'Description': ''}],
            [{'Group': 'dnegvp_volume', 'Users': ['tjen', 'empty']}],
            [f"Group {show}-External created"],
            [{'Group': f'{show}-Main', 'Description': ''}],
            [{'Group': 'dnegvp_volume', 'Users': ['tjen', 'empty']}],
            [f"Group {show}-Main created"],
            P4Exception("error")
        ]
        expected_groups = [show, f'{show}-External', f'{show}-Main']
        show_setup_instance = p4ss.P4ShowSetup(show, self.json_config)
        show_setup_instance.create_groups()
        assert show_setup_instance.result == {"Groups": expected_groups}
        assert self.mock_p4_run.call_count == 9

    def test_create_initial_streams(self):
        """Test creating initial streams."""
        description = f"Created by {self.user} {self.mdy_str} \n"
        show = "TESTSTREAMS"
        self.mock_p4_run.side_effect = [
            [{
                'Stream': f'//{show}/{show}-main',
                'Owner': {self.user},
                'Name': f'{show}-main',
                'Parent': 'none', 'Type': 'development',
                'Description': description,
                'Options': 'allsubmit unlocked toparent fromparent mergedown',
                'ParentView': 'inherit'
            }],
            [f'Stream //{show}/{show}-main saved.'],
            [{'fileCount': '1498', 'change': '138'}],
            [{
                'Stream': f'//{show}/{show}-dev',
                'Owner': {self.user},
                'Name': f'{show}-dev',
                'Parent': 'none',
                'Type': 'development',
                'Description': description,
                'Options': 'allsubmit unlocked toparent fromparent mergedown',
                'ParentView': 'inherit'
            }],
            [f'Stream //{show}/{show}-dev saved.'],
            [{
                'Branch': 'placeholder2',
                'Owner': {self.user},
                'Description': description,
                'Options': 'unlocked',
                'View': [f'//{show}/{show}-dev/... //{show}/{show}-main/...']
            }],
            [{
                'Stream': f'//{show}/{show}-incoming',
                'Owner': {self.user},
                'Name': f'{show}-incoming',
                'Parent': 'none',
                'Type': 'development',
                'Description': description,
                'Options': 'allsubmit unlocked toparent fromparent mergedown',
                'ParentView': 'inherit'
            }],
            [f'Stream //{show}/{show}-incoming saved.'],
            [{
                'Stream': f'//{show}/{show}-outgoing',
                'Owner': {self.user},
                'Name': f'{show}-outgoing',
                'Parent': 'none', 'Type': 'development',
                'Description': description,
                'Options': 'allsubmit unlocked toparent fromparent mergedown',
                'ParentView': 'inherit'
            }],
            [f'Stream //{show}/{show}-outgoing saved.'],
        ]
        expected_streams = [
            f'//{show}/{show}-main',
            f'//{show}/{show}-dev',
            f'//{show}/{show}-incoming',
            f'//{show}/{show}-outgoing'
        ]
        result = p4ss._create_initial_streams(show, self.json_config["streams"])
        self.assertEqual(result, expected_streams)
        self.mock_p4_run.call_count = 12

    def test_undo_show_setup(self):
        """Test deleting the depot, permissions, and streams."""
        show = "TESTUNDO"
        objs_to_remove = {
            "Depot": show,
            "Permissions": [
                (f"write group {show} 10.* //{show}/*-dev/...## Internal content "
                    f"creation access - {self.user} {self.mdy_str}"),
                (f"write group {show}-External * //{show}/*-dev/...## External "
                    f"content creation access - {self.user} {self.mdy_str}"),
                (f"write group {show}-Incoming * //{show}/*-incoming/...## External "
                    f"write access for incoming client data - {self.user} "
                    f"{self.mdy_str}"),
                (f"read group {show}-Outgoing * //{show}/*-outgoing/...## External "
                    f"read-only access for outgoing client data - {self.user} "
                    f"{self.mdy_str}"),
                (f"write group {show}-Production * //{show}/...## Production "
                    f"management access for the depot - {self.user} {self.mdy_str}"),
                (f"write group {show}-Build-External * //{show}/...## DNEGVP "
                    f"external OSS access - {self.user} {self.mdy_str}"),
                (f"admin user {show}_LEDWall * //{show}/...## DNEGVP LED Wall user -"
                    f" {self.user} {self.mdy_str}"),
                (f"owner group dnegvp_volume * //{show}/...## Granting sub-permissions"
                    f" access for DNEG VP - {self.user} {self.mdy_str}"),
            ],
            "Groups": [
                show,
                f'{show}-External',
                f'{show}-Incoming',
                f'{show}-Outgoing',
                f'{show}-Production',
                f'{show}-Build-External'
            ],
            "Streams": [
                f'//{show}/{show}-main',
                f'//{show}/{show}-dev',
                f'//{show}/{show}-incoming',
                f'//{show}/{show}-outgoing'
            ]
        }
        p4ss._undo_show_setup(objs_to_remove)
        assert self.mock_p4_run.call_count == (
            3 + len(objs_to_remove['Groups']) + (2 * len(objs_to_remove['Streams']))
        )
        for stream in objs_to_remove['Streams']:
            self.mock_p4_run.assert_any_call("stream", "--obliterate -y", stream)
            self.mock_p4_run.assert_any_call("stream", "-d", stream)
        for group in objs_to_remove['Groups']:
            self.mock_p4_run.assert_any_call("group", f"-d {group}")
        self.mock_p4_run.assert_any_call("protect", "-o")
        self.mock_p4_run.assert_any_call("protect", "-i")
        self.mock_p4_run.assert_any_call("depot", f"-d {show}")
        assert self.mock_info.call_count == (
            5 + len(objs_to_remove["Groups"]) + len(objs_to_remove["Streams"])
        )

    def test_partial_undo_show_setup(self):
        """Test deleting the depot, permissions, and streams."""
        show = "TESTUNDO"
        objs_to_remove = {
            "Depot": show,
            "Permissions": [
                (f"write group {show} 10.* //{show}/*-dev/...## Internal content "
                    f"creation access - {self.user} {self.mdy_str}"),
                (f"write group {show}-Incoming * //{show}/*-incoming/...## External "
                    f"write access for incoming client data - {self.user} "
                    f"{self.mdy_str}"),
                (f"write group {show}-Production * //{show}/...## Production "
                    f"management access for the depot - {self.user} {self.mdy_str}"),
                (f"write group {show}-Build-External * //{show}/...## DNEGVP "
                    f"external OSS access - {self.user} {self.mdy_str}"),
                (f"owner group dnegvp_volume * //{show}/...## Granting sub-permissions"
                    f" access for DNEG VP - {self.user} {self.mdy_str}"),
            ],
            "Groups": [
                show,
                f'{show}-External',
                f'{show}-Incoming',
            ],
            "Streams": [
                f'//{show}/{show}-main',
                f'//{show}/{show}-dev',
            ]
        }
        p4ss._undo_show_setup(objs_to_remove)
        assert self.mock_p4_run.call_count == (
            3 + len(objs_to_remove['Groups']) + (2 * len(objs_to_remove['Streams']))
        )
        for stream in objs_to_remove['Streams']:
            self.mock_p4_run.assert_any_call("stream", "--obliterate -y", stream)
            self.mock_p4_run.assert_any_call("stream", "-d", stream)
        for group in objs_to_remove['Groups']:
            self.mock_p4_run.assert_any_call("group", f"-d {group}")
        self.mock_p4_run.assert_any_call("protect", "-o")
        self.mock_p4_run.assert_any_call("protect", "-i")
        self.mock_p4_run.assert_any_call("depot", f"-d {show}")
# pylint: enable=W0212


class TestRunP4Setup(BaseUnitTestClass):
    """Test wrapper class to test p4_show_setup.

    Args:
        BaseUnitTestClass: unit test class decorator.
    """

    def setUp(self):
        """Run setup function before each test."""
        # Set up common variables.
        self.user = os.getlogin()
        self.date = datetime.today()
        self.mdy_str = f"{self.date.month}/{self.date.day}/{self.date.year}"
        # Set up mocking functions.
        self.mock_input = self.create_patch("tests.test_p4_show_setup.p4ss.input")
        self.mock_validate_show = self.create_patch("p4_show_setup._validate_show")
        self.mock_setup_p4_instance = self.create_patch("p4_show_setup._setup_p4_instance")
        self.mock_create_depot = self.create_patch("p4_show_setup._create_depot")
        self.mock_populate_permissions = self.create_patch(
            "p4_show_setup._populate_permissions_table"
        )
        self.mock_create_groups = self.create_patch("p4_show_setup._create_groups")
        self.mock_create_initial_streams = self.create_patch(
            "p4_show_setup._create_initial_streams"
        )
        self.mock_cleanup_p4_instance = self.create_patch("p4_show_setup._cleanup_p4_instance")
        self.mock_undo = self.create_patch("p4_show_setup._undo_show_setup")
        self.mock_error = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.error"
        )
        self.mock_warning = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.warning"
        )
        self.mock_info = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.info"
        )
        self.mock_debug = self.create_patch(
            "tests.test_p4_show_setup.p4ss.logging.debug"
        )

        try:
            with open('.\\config\\show_setup_configs.json', 'r') as self.config_file:
                self.config_data = json.load(self.config_file)
        except OSError as error:
            logging.warning("Unable to open file show_setup_configs.json: %s", error)

        self.json_config = self.config_data["TESTDIV"]

        self.mock_json_load = self.create_patch(
            "tests.test_p4_show_setup.p4ss.json.load"
        )


    @patch('argparse.ArgumentParser.parse_args',
        return_value=arg_parser_utility.argparse.Namespace(
            show="TESTRUN", users=["test1"], division="TESTDIV"
        )
    )
    def test_success(self, mock_args):
        """Test that run_P4_show_setup succeeds if given all valid values.

        Args:
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        users = mock_args.return_value.users
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_json_load.return_value = self.config_data
        self.mock_setup_p4_instance.return_value = None
        self.mock_create_depot.return_value = show
        self.mock_populate_permissions.return_value = [
            (f"write group {show} 10.* //{show}/...## Only for those who need "
                f"access to the entire depot - {self.user} {self.mdy_str}"),
            (f"write group {show}-External * //{show}/...## Only for those who need"
                f" access to the entire depot - {self.user} {self.mdy_str}"),
            (f"write group {show}-Main 10.* //{show}/*-main/...## For those who "
                f"need to manage data transfers to or from the mainline - "
                f"{self.user} {self.mdy_str}"),
            (f"write group {show}-Main-External * //{show}/*-main/...## For those "
                f"who need to manage data transfers to or from the mainline - "
                f"{self.user} {self.mdy_str}"),
            (f"write group dnegvp_volume * //{show}/...## Granting sub-permissions "
                f"access for DNEG VP - {self.user} {self.mdy_str}")
        ]
        self.mock_create_groups.return_value = [
            show,
            f'{show}-External',
            f'{show}-Main',
            f'{show}-Main-External'
        ]
        self.mock_create_initial_streams.return_value = [
            f'//{show}/{show}-main',
            f'//{show}/{show}-dev',
            f'//{show}/{show}-incoming',
            f'//{show}/{show}-outgoing'
        ]

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_json_load.assert_called_once()
        self.mock_setup_p4_instance.assert_called_once()
        self.mock_create_depot.assert_called_once_with(show)
        self.mock_populate_permissions.assert_called_once_with(
            show,
            self.json_config["permissions"]
        )
        self.mock_create_groups.assert_called_once_with(
            show,
            self.json_config["groups"],
            users
        )
        self.mock_create_initial_streams.assert_called_once_with(
            show,
            self.json_config["streams"]
        )
        self.mock_cleanup_p4_instance.assert_called_once()

        # Verify the error handling did not run.
        self.mock_undo.assert_not_called()
        self.mock_warning.assert_not_called()

    @patch('argparse.ArgumentParser.parse_args',
            return_value=arg_parser_utility.argparse.Namespace(
                show="TEST_RUN_INVALID", users=[], division="TESTDIV"
            )
    )
    def test_show_invalid_fails(self, mock_args):
        """Test that run_P4_show_setup fails with invalid show name.

        Args:
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = [
            "Show code can not contain special characters"
        ]

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        # Assert function exits with warning.
        self.mock_warning.assert_called_once_with(
            "Show code invalid: %s", "Show code can not contain special characters"
        )

        # Verify the rest of the function was not called.
        self.mock_setup_p4_instance.assert_not_called()
        self.mock_create_depot.assert_not_called()
        self.mock_populate_permissions.assert_not_called()
        self.mock_create_groups.assert_not_called()
        self.mock_create_initial_streams.assert_not_called()
        self.mock_cleanup_p4_instance.assert_not_called()
        self.mock_undo.assert_not_called()

    @patch('argparse.ArgumentParser.parse_args',
        return_value=arg_parser_utility.argparse.Namespace(
            show="TESTRUN", users=["test1"], division="TESTDIV"
        )
    )
    def test_json_load_fails(self, mock_args):
        """Test that run_P4_show_setup fails if perforce setup fails.

        Args:
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_json_load.side_effect = OSError("error")

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_json_load.assert_called_once()
        self.mock_warning.assert_called_once_with(
            "Unable to open file show_setup_configs.json: %s", "OSError('error')"
        )

        # Verify the rest of the function was not called.
        self.mock_setup_p4_instance.assert_not_called()
        self.mock_create_depot.assert_not_called()
        self.mock_populate_permissions.assert_not_called()
        self.mock_create_groups.assert_not_called()
        self.mock_create_initial_streams.assert_not_called()
        self.mock_cleanup_p4_instance.assert_not_called()
        self.mock_undo.assert_not_called()

    @patch('argparse.ArgumentParser.parse_args',
            return_value=arg_parser_utility.argparse.Namespace(
                show="TESTRUN", users=["test1"], division="TESTDIV"
            )
    )
    def test_setup_p4_instance_fails(self, mock_args):
        """Test that run_P4_show_setup fails if perforce setup fails.

        Args:
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_json_load.return_value = self.config_data
        self.mock_setup_p4_instance.return_value = (
            "Connect to server failed; check $P4PORT."
        )

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_json_load.assert_called_once()
        self.mock_setup_p4_instance.assert_called_once()
        self.mock_warning.assert_called_once_with(
            "Perforce Connection Setup Failed. Cancelling operation"
        )

        # Verify the rest of the function was not called.
        self.mock_create_depot.assert_not_called()
        self.mock_populate_permissions.assert_not_called()
        self.mock_create_groups.assert_not_called()
        self.mock_create_initial_streams.assert_not_called()
        self.mock_cleanup_p4_instance.assert_not_called()
        self.mock_undo.assert_not_called()

    @patch('argparse.ArgumentParser.parse_args',
        return_value=arg_parser_utility.argparse.Namespace(
            show="TESTRUN", users=["test1"], division="TESTDIV"
        )
    )
    def test_depot_fails(self, mock_args):
        """Test that run_P4_show_setup fails and when depot fails.

        Args:
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_json_load.return_value = self.config_data
        self.mock_setup_p4_instance.return_value = None
        self.mock_create_depot.return_value = None

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_setup_p4_instance.assert_called_once()
        self.mock_json_load.assert_called_once()
        self.mock_create_depot.assert_called_once_with(show)

        # Error handling
        self.mock_warning.assert_called_once_with("Could not create show depot. Cancelling operation")
        self.mock_cleanup_p4_instance.assert_called_once()

        # Verify the rest of the function was not called.
        self.mock_populate_permissions.assert_not_called()
        self.mock_create_groups.assert_not_called()
        self.mock_create_initial_streams.assert_not_called()
        self.mock_undo.assert_not_called()

    @parameterized.expand([
        [P4Exception("error")],
        [TypeError("error")],
        [AttributeError("error")],
        [KeyError("error")],
    ])
    @patch('argparse.ArgumentParser.parse_args',
        return_value=arg_parser_utility.argparse.Namespace(
            show="TESTRUN", users=["test1"], division="TESTDIV"
        )
    )
    def test_depot_fails_exception(self, exc_type, mock_args):
        """Test that run_P4_show_setup fails and runs undo when exception is thrown.

        Args:
            exc_type (exception): the type of exception to throw.
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_json_load.return_value = self.config_data
        self.mock_setup_p4_instance.return_value = None
        self.mock_create_depot.side_effect = exc_type

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_setup_p4_instance.assert_called_once()
        self.mock_json_load.assert_called_once()
        self.mock_create_depot.assert_called_once_with(show)

        # Error handling
        self.mock_undo.assert_called_once()
        assert self.mock_warning.call_count == 2
        self.mock_cleanup_p4_instance.assert_called_once()

        # Verify the rest of the function was not called.
        self.mock_populate_permissions.assert_not_called()
        self.mock_create_groups.assert_not_called()
        self.mock_create_initial_streams.assert_not_called()

    @parameterized.expand([
        [P4Exception("error")],
        [TypeError("error")],
        [AttributeError("error")],
        [KeyError("error")],
    ])
    @patch('argparse.ArgumentParser.parse_args',
        return_value=arg_parser_utility.argparse.Namespace(
            show="TESTRUN", users=["test1"], division="TESTDIV"
        )
    )
    def test_permissions_fail_exception(self, exc_type, mock_args):
        """Test that run_P4_show_setup fails and runs undo when exception is thrown.

        Args:
            exc_type (exception): the type of exception to throw.
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        result = {
            "Depot": show,
        }
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_setup_p4_instance.return_value = None
        self.mock_json_load.return_value = self.config_data
        self.mock_create_depot.return_value = show
        self.mock_populate_permissions.side_effect = exc_type

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_setup_p4_instance.assert_called_once()
        self.mock_json_load.assert_called_once()
        self.mock_create_depot.assert_called_once_with(show)
        self.mock_populate_permissions.assert_called_once_with(
            show,
            self.json_config["permissions"]
        )

        # Error handling
        self.mock_undo.assert_called_once_with(result)
        assert self.mock_warning.call_count == 2
        self.mock_cleanup_p4_instance.assert_called_once()

        # Verify the rest of the function was not called.
        self.mock_create_groups.assert_not_called()
        self.mock_create_initial_streams.assert_not_called()

    @parameterized.expand([
        [P4Exception("error")],
        [TypeError("error")],
        [AttributeError("error")],
        [KeyError("error")],
    ])
    @patch('argparse.ArgumentParser.parse_args',
        return_value=arg_parser_utility.argparse.Namespace(
            show="TESTRUN", users=["test1"], division="TESTDIV"
        )
    )
    def test_groups_fail_exception(self, exc_type, mock_args):
        """Test that run_P4_show_setup fails and runs undo when exception is thrown.

        Args:
            exc_type (exception): the type of exception to throw.
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        users = mock_args.return_value.users
        result = {
            "Depot": show,
            "Permissions": [
                (f"write group {show} 10.* //{show}/...## Only for those who need "
                    f"access to the entire depot - {self.user} {self.mdy_str}"),
                (f"write group {show}-External * //{show}/...## Only for those who need"
                    f" access to the entire depot - {self.user} {self.mdy_str}"),
                (f"write group {show}-Main 10.* //{show}/*-main/...## For those who "
                    f"need to manage data transfers to or from the mainline - "
                    f"{self.user} {self.mdy_str}"),
                (f"write group {show}-Main-External * //{show}/*-main/...## For those "
                    f"who need to manage data transfers to or from the mainline - "
                    f"{self.user} {self.mdy_str}"),
                (f"write group dnegvp_volume * //{show}/...## Granting sub-permissions "
                    f"access for DNEG VP - {self.user} {self.mdy_str}")
            ],
        }
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_setup_p4_instance.return_value = None
        self.mock_json_load.return_value = self.config_data
        self.mock_create_depot.return_value = show
        self.mock_populate_permissions.return_value = [
            (f"write group {show} 10.* //{show}/...## Only for those who need "
                f"access to the entire depot - {self.user} {self.mdy_str}"),
            (f"write group {show}-External * //{show}/...## Only for those who need"
                f" access to the entire depot - {self.user} {self.mdy_str}"),
            (f"write group {show}-Main 10.* //{show}/*-main/...## For those who "
                f"need to manage data transfers to or from the mainline - "
                f"{self.user} {self.mdy_str}"),
            (f"write group {show}-Main-External * //{show}/*-main/...## For those "
                f"who need to manage data transfers to or from the mainline - "
                f"{self.user} {self.mdy_str}"),
            (f"write group dnegvp_volume * //{show}/...## Granting sub-permissions "
                f"access for DNEG VP - {self.user} {self.mdy_str}")
        ]
        self.mock_create_groups.side_effect = exc_type

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_setup_p4_instance.assert_called_once()
        self.mock_json_load.assert_called_once()
        self.mock_create_depot.assert_called_once_with(show)
        self.mock_populate_permissions.assert_called_once_with(
            show,
            self.json_config["permissions"]
        )
        self.mock_create_groups.assert_called_once_with(
            show,
            self.json_config["groups"],
            users
        )

        # Error handling
        self.mock_undo.assert_called_once_with(result)
        assert self.mock_warning.call_count == 2
        self.mock_cleanup_p4_instance.assert_called_once()

        # Verify the rest of the function was not called.
        self.mock_create_initial_streams.assert_not_called()

    @parameterized.expand([
        [P4Exception("error")],
        [TypeError("error")],
        [AttributeError("error")],
        [KeyError("error")],
    ])
    @patch('argparse.ArgumentParser.parse_args',
        return_value=arg_parser_utility.argparse.Namespace(
            show="TESTRUN", users=["test1"], division="TESTDIV"
        )
    )
    def test_streams_fail_exception(self, exc_type, mock_args):
        """Test that run_P4_show_setup fails and runs undo when exception is thrown.

        Args:
            exc_type (exception): the type of exception to throw.
            mock_args (ArgParser): mimic of command line arguments passed to function.
        """
        show = mock_args.return_value.show
        users = mock_args.return_value.users
        result = {
            "Depot": show,
            "Permissions": [
                (f"write group {show} 10.* //{show}/...## Only for those who need "
                    f"access to the entire depot - {self.user} {self.mdy_str}"),
                (f"write group {show}-External * //{show}/...## Only for those who need"
                    f" access to the entire depot - {self.user} {self.mdy_str}"),
                (f"write group {show}-Main 10.* //{show}/*-main/...## For those who "
                    f"need to manage data transfers to or from the mainline - "
                    f"{self.user} {self.mdy_str}"),
                (f"write group {show}-Main-External * //{show}/*-main/...## For those "
                    f"who need to manage data transfers to or from the mainline - "
                    f"{self.user} {self.mdy_str}"),
                (f"write group dnegvp_volume * //{show}/...## Granting sub-permissions "
                    f"access for DNEG VP - {self.user} {self.mdy_str}")
            ],
            "Groups": [
                show,
                f'{show}-External',
                f'{show}-Main',
                f'{show}-Main-External'
            ]
        }
        self.mock_input.return_value = show
        self.mock_validate_show.return_value = []
        self.mock_setup_p4_instance.return_value = None
        self.mock_json_load.return_value = self.config_data
        self.mock_create_depot.return_value = show
        self.mock_populate_permissions.return_value = [
            (f"write group {show} 10.* //{show}/...## Only for those who need "
                f"access to the entire depot - {self.user} {self.mdy_str}"),
            (f"write group {show}-External * //{show}/...## Only for those who need"
                f" access to the entire depot - {self.user} {self.mdy_str}"),
            (f"write group {show}-Main 10.* //{show}/*-main/...## For those who "
                f"need to manage data transfers to or from the mainline - "
                f"{self.user} {self.mdy_str}"),
            (f"write group {show}-Main-External * //{show}/*-main/...## For those "
                f"who need to manage data transfers to or from the mainline - "
                f"{self.user} {self.mdy_str}"),
            (f"write group dnegvp_volume * //{show}/...## Granting sub-permissions "
                f"access for DNEG VP - {self.user} {self.mdy_str}")
        ]
        self.mock_create_groups.return_value = [
            show,
            f'{show}-External',
            f'{show}-Main',
            f'{show}-Main-External'
        ]
        self.mock_create_initial_streams.side_effect = exc_type

        p4ss.run_p4_show_setup()

        self.mock_validate_show.assert_called_once_with(show)
        self.mock_setup_p4_instance.assert_called_once()
        self.mock_json_load.assert_called_once()
        self.mock_create_depot.assert_called_once_with(show)
        self.mock_populate_permissions.assert_called_once_with(
            show,
            self.json_config["permissions"]
        )
        self.mock_create_groups.assert_called_once_with(
            show,
            self.json_config["groups"],
            users
        )
        self.mock_create_initial_streams.assert_called_once_with(
            show,
            self.json_config["streams"]
        )

        # Error handling
        self.mock_undo.assert_called_once_with(result)
        assert self.mock_warning.call_count == 2
        self.mock_cleanup_p4_instance.assert_called_once()
