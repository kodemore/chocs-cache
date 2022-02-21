from datetime import datetime

import pytest
from chocs import HttpResponse, HttpStatus, HttpRequest, HttpMethod

from chocs_middleware.cache.http_support import dump_response, load_response, format_date_rfc_1123, parse_etag_value


@pytest.mark.parametrize("given,expected", [
    [datetime(2000, 12, 18, 10, 1, 1), "Mon, 18 Dec 2000 10:01:01 GMT"],
    [datetime(2000, 12, 19, 10, 1, 1), "Tue, 19 Dec 2000 10:01:01 GMT"],
    [datetime(2000, 12, 20, 10, 1, 1), "Wed, 20 Dec 2000 10:01:01 GMT"],
    [datetime(2000, 12, 21, 10, 1, 1), "Thu, 21 Dec 2000 10:01:01 GMT"],
    [datetime(2000, 12, 22, 10, 1, 1), "Fri, 22 Dec 2000 10:01:01 GMT"],
    [datetime(2000, 12, 23, 10, 1, 1), "Sat, 23 Dec 2000 10:01:01 GMT"],
    [datetime(2000, 12, 24, 10, 1, 1), "Sun, 24 Dec 2000 10:01:01 GMT"],
    [datetime(2000, 1, 24, 10, 1, 1), "Mon, 24 Jan 2000 10:01:01 GMT"],
    [datetime(2000, 2, 24, 10, 1, 1), "Thu, 24 Feb 2000 10:01:01 GMT"],
    [datetime(2000, 3, 24, 10, 1, 1), "Fri, 24 Mar 2000 10:01:01 GMT"],
    [datetime(2000, 4, 24, 10, 1, 1), "Mon, 24 Apr 2000 10:01:01 GMT"],
    [datetime(2000, 5, 24, 10, 1, 1), "Wed, 24 May 2000 10:01:01 GMT"],
    [datetime(2000, 6, 24, 10, 1, 1), "Sat, 24 Jun 2000 10:01:01 GMT"],
    [datetime(2000, 7, 24, 10, 1, 1), "Mon, 24 Jul 2000 10:01:01 GMT"],
    [datetime(2000, 8, 24, 10, 1, 1), "Thu, 24 Aug 2000 10:01:01 GMT"],
    [datetime(2000, 9, 24, 10, 1, 1), "Sun, 24 Sep 2000 10:01:01 GMT"],
    [datetime(2000, 10, 24, 10, 1, 1), "Tue, 24 Oct 2000 10:01:01 GMT"],
    [datetime(2000, 11, 24, 10, 1, 1), "Fri, 24 Nov 2000 10:01:01 GMT"],

])
def test_format_date_rfc_1123(given: datetime, expected: str) -> None:

    # then
    assert format_date_rfc_1123(given) == expected


@pytest.mark.parametrize("given, expected", [
    ['"d"', "d"],
    ['W/"d"', "d"],
])
def test_parse_etag_value(given: str, expected: str) -> None:
    assert parse_etag_value(given) == expected


def test_can_dump_and_load_response() -> None:
    # given
    response = HttpResponse("test", status=HttpStatus.OK, headers={"test": "ok"})

    # when
    d_response = dump_response(response)
    l_response = load_response(d_response)

    # then
    assert response == l_response
