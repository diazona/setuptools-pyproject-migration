"""
Tests of author and maintainer metadata
"""


class TestAuthors:
    def test_single_author(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
author = Monty Python
author_email = python@python.example.com
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "authors": [
                    {"name": "Monty Python", "email": "python@python.example.com"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject

    def test_only_name(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
author = Monty Python
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "authors": [
                    {"name": "Monty Python"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject

    def test_only_email(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
author_email = python@python.example.com
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "authors": [
                    {"email": "python@python.example.com"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject

    def test_multiple_authors(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
author = John Cleese, Terry Gilliam
author_email = john@python.example.com, terry-the-second@python.example.com
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "authors": [
                    {"name": "John Cleese", "email": "john@python.example.com"},
                    {"name": "Terry Gilliam", "email": "terry-the-second@python.example.com"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject


class TestMaintainers:
    def test_single_maintainer(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
maintainer = Monty Python
maintainer_email = python@python.example.com
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "maintainers": [
                    {"name": "Monty Python", "email": "python@python.example.com"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject

    def test_only_name(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
maintainer = Monty Python
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "maintainers": [
                    {"name": "Monty Python"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject

    def test_only_email(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
maintainer_email = python@python.example.com
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "maintainers": [
                    {"email": "python@python.example.com"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject

    def test_multiple_maintainers(self, project) -> None:
        setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
maintainer = John Cleese, Terry Gilliam
maintainer_email = john@python.example.com, terry-the-second@python.example.com
"""
        pyproject = {
            "build-system": {
                "requires": ["setuptools"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": "test-project",
                "version": "0.0.1",
                "maintainers": [
                    {"name": "John Cleese", "email": "john@python.example.com"},
                    {"name": "Terry Gilliam", "email": "terry-the-second@python.example.com"},
                ],
            },
        }
        project.setup_cfg(setup_cfg)
        project.setup_py()
        result = project.generate()
        assert result == pyproject


def test_authors_and_maintainers(project) -> None:
    """
    Test a situation where both the author and maintainer fields are set.
    """

    setup_cfg = """\
[metadata]
name = test-project
version = 0.0.1
author = Terry Jones, Michael Palin
author_email = terry-the-first@python.example.com, michael@python.example.com
maintainer = Graham Chapman, John Cleese
maintainer_email = graham@python.example.com, john@python.example.com
"""
    pyproject = {
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": "test-project",
            "version": "0.0.1",
            "authors": [
                {"name": "Terry Jones", "email": "terry-the-first@python.example.com"},
                {"name": "Michael Palin", "email": "michael@python.example.com"},
            ],
            "maintainers": [
                {"name": "Graham Chapman", "email": "graham@python.example.com"},
                {"name": "John Cleese", "email": "john@python.example.com"},
            ],
        },
    }
    project.setup_cfg(setup_cfg)
    project.setup_py()
    result = project.generate()
    assert result == pyproject
