import re

from typing import NamedTuple, Union
from wheel_filename import ParsedWheelFilename, parse_wheel_filename


def normalize_package_name(name: str):
    """
    Normalize a Python package name in the manner specified by :pep:`503`.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


class ParsedSdistFilename(NamedTuple):
    project: str
    version: str


def parse_package_filename(filename: str) -> Union[ParsedSdistFilename, ParsedWheelFilename]:
    if filename.endswith(".whl"):
        return parse_wheel_filename(filename)
    elif filename.endswith(".tar.gz"):
        # PEP 625 specifies that "-" should not occur in the
        name, _, version = filename[:-7].partition("-")
        return ParsedSdistFilename(name, version)
    else:
        raise ValueError(f"Not a valid Python package filename: {filename}")
