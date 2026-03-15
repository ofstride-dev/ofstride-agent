from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class TenantConfig:
    name: str
    system_prompt_path: Path
    knowledge_path: Path | None = None
    policy_notes: str | None = None


def load_tenants(base_dir: Path) -> Dict[str, TenantConfig]:
    raw = os.getenv("OFSTRIDE_TENANTS_JSON")
    tenants: Dict[str, TenantConfig] = {}
    if raw:
        try:
            data = json.loads(raw)
            for key, value in data.items():
                tenants[key] = TenantConfig(
                    name=value.get("name", key),
                    system_prompt_path=Path(value.get("system_prompt_path")),
                    knowledge_path=Path(value["knowledge_path"]) if value.get("knowledge_path") else None,
                    policy_notes=value.get("policy_notes"),
                )
        except Exception:
            tenants = {}

    if not tenants:
        tenants["default"] = TenantConfig(
            name="default",
            system_prompt_path=base_dir / "system_prompt.txt",
            knowledge_path=base_dir / "knowledge" / "ofstride_services.txt",
            policy_notes=None,
        )
    return tenants


def resolve_tenant(host: str, tenants: Dict[str, TenantConfig]) -> TenantConfig:
    hostname = host.split(":")[0].strip().lower()
    if not hostname:
        return tenants["default"]
    subdomain = hostname.split(".")[0]
    return tenants.get(subdomain) or tenants.get(hostname) or tenants["default"]
