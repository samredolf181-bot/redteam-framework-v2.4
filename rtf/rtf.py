#!/usr/bin/env python3
"""
RedTeam Framework (RTF) v4.0 OMEGA — Main Entry Point

Usage:
  rtf console                    — Interactive operator console (Metasploit-style)
  rtf api [--host H] [--port P]  — Start REST API server
  rtf dashboard [--port P]       — Start web dashboard
  rtf install [--skip-apt] …     — Run the full installer
  rtf module run <path> [opts]   — Run a single module (CLI)
  rtf workflow run <n> [opts]    — Run a workflow (CLI)
  rtf tools list [--installed]   — List registered tools
  rtf tools install <name>       — Install a specific tool
  rtf jobs                       — Show recent jobs
  rtf findings                   — Show recent findings
  rtf report [fmt] [output]      — Generate a report
  rtf version                    — Print version
  rtf titan [manifest|health|schema|investigate] — TITAN distributed architecture tools
  rtf upgrade [analyze|run]           — Generate V4 architecture and upgrade pipeline report
  rtf doctor|fix|validate|repair      — Self-healing diagnostics and repair planning
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from framework.core.config import config
from framework.core.logger import configure_root_logger, get_logger

log = get_logger("rtf.main")

# ── Kali/sudo PATH fix — runs before anything else ───────────────────────────
def _early_path_fix() -> None:
    """Restore user tool paths stripped by sudo before any imports."""
    import os, pwd
    try:
        sudo_user = os.environ.get("SUDO_USER", "")
        home = pwd.getpwnam(sudo_user).pw_dir if sudo_user else str(__import__('pathlib').Path.home())
    except Exception:
        home = os.path.expanduser("~")
    extras = [
        os.path.join(home, "go", "bin"),
        os.path.join(home, ".local", "bin"),
        os.path.join(home, ".cargo", "bin"),
        "/usr/local/go/bin", "/snap/bin",
    ]
    current = os.environ.get("PATH", "").split(":")
    new_parts = [p for p in extras if p not in current and __import__('os').path.isdir(p)]
    if new_parts:
        os.environ["PATH"] = ":".join(new_parts) + ":" + os.environ.get("PATH", "")

_early_path_fix()
VERSION = "4.0.0-omega"


def _init_framework() -> None:
    config.load()
    configure_root_logger(level=config.get("log_level","INFO"), log_file=config.get("log_file"))
    from framework.db.database import db
    db.init(config.get("db_path","data/framework.db"))


# ── Command handlers ──────────────────────────────────────────────────────────

def cmd_console(_args: argparse.Namespace) -> None:
    # Do NOT call _init_framework() here — console.start() handles all init
    # (calling it here causes double DB init and duplicate log lines)
    from framework.core.config import config
    config.load()
    from framework.cli.console import run_console
    run_console()


def cmd_api(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.api.server import run_server
    run_server(host=args.host or None, port=args.port or None)


def cmd_dashboard(args: argparse.Namespace) -> None:
    _init_framework()
    try:
        from framework.dashboard.app import run_dashboard
        run_dashboard(host=args.host or None, port=args.port or None)
    except ImportError:
        print("[ERROR] Flask not installed. Run: pip install flask")
        sys.exit(1)


def cmd_install(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.installer.installer import run_installer
    cats = args.categories.split(",") if args.categories else None
    summary = asyncio.run(run_installer(
        skip_apt=args.skip_apt, skip_go=args.skip_go, skip_rust=args.skip_rust,
        skip_python=args.skip_python, skip_repos=args.skip_repos,
        categories=cats, force=args.force,
    ))
    print(json.dumps(summary, indent=2))


def cmd_module(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.modules.loader import module_loader
    module_loader.load_all()

    if args.module_subcommand == "list":
        mods = module_loader.list_modules(category=args.category or None)
        for m in mods:
            print(f"  {m['path']:45} {m['category']:20} {m['description'][:60]}")

    elif args.module_subcommand == "info":
        cls = module_loader.get(args.path)
        inst = cls()
        print(json.dumps(inst.info(), indent=2))
        for opt in inst.show_options():
            req = "*" if opt["required"] else " "
            print(f"  {req} {opt['name']:22} {opt['description']}")

    elif args.module_subcommand == "run":
        cls = module_loader.get(args.path)
        opts = json.loads(args.options) if args.options else {}
        inst = cls()
        result = asyncio.run(inst.execute(opts))
        print(json.dumps(result.to_dict(), indent=2, default=str))

    elif args.module_subcommand == "search":
        results = module_loader.search(args.query)
        for m in results:
            print(f"  {m['path']:45} {m['category']:20} {m['description'][:60]}")


def cmd_workflow(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.workflows.engine import BUILTIN_WORKFLOWS, get_workflow

    if args.workflow_subcommand == "list":
        for name, cls in BUILTIN_WORKFLOWS.items():
            try:
                desc = cls().description
            except Exception:
                desc = ""
            print(f"  {name:25} {desc}")

    elif args.workflow_subcommand == "run":
        opts = json.loads(args.options) if args.options else {}
        wf = get_workflow(args.name, opts)
        result = asyncio.run(wf.run(output_dir=args.output_dir or None))
        print(json.dumps(result.to_dict(), indent=2, default=str))


def cmd_tools(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.registry.tool_registry import tool_registry, ToolCategory

    if args.tools_subcommand == "list":
        tool_registry.refresh()
        cat = ToolCategory(args.category) if args.category else None
        tools = tool_registry.list_all(category=cat)
        if args.installed:
            tools = [t for t in tools if t.installed]
        elif args.missing:
            tools = [t for t in tools if not t.installed]
        for t in tools:
            status = "✓" if t.installed else "✗"
            print(f"  {status} {t.name:30} {t.category.value:20} {t.description[:50]}")

    elif args.tools_subcommand == "install":
        tool_registry.refresh()
        ok = tool_registry.install(args.name)
        print("OK" if ok else "FAILED")

    elif args.tools_subcommand == "summary":
        tool_registry.refresh()
        print(json.dumps(tool_registry.summary(), indent=2))


def cmd_jobs(_args: argparse.Namespace) -> None:
    _init_framework()
    from framework.db.database import db
    jobs = db.list_jobs(limit=50)
    for j in jobs:
        print(f"  {j['id'][:8]}  {j['name']:30} {j['status']:12} {str(j.get('created_at',''))[:16]}")


def cmd_findings(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.db.database import db
    findings = db.list_findings(severity=args.severity or None, limit=100)
    for f in findings:
        print(f"  [{f.get('severity','info').upper():8}] {f.get('title','')[:60]:60}  {f.get('target','')}")


def cmd_report(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.db.database import db
    from framework.reporting.engine import report_engine, Finding as RF, Severity as RS
    findings_data = db.list_findings(limit=1000)
    findings_objs = [RF(title=f.get("title",""), target=f.get("target",""), severity=RS(f.get("severity","info")), description=f.get("description",""), category=f.get("category","general")) for f in findings_data]
    fmt = args.format or "html"
    out = args.output or f"data/report.{fmt}"
    path = report_engine.generate(title="RTF Engagement Report", findings=findings_objs, format=fmt, output_path=out)
    print(f"Report saved: {path}")


def cmd_titan(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.titan import TitanKnowledgeGraph, TitanOrchestrator, build_titan_manifest
    if args.titan_subcommand == "manifest":
        print(json.dumps(build_titan_manifest(), indent=2))
    elif args.titan_subcommand == "health":
        print(json.dumps(TitanOrchestrator().health(), indent=2))
    elif args.titan_subcommand == "schema":
        print(json.dumps(TitanKnowledgeGraph().schema(), indent=2))
    elif args.titan_subcommand == "investigate":
        seed = json.loads(args.options) if args.options else {}
        result = asyncio.run(TitanOrchestrator().run_investigation(seed))
        print(json.dumps(result, indent=2, default=str))



def cmd_upgrade(args: argparse.Namespace) -> None:
    _init_framework()
    from framework.upgrade import build_v4_upgrade_report
    report = build_v4_upgrade_report()
    if args.upgrade_subcommand == "analyze":
        print(json.dumps({"version": report["version"], "architecture": report["architecture"], "artifacts": report.get("artifacts", {})}, indent=2))
    else:
        print(json.dumps(report, indent=2))



def cmd_doctor(_args: argparse.Namespace) -> None:
    _init_framework()
    from framework.omega import omega_doctor
    print(json.dumps(omega_doctor.diagnose(), indent=2))


def cmd_fix(_args: argparse.Namespace) -> None:
    _init_framework()
    from framework.omega import omega_doctor
    print(json.dumps(omega_doctor.fix(), indent=2))


def cmd_validate(_args: argparse.Namespace) -> None:
    _init_framework()
    from framework.omega import omega_doctor
    print(json.dumps(omega_doctor.validate(), indent=2))


def cmd_repair(_args: argparse.Namespace) -> None:
    _init_framework()
    from framework.omega import omega_doctor
    print(json.dumps(omega_doctor.repair(), indent=2))

def cmd_version(_args: argparse.Namespace) -> None:
    print(f"RedTeam Framework v{VERSION}")
    print("Enterprise RedTeam OMEGA Intelligence Platform")


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rtf", description="RedTeam Framework v2.0 — Enterprise RedTeam Platform")
    subs = parser.add_subparsers(dest="command")

    subs.add_parser("console", help="Start interactive operator console")

    api_p = subs.add_parser("api", help="Start REST API server")
    api_p.add_argument("--host", default="")
    api_p.add_argument("--port", type=int, default=0)

    dash_p = subs.add_parser("dashboard", help="Start web dashboard")
    dash_p.add_argument("--host", default="")
    dash_p.add_argument("--port", type=int, default=0)

    inst_p = subs.add_parser("install", help="Run the full installer")
    inst_p.add_argument("--skip-apt", action="store_true")
    inst_p.add_argument("--skip-go", action="store_true")
    inst_p.add_argument("--skip-rust", action="store_true")
    inst_p.add_argument("--skip-python", action="store_true")
    inst_p.add_argument("--skip-repos", action="store_true")
    inst_p.add_argument("--force", action="store_true", help="Force reinstall")
    inst_p.add_argument("--categories", default="", help="Comma-separated categories to clone")

    mod_p = subs.add_parser("module", help="Module management")
    mod_subs = mod_p.add_subparsers(dest="module_subcommand")
    ml = mod_subs.add_parser("list"); ml.add_argument("--category", default="")
    mi = mod_subs.add_parser("info"); mi.add_argument("path")
    mr = mod_subs.add_parser("run"); mr.add_argument("path"); mr.add_argument("--options", default="")
    ms = mod_subs.add_parser("search"); ms.add_argument("query")

    wf_p = subs.add_parser("workflow", help="Workflow management")
    wf_subs = wf_p.add_subparsers(dest="workflow_subcommand")
    wf_subs.add_parser("list")
    wfr = wf_subs.add_parser("run"); wfr.add_argument("name"); wfr.add_argument("--options", default=""); wfr.add_argument("--output-dir", default="", dest="output_dir")

    tools_p = subs.add_parser("tools", help="Tool registry")
    tools_subs = tools_p.add_subparsers(dest="tools_subcommand")
    tl = tools_subs.add_parser("list"); tl.add_argument("--installed", action="store_true"); tl.add_argument("--missing", action="store_true"); tl.add_argument("--category", default="")
    tools_subs.add_parser("summary")
    ti = tools_subs.add_parser("install"); ti.add_argument("name")

    subs.add_parser("jobs", help="List recent jobs")

    fp = subs.add_parser("findings", help="List findings")
    fp.add_argument("--severity", default="")

    rp = subs.add_parser("report", help="Generate report")
    rp.add_argument("--format", default="html", choices=["html","pdf","xlsx","md","json"])
    rp.add_argument("--output", default="")

    titan_p = subs.add_parser("titan", help="RTF TITAN distributed architecture tools")
    titan_subs = titan_p.add_subparsers(dest="titan_subcommand")
    titan_subs.add_parser("manifest")
    titan_subs.add_parser("health")
    titan_subs.add_parser("schema")
    ti = titan_subs.add_parser("investigate")
    ti.add_argument("--options", default="{}")

    upgrade_p = subs.add_parser("upgrade", help="Generate V4 architecture and upgrade reports")
    upgrade_subs = upgrade_p.add_subparsers(dest="upgrade_subcommand")
    upgrade_subs.add_parser("analyze")
    upgrade_subs.add_parser("run")

    subs.add_parser("doctor", help="Run framework diagnostics")
    subs.add_parser("fix", help="Generate a non-destructive fix plan")
    subs.add_parser("validate", help="Validate Omega architecture state")
    subs.add_parser("repair", help="Generate a repair plan for degraded components")
    subs.add_parser("version")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "console": cmd_console, "api": cmd_api, "dashboard": cmd_dashboard,
        "install": cmd_install, "module": cmd_module, "workflow": cmd_workflow,
        "tools": cmd_tools, "jobs": cmd_jobs, "findings": cmd_findings,
        "report": cmd_report, "titan": cmd_titan, "upgrade": cmd_upgrade,
        "doctor": cmd_doctor, "fix": cmd_fix, "validate": cmd_validate, "repair": cmd_repair,
        "version": cmd_version,
    }
    if not args.command:
        parser.print_help(); sys.exit(0)
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
