from typing import Any


# todo: support floating point numbers as keys
class _Timed_Data:
    def __init__(self):
        self._data = {}

    def __getitem__(self, ts: int):
        return self._data.get(ts, None)

    def __setitem__(self, ts: int, item: Any):
        self._data[ts] = item

    def __delitem__(self, ts: int):
        self._data.pop(ts, None)
