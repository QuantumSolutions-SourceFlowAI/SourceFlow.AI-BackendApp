from contexts.iam.domain.enums import TenantStatus
from contexts.iam.domain.tenant import Tenant
from shared.application.tenant_context import TenantId


def _tenant():
    return Tenant(id=TenantId(1), business_name="PyME SAC", status=TenantStatus.ACTIVE)


def test_suspend_sets_status():
    t = _tenant()
    t.suspend()
    assert t.status is TenantStatus.SUSPENDED


def test_activate_sets_status():
    t = _tenant()
    t.suspend()
    t.activate()
    assert t.status is TenantStatus.ACTIVE
