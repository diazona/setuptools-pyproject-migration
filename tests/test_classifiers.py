from typing import List


def test_simple_classifiers(make_write_pyproject) -> None:
    """
    Test a simple setuptools configuration with some classifiers.
    """

    # We just need an arbitrary set of classifiers - these come from this project itself
    classifiers: List[str] = [
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Plugins",
        "Framework :: Setuptools Plugin",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development",
        "Topic :: System :: Archiving :: Packaging",
    ]

    cmd = make_write_pyproject(classifiers=classifiers)
    result = cmd._generate()
    assert result["project"]["classifiers"] == classifiers


def test_empty_classifiers_list(make_write_pyproject) -> None:
    """
    Test handling of an empty list of classifiers.
    """

    cmd = make_write_pyproject(classifiers=[])
    result = cmd._generate()
    assert "classifiers" not in result["project"]


def test_empty_classifiers_list_from_file(project) -> None:
    """
    Test handling of an empty list of classifiers when loaded from a file.

    In principle setuptools could load this as either an empty list, or as
    the absence of a list altogether, and it's important to make sure we have
    a test that covers the way setuptools actually behaves. (In practice,
    setuptools treats an empty list as though it were absent, but the point is,
    you don't have to know that to follow what this test is doing.)
    """

    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
classifiers =
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    assert "classifiers" not in result["project"]
