import importlib
import json
from typing import Type, TypedDict, List

# The raw data types, as we'll see from the JSON file

LicenseDict: Type = TypedDict(
    "LicenseDict",
    {
        "reference": str,
        "isDeprecatedLicenseId": bool,
        "detailsUrl": str,
        "referenceNumber": int,
        "name": str,
        "licenseId": str,
        "seeAlso": List[str],
        "isOsiApproved": bool,
        "isFsfLibre": bool,
    },
)
LicenseDict.__doc__ = """A representation of the raw dict we get from the json module after parsing."""

LicenseDataFile: Type = TypedDict(
    "LicenseDataFile",
    {
        "licenseListVersion": str,
        "licenses": List[LicenseDict],
        "releaseDate": str,  # ISO-8601 format
    },
)
LicenseDataFile.__doc__ = """The raw content of the licenses.json file."""


LicenseExceptionDict: Type = TypedDict(
    "LicenseExceptionDict",
    {
        "reference": str,
        "isDeprecatedLicenseId": bool,
        "detailsUrl": str,
        "referenceNumber": int,
        "name": str,
        "licenseExceptionId": str,
        "seeAlso": List[str],
    },
)
LicenseExceptionDict.__doc__ = """A representation of the raw dict we get from the json module after parsing."""


ExceptionDataFile: Type = TypedDict(
    "ExceptionDataFile",
    {
        "licenseListVersion": str,
        "exceptions": List[LicenseExceptionDict],
        "releaseDate": str,  # ISO-8601 format
    },
)
ExceptionDataFile.__doc__ = """The raw content of the exceptions.json file."""

# Raw file parsing logic


def load_licenses() -> LicenseDataFile:
    """Read and parse the embedded licenses.json data file"""
    raw = json.loads(importlib.resources.read_text(__package__, "licenses.json"))
    licenses: List[LicenseDict] = [
        LicenseDict(
            reference=str(lic["reference"]),
            isDeprecatedLicenseId=bool(lic.get("isDeprecatedLicenseId", False)),
            detailsUrl=str(lic["detailsUrl"]),
            referenceNumber=int(lic["referenceNumber"]),
            name=str(lic["name"]),
            licenseId=str(lic["licenseId"]),
            seeAlso=[str(uri) for uri in lic.get("seeAlso", [])],
            isOsiApproved=bool(lic.get("isOsiApproved", False)),
            isFsfLibre=bool(lic.get("isFsfLibre", False)),
        )
        for lic in raw.pop("licenses")
    ]

    return LicenseDataFile(
        licenseListVersion=raw["licenseListVersion"],
        licenses=licenses,
        releaseDate=raw["releaseDate"],
    )


def load_exceptions() -> ExceptionDataFile:
    """Read and parse the embedded exceptions.json data file"""
    raw = json.loads(importlib.resources.read_text(__package__, "exceptions.json"))
    exceptions: List[LicenseExceptionDict] = [
        LicenseExceptionDict(
            reference=str(exc["reference"]),
            isDeprecatedLicenseId=bool(exc.get("isDeprecatedLicenseId", False)),
            detailsUrl=str(exc["detailsUrl"]),
            referenceNumber=int(exc["referenceNumber"]),
            name=str(exc["name"]),
            licenseExceptionId=str(exc["licenseExceptionId"]),
            seeAlso=[str(uri) for uri in exc.get("seeAlso", [])],
        )
        for exc in raw.pop("exceptions")
    ]

    return ExceptionDataFile(
        licenseListVersion=raw["licenseListVersion"],
        exceptions=exceptions,
        releaseDate=raw["releaseDate"],
    )
