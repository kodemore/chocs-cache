import pytest

from chocs_middleware.cache import InMemoryCacheStorage, ICacheStorage, CacheItem, CacheError


def test_can_instantiate() -> None:
    # given
    instance = InMemoryCacheStorage()

    # then
    assert isinstance(instance, InMemoryCacheStorage)
    assert isinstance(instance, ICacheStorage)


def test_can_store_item() -> None:
    # given
    instance = InMemoryCacheStorage()

    # when
    instance.set(CacheItem("1", b"test_data"))

    # then
    assert "1" in instance._cache


def test_can_get_item() -> None:
    # given
    instance = InMemoryCacheStorage()
    item = CacheItem("1", b"test_data")

    # when
    instance.set(item)
    retrieved = instance.get("1")

    # then
    assert retrieved == item


def test_fail_to_get_item() -> None:
    # given
    instance = InMemoryCacheStorage()

    # then
    with pytest.raises(CacheError):
        instance.get("1")

