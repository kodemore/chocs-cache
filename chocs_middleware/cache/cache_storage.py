import hashlib
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable, Tuple

from chocs import HttpRequest, HttpMethod

from chocs_middleware.cache.error import CacheError

__all__ = ["InMemoryCacheStorage", "CacheItem", "ICacheStorage", "generate_cache_id"]


class CacheItem:
    _item_id: str
    _body: bytes
    ttl: int
    _created_at: datetime
    _updated_at: datetime
    _expires_at: datetime

    def __init__(self, item_id: str, body: bytes, ttl: int = 30):
        self._item_id = item_id
        self._body = body
        self.ttl = ttl
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()
        self._expires_at = self.updated_at + timedelta(0, self.ttl)

    @property
    def item_id(self) -> str:
        return self._item_id

    @property
    def is_expired(self) -> bool:
        return self.expires_at < datetime.utcnow()

    @property
    def body(self) -> bytes:
        return self._body

    @body.setter
    def body(self, value: bytes) -> None:
        self._body = value
        self._updated_at = datetime.utcnow()
        self._expires_at = self.updated_at + timedelta(0, self.ttl)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    def __bool__(self) -> bool:
        return self._body != b""

    @classmethod
    def empty(cls, cache_id: str) -> 'CacheItem':
        return cls(cache_id, b"", 0)


@runtime_checkable
class ICacheStorage(Protocol):
    @abstractmethod
    def get(self, item_id: str) -> CacheItem:
        ...

    @abstractmethod
    def set(self, item: CacheItem) -> None:
        ...


class InMemoryCacheStorage(ICacheStorage):
    def __init__(self):
        self._cache = {}

    def get(self, item_id: str) -> CacheItem:
        if item_id in self._cache:
            return self._cache[item_id]
        raise CacheError.for_not_found(item_id)

    def set(self, item: CacheItem) -> None:
        self._cache[item.item_id] = item


def generate_cache_id(request: HttpRequest, cache_vary: Tuple[str, ...] = ("accept", "accept-language")) -> str:
    method = request.method

    if method in (HttpMethod.GET, HttpMethod.HEAD):
        method = HttpMethod.GET

    hash_str = f"{method}:{request.path}:{request.query_string}"

    for header in cache_vary:
        hash_str += "".join(request.headers.get(header))

    return hashlib.sha1(hash_str.encode("utf8")).hexdigest()
