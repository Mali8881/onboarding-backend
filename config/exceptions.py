from __future__ import annotations

from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.i18n import tr


def _first_value(value):
    if isinstance(value, dict):
        for item in value.values():
            extracted = _first_value(item)
            if extracted is not None:
                return extracted
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            extracted = _first_value(item)
            if extracted is not None:
                return extracted
        return None
    return value


def _first_code(value):
    if isinstance(value, dict):
        for item in value.values():
            extracted = _first_code(item)
            if extracted:
                return extracted
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            extracted = _first_code(item)
            if extracted:
                return extracted
        return None
    if hasattr(value, "code"):
        return str(getattr(value, "code"))
    return None


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    request = context.get("request")
    language = getattr(request, "LANGUAGE_CODE", "ru")
    data = response.data
    if isinstance(data, dict) and "code" in data and "detail" in data:
        return response

    code = "error"
    detail = None
    if hasattr(exc, "get_codes"):
        exc_codes = exc.get_codes()
        extracted = _first_code(exc_codes)
        if extracted:
            code = extracted

    first = _first_value(data)
    if first is not None:
        detail = str(first)
    if not detail:
        if response.status_code == 401:
            code = "authentication_required"
            detail = tr("authentication_required", language)
        elif response.status_code == 403:
            code = "permission_denied"
            detail = tr("permission_denied", language)
        elif response.status_code == 400:
            code = "validation_error"
            detail = tr("validation_error", language)
        else:
            detail = tr("error", language)

    payload = {"code": str(code), "detail": str(detail)}
    if isinstance(data, (dict, list)):
        payload["errors"] = data
    response.data = payload
    return response
