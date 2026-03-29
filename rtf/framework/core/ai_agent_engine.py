"""RTF OMEGA-BLACK v6.0 — AI Agent Engine."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import json
from typing import Any, Dict, List
from uuid import uuid4

from framework.db.database import db


@dataclass
class InvestigationStep:
    step_id: str
    module_name: str
    target: str
    rationale: str


class InvestigationAgent:
    def build_plan(self, seed: str) -> List[InvestigationStep]:
        return [
            InvestigationStep(step_id=str(uuid4()), module_name="osint.domain_probe", target=seed, rationale="Baseline enrichment"),
            InvestigationStep(step_id=str(uuid4()), module_name="osint.whois_lookup", target=seed, rationale="Ownership pivot"),
            InvestigationStep(step_id=str(uuid4()), module_name="osint.breach_check", target=seed, rationale="Exposure mapping"),
        ]

    def start(self, workspace_id: str, seed: str, mode: str = "guided", max_depth: int = 3) -> Dict[str, Any]:
        aid = str(uuid4())
        plan = [asdict(s) for s in self.build_plan(seed)]
        db.execute(
            "INSERT INTO agent_sessions (id,workspace_id,mode,seed,seed_type,status,max_depth,plan,started_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (aid, workspace_id, mode, seed, "generic", "running", max_depth, json.dumps(plan), datetime.utcnow().isoformat()),
        )
        return self.status(aid)

    def status(self, agent_id: str) -> Dict[str, Any]:
        row = db.fetchone("SELECT * FROM agent_sessions WHERE id=?", (agent_id,))
        if not row:
            return {"error": "not found"}
        row["plan"] = json.loads(row.get("plan") or "[]")
        return row

    def stop(self, agent_id: str) -> Dict[str, Any]:
        db.execute("UPDATE agent_sessions SET status='stopped',completed_at=? WHERE id=?", (datetime.utcnow().isoformat(), agent_id))
        return self.status(agent_id)


_agent_engine = InvestigationAgent()


def get_ai_agent_engine() -> InvestigationAgent:
    return _agent_engine
