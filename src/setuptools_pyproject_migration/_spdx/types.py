from typing import List, Union, Set
from .data import LicenseDict, LicenseExceptionDict

LicenseExpression = Union[
    "SimpleLicense",
    "VersionOrLaterLicense",
    "LicenseWithException",
    "CompositeOrExpression",
    "CompositeAndExpression",
]


class DictEntity:
    """A crude class for implementing NamedTuple semantics whilst still preserving the ability to
    subclass base classes to avoid repetition.
    """

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, ", ".join(("%s=%r" for f, v in vars(self).items())))


class SPDXEntity(DictEntity):
    """Representation of an entity with common fields."""

    id: str
    reference: str
    is_deprecated_license_id: bool
    details_url: str
    reference_number: int
    name: str
    see_also: List[str]

    def __init__(
        self,
        id: str,
        reference: str,
        is_deprecated_license_id: bool,
        details_url: str,
        reference_number: int,
        name: str,
        see_also: List[str],
    ) -> None:
        super()
        self.id = id
        self.reference = reference
        self.is_deprecated_license_id = is_deprecated_license_id
        self.details_url = details_url
        self.reference_number = reference_number
        self.name = name
        self.see_also = see_also

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

    def __init__(self, *args, is_osi_approved: bool, is_fsf_libre: bool, **kwargs) -> None:
        super(*args, **kwargs)

        self.is_osi_approved = is_osi_approved
        self.is_fsf_libre = is_fsf_libre


class VersionOrLaterLicense(DictEntity):
    """Represents a license expression that specifies "this version of the license or later"."""

    SUFFIX: str = "+"
    NAME_SUFFIX: str = " or later"

    license: License

    @property
    def id(self) -> str:
        return self.license.id + self.SUFFIX

    @property
    def name(self) -> str:
        return self.license.name + self.NAME_SUFFIX

    def __hash__(self) -> int:
        return hash(self.id)

    def __init__(self, license: License) -> None:
        super()
        self.license = license


SimpleLicense = Union[License, VersionOrLaterLicense]


class LicenseException(SPDXEntity):
    """Representation of a simple license exception."""

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


class LicenseWithException(DictEntity):
    """Representation of a license with its exception"""

    OPERATOR: str = "WITH"

    license: SimpleLicense
    exception: LicenseException

    @property
    def id(self) -> str:
        return "%s %s %s" % (self.license.id, self.OPERATOR, self.exception.id)

    def __hash__(self) -> int:
        return hash((self.OPERATOR, self.license, self.exception))

    def __init__(self, license: SimpleLicense, exception: LicenseException):
        super()
        self.license = license
        self.exception = exception


class CompositeLicenseExpression(DictEntity):
    """Representation of a license expression that contains more than one
    license sub-expression"""

    OPERATOR: str
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

    def __init__(self, expressions: Set[LicenseExpression]):
        super()
        self.expressions = expressions


class CompositeOrExpression(CompositeLicenseExpression):
    """Representation of one or more sub-expressions joined with OR"""

    OPERATOR: str = "OR"


class CompositeAndExpression(CompositeLicenseExpression):
    """Representation of one or more sub-expressions joined with AND"""

    OPERATOR: str = "AND"
