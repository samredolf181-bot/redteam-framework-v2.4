"""RTF OMEGA-BLACK v6.0 — Workspace Manager."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from framework.db.database import db


@dataclass
class Workspace:
    id: str
    name: str
    client_name: str
    case_number: str
    status: str
    classification: str
    description: str
    tags: List[str]
    created_at: str
    updated_at: str
    closed_at: Optional[str] = None


class WorkspaceManager:
    """CRUD manager for workspace-scoped investigations."""

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        wid = payload.get("id") or str(uuid4())
        db.execute(
            """
            INSERT INTO workspaces (id,name,client_name,case_number,status,classification,description,tags,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                wid,
                payload.get("name", "Untitled Workspace"),
                payload.get("client_name", ""),
                payload.get("case_number", ""),
                payload.get("status", "active"),
                payload.get("classification", "CONFIDENTIAL"),
                payload.get("description", ""),
                json.dumps(payload.get("tags", [])),
                now,
                now,
            ),
        )
        return self.get(wid) or {"id": wid}

    def get(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        row = db.fetchone("SELECT * FROM workspaces WHERE id=?", (workspace_id,))
        if not row:
            return None
        row["tags"] = json.loads(row.get("tags") or "[]")
        return row

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            rows = db.fetchall("SELECT * FROM workspaces WHERE status=? ORDER BY updated_at DESC", (status,))
        else:
            rows = db.fetchall("SELECT * FROM workspaces ORDER BY updated_at DESC")
        for row in rows:
            row["tags"] = json.loads(row.get("tags") or "[]")
        return rows

    def update(self, workspace_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get(workspace_id)
        if not existing:
            return None
        merged = {**existing, **patch}
        db.execute(
            """
            UPDATE workspaces SET name=?,client_name=?,case_number=?,status=?,classification=?,description=?,tags=?,updated_at=?
            WHERE id=?
            """,
            (
                merged.get("name"),
                merged.get("client_name", ""),
                merged.get("case_number", ""),
                merged.get("status", "active"),
                merged.get("classification", "CONFIDENTIAL"),
                merged.get("description", ""),
                json.dumps(merged.get("tags", [])),
                datetime.utcnow().isoformat(),
                workspace_id,
            ),
        )
        return self.get(workspace_id)

    def archive(self, workspace_id: str) -> bool:
        cur = db.execute(
            "UPDATE workspaces SET status='archived',closed_at=?,updated_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), workspace_id),
        )
        return cur.rowcount > 0

    def export_zip(self, workspace_id: str) -> bytes:
        workspace = self.get(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")

        findings = db.fetchall("SELECT * FROM findings WHERE workspace_id=? ORDER BY created_at DESC", (workspace_id,))
        graph_nodes = db.fetchall("SELECT * FROM graph_nodes WHERE operation_id=?", (workspace_id,))
        graph_edges = db.fetchall("SELECT * FROM graph_edges WHERE operation_id=?", (workspace_id,))
        evidence = db.fetchall("SELECT * FROM evidence WHERE workspace_id=?", (workspace_id,))
        timelines = db.fetchall("SELECT * FROM timeline_events WHERE workspace_id=? ORDER BY timestamp", (workspace_id,))
        dossiers = db.fetchall("SELECT * FROM dossiers WHERE workspace_id=?", (workspace_id,))

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("workspace.json", json.dumps(workspace, indent=2))
            zf.writestr("findings.json", json.dumps(findings, indent=2, default=str))
            zf.writestr("graph_nodes.json", json.dumps(graph_nodes, indent=2, default=str))
            zf.writestr("graph_edges.json", json.dumps(graph_edges, indent=2, default=str))
            zf.writestr("evidence.json", json.dumps(evidence, indent=2, default=str))
            zf.writestr("dossiers.json", json.dumps(dossiers, indent=2, default=str))
            sio = io.StringIO()
            writer = csv.DictWriter(sio, fieldnames=["timestamp", "event_type", "description", "source", "entity_value", "entity_type", "confidence"])
            writer.writeheader()
            for event in timelines:
                writer.writerow({k: event.get(k) for k in writer.fieldnames})
            zf.writestr("timeline.csv", sio.getvalue())
            for ev in evidence:
                fp = ev.get("file_path")
                if fp and Path(fp).exists():
                    zf.write(fp, arcname=f"evidence/{Path(fp).name}")
        return buf.getvalue()


_manager = WorkspaceManager()


def get_workspace_manager() -> WorkspaceManager:
    return _manager
