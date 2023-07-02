def test_name_and_version(project) -> None:
    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
"""
    pyproject_toml = """\
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.0.1"
"""
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.run()
    assert result.returncode == 0
    assert result.stdout == "running pyproject\n" + pyproject_toml
