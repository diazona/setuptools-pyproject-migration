import itertools
import mimetypes
import setuptools
import sys
import tomlkit
import warnings
from packaging.specifiers import SpecifierSet
from pep508_parser import parser as pep508
from tomlkit.api import Array, InlineTable
from typing import Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

# After we drop support for Python <3.10, we can import TypeAlias directly from typing
from typing_extensions import Required, TypedDict


# PEP 518
BuildSystem: Type = TypedDict("BuildSystem", {"requires": List[str], "build-backend": str}, total=True)

# https://packaging.python.org/en/latest/specifications/declaring-project-metadata/
Contributor: Type = TypedDict("Contributor", {"name": str, "email": str}, total=False)
LicenseFile: Type = TypedDict("LicenseFile", {"file": str})
LicenseText: Type = TypedDict("LicenseText", {"text": str})
ReadmeInfo: Type = TypedDict("ReadmeInfo", {"file": str, "content-type": str})


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


def _generate_entry_points(entry_points: Optional[Dict[str, List[str]]]) -> Dict[str, Dict[str, str]]:
    """
    Dump the entry points given, if any.

    >>> _generate_entry_points(None)
    {}
    >>> _generate_entry_points({"type1": ["ep1=mod:fn1", "ep2=mod:fn2"],
    ...                        "type2": ["ep3=mod:fn3", "ep4=mod:fn4"]})
    {'type1': {'ep1': 'mod:fn1', 'ep2': 'mod:fn2'}, 'type2': {'ep3': 'mod:fn3', 'ep4': 'mod:fn4'}}

    :param: entry_points The `entry_points` property from the
                        :py:class:setuptools.dist.Distribution being examined.
    :returns:           The entry points, split up as per
                        :py:func:_parse_entry_point and grouped by entry point type.
    """
    if not entry_points:
        return {}

    parsed_entry_points: Dict[str, Dict[str, str]] = {}

    for eptype, raweps in entry_points.items():
        parsed_entry_points[eptype] = dict(map(_parse_entry_point, raweps))

    return parsed_entry_points


Project: Type = TypedDict(
    "Project",
    {
        "authors": List[Contributor],
        "classifiers": List[str],
        "dependencies": List[str],
        "description": str,
        "dynamic": List[str],
        "entry-points": Dict[str, Dict[str, str]],
        "gui-scripts": Dict[str, str],
        "keywords": List[str],
        "license": Union[LicenseFile, LicenseText],
        "maintainers": List[Contributor],
        "name": Required[str],
        "optional-dependencies": Dict[str, List[str]],
        "readme": Union[str, ReadmeInfo],
        "requires-python": str,
        "scripts": Dict[str, str],
        "urls": Dict[str, str],
        "version": str,
    },
    total=False,
)

Pyproject: Type = TypedDict("Pyproject", {"build-system": BuildSystem, "project": Project}, total=False)
"""
The type of the data structure stored in a ``pyproject.toml`` file. This only
includes the build system and core metadata portions, i.e. the ``build-system``
and ``project`` tables. The data structure may contain other entries that are
not constrained by this type.
"""

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


class WritePyproject(setuptools.Command):
    # Each option tuple contains (long name, short name, help string)
    user_options: List[Tuple[str, Optional[str], str]] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

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

    @staticmethod
    def _guess_readme_extension(content_type: str) -> Optional[str]:
        """
        Return the file extension that most canonically implies the given content
        type, focused mainly on content types that might plausibly be used for
        a README file. In particular, it respects the two mappings between
        content type and extension that are specified in `the packaging spec for
        ``pyproject.toml`` <https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#readme>`_:

        >>> WritePyproject._guess_readme_extension("text/markdown")
        '.md'
        >>> WritePyproject._guess_readme_extension("text/x-rst")
        '.rst'

        Plain text is also a common type. For explicitness, this returns an actual
        extension rather than omitting one, even though a file named just
        ``README`` will generally also be understood as plain text:

        >>> WritePyproject._guess_readme_extension("text/plain")
        '.txt'

        Any `parameters <https://packaging.python.org/en/latest/specifications/core-metadata/#description-content-type>`_
        present will be ignored.

        >>> WritePyproject._guess_readme_extension("text/markdown; charset=iso-8859-1; variant=GFM")
        '.md'
        >>> WritePyproject._guess_readme_extension("text/x-rst; charset=ascii")
        '.rst'
        >>> WritePyproject._guess_readme_extension("text/plain; charset=utf-8")
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
            long_description_source: str

            if "metadata" in dist.command_options:
                long_description_source = dist.command_options["metadata"]["long_description"][1]
            else:
                long_description_source = dist.get_long_description()

            long_description_content_type: Optional[str] = dist.metadata.long_description_content_type

            assert long_description_source

            filename: str
            if long_description_source.startswith("file:"):
                filename = long_description_source[5:].strip()
            else:
                filename = "README"
                if long_description_content_type:
                    extension: Optional[str] = self._guess_readme_extension(long_description_content_type)
                    if extension:
                        filename += extension
                    else:
                        warnings.warn(f"Could not guess extension for content type {long_description_content_type}")
                # If the long description is a hard-coded string, we need to write it out to
                # a file because pyproject.toml only allows specifying a filename, not a string.
                with open(filename, "w") as f:
                    f.write(long_description_source)

            if long_description_content_type:
                pyproject["project"]["readme"] = _tomlkit_inlinify(
                    {"file": filename, "content-type": long_description_content_type}
                )

            else:
                # By setting readme_info to a string, we can avoid making any assumptions about
                # the content type. The general approach in this package is to directly
                # translate the information from setuptools without injecting additional
                # information not provided by the user.
                pyproject["project"]["readme"] = filename

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

        # NB: ensure a consistent alphabetical ordering of dependencies
        dependencies = sorted(set(dist.install_requires))
        if dependencies:
            pyproject["project"]["dependencies"] = dependencies

        optional_dependencies: Dict[str, Set[str]] = {}
        for extra_dep_key, deps in dist.extras_require.items():
            extra, _, constraint = extra_dep_key.partition(":")
            optional_dependencies.setdefault(extra, set())
            for dep in deps:
                if constraint:
                    optional_dependencies[extra].add(f"{dep}; {constraint}")
                else:
                    optional_dependencies[extra].add(dep)
        if optional_dependencies:
            pyproject["project"]["optional-dependencies"] = {
                extra: sorted(deps) for extra, deps in optional_dependencies.items()
            }

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
