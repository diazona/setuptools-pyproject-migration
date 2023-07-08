import pathlib
import pytest
import warnings
from pytest_console_scripts import ScriptRunner
from typing import Optional, Union


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
        return self.script_runner.run(["setup.py", "pyproject"], cwd=self.root)


@pytest.fixture
def project(tmp_path: pathlib.Path, script_runner: ScriptRunner) -> Project:
    """
    Creates a temporary directory to serve as the root of a Python project. The returned
    object is an instance of :py:class:`Project`, and the directory can be populated
    with files before invoking ``setup.py pyproject`` with :py:meth:`Project.run()`.
    """
    return Project(tmp_path, script_runner)
