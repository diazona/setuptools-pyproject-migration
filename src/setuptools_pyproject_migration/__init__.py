import configparser
import itertools
import logging
import re
import setuptools
import sys
import tomlkit
from packaging.specifiers import SpecifierSet
from pep508_parser import parser as pep508
from setuptools.errors import OptionError
from setuptools_pyproject_migration._long_description import LongDescriptionMetadata
from setuptools_pyproject_migration._types import Contributor, Pyproject
from tomlkit.api import Array, InlineTable
from typing import Dict, List, Optional, Set, Tuple, TypeVar, Union


_logger = logging.getLogger("setuptools_pyproject_migration")


def _parse_entry_point(entry_point: str) -> Tuple[str, str]:
    """
    Extract the entry point and name from the string.

    >>> _parse_entry_point("hello-world = timmins:hello_world")
    ('hello-world', 'timmins:hello_world')
    >>> _parse_entry_point("hello-world=timmins:hello_world")
    ('hello-world', 'timmins:hello_world')
    >>> _parse_entry_point("  hello-world  =  timmins:hello_world  ")
    ('hello-world', 'timmins:hello_world')
    >>> _parse_entry_point("hello-world")
    Traceback (most recent call last):
        ...
    ValueError: Entry point 'hello-world' is not of the form 'name = module:function'

    :param: entry_point The entry point string, of the form
                        "entry_point = module:function" (whitespace optional)
    :returns:           A two-element `tuple`, first element is the entry point name, second element is the target
                        (module and function name) as a string.
    :raises ValueError: An equals (`=`) character was not present in the entry point string.
    """
    if "=" not in entry_point:
        raise ValueError("Entry point %r is not of the form 'name = module:function'" % entry_point)

    (name, target) = entry_point.split("=", 1)
    return (name.strip(), target.strip())


def _generate_entry_points(entry_points: Optional[Union[Dict[str, List[str]], str]]) -> Dict[str, Dict[str, str]]:
    """
    Dump the entry points given, if any.

    >>> _generate_entry_points(None)
    {}
    >>> _generate_entry_points('''
    ...     [type1]
    ...     ep1=mod:fn1
    ...     ep2=mod:fn2
    ...
    ...     [type2]
    ...     ep3=mod:fn3
    ...     ep4=mod:fn4
    ... ''')  # doctest: +NORMALIZE_WHITESPACE
    {'type1': {'ep1': 'mod:fn1', 'ep2': 'mod:fn2'},
     'type2': {'ep3': 'mod:fn3', 'ep4': 'mod:fn4'}}
    >>> _generate_entry_points('''
    ...     [DEFAULT]
    ...     ep0=mod:fn0
    ...
    ...     [type1]
    ...     ep1=mod:fn1
    ...     ep2=mod:fn2
    ...
    ...     [type2]
    ...     ep3=mod:fn3
    ...     ep4=mod:fn4
    ... ''')  # doctest: +NORMALIZE_WHITESPACE
    {'DEFAULT': {'ep0': 'mod:fn0'},
     'type1': {'ep1': 'mod:fn1', 'ep2': 'mod:fn2'},
     'type2': {'ep3': 'mod:fn3', 'ep4': 'mod:fn4'}}
    >>> _generate_entry_points({"type1": ["ep1=mod:fn1", "ep2=mod:fn2"],
    ...                        "type2": ["ep3=mod:fn3", "ep4=mod:fn4"]})  # doctest: +NORMALIZE_WHITESPACE
    {'type1': {'ep1': 'mod:fn1', 'ep2': 'mod:fn2'},
     'type2': {'ep3': 'mod:fn3', 'ep4': 'mod:fn4'}}
    >>> _generate_entry_points({"type1": ["ep1=mod:fn1", "ep2=mod:fn2"],
    ...                        "type2": []})
    {'type1': {'ep1': 'mod:fn1', 'ep2': 'mod:fn2'}}

    :param: entry_points The `entry_points` property from the
                        :py:class:setuptools.dist.Distribution being examined.
    :returns:           The entry points, split up as per
                        :py:func:_parse_entry_point and grouped by entry point type.
    """
    if not entry_points:
        return {}

    parsed_entry_points: Dict[str, Dict[str, str]] = {}

    if isinstance(entry_points, str):
        # INI-style…  `configparser` forbids "empty" section headers (i.e. []; it yields a MissingSectionHeaderError),
        # so we can "exploit" this to force ConfigParser to completely ignore the "DEFAULT" section and treat it like
        # any other section.
        parser = configparser.ConfigParser(default_section="")
        parser.read_string(entry_points)
        for eptype, section in parser.items():
            type_eps = dict(section.items())
            if type_eps:
                parsed_entry_points[eptype] = type_eps
    else:
        # dict
        for eptype, raweps in entry_points.items():
            if raweps:
                parsed_entry_points[eptype] = dict(map(_parse_entry_point, raweps))

    return parsed_entry_points


T = TypeVar("T")


def _tomlkit_inlinify(value: T) -> Union[T, Array, InlineTable]:
    if isinstance(value, list):
        new = tomlkit.array()
        for item in value:
            new.append(_tomlkit_inlinify(item))
        return new
    elif isinstance(value, dict):
        new = tomlkit.inline_table()
        for k, v in value.items():
            new[k] = _tomlkit_inlinify(v)
        return new
    else:
        return value


_MEDIA_TYPE_REGEX = re.compile(
    r"""
    [A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{,126}       # RFC 6838 type-name
    /
    [A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{,126}       # RFC 6838 subtype-name
    (?:
        \s*                                     # optional whitespace (not technically allowed by the RFC
                                                # but we see it in practice)
        ;
        \s*                                     # optional whitespace (not technically allowed by the RFC
                                                # but we see it in practice)
        [A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{,126}   # RFC 2045 attribute
        =
        (?:[^\s]+|"[^"]+")                      # RFC 2045 value
    )*
    """,
    re.VERBOSE,
)


def _looks_like_media_type(value: str) -> bool:
    """
    Return whether the string appears to represent a media type (MIME type).

    For example:

    >>> _looks_like_media_type("text/markdown")
    True
    >>> _looks_like_media_type("text/x-rst")
    True
    >>> _looks_like_media_type("text/plain")
    True

    This doesn't actually check whether the type is a real type that's registered
    with IANA or in common use (use the :py:module:`mimetypes` module for that),
    only whether it follows the syntax of a media type. So even unknown types
    will return true.

    >>> _looks_like_media_type("fake/this-is-not-a-real-type")
    True
    >>> _looks_like_media_type("this-does-not-even-look-like-a-type")
    False

    Parameters can also be included.

    >>> _looks_like_media_type("text/markdown; charset=iso-8859-1; variant=GFM")
    True
    """

    return bool(_MEDIA_TYPE_REGEX.fullmatch(value))


class WritePyproject(setuptools.Command):
    # Each option tuple contains (long name, short name, help string)
    user_options: List[Tuple[str, Optional[str], str]] = [
        (
            "readme-content-type=",
            None,
            (
                "content type to use for the README, or 'auto' if the program should guess; required if the content "
                "type cannot be determined automatically"
            ),
        )
    ]

    def initialize_options(self):
        self.readme_content_type = None

    def finalize_options(self):
        if self.readme_content_type and not _looks_like_media_type(self.readme_content_type):
            raise OptionError(
                f"error in readme_content_type option: {self.readme_content_type} is not a valid content type"
            )

    @staticmethod
    def _strip_and_canonicalize(s: str) -> str:
        """
        Strip whitespace from around a string, but replace the sentinel value
        ``"UNKNOWN"`` (used by setuptools<62.2) with an empty string.

        >>> WritePyproject._strip_and_canonicalize("        ooh, you lucky bastard")
        'ooh, you lucky bastard'
        >>> WritePyproject._strip_and_canonicalize("UNKNOWN")
        ''
        >>> WritePyproject._strip_and_canonicalize("")
        ''
        """
        s = s.strip()
        if s == "UNKNOWN":
            return ""
        else:
            return s

    @staticmethod
    def _transform_contributors(name_string: Optional[str], email_string: Optional[str]) -> List[Contributor]:
        """
        Transform the name and email strings that setuptools uses to specify
        contributors (either authors or maintainers) into a list of dicts of
        the form that should be written into ``pyproject.toml``.

        >>> WritePyproject._transform_contributors("John Cleese", "john@python.example.com")
        [{'name': 'John Cleese', 'email': 'john@python.example.com'}]

        Missing entries will be replaced with the empty string.

        >>> WritePyproject._transform_contributors("John Cleese, Graham Chapman", "john@python.example.com")
        [{'name': 'John Cleese', 'email': 'john@python.example.com'}, {'name': 'Graham Chapman'}]

        :param: name_string  A string giving a comma-separated list of contributor
                             names.
        :param: email_string A string giving a comma-separated list of contributor
                             email addresses which correspond to the names.
        :returns:            A list of dicts containing corresponding names and
                             email addresses parsed from the strings.
        """
        names = map(WritePyproject._strip_and_canonicalize, (name_string or "").split(","))
        emails = map(WritePyproject._strip_and_canonicalize, (email_string or "").split(","))
        contributors = []
        for name, email in itertools.zip_longest(names, emails, fillvalue=""):
            contributor: Contributor = {}
            if name:
                contributor["name"] = name
            if email:
                contributor["email"] = email
            if contributor:
                contributors.append(contributor)
        return contributors

    def _generate(self) -> Pyproject:
        """
        Create the raw data structure containing the information from
        a pyproject.toml file.
        """
        dist: setuptools.dist.Distribution = self.distribution

        # pyproject.toml schema:
        # https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#declaring-project-metadata

        # Enumerate all set-up and build requirements, ensure there are no duplicates
        setup_requirements = set(dist.setup_requires)

        # Is 'setuptools' already there?
        has_setuptools = any(pep508.parse(dep)[0] == "setuptools" for dep in setup_requirements)

        if not has_setuptools:
            # We will need it here
            setup_requirements.add("setuptools")

        pyproject: Pyproject = {
            "build-system": {
                "requires": sorted(setup_requirements),
                "build-backend": "setuptools.build_meta",
            }
        }

        pyproject["project"] = {
            "name": dist.get_name(),
            "version": dist.get_version(),  # TODO try to reverse-engineer dynamic version
        }

        # In older setuptools releases, unspecified license text is replaced with "UNKNOWN"
        license_text = dist.get_license()
        if license_text and (license_text != "UNKNOWN"):
            pyproject["project"]["license"] = _tomlkit_inlinify({"text": license_text})

        authors: List[Contributor] = self._transform_contributors(dist.get_author(), dist.get_author_email())
        if authors:
            pyproject["project"]["authors"] = _tomlkit_inlinify(authors)

        maintainers: List[Contributor] = self._transform_contributors(
            dist.get_maintainer(), dist.get_maintainer_email()
        )
        if maintainers:
            pyproject["project"]["maintainers"] = _tomlkit_inlinify(maintainers)

        keywords: List[str] = dist.get_keywords()
        if keywords:
            pyproject["project"]["keywords"] = keywords

        classifiers: List[str] = dist.get_classifiers()
        if classifiers:
            pyproject["project"]["classifiers"] = classifiers

        urls: Dict[str, str] = dist.metadata.project_urls
        if urls:
            pyproject["project"]["urls"] = urls

        description: str = dist.get_description()
        # "UNKNOWN" is used by setuptools<62.2 when the description in setup.cfg is empty or absent
        if description and description != "UNKNOWN":
            pyproject["project"]["description"] = description

        if dist.get_long_description() not in (None, "UNKNOWN"):
            long_description = LongDescriptionMetadata.from_distribution(
                dist, override_content_type=self.readme_content_type
            )
            pyproject["project"]["readme"] = _tomlkit_inlinify(long_description.pyproject_readme())

        # Technically the dist.python_requires field contains an instance of
        # setuptools.external.packaging.specifiers.SpecifierSet.
        # setuptools.external is a "proxy module" that tries to import something
        # but then falls back to setuptools' own vendored dependencies if it can't
        # find the submodule being imported. So in most cases, if the packaging
        # package is installed, setuptools.external.packaging.specifiers.SpecifierSet
        # will be the same as packaging.specifiers.SpecifierSet, but otherwise it
        # could be a different type, though with the same signature. This probably
        # won't cause any problems for type verification because we will always have
        # packaging installed when doing static type checking. If it causes trouble
        # at runtime, we can fix that as it comes up.
        python_specifiers: Optional[SpecifierSet] = dist.python_requires
        if python_specifiers:
            # SpecifierSet implements a __str__() method that produces a PEP 440-compliant
            # version constraint string, which is exactly what we want here
            pyproject["project"]["requires-python"] = str(python_specifiers)

        _logger.debug("dist.install_requires: %r", dist.install_requires)
        dependencies = set(dist.install_requires)

        _logger.debug("dist.extras_require: %r", dist.extras_require)
        optional_dependencies: Dict[str, Set[str]] = {}
        for extra_dep_key, deps in dist.extras_require.items():
            extra, _, constraint = extra_dep_key.partition(":")
            _logger.debug("Handling extra=%r, constraint=%r", extra, constraint)
            target: Set[str]
            if extra:
                _logger.debug("Adding to optional_dependencies[%r]", extra)
                target = optional_dependencies.setdefault(extra, set())
            else:
                _logger.debug("Adding to dependencies")
                target = dependencies
            for dep in deps:
                if constraint:
                    _logger.debug("Adding dependency %s with constraint %r", dep, constraint)
                    target.add(f"{dep}; {constraint}")
                else:
                    _logger.debug("Adding dependency %s with no constraint", dep)
                    target.add(dep)

        if dependencies:
            # NB: ensure a consistent alphabetical ordering of dependencies
            sorted_dependencies = sorted(dependencies)
            _logger.debug("Setting project.dependencies to: %r", sorted_dependencies)
            pyproject["project"]["dependencies"] = sorted_dependencies

        if optional_dependencies:
            sorted_optional_dependencies = {extra: sorted(deps) for extra, deps in optional_dependencies.items()}
            _logger.debug("Setting project.optional_dependencies to: %r", sorted_optional_dependencies)
            pyproject["project"]["optional-dependencies"] = sorted_optional_dependencies

        entry_points = _generate_entry_points(dist.entry_points)

        # GUI scripts and console scripts go separate in dedicated locations.
        if "console_scripts" in entry_points:
            pyproject["project"]["scripts"] = entry_points.pop("console_scripts")

        if "gui_scripts" in entry_points:
            pyproject["project"]["gui-scripts"] = entry_points.pop("gui_scripts")

        # Anything left over gets put in entry-points
        if entry_points:
            pyproject["project"]["entry-points"] = entry_points

        return pyproject

    def run(self):
        """
        Write out the contents of a pyproject.toml file containing information
        ingested from ``setup.py`` and/or ``setup.cfg``.
        """
        tomlkit.dump(self._generate(), sys.stdout)


__all__ = ["WritePyproject"]
