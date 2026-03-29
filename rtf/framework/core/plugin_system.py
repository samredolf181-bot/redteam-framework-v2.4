"""RTF OMEGA-BLACK v6.0 — Plugin System."""
from __future__ import annotations

import importlib.util
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from framework.db.database import db


@dataclass
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    type: str
    entry_point: str


class PluginRegistry:
    def __init__(self, plugins_dir: str = "plugins") -> None:
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def scan_plugins(self) -> List[Dict[str, Any]]:
        discovered: List[Dict[str, Any]] = []
        for manifest in self.plugins_dir.glob("*/manifest.json"):
            payload = json.loads(manifest.read_text())
            payload["id"] = payload.get("plugin_id", manifest.parent.name)
            discovered.append(payload)
            db.execute(
                "INSERT OR IGNORE INTO plugins (id,name,version,type,description,enabled,config) VALUES (?,?,?,?,?,?,?)",
                (payload["id"], payload.get("name", payload["id"]), payload.get("version", "0.0.0"), payload.get("type", "module"), payload.get("description", ""), 1, "{}"),
            )
        return discovered

    def list_plugins(self) -> List[Dict[str, Any]]:
        return db.fetchall("SELECT * FROM plugins ORDER BY installed_at DESC")

    def install_plugin(self, source: str) -> Dict[str, Any]:
        src = Path(source)
        if not src.exists():
            raise FileNotFoundError(source)
        dest = self.plugins_dir / src.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        self.scan_plugins()
        return {"installed": src.name}

    def enable(self, plugin_id: str, enabled: bool) -> None:
        db.execute("UPDATE plugins SET enabled=? WHERE id=?", (1 if enabled else 0, plugin_id))

    def remove(self, plugin_id: str) -> None:
        shutil.rmtree(self.plugins_dir / plugin_id, ignore_errors=True)
        db.execute("DELETE FROM plugins WHERE id=?", (plugin_id,))

    def load_plugin(self, plugin_id: str) -> Optional[Any]:
        manifest_path = self.plugins_dir / plugin_id / "manifest.json"
        if not manifest_path.exists():
            return None
        manifest = json.loads(manifest_path.read_text())
        entry = manifest.get("entry_point", "plugin.py")
        target = self.plugins_dir / plugin_id / entry
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_id}", target)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


_plugin_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    return _plugin_registry
