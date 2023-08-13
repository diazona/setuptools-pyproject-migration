import json
import setuptools

from typing import Any, Dict, List, Optional, Tuple


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
                    metadata.setdefault("methods", {})[attr] = self._to_json(value)
                except Exception:
                    continue
            else:
                metadata.setdefault("properties", {})[attr] = self._to_json(value)

        print(json.dumps(metadata, indent=4, sort_keys=True))

    def _to_json(self, v: Any) -> Any:
        if (v is None) or isinstance(v, (bool, int, str)):
            return v
        elif isinstance(v, list):
            return [self._to_json(e) for e in v]
        elif isinstance(v, dict):
            return dict([(self._to_json(k), self._to_json(e)) for k, e in v.items()])
        else:
            return repr(v)


__all__ = ["DumpMetadata"]
