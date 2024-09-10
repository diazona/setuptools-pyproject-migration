"""
Tests that verify the logic we use to match sdist and wheel filenames is
consistent with the packaging standards.
"""

import pytest

from test_support.distribution import ParsedSdistFilename, _parse_package_filename
from typing import List, Optional, Tuple
from wheel_filename import ParsedWheelFilename

SDIST: List[Tuple[str, str]] = [
    ("p", "1.0"),
    ("package", "1.0"),
    ("package_name", "1.0"),
    ("package", "0.1"),
    ("package", "0.0.1"),
    ("package", "0.0.100"),
    ("package", "1.post0"),
    ("package", "2024.09.06"),
    ("package", "20240906"),
    ("package", "1a"),
    ("package", "1a0"),
    ("package", "1a1"),
    ("package", "1a10"),
    ("package", "1b"),
    ("package", "1b0"),
    ("package", "1b1"),
    ("package", "1rc"),
    ("package", "1rc0"),
    ("package", "1rc1"),
]


@pytest.mark.parametrize(("name", "version"), SDIST)
class TestSDistFilename:
    @pytest.fixture
    def match_filename(self, name: str, version: str) -> ParsedSdistFilename:
        filename = f"{name}-{version}.tar.gz"
        parsed = _parse_package_filename(filename)
        assert isinstance(parsed, ParsedSdistFilename)
        return parsed

    def test_project(self, name: str, version: str, match_filename: ParsedSdistFilename) -> None:
        assert match_filename.project == name

    def test_version(self, name: str, version: str, match_filename: ParsedSdistFilename) -> None:
        assert match_filename.version == version


WHEEL_TAGS: List[Tuple[Optional[str], str, str, str]] = [
    (None, "py3", "none", "any"),
    ("1", "py3", "none", "any"),
    (None, "py38", "cp38", "any"),
    (None, "py3", "none", "linux_86_64"),
]


@pytest.mark.parametrize(("name", "version"), SDIST)
@pytest.mark.parametrize(("build", "python", "abi", "platform"), WHEEL_TAGS)
class TestWheelFilename:
    @pytest.fixture
    def match_filename(
        self, name: str, version: str, build: str, python: str, abi: str, platform: str
    ) -> ParsedWheelFilename:
        filename = f"{name}-{version}"
        if build:
            filename += f"-{build}"
        filename += f"-{python}-{abi}-{platform}.whl"
        parsed = _parse_package_filename(filename)
        assert isinstance(parsed, ParsedWheelFilename)
        return parsed

    def test_name(
        self, name: str, version: str, python: str, abi: str, platform: str, match_filename: ParsedWheelFilename
    ) -> None:
        assert match_filename.project == name

    def test_version(
        self, name: str, version: str, python: str, abi: str, platform: str, match_filename: ParsedWheelFilename
    ) -> None:
        assert match_filename.version == version
