from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class AuditEvent:
    action: str
    actor: Any = None
    object_type: str = ""
    object_id: str = ""
    level: str = "info"
    category: str = "system"
    ip_address: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
