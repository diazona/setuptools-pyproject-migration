# setuptools-pyproject-migration

<!-- markdownlint-disable MD013 -->
[![PyPI](https://img.shields.io/pypi/v/setuptools-pyproject-migration.svg)](https://pypi.org/project/setuptools-pyproject-migration)
![PyPI versions](https://img.shields.io/pypi/pyversions/setuptools-pyproject-migration.svg)
[![tests](https://github.com/diazona/setuptools-pyproject-migration/workflows/tests/badge.svg)](https://github.com/diazona/setuptools-pyproject-migration/actions?query=workflow%3A%22tests%22)
[![documentation](https://readthedocs.org/projects/setuptools-pyproject-migration/badge/?version=latest)](https://setuptools-pyproject-migration.readthedocs.io/en/latest/?badge=latest)
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![skeleton](https://img.shields.io/badge/skeleton-2023-informational)](https://blog.jaraco.com/skeleton)
<!-- markdownlint-enable MD013 -->

## Introduction

`pyproject.toml` represents the new era of Python packaging, but many old
projects are still using `setuptools`. That's where this package comes in: just
install it, run it, and it will print out a nicely formatted `pyproject.toml`
file with the same metadata that you had in `setup.py` or `setup.cfg`.

Or at least, that's the goal. The project is currently a work in progress with
only partial support for all the attributes that might exist in a setuptools
configuration, so this won't yet work for anything complex. Feel free to file
an issue to highlight anything that needs to be added!

## Installation and usage

There are two different ways to install this project. You can use either or both
depending on what you prefer.

### Standalone application

To install `setuptools-pyproject-migration` as an application, we recommend
using [pipx](https://pypa.github.io/pipx/) (though of course you can also do
this with `pip install --user` or in a virtual environment of your choice).
First make sure you have pipx installed, then run

```console
pipx install setuptools-pyproject-migration
```

After that, in any directory that has a `setup.py` and/or `setup.cfg` file, you
can run

```console
setuptools-pyproject-migration
```

and it will print out the content of `pyproject.toml` as computed from your
`setup.py` and/or `setup.cfg`. Running `setuptools-pyproject-migration -h` will
print a brief usage summary.

You can also install and run the application in one go as follows:

```console
pipx run setuptools-pyproject-migration
```

### Virtual environment

Or you can use `setuptools-pyproject-migration` in a virtual environment you use
to develop your project. Activate your virtual environment and then run

```console
python -m pip install setuptools-pyproject-migration
```

and then running

```console
python setup.py pyproject
```

will print out the content of your `pyproject.toml` file.

## History

Inspired by [a conversation on Mastodon](https://mastodon.longlandclan.id.au/@stuartl/110518282805008552).
