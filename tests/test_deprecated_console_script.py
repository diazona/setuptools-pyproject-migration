import pytest
import tomlkit

from test_support import ProjectRunner


def test_future_warning(project, console_script_project_runner: ProjectRunner) -> None:
    """
    Test that a ``FutureWarning`` is issued when calling the old script name.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
"""
    project.setup_cfg(setup_cfg)
    with pytest.warns(FutureWarning):
        console_script_project_runner(["setup-to-pyproject"], cwd=project.root)


def test_name_and_version(project, console_script_project_runner: ProjectRunner) -> None:
    """
    Test we can generate a basic project skeleton.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
"""
    expected = tomlkit.parse(
        """\
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.0.1"
"""
    )
    project.setup_cfg(setup_cfg)

    result = console_script_project_runner(["setup-to-pyproject"], cwd=project.root)

    assert result.returncode == 0

    prefix = "running pyproject\n"
    assert result.stdout.startswith(prefix)
    actual = tomlkit.parse(result.stdout[len(prefix) :])
    assert expected == actual
