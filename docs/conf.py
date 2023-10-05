import os.path
import sys


# Ensure that test_support package is importable
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_support"))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "jaraco.packaging.sphinx",
]

master_doc = "index"
html_theme = "furo"

# Link dates and other references in the changelog
extensions += ["rst.linker"]
link_files = {
    "../CHANGELOG.rst": dict(
        using=dict(GH="https://github.com"),
        replace=[
            dict(
                pattern=r"(Issue #|\B#)(?P<issue>\d+)",
                url="{package_url}/issues/{issue}",
            ),
            dict(
                pattern=r"(?m:^((?P<scm_version>v?\d+(\.\d+){1,2}))\n[-=]+\n)",
                with_scm="{text}\n{rev[timestamp]:%d %b %Y}\n",
            ),
            dict(
                pattern=r"PEP[- ](?P<pep_number>\d+)",
                url="https://peps.python.org/pep-{pep_number:0>4}/",
            ),
        ],
    )
}

# Be strict about any broken references
nitpicky = True

# Include Python intersphinx mapping to prevent failures
# jaraco/skeleton#51
extensions += ["sphinx.ext.intersphinx"]
intersphinx_mapping = {
    "packaging": ("https://packaging.pypa.io/en/stable/", None),
    "python": ("https://docs.python.org/3", None),
    "setuptools": ("https://setuptools.pypa.io/en/latest/", None),
}

# Preserve authored syntax for defaults
autodoc_preserve_defaults = True

extensions.append("sphinx_copybutton")
# Exclude line numbers, prompts, and output from copying
copybutton_exclude = ".linenos, .gp, .go"
