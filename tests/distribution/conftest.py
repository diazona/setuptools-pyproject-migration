import pytest

from typing import List


def pytest_configure(config: pytest.Config):
    config.addinivalue_line(
        "markers", "distribute(marks): mark a test group with sub-markers to be applied to individual tests by name"
    )


def pytest_collection_modifyitems(items: List[pytest.Item]):
    for item in items:
        base_name, _, _ = item.name.partition("[")
        try:
            marker = next(item.iter_markers("distribute"))
        except StopIteration:
            continue
        sub_marker = marker.args[0].get(base_name, None)
        if sub_marker:
            item.add_marker(sub_marker)
