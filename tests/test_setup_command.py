import tomlkit


def check_result(result, reference, prefix="running pyproject\n"):
    """
    Check the result succeeded, and matches the expected output.
    """
    assert result.returncode == 0
    assert result.stdout.startswith(prefix)

    # Parse the reference in case of formatting differences
    reference_parsed = tomlkit.parse(reference)

    # Parse the resultant text:
    result_parsed = tomlkit.parse(result.stdout[len(prefix) :])

    # Assert equivalence
    assert result_parsed == reference_parsed


def test_name_and_version(project) -> None:
    """
    Test we can generate a basic project skeleton.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
"""
    pyproject_toml = """\
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.0.1"
"""
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.run()
    check_result(result, pyproject_toml)


# install_requires tests, we use made-up module names here.


def test_install_requires(project) -> None:
    """
    Test the install_requires is passed through if given.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
install_requires =
        dependency1
        dependency2>=1.23
        dependency3<4.56
"""
    pyproject_toml = """\
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.0.1"
dependencies = ["dependency1", "dependency2>=1.23", "dependency3<4.56"]
"""
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.run()
    check_result(result, pyproject_toml)


# setup_requires tests: we have to use real dependencies that actually are
# installed, otherwise the tests will fail.


def test_setup_requires(project) -> None:
    """
    Test setup_requires is passed through with 'setuptools' dependency.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
setup_requires =
        sphinx
        pytest>=6
        pytest-black<99.88.77
"""
    pyproject_toml = """\
[build-system]
requires = ["pytest-black<99.88.77", "pytest>=6", "setuptools", "sphinx"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.0.1"
"""
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.run()
    check_result(result, pyproject_toml)


def test_setup_requires_setuptools(project) -> None:
    """
    Test that we don't duplicate 'setuptools' in build requirements
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
setup_requires =
        setuptools
        sphinx
        pytest>=6
        pytest-black<99.88.77
"""
    pyproject_toml = """\
[build-system]
requires = ["pytest-black<99.88.77", "pytest>=6", "setuptools", "sphinx"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.0.1"
"""
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.run()
    check_result(result, pyproject_toml)


def test_setup_requires_setuptools_version(project) -> None:
    """
    Test we can handle a build system that requires a specific setuptools version.
    """
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1

[options]
setup_requires =
        setuptools>=34.56
        sphinx
        pytest>=6
        pytest-black<99.88.77
"""
    pyproject_toml = """\
[build-system]
requires = ["pytest-black<99.88.77", "pytest>=6", "setuptools>=34.56", "sphinx"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.0.1"
"""
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.run()
    check_result(result, pyproject_toml)
