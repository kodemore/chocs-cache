import pytest

from chocs_middleware.cache import InMemoryCacheStorage, CollectableInMemoryCacheStorage, ICacheStorage, CacheItem, \
    CacheError


def test_can_instantiate() -> None:
    # given
    instance = InMemoryCacheStorage()

    # then
    assert isinstance(instance, InMemoryCacheStorage)
    assert isinstance(instance, ICacheStorage)
    assert instance.is_empty


def test_can_store_item() -> None:
    # given
    instance = InMemoryCacheStorage()

    # when
    instance.set(CacheItem("1", b"test_data"))

    # then
    assert "1" in instance._cache
    assert not instance.is_empty


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


def test_can_delete_item() -> None:
    # given
    instance = CollectableInMemoryCacheStorage()
    item = CacheItem.empty("1")

    # when
    instance.set(item)

    # then
    assert not instance.is_empty
    instance.get(item.id)

    # when
    instance.collect(item)

    # then
    with pytest.raises(CacheError):
        instance.get(item.id)

    assert instance.is_empty
