from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request, ClientDisconnect
from backend.config import Config
from utils.logger import get_logger
from fastapi import FastAPI
import contextvars
import time
import uuid

logger = get_logger("api.middlewares")

request_id_ctx = contextvars.ContextVar("request_id", default=None)


def mask_sensitive(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    return {
        k: "***" if k.lower() in Config.SENSITIVE_KEYS else v
        for k, v in data.items()
    }


def setup_middlewares(app: FastAPI):
    logger.info("Setting up API middlewares...")

    app.add_middleware(GZipMiddleware, minimum_size=Config.GZIP_MIN_SIZE)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def global_http_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        token = request_id_ctx.set(request_id)

        is_health_check = request.url.path == "/health"
        start_time = time.perf_counter()

        if not is_health_check:
            logger.info(
                "Incoming Request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            )

        try:
            response = await call_next(request)

            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"

            hostname = request.url.hostname or ""
            if "localhost" not in hostname and "127.0.0.1" not in hostname:
                response.headers["Strict-Transport-Security"] = f"max-age={Config.HSTS_MAX_AGE}; includeSubDomains"

            process_time = round(time.perf_counter() - start_time, 4)
            process_time_ms = process_time * 1000

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"
            response.headers["Server-Timing"] = f"app;dur={process_time_ms}"

            if not is_health_check:
                log_extra = {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time
                }

                if response.status_code >= 500:
                    logger.error("Request Server Error", extra=log_extra)
                elif response.status_code >= 400:
                    logger.warning("Request Client Error", extra=log_extra)
                else:
                    logger.info("Request Completed", extra=log_extra)

            return response

        except ClientDisconnect:
            process_time = round(time.perf_counter() - start_time, 4)
            if not is_health_check:
                logger.warning(
                    "Client Disconnected",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "process_time": process_time
                    }
                )
            raise

        except Exception as e:
            process_time = round(time.perf_counter() - start_time, 4)
            logger.error(
                "Request Failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time": process_time
                },
                exc_info=True
            )
            raise

        finally:
            request_id_ctx.reset(token)

    logger.info("API middlewares registered successfully.")
