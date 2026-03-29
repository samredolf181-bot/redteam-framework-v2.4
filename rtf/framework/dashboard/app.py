"""RedTeam Framework v2.0 - Web Dashboard"""
from __future__ import annotations
import json
from typing import Any, Dict

try:
    from flask import Flask, render_template_string, jsonify
    _HAS_FLASK = True
except ImportError:
    _HAS_FLASK = False

from framework.core.config import config
from framework.core.logger import get_logger
from framework.db.database import db
from framework.modules.loader import module_loader
from framework.registry.tool_registry import tool_registry
from framework.titan import TitanOrchestrator, build_titan_manifest
from framework.workflows.engine import BUILTIN_WORKFLOWS

log = get_logger("rtf.dashboard")

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RTF Dashboard v4.0 OMEGA</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{background:#0a0a0a;color:#e0e0e0;font-family:'Courier New',monospace;}</style>
</head><body>
<nav style="background:#111;border-bottom:3px solid #dc2626;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;">
  <div style="display:flex;align-items:center;gap:12px;">
    <span style="color:#dc2626;font-size:24px;font-weight:bold;">⚔</span>
    <span style="color:#dc2626;font-weight:bold;font-size:16px;letter-spacing:3px;">REDTEAM FRAMEWORK v4.0 OMEGA</span>
  </div>
  <div style="font-size:12px;color:#4cc9f0;">API: http://{{ api_host }}:{{ api_port }}</div>
</nav>
<div style="max-width:1300px;margin:0 auto;padding:24px;">
  <section style="margin-bottom:32px;">
    <h2 style="color:#dc2626;font-size:18px;margin-bottom:16px;">System Overview</h2>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
      {% for card in stats_cards %}
      <div style="background:#111;border:1px solid #333;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:32px;font-weight:bold;color:#dc2626;">{{ card.value }}</div>
        <div style="font-size:11px;color:#888;margin-top:4px;">{{ card.label }}</div>
      </div>{% endfor %}
    </div>
  </section>
  <section style="margin-bottom:32px;display:grid;grid-template-columns:1.3fr 1fr;gap:24px;">
    <div style="background:#111;border:1px solid #333;border-radius:8px;padding:20px;">
      <h3 style="color:#dc2626;margin-bottom:12px;">OMEGA Architecture Map</h3>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;font-size:12px;">
        {% for service in manifest.services %}
        <div style="background:#0f0f0f;border:1px solid #222;border-radius:6px;padding:12px;">
          <div style="color:#4cc9f0;font-weight:bold;">{{ service.name }}</div>
          <div style="color:#aaa;margin-top:6px;">{{ service.purpose }}</div>
          <div style="color:#666;margin-top:8px;">Pipelines: {{ service.pipelines|join(', ') }}</div>
        </div>{% endfor %}
      </div>
    </div>
    <div style="display:grid;grid-template-rows:1fr 1fr;gap:24px;">
      <div style="background:#111;border:1px solid #333;border-radius:8px;padding:20px;">
        <h3 style="color:#dc2626;margin-bottom:12px;">Tools by Category</h3>
        <canvas id="toolsChart" height="220"></canvas>
      </div>
      <div style="background:#111;border:1px solid #333;border-radius:8px;padding:20px;">
        <h3 style="color:#dc2626;margin-bottom:12px;">Installation Status</h3>
        <canvas id="installChart" height="220"></canvas>
      </div>
    </div>
  </section>
  <section style="margin-bottom:32px;display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div style="background:#111;border:1px solid #333;border-radius:8px;padding:20px;">
      <h2 style="color:#dc2626;font-size:18px;margin-bottom:16px;">Distributed Queue Topics</h2>
      {% for topic, depth in titan_health.queue_topics.items() %}
      <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1a1a1a;font-size:12px;">
        <span style="color:#4cc9f0;">{{ topic }}</span>
        <span style="color:#16a34a;">{{ depth }}</span>
      </div>{% else %}
      <div style="color:#666;font-size:12px;">No active queue backlog.</div>{% endfor %}
    </div>
    <div style="background:#111;border:1px solid #333;border-radius:8px;padding:20px;">
      <h2 style="color:#dc2626;font-size:18px;margin-bottom:16px;">SOCMINT 15-Stage Coverage</h2>
      {% for stage in socmint_stages %}
      <div style="display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid #1a1a1a;font-size:12px;">
        <span style="color:#4cc9f0;">{{ stage.code }}</span>
        <span style="flex:1;color:#ccc;">{{ stage.name }}</span>
        <span style="color:#16a34a;">READY</span>
      </div>{% endfor %}
    </div>
  </section>
  <section style="margin-bottom:32px;">
    <h2 style="color:#dc2626;font-size:18px;margin-bottom:16px;">RTF TITAN Service Health</h2>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
      {% for svc in titan_health.services %}
      <div style="background:#111;border:1px solid #333;border-radius:8px;padding:14px;">
        <div style="color:#4cc9f0;font-weight:bold;">{{ svc.name }}</div>
        <div style="color:#16a34a;font-size:11px;margin-top:4px;">{{ svc.status|upper }}</div>
        <div style="color:#888;font-size:11px;margin-top:6px;">Queue depth: {{ svc.queue_depth }}</div>
      </div>{% endfor %}
    </div>
  </section>
  <section style="margin-bottom:32px;">
    <h2 style="color:#dc2626;font-size:18px;margin-bottom:16px;">Modules ({{ modules|length }})</h2>
    <div style="overflow-x:auto;">
      <table style="width:100%;font-size:12px;border-collapse:collapse;">
        <thead><tr style="border-bottom:1px solid #333;color:#888;"><th style="text-align:left;padding:8px;">Path</th><th style="text-align:left;padding:8px;">Category</th><th style="text-align:left;padding:8px;">Description</th></tr></thead>
        <tbody>{% for m in modules[:25] %}
          <tr style="border-bottom:1px solid #1a1a1a;"><td style="padding:8px;color:#4cc9f0;font-weight:bold;">{{ m.path }}</td><td style="padding:8px;">{{ m.category }}</td><td style="padding:8px;color:#888;font-size:11px;">{{ m.description[:80] }}</td></tr>
        {% endfor %}</tbody>
      </table>
    </div>
  </section>
</div>
<script>
const toolData={{ tool_chart_data|tojson }};
new Chart(document.getElementById('toolsChart'),{type:'bar',data:{labels:toolData.labels,datasets:[{label:'Total',data:toolData.total,backgroundColor:'#374151'},{label:'Installed',data:toolData.installed,backgroundColor:'#dc2626'}]},options:{responsive:true,plugins:{legend:{labels:{color:'#9ca3af'}}},scales:{x:{ticks:{color:'#9ca3af'},grid:{color:'#1f2937'}},y:{ticks:{color:'#9ca3af'},grid:{color:'#1f2937'}}}}});
const instData={{ install_chart_data|tojson }};
new Chart(document.getElementById('installChart'),{type:'doughnut',data:{labels:['Installed','Missing'],datasets:[{data:[instData.installed,instData.missing],backgroundColor:['#16a34a','#dc2626'],borderColor:'#111'}]},options:{responsive:true,plugins:{legend:{labels:{color:'#9ca3af'}}}}});
</script>
</body></html>"""

def create_dashboard() -> "Flask":
    if not _HAS_FLASK:
        raise ImportError("flask is required: pip install flask")
    app = Flask(__name__)
    titan = TitanOrchestrator()
    db.init(config.get("db_path","data/framework.db"))
    tool_registry.refresh(); module_loader.load_all()

    @app.route("/")
    def index():
        modules = module_loader.list_modules()
        tools = [t.to_dict() for t in tool_registry.list_all()]
        findings = db.list_findings(limit=200)
        tool_summary = tool_registry.summary()
        titan_health = titan.health()
        manifest = build_titan_manifest()
        stats_cards = [
            {"label":"Modules Loaded","value":len(modules)},
            {"label":"Tools Registered","value":len(tools)},
            {"label":"Tools Installed","value":sum(1 for t in tools if t["installed"])},
            {"label":"TITAN Services","value":titan_health["service_count"]},
        ]
        by_cat = tool_summary.get("by_category",{})
        tool_chart_data = {"labels":list(by_cat.keys()),"total":[v["total"] for v in by_cat.values()],"installed":[v["installed"] for v in by_cat.values()]}
        install_chart_data = {"installed":tool_summary.get("installed",0),"missing":tool_summary.get("missing",0)}
        socmint_stages = titan.pipeline.run({"username": "demo"})["stages"]
        return render_template_string(_TEMPLATE, modules=modules, findings=findings, workflows=BUILTIN_WORKFLOWS, stats_cards=stats_cards, tool_chart_data=tool_chart_data, install_chart_data=install_chart_data, titan_health=titan_health, api_host=config.get("api_host","localhost"), api_port=config.get("api_port",8000), manifest=manifest, socmint_stages=socmint_stages)

    @app.route("/api/jobs")
    def api_jobs(): return jsonify(db.list_jobs(limit=50))

    @app.route("/api/findings")
    def api_findings(): return jsonify(db.list_findings(limit=200))

    @app.route("/api/omega/manifest")
    def api_manifest(): return jsonify(build_titan_manifest())


    @app.route("/api/v1/workspaces", methods=["GET"])
    def list_workspaces():
        from flask import request
        from framework.core.workspace_manager import get_workspace_manager
        return jsonify(get_workspace_manager().list(status=request.args.get("status")))

    @app.route("/api/v1/workspaces", methods=["POST"])
    def create_workspace():
        from flask import request
        from framework.core.workspace_manager import get_workspace_manager
        return jsonify(get_workspace_manager().create(request.get_json(silent=True) or {}))

    @app.route("/api/v1/workspaces/<wid>", methods=["GET", "PUT", "DELETE"])
    def workspace_item(wid: str):
        from flask import request
        from framework.core.workspace_manager import get_workspace_manager
        wm = get_workspace_manager()
        if request.method == "GET":
            item = wm.get(wid)
            return (jsonify(item), 404) if not item else jsonify(item)
        if request.method == "PUT":
            item = wm.update(wid, request.get_json(silent=True) or {})
            return (jsonify({"error": "not found"}), 404) if not item else jsonify(item)
        return jsonify({"archived": wm.archive(wid)})

    @app.route("/api/v1/workspaces/<wid>/export", methods=["POST"])
    def export_workspace(wid: str):
        from flask import Response
        from framework.core.workspace_manager import get_workspace_manager
        payload = get_workspace_manager().export_zip(wid)
        return Response(payload, mimetype="application/zip", headers={"Content-Disposition": f"attachment; filename={wid}.zip"})

    @app.route("/api/v1/evidence", methods=["GET", "POST"])
    def evidence_collection():
        from flask import request
        from framework.core.evidence_vault import get_evidence_vault
        ev = get_evidence_vault()
        if request.method == "GET":
            return jsonify(ev.list(workspace_id=request.args.get("workspace_id")))
        data = request.get_json(silent=True) or {}
        if data.get("type") == "url_snapshot":
            return jsonify(ev.add_url_snapshot(data["workspace_id"], data["url"], data))
        return jsonify(ev.add_file(data["workspace_id"], data["file_path"], data))

    @app.route("/api/v1/evidence/<eid>", methods=["GET", "DELETE"])
    def evidence_item(eid: str):
        from framework.core.evidence_vault import get_evidence_vault
        item = get_evidence_vault().get(eid)
        return (jsonify(item), 404) if not item else jsonify(item)

    @app.route("/api/v1/evidence/<eid>/hash_verify", methods=["POST"])
    def verify_evidence(eid: str):
        from framework.core.evidence_vault import get_evidence_vault
        return jsonify(get_evidence_vault().verify_integrity(eid))

    @app.route("/api/v1/evidence/<eid>/chain")
    def evidence_chain(eid: str):
        from framework.core.evidence_vault import get_evidence_vault
        return jsonify(get_evidence_vault().get_chain(eid))

    @app.route("/api/v1/timeline", methods=["GET"])
    def timeline_all():
        from flask import request
        from framework.core.timeline_engine import get_timeline_engine
        return jsonify(get_timeline_engine().get_timeline(workspace_id=request.args.get("workspace_id"), entity=request.args.get("entity")))

    @app.route("/api/v1/timeline/events", methods=["POST"])
    def timeline_add():
        from flask import request
        from framework.core.timeline_engine import get_timeline_engine
        data = request.get_json(silent=True) or {}
        return jsonify(get_timeline_engine().add_event(data["workspace_id"], data))

    @app.route("/api/v1/timeline/export")
    def timeline_export():
        from flask import request
        from framework.core.timeline_engine import get_timeline_engine
        fmt = request.args.get("format", "json")
        wid = request.args.get("workspace_id")
        if fmt == "csv":
            return app.response_class(get_timeline_engine().export_csv(wid), mimetype="text/csv")
        return jsonify(get_timeline_engine().export_json(wid))

    @app.route("/api/v1/agents/investigate", methods=["POST"])
    def agents_start():
        from flask import request
        from framework.core.ai_agent_engine import get_ai_agent_engine
        data = request.get_json(silent=True) or {}
        return jsonify(get_ai_agent_engine().start(data["workspace_id"], data["seed"], data.get("mode", "guided"), int(data.get("max_depth", 3))))

    @app.route("/api/v1/agents/<aid>/status")
    def agents_status(aid: str):
        from framework.core.ai_agent_engine import get_ai_agent_engine
        return jsonify(get_ai_agent_engine().status(aid))

    @app.route("/api/v1/agents/<aid>/stop", methods=["POST"])
    def agents_stop(aid: str):
        from framework.core.ai_agent_engine import get_ai_agent_engine
        return jsonify(get_ai_agent_engine().stop(aid))

    @app.route("/api/v1/agents", methods=["GET"])
    def agents_list():
        return jsonify(db.fetchall("SELECT * FROM agent_sessions ORDER BY started_at DESC"))

    @app.route("/api/v1/dossiers", methods=["GET", "POST"])
    def dossiers_collection():
        from flask import request
        from framework.core.dossier_engine import get_dossier_engine
        if request.method == "GET":
            return jsonify(db.fetchall("SELECT * FROM dossiers ORDER BY generated_at DESC"))
        data = request.get_json(silent=True) or {}
        return jsonify(get_dossier_engine().generate(data["workspace_id"], data.get("type", "brief"), data.get("title", "Intelligence Brief"), data.get("format", "html"), data.get("classification", "CONFIDENTIAL")))

    @app.route("/api/v1/plugins", methods=["GET"])
    def plugins_list():
        from framework.core.plugin_system import get_plugin_registry
        reg = get_plugin_registry(); reg.scan_plugins()
        return jsonify(reg.list_plugins())

    @app.route("/api/v1/plugins/install", methods=["POST"])
    def plugins_install():
        from flask import request
        from framework.core.plugin_system import get_plugin_registry
        data = request.get_json(silent=True) or {}
        return jsonify(get_plugin_registry().install_plugin(data["source"]))

    return app

def run_dashboard(host=None, port=None):
    _host=host or config.get("dashboard_host","0.0.0.0")
    _port=port or int(config.get("dashboard_port",5000))
    log.info(f"Starting dashboard on http://{_host}:{_port}")
    app=create_dashboard()
    app.run(host=_host, port=_port, debug=False)
