import os
from typing import Any

import requests

from config import MOCK_NS


class CloudflareIntegration:
    def __init__(self) -> None:
        self.mode = os.getenv("CLOUDFLARE_MODE", "mock")
        self.token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_base = os.getenv("CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def create_zone(self, domain: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"zone_id": f"zone_mock_{domain}", "nameservers": list(MOCK_NS), "mode": "mock"}
        payload = {"name": domain, "account": {"id": self.account_id}, "jump_start": False, "type": "full"}
        response = requests.post(f"{self.api_base}/zones", headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()["result"]
        return {
            "zone_id": result.get("id"),
            "domain": result.get("name", domain),
            "nameservers": result.get("name_servers") or [],
            "status": result.get("status"),
            "mode": "real",
        }

    def create_record(self, zone_id: str, record_type: str, name: str, content: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"zone_id": zone_id, "type": record_type, "name": name, "content": content, "mode": "mock"}
        response = requests.post(f"{self.api_base}/zones/{zone_id}/dns_records", headers=self._headers(), json={"type": record_type, "name": name, "content": content, "ttl": 1, "proxied": False}, timeout=30)
        response.raise_for_status()
        return response.json()["result"]

    def zone_status(self, zone_id: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"zone_id": zone_id, "status": "active", "ssl": "active", "mode": "mock"}
        response = requests.get(f"{self.api_base}/zones/{zone_id}", headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()["result"]
