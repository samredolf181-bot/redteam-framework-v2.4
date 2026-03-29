"""RTF OMEGA-BLACK v6.0 — Dossier Engine."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, select_autoescape

from framework.db.database import db


class DossierEngine:
    def __init__(self, template_dir: str = "templates/dossiers", output_dir: str = "data/dossiers") -> None:
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(str(self.template_dir)), autoescape=select_autoescape())

    def _ctx(self, workspace_id: str) -> Dict[str, Any]:
        return {
            "workspace": db.fetchone("SELECT * FROM workspaces WHERE id=?", (workspace_id,)) or {},
            "findings": db.fetchall("SELECT * FROM findings WHERE workspace_id=? ORDER BY created_at DESC", (workspace_id,)),
            "events": db.fetchall("SELECT * FROM timeline_events WHERE workspace_id=? ORDER BY timestamp", (workspace_id,)),
            "entities": db.fetchall("SELECT * FROM graph_nodes WHERE operation_id=? ORDER BY last_seen DESC", (workspace_id,)),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def generate(self, workspace_id: str, dossier_type: str, title: str, fmt: str = "html", classification: str = "CONFIDENTIAL") -> Dict[str, Any]:
        template_name = {
            "personal": "personal_subject.html",
            "corporate": "corporate.html",
            "footprint": "digital_footprint_report.html",
            "brief": "intelligence_brief.html",
        }.get(dossier_type, "intelligence_brief.html")
        html = self.env.get_template(template_name).render(**self._ctx(workspace_id), title=title, classification=classification)
        did = str(uuid4())
        suffix = "html" if fmt == "html" else "md"
        out = self.output_dir / f"{did}.{suffix}"
        out.write_text(html, encoding="utf-8")
        db.execute(
            "INSERT INTO dossiers (id,workspace_id,type,title,classification,status,format,file_path,file_size,generated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (did, workspace_id, dossier_type, title, classification, "final", fmt, str(out), out.stat().st_size, datetime.utcnow().isoformat()),
        )
        return {"id": did, "file_path": str(out), "format": fmt}


_dossier_engine = DossierEngine()


def get_dossier_engine() -> DossierEngine:
    return _dossier_engine
