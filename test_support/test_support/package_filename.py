import logging
import packaging.version
import re

from typing import NamedTuple, Union
from wheel_filename import ParsedWheelFilename, parse_wheel_filename


_logger = logging.getLogger("test_support.package_filename")


def normalize_package_name(name: str):
    """
    Normalize a Python package name in the manner specified by :pep:`503`.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


class ParsedSdistFilename(NamedTuple):
    """
    A simple representation of the filename of an sdist. This is modeled after
    :py:class:`wheel_filename.ParsedWheelFilename`.

    This needs to represent both standard (:pep:`625`-compliant) and nonstandard
    filenames.
    """

    project: str
    """
    The distribution name of the project. This is the name it would be listed
    under on PyPI.
    """

    version: str
    """
    The version of the project.

    For compatibility with :py:class:`wheel_filename.ParsedWheelFilename`, this
    will be a string, but under all but the most unusual circumstances it's
    guaranteed to be a valid :pep:`440` version string which can be passed to
    :py:func:`packaging.version.parse()`. The only exception is if an sdist has
    an extremely nonstandard filename from which it wasn't possible to extract
    a :pep:`440`-compliant version, this may be set to a best guess at
    the package's version.
    """

    def __str__(self) -> str:
        return f"{self.project}-{self.version!s}.tar.gz"


def parse_package_filename(filename: str) -> Union[ParsedSdistFilename, ParsedWheelFilename]:
    """
    Parse a filename of a Python package, either sdist or wheel.

    >>> parse_package_filename("project-0.1.tar.gz")
    ParsedSdistFilename(project='project', version='0.1')
    >>> parse_package_filename("project-0.1-py3-none-any.whl")
    ParsedWheelFilename(project='project', version='0.1', build=None, python_tags=['py3'], abi_tags=['none'], platform_tags=['any'])

    This will handle nonstandard sdist filenames as well, as long as they're
    not too crazy.

    >>> parse_package_filename("project-name-0.1-post0.tar.gz")
    ParsedSdistFilename(project='project-name', version='0.1-post0')
    """  # noqa: E501
    if filename.endswith(".whl"):
        return parse_wheel_filename(filename)
    elif filename.endswith(".tar.gz"):
        basename = filename[:-7]
        # PEP 625 specifies that "-" should not occur in the package name portion
        # of a filename, so we should be able to split on the first hyphen.
        name, _, version = basename.partition("-")
        try:
            packaging.version.parse(version)
        except packaging.version.InvalidVersion:
            # But to support testing of nonstandard sdist filenames, we need to
            # handle cases where the separator between the name and version
            # is not the first hyphen.
            _logger.debug("Parsing nonstandard version %s", version)
        else:
            return ParsedSdistFilename(name, version)

        # Loop over subsequent hyphens and find the first one that we can split
        # on and have the second portion of the string be a valid version.
        try:
            while True:
                split_point = basename.index("-", len(name) + 1)
                assert split_point > len(name)
                name = basename[:split_point]
                assert len(name) == split_point
                version = basename[split_point + 1 :]
                try:
                    packaging.version.parse(version)
                except packaging.version.InvalidVersion:
                    _logger.debug("Failed to parse as name %s and version %s", name, version)
                else:
                    return ParsedSdistFilename(name, version)
        except IndexError:
            # We could not produce a valid version by splitting on any hyphen.
            # For now, just continue on to raise an error. If we need to support
            # this case, a good heuristic might be to find the first hyphen
            # which is immediately followed by a number and split on that.
            _logger.warning("Failed to parse sdist filename %s", filename)
    raise ValueError(f"Not a valid Python package filename: {filename}")
