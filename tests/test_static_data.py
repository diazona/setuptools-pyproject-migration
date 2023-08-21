"""
Tests of the "simple cases", where the data in setup.cfg or setup.py is read
in by setuptools, stored as-is, and added directly or with minor transformations
into the pyproject data structure, rather than being parsed and used to
configure some kind of dynamic functionality.
"""

import pytest

from setuptools import Distribution
from setuptools_pyproject_migration import WritePyproject
from typing import List


def test_name_and_version(project) -> None:
    """
    Test we can generate a basic project skeleton.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
"""
    pyproject = {
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": "test-project",
            "version": "0.0.1",
        },
    }
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    assert result == pyproject


# install_requires tests, we use made-up module names here.


def test_install_requires(project) -> None:
    """
    Test the install_requires is passed through if given.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
install_requires =
        dependency1
        dependency2>=1.23
        dependency3<4.56
"""
    pyproject = {
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": "test-project",
            "version": "0.0.1",
            "dependencies": ["dependency1", "dependency2>=1.23", "dependency3<4.56"],
        },
    }
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    assert result == pyproject


# setup_requires tests: we have to use real dependencies that actually are
# installed, otherwise the tests will fail.


def test_setup_requires(project) -> None:
    """
    Test setup_requires is passed through with 'setuptools' dependency.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
setup_requires =
        sphinx
        pytest>=6
        pytest-black<99.88.77
"""
    pyproject = {
        "build-system": {
            "requires": ["pytest-black<99.88.77", "pytest>=6", "setuptools", "sphinx"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": "test-project",
            "version": "0.0.1",
        },
    }
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    assert result == pyproject


def test_setup_requires_setuptools(project) -> None:
    """
    Test that we don't duplicate 'setuptools' in build requirements
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
setup_requires =
        setuptools
        sphinx
        pytest>=6
        pytest-black<99.88.77
"""
    pyproject = {
        "build-system": {
            "requires": ["pytest-black<99.88.77", "pytest>=6", "setuptools", "sphinx"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": "test-project",
            "version": "0.0.1",
        },
    }
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    assert result == pyproject


def test_setup_requires_setuptools_version(project) -> None:
    """
    Test we can handle a build system that requires a specific setuptools version.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
setup_requires =
        setuptools>=34.56
        sphinx
        pytest>=6
        pytest-black<99.88.77
"""
    pyproject = {
        "build-system": {
            "requires": ["pytest-black<99.88.77", "pytest>=6", "setuptools>=34.56", "sphinx"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": "test-project",
            "version": "0.0.1",
        },
    }
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    assert result == pyproject


def test_description() -> None:
    description = "Description of TestProject"

    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                description=description,
            )
        )
    )
    result = cmd._generate()

    assert result["project"]["description"] == description


def test_empty_description() -> None:
    description = ""

    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                description=description,
            )
        )
    )
    result = cmd._generate()

    assert "description" not in result["project"]


@pytest.mark.parametrize(
    "keywords",
    [
        ["hovercraft", "full", "of", "eels"],
        [""],
        ["hovercraft", "full of", "eels"],
    ],
    ids=["simple", "zero-length", "space"],
)
def test_keywords(keywords: List[str]) -> None:
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                keywords=keywords,
            )
        )
    )
    result = cmd._generate()

    assert result["project"]["keywords"] == keywords


def test_no_keywords() -> None:
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
                keywords=[],
            )
        )
    )
    result = cmd._generate()

    assert "keywords" not in result["project"]


def test_keywords_not_given() -> None:
    cmd = WritePyproject(
        Distribution(
            dict(
                name="TestProject",
                version="1.2.3",
            )
        )
    )
    result = cmd._generate()

    assert "keywords" not in result["project"]
