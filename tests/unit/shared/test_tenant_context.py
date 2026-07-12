from shared.application.tenant_context import TenantContext, TenantId


def test_tenant_context_carries_tenant_id():
    ctx = TenantContext(tenant_id=TenantId(1))
    assert ctx.tenant_id.value == 1
