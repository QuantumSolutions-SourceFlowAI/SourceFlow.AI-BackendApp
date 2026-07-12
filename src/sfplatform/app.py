from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from contexts.chatbots.interfaces.router import router as chatbots_router
from contexts.inference.interfaces.router import router as chat_router
from contexts.knowledge_ingestion.interfaces.router import router as documents_router
from sfplatform.config import get_settings
from sfplatform.middleware import TenantMiddleware, get_tenant_context
from shared.application.tenant_context import TenantContext
from shared.domain.errors import InvariantViolation, NotFoundError, ValidationError


def create_app() -> FastAPI:
    app = FastAPI(title="SourceFlow.AI API")
    app.add_middleware(TenantMiddleware)

    origins = [o.strip() for o in get_settings().allowed_origins.split(",") if o.strip()]
    if origins:
        # Added AFTER TenantMiddleware so CORS is the outermost layer (handles preflight first).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/health")
    def health(ctx: TenantContext = Depends(get_tenant_context)) -> dict:
        return {"status": "ok", "tenant_id": ctx.tenant_id.value}

    app.include_router(chatbots_router)
    app.include_router(documents_router)
    app.include_router(chat_router)

    @app.exception_handler(InvariantViolation)
    def _conflict(request: Request, exc: InvariantViolation) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    def _unprocessable(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return app


app = create_app()
