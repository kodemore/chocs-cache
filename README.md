# Chocs-cache <br> [![PyPI version](https://badge.fury.io/py/chocs-middleware.cache.svg)](https://pypi.org/project/chocs-middleware.cache/) [![CI](https://github.com/kodemore/chocs-cache/actions/workflows/main.yaml/badge.svg)](https://github.com/kodemore/chocs-cache/actions/workflows/main.yaml) [![Release](https://github.com/kodemore/chocs-cache/actions/workflows/release.yml/badge.svg)](https://github.com/kodemore/chocs-cache/actions/workflows/release.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
Cache middleware for chocs library.

## Features

- Easy integration
- Support for ETags
- Support for conditional request headers `if-none-match`, `if-match`
- Built-in in-memory cache storage for debugging and testing purposes
- Automatic cache revalidation

## Installation

With pip,
```shell
pip install chocs-middleware.cache
```
or through poetry
```shell
poetry add chocs-middleware.cache
```

# Usage

## Simple cache
The following example shows the simplest usage of cache mechanism with a custom
in-memory cache storage.

```python
import chocs
from chocs import HttpRequest, HttpResponse
from chocs_middleware.cache import ICacheStorage, CacheItem, CacheMiddleware


class MemoryCache(ICacheStorage):
    """
    Custom cache storage that uses memory to store the cache items.
    In production, this should use Redis or other cache databases used by your application.
    """

    def __init__(self):
        self._cache = {}

    def get(self, cache_id: str) -> CacheItem:
        return self._cache[cache_id]

    def set(self, item: CacheItem) -> None:
        self._cache[item.id] = item


app = chocs.Application(CacheMiddleware(MemoryCache()))


@app.get("/users/{user_id}", cache_expiry=10)
def get_user(request: HttpRequest) -> HttpResponse:
    """
    cache_expiry enables caching for the returned response and keeps
    it alive for 10 seconds. 
    """

    return HttpResponse("Bob Bobber", 200)
```

## ETag based cache

To make use of e-tags simply return the e-tag header in the response, like in the example below:

```python
import chocs
from chocs import HttpRequest, HttpResponse
from chocs_middleware.cache import CacheMiddleware, InMemoryCacheStorage

app = chocs.Application(CacheMiddleware(InMemoryCacheStorage()))


@app.get("/users/{user_id}", cache_expiry=10)
def get_user(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Bob Bobber", headers={
        "etag": '"etag-1"', # your custom etag value
    })
```

> Keep in mind e-tag values MUST BE unique per REST endpoint and per content type to avoid cache collisions.

## Using cache vary

To allow the cache system better understand your intention it is recommended to use the `cache_vary` attribute.
You can read more about the `Vary` header [here](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Vary)

```python
import chocs
from chocs import HttpRequest, HttpResponse
from chocs_middleware.cache import CacheMiddleware, InMemoryCacheStorage

# you can specify cache vary globally when initialising middleware
app = chocs.Application(CacheMiddleware(InMemoryCacheStorage(), cache_vary=set("accept-language")))

# or you can specify cache vary per endpoint
@app.get("/users/{user_id}", cache_expiry=10, cache_vary=("accept-language", "x-custom-header"))
def get_user(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Bob Bobber")
```

## Specifying cache control

You can also specify the type of cache by setting the `cache_control` attribute to `public` or `private`.
You can read more about cache-control [here](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#types_of_caches)

```python
import chocs
from chocs import HttpRequest, HttpResponse
from chocs_middleware.cache import CacheMiddleware, InMemoryCacheStorage

app = chocs.Application(CacheMiddleware(InMemoryCacheStorage()))

# cache control can only be specified in the route definition.
@app.get("/users/{user_id}", cache_expiry=10, cache_control="private")
def get_user(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Bob Bobber")
```

## Conditional request support

This cache system supports conditional requests headers [`if-none-match`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match) 
and [`if-match`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-Match) in a limited manner.
This means values passed in `if-none-match` and `if-match` headers will be treated as a single value.

## Cache revalidation

The middleware provides `ICollectableCache` interfaces that you can use to implement your  
cache re-validation. It might be just a simple mechanism that just deletes the stale cache, but
there are no limitations and more powerful systems might be built on the top of the interface.

The following diagram represents the way how to cache revalidation works in the middleware:
![Cache Revalidation](./docs/cache_revalidation.png)


The following example shows the simplest implementation of cache re-validation:

```python
from chocs import Application, HttpRequest, HttpResponse
from chocs_middleware.cache import ICollectableCacheStorage, CacheItem, CacheMiddleware


class CacheStorage(ICollectableCacheStorage):
    def __init__(self):
        self._storage = {}

    def set(self, item: CacheItem) -> None:
        self._storage[item.id] = item

    def get(self, item_id: str) -> CacheItem:
        return self._storage[item_id]

    def collect(self, item: CacheItem) -> None:
        del self._storage[item.id]

app = Application(CacheMiddleware(CacheStorage))

@app.get("/users/{user_id}", cache_expiry=10)
def get_test(req: HttpRequest) -> HttpResponse:
    user_id = req.path_parameters.get("user_id")
    return HttpResponse(f"user {user_id}", headers={"etag": f"{user_id}"})


@app.patch("/users/{user_id}", cache=True)  # cache attribute enables cache middleware for the endpoint, to collect stale data
def get_test(req: HttpRequest) -> HttpResponse:
    """
    Once this function generate a successful response and cache exists for the given user CacheStorage.collect is called
    """
    return HttpResponse("{user data}")
```
