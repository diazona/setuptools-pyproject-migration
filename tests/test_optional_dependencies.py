from typing import Dict, List, Mapping, Sequence


def _normalize(optional_dependencies: Mapping[str, Sequence[str]], deduplicate: bool = True) -> Dict[str, List[str]]:
    """
    Normalize a representation of optional dependencies by converting the list
    of dependencies for each extra to a set. This ensures that variations in
    the order in which dependencies are listed won't affect the comparison
    result.
    """
    if deduplicate:
        return {extra: sorted(set(deps)) for extra, deps in optional_dependencies.items()}
    else:
        return {extra: sorted(deps) for extra, deps in optional_dependencies.items()}


def test_one_extra(make_write_pyproject) -> None:
    """
    Test that optional dependencies are handled properly when there is one extra.
    """
    optional_dependencies = {"lindisfarne": ["egg", "bacon"]}
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(optional_dependencies)


def test_multiple_extras(make_write_pyproject) -> None:
    """
    Test that optional dependencies are handled properly when there is more than
    one extra.
    """
    optional_dependencies = {
        "clontarf": ["egg", "sausage", "bacon"],
        "frisia": ["egg", "spam"],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(optional_dependencies)


def test_version_constraints_and_environment_markers(make_write_pyproject) -> None:
    """
    Test that dependencies with version constraints and environment markers are
    handled properly.
    """
    optional_dependencies = {
        "asselt": [
            "egg>=0.2",
            'sausage; python_version == "3.6"',
            'spam>=1.1; python_version < "3.10" and platform_system == "Windows" and implementation_name == "cpython"',
        ],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(optional_dependencies)


def test_extra_name_with_special_characters(make_write_pyproject) -> None:
    """
    Test that the name of an extra can include a space and punctuation.
    """
    optional_dependencies = {"hengest's hill": ["egg", "bacon", "sausage", "spam"]}
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(optional_dependencies)


def test_deduplication(make_write_pyproject) -> None:
    """
    Test that dependencies are deduplicated. Even if a dependency is listed more
    than once in the setuptools configuration, it should only appear once in
    ``pyproject.toml``.
    """
    optional_dependencies = {
        "edington": ["spam", "bacon", "sausage", "spam"],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    actual = _normalize(result["project"]["optional-dependencies"], deduplicate=False)  # keep duplicates here
    expected = _normalize(optional_dependencies, deduplicate=True)
    assert actual == expected


def test_version_formatting_normalization(make_write_pyproject) -> None:
    """
    Test that dependencies with version constraints which are semantically
    equivalent are deduplicated even if they are formatted differently.
    """
    optional_dependencies = {
        "maldon": ["spam >= 2", "egg", "spam>=2"],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    expected = {"maldon": ["egg", "spam>=2"]}
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(expected)


def test_environment_marker_normalization(make_write_pyproject) -> None:
    """
    Test that dependencies with environment markers which are semantically
    equivalent due to normalization of environment variables are deduplicated.

    The only environment variable subject to this normalization is
    ``python_implementation``, which is a deprecated setuptools-specific
    variable that gets converted to ``platform_python_implementation`` by code
    in ``packaging``. (See
    `packaging issue #72 <https://github.com/pypa/packaging/issues/72>`_.)

    """
    optional_dependencies = {
        "holme": ["spam; python_implementation=='CPython'", "bacon", "spam; platform_python_implementation=='CPython'"],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    expected = {"holme": ["bacon", 'spam; platform_python_implementation == "CPython"']}
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(expected)


def test_environment_marker_formatting_normalization(make_write_pyproject) -> None:
    """
    Test that dependencies with environment markers which are semantically
    equivalent are deduplicated even if they are formatted differently.
    """
    optional_dependencies = {
        "cynwit": [
            "spam; python_version>'3.6'",
            'spam; python_version>"3.6"',
            "spam; python_version   >   '3.6'",
            "egg",
            "spam;python_version>'3.6'",
        ],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    expected = {"cynwit": ['spam; python_version > "3.6"', "egg"]}
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(expected)


def test_intersecting_specifications(make_write_pyproject) -> None:
    """
    Test that multiple dependency specifications with different version
    constraints and environment markers are preserved.
    """
    optional_dependencies = {
        "danelaw": [
            "spam",
            "spam>=1.2",
            "spam<2",
            'spam>=1.4; python_version >= "3.5"',
            'spam>=1.5; python_version < "3.10"',
            'spam!=1.14,>=1.7; python_version == "3.8" and platform_system == "Linux"',
            "baked-beans",
            'spam!=1.9.1; python_version < "3.7" and platform_system == "Windows" and implementation_name == "cpython"',
            'spam<1.14; platform_system == "Linux" and platform_python_implementation == "CPython"',
            'spam>1.7.1; python_version < "3.9" and python_version > "3.6" and implementation_name == "pypy"',
            'spam<1.15; python_version < "3.10"',
        ],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(optional_dependencies)


def test_environment_markers(make_write_pyproject) -> None:
    """
    Test that environment markers are handled appropriately.
    """
    optional_dependencies = {
        "stamford bridge": [
            "lobster-thermidor-aux-crevettes",
            "mornay-sauce",
            "shallots",
            "aubergines",
            "truffle-pate",
            "brandy",
            'fried-egg; python_version >= "4.1"',
            "spam",
        ],
    }
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    assert _normalize(result["project"]["optional-dependencies"]) == _normalize(optional_dependencies)


def test_optional_dependencies_empty_deps(make_write_pyproject) -> None:
    """
    Test that optional dependencies where the list of dependencies is empty are
    handled properly. This situation is common when a package removes all
    the dependencies associated with an extra; the setuptools documentation
    recommends keeping the extra in future versions with an empty list of
    dependencies, so that anything depending on ``package[extra]`` doesn't break
    with those future versions.
    """
    optional_dependencies: Dict[str, List[str]] = {"green midget cafe": []}
    cmd = make_write_pyproject(extras_require=optional_dependencies)
    result = cmd._generate()
    assert result["project"]["optional-dependencies"] == optional_dependencies


def test_empty_extras(make_write_pyproject) -> None:
    """
    Test that if there is an empty list of extras in the setuptools config,
    the plugin does not emit an ``optional-dependencies`` field.
    """
    cmd = make_write_pyproject(extras_require={})
    result = cmd._generate()
    assert "optional-dependencies" not in result["project"]


def test_required_dependencies_with_constraints(make_write_pyproject) -> None:
    """
    Test that required dependencies with constraints are not added to the list
    of optional dependencies.

    This exercises a bug in setuptools<68.2 where required deps with constraints
    get added to the list of optional dependencies with an empty extra.
    """
    dependencies: List[str] = ["holy-pin", 'holy-hand-grenade; python_version == "3.*"']
    cmd = make_write_pyproject(install_requires=dependencies)
    result = cmd._generate()
    assert set(result["project"]["dependencies"]) == set(dependencies)
    assert "optional-dependencies" not in result["project"]
