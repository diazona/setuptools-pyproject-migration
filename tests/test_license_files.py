"""
Skeleton tests for ``license_files`` from ``setup.cfg``.  This is a ``setuptools`` extension which is not yet ratified
by the Python community.

``license_files`` is the subject of `PEP-639 <https://peps.python.org/pep-0639/>`_.
"""

import pytest


@pytest.mark.xfail
def test_license_files_setupcfg_globs(project) -> None:
    """
    Test that file names that contain glob characters are added as globs.
    """
    license_files = ["LICENSE.*", "COPYING.*"]
    license_files_lst = ", ".join(license_files)

    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
license_files = {license_files_lst}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()

    assert result["project"]["license_files"] == {"globs": license_files}


@pytest.mark.xfail
def test_license_files_setupcfg_files(project) -> None:
    """
    Test that concrete file names are added as paths.
    """
    license_files = ["LICENSE.md", "COPYING"]
    license_files_lst = ", ".join(license_files)

    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
license_files = {license_files_lst}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()

    assert result["project"]["license_files"] == {"paths": license_files}
