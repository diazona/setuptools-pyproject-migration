API
===

|project| is only intended for use as a `setuptools`_ plugin or a command-line
executable, so it does not expose an API to be used as a Python library.

* :ref:`genindex`
* :ref:`modindex`

``setuptools_pyproject_migration``
----------------------------------

There should generally be no need to use this API unless you're trying to invoke
setuptools plugins in a custom way, in which case you're probably better off
looking at the `setuptools`_ documentation.

.. automodule:: setuptools_pyproject_migration
    :members:
    :undoc-members:
    :show-inheritance:

``setuptools_pyproject_migration.cli``
--------------------------------------

This API is only meant for use by this project's built-in console script. You
can call it from Python at your own risk.

.. automodule:: setuptools_pyproject_migration.cli
    :members:
    :undoc-members:
    :show-inheritance:

.. _setuptools: https://setuptools.pypa.io/en/latest/
