"""
Support code for distribution package testing.

"Distribution package" means the same thing here that it does in
`importlib-metadata <https://importlib-metadata.readthedocs.io/en/latest/using.html>`_:
basically a Python project that can be installed with ``pip`` or a compatible
tool. Most distribution packages, of course, come from `PyPI <https://pypi.org/>`_,
but it's also possible to use raw source code as a distribution package. Since
this plugin only works on projects that use setuptools (and have not been
converted to take setuptools configuration from ``pyproject.toml``), we only
test with distribution packages that have ``setup.py`` or ``setup.cfg`` in their
source code.
"""

import enum
import hashlib
import html.parser
import logging
import packaging
import pathlib
import re
import requests
import subprocess
import tarfile
import tempfile
import urllib.parse
import warnings

from abc import ABC, abstractmethod
from test_support import importlib_metadata, Project
from typing import Any, List, Optional, Sequence

try:
    from pyproject_metadata import RFC822Message
except ImportError:
    # pyproject-metadata is not available for Python <3.7. That's okay because
    # we skip all the tests that would use RFC822Message if pyproject-metadata
    # is not available, so that name doesn't need to have a definition that is
    # valid at runtime, but pytest still scans this file looking for doctests
    # so it still needs to be importable. As long as this name is defined as
    # _something_ which is a valid type, that will be the case.
    class RFC822Message:  # type: ignore[no-redef]
        pass


_logger = logging.getLogger("setuptools_pyproject_migration:" + __name__)


class HashChecker:
    def __init__(self, algorithm: str, expected_hash: str):
        self.algorithm: str = algorithm
        self.expected_hash: str = expected_hash

    @classmethod
    def from_spec(cls, spec: str, sep: str = "="):
        algorithm, _, hash = spec.partition(sep)
        if not hash:
            raise ValueError(f"Input {spec!r} is not a valid hash constraint")
        return cls(algorithm, hash)

    def check(self, data):
        return hashlib.new(self.algorithm, data).hexdigest() == self.expected_hash


class PackageType(enum.Enum):
    SDIST = "sdist"
    WHEEL = "bdist_wheel"


class PackageInfo:
    def __init__(self, package_url: str, package_hash_spec: str, metadata_hash_spec: Optional[str]):
        self.package_type: PackageType
        if package_url.endswith(".whl"):
            self.package_type = PackageType.WHEEL
        elif package_url.endswith(".tar.gz"):
            self.package_type = PackageType.SDIST
        else:
            raise ValueError(f"Unrecognized extension for url {package_url!r}")
        self.package_url: str = package_url
        self.package_hasher: HashChecker = HashChecker.from_spec(package_hash_spec)
        self.metadata_url: str = package_url + ".metadata"
        self.metadata_hasher: Optional[HashChecker]
        if metadata_hash_spec:
            self.metadata_hasher = HashChecker.from_spec(metadata_hash_spec)
        else:
            self.metadata_hasher = None


class SimplePackageListingParser(html.parser.HTMLParser):
    """
    A bare-bones parser for the list of versions of a given package offered by
    the simple repository API. It will select releases of the given version of
    the package.
    """

    _filename_regex = re.compile(
        r"(?P<name>[\w.-]+)-(?P<version>{}).+\.(?:whl|tar\.gz)".format(packaging.version.VERSION_PATTERN),
        flags=re.VERBOSE | re.IGNORECASE,
    )

    @staticmethod
    def _normalize_package_name(name: str):
        """
        Normalize a Python package name in the manner specified by :pep:`503`.
        """
        return re.sub(r"[-_.]+", "-", name).lower()

    def __init__(self, name: str, version: str):
        super().__init__()
        self.normalized_name: str = self._normalize_package_name(name)
        self.version: packaging.version.Version = packaging.version.parse(version)
        self.releases: List[PackageInfo] = []

    def handle_starttag(self, tag: Any, attrs: Any):
        if not isinstance(tag, str):
            raise TypeError(f"Tag {tag!r} is not a string")
        if tag != "a":
            return
        href: Optional[str] = None
        data_dist_info_metadata: Optional[str] = None
        for k, v in attrs:
            if not isinstance(k, str) or not isinstance(v, str):
                raise TypeError(f"Unexpected type of HTML tag attribute {k!r}={v!r}")
            if k == "href":
                href = v
            elif k == "data-dist-info-metadata":
                data_dist_info_metadata = v
        if not href:
            return  # This <a> is not a link
        parsed_url: urllib.parse.ParseResult = urllib.parse.urlparse(href)
        filename: str
        _, _, filename = parsed_url.path.rpartition("/")
        m = self._filename_regex.match(filename)
        if not m or self.version != packaging.version.parse(m.group("version")):
            return
        assert self.normalized_name == self._normalize_package_name(m.group("name"))
        no_fragment_url: str = urllib.parse.urlunparse(list(parsed_url[:5]) + [""])
        self.releases.append(PackageInfo(no_fragment_url, parsed_url.fragment, data_dist_info_metadata))


class DistributionPackage(ABC):
    """
    A "distribution package" in the sense used in `importlib_metadata`_.

    Basically, this is a Python project that can be installed with ``pip`` or
    a compatible tool, and that has a ``setup.py`` or ``setup.cfg`` file.

    .. _`importlib_metadata`: https://importlib-metadata.readthedocs.io/en/latest/using.html
    """

    def __init__(self) -> None:
        self.test_id: Optional[str] = None

    @abstractmethod
    def prepare_source(self, path: pathlib.Path) -> pathlib.Path:
        """
        Populate a directory with the package's source code. This might involve
        checking out a repository, extracting an archive, or something else,
        depending on the type of project.

        This method will be given an empty, writable directory. It should put
        the distribution package's source code somewhere inside that directory
        and return the path in which |project| should be run, i.e. the parent
        directory of ``setup.py`` or ``setup.cfg`` (unless the distribution
        package does something *extremely* weird that involves a custom path to
        setuptools config files).

        :param path: An empty, writable directory in which the package's source
            code should be placed. Implementations can also use parts of this
            directory as temporary storage; everything put in here will be
            ignored except for the path returned.
        :return: The root directory of the package, which contains ``setup.py``
            or ``setup.cfg``. This may be ``path`` or a subdirectory of ``path``
            depending on how the source code is prepared.
        """

    @abstractmethod
    def core_metadata_reference(self) -> RFC822Message:
        """
        Return the "reference" core metadata for the distribution package.
        Typically this comes from the package's wheel, if a wheel is available.

        :return: The known correct core metadata for the distribution package
        """


class DistributionPackagePreparation:
    """
    A distribution package that has been prepared for testing. "Prepared" means
    the source code is downloaded/extracted/checked out/whatever in a local
    directory, in a state that allows |project| to run on it to generate
    a ``pyproject.toml`` file.

    .. note:
        The "preparation" in the class name should be understood as the result
        of preparing, not the _act_ of preparing. (Naming is hard)

    :param distribution_package: The distribution package to prepare
    :param path: The path in which to prepare the distribution package
    :param script_runner: A runner that will be used to run |project|
    """

    # TODO get rid of the requirement to pass a ScriptRunner here
    def __init__(self, distribution_package: DistributionPackage, path: pathlib.Path):
        self.distribution_package: DistributionPackage = distribution_package
        self.path: pathlib.Path = path
        project_root: pathlib.Path = distribution_package.prepare_source(path)
        self.project: Project = Project(project_root)


class PyPiDistribution(DistributionPackage):
    """
    A distribution package obtained from PyPI.

    :param name: The name of the project as registered on PyPI, i.e. the name
         in the project's URL: ``https://pypi.org/project/<name>``
    :param version: The version string of the project as registered on PyPI
    :param project_root: The relative path within the project's sdist to
        the directory containing ``setup.py`` or ``setup.cfg``. If omitted,
        this defaults to ``<name>-<version>``, which matches the convention
        used by most of the common build systems when preparing sdists.
    """

    def __init__(self, name: str, version: str, project_root: Optional[pathlib.Path] = None):
        super().__init__()
        self.name: str = name
        self.version = version
        self.basename: str = f"{self.name}-{self.version}"
        self.package_spec: str = f"{self.name}=={self.version}"
        self.test_id: Optional[str] = self.package_spec
        self.project_root: pathlib.Path
        if project_root:
            if project_root.is_absolute():
                raise ValueError(f"project_root must be a relative path, got {project_root!r}")
            else:
                self.project_root = project_root
        else:
            self.project_root = pathlib.Path(self.basename)

    def prepare_source(self, path: pathlib.Path) -> pathlib.Path:
        """
        Populate a directory with the package's source code. This involves
        downloading the sdist and extracting it.
        """

        # pip might not be the most efficient way to do this, since it seems
        # to try building something - but pip does cache downloads
        subprocess.check_call(["pip", "download", "--no-binary", ":all:", "--no-deps", self.package_spec])
        _logger.debug("Extracting to %s", path)
        with tarfile.open(self.basename + ".tar.gz") as tf:
            tf.extractall(path=path, filter="data")
        abs_project_root: pathlib.Path = path / self.project_root
        _logger.debug("Project root: %s", abs_project_root)
        if not (abs_project_root / "setup.py").exists() and not (abs_project_root / "setup.cfg").exists():
            _logger.warning("No setup.py or setup.cfg in project root %s", abs_project_root)
        return abs_project_root

    def _parse_pypi_simple_listing(self) -> Sequence[PackageInfo]:
        """
        Access the PyPI simple API to download and parse the page that lists
        versions for the package.

        :return: A collection of :py:class:`PackageInfo` objects representing
            all available releases of the right name and version. Typically this
            will include one sdist and at least one wheel.
        """

        # Ideally we could use the pypi-simple package, but it doesn't support
        # metadata downloads. (https://github.com/jwodder/pypi-simple/issues/6)
        simple_api_response = requests.get(f"https://pypi.org/simple/{self.name}/")
        simple_api_response.raise_for_status()
        parser: SimplePackageListingParser = SimplePackageListingParser(self.name, self.version)
        parser.feed(simple_api_response.text)
        return parser.releases

    def _get_metadata_from_pypi(self, wheel_release: PackageInfo) -> str:
        """
        Obtain the metadata for a package release from PyPI.

        This will first try to download a separate metadata file as specified in
        :pep:`658`. If that file exists, can be downloaded, and passes hash
        verification (if a hash is available), then that's it. Otherwise, this
        will download the actual wheel file and extract the metadata from it.

        :param wheel_release: The wheel release for which to obtain metadata
        :return: A string containing the metadata
        :raises ValueError: If a separate metadata file was available and a hash
            was provided for that file, and the file content did not match
            the hash
        """

        assert wheel_release.package_type == PackageType.WHEEL
        metadata_response = requests.get(wheel_release.metadata_url)
        if metadata_response.status_code == requests.codes.ok:
            if not wheel_release.metadata_hasher:
                warnings.warn(f"No hash available for {self.name}=={self.version}")
            elif not wheel_release.metadata_hasher.check(metadata_response.content):
                raise ValueError(f"hash verification failed for {self.name}=={self.version}")
            return metadata_response.text
        elif metadata_response.status_code != requests.codes.not_found:
            metadata_response.raise_for_status()

        # No separate metadata file exists; this is fine, just download the wheel
        wheel_response = requests.get(wheel_release.package_url)
        with tempfile.NamedTemporaryFile(suffix=".whl") as tf:
            # Write the data to a temporary wheel file and then read the metadata from it
            # TODO it should be possible to do this completely in memory
            for chunk in wheel_response.iter_content(chunk_size=4096):
                tf.write(chunk)
            tf.flush()
            distribution = importlib_metadata.distributions(path=[tf.name])
        return distribution["dist_info"]["metadata"]

    @staticmethod
    def _parse_metadata_from_text(metadata: str) -> RFC822Message:
        """
        Parse a text representation of package metadata into an :py:class:`RFC822Message`.

        This is meant to do the same thing as :py:class:`email.parser.HeaderParser`
        except that it produces an ``RFC822Message``.
        """

        message: RFC822Message = RFC822Message()
        line: str
        for line in metadata.splitlines():
            line = line.rstrip("\r\n")
            if not line:
                # End of headers
                break
            key: str
            value: Optional[str]
            key, _, value = line.partition(":")
            if not value:
                raise ValueError(f"Could not parse metadata line {line!r}")
            message[key] = value
        return message

    def core_metadata_reference(self) -> RFC822Message:
        # We have several different ways to get metadata from the package:
        # - Download wheel (or sdist) and install it, then use importlib_metadata to get the metadata:
        #
        #       distribution: importlib_metadata.Distribution = importlib_metadata.distribution(self.name)
        #       expected_metadata: importlib_metadata.PackageMetadata = distribution.metadata
        #       entry_points: importlib_metadata.EntryPoints = distribution.entry_points
        #
        # - Download sdist and extract it, then use the packaging system to emit the metadata
        #
        # - Download wheel and use wheel_inspect or importlib_metadata to get the metadata without
        #   installing it
        #
        #        subprocess.check_call(
        #            ["pip", "download", "--only-binary", ":all:", "--no-deps", "--dest", "dist",
        #             f"{self.name}=={self.version}"]
        #        )
        #        etc.
        #
        # - Download metadata directly from PyPI, if it's available
        #
        # Theoretically all ways should give the same result; if not, we've got
        # some more investigating to do.

        releases: Sequence[PackageInfo] = self._parse_pypi_simple_listing()
        try:
            wheel_release: PackageInfo = next(r for r in releases if r.package_type == PackageType.WHEEL)
        except StopIteration:
            raise ValueError("No wheel found")
        else:
            metadata: str = self._get_metadata_from_pypi(wheel_release)
            return self._parse_metadata_from_text(metadata)
