from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from sfplatform.config import get_settings
from shared.application.tenant_context import TenantContext, TenantId


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        raw = request.headers.get("X-Tenant-Id")
        tenant_id = int(raw) if raw and raw.isdigit() else get_settings().default_tenant_id
        request.state.tenant_context = TenantContext(tenant_id=TenantId(tenant_id))
        return await call_next(request)


def get_tenant_context(request: Request) -> TenantContext:
    return request.state.tenant_context
