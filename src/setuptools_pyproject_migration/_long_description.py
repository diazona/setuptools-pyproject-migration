"""
Code for computing the long description and its content type.
"""

import dataclasses
import glob
import logging
import mimetypes
import pathlib
import setuptools.dist
import warnings

from setuptools_pyproject_migration._types import ReadmeFile, ReadmeText
from typing import Optional, Union


_logger = logging.getLogger("setuptools_pyproject_migration")


@dataclasses.dataclass
class LongDescriptionMetadata:
    """
    Metadata related to the long description.
    """

    text: str
    """The raw description text."""

    content_type: Optional[str] = None
    """The content type associated with the description."""

    path: Optional[pathlib.Path] = None
    """The path to a file whose content is the description text."""

    @staticmethod
    def from_distribution(
        dist: setuptools.dist.Distribution, *, override_content_type: Optional[str] = None
    ) -> "LongDescriptionMetadata":
        """
        Construct a ``LongDescriptionMetadata`` object by reading the metadata
        from a ``Distribution``.

        :param dist: The ``Distribution`` from which to compute the long
            description metadata.
        :param content_type: Override the computed content type of the long
            description, or ``None`` to skip any override and raise an error
            if no content type could be determined.
        :raise RuntimeError: If no content type could be determined either from
            ``override_content_type`` or from the distribution metadata.
        """
        text: str
        content_type: Optional[str] = dist.metadata.long_description_content_type
        path: Optional[pathlib.Path]

        if override_content_type:
            if content_type and content_type != override_content_type:
                _logger.warning("Overriding original content type %s with %s", content_type, override_content_type)
            content_type = override_content_type

        raw: str = _raw_long_description_value(dist)

        if raw.startswith("file:"):
            path = pathlib.Path(raw[5:].strip())
            text = _read_long_description_file(path)
        else:
            # We don't have access to the filename, so we have to use some
            # heuristics to either guess what it should be or come up with
            # a reasonable filename of our own.
            path = _guess_path(dist, raw, content_type)
            text = raw

        if path and content_type:
            return LongDescriptionMetadata(text, content_type, path)
        elif content_type:
            assert not raw.startswith("file:")
            return LongDescriptionMetadata(text, content_type)
        elif path and path.suffixes:
            # We can get away without having a content type if it can likely
            # be inferred from the filename. We don't have to do the inferring
            # ourselves in that case; whatever reads pyproject.toml should be
            # able to do it.
            return LongDescriptionMetadata(text, path=path)
        else:
            warnings.warn("Assuming content type of text/plain for long_description")
            return LongDescriptionMetadata(text, content_type="text/plain")

    def pyproject_readme(self) -> Union[str, ReadmeFile, ReadmeText]:
        """
        Compute the value that should be added to the ``pyproject.readme`` entry
        in ``pyproject.toml`` to represent this long description.

        >>> LongDescriptionMetadata("Description", "text/plain", pathlib.Path("readme.txt")).pyproject_readme()
        {'file': 'readme.txt', 'content-type': 'text/plain'}
        >>> LongDescriptionMetadata("Description", "text/plain", None).pyproject_readme()
        {'text': 'Description', 'content-type': 'text/plain'}

        This class does not make any assumptions about the content type, so it
        will not emit a content type if one was not provided, but in that case
        the filename needs to have an extension so that consumers will be able to
        infer it from that extension.

        >>> LongDescriptionMetadata("Description", None, pathlib.Path("readme.txt")).pyproject_readme()
        'readme.txt'
        """
        if self.content_type:
            if self.path:
                return {"file": str(self.path), "content-type": self.content_type}
            else:
                return {"text": self.text, "content-type": self.content_type}
        else:
            # We should never get to a situation where there is no content type
            # stored in this object unless the content type can be inferred from
            # the filename.
            if not (self.path and self.path.suffixes):
                raise ValueError(f"No content type provided or can be inferred from filename {self.path}")
            return str(self.path)


def _raw_long_description_value(dist: setuptools.dist.Distribution) -> str:
    """
    Return the raw value of the ``long_description`` option given to setuptools.

    This will be either the value in ``setup.cfg``, or the value passed to
    the ``setup()`` function.
    """
    try:
        # If this is present, it contains the raw text value of the
        # long_description option from setup.cfg. (Or, it should. Otherwise we'd
        # have to manually parse setup.cfg to get it.) If it names a file,
        # get_long_description() should give the string obtained by
        # reading the file.
        return dist.command_options["metadata"]["long_description"][1]
    except KeyError:
        # If the option comes from setup.py then get_long_description()
        # gives us the raw value instead. We can't necessarily get the
        # filename this way because setup() might never receive the
        # filename if the file was read directly by setup.py.
        return dist.get_long_description()


def _read_long_description_file(path: pathlib.Path) -> str:
    """
    Read the content of the long description from a filename.
    """
    # TODO handle multiple comma-separated filenames
    return path.read_text()


def _guess_path(
    dist: setuptools.dist.Distribution, long_description: str, content_type: Optional[str]
) -> Optional[pathlib.Path]:
    """
    Try to find or guess the file path for the long description.

    This uses various heuristics to try to find a file that contains the long
    description text, or if it can't be found, to create one with the right
    extension and write the long description into it.

    :return: The path to a file which exists and contains the long description
        text, or ``None`` if no such file could be found or created.
    """
    path: Optional[pathlib.Path]
    path = _guess_path_from_description_file(dist, long_description)
    if path:
        return path
    path = _guess_path_from_content(long_description)
    if path:
        return path
    return None


def _guess_path_from_description_file(
    dist: setuptools.dist.Distribution, long_description: str
) -> Optional[pathlib.Path]:
    """
    Try to get the ``long_description`` filename from ``description_file``
    metadata.

    ``description_file`` is a metadata element which some packages (mostly
    older ones) use `for compatibility with pbr
    <https://docs.openstack.org/pbr/latest/user/features.html#long-description>`_,
    an old ``setuptools`` extension.

    :return: The path obtained from the ``description_file`` metadata element,
        otherwise ``None``.
    """
    try:
        return pathlib.Path(dist.command_options["metadata"]["description_file"][1])
    except KeyError:
        return None


def _guess_path_from_content(long_description: str) -> Optional[pathlib.Path]:
    """
    Try to get the ``long_description`` path by checking the filesystem for
    a file whose contents matches the long description.

    This will look for some common filenames, and for any which are found,
    it will check their contents against the given long description. If
    there's a match, we assume that's the file. The list of filenames
    checked includes at least ``README.*``, and can be expanded over time as
    we find other paths which make sense to check.

    :return: The path to a file whose contents matches the long description,
        or ``None`` if not found.
    """
    for filename in glob.glob("README.*") + ["README"]:
        path = pathlib.Path(filename)
        if path.exists() and path.read_text() == long_description:
            return path
    return None


def _guess_readme_extension(content_type: str) -> Optional[str]:
    """
    Return the file extension that most canonically implies the given content
    type, focused mainly on content types that might plausibly be used for
    a README file. In particular, it respects the two mappings between
    content type and extension that are specified in `the packaging spec for
    ``pyproject.toml`` <https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#readme>`_:

    >>> _guess_readme_extension("text/markdown")
    '.md'
    >>> _guess_readme_extension("text/x-rst")
    '.rst'

    Plain text is also a common type. For explicitness, this returns an actual
    extension rather than omitting one, even though a file named just
    ``README`` will generally also be understood as plain text:

    >>> _guess_readme_extension("text/plain")
    '.txt'

    Any `parameters <https://packaging.python.org/en/latest/specifications/core-metadata/#description-content-type>`_
    present will be ignored.

    >>> _guess_readme_extension("text/markdown; charset=iso-8859-1; variant=GFM")
    '.md'
    >>> _guess_readme_extension("text/x-rst; charset=ascii")
    '.rst'
    >>> _guess_readme_extension("text/plain; charset=utf-8")
    '.txt'
    """  # noqa: E501

    content_type = content_type.lower().partition(";")[0]
    # .md and .rst are called out specifically in the packaging specification
    # https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#readme
    if content_type == "text/markdown":
        return ".md"
    elif content_type == "text/x-rst":
        return ".rst"
    # Python <3.8 returns an arbitrary one from among all extensions associated
    # with the content type, so we override it to return the most likely one for
    # common README content types
    # - https://github.com/python/cpython/issues/40993
    # - https://github.com/python/cpython/issues/51048
    elif content_type == "text/plain":
        return ".txt"
    else:
        return mimetypes.guess_extension(content_type)
