import distutils.core
import distutils.dist
import logging
import os
import packaging.version
import pathlib
import setuptools
import setuptools.dist
import warnings
from setuptools_pyproject_migration import Pyproject, WritePyproject
from typing import Iterable, Optional, Sequence, Union, cast

try:
    # Try importing the third-party package first to get the most up-to-date
    # code if it's available
    import importlib_metadata
except ImportError:
    # Fall back to the version in the standard library, if available
    import importlib.metadata as importlib_metadata

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # type: ignore[assignment]


def is_at_least(distribution_name: str, required_version: Union[packaging.version.Version, str]) -> bool:
    distribution_version: packaging.version.Version = packaging.version.Version(
        importlib_metadata.version(distribution_name)
    )
    if isinstance(required_version, str):
        required_version = packaging.version.Version(required_version)
    return distribution_version >= required_version


_logger = logging.getLogger("setuptools_pyproject_migration:test_support:" + __name__)


class ProjectRunResult(Protocol):
    success: bool
    returncode: int
    stdout: str
    stderr: str


# A callback protocol - like Callable but it lets us specify argument names
class ProjectRunner(Protocol):
    """
    A runner for an external command. This is basically an abstraction of
    ``ScriptRunner.run()`` from `pytest-console-scripts`_, or at least
    the subset of its behavior which we use in this project.

    .. _pytest-console-scripts: https://github.com/kvas-it/pytest-console-scripts/blob/master/pytest_console_scripts/__init__.py
    """  # noqa: E501

    def __call__(self, args: Sequence[str], cwd: Union[str, os.PathLike]) -> ProjectRunResult:
        """
        Run a command.

        If the first argument is an existing Python file, the argument list
        should be prepended with the current Python executable before running
        the command. (This is the behavior of ``ScriptRunner.run()``. It doesn't
        really make a difference unless the Python file is non-executable.)

        :param args: Arguments forming the command to run. The first one should
            generally be either an entry point or a runnable Python script file.
        """
        ...


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
    """

    def __init__(self, root: pathlib.Path) -> None:
        self.root: pathlib.Path = root
        """The directory in which the project is to be created"""

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

    def run(self, runner: ProjectRunner, *, extra_args: Optional[Iterable[str]] = None) -> ProjectRunResult:
        """
        Run ``setup.py pyproject`` on the created project and return the output.

        If the project doesn't already have a ``setup.py`` file, a simple one will be
        automatically created by calling :py:meth:`setup_py()` with no arguments before
        running it.

        :param runner: The callable to use to run the script
        """
        if not (self.root / "setup.py").exists():
            self.setup_py()
        cmdargs = ["setup.py", "pyproject"]
        if extra_args:
            cmdargs.extend(extra_args)
        _logger.debug("Running %r in %s", " ".join(["python"] + cmdargs), self.root)
        return runner(cmdargs, cwd=self.root)

    def run_cli(self, runner: ProjectRunner, *, extra_args: Optional[Iterable[str]] = None) -> ProjectRunResult:
        """
        Run the console script ``setuptools-pyproject-migration`` on the created
        project and return the output.

        In contrast to :py:meth:`run()`, if ``setup.py`` doesn't exist, it will
        not be created, because the script is supposed to work without it. If
        you want to test the script's behavior with a ``setup.py`` file, create
        it "manually" with a call to :py:meth:`setup_py()`.

        :param runner: The callable to use to run the script
        """
        _logger.debug("Running setuptools-pyproject-migration in %s", self.root)
        cmdargs = ["setuptools-pyproject-migration"]
        if extra_args:
            cmdargs.extend(extra_args)
        _logger.debug("Running %r in %s", " ".join(cmdargs), self.root)
        return runner(cmdargs, cwd=self.root)

    def distribution(self, *, extra_args: Optional[Iterable[str]] = None) -> setuptools.dist.Distribution:
        """
        Run ``setup.py`` but stop before actually executing any commands, and
        instead return the ``Distribution`` object.
        """
        if not (self.root / "setup.py").exists():
            self.setup_py()

        # The project fixture should already have set the proper working directory
        assert pathlib.Path.cwd() == self.root

        script_args = ["pyproject"]
        if extra_args:
            script_args += list(extra_args)

        _logger.debug("Calling distutils.core.run_setup(script_args=%r) in %s", script_args, self.root)
        distribution: distutils.dist.Distribution = distutils.core.run_setup(
            "setup.py",
            script_args=script_args,
            stop_after="commandline",
        )
        # run_setup() claims to return a distutils.dist.Distribution, but in
        # practice it seems to return a setuptools.dist.Distribution, which is
        # what we need to pass to WritePyproject(). However, the type checker
        # complains if we don't take some step (like this assertion) to verify
        # that it is in fact a setuptools.dist.Distribution.
        #
        # If this assertion ever fails we will need to find some kind of workaround.
        assert isinstance(distribution, setuptools.dist.Distribution)
        return distribution

    def generate(self, *, extra_args: Optional[Iterable[str]] = None) -> Pyproject:
        """
        Run the equivalent of ``setup.py pyproject`` but return the generated
        data structure that would go into pyproject.toml instead of writing it
        out.
        """

        distribution = self.distribution(extra_args=extra_args)

        # setuptools wants each command class to be a singleton; among other
        # reasons, this means setuptools can automatically set command options
        # as attributes on the single instance of the command class. (See
        # Distribution._set_command_options() for details.) The single instance
        # is supposed to be created by get_command_obj(). So we use that here
        # rather than constructing an instance of the class directly.
        command: WritePyproject = cast(WritePyproject, distribution.get_command_obj("pyproject"))
        assert isinstance(command, WritePyproject)

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
