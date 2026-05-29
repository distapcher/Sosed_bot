from __future__ import annotations

import logging
import secrets
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from .config import Settings, load_settings
from .stats import get_summary, get_users, init_db

security = HTTPBasic()
log = logging.getLogger("sosed.web")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _auth(settings: Settings, credentials: HTTPBasicCredentials = Depends(security)) -> None:
    user_ok = secrets.compare_digest(credentials.username, settings.admin_user)
    pass_ok = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Sosed Dashboard", docs_url=None, redoc_url=None)

    def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> None:
        _auth(settings, credentials)

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
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
    settings = load_settings(require_admin_password=True)
    init_db(settings.stats_db_path)
    app = create_app(settings)
    uvicorn.run(app, host=settings.web_host, port=settings.web_port, log_level="info")


if __name__ == "__main__":
    main()
