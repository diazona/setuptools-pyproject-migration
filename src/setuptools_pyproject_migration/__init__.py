import setuptools
import sys
import tomlkit


class WritePyproject(setuptools.Command):
    user_options = []

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
