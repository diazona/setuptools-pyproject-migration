from typing import ForwardRef, List, NamedTuple, Union, Type, Set
from .data import LicenseDict, LicenseExceptionDict


LicenseExpression = Union[
    ForwardRef("SimpleLicense"),
    ForwardRef("VersionOrLaterLicense"),
    ForwardRef("LicenseWithException"),
    ForwardRef("CompositeOrExpression"),
    ForwardRef("CompositeAndExpression"),
]


class SPDXEntity(NamedTuple):
    """Representation of an entity with common fields."""

    id: str
    reference: str
    is_deprecated_license_id: bool
    details_url: str
    reference_number: int
    name: str
    see_also: List[str]

    def __hash__(self) -> int:
        return hash(self.id)


class License(SPDXEntity):
    """Representation of a simple license."""

    is_osi_approved: bool
    is_fsf_libre: bool

    @classmethod
    def from_dict(cls, ld: LicenseDict):
        return cls(
            reference=ld["reference"],
            is_deprecated_license_id=ld["isDeprecatedLicenseId"],
            details_url=ld["detailsUrl"],
            reference_number=ld["referenceNumber"],
            name=ld["name"],
            id=ld["licenseId"],
            see_also=ld["seeAlso"],
            is_osi_approved=ld["isOsiApproved"],
            is_fsf_libre=ld["isFsfLibre"],
        )


class VersionOrLaterLicense(NamedTuple):
    """Represents a license expression that specifies "this version of the license or later"."""

    SUFFIX = "+"

    license: License

    @property
    def id(self) -> str:
        return self.license.id + self.SUFFIX

    def __hash__(self) -> int:
        return hash(self.id)


SimpleLicense: Type = Union[License, VersionOrLaterLicense]


class LicenseException(SPDXEntity):
    """Representation of a simple license exception."""

    reference: str
    is_deprecated_license_id: bool
    details_url: str
    reference_number: int
    name: str
    license_exception_id: str
    see_also: List[str]

    @classmethod
    def from_dict(cls, led: LicenseExceptionDict):
        return cls(
            reference=led["reference"],
            is_deprecated_license_id=led["isDeprecatedLicenseId"],
            details_url=led["detailsUrl"],
            reference_number=led["referenceNumber"],
            name=led["name"],
            id=led["licenseExceptionId"],
            see_also=led["seeAlso"],
        )


class LicenseWithException(NamedTuple):
    """Representation of a license with its exception"""

    OPERATOR = "WITH"

    license: SimpleLicense
    exception: LicenseException

    @property
    def id(self) -> str:
        return "%s %s %s" % (self.license.id, self.OPERATOR, self.exception.id)

    def __hash__(self) -> int:
        return hash((self.OPERATOR, self.license, self.exception))


class CompositeLicenseExpression(NamedTuple):
    """Representation of a license expression that contains more than one
    license sub-expression"""

    expressions: Set[LicenseExpression]

    @property
    def id(self) -> str:
        # Operators are considered commutative, so sort them in a consistent
        # order for direct comparison purposes.
        expr = (" %s " % self.OPERATOR).join(sorted(expr.id for expr in self.expressions))

        if len(self.expressions) > 2:
            return "(%s)" % expr
        else:
            return expr

    def __hash__(self) -> int:
        return hash((self.OPERATOR,) + tuple(self.expressions))


class CompositeOrExpression(CompositeLicenseExpression):
    """Representation of one or more sub-expressions joined with OR"""

    OPERATOR = "OR"


class CompositeAndExpression(CompositeLicenseExpression):
    """Representation of one or more sub-expressions joined with AND"""

    OPERATOR = "AND"
