"""RTF OMEGA-BLACK v6.0 — TECHINT modules."""
from __future__ import annotations

import re
import requests
from framework.modules.base import BaseModule, ModuleResult


class TechStackDeepDiveModule(BaseModule):
    def info(self): return {"name":"tech_stack_deep_dive","category":"techint","description":"Header/js tech stack fingerprint"}
    def _declare_options(self): self._register_option("target","Domain or URL")
    async def run(self)->ModuleResult:
        url=self.get("target")
        if not url.startswith("http"): url="https://"+url
        try:
            r=requests.get(url,timeout=20)
            libs=re.findall(r"([\w\-]+(?:react|vue|angular|jquery|bootstrap)[\w\-.]*)",r.text,re.I)
            return ModuleResult(success=True, output={"status":r.status_code,"headers":dict(r.headers),"libraries":sorted(set(libs))[:50]})
        except Exception as exc:
            return ModuleResult(success=False,error=str(exc))


class SSLCertificateIntelModule(BaseModule):
    def info(self): return {"name":"ssl_certificate_intel","category":"techint","description":"crt.sh certificate intelligence"}
    def _declare_options(self): self._register_option("target","Domain")
    async def run(self)->ModuleResult:
        domain=self.get("target")
        try:
            r=requests.get("https://crt.sh/",params={"q":domain,"output":"json"},timeout=20)
            return ModuleResult(success=True, output=r.json()[:50])
        except Exception as exc:
            return ModuleResult(success=False,error=str(exc))
