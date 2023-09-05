Why bother?
===========

You might be wondering, why use this package at all? Isn't ``setup.py`` or
``setup.cfg`` good enough? And honestly... yes, it is. For now.

To briefly summarize a very long story, `setuptools`_ (the code that handles
``setup.py`` and ``setup.cfg`` is a very large, complex, and *old* piece of
software, and while it's very useful in many cases, there are other cases where
people *don't* want to use it. So the Python community has agreed on a set of
standards to allow other projects to do what setuptools does, namely building
a Python package into something that you can upload to `PyPI`_. One of those
standards, the one that matters for us, is :pep:`621`, which defines how core
project metadata (some of the information that people would normally put in
``setup.cfg`` or as keyword arguments to ``setup()``) should be stored in a new
standard file called ``pyproject.toml``. And now that that standard exists,
setuptools is strongly `encouraging people to use it <https://github.com/pypa/setuptools/issues/1688>`_.

This project was born in `a conversation on Mastodon`_ when we realized that as
far as we know, there's no existing tool to generically convert setuptools
configuration data to ``pyproject.toml``. There are some tools that work on
``setup.cfg``:

- `ini2toml`_
- `pyproject-migrator`_

but that doesn't help all the projects which pass keyword arguments to
the ``setup()`` call in ``setup.py``. This project is our attempt to make
the process of migrating from the "old way" ``setup.py`` to the "new way"
``pyproject.toml`` as convenient as possible.

.. _setuptools: https://setuptools.pypa.io/en/latest/
.. _PyPI: https://pypi.org/
.. _a conversation on Mastodon: https://mastodon.longlandclan.id.au/@stuartl/110518282805008552
.. _ini2toml: https://ini2toml.readthedocs.io/en/latest/
.. _pyproject-migrator: https://github.com/akx/pyproject-migrator
