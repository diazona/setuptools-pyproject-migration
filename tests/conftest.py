import distutils.core
import distutils.dist
import packaging.version
import pathlib
import pytest
import setuptools
import setuptools.dist
import warnings
from pytest_console_scripts import ScriptRunner
from setuptools_pyproject_migration import Pyproject, WritePyproject
from typing import Iterator, List, Optional, Union

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


@pytest.fixture(scope="session")
def _session_empty_directory(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """
    Create an empty temporary directory that persists throughout the entire
    session.

    The directory is returned as a :py:class:`pathlib.Path` which has had
    its write permission removed. While it's technically possible for a caller
    to restore write permission and put something in the directory... don't
    do that.
    """
    empty_tmpdir: pathlib.Path = tmp_path_factory.mktemp("empty")
    # Make the directory read-only to try to prevent accidental creation of files in it.
    # 0o555 gives read and execute (but not write) access to user, group, and others.
    empty_tmpdir.chmod(0o555)
    return empty_tmpdir


# This has to be a function-scoped fixture because it relies on monkeypatch
@pytest.fixture
def in_empty_directory(
    _session_empty_directory: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    """
    Change into an empty directory for the duration of the test.

    The empty directory used is one that persists for the entire session and
    has been set read-only to try to prevent any files from being created in
    it. Test code should not write anything into the directory.
    """

    assert "project" not in request.fixturenames, "in_empty_directory fixture conflicts with project fixture"

    # Change into the session's empty directory
    monkeypatch.chdir(_session_empty_directory)

    # Wait for the test to run
    yield

    # Make sure that the directory is still empty

    # This is inefficient if a large number of files do get written into
    # the directory, but we really shouldn't need to optimize for that case
    dir_contents: List[pathlib.Path] = list(_session_empty_directory.iterdir())
    # fmt: off
    assert not dir_contents, \
        "Files were added to the session's empty directory: " + ", ".join(f.name for f in dir_contents)
    # fmt: on


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


_factory_instance: WritePyprojectFactory = WritePyprojectFactory()


@pytest.fixture
def make_write_pyproject(in_empty_directory: None) -> WritePyprojectFactory:
    """
    Simplify the process of writing tests using a manually instantiated
    :py:class:`setuptools.dist.Distribution`.

    This fixture returns a convenience function that will accept any keyword
    arguments, pass them as a dictionary to ``Distribution()``, and then use
    the created ``Distribution`` instance to create a :py:class:`WritePyproject`.
    Since the keywords ``name`` and ``version`` are mandatory, they will be
    filled in with default values if they are not present in the arguments.
    The default values used are accessible as the ``default_name`` and
    ``default_version`` attributes of the returned object, in case a test needs
    to use them for comparison.

    In addition, this fixture ensures that any test requesting it runs in
    an empty directory, to ensure that the created ``Distribution`` instance
    only takes its attributes from the keyword arguments passed, not from any
    setuptools configuration files that may exist in the working directory.
    If you do want a ``Distribution`` object to use files in the current
    directory as a configuration source, use the :py:func:`project` fixture
    instead.
    """

    return _factory_instance
