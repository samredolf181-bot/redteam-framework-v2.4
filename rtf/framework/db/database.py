"""RedTeam Framework - Database Layer (SQLite)"""
from __future__ import annotations
import json, sqlite3, threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from framework.core.logger import get_logger

log = get_logger("rtf.db")

_CREATE = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, module_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending', started_at DATETIME, finished_at DATETIME,
    options TEXT, result TEXT, error TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT REFERENCES jobs(id),
    target TEXT, severity TEXT DEFAULT 'info', category TEXT, title TEXT NOT NULL,
    description TEXT, evidence TEXT, tags TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tool_registry (
    name TEXT PRIMARY KEY, category TEXT, install_type TEXT, binary TEXT,
    repo_url TEXT, installed INTEGER DEFAULT 0, version TEXT, last_checked DATETIME, metadata TEXT
);
CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT NOT NULL UNIQUE,
    type TEXT, tags TEXT, notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, module_path TEXT, cron_expr TEXT,
    interval_seconds INTEGER, options TEXT, enabled INTEGER DEFAULT 1,
    last_run DATETIME, next_run DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS operations (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
    priority TEXT DEFAULT 'high', target TEXT, operator TEXT DEFAULT 'rtf',
    summary TEXT, tags TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS graph_nodes (
    id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, value TEXT NOT NULL,
    label TEXT, confidence REAL DEFAULT 0.5, first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP, source_module TEXT, source_job_id TEXT,
    operation_id TEXT, properties TEXT DEFAULT '{}', tags TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS graph_edges (
    id TEXT PRIMARY KEY, source_node_id TEXT NOT NULL REFERENCES graph_nodes(id),
    relationship TEXT NOT NULL, target_node_id TEXT NOT NULL REFERENCES graph_nodes(id),
    confidence REAL DEFAULT 0.5, source_module TEXT, source_job_id TEXT,
    operation_id TEXT, first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP, properties TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS intelligence_artifacts (
    id TEXT PRIMARY KEY, artifact_type TEXT NOT NULL, name TEXT NOT NULL,
    location TEXT, linked_node_id TEXT, linked_job_id TEXT, operation_id TEXT,
    tags TEXT, metadata TEXT DEFAULT '{}', created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS credentials_vault (
    id TEXT PRIMARY KEY, username TEXT, secret TEXT, kind TEXT DEFAULT 'password',
    source TEXT, linked_node_id TEXT, operation_id TEXT, tags TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, severity TEXT DEFAULT 'info',
    source TEXT, target TEXT, operation_id TEXT, job_id TEXT, message TEXT NOT NULL,
    payload TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, format TEXT NOT NULL,
    output_path TEXT NOT NULL, operation_id TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS console_sessions (
    id TEXT PRIMARY KEY, workspace TEXT NOT NULL DEFAULT 'default',
    title TEXT NOT NULL, transcript TEXT DEFAULT '', status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    client_name TEXT,
    case_number TEXT,
    status TEXT DEFAULT 'active',
    classification TEXT DEFAULT 'CONFIDENTIAL',
    description TEXT,
    tags TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    closed_at TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    title TEXT NOT NULL,
    description TEXT,
    type TEXT,
    file_path TEXT,
    original_url TEXT,
    md5_hash TEXT,
    sha256_hash TEXT,
    file_size INTEGER,
    mime_type TEXT,
    tags TEXT,
    linked_entities TEXT,
    collector_name TEXT DEFAULT 'system',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evidence_workspace ON evidence(workspace_id);
CREATE TABLE IF NOT EXISTS custody_chain (
    id TEXT PRIMARY KEY,
    evidence_id TEXT REFERENCES evidence(id),
    event_type TEXT,
    actor TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    notes TEXT,
    hash_verified INTEGER
);
CREATE TABLE IF NOT EXISTS timeline_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    timestamp TEXT,
    event_type TEXT,
    description TEXT,
    source TEXT,
    entity_value TEXT,
    entity_type TEXT,
    confidence REAL DEFAULT 0.5,
    metadata TEXT,
    tags TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_timeline_workspace ON timeline_events(workspace_id);
CREATE INDEX IF NOT EXISTS idx_timeline_timestamp ON timeline_events(timestamp);
CREATE TABLE IF NOT EXISTS agent_sessions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    mode TEXT,
    seed TEXT,
    seed_type TEXT,
    status TEXT DEFAULT 'running',
    max_depth INTEGER DEFAULT 3,
    findings_count INTEGER DEFAULT 0,
    pivots_taken INTEGER DEFAULT 0,
    plan TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS dossiers (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    type TEXT,
    title TEXT,
    classification TEXT DEFAULT 'CONFIDENTIAL',
    status TEXT DEFAULT 'draft',
    format TEXT,
    file_path TEXT,
    file_size INTEGER,
    generated_at TEXT DEFAULT (datetime('now')),
    regenerated_at TEXT
);
CREATE TABLE IF NOT EXISTS plugins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    type TEXT,
    description TEXT,
    enabled INTEGER DEFAULT 1,
    config TEXT,
    installed_at TEXT DEFAULT (datetime('now')),
    last_run TEXT,
    error_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS workspace_notes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    title TEXT,
    content TEXT,
    tags TEXT,
    entity_mentions TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


class Database:
    _instance: Optional["Database"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None) -> "Database":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._db_path = db_path or ""
                obj._local = threading.local()
                cls._instance = obj
        return cls._instance

    def init(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_CREATE)
            try:
                conn.execute("ALTER TABLE findings ADD COLUMN workspace_id TEXT")
            except Exception:
                pass
            conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_workspace ON findings(workspace_id)")
        log.info(f"Database initialised at {db_path}")

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        if not self._db_path:
            self._db_path = "data/framework.db"
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self._db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield self._local.conn
            self._local.conn.commit()
        except Exception:
            self._local.conn.rollback()
            raise

    @staticmethod
    def _encode_json(value: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def _decode_json(value: Any, default: Any = None) -> Any:
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except Exception:
            return default if default is not None else value

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._conn() as conn:
            return conn.execute(sql, params)

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def create_job(self, job_id: str, name: str, module_path: str, options: Dict) -> None:
        self.execute("INSERT INTO jobs (id,name,module_path,status,options) VALUES (?,?,?,?,?)",
                     (job_id, name, module_path, "pending", json.dumps(options)))

    def start_job(self, job_id: str) -> None:
        self.execute("UPDATE jobs SET status='running',started_at=? WHERE id=?",
                     (datetime.utcnow().isoformat(), job_id))

    def finish_job(self, job_id: str, result: Any, error: Optional[str] = None) -> None:
        status = "failed" if error else "completed"
        self.execute("UPDATE jobs SET status=?,finished_at=?,result=?,error=? WHERE id=?",
                     (status, datetime.utcnow().isoformat(),
                      json.dumps(result) if result is not None else None, error, job_id))

    def get_job(self, job_id: str) -> Optional[Dict]:
        job = self.fetchone("SELECT * FROM jobs WHERE id=?", (job_id,))
        if not job:
            return None
        job["options"] = self._decode_json(job.get("options"), {})
        job["result"] = self._decode_json(job.get("result"), None)
        return job

    def list_jobs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        items = self.fetchall("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        for item in items:
            item["options"] = self._decode_json(item.get("options"), {})
            item["result"] = self._decode_json(item.get("result"), None)
        return items

    def count_jobs(self) -> int:
        row = self.fetchone("SELECT COUNT(*) AS count FROM jobs")
        return int(row["count"]) if row else 0

    def add_finding(self, job_id: str, target: str, title: str, category: str = "general",
                    severity: str = "info", description: str = "", evidence: Optional[Dict] = None,
                    tags: Optional[List[str]] = None) -> int:
        cur = self.execute(
            "INSERT INTO findings (job_id,target,severity,category,title,description,evidence,tags) VALUES (?,?,?,?,?,?,?,?)",
            (job_id, target, severity, category, title, description,
             json.dumps(evidence) if evidence else None,
             ",".join(tags) if tags else None))
        return cur.lastrowid

    def list_findings(self, job_id: Optional[str] = None, severity: Optional[str] = None,
                      limit: int = 500, offset: int = 0) -> List[Dict]:
        clauses, params = [], []
        if job_id:
            clauses.append("job_id=?")
            params.append(job_id)
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.extend([limit, offset])
        rows = self.fetchall(f"SELECT * FROM findings {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", tuple(params))
        for row in rows:
            row["evidence"] = self._decode_json(row.get("evidence"), {})
            row["tags"] = [tag for tag in (row.get("tags") or "").split(",") if tag]
        return rows

    def count_findings(self, job_id: Optional[str] = None, severity: Optional[str] = None) -> int:
        clauses, params = [], []
        if job_id:
            clauses.append("job_id=?")
            params.append(job_id)
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = self.fetchone(f"SELECT COUNT(*) AS count FROM findings {where}", tuple(params))
        return int(row["count"]) if row else 0

    def add_target(self, value: str, type_: str = "domain", tags: str = "") -> None:
        self.execute("INSERT OR IGNORE INTO targets (value,type,tags) VALUES (?,?,?)", (value, type_, tags))

    def list_targets(self, limit: int = 500, offset: int = 0) -> List[Dict]:
        return self.fetchall("SELECT * FROM targets ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))

    def count_targets(self) -> int:
        row = self.fetchone("SELECT COUNT(*) AS count FROM targets")
        return int(row["count"]) if row else 0

    def upsert_tool(self, name: str, **kwargs: Any) -> None:
        kwargs["name"] = name
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        updates = ", ".join(f"{k}=excluded.{k}" for k in kwargs if k != "name")
        self.execute(
            f"INSERT INTO tool_registry ({cols}) VALUES ({placeholders}) ON CONFLICT(name) DO UPDATE SET {updates}",
            tuple(kwargs.values()))

    def get_tool(self, name: str) -> Optional[Dict]:
        return self.fetchone("SELECT * FROM tool_registry WHERE name=?", (name,))

    def list_tools(self, category: Optional[str] = None) -> List[Dict]:
        if category:
            return self.fetchall("SELECT * FROM tool_registry WHERE category=? ORDER BY name", (category,))
        return self.fetchall("SELECT * FROM tool_registry ORDER BY name")

    def upsert_operation(self, operation_id: str, name: str, status: str = "active", target: str = "",
                         operator: str = "rtf", priority: str = "high", summary: str = "",
                         tags: Optional[List[str]] = None) -> None:
        self.execute(
            """
            INSERT INTO operations (id,name,status,priority,target,operator,summary,tags,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,status=excluded.status,priority=excluded.priority,target=excluded.target,
                operator=excluded.operator,summary=excluded.summary,tags=excluded.tags,updated_at=excluded.updated_at
            """,
            (operation_id, name, status, priority, target, operator, summary, ",".join(tags or []), datetime.utcnow().isoformat()),
        )

    def list_operations(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM operations ORDER BY updated_at DESC LIMIT ?", (limit,))
        for row in rows:
            row["tags"] = [tag for tag in (row.get("tags") or "").split(",") if tag]
        return rows

    def upsert_graph_node(self, node_id: str, entity_type: str, value: str, label: Optional[str] = None,
                          confidence: float = 0.5, source_module: Optional[str] = None,
                          source_job_id: Optional[str] = None, operation_id: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> None:
        self.execute(
            """
            INSERT INTO graph_nodes (id,entity_type,value,label,confidence,last_seen,source_module,source_job_id,operation_id,properties,tags)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                entity_type=excluded.entity_type,value=excluded.value,label=excluded.label,
                confidence=excluded.confidence,last_seen=excluded.last_seen,source_module=excluded.source_module,
                source_job_id=excluded.source_job_id,operation_id=excluded.operation_id,
                properties=excluded.properties,tags=excluded.tags
            """,
            (node_id, entity_type, value, label or value, confidence, datetime.utcnow().isoformat(),
             source_module, source_job_id, operation_id, self._encode_json(properties or {}), ",".join(tags or [])),
        )

    def list_graph_nodes(self, operation_id: Optional[str] = None, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        clauses, params = [], []
        if operation_id:
            clauses.append("operation_id=?")
            params.append(operation_id)
        if entity_type:
            clauses.append("entity_type=?")
            params.append(entity_type)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.fetchall(f"SELECT * FROM graph_nodes {where} ORDER BY last_seen DESC", tuple(params))
        for row in rows:
            row["properties"] = self._decode_json(row.get("properties"), {})
            row["tags"] = [tag for tag in (row.get("tags") or "").split(",") if tag]
        return rows

    def upsert_graph_edge(self, edge_id: str, source_node_id: str, relationship: str, target_node_id: str,
                          confidence: float = 0.5, source_module: Optional[str] = None,
                          source_job_id: Optional[str] = None, operation_id: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None) -> None:
        self.execute(
            """
            INSERT INTO graph_edges (id,source_node_id,relationship,target_node_id,confidence,source_module,source_job_id,operation_id,last_seen,properties)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                source_node_id=excluded.source_node_id,relationship=excluded.relationship,
                target_node_id=excluded.target_node_id,confidence=excluded.confidence,
                source_module=excluded.source_module,source_job_id=excluded.source_job_id,
                operation_id=excluded.operation_id,last_seen=excluded.last_seen,properties=excluded.properties
            """,
            (edge_id, source_node_id, relationship, target_node_id, confidence, source_module,
             source_job_id, operation_id, datetime.utcnow().isoformat(), self._encode_json(properties or {})),
        )

    def list_graph_edges(self, operation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if operation_id:
            rows = self.fetchall("SELECT * FROM graph_edges WHERE operation_id=? ORDER BY last_seen DESC", (operation_id,))
        else:
            rows = self.fetchall("SELECT * FROM graph_edges ORDER BY last_seen DESC")
        for row in rows:
            row["properties"] = self._decode_json(row.get("properties"), {})
        return rows

    def add_event(self, event_type: str, message: str, severity: str = "info", source: str = "system",
                  target: Optional[str] = None, operation_id: Optional[str] = None,
                  job_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> int:
        cur = self.execute(
            "INSERT INTO event_log (event_type,severity,source,target,operation_id,job_id,message,payload) VALUES (?,?,?,?,?,?,?,?)",
            (event_type, severity, source, target, operation_id, job_id, message, self._encode_json(payload or {})),
        )
        return int(cur.lastrowid)

    def list_events(self, limit: int = 250, severity: Optional[str] = None, source: Optional[str] = None,
                    target: Optional[str] = None) -> List[Dict[str, Any]]:
        clauses, params = [], []
        if severity:
            clauses.append("severity=?")
            params.append(severity)
        if source:
            clauses.append("source=?")
            params.append(source)
        if target:
            clauses.append("target=?")
            params.append(target)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.fetchall(f"SELECT * FROM event_log {where} ORDER BY created_at DESC LIMIT ?", tuple(params + [limit]))
        for row in rows:
            row["payload"] = self._decode_json(row.get("payload"), {})
        return rows

    def add_artifact(self, artifact_id: str, artifact_type: str, name: str, location: str = "",
                     linked_node_id: Optional[str] = None, linked_job_id: Optional[str] = None,
                     operation_id: Optional[str] = None, tags: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        self.execute(
            "INSERT INTO intelligence_artifacts (id,artifact_type,name,location,linked_node_id,linked_job_id,operation_id,tags,metadata) VALUES (?,?,?,?,?,?,?,?,?)",
            (artifact_id, artifact_type, name, location, linked_node_id, linked_job_id, operation_id,
             ",".join(tags or []), self._encode_json(metadata or {})),
        )

    def list_artifacts(self, operation_id: Optional[str] = None, limit: int = 250) -> List[Dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM intelligence_artifacts WHERE (? IS NULL OR operation_id=?) ORDER BY created_at DESC LIMIT ?",
            (operation_id, operation_id, limit),
        )
        for row in rows:
            row["metadata"] = self._decode_json(row.get("metadata"), {})
            row["tags"] = [tag for tag in (row.get("tags") or "").split(",") if tag]
        return rows

    def add_credential(self, credential_id: str, username: str, secret: str, kind: str = "password",
                       source: str = "module", linked_node_id: Optional[str] = None,
                       operation_id: Optional[str] = None, tags: Optional[List[str]] = None) -> None:
        self.execute(
            "INSERT INTO credentials_vault (id,username,secret,kind,source,linked_node_id,operation_id,tags) VALUES (?,?,?,?,?,?,?,?)",
            (credential_id, username, secret, kind, source, linked_node_id, operation_id, ",".join(tags or [])),
        )

    def list_credentials(self, operation_id: Optional[str] = None, limit: int = 250) -> List[Dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM credentials_vault WHERE (? IS NULL OR operation_id=?) ORDER BY created_at DESC LIMIT ?",
            (operation_id, operation_id, limit),
        )
        for row in rows:
            row["tags"] = [tag for tag in (row.get("tags") or "").split(",") if tag]
        return rows

    def add_report(self, report_id: str, title: str, format: str, output_path: str,
                   operation_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.execute(
            "INSERT INTO reports (id,title,format,output_path,operation_id,metadata) VALUES (?,?,?,?,?,?)",
            (report_id, title, format, output_path, operation_id, self._encode_json(metadata or {})),
        )

    def list_reports(self, operation_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM reports WHERE (? IS NULL OR operation_id=?) ORDER BY created_at DESC LIMIT ?",
            (operation_id, operation_id, limit),
        )
        for row in rows:
            row["metadata"] = self._decode_json(row.get("metadata"), {})
        return rows

    def upsert_console_session(self, session_id: str, title: str, workspace: str = "default",
                               transcript: str = "", status: str = "active") -> None:
        self.execute(
            """
            INSERT INTO console_sessions (id,workspace,title,transcript,status,updated_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET workspace=excluded.workspace,title=excluded.title,
                transcript=excluded.transcript,status=excluded.status,updated_at=excluded.updated_at
            """,
            (session_id, workspace, title, transcript, status, datetime.utcnow().isoformat()),
        )

    def list_console_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.fetchall("SELECT * FROM console_sessions ORDER BY updated_at DESC LIMIT ?", (limit,))


db = Database()
