import distutils.core
import distutils.dist
import logging
import packaging.version
import pathlib
import setuptools
import setuptools.dist
import warnings
from pytest_console_scripts import ScriptRunner
from setuptools_pyproject_migration import Pyproject, WritePyproject
from typing import Optional, Union

try:
    from importlib.metadata import version as im_version
except ModuleNotFoundError:
    # See https://github.com/python/mypy/issues/13914 for why we ignore the error here
    from importlib_metadata import version as im_version  # type: ignore[no-redef]


# Once we drop support for Python 3.6 we can probably remove this check since
# pytest-console-scripts 1.4.0 supports Python 3.7
_new_console_scripts = (
    packaging.version.Version(im_version("pytest-console-scripts")) >= packaging.version.Version("1.4.0")  # fmt: skip
)


_logger = logging.getLogger("setuptools_pyproject_migration:test_support:" + __name__)


class Project:
    """
    A Python project on which ``setup.py pyproject`` can be run. Test code
    should not normally construct instances of ``Project()`` directly;
    instead, they can get one through a fixture or some helper function.

    Once you have the ``Project`` object, create any files you need underneath
    the root by calling :py:meth:`.write()` or one of its convenience wrappers
    like :py:meth:`.setup_py()` or :py:meth:`.setup_cfg()`. If you need to do
    anything other than creating files or if there is some reason not to use
    the ``write()`` method, you can work directly on :py:attr:`.root`, but don't
    change anything outside of ``root``. Finally, when all necessary files have
    been created, call one of :py:meth:`.run()`, :py:meth:`.run_cli()`, or
    :py:meth:`.generate()` to run ``setup.py pyproject`` (or an equivalent) on
    the project.

    :param root:
        The root directory in which to create the project. It should already
        exist. Typically this might be a temporary directory created by pytest's
        ``tmp_path`` fixture.

    :param script_runner:
        The ``script_runner`` fixture from ``pytest-console-scripts``.
    """

    def __init__(self, root: pathlib.Path, script_runner: ScriptRunner) -> None:
        self.root: pathlib.Path = root
        """The directory in which the project is to be created"""
        self.script_runner: ScriptRunner = script_runner
        """The object from the ``script_runner`` fixture from ``pytest-console-scripts``"""

    def write(self, filename: Union[pathlib.Path, str], content: str) -> None:
        """
        Write a file with the given content and the given filename relative to
        the project root. If the file already exists, it will be overwritten after
        issuing a warning.

        :param filename:
            A filename or ``pathlib.Path`` representing the file to write. This should
            be a relative path, which will be interpreted relative to the project root
            directory. If the referenced file is not inside the project root, a warning
            will be issued.

        :param content:
            Text content to write to the file.
        """
        file = (self.root / filename).resolve()
        try:
            file.relative_to(self.root)
        except ValueError:
            warnings.warn("Writing to path {} which is not under project root {}".format(file, self.root))
        if file.exists() and not file.is_dir():
            # This warning message is confusing if the file is a directory, so just go
            # ahead and let the write_text() call fail in that case
            warnings.warn("Overwriting existing file {}".format(file))

        _logger.debug("Writing to %s", file)
        file.write_text(content, encoding="utf-8")

    def setup_cfg(self, content: str) -> None:
        """
        Write a ``setup.cfg`` file in the project root directory.

        :param content:
            Text content to write to the file.
        """
        self.write("setup.cfg", content)

    def setup_py(self, content: Optional[str] = None) -> None:
        """
        Write a ``setup.py`` file in the project root directory.

        :param content:
            Text content to write to the file.
        """
        if content is None:
            content = """
import setuptools

setuptools.setup()
"""
        self.write("setup.py", content)

    def run(self):
        """
        Run ``setup.py pyproject`` on the created project and return the output.

        If the project doesn't already have a ``setup.py`` file, a simple one will be
        automatically created by calling :py:meth:`setup_py()` with no arguments before
        running it.
        """
        if not (self.root / "setup.py").exists():
            self.setup_py()
        _logger.debug("Running python setup.py pyproject in %s", self.root)
        if _new_console_scripts:
            return self.script_runner.run(["setup.py", "pyproject"], cwd=self.root)
        else:
            # pytest-console-scripts<1.4, which requires Python 3.7+, didn't
            # support passing arguments as a list. Once we drop support for
            # Python 3.6 we can discard this branch.
            return self.script_runner.run("setup.py", "pyproject", cwd=self.root)

    def run_cli(self):
        """
        Run the console script ``setup-to-pyproject`` on the created project and
        return the output.

        In contrast to :py:meth:`run()`, if ``setup.py`` doesn't exist, it will
        not be created, because the script is supposed to work without it. If
        you want to test the script's behavior with a ``setup.py`` file, create
        it "manually" with a call to :py:meth:`setup_py()`.
        """
        _logger.debug("Running setup-to-pyproject in %s", self.root)
        if _new_console_scripts:
            return self.script_runner.run(["setup-to-pyproject"], cwd=self.root)
        else:
            # pytest-console-scripts<1.4, which requires Python 3.7+, didn't
            # support passing arguments as a list. Once we drop support for
            # Python 3.6 we can discard this branch.
            return self.script_runner.run("setup-to-pyproject", cwd=self.root)

    def generate(self) -> Pyproject:
        """
        Run the equivalent of ``setup.py pyproject`` but return the generated
        data structure that would go into pyproject.toml instead of writing it
        out.
        """
        if not (self.root / "setup.py").exists():
            self.setup_py()

        # The project fixture should already have set the proper working directory
        assert pathlib.Path.cwd() == self.root

        _logger.debug("Calling distutils.core.run_setup() in %s", self.root)
        distribution: distutils.dist.Distribution = distutils.core.run_setup(
            "setup.py",
            # This should be changed to "commandline" if we start pass meaningful
            # arguments to script_args.
            stop_after="config",
        )
        # run_setup() claims to return a distutils.dist.Distribution, but in
        # practice it seems to return a setuptools.dist.Distribution, which is
        # what we need to pass to WritePyproject(). However, the type checker
        # complains if we don't take some step (like this assertion) to verify
        # that it is in fact a setuptools.dist.Distribution.
        #
        # If this assertion ever fails we will need to find some kind of workaround.
        assert isinstance(distribution, setuptools.dist.Distribution)
        command: WritePyproject = WritePyproject(distribution)
        return command._generate()


class WritePyprojectFactory:
    DEFAULT_NAME = "TestProject"
    DEFAULT_VERSION = "1.2.3"

    def __call__(self, **kwargs) -> WritePyproject:
        """
        Create a :py:class:`WritePyproject` instance initialized from
        a :py:class:`setuptools.dist.Distribution` with the given arguments.
        """

        kwargs.setdefault("name", self.DEFAULT_NAME)
        kwargs.setdefault("version", self.DEFAULT_VERSION)
        return WritePyproject(setuptools.dist.Distribution(kwargs))
