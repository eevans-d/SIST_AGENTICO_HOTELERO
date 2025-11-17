# Tenant Context Propagation Manager

class TenantContextManager:
    def __init__(self):
        self.tenant_context = None

    def set_tenant_context(self, tenant_id):
        self.tenant_context = tenant_id
        # Additional logic for setting context

    def get_tenant_context(self):
        return self.tenant_context

    def clear_tenant_context(self):
        self.tenant_context = None
        # Additional logic for clearing context

# Example usage:
# manager = TenantContextManager()
# manager.set_tenant_context('tenant123')
# print(manager.get_tenant_context())
# manager.clear_tenant_context()