import distutils.core
import distutils.dist
import packaging.version
import pathlib
import pytest
import setuptools
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


class Project:
    """
    A Python project on which ``setup.py pyproject`` can be run. Tests should get access
    to instances of this class by requesting the :py:func:`project()` fixture.

    Instantiating ``Project`` creates the project under the given root directory, which
    will typically be provided by pytest's ``tmp_path`` fixture. After instantiating
    the ``Project`` object, create files underneath the root by calling methods like
    :py:meth:`.setup_py()` and :py:meth:`.setup_cfg()`, or :py:meth:`.write()` for
    custom filenames. Any unusual cases can be handled by directly operating on
    :py:attr:`.root`. Finally, call :py:meth:`.run()` to run ``setup.py pyproject`` on
    the project.

    :param root:
        The root directory in which to create the project. It should already exist.

    :param script_runner:
        The ``script_runner`` fixture from ``pytest-console-scripts``.
    """

    def __init__(self, root: pathlib.Path, script_runner: ScriptRunner) -> None:
        self.root: pathlib.Path = root
        self.script_runner: ScriptRunner = script_runner

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

        file.write_text(content)

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
        if _new_console_scripts:
            return self.script_runner.run(["setup.py", "pyproject"], cwd=self.root)
        else:
            # pytest-console-scripts<1.4, which requires Python 3.7+, didn't
            # support passing arguments as a list. Once we drop support for
            # Python 3.6 we can discard this branch.
            return self.script_runner.run("setup.py", "pyproject", cwd=self.root)

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


@pytest.fixture
def project(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, script_runner: ScriptRunner) -> Project:
    """
    Creates a temporary directory to serve as the root of a Python project. The returned
    object is an instance of :py:class:`Project`, and the directory can be populated
    with files before invoking ``setup.py pyproject`` with :py:meth:`Project.run()`.
    """
    monkeypatch.chdir(tmp_path)
    return Project(tmp_path, script_runner)
