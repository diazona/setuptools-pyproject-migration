# setuptools-pyproject-migration

[![PyPI](https://img.shields.io/pypi/v/setuptools-pyproject-migration.svg)](https://pypi.org/project/setuptools-pyproject-migration)
![PyPI versions](https://img.shields.io/pypi/pyversions/setuptools-pyproject-migration.svg)
[![tests](https://github.com/diazona/setuptools-pyproject-migration/workflows/tests/badge.svg)](https://github.com/diazona/setuptools-pyproject-migration/actions?query=workflow%3A%22tests%22)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![skeleton](https://img.shields.io/badge/skeleton-2023-informational)](https://blog.jaraco.com/skeleton)

`pyproject.toml` represents the new era of Python packaging, but many old
projects are still using `setuptools`. That's where this package comes in:
just activate a virtual environment, install `setuptools-pyproject-migration`,
then you can run

```console
python setup.py pyproject
```

to print out a nicely formatted `pyproject.toml` file with all the same metadata
that you had in `setup.py` or `setup.cfg`.

## History

Inspired by [a conversation on Mastodon](https://mastodon.longlandclan.id.au/@stuartl/110518282805008552).
