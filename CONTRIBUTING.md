# setuptools-pyproject-migration contribution guide

`setuptools-pyproject-migration` welcomes your contributions! The contribution
workflow may be a little rough sometimes, so please be patient while we figure
it out.

## Development workflow

To work on this project locally, start by cloning the repository.

```console
git clone git@github.com:diazona/setuptools-pyproject-migration.git
```

Use `tox` to run tests. It can be called with no arguments to run the tests
using your default Python interpreter:

```console
tox
```

or you can select a specific version of Python that you have installed, for
example to run with CPython 3.11:

```console
tox -e py311
```

We recommend using [pre-commit](https://pre-commit.com/) to get the quickest
possible feedback that your code follows the project's conventions. After you
have installed pre-commit following the instructions on its website, in your
checkout of `setuptools-pyproject-migration`, run

```console
pre-commit install
```

to install the hooks so that these checks will trigger every time you run
`git commit`. Or if you prefer not to install pre-commit, you can run

```console
tox -e pre_commit
```

to run the checks.

## Submitting a pull request

Anyone is welcome to submit a pull request, so if you want to suggest a change
to the code, just go ahead! Make sure the pull request title and description are
a clear representation of what you're changing.

- If your pull request solves an issue, link the PR to the issue so that
  the issue gets closed when the pull request is merged. One way to do this is
  by including `Closes #<N>` in the description, where `<N>` is the issue number.
- When you've implemented your changes, request review from any maintainer(s).
  If you're not sure who to ask, it's fine to pick a maintainer at random. We
  will approve your PR or work with you to make any further changes needed until
  everyone is satisfied.
- All pull requests have to be approved by a project maintainer who is not
  the author before they get merged. This is enforced by the project settings in
  Github.
- Generally the person approving the pull request will also merge it, but if that
  doesn't happen, feel free to merge the pull request any time after it has been
  approved. Or you can enable auto-merging.
- You can start a draft pull request to get feedback on changes that aren't
  ready to merge.

## Submitting a bug report or feature request

We use Github's [issue tracker](https://github.com/diazona/setuptools-pyproject-migration/issues)
for bug reports and new feature requests. If you find a bug or you'd like to
request a feature or change in the project, just search through the existing
issues to see if there's one that covers what you want, and if you don't find
one, go ahead and create a new one.

- If possible, please include enough information for other people to reproduce
  the bug you're reporting or to understand how the feature you're requesting
  should behave. It's ideal if you can provide a test case that currently fails
  but would pass if the bug is fixed or the feature is added, but if you can't,
  just be as precise as you can.
- If the issue is something you'd like to fix, you can assign it to yourself;
  otherwise just leave it unassigned.

## Coding conventions

Many of our coding conventions, things like code style, are automatically
enforced by pre-commit. You can install pre-commit locally to get the quickest
possible feedback that code you commit satisfies the checks, but if you don't,
that's fine; all the checks done by pre-commit will be repeated when you push.

- Commits should be atomic: one logical change per commit. Sometimes it's a bit
  subjective what constitutes a "logical change", but whoever reviews your pull
  request will offer suggestions on how to meet this criterion.
- Make sure to write a descriptive commit message. Some good things to include
  in a commit message:

  - What are you changing (of course!)
  - Why you're changing it
  - Why you decided to scope the commit as you did, if there was doubt about
      whether to combine some changes into one commit or keep them separate
  - If it builds on something from a previous commit, reference that
  - If you have plans for a future commit that builds on your current one, mention
      those plans in the message
