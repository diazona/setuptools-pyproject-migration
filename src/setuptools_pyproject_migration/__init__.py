import setuptools
import sys
import tomlkit
import json
from pep508_parser import parser as pep508
from typing import Any, Dict, List, Optional, Tuple, Type, Union

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


class DumpMetadata(setuptools.Command):  # pragma: no cover
    """
    Dump the metadata provided in the setup package.  This is a debugging tool
    primarily to figure out what fields are exposed and where they may be
    hiding.
    """
    # Note: excluded from coverage, as this is meant as a debugging fixture.

    # Each option tuple contains (long name, short name, help string)
    user_options: List[Tuple[str, Optional[str], str]] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        metadata: Dict[str, Dict[str, Any]] = {}

        for attr in dir(self.distribution):
            if attr.startswith("_"):
                # Ignore 'protected' members
                continue

            value: Any = getattr(self.distribution, attr)
            if hasattr(value, "__call__"):
                if not attr.startswith("get_"):
                    # Ignore methods that are not "getters"
                    continue

                try:
                    value = value()
                    metadata.setdefault("methods", {})[attr] = self._to_json(value)
                except:
                    continue
            else:
                metadata.setdefault("properties", {})[attr] = self._to_json(value)

        print(json.dumps(metadata, indent=4, sort_keys=True))


    def _to_json(self, v: Any) -> Any:
        if (v is None) or isinstance(v, (bool, int, str)):
            return v
        elif isinstance(v, list):
            return [self._to_json(e) for e in v]
        elif isinstance(v, dict):
            return dict([
                (self._to_json(k), self._to_json(e))
                for k, e
                in v.items()
            ])
        else:
            return repr(v)


class WritePyproject(setuptools.Command):
    # Each option tuple contains (long name, short name, help string)
    user_options: List[Tuple[str, Optional[str], str]] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

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


__all__ = ["WritePyproject", "DumpMetadata"]
