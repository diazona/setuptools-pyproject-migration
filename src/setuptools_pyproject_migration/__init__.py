import setuptools
import sys
import tomlkit
from pep508_parser import parser as pep508
from typing import List, Optional, Tuple


class WritePyproject(setuptools.Command):
    # Each option tuple contains (long name, short name, help string)
    user_options: List[Tuple[str, Optional[str], str]] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        dist: setuptools.dist.Distribution = self.distribution

        # pyproject.toml schema:
        # https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#declaring-project-metadata

        # Enumerate all set-up and build requirements, ensure there are no duplicates
        setup_requirements = set(dist.setup_requires)

        # Is 'setuptools' already there?
        seen_setuptools = False
        for dep in setup_requirements:
            (dep_module, _, _, _) = pep508.parse(dep)
            if dep_module == "setuptools":
                # Yep, here it is!
                seen_setuptools = True
                break

        if not seen_setuptools:
            # We will need it here
            setup_requirements.add("setuptools")

        pyproject = {
            "build-system": {
                "requires": list(sorted(setup_requirements)),
                "build-backend": "setuptools.build_meta",
            }
        }

        pyproject["project"] = {
            "name": dist.get_name(),
            "version": dist.get_version(),  # TODO try to reverse-engineer dynamic version
        }

        # NB: ensure a consistent alphabetical ordering of dependencies
        dependencies = list(sorted(set(dist.install_requires)))
        if dependencies:
            pyproject["project"]["dependencies"] = dependencies

        tomlkit.dump(pyproject, sys.stdout)
