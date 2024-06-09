"""
Testing the logic that extracts the entrypoint data:
    - CLI entrypoints
    - GUI entrypoints
    - miscellaneous entrypoints
"""


def test_generate_noentrypoints(make_write_pyproject):
    """
    Test distribution with no entry points generates no entry points
    """
    cmd = make_write_pyproject()
    result = cmd._generate()

    assert "scripts" not in result["project"]
    assert "gui-scripts" not in result["project"]
    assert "entry-points" not in result["project"]


def test_generate_clionly(make_write_pyproject):
    """
    Test distribution with only CLI scripts generates only "scripts"
    """
    cmd = make_write_pyproject(
        entry_points=dict(
            console_scripts=[
                "spanish-inquisition=montypython.unexpected:spanishinquisition",
                "brian=montypython.naughtyboy:brian",
            ]
        ),
    )
    result = cmd._generate()

    assert "gui-scripts" not in result["project"]
    assert "entry-points" not in result["project"]

    assert result["project"]["scripts"] == {
        "spanish-inquisition": "montypython.unexpected:spanishinquisition",
        "brian": "montypython.naughtyboy:brian",
    }


def test_generate_guionly(make_write_pyproject):
    """
    Test distribution with only GUI scripts generates only "gui-scripts"
    """
    cmd = make_write_pyproject(
        entry_points=dict(
            gui_scripts=[
                "dead-parrot=montypython.sketch:petshop",
                "shrubbery=montypython.holygrail:knightswhosayni",
            ]
        ),
    )
    result = cmd._generate()

    assert "scripts" not in result["project"]
    assert "entry-points" not in result["project"]

    assert result["project"]["gui-scripts"] == {
        "dead-parrot": "montypython.sketch:petshop",
        "shrubbery": "montypython.holygrail:knightswhosayni",
    }


def test_generate_misconly(make_write_pyproject):
    """
    Test distribution with only misc entry points generates only "entry-points"
    """
    cmd = make_write_pyproject(
        entry_points={
            "project.plugins": [
                "babysnatchers=montypython.somethingcompletelydifferent:babysnatchers",
                "eels=montypython.somethingcompletelydifferent:eels",
            ]
        },
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


def test_generate_all_entrypoints(make_write_pyproject):
    """
    Test distribution with all entry point types, generates all sections
    """
    cmd = make_write_pyproject(
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


def test_generate_ini_entrypoints(make_write_pyproject):
    """
    Test distribution with INI-style entry_points
    """
    # https://github.com/diazona/setuptools-pyproject-migration/issues/152
    cmd = make_write_pyproject(
        entry_points="""
            [console_scripts]
            spanish-inquisition=montypython.unexpected:spanishinquisition
            brian=montypython.naughtyboy:brian

            [gui_scripts]
            dead-parrot=montypython.sketch:petshop
            shrubbery=montypython.holygrail:knightswhosayni

            [project.plugins]
            babysnatchers=montypython.somethingcompletelydifferent:babysnatchers
            eels=montypython.somethingcompletelydifferent:eels
        """
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
