"""
Tests of the logic that handles the ``requires-python`` field.
"""

import pytest

from packaging.specifiers import SpecifierSet


@pytest.mark.parametrize(
    "specifiers",
    [
        # Test common version constraints that are likely to occur in practice.
        # It's definitely overkill to test all of these, but it's just so easy....
        ">=2.7",
        "~=2.7",
        ">=3,<4",
        ">=3.8",
        ">=3.8,<4",
        "~=3.8",
        # Also test various less-likely combinations
        ">=3",
        "<=3.11",
        ">3.6",
        "<3.11",
        ">=3.6,<=3.11",
        ">=3.6,<=3.11,!=3.8",
        "===3.11",
    ],
)
def test_simple_requires_python(make_write_pyproject, specifiers: str):
    """
    Test that a Python version specifier given in the setuptools configuration
    is properly transferred to the data structure that would be written into
    ``pyproject.toml``.

    This test doesn't check that the specifier string comes through unchanged,
    because setuptools doesn't guarantee that. It only checks the parsed
    representation created using :py:class:`packaging.specifiers.SpecifierSet`.
    """
    expected_parsed = SpecifierSet(specifiers)
    cmd = make_write_pyproject(python_requires=specifiers)
    result = cmd._generate()
    assert SpecifierSet(result["project"]["requires-python"]) == expected_parsed


def test_no_requires_python(make_write_pyproject):
    cmd = make_write_pyproject()
    result = cmd._generate()
    assert "requires-python" not in result["project"]
