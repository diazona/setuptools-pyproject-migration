"""
Tests of the plugin on real distribution packages.

"Distribution package" in this sense means a full-fledged project that has
source code and packaging metadata, as opposed to the mock projects created by
our test suite. In short, these tests run the plugin on real Python projects to
make sure it works. The tests run approximately the following procedure:

1. Acquire the source code of an "external" project
2. Build and package it in the standard way using a :pep:`517`-compliant
   build frontend, like `build <https://github.com/pypa/build>`_
3. Run ``python setup.py pyproject`` to convert the project's setuptools
   configuration to a ``pyproject.toml``
4. Build a wheel from that ``pyproject.toml``
5. Compare the two wheels to make sure there are no differences that stem from
   discrepancies in ``pyproject.toml``

In practice, the implementation takes some shortcuts to avoid _actually_
having to build all those wheel files, such as using already-published wheels
from PyPI. But verifying that the procedure above works is the ultimate goal.
"""

import pathlib
import pytest

from typing import List

# Try importing pyproject_metadata but don't save the module itself because we don't need it
pytest.importorskip("pyproject_metadata")

from pyproject_metadata import RFC822Message, StandardMetadata  # noqa: E402

# If pyproject_metadata isn't available, test_support.distribution won't be either
from test_support.distribution import (  # noqa: E402
    DistributionPackage,
    DistributionPackagePreparation,
    PyPiDistribution,
)


# The return type here is _pytest.mark.structures.ParameterSet but that's not
# part of pytest's public API so we don't use it.
# See https://github.com/pytest-dev/pytest/issues/7469
def _xfail(*args):
    """
    Syntactic sugar for marking a test as an expected failure.
    """
    return pytest.param(*args, marks=pytest.mark.xfail)


distributions: List = [
    # e.g.
    # GitHubDistribution(url, commit-ish)
    # PyPiDistribution(name, version)
    _xfail(PyPiDistribution("pytest", "7.3.0")),
    _xfail(PyPiDistribution("pytest-localserver", "0.8.0")),
]


@pytest.fixture(params=distributions, ids=lambda ep: ep.test_id)
def distribution_package(request: pytest.FixtureRequest, tmp_path: pathlib.Path) -> DistributionPackagePreparation:
    """
    Prepare a DistributionPackage for testing. This populates the temporary
    path with the package's source code.
    """

    dist: DistributionPackage = request.param
    return DistributionPackagePreparation(dist, tmp_path)


@pytest.mark.needs_network
@pytest.mark.slow
def test_external_project(distribution_package: DistributionPackagePreparation, monkeypatch: pytest.MonkeyPatch):
    """
    Test that the generated core metadata for a distributable package
    matches the pyproject.toml file we generate for that package.
    """
    monkeypatch.chdir(distribution_package.project.root)
    expected_metadata: RFC822Message = distribution_package.distribution_package.core_metadata_reference()
    actual_metadata: RFC822Message = StandardMetadata.from_pyproject(
        distribution_package.project.generate()
    ).as_rfc822()

    assert str(expected_metadata) == str(actual_metadata)
