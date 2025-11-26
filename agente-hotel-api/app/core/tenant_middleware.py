from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from .tenant_context import set_tenant_id, reset_tenant_id

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant ID from request and set it in the context.
    Checks 'X-Tenant-ID' header first, then 'tenant_id' query parameter.
    """
    def __init__(self, app, default_tenant: str = "default"):
        super().__init__(app)
        self.default_tenant = default_tenant

    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # Fallback to query param if needed
        if not tenant_id:
             tenant_id = request.query_params.get("tenant_id")
        
        # Fallback to default tenant
        if not tenant_id:
            tenant_id = self.default_tenant
        
        token = set_tenant_id(tenant_id)
        try:
            response = await call_next(request)
            return response
        finally:
            reset_tenant_id(token)
