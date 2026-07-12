from dataclasses import dataclass

from shared.domain.identity import IntId


class TenantId(IntId):
    pass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: TenantId
