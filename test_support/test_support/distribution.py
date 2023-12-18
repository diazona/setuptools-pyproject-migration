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
import io
import logging
import packaging
import pathlib
import re
import requests
import tarfile
import urllib.parse
import warnings

from abc import ABC, abstractmethod
from test_support import importlib_metadata, Project
from test_support.metadata import parse_core_metadata
from typing import Any, IO, Iterable, List, Optional, Sequence

try:
    from pyproject_metadata import RFC822Message, StandardMetadata
except ImportError:
    # pyproject-metadata is not available for Python <3.7. That's okay because
    # we skip all the tests that would use RFC822Message if pyproject-metadata
    # is not available, so that name doesn't need to have a definition that is
    # valid at runtime, but pytest still scans this file looking for doctests
    # so it still needs to be importable. As long as this name is defined as
    # _something_ which is a valid type, that will be the case.
    class RFC822Message:  # type: ignore[no-redef]
        pass

    class StandardMetadata:  # type: ignore[no-redef]
        pass


try:
    from functools import cached_property
except ImportError:
    from backports.cached_property import cached_property  # type: ignore[no-redef]


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


def _download(url: str, destination: pathlib.Path) -> pathlib.Path:
    """
    Download the content of a URL to a local file.

    :param url: The URL to download
    :param destination: Path to save the downloaded content to. If the path
        refers to an existing directory, then the download will be saved to
        a new file created in that directory whose name is determined from
        the URL and/or the response metadata. Otherwise, the path must not
        exist, and the content will be saved to a new file created at that
        path.
    :raises ValueError: If the download would overwrite an existing file
    :raises requests.HTTPError: If the attempt to access the URL returns
        an HTTP status code that indicates failure (in this case the file
        will not be created)
    """
    if destination.is_dir():
        # If necessary we could add support for the Content-Disposition header
        # or other methods of determining the filename
        parsed_url = urllib.parse.urlparse(url)
        _, _, tail = parsed_url.path.rpartition("/")
        # Unlikely that we need to split on ';' but it's easy enough to make sure
        filename, _, _ = tail.partition(";")
        destination = destination / filename

    if destination.exists():
        raise ValueError("File {destination} already exists")

    response = requests.get(url)
    response.raise_for_status()
    with destination.open("wb") as f:
        for chunk in response.iter_content(chunk_size=20 * 512):  # arbitrarily chosen chunk size
            f.write(chunk)

    return destination


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
    def prepare(self, path: pathlib.Path) -> "DistributionPackagePreparation":
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


class DistributionPackagePreparation:
    """
    A distribution package that has been prepared for testing. "Prepared" means
    the source code is downloaded/extracted/checked out/whatever in a local
    directory, in a state that allows |project| to run on it to generate
    a ``pyproject.toml`` file.

    .. note:
        The "preparation" in the class name should be understood as the result
        of preparing, not the _act_ of preparing. (Naming is hard)

    :param make_importable: When running |project| on the code of the distribution
        package, the code is in a "raw" form that may not be usable, since many
        distribution packages require a build step to go from their raw code to
        something that can be imported. So, in accordance with standard packaging
        conventions, by default we don't make the distribution package's own code
        available for import when running its ``setup.py``. But some projects
        (that don't have build steps) expect their own code to be importable
        straight from the filesystem when running their ``setup.py`` file. This
        flag can be set to ``True`` to make that happen during testing.
    """

    def __init__(self, make_importable: bool = False) -> None:
        self.make_importable: bool = make_importable

    @property
    @abstractmethod
    def project(self) -> Project:
        """
        Return the :py:class:`test_support.Project` instance which can be used
        to compute the metadata from the prepared source code.
        """

    @property
    @abstractmethod
    def core_metadata_reference(self) -> StandardMetadata:
        """
        Return the known correct core metadata for the distribution package.
        Typically this comes from the package's wheel, if a wheel is available.

        :return: The known correct core metadata for the distribution package
        """


class PyPiDistribution(DistributionPackage):
    """
    A distribution package obtained from PyPI.

    :param name: The name of the project as registered on PyPI, i.e. the name
         in the project's URL: ``https://pypi.org/project/<name>``
    :param version: The version string of the project as registered on PyPI
    :param project_root: The relative path within the project's sdist to
        the directory containing ``setup.py`` or ``setup.cfg``. If omitted,
        this defaults to ``<name>-<version>`` with ``<name>`` normalized in
        the manner specified by the `sdist specification`_. Because the spec was
        designed to match what the vast majority of build tools actually produce
        in sdist files, it should be extremely rare to have to specify a custom
        project root.
    :param make_importable: When running |project| on the code of the distribution
        package, the code is in a "raw" form that may not be usable, since many
        distribution packages require a build step to go from their raw code to
        something that can be imported. So, in accordance with standard packaging
        conventions, by default we don't make the distribution package's own code
        available for import when running its ``setup.py``. But some projects
        (that don't have build steps) expect their own code to be importable
        straight from the filesystem when running their ``setup.py`` file. This
        flag can be set to ``True`` to make that happen during testing.

    .. _sdist specification: https://packaging.python.org/en/latest/specifications/source-distribution-format/
    """

    def __init__(
        self,
        name: str,
        version: str,
        *,
        project_root: Optional[pathlib.Path] = None,
        make_importable: bool = False,
    ):
        super().__init__()
        self.name: str = name
        self.version: str = version
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
        self.make_importable: bool = make_importable

    def prepare(self, path: pathlib.Path) -> DistributionPackagePreparation:
        """
        Populate a directory with the package's source code. This involves
        downloading the sdist and extracting it.
        """
        return PyPiPackagePreparation(self, path)


class PyPiPackagePreparation(DistributionPackagePreparation):
    """
    :param distribution_package: The distribution package to prepare
    :param path: A temporary directory to use in preparing the distribution
        package. Typically this would be provided by pytest's ``tmp_path``
        fixture.
    """

    def __init__(self, distribution: PyPiDistribution, path: pathlib.Path) -> None:
        super().__init__(distribution.make_importable)

        self._distribution: PyPiDistribution = distribution
        self._path: pathlib.Path = path

        # The download path must be set before using self._sdist
        self._download_path = path / "downloads"

        self._project_path = path / "project"

    @cached_property
    def project(self) -> Project:
        sdist: Optional[pathlib.Path] = self._sdist
        if not sdist:
            raise RuntimeError(f"sdist not available for {self._distribution.package_spec}")
        self._project_path.mkdir(exist_ok=True)
        _logger.debug("Extracting to %s", self._project_path)
        with tarfile.open(sdist) as tf:
            try:
                tf.extractall(path=self._project_path, filter="data")
            except TypeError:
                tf.extractall(path=self._project_path)  # for Python <3.8
        abs_project_root: pathlib.Path = self._project_path / self._distribution.project_root
        _logger.debug("Project root: %s", abs_project_root)
        if not (abs_project_root / "setup.py").exists() and not (abs_project_root / "setup.cfg").exists():
            _logger.warning("No setup.py or setup.cfg in project root %s", abs_project_root)
        return Project(abs_project_root)

    @cached_property
    def _pypi_downloads(self) -> Sequence[PackageInfo]:
        """
        Access the PyPI simple API to download and parse the page that lists
        versions for the package.

        :return: A collection of :py:class:`PackageInfo` objects representing
            all available releases of the right name and version. Typically this
            will include one sdist and at least one wheel.
        """

        # Ideally we could use the pypi-simple package, but it doesn't support
        # metadata downloads. (https://github.com/jwodder/pypi-simple/issues/6)
        simple_api_response = requests.get(f"https://pypi.org/simple/{self._distribution.name}/")
        simple_api_response.raise_for_status()
        parser: SimplePackageListingParser = SimplePackageListingParser(
            self._distribution.name, self._distribution.version
        )
        parser.feed(simple_api_response.text)
        return parser.releases

    def _download(self, url: str) -> pathlib.Path:
        """
        Download the content of a URL to a local file under this preparation's
        download directory.

        :param url: The URL to download
        :raises ValueError: If the download would overwrite an existing file
        :raises requests.HTTPError: If the attempt to access the URL returns
            an HTTP status code that indicates failure (in this case the file
            will not be created)
        """
        self._download_path.mkdir(exist_ok=True)
        return _download(url, self._download_path)

    @cached_property
    def _sdist(self) -> Optional[pathlib.Path]:
        """
        Download the sdist for the package.

        :return: The path to the downloaded sdist, or ``None`` if the URL to
            the sdist could not be determined
        :raises requests.HTTPError: If the attempt to download the sdist returns
            an HTTP status code that indicates failure
        """
        releases: Sequence[PackageInfo] = self._pypi_downloads
        try:
            sdist_release: PackageInfo = next(r for r in releases if r.package_type == PackageType.SDIST)
        except StopIteration:
            return None

        sdist_path: pathlib.Path = self._download(sdist_release.package_url)
        assert sdist_path.name == f"{self._distribution.basename}.tar.gz", f"Filename mismatch: {sdist_path!s}"
        return sdist_path

    @cached_property
    def _wheel(self) -> Optional[pathlib.Path]:
        """
        Download a wheel for the package.

        .. note::
            It's arbitrary which wheel will be downloaded, if there is more than
            one for the given package name and version. We assume that they all
            have the same core metadata. If that proves not to be the case, this
            API would have to change.

        :return: The path to the downloaded wheel, or ``None`` if the URL to
            the wheel could not be determined
        :raises requests.HTTPError: If the attempt to download the wheel returns
            an HTTP status code that indicates failure
        :raises ValueError: If a separate metadata file was available and a hash
            was provided for that file, and the file content did not match
            the hash
        """
        releases: Sequence[PackageInfo] = self._pypi_downloads
        try:
            wheel_release: PackageInfo = next(r for r in releases if r.package_type == PackageType.WHEEL)
        except StopIteration:
            return None

        wheel_path: pathlib.Path = self._download(wheel_release.package_url)
        if not wheel_release.metadata_hasher:
            warnings.warn(f"No hash available for {self._distribution.package_spec}")
        elif not wheel_release.metadata_hasher.check(wheel_path.read_bytes()):
            raise ValueError(f"Hash verification failed for {self._distribution.package_spec}")
        return wheel_path

    @staticmethod
    def _parse_metadata_from_text(metadata: str) -> RFC822Message:
        """
        Parse a text representation of package metadata into an :py:class:`RFC822Message`.

        This is meant to do the same thing as :py:class:`email.parser.HeaderParser`
        except that it produces an ``RFC822Message``.
        """

        message: RFC822Message = RFC822Message()
        raw_metadata = io.StringIO(metadata)
        line: str
        for line in raw_metadata:
            line = line.rstrip("\r\n")
            if not line:
                # End of headers
                break
            key: str
            value: Optional[str]
            key, _, value = line.partition(":")
            if not value:
                raise ValueError(f"Could not parse metadata line {line!r}")
            message[key] = value.strip()
        body: str = raw_metadata.read()
        if body:
            message.body = body
        return message

    @cached_property
    def _core_metadata_from_pypi(self) -> Optional[StandardMetadata]:
        """
        Download the core metadata for a package directly from a metadata file
        on PyPI.

        This will try to download a separate metadata file as specified in
        :pep:`658`. If that file exists, can be downloaded, and passes hash
        verification (if a hash is available), then this will return
        the metadata parsed from the file contents.

        :return: The metadata from the separate metadata file on PyPI, if it
            could be found and parsed, otherwise ``None``
        :raises ValueError: If a separate metadata file was available and a hash
            was provided for that file, and the file content did not match
            the hash
        """
        releases: Sequence[PackageInfo] = self._pypi_downloads
        try:
            wheel_release: PackageInfo = next(r for r in releases if r.package_type == PackageType.WHEEL)
        except StopIteration:
            _logger.debug("No wheel found on PyPI")
            return None

        metadata_response = requests.get(wheel_release.metadata_url)
        if metadata_response.status_code == requests.codes.ok:
            _logger.debug("Metadata file found on PyPI")
            if not wheel_release.metadata_hasher:
                warnings.warn(f"No metadata hash available for {self._distribution.package_spec}")
            elif not wheel_release.metadata_hasher.check(metadata_response.content):
                raise ValueError(f"Metadata hash verification failed for {self._distribution.package_spec}")
            return parse_core_metadata(self._parse_metadata_from_text(metadata_response.text))
        elif metadata_response.status_code == requests.codes.not_found:
            _logger.debug("No metadata file found on PyPI")
            return None
        else:
            metadata_response.raise_for_status()
            return None

    @cached_property
    def _core_metadata_from_wheel(self) -> Optional[StandardMetadata]:
        """
        Extract the core metadata for a package from a wheel.

        This will download the actual wheel file from PyPI and extract and parse
        the metadata from it.

        :return: The metadata read and parsed from a wheel file on PyPI, if it
            could be found and parsed, otherwise ``None``
        """
        wheel: Optional[pathlib.Path] = self._wheel
        if not wheel:
            _logger.debug("No wheel found on PyPI")
            return None
        distributions: Iterable[importlib_metadata.Distribution] = importlib_metadata.distributions(path=[wheel])
        try:
            dist: importlib_metadata.Distribution = next(iter(distributions))
        except StopIteration:
            # This happens if the wheel was downloaded but there is no Finder
            # capable of determining its metadata, which shouldn't happen
            # (which is why we raise instead of returning None)
            raise RuntimeError(f"Could not determine metadata from {self._wheel!s}")
        else:
            return parse_core_metadata(dist.metadata)

    @cached_property
    def _core_metadata_from_sdist(self) -> Optional[StandardMetadata]:
        """
        Compute the core metadata for a package from the package's sdist without
        installing it.
        """

        # sdist file characteristics are defined by
        # https://packaging.python.org/en/latest/specifications/source-distribution-format/
        # - must be named {normalized-name}-{version}.tar.gz
        # - must have a single directory at the top level named {normalized-name}-{version}
        # - must include core metadata in a PKG-INFO file in that directory
        sdist: Optional[pathlib.Path] = self._sdist
        if not sdist:
            _logger.debug("No sdist found on PyPI for %s", self._distribution.package_spec)
            return None
        pkg_info_name: str = self._distribution.basename + "/PKG-INFO"
        with tarfile.open(sdist, mode="r:gz") as tf:
            try:
                pkg_info_f: Optional[IO[bytes]] = tf.extractfile(pkg_info_name)
            except KeyError:
                # No PKG-INFO file in the sdist (which is a spec violation)
                _logger.error("No %s file in %s", pkg_info_name, tf.name)
                return None
            else:
                if not pkg_info_f:
                    _logger.error("%s is something other than a file in %s", pkg_info_name, tf.name)
                    # PKG-INFO is something other than a regular file
                    return None
                with pkg_info_f:
                    metadata: str = pkg_info_f.read().decode("utf-8")  # TODO need to consider other encodings?

        return parse_core_metadata(self._parse_metadata_from_text(metadata))

    @property
    def core_metadata_reference(self) -> StandardMetadata:
        metadata: Optional[StandardMetadata] = self._core_metadata_from_pypi
        if metadata:
            _logger.info("Got separate metadata from PyPI for %s", self._distribution.package_spec)
            return metadata
        metadata = self._core_metadata_from_wheel
        if metadata:
            _logger.info("Got metadata from wheel for %s", self._distribution.package_spec)
            return metadata
        metadata = self._core_metadata_from_sdist
        if metadata:
            _logger.info("Got metadata from sdist for %s", self._distribution.package_spec)
            return metadata
        raise RuntimeError("No metadata available")
