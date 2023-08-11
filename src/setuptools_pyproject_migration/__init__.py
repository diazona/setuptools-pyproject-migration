import itertools
import setuptools
import sys
import tomlkit
from pep508_parser import parser as pep508
from typing import Dict, List, Optional, Tuple, Type, Union

# After we drop support for Python <3.10, we can import TypeAlias directly from typing
from typing_extensions import Required, TypedDict


# PEP 518
BuildSystem: Type = TypedDict("BuildSystem", {"requires": List[str], "build-backend": str}, total=True)

# https://packaging.python.org/en/latest/specifications/declaring-project-metadata/
Contributor: Type = TypedDict("Contributor", {"name": str, "email": str}, total=False)
LicenseFile: Type = TypedDict("LicenseFile", {"file": str})
LicenseText: Type = TypedDict("LicenseText", {"text": str})
ReadmeInfo: Type = TypedDict("ReadmeInfo", {"file": str, "content-type": str})

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
        [{'name': 'John Cleese', 'email': 'john@python.example.com'}, {'name': 'Graham Chapman', 'email': ''}]

        :param: name_string  A string giving a comma-separated list of contributor
                             names.
        :param: email_string A string giving a comma-separated list of contributor
                             email addresses which correspond to the names.
        :returns:            A list of dicts containing corresponding names and
                             email addresses parsed from the strings.
        """
        names = map(WritePyproject._strip_and_canonicalize, (name_string or "").split(","))
        emails = map(WritePyproject._strip_and_canonicalize, (email_string or "").split(","))
        return [{"name": n, "email": e} for n, e in itertools.zip_longest(names, emails, fillvalue="") if n or e]

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

        authors: List[Contributor] = self._transform_contributors(dist.get_author(), dist.get_author_email())
        if authors:
            pyproject["project"]["authors"] = authors

        maintainers: List[Contributor] = self._transform_contributors(
            dist.get_maintainer(), dist.get_maintainer_email()
        )
        if maintainers:
            pyproject["project"]["maintainers"] = maintainers

        # NB: ensure a consistent alphabetical ordering of dependencies
        dependencies = sorted(set(dist.install_requires))
        if dependencies:
            pyproject["project"]["dependencies"] = dependencies

        return pyproject

    def run(self):
        """
        Write out the contents of a pyproject.toml file containing information
        ingested from ``setup.py`` and/or ``setup.cfg``.
        """
        tomlkit.dump(self._generate(), sys.stdout)


__all__ = ["WritePyproject"]
