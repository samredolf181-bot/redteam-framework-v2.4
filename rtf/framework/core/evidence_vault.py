"""RTF OMEGA-BLACK v6.0 — Evidence Vault."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

from framework.db.database import db


@dataclass
class EvidenceItem:
    id: str
    workspace_id: str
    title: str
    description: str
    type: str
    file_path: str
    original_url: str
    md5_hash: str
    sha256_hash: str
    collection_timestamp: str
    collector_name: str


class EvidenceVault:
    def __init__(self, root: str = "data/evidence") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _hash_file(self, path: Path) -> Dict[str, str]:
        md5 = hashlib.md5()
        sha = hashlib.sha256()
        with path.open("rb") as fh:
            while chunk := fh.read(8192):
                md5.update(chunk)
                sha.update(chunk)
        return {"md5": md5.hexdigest(), "sha256": sha.hexdigest()}

    def _add_chain(self, evidence_id: str, event_type: str, actor: str, notes: str = "", verified: Optional[bool] = None) -> None:
        db.execute(
            "INSERT INTO custody_chain (id,evidence_id,event_type,actor,timestamp,notes,hash_verified) VALUES (?,?,?,?,?,?,?)",
            (str(uuid4()), evidence_id, event_type, actor, datetime.utcnow().isoformat(), notes, None if verified is None else int(verified)),
        )

    def add_file(self, workspace_id: str, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(file_path)
        eid = str(uuid4())
        dst_dir = self.root / workspace_id / eid
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        shutil.copy2(src, dst)
        hashes = self._hash_file(dst)
        stat = dst.stat()
        db.execute(
            """INSERT INTO evidence (id,workspace_id,title,description,type,file_path,original_url,md5_hash,sha256_hash,file_size,mime_type,tags,linked_entities,collector_name,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eid, workspace_id, metadata.get("title", src.name), metadata.get("description", ""), metadata.get("type", "file"),
                str(dst), metadata.get("original_url", ""), hashes["md5"], hashes["sha256"], stat.st_size,
                mimetypes.guess_type(str(dst))[0] or "application/octet-stream", json.dumps(metadata.get("tags", [])),
                json.dumps(metadata.get("linked_entities", [])), metadata.get("collector_name", "system"), datetime.utcnow().isoformat(),
            ),
        )
        self._add_chain(eid, "collected", metadata.get("collector_name", "system"), notes="File ingested")
        return self.get(eid)

    def add_url_snapshot(self, workspace_id: str, url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        eid = str(uuid4())
        dst_dir = self.root / workspace_id / eid
        dst_dir.mkdir(parents=True, exist_ok=True)
        html_path = dst_dir / "snapshot.html"
        res = requests.get(url, timeout=20)
        res.raise_for_status()
        html_path.write_text(res.text, encoding="utf-8", errors="ignore")
        return self.add_file(workspace_id, str(html_path), {**metadata, "title": metadata.get("title", url), "type": "url_snapshot", "original_url": url})

    def get(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        row = db.fetchone("SELECT * FROM evidence WHERE id=?", (evidence_id,))
        if not row:
            return None
        row["tags"] = json.loads(row.get("tags") or "[]")
        row["linked_entities"] = json.loads(row.get("linked_entities") or "[]")
        return row

    def list(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = db.fetchall("SELECT * FROM evidence WHERE (? IS NULL OR workspace_id=?) ORDER BY created_at DESC", (workspace_id, workspace_id))
        for row in rows:
            row["tags"] = json.loads(row.get("tags") or "[]")
            row["linked_entities"] = json.loads(row.get("linked_entities") or "[]")
        return rows

    def verify_integrity(self, evidence_id: str, actor: str = "system") -> Dict[str, Any]:
        item = self.get(evidence_id)
        if not item:
            raise ValueError("Evidence not found")
        hashes = self._hash_file(Path(item["file_path"]))
        ok = hashes["md5"] == item.get("md5_hash") and hashes["sha256"] == item.get("sha256_hash")
        self._add_chain(evidence_id, "verified", actor, notes="Hash verification", verified=ok)
        return {"evidence_id": evidence_id, "ok": ok, "current": hashes}

    def get_chain(self, evidence_id: str) -> List[Dict[str, Any]]:
        return db.fetchall("SELECT * FROM custody_chain WHERE evidence_id=? ORDER BY timestamp", (evidence_id,))


_evidence_vault = EvidenceVault()


def get_evidence_vault() -> EvidenceVault:
    return _evidence_vault
