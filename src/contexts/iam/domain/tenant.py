from dataclasses import dataclass

from contexts.iam.domain.enums import TenantStatus
from shared.application.tenant_context import TenantId


@dataclass
class Tenant:
    id: TenantId | None
    business_name: str
    status: TenantStatus = TenantStatus.ACTIVE

    def activate(self) -> None:
        self.status = TenantStatus.ACTIVE

    def suspend(self) -> None:
        self.status = TenantStatus.SUSPENDED
