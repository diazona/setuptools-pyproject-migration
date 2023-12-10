Use as a standalone application
===============================

To install |project| as an application, we recommend using `pipx`_ (though of
course you can also do this with ``pip install --user`` or in a virtual
environment of your choice). First make sure you have pipx installed, then run

.. highlight:: console

.. code-block::

    $ pipx install setuptools-pyproject-migration

After that, in any directory that has a ``setup.py`` and/or ``setup.cfg`` file,
you can run

.. code-block::

    $ setuptools-pyproject-migration

and it will print out the content of ``pyproject.toml`` as computed from your
``setup.py`` and/or ``setup.cfg``.

Running ``setuptools-pyproject-migration --help`` will print a brief usage
summary.

You can also install and run the application in one go as follows:

.. code-block::

    $ pipx run setuptools-pyproject-migration

.. _pipx: https://pypa.github.io/pipx/
