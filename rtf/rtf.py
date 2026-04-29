#!/usr/bin/env python3
"""
RedTeam Framework (RTF) v2.0 — Main Entry Point

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
  
  MASSIVE AUTOMATIC INVESTIGATION PIPELINE:
  rtf investigate -u "username" -d "domain" -p "phone" --active-investigation -o ~/results
  rtf investigate --target "example.com" --comprehensive -o ./output
  rtf investigate --email "user@example.com" --full-stack -o ./results
  rtf investigate -d "target.com" --ai-autonomous -o ./ai_results
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
VERSION = "2.0.0"


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


def cmd_version(_args: argparse.Namespace) -> None:
    print(f"RedTeam Framework v{VERSION}")
    print("Enterprise RedTeam Platform — For Authorized Testing Only")


def cmd_investigate(args: argparse.Namespace) -> None:
    """Run the massive automatic investigation pipeline."""
    _init_framework()
    
    # Import investigation module
    from investigate import MassiveInvestigationPipeline, run_investigation
    
    # Build targets dictionary
    targets = {}
    if args.username:
        targets["username"] = args.username
    if args.domain:
        targets["domain"] = args.domain
    if args.email:
        targets["email"] = args.email
    if args.phone:
        targets["phone"] = args.phone
    if args.ip:
        targets["ip"] = args.ip
    if args.url:
        targets["url"] = args.url
    
    if not targets:
        print("[ERROR] No targets specified. Use -u, -d, -e, -p, -i, --url, or --target")
        sys.exit(1)
    
    # Determine profile
    profile = args.profile
    if args.comprehensive:
        profile = "comprehensive"
    elif args.full_stack or args.active_investigation:
        profile = "aggressive"
    elif args.passive_only:
        profile = "core"
    elif args.ai_autonomous:
        profile = "ai_autonomous"
    
    # Configure options
    options = {
        "enable_credential_attacks": args.enable_credential_attacks,
        "enable_exploitation": args.enable_exploitation,
    }
    
    # Run investigation
    asyncio.run(run_investigation(args))


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

    subs.add_parser("version")
    
    # Investigation command (massive automatic pipeline)
    inv_p = subs.add_parser("investigate", help="Run massive automatic investigation pipeline")
    inv_p.add_argument("-u", "--username", default="", help="Username to investigate")
    inv_p.add_argument("-d", "--domain", default="", help="Domain to investigate")
    inv_p.add_argument("-e", "--email", default="", help="Email address to investigate")
    inv_p.add_argument("-p", "--phone", default="", help="Phone number to investigate")
    inv_p.add_argument("-i", "--ip", default="", help="IP address to investigate")
    inv_p.add_argument("--url", default="", help="URL to investigate")
    inv_p.add_argument("--target", default="", help="Generic target (will auto-detect type)")
    inv_p.add_argument("--comprehensive", action="store_true", help="Run comprehensive investigation")
    inv_p.add_argument("--full-stack", action="store_true", help="Run full-stack investigation")
    inv_p.add_argument("--active-investigation", action="store_true", help="Enable active scanning")
    inv_p.add_argument("--passive-only", action="store_true", help="Run only passive recon")
    inv_p.add_argument("--ai-autonomous", action="store_true", help="Use AI autonomous agent")
    inv_p.add_argument("-o", "--output", default="./investigation_results", help="Output directory")
    inv_p.add_argument("--no-reports", action="store_true", help="Disable report generation")
    inv_p.add_argument("--no-save-raw", action="store_true", help="Disable saving raw output")
    inv_p.add_argument("--sequential", action="store_true", help="Run tools sequentially")
    inv_p.add_argument("--max-concurrency", type=int, default=10, help="Max concurrent executions")
    inv_p.add_argument("--enable-credential-attacks", action="store_true", help="Enable credential attacks")
    inv_p.add_argument("--enable-exploitation", action="store_true", help="Enable exploitation")
    inv_p.add_argument("--skip-installed-check", action="store_true", help="Skip tool install check")
    inv_p.add_argument("--profile", default="comprehensive", choices=["core", "comprehensive", "full", "aggressive", "ai_autonomous"], help="Investigation profile")
    
    return parser


def dispatch():
    """Dispatch table for commands."""
    return {
        "console": cmd_console, "api": cmd_api, "dashboard": cmd_dashboard,
        "install": cmd_install, "module": cmd_module, "workflow": cmd_workflow,
        "tools": cmd_tools, "jobs": cmd_jobs, "findings": cmd_findings,
        "report": cmd_report, "version": cmd_version, "investigate": cmd_investigate,
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch_table = {
        "console": cmd_console, "api": cmd_api, "dashboard": cmd_dashboard,
        "install": cmd_install, "module": cmd_module, "workflow": cmd_workflow,
        "tools": cmd_tools, "jobs": cmd_jobs, "findings": cmd_findings,
        "report": cmd_report, "version": cmd_version, "investigate": cmd_investigate,
    }
    if not args.command:
        parser.print_help(); sys.exit(0)
    fn = dispatch_table.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
