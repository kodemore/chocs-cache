import pickle
from datetime import datetime

from chocs import HttpResponse

__all__ = ["format_date_rfc_1123", "parse_etag_value", "dump_response", "load_response"]


def format_date_rfc_1123(value: datetime) -> str:
    iso_1123_format = "%s, %02d %s %04d %02d:%02d:%02d GMT"
    weekday = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[value.weekday()]
    month = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[value.month - 1]

    return iso_1123_format % (weekday, value.day, month, value.year, value.hour, value.minute, value.second)


def parse_etag_value(value: str) -> str:
    value = value.strip()
    if value[0:1] == '"' and value[-1] == '"':
        return value[1:-1]

    if value[0:3] == 'W/"' and value[-1] == '"':
        return value[3:-1]

    return value


def dump_response(response: HttpResponse) -> bytes:
    response.body.seek(0)
    result = pickle.dumps((int(response.status_code), response.body.read(), dict(response.headers)))
    response.body.seek(0)

    return result


def load_response(data: bytes) -> HttpResponse:
    response_data = pickle.loads(data)
    return HttpResponse(status=response_data[0], body=response_data[1], headers=response_data[2])
