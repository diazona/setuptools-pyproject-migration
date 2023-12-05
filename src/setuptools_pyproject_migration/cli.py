"""
A simple command-line interface to the plugin.
"""

import argparse
import os.path
import sys
import warnings


def _parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="""
Run the pyproject setuptools command. This effectively does the same thing as

    python setup.py pyproject

except that if setup.py doesn't exist, it will act as though there were a "stub"
setup.py script with the following contents:

    import setuptools
    setuptools.setup()

Effectively, this lets you use setuptools-pyproject-migration without having to
install the plugin in your project's virtual environment, and without having to
create a setup.py file if all you have is setup.cfg.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    return parser.parse_args()


def main() -> None:
    """
    Run the :py:class:`setuptools_pyproject_migration.WritePyproject` setuptools
    command. This does the same thing as ``python setup.py pyproject``, except
    that if ``setup.py`` doesn't exist, it will act as though there were
    a "stub" ``setup.py`` script with the following contents:

    .. code-block:: python
        :name: setup.py

        import setuptools
        setuptools.setup()

    Effectively, this lets you use ``setuptools-pyproject-migration`` without
    having to install the plugin and without having to create a ``setup.py``
    file if all you have is ``setup.cfg``.

    .. note::

        This function changes ``sys.argv``. If you call this from Python, make
        sure to restore the original argument list afterwards if your program
        needs it.
    """
    _parse_args()

    sys.argv = ["setup.py", "pyproject"]

    setup_code: str
    if os.path.exists("setup.py"):
        with open("setup.py") as f:
            setup_code = f.read()
    else:
        setup_code = "import setuptools\nsetuptools.setup()\n"
    setup_bytecode = compile(setup_code, "setup.py", "exec", dont_inherit=True)
    exec(setup_bytecode)


def old_main() -> None:
    """
    Print a deprecation warning and then call :py:func:`main()`.
    """
    warnings.warn(f"{sys.argv[0]} is deprecated; run setuptools-pyproject-migration instead", category=FutureWarning)
    main()


# Allow running as `python -m setuptools_pyproject_migration.cli`
if __name__ == "__main__":  # pragma: no cover
    main()
