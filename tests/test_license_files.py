"""
Skeleton tests for ``license_files`` from ``setup.cfg``.

``license_files`` is the subject of `PEP-639 <https://peps.python.org/pep-0639/>`_.
"""


def test_license_files_setupcfg_globs_newlines(project) -> None:
    """
    Test that file names that contain glob characters are added as globs. (newline separated)
    """
    license_files = ["LICENSE.*", "COPYING.*"]
    license_files_lst = "\n    ".join(license_files)

    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
license_files = {license_files_lst}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    project.write("LICENSE.md", "An example file to match LICENSE.*")
    project.write("LICENSE.txt", "Another example file to match LICENSE.*")
    project.write("COPYING.txt", "An example file to match COPYING.*")
    result = project.generate()

    assert result["project"]["license-files"] == license_files


def test_license_files_setupcfg_globs_comma(project) -> None:
    """
    Test that file names that contain glob characters are added as globs.  (comma separated)
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
    project.write("LICENSE.md", "An example file to match LICENSE.*")
    project.write("LICENSE.txt", "Another example file to match LICENSE.*")
    project.write("COPYING.txt", "An example file to match COPYING.*")
    result = project.generate()

    assert result["project"]["license-files"] == license_files


def test_license_files_setupcfg_nomatch_newlines(project) -> None:
    """
    Test lists that match nothing trigger an error. (newline separated)
    """
    license_files = ["NONEXISTENT_LICENSE.*", "NONEXISTENT_COPYING.*"]
    license_files_lst = "\n    ".join(license_files)

    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
license_files = {license_files_lst}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    try:
        project.generate()
        assert False, "Should not have accepted the globs"
    except ValueError as e:
        # It'll fail at the first non-matching glob
        assert str(e) == f"{license_files[0]!r} did not match any files"


def test_license_files_setupcfg_nomatch_comma(project) -> None:
    """
    Test lists that match nothing trigger an error. (comma separated)
    """
    license_files = ["NONEXISTENT_LICENSE.*", "NONEXISTENT_COPYING.*"]
    license_files_lst = ", ".join(license_files)

    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
license_files = {license_files_lst}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    try:
        project.generate()
        assert False, "Should not have accepted the globs"
    except ValueError as e:
        # It'll fail at the first non-matching glob
        assert str(e) == f"{license_files[0]!r} did not match any files"


def test_license_files_setupcfg_files_newlines(project) -> None:
    """
    Test that concrete file names are added as paths. (newline separated)
    """
    license_files = ["LICENSE.md", "COPYING"]
    license_files_lst = "\n    ".join(license_files)

    setup_cfg = f"""\
[metadata]
name = test-project
version = 0.0.1
license_files = {license_files_lst}
"""

    project.setup_cfg(setup_cfg)
    project.setup_py()
    project.write("LICENSE.md", "An example file to match LICENSE.md")
    project.write("LICENSE.txt", "A file that will be ignored")
    project.write("COPYING", "An example file to match COPYING")
    result = project.generate()

    assert result["project"]["license-files"] == license_files


def test_license_files_setupcfg_files_comma(project) -> None:
    """
    Test that concrete file names are added as paths. (comma separated)
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
    project.write("LICENSE.md", "An example file to match LICENSE.md")
    project.write("LICENSE.txt", "A file that will be ignored")
    project.write("COPYING", "An example file to match COPYING")
    result = project.generate()

    assert result["project"]["license-files"] == license_files
