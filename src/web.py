from __future__ import annotations

import hashlib
import logging
import secrets
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import Settings, load_settings
from .promo import PROMO_DESCRIPTION, PROMO_TITLE, bot_telegram_url, promo_image_url, promo_page_url
from .stats import get_summary, get_users, init_db

security = HTTPBasic(auto_error=False)
log = logging.getLogger("sosed.web")
_APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_APP_DIR / "templates"))
_STATIC_DIR = _APP_DIR / "static"

SESSION_KEY = "sosed_dashboard_user"


def _session_secret(settings: Settings) -> str:
    raw = (settings.web_session_secret or settings.admin_password).encode()
    return hashlib.sha256(raw).hexdigest()


def _credentials_ok(settings: Settings, username: str, password: str) -> bool:
    return secrets.compare_digest(username, settings.admin_user) and secrets.compare_digest(
        password, settings.admin_password
    )


def _basic_ok(settings: Settings, credentials: HTTPBasicCredentials | None) -> bool:
    if credentials is None:
        return False
    return _credentials_ok(settings, credentials.username, credentials.password)


def _session_ok(request: Request, settings: Settings) -> bool:
    user = request.session.get(SESSION_KEY)
    return isinstance(user, str) and secrets.compare_digest(user, settings.admin_user)


def _public_base_url(request: Request, settings: Settings) -> str:
    if settings.public_promo_base_url:
        return settings.public_promo_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Sosed Dashboard", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=_session_secret(settings), https_only=False)
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/login", response_class=HTMLResponse, response_model=None)
    def login_page(request: Request) -> HTMLResponse | RedirectResponse:
        if _session_ok(request, settings):
            return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse(request, "login.html", {"error": None})

    @app.post("/login", response_model=None)
    async def login_submit(request: Request) -> RedirectResponse | HTMLResponse:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        if _credentials_ok(settings, username, password):
            request.session[SESSION_KEY] = settings.admin_user
            return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Неверный логин или пароль"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    @app.get("/logout")
    def logout(request: Request) -> RedirectResponse:
        request.session.clear()
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/promo", response_class=HTMLResponse, response_model=None)
    def promo_landing(request: Request) -> HTMLResponse:
        """Публичная страница с Open Graph — для постов в каналах (не голый t.me)."""
        base = _public_base_url(request, settings)
        page_url = promo_page_url(base)
        return templates.TemplateResponse(
            request,
            "promo.html",
            {
                "title": PROMO_TITLE,
                "description": PROMO_DESCRIPTION,
                "page_url": page_url,
                "image_url": promo_image_url(base),
                "bot_url": bot_telegram_url(settings.bot_username),
            },
        )

    @app.get("/go")
    def promo_redirect() -> RedirectResponse:
        return RedirectResponse(bot_telegram_url(settings.bot_username), status_code=302)

    @app.get("/", response_class=HTMLResponse, response_model=None)
    def dashboard(
        request: Request,
        credentials: HTTPBasicCredentials | None = Depends(security),
    ) -> HTMLResponse | RedirectResponse:
        if not (_session_ok(request, settings) or _basic_ok(settings, credentials)):
            return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
        summary = get_summary(settings.stats_db_path)
        users = get_users(settings.stats_db_path)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "summary": summary,
                "users": users,
                "input_price": settings.cost_input_per_1m_usd,
                "output_price": settings.cost_output_per_1m_usd,
            },
        )

    return app


def main() -> None:
    load_dotenv()
    settings = load_settings()
    if not settings.admin_password:
        raise ValueError("Missing ADMIN_PASSWORD in environment (required for web dashboard)")
    init_db(settings.stats_db_path)
    app = create_app(settings)
    uvicorn.run(app, host=settings.web_host, port=settings.web_port, log_level="info")


if __name__ == "__main__":
    main()
