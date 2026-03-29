from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from shutil import which
from typing import Any, Dict, List

from framework.modules.loader import module_loader
from framework.registry.tool_registry import tool_registry
from framework.omega.engine_registry import omega_registry


@dataclass
class DiagnosticCheck:
    name: str
    status: str
    detail: str

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


class OmegaDoctor:
    def diagnose(self) -> Dict[str, Any]:
        module_loader.load_all()
        tool_registry.refresh()
        checks: List[DiagnosticCheck] = []
        checks.append(self._check_python_module("fastapi"))
        checks.append(self._check_python_module("uvicorn"))
        checks.append(self._check_binary("neo4j", "Graph backend CLI availability"))
        checks.append(self._check_binary("exiftool", "Metadata extraction support"))
        checks.append(self._check_loader())
        checks.append(self._check_tool_registry())
        checks.append(self._check_omega_engines())
        overall = "healthy" if all(c.status == "ok" for c in checks) else "degraded"
        return {
            "status": overall,
            "checks": [c.to_dict() for c in checks],
            "summary": {
                "ok": sum(1 for c in checks if c.status == "ok"),
                "warn": sum(1 for c in checks if c.status == "warn"),
                "fail": sum(1 for c in checks if c.status == "fail"),
            },
        }

    def validate(self) -> Dict[str, Any]:
        module_loader.load_all()
        manifest = omega_registry.manifest()
        integration = manifest["loader_integration"]
        return {
            "status": "ok",
            "engine_count": len(manifest["engines"]),
            "workflow_count": sum(len(engine["workflows"]) for engine in manifest["engines"]),
            "module_count": integration["module_count"],
            "graph_backend": manifest["graph_schema"]["backend"],
            "self_healing_commands": manifest["self_healing_commands"],
        }

    def repair_plan(self) -> Dict[str, Any]:
        diagnosis = self.diagnose()
        actions: List[Dict[str, str]] = []
        for check in diagnosis["checks"]:
            if check["status"] == "ok":
                continue
            if check["name"] == "neo4j":
                actions.append({"component": "neo4j", "action": "Install/start Neo4j or configure remote bolt endpoint."})
            elif check["name"] == "exiftool":
                actions.append({"component": "exiftool", "action": "Install exiftool for media/document intelligence enrichment."})
            elif check["name"] == "tool_registry":
                actions.append({"component": "tool_registry", "action": "Run `rtf tools summary` and install missing priority tools."})
            else:
                actions.append({"component": check["name"], "action": f"Review {check['detail']}"})
        return {"status": "ok", "actions": actions, "diagnosis": diagnosis}

    def fix(self) -> Dict[str, Any]:
        plan = self.repair_plan()
        plan["status"] = "planned"
        plan["mode"] = "non-destructive"
        return plan

    def repair(self) -> Dict[str, Any]:
        return self.fix()

    def _check_binary(self, binary: str, detail: str) -> DiagnosticCheck:
        return DiagnosticCheck(binary, "ok" if which(binary) else "warn", detail)

    def _check_python_module(self, module: str) -> DiagnosticCheck:
        return DiagnosticCheck(module, "ok" if importlib.util.find_spec(module) else "warn", f"Python dependency `{module}`")

    def _check_loader(self) -> DiagnosticCheck:
        modules = module_loader.list_modules()
        return DiagnosticCheck("module_loader", "ok" if modules else "fail", f"Registered modules: {len(modules)}")

    def _check_tool_registry(self) -> DiagnosticCheck:
        summary = tool_registry.summary()
        installed = int(summary.get("installed", 0))
        total = int(summary.get("total", 0))
        status = "ok" if installed else "warn"
        return DiagnosticCheck("tool_registry", status, f"Installed tools: {installed}/{total}")

    def _check_omega_engines(self) -> DiagnosticCheck:
        engine_count = len(omega_registry.list_engines())
        return DiagnosticCheck("omega_engines", "ok" if engine_count >= 12 else "fail", f"Engine count: {engine_count}")


omega_doctor = OmegaDoctor()
