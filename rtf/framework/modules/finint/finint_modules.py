"""RTF OMEGA-BLACK v6.0 — FININT modules."""
from __future__ import annotations

import requests
from framework.modules.base import BaseModule, ModuleResult, Severity


class _FinintBase(BaseModule):
    def _declare_options(self) -> None:
        self._register_option("target", "Target value")

    def info(self):
        return {"name": self.__class__.__name__.lower(), "category": "finint", "description": self.__doc__ or ""}


class CryptoWalletIntelModule(_FinintBase):
    """Inspect BTC wallet activity via Blockstream."""
    async def run(self) -> ModuleResult:
        addr = self.get("target")
        try:
            r = requests.get(f"https://blockstream.info/api/address/{addr}", timeout=20)
            r.raise_for_status()
            data = r.json()
            finding = self.make_finding("Wallet activity observed", addr, Severity.INFO, evidence=data)
            return ModuleResult(success=True, output=data, findings=[finding])
        except Exception as exc:
            return ModuleResult(success=False, error=str(exc))


class CompanyFinancialModule(_FinintBase):
    """Lookup company records from OpenCorporates."""
    async def run(self) -> ModuleResult:
        q = self.get("target")
        try:
            r = requests.get("https://api.opencorporates.com/v0.4/companies/search", params={"q": q}, timeout=20)
            r.raise_for_status()
            data = r.json()
            return ModuleResult(success=True, output=data)
        except Exception as exc:
            return ModuleResult(success=False, error=str(exc))


class SanctionsScreeningModule(_FinintBase):
    """Screen a name against OpenSanctions."""
    async def run(self) -> ModuleResult:
        name = self.get("target")
        try:
            r = requests.get("https://api.opensanctions.org/match/default", params={"q": name}, timeout=20)
            r.raise_for_status()
            data = r.json()
            return ModuleResult(success=True, output=data)
        except Exception as exc:
            return ModuleResult(success=False, error=str(exc))
