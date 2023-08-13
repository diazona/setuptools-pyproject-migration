import distutils.dist
import json
import setuptools

from typing import Any, Dict, List, Optional, Tuple


def serialize_object(o: Any):
    metadata: Dict[str, Dict[str, Any]] = {
        "__class__": o.__class__.__name__,
        "methods": {},
        "properties": {},
    }

    for attr in dir(o):
        if attr.startswith("_"):
            # Ignore 'protected' members
            continue

        value: Any = getattr(o, attr)
        if callable(value):
            if not attr.startswith("get_"):
                # Ignore methods that are not "getters"
                metadata["methods"][attr] = "<not getter>"
                continue

            try:
                value = value()
                metadata["methods"][attr] = value
            except Exception:
                metadata["methods"][attr] = "<not callable>"
        else:
            metadata["properties"][attr] = value

    return metadata


def encode_anything(o: Any):
    if isinstance(o, (distutils.dist.Distribution, distutils.dist.DistributionMetadata)):
        return serialize_object(o)
    return repr(o)


class DumpMetadata(setuptools.Command):  # pragma: no cover
    """
    Dump the metadata provided in the setup package.  This is a debugging tool
    primarily to figure out what fields are exposed and where they may be
    hiding.
    """

    # Note: excluded from coverage, as this is meant as a debugging fixture.

    # Each option tuple contains (long name, short name, help string)
    user_options: List[Tuple[str, Optional[str], str]] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print(json.dumps(self.distribution, indent=4, sort_keys=True, default=encode_anything))


__all__ = ["DumpMetadata"]
