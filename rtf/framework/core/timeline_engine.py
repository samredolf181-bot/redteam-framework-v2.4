"""RTF OMEGA-BLACK v6.0 — Timeline Engine."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from framework.db.database import db


class TimelineEngine:
    def add_event(self, workspace_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        eid = event.get("id") or str(uuid4())
        db.execute(
            """INSERT INTO timeline_events (id,workspace_id,timestamp,event_type,description,source,entity_value,entity_type,confidence,metadata,tags,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eid, workspace_id, event.get("timestamp", datetime.utcnow().isoformat()), event.get("event_type", "note"),
                event.get("description", ""), event.get("source", "manual"), event.get("entity_value", ""),
                event.get("entity_type", ""), float(event.get("confidence", 0.5)), json.dumps(event.get("metadata", {})),
                json.dumps(event.get("tags", [])), datetime.utcnow().isoformat(),
            ),
        )
        return self.get_event(eid) or {"id": eid}

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        row = db.fetchone("SELECT * FROM timeline_events WHERE id=?", (event_id,))
        if not row:
            return None
        row["metadata"] = json.loads(row.get("metadata") or "{}")
        row["tags"] = json.loads(row.get("tags") or "[]")
        return row

    def get_timeline(self, workspace_id: Optional[str] = None, entity: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = db.fetchall(
            "SELECT * FROM timeline_events WHERE (? IS NULL OR workspace_id=?) AND (? IS NULL OR entity_value=?) ORDER BY timestamp",
            (workspace_id, workspace_id, entity, entity),
        )
        for row in rows:
            row["metadata"] = json.loads(row.get("metadata") or "{}")
            row["tags"] = json.loads(row.get("tags") or "[]")
        return rows

    def export_csv(self, workspace_id: str) -> str:
        rows = self.get_timeline(workspace_id=workspace_id)
        sio = io.StringIO()
        fields = ["id", "timestamp", "event_type", "description", "source", "entity_value", "entity_type", "confidence"]
        writer = csv.DictWriter(sio, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({f: row.get(f) for f in fields})
        return sio.getvalue()

    def export_json(self, workspace_id: str) -> Dict[str, Any]:
        return {"workspace_id": workspace_id, "events": self.get_timeline(workspace_id=workspace_id)}


_timeline_engine = TimelineEngine()


def get_timeline_engine() -> TimelineEngine:
    return _timeline_engine
