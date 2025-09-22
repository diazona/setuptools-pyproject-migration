import re
from typing import Dict, Generic, Optional, Sequence, TypeVar, Union

from .data import load_licenses, load_exceptions, LicenseDict, LicenseExceptionDict
from .types import (
    License,
    LicenseException,
    LicenseExpression,
    VersionOrLaterLicense,
    LicenseWithException,
    CompositeAndExpression,
    CompositeOrExpression,
    SimpleLicense,
)

RegistryType = TypeVar("RegistryType", bound=Union[SimpleLicense, LicenseException])
RegistryDerivedType = TypeVar("RegistryDerivedType", bound=Union[SimpleLicense, LicenseException])
RawType = TypeVar("RawType")


class Registry(Generic[RegistryType, RegistryDerivedType, RawType]):
    """In-memory database of entities."""

    def __init__(self, raw_entities: Sequence[RawType]):
        by_id: Dict[str, RegistryType] = {}
        by_name: Dict[str, RegistryType] = {}

        for raw_entity in raw_entities:
            entity: RegistryType = self._parse(raw_entity)
            by_id[entity.id.upper()] = entity
            by_name[entity.name.upper()] = entity

        self._by_id: Dict[str, RegistryType] = by_id
        self._by_name: Dict[str, RegistryType] = by_name

    def _raw_lookup_id(self, entity_id: str) -> RegistryType:
        """Look up an entity by ID (case insensitive), return the base type only."""
        try:
            return self._by_id[entity_id.upper()]
        except KeyError:
            pass

        # Raise exception with original given value
        raise KeyError(entity_id)

    def _raw_lookup_name(self, entity_name: str) -> RegistryType:
        """Look up an entity by name (case insensitive), return the base type only."""
        try:
            return self._by_name[entity_name.upper()]
        except KeyError:
            pass

        # Raise exception with original given value
        raise KeyError(entity_name)

    def lookup_id(self, entity_id: str) -> Union[RegistryType, RegistryDerivedType]:
        """Look up an entity by ID (case insensitive)"""
        return self._raw_lookup_id(entity_id)

    def lookup_name(self, entity_name: str) -> Union[RegistryType, RegistryDerivedType]:
        """Look up an entity by name (case insensitive)"""
        return self._raw_lookup_name(entity_name)

    def _parse(self, raw_entity: RawType) -> RegistryType:
        raise NotImplementedError


class LicensesRegistry(Registry[License, SimpleLicense, LicenseDict]):
    @staticmethod
    def _parse(raw_license: LicenseDict) -> License:
        return License.from_dict(raw_license)

    def __init__(self):
        super(load_licenses()["licenses"])

    def lookup_id(self, entity_id: str) -> SimpleLicense:
        if entity_id.endswith(VersionOrLaterLicense.SUFFIX):
            return VersionOrLaterLicense(license=self._raw_lookup_id(entity_id[: -len(VersionOrLaterLicense.SUFFIX)]))
        else:
            return self._raw_lookup_id(entity_id)


class ExceptionsRegistry(Registry[LicenseException, LicenseException, LicenseExceptionDict]):
    @staticmethod
    def _parse(raw_license: LicenseExceptionDict) -> LicenseException:
        return LicenseException.from_dict(raw_license)

    def __init__(self):
        super(load_exceptions()["exceptions"])


class ExpressionParser:
    _SPACES = re.compile(" +")
    _OPEN_BRACKET = "("
    _CLOSE_BRACKET = ")"
    _LICENSES: Optional[LicensesRegistry] = None
    _EXCEPTIONS: Optional[ExceptionsRegistry] = None

    @classmethod
    def _init(cls):
        if cls._LICENSES is None:
            cls._LICENSES = LicensesRegistry()
        if cls._EXCEPTIONS is None:
            cls._EXCEPTIONS = ExceptionsRegistry()

    @classmethod
    def parse(cls, expression: str) -> LicenseExpression:
        """Parse a SPDR license expression and return the abstract tree it represents."""
        cls._init()
        parser = ExpressionParser(expression)
        return parser._parse()

    def __init__(self, expression: str):
        self._expression = expression

    def _parse(self) -> LicenseExpression:
        raise NotImplementedError("TODO")

    def _make_and(self, expressions: Sequence[LicenseExpression]):
        return CompositeAndExpression(set(expressions))

    def _make_or(self, expressions: Sequence[LicenseExpression]):
        return CompositeOrExpression(set(expressions))

    def _make_exception(self, license, license_exception):
        return LicenseWithException(license=license, exception=license_exception)
