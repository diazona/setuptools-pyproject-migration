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

    $ setup-to-pyproject

and it will print out the content of ``pyproject.toml`` as computed from your
``setup.py`` and/or ``setup.cfg``.

Running ``setup-to-pyproject --help`` will print a brief usage summary.

.. _pipx: https://pypa.github.io/pipx/
