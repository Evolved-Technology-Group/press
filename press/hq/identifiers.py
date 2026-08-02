# Copyright (c) 2026, Evolved Technology Group
# See license.txt

from __future__ import annotations

import hashlib


def tenant_record_name(prefix: str, tenant: str, request_id: str) -> str:
	"""Return a short deterministic key scoped to one tenant."""
	value = f"{str(tenant).strip().lower()}:{str(request_id).strip()}"
	digest = hashlib.sha256(value.encode()).hexdigest()
	return f"{prefix}-{digest[:40]}"
