"""
Testing the logic that extracts the entrypoint data:
    - CLI entrypoints
    - GUI entrypoints
    - miscellaneous entrypoints
"""

from typing import Dict, List

from setuptools_pyproject_migration import WritePyproject
from setuptools.dist import Distribution


# Entry point parsing


def test_parse_entrypoint_happypath():
    """
    Test we can extract the entry point name and target from a string.
    """
    assert WritePyproject._parse_entrypoint("ep=project.module:target") == {"ep": "project.module:target"}


def test_parse_entrypoint_happypath_whitespace():
    """
    Test we strip extraneous whitespace from the strings received.
    """
    assert WritePyproject._parse_entrypoint("  ep  =  project.module:target  ") == {"ep": "project.module:target"}


def test_parse_entrypoint_missing_eq():
    """
    Test that a string lacking a '=' is refused.
    """
    try:
        WritePyproject._parse_entrypoint("ep project.module:target")
        assert False, "Should not have been accepted as valid"
    except ValueError as e:
        assert str(e).endswith(" is not of the form 'name = module:function'")


# Wrapper function logic


def test_generate_entrypoints_none():
    """
    Test we get an empty dict if entrypoints is None.
    """
    assert WritePyproject._generate_entrypoints(None) == {}


def test_generate_entrypoints():
    """
    Test we get all entry points grouped by type.
    """
    assert WritePyproject._generate_entrypoints(
        {
            "console_scripts": [
                "spanish-inquisition = montypython.unexpected:spanishinquisition",
                "brian=montypython.naughtyboy:brian",
            ],
            "gui_scripts": [
                "dead-parrot=montypython.sketch:petshop",
                "shrubbery=montypython.holygrail:knightswhosayni",
            ],
            "project.plugins": [
                "babysnatchers=montypython.somethingcompletelydifferent:babysnatchers",
                "eels=montypython.somethingcompletelydifferent:eels",
            ],
        }
    ) == {
        "console_scripts": {
            "spanish-inquisition": "montypython.unexpected:spanishinquisition",
            "brian": "montypython.naughtyboy:brian",
        },
        "gui_scripts": {
            "dead-parrot": "montypython.sketch:petshop",
            "shrubbery": "montypython.holygrail:knightswhosayni",
        },
        "project.plugins": {
            "babysnatchers": "montypython.somethingcompletelydifferent:babysnatchers",
            "eels": "montypython.somethingcompletelydifferent:eels",
        },
    }


# Test correct placement of the parsed endpoints


def test_generate_noentrypoints():
    """
    Test distribution with no entry points generates no entry points
    """
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
            )
        )
    )
    project = cmd._generate()

    assert "scripts" not in project["project"]
    assert "gui-scripts" not in project["project"]
    assert "entry-points" not in project["project"]


def test_generate_clionly():
    """
    Test distribution with only CLI scripts generates only "scripts"
    """
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                entry_points=dict(
                    console_scripts=[
                        "spanish-inquisition=montypython.unexpected:spanishinquisition",
                        "brian=montypython.naughtyboy:brian",
                    ]
                ),
            )
        )
    )
    project = cmd._generate()

    assert "gui-scripts" not in project["project"]
    assert "entry-points" not in project["project"]

    assert project["project"]["scripts"] == {
        "spanish-inquisition": "montypython.unexpected:spanishinquisition",
        "brian": "montypython.naughtyboy:brian",
    }


def test_generate_guionly():
    """
    Test distribution with only GUI scripts generates only "gui-scripts"
    """
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                entry_points=dict(
                    gui_scripts=[
                        "dead-parrot=montypython.sketch:petshop",
                        "shrubbery=montypython.holygrail:knightswhosayni",
                    ]
                ),
            )
        )
    )
    project = cmd._generate()

    assert "scripts" not in project["project"]
    assert "entry-points" not in project["project"]

    assert project["project"]["gui-scripts"] == {
        "dead-parrot": "montypython.sketch:petshop",
        "shrubbery": "montypython.holygrail:knightswhosayni",
    }


def test_generate_misconly():
    """
    Test distribution with only misc entry points generates only "entry-points"
    """
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                entry_points={
                    "project.plugins": [
                        "babysnatchers=montypython.somethingcompletelydifferent:babysnatchers",
                        "eels=montypython.somethingcompletelydifferent:eels",
                    ]
                },
            )
        )
    )
    project = cmd._generate()

    assert "scripts" not in project["project"]
    assert "gui-scripts" not in project["project"]

    assert project["project"]["entry-points"] == {
        "project.plugins": {
            "babysnatchers": "montypython.somethingcompletelydifferent:babysnatchers",
            "eels": "montypython.somethingcompletelydifferent:eels",
        },
    }


def test_generate_all_entrypoints():
    """
    Test distribution with all entry point types, generates all sections
    """
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                entry_points={
                    "console_scripts": [
                        "spanish-inquisition=montypython.unexpected:spanishinquisition",
                        "brian=montypython.naughtyboy:brian",
                    ],
                    "gui_scripts": [
                        "dead-parrot=montypython.sketch:petshop",
                        "shrubbery=montypython.holygrail:knightswhosayni",
                    ],
                    "project.plugins": [
                        "babysnatchers=montypython.somethingcompletelydifferent:babysnatchers",
                        "eels=montypython.somethingcompletelydifferent:eels",
                    ],
                },
            )
        )
    )
    project = cmd._generate()

    assert project["project"]["scripts"] == {
        "spanish-inquisition": "montypython.unexpected:spanishinquisition",
        "brian": "montypython.naughtyboy:brian",
    }

    assert project["project"]["gui-scripts"] == {
        "dead-parrot": "montypython.sketch:petshop",
        "shrubbery": "montypython.holygrail:knightswhosayni",
    }

    assert project["project"]["entry-points"] == {
        "project.plugins": {
            "babysnatchers": "montypython.somethingcompletelydifferent:babysnatchers",
            "eels": "montypython.somethingcompletelydifferent:eels",
        },
    }
