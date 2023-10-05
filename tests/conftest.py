import os
import pathlib
import pytest
import test_support
from pytest_console_scripts import ScriptRunner
from typing import Iterator, List, Sequence, Union


# Once we drop support for Python 3.6 we can probably remove this check since
# pytest-console-scripts 1.4.0 supports Python 3.7
if test_support.is_at_least("pytest-console-scripts", "1.4.0"):

    def _project_runner_for(script_runner: ScriptRunner) -> test_support.ProjectRunner:
        """
        Return a callable satisfying the :py:class:`test_support.ProjectRunner`
        protocol that delegates to the given :py:class:`pytest_console_scripts.ScriptRunner`.
        """
        return script_runner.run

else:

    def _project_runner_for(script_runner: ScriptRunner) -> test_support.ProjectRunner:
        """
        Return a callable satisfying the :py:class:`test_support.ProjectRunner`
        protocol that delegates to the given :py:class:`pytest_console_scripts.ScriptRunner`.
        """

        def run(args: Sequence[str], cwd: Union[str, os.PathLike]) -> test_support.ProjectRunResult:
            return script_runner.run(*args, cwd=cwd)

        return run


@pytest.fixture
def console_script_project_runner(script_runner: ScriptRunner) -> test_support.ProjectRunner:
    return _project_runner_for(script_runner)


@pytest.fixture
def project(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> test_support.Project:
    """
    Creates a temporary directory to serve as the root of a Python project. The returned
    object is an instance of :py:class:`Project`, and the directory can be populated
    with files before invoking ``setup.py pyproject`` with :py:meth:`Project.run()`.
    """
    monkeypatch.chdir(tmp_path)
    return test_support.Project(tmp_path)


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


_factory_instance: test_support.WritePyprojectFactory = test_support.WritePyprojectFactory()


@pytest.fixture
def make_write_pyproject(in_empty_directory: None) -> test_support.WritePyprojectFactory:
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
