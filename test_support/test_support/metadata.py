"""
Code for manipulating core metadata
"""

import logging
import packaging.specifiers
import packaging.version
import re

from collections import defaultdict
from test_support import importlib_metadata
from typing import Callable, Dict, List, Optional, Tuple, Union

try:
    from functools import cache
except ImportError:
    import functools

    cache = functools.lru_cache(maxsize=128)


try:
    from pyproject_metadata import License, Readme, RFC822Message, StandardMetadata
except ImportError:
    # pyproject-metadata is not available for Python <3.7. That's okay because
    # we skip all the tests that would use RFC822Message if pyproject-metadata
    # is not available, so that name doesn't need to have a definition that is
    # valid at runtime, but pytest still scans this file looking for doctests
    # so it still needs to be importable. As long as this name is defined as
    # _something_ which is a valid type, that will be the case.

    class License:  # type: ignore[no-redef]
        pass

    class Readme:  # type: ignore[no-redef]
        pass

    class RFC822Message:  # type: ignore[no-redef]
        pass

    class StandardMetadata:  # type: ignore[no-redef]
        pass


_logger = logging.getLogger("setuptools_pyproject_migration:test_support:" + __name__)


def _parse_contributors(
    name_field: str, names: List[str], email_field: str, emails: List[str]
) -> List[Tuple[str, str]]:
    if not names and not emails:
        return []
    # NOTE: this may not be the right algorithm for handling missing names or
    # emails, but if necessary we'll fix it up later
    elif not emails:
        if len(names) != 1:
            raise ValueError(f"Multiple values for {name_field}")
        # If people have names that start or end in whitespace, I'm really not
        # sure what to do here, but we'll figure that out if necessary
        return [(n.strip(), "") for n in names[0].split(",")]
    elif not names:
        if len(emails) != 1:
            raise ValueError(f"Multiple values for {email_field}")
        return [("", e.strip()) for e in emails[0].split(",")]
    else:
        if len(names) != 1:
            raise ValueError(f"Multiple values for {name_field}")
        if len(emails) != 1:
            raise ValueError(f"Multiple values for {email_field}")
        split_names = (n.strip() for n in names[0].split(","))
        split_emails = (e.strip() for e in emails[0].split(","))
        return [(n, e) for n, e in zip(split_names, split_emails)]


_extra_pattern = re.compile(r"""extra\s*==\s*['"](?P<extra>[a-z0-9]|[a-z0-9]([a-z0-9-](?!--))*[a-z0-9])['"]""")


def parse_core_metadata(message: Union[RFC822Message, importlib_metadata.PackageMetadata]) -> StandardMetadata:
    """
    Parse core metadata from a message.

    The message should be parsed from something like a ``PKG-INFO`` file.
    """

    has: Callable[[str], bool]
    get: Callable[[str, Optional[List[str]]], List[str]]

    if isinstance(message, RFC822Message):

        def has(name: str) -> bool:
            return name in message.headers

        def get(name: str, default: Optional[List[str]] = None) -> List[str]:
            try:
                return message.headers[name]
            except KeyError:
                if default is None:
                    raise
                else:
                    return default

    else:

        def has(name: str) -> bool:
            return message[name] is not None

        def get(name: str, default: Optional[List[str]] = None) -> List[str]:
            value = message.get_all(name)
            if value is not None:
                return value
            elif default is not None:
                return default
            else:
                raise KeyError(name)

    # The variables being assigned to are taken from the project metadata
    # specification and are listed in the same order they appear on that page.
    # https://packaging.python.org/en/latest/specifications/declaring-project-metadata/
    #
    # The `message` field names are the corresponding core metadata fields.
    # https://packaging.python.org/en/latest/specifications/core-metadata/

    _metadata_version_raw = get("Metadata-Version")
    if len(_metadata_version_raw) != 1:
        raise ValueError("Multiple values for Metadata-Version")
    elif _metadata_version_raw[0] not in ("1.0", "1.1", "1.2", "2.1", "2.2", "2.3"):
        raise ValueError("Invalid or unsupported Metadata-Version {}".format(_metadata_version_raw[0]))

    metadata_version = packaging.version.Version(_metadata_version_raw[0])

    @cache
    def is_at_least(required: str, *, v=metadata_version):
        return v >= packaging.version.Version(required)

    name = get("Name")[0]

    if get("Version"):
        version = packaging.version.Version(get("Version")[0])
    else:
        version = None

    description = get("Summary")[0]

    _readme_text: Optional[str]
    try:
        _readme_text = get("Description")[0]
    except KeyError:
        if is_at_least("2.1") and message.body:
            _readme_text = message.body
        else:
            _readme_text = None

    if is_at_least("2.1") and has("Description-Content-Type"):
        _readme_content_type = get("Description-Content-Type")[0]
    else:
        # TODO use text/x-rst; charset=UTF-8 if Description is valid RST, otherwise text/plain
        _readme_content_type = "text/plain"

    readme: Optional[Readme] = Readme(_readme_text, None, _readme_content_type) if _readme_text else None

    requires_python: Optional[packaging.specifiers.SpecifierSet] = None
    if is_at_least("1.2"):
        try:
            _requires_python_raw = get("Requires-Python")[0]
        except KeyError:
            pass
        else:
            requires_python = packaging.specifiers.SpecifierSet(_requires_python_raw)

    license = License(get("License")[0], None)

    authors = _parse_contributors("Author", get("Author", []), "Author-email", get("Author-email", []))

    maintainers: List[Tuple[str, str]]
    if is_at_least("1.2"):
        maintainers = _parse_contributors(
            "Maintainer", get("Maintainer", []), "Maintainer-email", get("Maintainer-email", [])
        )
    else:
        maintainers = []

    keywords: List[str]
    # Up through version 1.2 of the core metadata specification (PEP 241, 314, 345),
    # the examples show space-separated keywords, but the current version of the spec
    # says that they should be comma-separated, and notes that setuptools and
    # distutils had been using commas all along. It's unclear when exactly it became
    # non-compliant to use spaces in this field, but v2 of the spec seems like as
    # good a guess as any. If we find real-world examples of packages with v2 core
    # metadata that are using space-separated keywords, we can adjust this accordingly.
    raw_keywords: List[str] = get("Keywords", [])
    _logger.debug("Handling Keywords: %r", raw_keywords)
    if len(raw_keywords) == 1:
        if is_at_least("2.0"):
            _logger.debug("Splitting keywords on commas")
            kwsplit_pattern = r","
        else:
            _logger.debug("Splitting keywords on commas or spaces")
            kwsplit_pattern = r"\s+|,"
        keywords = [kw.strip() for kw in re.split(kwsplit_pattern, raw_keywords[0])]
    else:
        # Either there are no keywords, or there are multiple Keywords entries in
        # the core metadata, suggesting that whatever build backend produced this
        # package was kind enough to split the keywords into separate headers for us.
        _logger.debug("Not splitting keywords")
        keywords = raw_keywords

    classifiers: List[str]
    if is_at_least("1.1"):
        classifiers = get("Classifier", [])
    else:
        classifiers = []

    urls: Dict[str, str] = {}
    if is_at_least("1.2"):
        for s in get("Project-URL", []):
            _label, _, _url = s.partition(",")
            urls[_label.strip()] = _url.strip()

    dependencies: List[packaging.requirements.Requirement] = []
    optional_dependencies: Dict[str, List[packaging.requirements.Requirement]]

    if is_at_least("1.2") and has("Requires-Dist"):
        if is_at_least("2.1"):
            optional_dependencies = {e: [] for e in get("Provides-Extra", [])}
        else:
            optional_dependencies = defaultdict(list)

        for dist in get("Requires-Dist"):
            _logger.debug("Handling Requires-Dist: %s", dist)
            req = packaging.requirements.Requirement(dist)
            if req.marker:
                m = _extra_pattern.search(str(req.marker))
                if m:
                    _extra_name = m.group("extra")
                    assert _extra_name
                    _logger.debug("Adding optional dependency %r with extra %s", req, _extra_name)
                    try:
                        optional_dependencies[_extra_name].append(req)
                    except KeyError:
                        raise ValueError(f"Unknown extra {_extra_name}")
                else:
                    _logger.debug("Adding dependency %r (marker is not an extra)", req)
                    dependencies.append(req)
            else:
                _logger.debug("Adding dependency %r (no marker)", req)
                dependencies.append(req)
        if isinstance(optional_dependencies, defaultdict):
            optional_dependencies = dict(optional_dependencies)
    elif is_at_least("1.1") and has("Requires"):
        dependencies = [packaging.requirements.Requirement(dist) for dist in get("Requires")]
        optional_dependencies = {}

    dynamic: List[str]
    if is_at_least("2.2"):
        dynamic = message.headers.get("Dynamic", [])
    else:
        dynamic = []

    # These are not part of core metadata
    scripts: Dict[str, str] = {}
    gui_scripts: Dict[str, str] = {}
    entry_points: Dict[str, Dict[str, str]] = {}

    return StandardMetadata(
        name,  # will be normalized by StandardMetadata.__post_init__()
        version,
        description,
        license,
        readme,
        requires_python,
        dependencies,
        optional_dependencies,
        entry_points,
        authors,
        maintainers,
        urls,
        classifiers,
        keywords,
        scripts,
        gui_scripts,
        dynamic,
    )
