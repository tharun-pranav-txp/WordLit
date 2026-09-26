class MemoryCache:
    def __init__(self):
        self._data: dict[str, dict] = {}

    def get(
        self,
        key: str,
    ) -> dict | None:
        return self._data.get(key)

    def set(
        self,
        key: str,
        value: dict,
    ) -> None:
        self._data[key] = value

    def contains(
        self,
        key: str,
    ) -> bool:
        return key in self._data

    def clear(self) -> None:
        self._data.clear()