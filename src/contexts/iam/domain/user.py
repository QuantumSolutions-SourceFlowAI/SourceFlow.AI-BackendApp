from dataclasses import dataclass

from contexts.iam.domain.value_objects import Email, UserId
from shared.application.tenant_context import TenantId


@dataclass
class User:
    id: UserId | None
    tenant_id: TenantId
    email: Email
    password_hash: str
