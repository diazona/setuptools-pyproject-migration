"""
Tests of the ``readme`` field in ``pyproject.toml``, which can be populated
from setuptools' ``long_description`` field
"""

import pathlib
import pytest


parametrize_readme_type = pytest.mark.parametrize(
    ("extension", "mime_type"),
    [
        ("txt", "text/plain"),
        ("md", "text/markdown"),
        ("rst", "text/x-rst"),
    ],
    ids=["text", "markdown", "rst"],
)


@parametrize_readme_type
def test_string_with_content_type(project, extension: str, mime_type: str) -> None:
    long_description = "This is a long description string"
    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
long_description = {long_description}
long_description_content_type = {mime_type}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    readme = result["project"]["readme"]
    assert isinstance(readme, dict)
    readme_path: pathlib.Path = pathlib.Path(readme["file"])
    assert readme_path.suffix == f".{extension}"
    assert readme_path.exists()
    assert readme_path.read_text(encoding="utf-8").rstrip("\n") == long_description
    assert readme["content-type"] == mime_type


@parametrize_readme_type
def test_string_with_content_type_setuppy(project, extension: str, mime_type: str) -> None:
    long_description = "This is a long description string"
    setup_py = f"""\
import setuptools

setuptools.setup(
    name="test-project",
    version="0.0.1",
    long_description="{long_description}",
    long_description_content_type="{mime_type}"
)
"""

    project.setup_py(setup_py)
    result = project.generate()
    readme = result["project"]["readme"]
    assert isinstance(readme, dict)
    readme_path: pathlib.Path = pathlib.Path(readme["file"])
    assert readme_path.suffix == f".{extension}"
    assert readme_path.exists()
    assert readme_path.read_text(encoding="utf-8").rstrip("\n") == long_description
    assert readme["content-type"] == mime_type


def test_string_without_content_type(project) -> None:
    long_description = "This is a long description string"
    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
long_description = {long_description}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    readme = result["project"]["readme"]
    assert isinstance(readme, str)
    readme_path: pathlib.Path = pathlib.Path(readme)
    # Without a content type specified, there should be no extension given to the README file
    assert not readme_path.suffix
    assert readme_path.exists()
    assert readme_path.read_text(encoding="utf-8").rstrip("\n") == long_description


def test_string_without_content_type_setuppy(project) -> None:
    long_description = "This is a long description string"
    setup_py = f"""\
import setuptools

setuptools.setup(
    name="test-project",
    version="0.0.1",
    long_description="{long_description}"
)
"""

    project.setup_py(setup_py)
    result = project.generate()
    readme = result["project"]["readme"]
    assert isinstance(readme, str)
    readme_path: pathlib.Path = pathlib.Path(readme)
    # Without a content type specified, there should be no extension given to the README file
    assert not readme_path.suffix
    assert readme_path.exists()
    assert readme_path.read_text(encoding="utf-8").rstrip("\n") == long_description


def test_file_with_space(project) -> None:
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
long_description = file: README.rst
"""

    project.setup_cfg(setup_cfg)
    project.write("README.rst", "Dummy README\n")
    project.setup_py()
    result = project.generate()
    assert result["project"]["readme"] == "README.rst"


@parametrize_readme_type
def test_file_with_content_type(project, extension: str, mime_type: str) -> None:
    readme_filename = f"README.{extension}"
    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
long_description = file:{readme_filename}
long_description_content_type = {mime_type}
"""

    project.setup_cfg(setup_cfg)
    project.write(readme_filename, "Dummy README\n")
    project.setup_py()
    result = project.generate()
    assert result["project"]["readme"] == {"content-type": mime_type, "file": readme_filename}


@parametrize_readme_type
def test_file_with_content_type_setuppy(project, extension: str, mime_type: str) -> None:
    readme_filename = f"README.{extension}"
    setup_py = f"""\
import setuptools

setuptools.setup(
    name="test-project",
    version="0.0.1",
    long_description="file:{readme_filename}",
    long_description_content_type="{mime_type}"
)
"""

    project.write(readme_filename, "Dummy README\n")
    project.setup_py(setup_py)
    result = project.generate()
    assert result["project"]["readme"] == {"content-type": mime_type, "file": readme_filename}


@parametrize_readme_type
def test_file_without_content_type(project, extension: str, mime_type: str) -> None:
    # mime_type is unused but we keep it to be able to use the same parametrization as other tests
    readme_filename = f"README.{extension}"
    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
long_description = file:{readme_filename}
"""

    project.setup_cfg(setup_cfg)
    project.write(readme_filename, "Dummy README\n")
    project.setup_py()
    result = project.generate()
    assert result["project"]["readme"] == readme_filename


@parametrize_readme_type
def test_file_without_content_type_setuppy(project, extension: str, mime_type: str) -> None:
    # mime_type is unused but we keep it to be able to use the same parametrization as other tests
    readme_filename = f"README.{extension}"
    setup_py = f"""\
import setuptools

setuptools.setup(
    name="test-project",
    version="0.0.1",
    long_description="file:{readme_filename}"
)
"""

    project.write(readme_filename, "Dummy README\n")
    project.setup_py(setup_py)
    result = project.generate()
    assert result["project"]["readme"] == readme_filename
