0.3
===

Bugfixes
--------

- Add more robust handling of long descriptions and their content types (#132)
- Fix a bug in test support code where it wouldn't parse dependencies without markers from a package's core metadata (#133)
- Relax matching of optional dependency requirements to allow for a missing extra condition in the marker (#134)
- Work around pyproject-metadata producing None for author/maintainer email addresses (#135)
- Fix a bug in test support code where it was not splitting lists of keywords from core metadata (#136)
- Handle INI-style ``entry_point`` strings. (#152)


Misc
----

- #109
- Add a coverage.py configuration to select which files are measured and enable branch coverage
- Apply xfail markers to individual test methods in external project tests and enable xfail_strict
- Mark project as active
- Run slow tests during CI


0.2
===

Features
--------

- Support testing against live distribution packages that don't provide wheels by computing the metadata from the sdist, and against packages that require their own source code to be importable from ``setup.py`` (#105)
- Use inline arrays and tables for keys within the ``project`` key, matching setuptools documentation. (#112)


Bugfixes
--------

- When building documentation on ReadTheDocs, use a full (non-shallow) clone and
  ignore local modifications, in order to get the right version number (#99)
- Explicitly list ``packaging`` as a dependency so ``pipx`` installs it in the virtual environment instead of relying on
  ``setuptools`` to pull it in. (#100)
- Add fixes to handle ``README`` data specified in ``setup.py`` instead of ``setup.cfg``. (#102)
- Fix converting README ``file:`` directive with whitespace, such as ``file: README.rst``. (#111)
- Avoid adding empty ``name`` and ``email`` fields in ``authors`` and
  ``maintainers``. An empty ``name`` provides no information, and an empty
  ``email`` is not accepted by setuptools. (#117)
- Require ``setuptools>=66.1`` when running on Python 3.12 (#139)


Deprecations and Removals
-------------------------

- Deprecate setup-to-pyproject console script in favor of setuptools-pyproject-migration to support ``pipx run`` (#107)


Misc
----

- #105
- #143


0.1.0
=====

Features
--------

- Support authors and maintainers (#28)
- Support classifiers (#29)
- Support description (#30)
- Support keywords (#31)
- Support license (#32)
- Support readme (#33)
- Support requires-python (#34)
- Support urls (#35)
- Support entry points (#36)
- Support extras (#37)
- Enable towncrier (#88)


Bugfixes
--------

- Set the long description content type to Markdown in order to
  (hopefully) make the description render properly on PyPI. (#99)


Improved Documentation
----------------------

- Update development status to alpha (#9)
- Set up documentation on ReadTheDocs (#18)
- Write some meaningful documentation (#71)
