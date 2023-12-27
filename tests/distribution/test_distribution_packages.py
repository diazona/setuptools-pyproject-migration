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

import pytest
import sys

from typing import Iterator, List

# Try importing pyproject_metadata but don't save the module itself because we don't need it
pytest.importorskip("pyproject_metadata")

from pyproject_metadata import StandardMetadata  # noqa: E402

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


def _setuptools_scm_version_conflict() -> bool:
    """
    Check whether the conditions exist to trigger the ``setuptools_scm`` version
    conflict. If these conditions exist, certain tests should be skipped.
    See `issue 145 <https://github.com/diazona/setuptools-pyproject-migration/issues/145>`_.
    """

    if sys.version_info < (3, 12):
        return False
    from test_support import importlib_metadata
    from packaging.version import Version

    try:
        setuptools_scm_version = Version(importlib_metadata.version("setuptools_scm"))
    except importlib_metadata.PackageNotFoundError:
        return False
    return setuptools_scm_version < Version("6")


distributions: List = [
    # e.g.
    # GitHubDistribution(url, commit-ish)
    # PyPiDistribution(name, version)
    pytest.param(
        PyPiDistribution("pytest", "7.3.0"),
        marks=[
            pytest.mark.xfail,
            pytest.mark.skipif(_setuptools_scm_version_conflict(), reason="Issue #145"),
        ],
    ),
    _xfail(PyPiDistribution("pytest-localserver", "0.8.0")),
    PyPiDistribution("aioax25", "0.0.11.post0", make_importable=True),
]


@pytest.mark.needs_network
@pytest.mark.slow
class TestExternalProject:
    """
    Test that the generated core metadata for a distributable package
    matches the pyproject.toml file we generate for that package.
    """

    @pytest.fixture(scope="class", params=distributions, ids=lambda ep: ep.test_id)
    def distribution_package(
        self, request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
    ) -> Iterator[DistributionPackagePreparation]:
        """
        Prepare a DistributionPackage for testing. This populates the temporary
        path with the package's source code.
        """

        dist: DistributionPackage = request.param
        prep: DistributionPackagePreparation = dist.prepare(tmp_path_factory.mktemp(dist.test_id))
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.chdir(prep.project.root)
            if prep.make_importable:
                monkeypatch.syspath_prepend(prep.project.root)
            yield prep

    @pytest.fixture(scope="class")
    def expected(self, distribution_package: DistributionPackagePreparation) -> StandardMetadata:
        return distribution_package.core_metadata_reference

    @pytest.fixture(scope="class")
    def actual(self, distribution_package: DistributionPackagePreparation) -> StandardMetadata:
        return StandardMetadata.from_pyproject(distribution_package.project.generate())

    def test_name(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.name == actual.name

    def test_version(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.version == actual.version

    def test_description(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.description == actual.description

    def test_license(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.license == actual.license

    def test_readme(self, expected: StandardMetadata, actual: StandardMetadata):
        """
        Test that the ``readme`` metadata matches.

        Because the filename is not part of the core metadata, we simply check
        that the text and content type match, and if a file is named, that it
        exists and its content matches the text.
        """
        if expected.readme is None or actual.readme is None:
            assert expected.readme == actual.readme
            # If both are None, no further checking to do
            return

        assert expected.readme.text == actual.readme.text
        assert expected.readme.content_type == actual.readme.content_type
        if expected.readme.file:
            # If this happens, it might be okay but we have to figure out how
            # the filename made it into the reference metadata and add whatever
            # kind of check would make sense to verify that
            raise ValueError("readme filename found in reference metadata")
        if actual.readme.file:
            assert actual.readme.file.exists()
            # Use actual.readme.text as the expected value here instead of
            # expected.readme.text to reflect the intent that we're only
            # checking if the contents of the file matches the text. If both
            # of those are the same but they don't match the expected readme
            # text, then it's the earlier assertion's job to catch that.
            assert actual.readme.text == actual.readme.file.read_text()

    def test_requires_python(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.requires_python == actual.requires_python

    def test_dependencies(self, expected: StandardMetadata, actual: StandardMetadata):
        assert sorted(expected.dependencies, key=str) == sorted(actual.dependencies, key=str)

    def test_optional_dependencies(self, expected: StandardMetadata, actual: StandardMetadata):
        # Check that the set of extras is the same
        assert expected.optional_dependencies.keys() == actual.optional_dependencies.keys()

        # Check that the dependencies associated with each extra are the same
        for extra in expected.optional_dependencies:
            assert sorted(expected.optional_dependencies[extra], key=str) == sorted(
                actual.optional_dependencies[extra], key=str
            )

    # Not part of core metadata
    # def test_entrypoints(self, expected: StandardMetadata, actual: StandardMetadata):
    #     assert expected.entrypoints == actual.entrypoints

    def test_authors(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.authors == actual.authors

    def test_maintainers(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.maintainers == actual.maintainers

    def test_urls(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.urls == actual.urls

    def test_classifiers(self, expected: StandardMetadata, actual: StandardMetadata):
        assert sorted(expected.classifiers) == sorted(actual.classifiers)

    def test_keywords(self, expected: StandardMetadata, actual: StandardMetadata):
        assert sorted(expected.keywords) == sorted(actual.keywords)

    # Not part of core metadata
    # def test_scripts(self, expected: StandardMetadata, actual: StandardMetadata):
    #     assert expected.scripts == actual.scripts

    # Not part of core metadata
    # def test_gui_scripts(self, expected: StandardMetadata, actual: StandardMetadata):
    #     assert expected.gui_scripts == actual.gui_scripts

    def test_dynamic(self, expected: StandardMetadata, actual: StandardMetadata):
        assert expected.dynamic == actual.dynamic
