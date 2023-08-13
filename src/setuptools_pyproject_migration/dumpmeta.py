import json
import setuptools

from typing import Any, Dict, List, Optional, Tuple


def encode_anything(o: Any):
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
        metadata: Dict[str, Dict[str, Any]] = {}

        for attr in dir(self.distribution):
            if attr.startswith("_"):
                # Ignore 'protected' members
                continue

            value: Any = getattr(self.distribution, attr)
            if hasattr(value, "__call__"):
                if not attr.startswith("get_"):
                    # Ignore methods that are not "getters"
                    continue

                try:
                    value = value()
                    metadata.setdefault("methods", {})[attr] = value
                except Exception:
                    continue
            else:
                metadata.setdefault("properties", {})[attr] = value

        print(json.dumps(metadata, indent=4, sort_keys=True, default=encode_anything))


__all__ = ["DumpMetadata"]
