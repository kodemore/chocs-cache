from datetime import datetime, timedelta

from chocs import Application
from chocs import HttpResponse, HttpStatus, HttpRequest, HttpMethod

from chocs_middleware.cache import CacheMiddleware, InMemoryCacheStorage, CollectableInMemoryCacheStorage
from chocs_middleware.cache.cache_storage import generate_cache_id, CacheItem


def test_can_skip_cache() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    request = HttpRequest(HttpMethod.GET, "/test")
    response = HttpResponse("test", headers={"test": "ok"})
    controller_call_count = 0

    @app.get("/test")
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return response

    # when
    responses = [
        app(request),
        app(request),
        app(request),
        app(request),
        app(request),
    ]

    # then
    assert controller_call_count == 5
    for item in responses:
        assert item == response


def test_can_use_simple_caching_strategy() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    request = HttpRequest(HttpMethod.GET, "/test")
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok"})

    # when
    response = app(request)
    cached_response = app(request)

    # then
    assert controller_call_count == 1
    assert cached_response.body.read() == b"test"
    assert response.body.read() == b"test"
    assert response is not cached_response

    assert "cache-control" in response.headers
    assert response.headers["cache-control"] == "max-age=10"
    assert "vary" in response.headers
    assert response.headers["vary"].lower() == "accept,accept-language"
    assert "test" in response.headers
    assert "age" not in response.headers
    assert "last-modified" not in response.headers

    assert "age" in cached_response.headers
    assert cached_response.headers["age"] == "0"
    assert "vary" in cached_response.headers
    assert cached_response.headers["vary"].lower() == "accept,accept-language"
    assert "last-modified" in cached_response.headers
    assert "test" in cached_response.headers


def test_can_use_simple_caching_strategy_with_head_request() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    request = HttpRequest(HttpMethod.GET, "/test")
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    @app.head("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok"})

    # when
    response = app(request)
    cached_response = app(HttpRequest(HttpMethod.HEAD, "/test"))

    # then
    assert cached_response.status_code == HttpStatus.NOT_MODIFIED


def test_can_use_etag_based_cache() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok", "etag": '"1"'})

    # when
    response = app(HttpRequest(HttpMethod.GET, "/test"))
    cached_response = app(HttpRequest(HttpMethod.GET, "/test", headers={"etag": '"1"'}))
    cached_response.body.seek(0)

    # then
    assert controller_call_count == 1
    assert response.status_code == HttpStatus.OK
    assert cached_response.status_code == HttpStatus.NOT_MODIFIED

    assert not cached_response.body.read()
    assert "age" in cached_response.headers
    assert cached_response.headers["age"] == "0"
    assert "vary" in cached_response.headers
    assert cached_response.headers["vary"].lower() == "accept,accept-language"
    assert "last-modified" in cached_response.headers
    assert "test" in cached_response.headers


def test_can_serve_response_for_non_existing_etag() -> None:
    # given
    app = Application(CacheMiddleware(InMemoryCacheStorage()))
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok", "etag": '"1"'})

    # when
    response = app(HttpRequest(HttpMethod.GET, "/test"))
    cached_response = app(HttpRequest(HttpMethod.GET, "/test", headers={"etag": '"2"'}))

    # then
    assert response == cached_response
    assert controller_call_count == 2


def test_can_serve_response_for_expired_cache() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    request = HttpRequest(HttpMethod.GET, "/test")
    e_tag = '"1"'
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok", "etag": e_tag})

    # when
    response = app(request)
    cache_item = cache.get("1")
    cache_item._expires_at = datetime.utcnow() - timedelta(0, -20)
    cached_response = app(request)

    # then
    assert response == cached_response
    assert controller_call_count == 2


def test_can_pass_conditional_request_if_none_match() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    e_tag = '"1"'
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok", "etag": e_tag})

    # when
    response = app(HttpRequest(HttpMethod.GET, "/test"))
    response_without_cache = app(HttpRequest(HttpMethod.GET, "/test", headers={
        "etag": e_tag,
        "if-none-match": "non-existing-etag",
    }))

    # then
    assert controller_call_count == 2
    assert response.status_code == HttpStatus.OK
    assert response_without_cache.status_code == HttpStatus.OK

    assert response == response_without_cache


def test_can_fail_conditional_request_if_none_match() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    e_tag = '"1"'
    controller_call_count = 0
    cache.set(CacheItem("existing_etag", b""))

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok", "etag": e_tag})

    # when
    response = app(HttpRequest(HttpMethod.GET, "/test"))
    cached_response = app(HttpRequest(HttpMethod.GET, "/test", headers={
        "etag": e_tag,
        "if-none-match": "existing_etag",
    }))

    # then
    assert controller_call_count == 1
    assert response.status_code == HttpStatus.OK
    assert cached_response.status_code == HttpStatus.NOT_MODIFIED


def test_can_fail_conditional_request_with_precondition_failure() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    cache.set(CacheItem("existing_etag", b""))

    @app.post("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        return HttpResponse("test")

    # when
    response = app(HttpRequest(HttpMethod.POST, "/test", headers={"if-none-match": "existing_etag"}))

    # then
    assert response.status_code == HttpStatus.PRECONDITION_FAILED


def test_can_pass_conditional_request_if_match() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    e_tag = '"1"'
    controller_call_count = 0
    cache.set(CacheItem("etag", b""))

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok", "etag": e_tag})

    # when
    response = app(HttpRequest(HttpMethod.GET, "/test"))
    response_without_cache = app(HttpRequest(HttpMethod.GET, "/test", headers={
        "if-match": "etag",
    }))

    # then
    assert controller_call_count == 2
    assert response.status_code == HttpStatus.OK
    assert response_without_cache.status_code == HttpStatus.OK

    assert response == response_without_cache


def test_can_fail_conditional_request_if_match() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    e_tag = '"1"'
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test", headers={"test": "ok", "etag": e_tag})

    # when
    response = app(HttpRequest(HttpMethod.GET, "/test"))
    cached_response = app(HttpRequest(HttpMethod.GET, "/test", headers={
        "if-match": "etag",
        "etag": "1"
    }))

    # then
    assert controller_call_count == 1
    assert response.status_code == HttpStatus.OK
    assert cached_response.status_code == HttpStatus.NOT_MODIFIED


def test_can_fail_conditional_request_if_match_with_precondition_failure() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        return HttpResponse("test", headers={"test": "ok"})

    # when
    response = app(HttpRequest(HttpMethod.GET, "/test", headers={
        "if-match": "etag",
    }))

    # then
    assert response.status_code == HttpStatus.PRECONDITION_FAILED


def test_can_skip_caching_for_non_safe_methods() -> None:
    # given
    cache = InMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))

    @app.post("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        return HttpResponse("test")

    # when
    app(HttpRequest(HttpMethod.POST, "/test"))

    # then
    assert cache.is_empty


def test_can_collect_stale_cache() -> None:
    # given
    cache = CollectableInMemoryCacheStorage()
    app = Application(CacheMiddleware(cache))
    controller_call_count = 0

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        nonlocal controller_call_count
        controller_call_count += 1
        return HttpResponse("test")

    @app.delete("/test", cache=True)
    def delete_test(req: HttpRequest) -> HttpResponse:
        return HttpResponse()

    # when
    app(HttpRequest(HttpMethod.GET, "/test"))
    app(HttpRequest(HttpMethod.GET, "/test"))

    # then
    assert controller_call_count == 1
    assert len(cache) == 1
    assert not cache.is_empty

    # when
    app(HttpRequest(HttpMethod.DELETE, "/test"))

    # then
    assert cache.is_empty


def test_can_update_etag_in_cached_item() -> None:
    # given
    cache_storage = CollectableInMemoryCacheStorage()
    app = Application(CacheMiddleware(cache_storage))
    cache_item = CacheItem.empty("1")  # this is an expired item by default

    @app.get("/test", cache_expiry=10)
    def get_test(req: HttpRequest) -> HttpResponse:
        return HttpResponse("test", headers={"etag": "2"})

    # when
    cache_storage.set(cache_item)
    app(HttpRequest(HttpMethod.GET, "/test", headers={"etag": "1"}))

    # then
    assert cache_item.id == "2"
    assert len(cache_storage) == 1
