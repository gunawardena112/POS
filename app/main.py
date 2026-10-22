import logging

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import DomainError
from app.routers import loyalty_customers, orders, products, sales

logger = logging.getLogger("pos")
app = FastAPI(title="POS Orders & Loyalty API", version="1.0.0")


def error_body(code: str, message: str, details=None) -> dict:
    body = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in e["loc"] if p not in ("body", "query")), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content=error_body("validation_error", "Request validation failed", details))


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content=error_body("http_error", str(exc.detail)))


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception):
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content=error_body("internal_error", "Internal server error"))


api = APIRouter(prefix="/api/v1")
for r in (products.router, orders.router, loyalty_customers.router, sales.router):
    api.include_router(r)
app.include_router(api)
