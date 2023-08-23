"""
Tests of the various ways that the ``urls`` field of ``pyproject.toml`` can be
populated.
"""

from typing import Dict


def test_one_project_url(make_write_pyproject):
    """
    Test that ``project_urls`` with one URL is faithfully copied into
    the generated pyproject data structure.
    """

    project_urls: Dict[str, str] = {
        "Homepage": "https://python.example.com/romani-ite-domum",
    }
    cmd = make_write_pyproject(project_urls=project_urls)
    result = cmd._generate()
    assert result["project"]["urls"] == project_urls


def test_several_project_urls(make_write_pyproject):
    """
    Test that ``project_urls`` with more than one URL is faithfully copied into
    the generated pyproject data structure.
    """

    project_urls: Dict[str, str] = {
        "Homepage": "https://python.example.com/romani-ite-domum",
        "Parrot Tracker": "https://python.example.com/that-pet-shop",
    }
    cmd = make_write_pyproject(project_urls=project_urls)
    result = cmd._generate()
    assert result["project"]["urls"] == project_urls


def test_main_url(make_write_pyproject):
    """
    Test that if a project has a single URL in the ``url`` field and no entry
    for ``project_urls``, the pyproject data structure does not wind up having
    any URLs.

    .. note::
        This behavior has a good chance of changing in the future. It's probably
        more useful for the ``url`` field value to be added to ``project_urls``.
    """

    url: str = "https://python.example.com/castle-aarrgh"
    cmd = make_write_pyproject(url=url)
    result = cmd._generate()
    assert "urls" not in result["project"]


def test_download_url(make_write_pyproject):
    """
    Test that if a project has a single URL in the ``download_url`` field and no
    entry for ``project_urls``, the pyproject data structure does not wind up
    having any URLs.

    .. note::
        This behavior has a good chance of changing in the future. It's probably
        more useful for the ``download_url`` field value to be added to
        ``project_urls``.
    """

    download_url: str = "https://python.example.com/shrubbery"
    cmd = make_write_pyproject(download_url=download_url)
    result = cmd._generate()
    assert "urls" not in result["project"]


def test_main_and_download_urls(make_write_pyproject):
    """
    Test that if a project has a single URL in each of the ``url`` and
    ``download_url`` fields, and no entry for ``project_urls``, the pyproject
    data structure does not wind up having any URLs.

    .. note::
        This behavior has a good chance of changing in the future. It's probably
        more useful for the ``url`` and ``download_url`` field values to be
        added to ``project_urls``.
    """

    url: str = "https://python.example.com/castle-aarrgh"
    download_url: str = "https://python.example.com/shrubbery"
    cmd = make_write_pyproject(url=url, download_url=download_url)
    result = cmd._generate()
    assert "urls" not in result["project"]


def test_main_and_download_and_project_urls(make_write_pyproject):
    """
    Test that if a project has a single URL in each of the ``url`` and
    ``download_url`` fields, as well as some URLs in ``project_urls``,
    the pyproject data structure contains only the URLs from ``project_urls``.

    .. note::
        This *could* change in the future. It's probably more useful for
        the project to have a homepage and download URL in ``project_urls``
        regardless of where they are provided, but trying to combine
        other fields with ``project_urls`` could easily lead to conflicts,
        so figuring out how best to handle this is left as a future task.
    """

    project_urls: Dict[str, str] = {
        "Download": "https://python.example.com/the-spanish-inquisition",  # bet you didn't expect that
        "Homepage": "https://python.example.com/romani-ite-domum",
        "Main": "https://python.example.com/the-holy-grail",
        "Project": "https://python.example.com/flying-circus",
        "Source": "https://python.example.com/cheeseshop",
    }
    url: str = "https://python.example.com/castle-aarrgh"
    download_url: str = "https://python.example.com/shrubbery"
    cmd = make_write_pyproject(url=url, download_url=download_url, project_urls=project_urls)
    result = cmd._generate()
    assert result["project"]["urls"] == project_urls


def test_empty_project_urls(make_write_pyproject):
    """
    Test that an empty list of project URLs, with no URLs given in other fields,
    does not produce a ``urls`` field in the result.
    """

    cmd = make_write_pyproject(project_urls={})
    result = cmd._generate()
    assert "urls" not in result["project"]
