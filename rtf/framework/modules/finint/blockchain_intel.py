"""RTF OMEGA-BLACK v6.0 — Blockchain Intelligence modules."""
from __future__ import annotations

import requests
from framework.modules.base import BaseModule, ModuleResult


class BitcoinAddressIntelModule(BaseModule):
    def info(self):
        return {"name": "bitcoin_address_intel", "category": "finint", "description": "Blockstream BTC intelligence"}
    def _declare_options(self) -> None:
        self._register_option("target", "BTC address")
    async def run(self) -> ModuleResult:
        addr = self.get("target")
        try:
            data = requests.get(f"https://blockstream.info/api/address/{addr}", timeout=20).json()
            txs = requests.get(f"https://blockstream.info/api/address/{addr}/txs", timeout=20).json()
            return ModuleResult(success=True, output={"address": data, "txs": txs[:25]})
        except Exception as exc:
            return ModuleResult(success=False, error=str(exc))
