from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin

from apps.common.i18n import pick_language, tr


class APILanguageMiddleware(MiddlewareMixin):
    """
    API language resolver.
    Priority: ?lang=ru|en|kg -> Accept-Language -> default ru.
    """

    def process_request(self, request: HttpRequest):
        language = pick_language(
            query_lang=request.GET.get("lang"),
            accept_language=request.headers.get("Accept-Language"),
        )
        request.LANGUAGE_CODE = language
        translation.activate(language)


class APIErrorEnvelopeMiddleware(MiddlewareMixin):
    """
    Ensures API error payload always contains stable fields:
    {
      "code": "...",
      "detail": "localized text",
      "errors": {...}  # optional, for field-level validation details
    }
    """

    @staticmethod
    def _first_code(value):
        if isinstance(value, dict):
            for item in value.values():
                extracted = APIErrorEnvelopeMiddleware._first_code(item)
                if extracted:
                    return extracted
            return None
        if isinstance(value, (list, tuple)):
            for item in value:
                extracted = APIErrorEnvelopeMiddleware._first_code(item)
                if extracted:
                    return extracted
            return None
        if hasattr(value, "code"):
            return str(getattr(value, "code"))
        return None

    @staticmethod
    def _first_message(value):
        if isinstance(value, dict):
            if "detail" in value and isinstance(value["detail"], (str, bytes)):
                return str(value["detail"])
            for item in value.values():
                extracted = APIErrorEnvelopeMiddleware._first_message(item)
                if extracted:
                    return extracted
            return None
        if isinstance(value, (list, tuple)):
            for item in value:
                extracted = APIErrorEnvelopeMiddleware._first_message(item)
                if extracted:
                    return extracted
            return None
        if value is None:
            return None
        return str(value)

    def process_response(self, request: HttpRequest, response: HttpResponse):
        if not request.path.startswith("/api/"):
            return response
        if response.status_code < 400:
            return response
        if not hasattr(response, "data"):
            return response

        data = response.data
        if isinstance(data, dict) and "code" in data and "detail" in data:
            return response

        language = getattr(request, "LANGUAGE_CODE", "ru")
        code = self._first_code(data) or "error"
        detail = self._first_message(data)
        if not detail:
            if response.status_code == 401:
                detail = tr("authentication_required", language)
                code = code if code != "error" else "authentication_required"
            elif response.status_code == 403:
                detail = tr("permission_denied", language)
                code = code if code != "error" else "permission_denied"
            elif response.status_code == 400:
                detail = tr("validation_error", language)
                code = code if code != "error" else "validation_error"
            else:
                detail = tr("error", language)

        payload = {"code": str(code), "detail": str(detail)}
        if isinstance(data, (dict, list)):
            payload["errors"] = data
        response.data = payload
        return response
