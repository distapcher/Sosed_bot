from __future__ import annotations

import logging
import secrets
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from .config import Settings, load_settings
from .payments import configure_yookassa, parse_webhook
from .stats import get_summary, get_users, init_db, mark_payment_succeeded

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

    @app.post("/yookassa/webhook")
    async def yookassa_webhook(request: Request) -> JSONResponse:
        if not settings.payment_enabled:
            raise HTTPException(status_code=404, detail="Payments disabled")

        body = await request.body()
        try:
            event, payment_id, telegram_user_id, access_days, _amount = parse_webhook(body)
        except Exception:
            log.exception("Invalid YooKassa webhook payload")
            raise HTTPException(status_code=400, detail="Invalid payload") from None

        if event == "payment.succeeded" and telegram_user_id > 0:
            mark_payment_succeeded(
                settings.stats_db_path,
                payment_id=payment_id,
                telegram_user_id=telegram_user_id,
                access_days=access_days or settings.payment_access_days,
            )
            log.info("Payment succeeded: user=%s payment=%s", telegram_user_id, payment_id)

        return JSONResponse({"status": "ok"})

    return app


def main() -> None:
    load_dotenv()
    settings = load_settings(require_admin_password=True)
    init_db(settings.stats_db_path)
    if settings.payment_enabled and settings.yookassa_shop_id and settings.yookassa_secret_key:
        configure_yookassa(settings)
    app = create_app(settings)
    uvicorn.run(app, host=settings.web_host, port=settings.web_port, log_level="info")


if __name__ == "__main__":
    main()
