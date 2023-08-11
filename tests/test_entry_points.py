"""
Testing the logic that extracts the entrypoint data:
    - CLI entrypoints
    - GUI entrypoints
    - miscellaneous entrypoints
"""

from setuptools_pyproject_migration import WritePyproject
from setuptools.dist import Distribution


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
    result = cmd._generate()

    assert "scripts" not in result["project"]
    assert "gui-scripts" not in result["project"]
    assert "entry-points" not in result["project"]


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
    result = cmd._generate()

    assert "gui-scripts" not in result["project"]
    assert "entry-points" not in result["project"]

    assert result["project"]["scripts"] == {
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
    result = cmd._generate()

    assert "scripts" not in result["project"]
    assert "entry-points" not in result["project"]

    assert result["project"]["gui-scripts"] == {
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
    result = cmd._generate()

    assert "scripts" not in result["project"]
    assert "gui-scripts" not in result["project"]

    assert result["project"]["entry-points"] == {
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
    result = cmd._generate()

    assert result["project"]["scripts"] == {
        "spanish-inquisition": "montypython.unexpected:spanishinquisition",
        "brian": "montypython.naughtyboy:brian",
    }

    assert result["project"]["gui-scripts"] == {
        "dead-parrot": "montypython.sketch:petshop",
        "shrubbery": "montypython.holygrail:knightswhosayni",
    }

    assert result["project"]["entry-points"] == {
        "project.plugins": {
            "babysnatchers": "montypython.somethingcompletelydifferent:babysnatchers",
            "eels": "montypython.somethingcompletelydifferent:eels",
        },
    }
