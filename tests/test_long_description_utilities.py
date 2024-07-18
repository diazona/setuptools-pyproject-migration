"""
Tests of the utilities that manipulate the long description.
"""

import pathlib
import pytest
import setuptools.dist

from setuptools_pyproject_migration._long_description import LongDescriptionMetadata, _guess_path
from setuptools_pyproject_migration._types import ReadmeFile, ReadmeText
from typing import Optional, Union


def test_guess_path_with_no_file(project):
    project.setup_py()
    distribution: setuptools.dist.Distribution = project.distribution()
    result = _guess_path(distribution, "This is a long description", "text/plain")
    assert result is None


def test_guess_path_with_description_file_metadata(project):
    readme_path = pathlib.Path("README.txt")
    description = "This is a long description"
    project.setup_cfg(
        f"""
[metadata]
description_file = {readme_path!s}
"""
    )
    project.setup_py()
    distribution: setuptools.dist.Distribution = project.distribution()
    result = _guess_path(distribution, description, "text/plain")
    assert result == readme_path


def test_guess_path_with_file(project):
    readme_path = pathlib.Path("README.txt")
    description = "This is a long description"
    project.write(readme_path, description)
    project.setup_py()
    distribution: setuptools.dist.Distribution = project.distribution()
    result = _guess_path(distribution, description, "text/plain")
    assert result == readme_path


@pytest.mark.parametrize(
    ["text", "content_type", "path", "expected"],
    [
        ("Description", "text/plain", "path.txt", {"file": "path.txt", "content-type": "text/plain"}),
        ("Description", "text/plain", None, {"text": "Description", "content-type": "text/plain"}),
        ("Description", None, "path.txt", "path.txt"),
        ("Description", "text/plain", "path.md", {"file": "path.md", "content-type": "text/plain"}),
    ],
    ids=["file-dict", "text-dict", "filename-str", "mismatched-content-type"],
)
def test_long_description_metadata_rendering(
    text: str, content_type: Optional[str], path: Optional[str], expected: Union[str, ReadmeFile, ReadmeText]
):
    actual = LongDescriptionMetadata(text, content_type, pathlib.Path(path) if path else None).pyproject_readme()
    assert actual == expected


def test_long_description_metadata_with_only_text():
    metadata = LongDescriptionMetadata("Description", None, None)
    with pytest.raises(ValueError):
        metadata.pyproject_readme()


def test_long_description_metadata_with_no_extension():
    metadata = LongDescriptionMetadata("Description", None, pathlib.Path("path"))
    with pytest.raises(ValueError):
        metadata.pyproject_readme()
