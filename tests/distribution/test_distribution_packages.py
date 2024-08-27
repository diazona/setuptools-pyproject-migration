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

import logging
import packaging.markers
import packaging.requirements
import pytest

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


_logger = logging.getLogger("setuptools_pyproject_migration:tests:" + __name__)


def _setuptools_scm_version_conflict() -> bool:
    """
    Check whether the conditions exist to trigger the ``setuptools_scm`` version
    conflict. If these conditions exist, certain tests should be skipped.
    See `issue 145 <https://github.com/diazona/setuptools-pyproject-migration/issues/145>`_.
    """

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
        marks=pytest.mark.skipif(_setuptools_scm_version_conflict(), reason="Issue #145"),
    ),
    pytest.param(
        PyPiDistribution("pytest-localserver", "0.8.0"),
        marks=pytest.mark.distribute(
            {
                "test_readme": pytest.mark.xfail,
            }
        ),
    ),
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
        metadata = StandardMetadata.from_pyproject(distribution_package.project.generate())
        # Work around a bug where StandardMetadata.from_pyproject() can produce
        # None for an email address which isn't present, contradicting its type
        # hinting. (https://github.com/pypa/pyproject-metadata/issues/126)
        for i, (name, email) in enumerate(metadata.authors):
            if email is None:
                metadata.authors[i] = (name, "")
        for i, (name, email) in enumerate(metadata.maintainers):
            if email is None:
                metadata.maintainers[i] = (name, "")
        return metadata

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

        # The Requirements in the expected optional dependencies will have extra
        # markers because those are parsed directly from core metadata's
        # Requires-Dist lines, but in the actual optional dependencies they
        # won't because those come from StandardMetadata.from_pyproject()
        # which does not include extras in the Requirements. Normalizing
        # the two to match each other is tricky because it would require
        # parsing the markers, which is not easy; the code to do it is in
        # the packaging package but it's not part of their public API. So for
        # now we just compare names/urls and versions and ignore the markers.
        def sort_key(req: packaging.requirements.Requirement):
            return req.name, req.url, req.specifier, req.extras, str(req.marker)

        for extra in expected.optional_dependencies:
            sorted_expected = sorted(expected.optional_dependencies[extra], key=sort_key)
            sorted_actual = sorted(actual.optional_dependencies[extra], key=sort_key)
            assert len(sorted_expected) == len(sorted_actual)
            for e, a in zip(sorted_expected, sorted_actual):
                assert e.name == a.name
                assert e.url == a.url
                assert e.specifier == a.specifier
                assert e.extras == a.extras
                # We expect the markers to be different because e.marker includes
                # the extra but a.marker won't. So we look for some heuristics
                # which are easy to detect.
                _logger.debug("Comparing markers %r and %r", e.marker, a.marker)
                if e.marker == a.marker:
                    _logger.debug("Markers are equal")
                    continue
                elif not a.marker and e.marker == packaging.markers.Marker(f'extra == "{extra}"'):
                    _logger.debug("Actual marker is None and expected marker is 'extra == %s'", f'"{extra}"')
                    continue
                # Check the same patterns that pyproject-metadata uses to add
                # extras when writing markers out to RFC822 headers (see
                # pyproject_metadata._build_extra_req()). Note that this isn't
                # quite perfect; this next condition will trigger if " or "
                # appears anywhere in the marker, even within parentheses,
                # whereas the implementation of _build_extra_req() (correctly)
                # only looks for an "or" token at the top level of the marker,
                # but if that becomes an issue we'll hopefully know because
                # a test will fail, and at that time we can make this check
                # smarter.
                elif " or " in str(a.marker):
                    if e.marker == packaging.markers.Marker(f'({a.marker}) and extra == "{extra}"'):
                        _logger.debug("Expected marker matches '(actual marker) and extra == %s'", f'"{extra}"')
                        continue
                else:
                    if e.marker == packaging.markers.Marker(f'{a.marker} and extra == "{extra}"'):
                        _logger.debug("Expected marker matches 'actual marker and extra == %s'", f'"{extra}"')
                        continue
                # We know this will fail but writing it as an assert rather than
                # a direct call to pytest.fail() gives a better error message
                assert e.marker == a.marker

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
