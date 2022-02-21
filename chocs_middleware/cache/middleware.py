from datetime import datetime
from typing import Tuple

from chocs import HttpMethod, HttpRequest, HttpResponse, HttpStatus
from chocs.middleware import Middleware, MiddlewareHandler

from .cache_storage import CacheItem, ICacheStorage, generate_cache_id
from .http_support import load_response, dump_response, format_date_rfc_1123, parse_etag_value

__all__ = ["CacheMiddleware"]


class CacheMiddleware(Middleware):
    def __init__(self, cache_storage: ICacheStorage, cache_vary: Tuple[str, ...] = ("accept", "accept-language")):
        self._cache_vary = cache_vary
        self._cache_storage = cache_storage

    def handle(self, request: HttpRequest, next: MiddlewareHandler) -> HttpResponse:
        cache_expiry = request.route.attributes.get("cache_expiry", 0)
        cache_control = request.route.attributes.get("cache_control", "")
        cache_vary = request.route.attributes.get("cache_vary", tuple(self._cache_vary))

        assert isinstance(cache_vary, tuple)

        if not cache_expiry:
            return next(request)

        # Generate cache_id
        if "etag" in request.headers:
            cache_id = parse_etag_value(request.headers["etag"])
        else:
            cache_id = generate_cache_id(request, cache_vary)

        cache_item = CacheItem.empty(cache_id)

        try:
            cache_item = self._cache_storage.get(cache_id)
        except Exception:
            ...  # ignore

        # Check for conditional headers `if-none-match` `if-match`
        conditional_headers_exists = "if-none-match" in request.headers or "if-match" in request.headers

        if cache_item and not cache_item.is_expired and request.method in (HttpMethod.GET, HttpMethod.HEAD):
            if "etag" in request.headers and not conditional_headers_exists:
                return self.create_etag_response_from_cache_item(cache_item)

            if "etag" not in request.headers:
                cached_response = load_response(cache_item.body)
                cached_response.headers["Last-Modified"] = format_date_rfc_1123(cache_item.updated_at)
                cached_response.headers["Vary"] = ",".join(cache_vary)
                cached_response.headers["Age"] = str(int((datetime.utcnow() - cache_item.updated_at).total_seconds()))

                if request.method == HttpMethod.HEAD:
                    cached_response.body = b""
                    cached_response.status_code = HttpStatus.NOT_MODIFIED

                return cached_response

        if "if-none-match" in request.headers:
            try:
                # try to get the cached etag
                self._cache_storage.get(parse_etag_value(request.headers.get("if-none-match")))

                # For methods that apply server-side changes, the status code 412 (Precondition Failed) is used.
                if request.method in (HttpMethod.PUT, HttpMethod.PATCH, HttpMethod.POST, HttpMethod.DELETE):
                    return HttpResponse(status=HttpStatus.PRECONDITION_FAILED)

                # When the condition fails for GET and HEAD methods,
                # then the server must return HTTP status code 304 (Not Modified).
                if cache_item and not cache_item.is_expired and request.method in (HttpMethod.GET, HttpMethod.HEAD):
                    return self.create_etag_response_from_cache_item(cache_item)

            except Exception:
                # For GET and HEAD methods, the server will return the requested resource, with a 200 status,
                # only if it doesn't have an ETag matching the given ones

                # For other methods, the request will be processed only if the eventually existing resource's ETag
                # doesn't match any of the values listed.
                ...  # ignore

        if "if-match" in request.headers:
            try:
                self._cache_storage.get(parse_etag_value(request.headers.get("if-match")))
                # we allow request to be processed if there is a match

            except Exception:
                if cache_item and not cache_item.is_expired and request.method in (HttpMethod.GET, HttpMethod.HEAD):
                    return self.create_etag_response_from_cache_item(cache_item)

                return HttpResponse(status=HttpStatus.PRECONDITION_FAILED)

        # cache does not exists
        response = next(request)

        if cache_control:
            response.headers["cache-control"] = f"{cache_control}, max-age={cache_expiry}"
        else:
            response.headers["cache-control"] = f"max-age={cache_expiry}"

        if "vary" not in response.headers:
            response.headers["vary"] = ",".join(cache_vary)
        else:
            cache_vary = response.headers.get("vary")
            if isinstance(cache_vary, str):
                cache_vary = tuple([value.strip() for value in cache_vary.split(",")])
            cache_id = generate_cache_id(request, cache_vary)

        if "etag" in response.headers:
            cache_id = parse_etag_value(response.headers["etag"])

        if not cache_item:
            cache_item = CacheItem(cache_id, dump_response(response), cache_expiry)
        else:
            cache_item.body = dump_response(response)
            cache_item.ttl = cache_expiry

        self._cache_storage.set(cache_item)

        return response

    @staticmethod
    def create_etag_response_from_cache_item(cache_item: CacheItem) -> HttpResponse:
        response = load_response(cache_item.body)
        response.body = b""
        response.status_code = HttpStatus.NOT_MODIFIED

        response.headers["Last-Modified"] = format_date_rfc_1123(cache_item.updated_at)
        response.headers["Age"] = str(int((datetime.utcnow() - cache_item.updated_at).total_seconds()))

        return response
