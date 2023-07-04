import setuptools
import sys
import tomlkit
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

        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            }
        }

        pyproject["project"] = {
            "name": dist.get_name(),
            "version": dist.get_version(),  # TODO try to reverse-engineer dynamic version
        }

        tomlkit.dump(pyproject, sys.stdout)
