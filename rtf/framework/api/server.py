"""RedTeam Framework v2.0 - REST API Server"""
from __future__ import annotations
import asyncio, json, uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

try:
    from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

from framework.core.config import config
from framework.core.logger import get_logger
from framework.db.database import db
from framework.modules.loader import module_loader
from framework.omega import omega_doctor, omega_registry
from framework.registry.tool_registry import ToolCategory, tool_registry
from framework.reporting.engine import Finding as ReportFinding, ReportEngine
from framework.scheduler.scheduler import JobStatus, scheduler
from framework.titan import TitanKnowledgeGraph, TitanOrchestrator, build_titan_manifest
from framework.titan.knowledge_graph import ENTITY_TYPES, RELATIONSHIP_TYPES
from framework.titan.socmint_pipeline import SOCMINT_STAGES, TitanSOCMINTPipeline
from framework.upgrade import build_v4_upgrade_report
from framework.workflows.engine import BUILTIN_WORKFLOWS, get_workflow

log = get_logger("rtf.api")
report_engine = ReportEngine()

if _HAS_FASTAPI:
    class ModuleRunRequest(BaseModel):
        options: Dict[str, Any] = {}
        operation_id: str = "primary"
        target: Optional[str] = None

    class WorkflowRunRequest(BaseModel):
        options: Dict[str, Any] = {}
        output_dir: Optional[str] = None
        operation_id: str = "primary"

    class TargetAddRequest(BaseModel):
        value: str
        type: str = "domain"
        tags: str = ""

    class ScheduleRequest(BaseModel):
        path: str
        interval_seconds: int
        options: Dict[str, Any] = {}
        operation_id: str = "primary"

    class GraphSeedRequest(BaseModel):
        operation_id: str = "primary"
        entity_type: str
        value: str
        label: Optional[str] = None
        confidence: float = 0.75
        properties: Dict[str, Any] = {}
        tags: List[str] = []

    class GraphRelationshipRequest(BaseModel):
        operation_id: str = "primary"
        source_node_id: str
        relationship: str
        target_node_id: str
        confidence: float = 0.7
        properties: Dict[str, Any] = {}

    class ReportRequest(BaseModel):
        title: str
        format: str = "html"
        operation_id: str = "primary"
        finding_ids: List[int] = []
        metadata: Dict[str, Any] = {}

    class TerminalCommandRequest(BaseModel):
        command: str
        workspace: str = "default"
        session_id: Optional[str] = None


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    async def publish(self, event: Dict[str, Any]) -> None:
        for subscriber in list(self._subscribers):
            try:
                subscriber.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)


event_broker = EventBroker()


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _safe_node_id(entity_type: str, value: str) -> str:
    return f"{entity_type}:{value}".replace(" ", "_")


def _module_registry() -> List[Dict[str, Any]]:
    registry: List[Dict[str, Any]] = []
    for item in module_loader.list_modules():
        cls = module_loader.get(item["path"])
        instance = cls()
        info = instance.info()
        registry.append(
            {
                **item,
                "info": info,
                "options": instance.show_options(),
                "supports_schedule": True,
                "supports_workflow_attach": True,
            }
        )
    return registry


def _workflow_registry() -> List[Dict[str, Any]]:
    workflows: List[Dict[str, Any]] = []
    for name, wf_class in BUILTIN_WORKFLOWS.items():
        wf = wf_class()
        workflows.append(
            {
                "name": name,
                "description": wf.description,
                "steps": [
                    {
                        "name": step.name,
                        "module": step.module_class.__name__,
                        "required": step.required,
                        "retry_count": step.retry_count,
                        "depends_on_success": step.depends_on_success,
                    }
                    for step in wf.steps()
                ],
            }
        )
    return workflows


def _findings_for_report(finding_ids: List[int]) -> List[ReportFinding]:
    findings = db.list_findings(limit=5000)
    filtered = [f for f in findings if not finding_ids or f["id"] in finding_ids]
    result: List[ReportFinding] = []
    for item in filtered:
        result.append(
            ReportFinding(
                title=item["title"],
                target=item.get("target") or "",
                severity=item["severity"],
                description=item.get("description") or "",
                category=item.get("category") or "general",
                evidence=item.get("evidence") or {},
                tags=item.get("tags") or [],
            )
        )
    return result


def _infer_graph_entities(operation_id: str, result: Dict[str, Any], module_path: str, job_id: str) -> None:
    output = result.get("output") or {}
    candidates: List[tuple[str, str, Dict[str, Any]]] = []
    findings = result.get("findings") or []

    def _classify(field: str, value: str) -> Optional[str]:
        lowered = field.lower()
        if "@" in value or "email" in lowered:
            return "Email"
        if lowered in {"username", "candidate_username", "handle"}:
            return "Username"
        if lowered in {"phone", "mobile"}:
            return "Phone"
        if lowered in {"organization", "company"}:
            return "Organization"
        if lowered in {"repository", "repo"}:
            return "Repository"
        if lowered in {"location", "city", "country"}:
            return "Location"
        if lowered in {"device", "user_agent"}:
            return "Device"
        if lowered in {"website", "url"}:
            return "Website"
        if lowered in {"document", "file"}:
            return "Document"
        if lowered in {"media", "image", "avatar"}:
            return "Media"
        if lowered in {"ip", "host"} or value.replace('.', '').isdigit():
            return "IP"
        if "." in value and " " not in value and "/" not in value:
            return "Domain"
        return "Person"

    for finding in findings:
        target = finding.get("target")
        if not target:
            continue
        entity_type = _classify(finding.get("category", "target"), target)
        candidates.append((entity_type, target, {"title": finding.get("title"), "category": finding.get("category")}))
    if isinstance(output, dict):
        for key, value in output.items():
            if isinstance(value, str) and value:
                candidates.append((_classify(key, value), value, {"field": key}))
            elif isinstance(value, list):
                for item in value[:10]:
                    if isinstance(item, str) and item:
                        candidates.append((_classify(key, item), item, {"field": key}))
    previous_node_id: Optional[str] = None
    primary_person_id: Optional[str] = None
    for entity_type, value, props in candidates[:40]:
        node_id = _safe_node_id(entity_type, value)
        db.upsert_graph_node(
            node_id=node_id,
            entity_type=entity_type,
            value=value,
            label=value,
            confidence=0.72,
            source_module=module_path,
            source_job_id=job_id,
            operation_id=operation_id,
            properties=props,
            tags=[module_path.split("/")[0]],
        )
        if entity_type == "Person" and primary_person_id is None:
            primary_person_id = node_id
        relationship = "ASSOCIATED_WITH"
        if primary_person_id and primary_person_id != node_id:
            if entity_type == "Email":
                relationship = "USES_EMAIL"
            elif entity_type == "Phone":
                relationship = "USES_PHONE"
            elif entity_type == "Domain":
                relationship = "ASSOCIATED_WITH"
            elif entity_type == "Username":
                relationship = "OWNS"
            elif entity_type == "Location":
                relationship = "POSTED_FROM"
            elif entity_type in {"Repository", "Document", "Media", "Website"}:
                relationship = "MENTIONED_IN"
            edge_id = f"{primary_person_id}->{relationship}->{node_id}"
            db.upsert_graph_edge(
                edge_id=edge_id,
                source_node_id=primary_person_id,
                relationship=relationship,
                target_node_id=node_id,
                confidence=0.65,
                source_module=module_path,
                source_job_id=job_id,
                operation_id=operation_id,
                properties={"provenance": module_path},
            )
        elif previous_node_id and previous_node_id != node_id:
            edge_id = f"{previous_node_id}->{module_path}->{node_id}"
            db.upsert_graph_edge(
                edge_id=edge_id,
                source_node_id=previous_node_id,
                relationship="CONNECTED_TO",
                target_node_id=node_id,
                confidence=0.6,
                source_module=module_path,
                source_job_id=job_id,
                operation_id=operation_id,
                properties={"provenance": module_path},
            )
        previous_node_id = node_id


async def _record_event(event_type: str, message: str, severity: str = "info", source: str = "system",
                        target: Optional[str] = None, operation_id: Optional[str] = None,
                        job_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
    event_id = db.add_event(
        event_type=event_type,
        message=message,
        severity=severity,
        source=source,
        target=target,
        operation_id=operation_id,
        job_id=job_id,
        payload=payload or {},
    )
    await event_broker.publish(
        {
            "id": event_id,
            "event_type": event_type,
            "severity": severity,
            "source": source,
            "target": target,
            "operation_id": operation_id,
            "job_id": job_id,
            "message": message,
            "payload": payload or {},
        }
    )


def create_app() -> "FastAPI":
    if not _HAS_FASTAPI:
        raise ImportError("fastapi and pydantic are required: pip install fastapi uvicorn")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        log.info("API server starting")
        db.init(config.get("db_path", "data/framework.db"))
        module_loader.load_all()
        tool_registry.refresh()
        db.upsert_operation("primary", name="Primary Operation", summary="Default dashboard operation", tags=["dashboard"])
        await scheduler.start()
        yield
        await scheduler.stop()
        log.info("API server stopped")

    app = FastAPI(title="RTF API", description="RedTeam Framework v2.0 REST API", version="2.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    frontend_dist = Path(__file__).resolve().parents[2] / "dashboard_ui" / "dist"
    if frontend_dist.exists():
        app.mount("/dashboard/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="dashboard-assets")

    def _api_keys() -> Set[str]:
        raw = config.get("api_keys", [])
        if isinstance(raw, str):
            return {k.strip() for k in raw.split(",") if k.strip()}
        if isinstance(raw, list):
            return {str(k).strip() for k in raw if str(k).strip()}
        return set()

    def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
        allowed = _api_keys()
        if not allowed:
            return
        if not x_api_key or x_api_key not in allowed:
            raise HTTPException(status_code=401, detail="Unauthorized")

    def paginated(items: List[Any], limit: int, offset: int, total: int) -> Dict[str, Any]:
        return {"items": items, "pagination": {"limit": limit, "offset": offset, "total": total, "has_more": offset + len(items) < total}}

    v1 = APIRouter(prefix="/api/v1")
    titan = TitanOrchestrator()
    socmint = TitanSOCMINTPipeline()

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_shell():
        if frontend_dist.exists() and (frontend_dist / "index.html").exists():
            return FileResponse(frontend_dist / "index.html")
        return {"message": "Build the React dashboard in dashboard_ui/ before serving /dashboard."}

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket):
        await websocket.accept()
        queue = await event_broker.subscribe()
        try:
            await websocket.send_json({"type": "snapshot", "events": db.list_events(limit=50)})
            while True:
                event = await queue.get()
                await websocket.send_json({"type": "event", "data": event})
        except WebSocketDisconnect:
            event_broker.unsubscribe(queue)
        except Exception:
            event_broker.unsubscribe(queue)
            raise

    @app.get("/health", tags=["system"])
    @v1.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "framework": "RTF v4.0 OMEGA-BLACK", "doctor": omega_doctor.validate()}

    @app.get("/stats", tags=["system"])
    @v1.get("/stats", tags=["system"])
    async def stats():
        return {"modules": len(module_loader.list_modules()), "tools": tool_registry.summary(), "jobs": scheduler.stats(), "omega": omega_doctor.validate()}

    @app.get("/modules", tags=["modules"])
    @v1.get("/modules", tags=["modules"])
    async def list_modules(category: Optional[str] = Query(None), _auth: None = Depends(require_api_key)):
        modules = _module_registry()
        if category:
            modules = [m for m in modules if m["category"] == category]
        return modules

    @app.get("/modules/search", tags=["modules"])
    @v1.get("/modules/search", tags=["modules"])
    async def search_modules(q: str = Query(..., min_length=1), _auth: None = Depends(require_api_key)):
        ql = q.lower()
        return [m for m in _module_registry() if ql in json.dumps(m).lower()]

    @app.get("/modules/{category}/{name}", tags=["modules"])
    @v1.get("/modules/{category}/{name}", tags=["modules"])
    async def get_module(category: str, name: str, _auth: None = Depends(require_api_key)):
        path = f"{category}/{name}"
        try:
            cls = module_loader.get(path)
            instance = cls()
            return {"path": path, "info": instance.info(), "options": instance.show_options()}
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/modules/{category}/{name}/run", tags=["modules"])
    @v1.post("/modules/{category}/{name}/run", tags=["modules"])
    async def run_module(category: str, name: str, body: ModuleRunRequest, background_tasks: BackgroundTasks, _auth: None = Depends(require_api_key)):
        path = f"{category}/{name}"
        try:
            cls = module_loader.get(path)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        job_id = str(uuid.uuid4())
        target = body.target or body.options.get("target") or body.options.get("domain")
        db.create_job(job_id, name, path, body.options)
        db.start_job(job_id)
        db.upsert_operation(body.operation_id, name=f"Operation {body.operation_id}", target=target or "", summary=f"Latest run: {path}")
        await _record_event("module.submitted", f"Queued module {path}", source=path, target=target, operation_id=body.operation_id, job_id=job_id, payload=body.options)

        async def _run() -> None:
            await _record_event("module.started", f"Started module {path}", source=path, target=target, operation_id=body.operation_id, job_id=job_id)
            instance = cls()
            result = await instance.execute(body.options)
            result_payload = result.to_dict()
            db.finish_job(job_id, result_payload, result.error)
            for finding in result.findings:
                db.add_finding(job_id=job_id, target=finding.target, title=finding.title, category=finding.category, severity=finding.severity.value, description=finding.description, evidence=finding.evidence, tags=finding.tags)
            _infer_graph_entities(body.operation_id, result_payload, path, job_id)
            artifact_id = str(uuid.uuid4())
            db.add_artifact(artifact_id, artifact_type="module-result", name=path, location=f"job:{job_id}", linked_job_id=job_id, operation_id=body.operation_id, tags=[category], metadata=result_payload)
            await _record_event("module.completed" if result.success else "module.failed", f"Finished module {path}", severity="info" if result.success else "high", source=path, target=target, operation_id=body.operation_id, job_id=job_id, payload=result_payload)

        background_tasks.add_task(_run)
        return {"job_id": job_id, "status": "running", "module": path}

    @app.post("/scheduler/interval", tags=["scheduler"])
    @v1.post("/scheduler/interval", tags=["scheduler"])
    async def schedule_module(body: ScheduleRequest, _auth: None = Depends(require_api_key)):
        cls = module_loader.get(body.path)

        async def _scheduled_run() -> Dict[str, Any]:
            instance = cls()
            result = await instance.execute(body.options)
            await _record_event("schedule.execution", f"Scheduled module ran: {body.path}", source=body.path, operation_id=body.operation_id, payload=result.to_dict())
            return result.to_dict()

        job = scheduler.schedule_interval(body.path, _scheduled_run, body.interval_seconds, tags=["scheduled", body.operation_id])
        await _record_event("schedule.created", f"Scheduled {body.path} every {body.interval_seconds}s", source="scheduler", operation_id=body.operation_id, payload={"job_id": job.id})
        return job.to_dict()

    @app.get("/workflows", tags=["workflows"])
    @v1.get("/workflows", tags=["workflows"])
    async def list_workflows(_auth: None = Depends(require_api_key)):
        return _workflow_registry()

    @app.post("/workflows/{name}/run", tags=["workflows"])
    @v1.post("/workflows/{name}/run", tags=["workflows"])
    async def run_workflow(name: str, body: WorkflowRunRequest, background_tasks: BackgroundTasks, _auth: None = Depends(require_api_key)):
        try:
            wf = get_workflow(name, body.options)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        job_id = str(uuid.uuid4())
        db.create_job(job_id, name, f"workflow/{name}", body.options)
        db.start_job(job_id)
        await _record_event("workflow.submitted", f"Queued workflow {name}", source=name, operation_id=body.operation_id, job_id=job_id, payload=body.options)

        async def _run() -> None:
            await _record_event("workflow.started", f"Started workflow {name}", source=name, operation_id=body.operation_id, job_id=job_id)
            result = await wf.run(output_dir=body.output_dir)
            payload = result.to_dict()
            db.finish_job(job_id, payload)
            for step in payload.get("steps", []):
                await _record_event("workflow.step", f"{name}:{step['name']} -> {'ok' if step['success'] else 'failed'}", severity="info" if step["success"] else "medium", source=name, operation_id=body.operation_id, job_id=job_id, payload=step)
            db.add_artifact(str(uuid.uuid4()), artifact_type="workflow-result", name=name, location=f"workflow:{job_id}", linked_job_id=job_id, operation_id=body.operation_id, tags=["workflow"], metadata=payload)
            await _record_event("workflow.completed", f"Finished workflow {name}", source=name, operation_id=body.operation_id, job_id=job_id, payload=payload)

        background_tasks.add_task(_run)
        return {"job_id": job_id, "status": "running", "workflow": name}

    @app.get("/jobs", tags=["jobs"])
    @v1.get("/jobs", tags=["jobs"])
    async def list_jobs(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), _auth: None = Depends(require_api_key)):
        items = db.list_jobs(limit=limit, offset=offset)
        return paginated(items, limit=limit, offset=offset, total=db.count_jobs())

    @app.get("/jobs/{job_id}", tags=["jobs"])
    @v1.get("/jobs/{job_id}", tags=["jobs"])
    async def get_job(job_id: str, _auth: None = Depends(require_api_key)):
        job = db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.get("/findings", tags=["findings"])
    @v1.get("/findings", tags=["findings"])
    async def list_findings(job_id: Optional[str] = None, severity: Optional[str] = None, limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0), _auth: None = Depends(require_api_key)):
        items = db.list_findings(job_id=job_id, severity=severity, limit=limit, offset=offset)
        return paginated(items, limit=limit, offset=offset, total=db.count_findings(job_id=job_id, severity=severity))

    @app.get("/targets", tags=["targets"])
    @v1.get("/targets", tags=["targets"])
    async def list_targets(limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0), _auth: None = Depends(require_api_key)):
        items = db.list_targets(limit=limit, offset=offset)
        return paginated(items, limit=limit, offset=offset, total=db.count_targets())

    @app.post("/targets", tags=["targets"])
    @v1.post("/targets", tags=["targets"])
    async def add_target(body: TargetAddRequest, _auth: None = Depends(require_api_key)):
        db.add_target(body.value, body.type, body.tags)
        return {"status": "added", "target": body.value}

    @app.get("/tools", tags=["tools"])
    @v1.get("/tools", tags=["tools"])
    async def list_tools(category: Optional[str] = None, installed: Optional[bool] = None, _auth: None = Depends(require_api_key)):
        cat = ToolCategory(category) if category else None
        tools = tool_registry.list_all(category=cat)
        if installed is not None:
            tools = [t for t in tools if t.installed == installed]
        return [t.to_dict() for t in tools]

    @app.get("/tools/summary", tags=["tools"])
    @v1.get("/tools/summary", tags=["tools"])
    async def tools_summary(_auth: None = Depends(require_api_key)):
        return tool_registry.summary()

    @app.post("/tools/{name}/install", tags=["tools"])
    @v1.post("/tools/{name}/install", tags=["tools"])
    async def install_tool(name: str, background_tasks: BackgroundTasks, _auth: None = Depends(require_api_key)):
        if not tool_registry.get(name):
            raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
        background_tasks.add_task(tool_registry.install, name)
        return {"status": "installing", "tool": name}

    @app.post("/tools/refresh", tags=["tools"])
    @v1.post("/tools/refresh", tags=["tools"])
    async def refresh_tools(background_tasks: BackgroundTasks, _auth: None = Depends(require_api_key)):
        background_tasks.add_task(tool_registry.refresh)
        return {"status": "refreshing"}

    @app.get("/scheduler/jobs", tags=["scheduler"])
    @v1.get("/scheduler/jobs", tags=["scheduler"])
    async def list_scheduler_jobs(_auth: None = Depends(require_api_key)):
        return [j.to_dict() for j in scheduler.list_jobs()]

    @app.get("/upgrade/report", tags=["upgrade"])
    @v1.get("/upgrade/report", tags=["upgrade"])
    async def upgrade_report(_auth: None = Depends(require_api_key)):
        return build_v4_upgrade_report()

    @app.get("/omega/manifest", tags=["omega"])
    @v1.get("/omega/manifest", tags=["omega"])
    async def omega_manifest(_auth: None = Depends(require_api_key)):
        module_loader.load_all()
        return omega_registry.manifest()

    @app.get("/omega/sources", tags=["omega"])
    @v1.get("/omega/sources", tags=["omega"])
    async def omega_sources(_auth: None = Depends(require_api_key)):
        return omega_registry.source_catalog()

    @app.get("/omega/doctor", tags=["omega"])
    @v1.get("/omega/doctor", tags=["omega"])
    async def omega_doctor_endpoint(_auth: None = Depends(require_api_key)):
        return omega_doctor.diagnose()

    @app.get("/omega/validate", tags=["omega"])
    @v1.get("/omega/validate", tags=["omega"])
    async def omega_validate(_auth: None = Depends(require_api_key)):
        return omega_doctor.validate()

    @app.get("/titan/manifest", tags=["titan"])
    @v1.get("/titan/manifest", tags=["titan"])
    async def titan_manifest(_auth: None = Depends(require_api_key)):
        return build_titan_manifest()

    @app.get("/titan/health", tags=["titan"])
    @v1.get("/titan/health", tags=["titan"])
    async def titan_health(_auth: None = Depends(require_api_key)):
        return titan.health()

    @app.post("/titan/investigate", tags=["titan"])
    @v1.post("/titan/investigate", tags=["titan"])
    async def titan_investigate(body: ModuleRunRequest, _auth: None = Depends(require_api_key)):
        result = await titan.run_investigation(body.options)
        await _record_event("titan.investigation", "Completed TITAN investigation", source="titan", operation_id=body.operation_id, payload=result)
        return result

    @app.get("/dashboard/summary", tags=["dashboard"])
    @v1.get("/dashboard/summary", tags=["dashboard"])
    async def dashboard_summary(operation_id: str = Query("primary"), _auth: None = Depends(require_api_key)):
        modules = _module_registry()
        jobs = db.list_jobs(limit=20)
        findings = db.list_findings(limit=200)
        events = db.list_events(limit=50)
        graph_nodes = db.list_graph_nodes(operation_id=operation_id)
        graph_edges = db.list_graph_edges(operation_id=operation_id)
        tool_summary = tool_registry.summary()
        scheduler_jobs = [j.to_dict() for j in scheduler.list_jobs()]
        operations = db.list_operations(limit=10)
        severity_counts: Dict[str, int] = {sev: 0 for sev in ["critical", "high", "medium", "low", "info"]}
        for finding in findings:
            severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1
        return {
            "operation_id": operation_id,
            "operations": operations,
            "metrics": {
                "modules": len(modules),
                "categories": len({m['category'] for m in modules}),
                "jobs_total": db.count_jobs(),
                "findings_total": db.count_findings(),
                "graph_nodes": len(graph_nodes),
                "graph_edges": len(graph_edges),
                "scheduler_queue_depth": len([j for j in scheduler_jobs if j["status"] in {JobStatus.PENDING.value, JobStatus.SCHEDULED.value}]),
                "tool_coverage": tool_summary,
                "severity_counts": severity_counts,
            },
            "recent_jobs": jobs,
            "recent_findings": findings[:12],
            "recent_events": events,
            "module_categories": sorted({m["category"] for m in modules}),
        }

    @app.get("/dashboard/graph", tags=["dashboard"])
    @v1.get("/dashboard/graph", tags=["dashboard"])
    async def dashboard_graph(operation_id: str = Query("primary"), entity_type: Optional[str] = Query(None), _auth: None = Depends(require_api_key)):
        nodes = db.list_graph_nodes(operation_id=operation_id, entity_type=entity_type)
        edges = db.list_graph_edges(operation_id=operation_id)
        return {
            "schema": {"entity_types": ENTITY_TYPES, "relationship_types": RELATIONSHIP_TYPES},
            "nodes": nodes,
            "edges": edges,
        }

    @app.post("/dashboard/graph/nodes", tags=["dashboard"])
    @v1.post("/dashboard/graph/nodes", tags=["dashboard"])
    async def add_graph_node(body: GraphSeedRequest, _auth: None = Depends(require_api_key)):
        if body.entity_type not in ENTITY_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported entity type {body.entity_type}")
        node_id = _safe_node_id(body.entity_type, body.value)
        db.upsert_graph_node(node_id, body.entity_type, body.value, label=body.label, confidence=body.confidence, operation_id=body.operation_id, properties=body.properties, tags=body.tags)
        await _record_event("graph.node", f"Added graph node {node_id}", source="graph", operation_id=body.operation_id, payload=body.model_dump())
        return {"node_id": node_id}

    @app.post("/dashboard/graph/edges", tags=["dashboard"])
    @v1.post("/dashboard/graph/edges", tags=["dashboard"])
    async def add_graph_edge(body: GraphRelationshipRequest, _auth: None = Depends(require_api_key)):
        if body.relationship not in RELATIONSHIP_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported relationship {body.relationship}")
        edge_id = f"{body.source_node_id}->{body.relationship}->{body.target_node_id}"
        db.upsert_graph_edge(edge_id, body.source_node_id, body.relationship, body.target_node_id, confidence=body.confidence, operation_id=body.operation_id, properties=body.properties)
        await _record_event("graph.edge", f"Linked {body.source_node_id} to {body.target_node_id}", source="graph", operation_id=body.operation_id, payload=body.model_dump())
        return {"edge_id": edge_id}

    @app.get("/dashboard/workflows", tags=["dashboard"])
    @v1.get("/dashboard/workflows", tags=["dashboard"])
    async def workflow_builder(_auth: None = Depends(require_api_key)):
        modules = _module_registry()
        workflow_map = {wf["name"]: wf for wf in _workflow_registry()}
        return {"workflows": workflow_map, "module_registry": modules}

    @app.get("/dashboard/socmint", tags=["dashboard"])
    @v1.get("/dashboard/socmint", tags=["dashboard"])
    async def socmint_view(seed_username: str = Query("analyst_seed"), operation_id: str = Query("primary"), _auth: None = Depends(require_api_key)):
        seed = {"username": seed_username, "candidate_username": f"{seed_username}_ops", "email": f"{seed_username}@example.com", "posting_hour": 22, "candidate_posting_hour": 21, "writing_sample": "tradecraft and operational security", "candidate_writing_sample": "tradecraft and opsec workflow"}
        pipeline = socmint.run(seed)
        identity = pipeline["identity_resolution"]
        clusters = [
            {"cluster_id": "cluster-alpha", "confidence": identity["confidence"], "signals": identity["signals"], "entities": [seed_username, f"{seed_username}_ops", f"{seed_username}@example.com"]}
        ]
        return {
            "operation_id": operation_id,
            "stage_count": len(SOCMINT_STAGES),
            "stages": pipeline["stages"],
            "graph": pipeline["graph"],
            "identity_clusters": clusters,
            "correlation": identity,
        }

    @app.get("/dashboard/vault", tags=["dashboard"])
    @v1.get("/dashboard/vault", tags=["dashboard"])
    async def data_vault(operation_id: str = Query("primary"), q: Optional[str] = Query(None), _auth: None = Depends(require_api_key)):
        findings = db.list_findings(limit=250)
        entities = db.list_graph_nodes(operation_id=operation_id)
        artifacts = db.list_artifacts(operation_id=operation_id)
        creds = db.list_credentials(operation_id=operation_id)
        if q:
            ql = q.lower()
            findings = [f for f in findings if ql in json.dumps(f).lower()]
            entities = [e for e in entities if ql in json.dumps(e).lower()]
            artifacts = [a for a in artifacts if ql in json.dumps(a).lower()]
            creds = [c for c in creds if ql in json.dumps(c).lower()]
        return {"findings": findings, "entities": entities, "artifacts": artifacts, "credentials": creds}

    @app.get("/dashboard/events", tags=["dashboard"])
    @v1.get("/dashboard/events", tags=["dashboard"])
    async def dashboard_events(limit: int = Query(250, ge=1, le=2000), severity: Optional[str] = None, source: Optional[str] = None, target: Optional[str] = None, _auth: None = Depends(require_api_key)):
        return db.list_events(limit=limit, severity=severity, source=source, target=target)

    @app.get("/dashboard/reports", tags=["dashboard"])
    @v1.get("/dashboard/reports", tags=["dashboard"])
    async def list_reports(operation_id: str = Query("primary"), _auth: None = Depends(require_api_key)):
        return db.list_reports(operation_id=operation_id)

    @app.post("/dashboard/reports", tags=["dashboard"])
    @v1.post("/dashboard/reports", tags=["dashboard"])
    async def generate_report(body: ReportRequest, _auth: None = Depends(require_api_key)):
        findings = _findings_for_report(body.finding_ids)
        output_dir = Path("data/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{body.title.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}.{body.format}"
        path = report_engine.generate(body.title, findings, format=body.format, output_path=str(output_path), metadata={**body.metadata, "operation_id": body.operation_id})
        report_id = str(uuid.uuid4())
        db.add_report(report_id, body.title, body.format, path, operation_id=body.operation_id, metadata=body.metadata)
        await _record_event("report.generated", f"Generated {body.format} report {body.title}", source="reporting", operation_id=body.operation_id, payload={"report_id": report_id, "path": path})
        return {"report_id": report_id, "path": path}

    @app.get("/dashboard/health", tags=["dashboard"])
    @v1.get("/dashboard/health", tags=["dashboard"])
    async def dashboard_health(_auth: None = Depends(require_api_key)):
        tool_summary = tool_registry.summary()
        return {
            "tool_summary": tool_summary,
            "worker_status": scheduler.stats(),
            "scheduler_jobs": [j.to_dict() for j in scheduler.list_jobs()],
            "api": {"status": "ok", "version": "2.1.0"},
            "database": {"path": config.get("db_path", "data/framework.db"), "status": "connected"},
        }

    @app.post("/dashboard/terminal/command", tags=["dashboard"])
    @v1.post("/dashboard/terminal/command", tags=["dashboard"])
    async def terminal_command(body: TerminalCommandRequest, _auth: None = Depends(require_api_key)):
        session_id = body.session_id or str(uuid.uuid4())
        command = body.command.strip()
        transcript_lines: List[str] = [f"rtf({body.workspace})> {command}"]
        response: Dict[str, Any] = {"session_id": session_id, "workspace": body.workspace, "command": command}
        if command in {"help", "?"}:
            transcript_lines.append("commands: sessions, creds, notes, workspace, resource <file>, jobs, findings")
        elif command == "sessions":
            transcript_lines.append(json.dumps(db.list_console_sessions(limit=10), indent=2))
        elif command == "creds":
            transcript_lines.append(json.dumps(db.list_credentials(limit=25), indent=2))
        elif command == "notes":
            transcript_lines.append(json.dumps(db.list_artifacts(limit=25), indent=2))
        elif command == "jobs":
            transcript_lines.append(json.dumps(db.list_jobs(limit=10), indent=2))
        elif command.startswith("resource "):
            transcript_lines.append(f"resource script queued: {command.split(' ', 1)[1]}")
        elif command.startswith("workspace "):
            body.workspace = command.split(" ", 1)[1]
            transcript_lines.append(f"switched workspace to {body.workspace}")
        else:
            transcript_lines.append(f"executed synthetic terminal command: {command}")
        transcript = "\n".join(transcript_lines)
        db.upsert_console_session(session_id, title=f"{body.workspace} terminal", workspace=body.workspace, transcript=transcript)
        await _record_event("terminal.command", f"Terminal command executed: {command}", source="terminal", payload=response)
        response["transcript"] = transcript
        return response

    app.include_router(v1)
    return app


def run_server(host: Optional[str] = None, port: Optional[int] = None) -> None:
    try:
        import uvicorn
    except ImportError:
        raise ImportError("uvicorn is required: pip install uvicorn")
    _host = host or config.get("api_host", "0.0.0.0")
    _port = port or int(config.get("api_port", 8000))
    log.info(f"Starting API server on http://{_host}:{_port}")
    app = create_app()
    uvicorn.run(app, host=_host, port=_port, log_level="info")
