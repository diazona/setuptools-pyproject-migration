Use as a setuptools plugin
==========================

You can install |project| in a virtual environment of your choice, perhaps one
that you already use to develop your project, by activating the environment and
running

.. code-block::

    $ python -m pip install setuptools-pyproject-migration

Then, make sure you're in the directory with your ``setup.py`` and/or
``setup.cfg`` files, and run

.. code-block::

    $ python setup.py pyproject

That will print out the content of your ``pyproject.toml`` file as computed from
your ``setup.py`` and/or ``setup.cfg``.

This method of using the plugin requires you to have a ``setup.py`` file. If you
only use ``setup.cfg``, consider using the :doc:`CLI application <usage-cli>`
instead.
