import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


FRONTEND_DIST_DIR = Path(settings.BASE_DIR) / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"


def spa_index(request):
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        raise Http404("Frontend build not found. Run `npm run build` in frontend/.")
    return HttpResponse(index_path.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")


def spa_asset(request, asset_path: str):
    candidate = (FRONTEND_ASSETS_DIR / asset_path).resolve()
    try:
        candidate.relative_to(FRONTEND_ASSETS_DIR.resolve())
    except ValueError as exc:
        raise Http404("Invalid asset path.") from exc
    if not candidate.exists() or not candidate.is_file():
        raise Http404("Asset not found.")
    content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
    return FileResponse(open(candidate, "rb"), content_type=content_type)


def spa_vite_icon(request):
    icon_path = FRONTEND_DIST_DIR / "vite.svg"
    if not icon_path.exists():
        raise Http404("Icon not found.")
    return FileResponse(open(icon_path, "rb"), content_type="image/svg+xml")
