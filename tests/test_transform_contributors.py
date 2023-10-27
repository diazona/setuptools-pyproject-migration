"""
Unit tests of WritePyproject._transform_contributors()
"""

import pytest

from setuptools_pyproject_migration import Contributor, WritePyproject
from typing import List, Optional


@pytest.mark.parametrize(
    ("name_string", "email_string", "expected_contributor"),
    [
        (
            "Monty Python",
            "python@python.example.com",
            {"name": "Monty Python", "email": "python@python.example.com"},
        ),
        (
            "Python",
            "python@example.com",
            {"name": "Python", "email": "python@example.com"},
        ),
        (
            "",
            "python@python.example.com",
            {"email": "python@python.example.com"},
        ),
        (
            "Monty Python",
            "",
            {"name": "Monty Python"},
        ),
    ],
    ids=["normal", "minimal", "empty-name", "empty-email"],
)
def test_valid_single_contributor(
    name_string: Optional[str], email_string: Optional[str], expected_contributor: Contributor
) -> None:
    expected_result: List[Contributor] = [expected_contributor]
    assert WritePyproject._transform_contributors(name_string, email_string) == expected_result


@pytest.mark.parametrize(
    ("names", "emails"),
    [
        # two contributors
        (
            ("Terry Jones", "Michael Palin"),
            ("terry-the-first@python.example.com", "michael@python.example.com"),
        ),
        # six contributors
        (
            ("Terry Jones", "Michael Palin", "Graham Chapman", "John Cleese", "Eric Idle", "Terry Gilliam"),
            (
                "terry-the-first@python.example.com",
                "michael@python.example.com",
                "graham@python.example.com",
                "john@python.example.com",
                "eric@python.example.com",
                "terry-the-second@python.example.com",
            ),
        ),
    ],
    ids=["two-contributors", "six-contributors"],
)
def test_multiple_contributors(names: List[str], emails: List[str]) -> None:
    # Construct the test case
    name_string = ", ".join(names)
    email_string = ", ".join(emails)
    # Construct the expected result
    expected_result = [{"name": n, "email": e} for n, e in zip(names, emails)]
    assert WritePyproject._transform_contributors(name_string, email_string) == expected_result


@pytest.mark.parametrize(
    ("name_string", "email_string", "expected_result"),
    [
        (
            "Terry Jones, Michael Palin",
            "terry-the-first@python.example.com",
            [
                {"name": "Terry Jones", "email": "terry-the-first@python.example.com"},
                {"name": "Michael Palin"},
            ],
        ),
        (
            "Terry Jones",
            "terry-the-first@python.example.com, michael@python.example.com",
            [
                {"name": "Terry Jones", "email": "terry-the-first@python.example.com"},
                {"email": "michael@python.example.com"},
            ],
        ),
        (
            "Terry Jones, Michael Palin",
            "",
            [
                {"name": "Terry Jones"},
                {"name": "Michael Palin"},
            ],
        ),
        (
            "",
            "terry-the-first@python.example.com, michael@python.example.com",
            [
                {"email": "terry-the-first@python.example.com"},
                {"email": "michael@python.example.com"},
            ],
        ),
    ],
    ids=["fewer-emails", "fewer-names", "no-emails", "no-names"],
)
def test_mismatched_lengths(name_string: str, email_string: str, expected_result: List[Contributor]) -> None:
    assert WritePyproject._transform_contributors(name_string, email_string) == expected_result


def test_absent_name() -> None:
    """
    Test the behavior of WritePyproject._transform_contributors() if the name
    string is ``None``
    """

    email_string = "python@python.example.com"
    expected_result: List[Contributor] = [{"email": email_string}]
    assert WritePyproject._transform_contributors(None, email_string) == expected_result


def test_absent_email() -> None:
    """
    Test the behavior of WritePyproject._transform_contributors() if the email
    string is ``None``
    """

    name_string = "Monty Python"
    expected_result: List[Contributor] = [{"name": name_string}]
    assert WritePyproject._transform_contributors(name_string, None) == expected_result


def test_absent_both() -> None:
    """
    Test the behavior of WritePyproject._transform_contributors() if both
    parameters are ``None``
    """

    expected_result: List[Contributor] = []
    assert WritePyproject._transform_contributors(None, None) == expected_result


@pytest.mark.parametrize(
    ("name_string", "email_string", "expected_result"),
    [
        ("Eric Idle,", "eric@python.example.com,", [{"name": "Eric Idle", "email": "eric@python.example.com"}]),
        (",Eric Idle", ",eric@python.example.com", [{"name": "Eric Idle", "email": "eric@python.example.com"}]),
        (",Eric Idle,", ",eric@python.example.com,", [{"name": "Eric Idle", "email": "eric@python.example.com"}]),
        ("Eric Idle,,", "eric@python.example.com,,", [{"name": "Eric Idle", "email": "eric@python.example.com"}]),
        (",,Eric Idle", ",,eric@python.example.com", [{"name": "Eric Idle", "email": "eric@python.example.com"}]),
        (
            "Eric Idle,,Terry Gilliam",
            "eric@python.example.com,,terry-the-first@python.example.com",
            [
                {"name": "Eric Idle", "email": "eric@python.example.com"},
                {"name": "Terry Gilliam", "email": "terry-the-first@python.example.com"},
            ],
        ),
        (",", ",", []),
        (",,", ",,", []),
    ],
    ids=[
        "trailing-comma",
        "leading-comma",
        "trailing-and-leading-commas",
        "trailing-double-comma",
        "leading-double-comma",
        "middle-double-comma",
        "lone-comma",
        "lone-double-comma",
    ],
)
def test_empty_components(name_string: str, email_string: str, expected_result: List[Contributor]) -> None:
    """
    Test that WritePyproject._transform_contributors() properly handles name
    or email strings with empty components - two consecutive commas, or a comma
    at the start or end of the string
    """
    assert WritePyproject._transform_contributors(name_string, email_string) == expected_result


def test_invalid_email() -> None:
    """
    Test how the function handles a syntactically invalid email address
    """
    name_string = "Monty Python"
    email_string = "python@"
    expected_result: List[Contributor] = [{"name": name_string, "email": email_string}]
    assert WritePyproject._transform_contributors(name_string, email_string) == expected_result
