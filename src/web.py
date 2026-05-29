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
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import Settings, load_settings
from .stats import get_summary, get_users, init_db

security = HTTPBasic(auto_error=False)
log = logging.getLogger("sosed.web")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

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


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Sosed Dashboard", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=_session_secret(settings), https_only=False)

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
