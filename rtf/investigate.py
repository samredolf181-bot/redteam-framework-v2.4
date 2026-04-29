#!/usr/bin/env python3
"""
RTF v2.0 - Massive Automatic Investigation Pipeline
Unified entry point for full-spectrum investigations combining ALL modules, tools, workflows, and pipelines.

Usage:
    python3 rtf.py --investigate -u "username" -d "domain" -p "phone" --active-investigation -o ~/results
    python3 rtf.py --investigate --target "example.com" --comprehensive -o ./output
    python3 rtf.py --investigate --email "user@example.com" --full-stack -o ./results
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Add framework to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from framework.core.config import config
from framework.core.logger import configure_root_logger, get_logger
from framework.db.database import db
from framework.modules.loader import module_loader
from framework.registry.tool_registry import tool_registry
from framework.workflows.engine import BUILTIN_WORKFLOWS, get_workflow, WorkflowResult
from framework.reporting.engine import report_engine, Finding as RF, Severity as RS
from framework.correlation.identity_graph import IdentityGraph
from framework.graph.graph_builder import GraphBuilder
from framework.ai.autonomous_agent import AutonomousAgent
from framework.ai.decision_engine import DecisionEngine
from framework.automation.advanced_pipeline import AdvancedPipeline, AdvancedStep, AdvancedPipelineResult
from framework.automation.pipeline_v2 import PipelineEngineV2, PipelineStepV2, PipelineResultV2

log = get_logger("rtf.investigation")

VERSION = "2.0.0"


# =============================================================================
# COMPREHENSIVE INVESTIGATION RESULT
# =============================================================================

@dataclass
class InvestigationResult:
    """Comprehensive result from the massive investigation pipeline."""
    investigation_id: str
    started_at: str
    finished_at: str
    duration_seconds: float
    targets: Dict[str, str]
    profile: str
    success: bool
    
    # Stage results
    recon_results: Dict[str, Any] = field(default_factory=dict)
    osint_results: Dict[str, Any] = field(default_factory=dict)
    scanning_results: Dict[str, Any] = field(default_factory=dict)
    exploitation_results: Dict[str, Any] = field(default_factory=dict)
    post_exploit_results: Dict[str, Any] = field(default_factory=dict)
    threat_intel_results: Dict[str, Any] = field(default_factory=dict)
    ai_analysis_results: Dict[str, Any] = field(default_factory=dict)
    
    # Aggregated data
    findings: List[Dict[str, Any]] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    attack_paths: List[Dict[str, Any]] = field(default_factory=list)
    credentials_found: List[Dict[str, Any]] = field(default_factory=list)
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=dict)
    open_ports: List[Dict[str, Any]] = field(default_factory=list)
    subdomains: List[str] = field(default_factory=list)
    urls_discovered: List[str] = field(default_factory=list)
    social_accounts: List[Dict[str, Any]] = field(default_factory=dict)
    breaches: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool execution stats
    tools_executed: int = 0
    tools_successful: int = 0
    tools_failed: int = 0
    workflows_run: List[str] = field(default_factory=list)
    pipelines_executed: List[str] = field(default_factory=list)
    
    # Output files
    report_files: List[str] = field(default_factory=list)
    raw_data_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": round(self.duration_seconds, 2),
            "targets": self.targets,
            "profile": self.profile,
            "success": self.success,
            "summary": {
                "tools_executed": self.tools_executed,
                "tools_successful": self.tools_successful,
                "tools_failed": self.tools_failed,
                "total_findings": len(self.findings),
                "workflows_run": self.workflows_run,
                "pipelines_executed": self.pipelines_executed,
            },
            "recon": self.recon_results,
            "osint": self.osint_results,
            "scanning": self.scanning_results,
            "exploitation": self.exploitation_results,
            "post_exploitation": self.post_exploit_results,
            "threat_intelligence": self.threat_intel_results,
            "ai_analysis": self.ai_analysis_results,
            "findings": self.findings,
            "entities": self.entities,
            "attack_paths": self.attack_paths,
            "report_files": self.report_files,
        }


# =============================================================================
# MASSIVE AUTOMATIC INVESTIGATION PIPELINE
# =============================================================================

class MassiveInvestigationPipeline:
    """
    The ultimate unified investigation framework that combines ALL modules,
    tools, workflows, and pipelines into one massive automatic execution engine.
    
    This orchestrates:
    - All reconnaissance tools (subfinder, amass, naabu, httpx, etc.)
    - All OSINT modules (sherlock, maigret, holehe, phoneinfoga, etc.)
    - All scanning tools (nuclei, trivy, lynis, etc.)
    - All web exploitation tools (sqlmap, dalfox, wpscan, etc.)
    - All credential attack tools (hydra, kerbrute, hashcat, etc.)
    - All exploitation frameworks (metasploit, autosploit, etc.)
    - All post-exploitation tools (bloodhound, linenum, etc.)
    - All threat intelligence tools (intelowl, threatingestor, etc.)
    - All AI analysis modules (anomaly detection, attack path generation, etc.)
    - All built-in workflows
    - All automation pipelines
    """
    
    # Complete tool inventory by category
    RECON_TOOLS = [
        "subfinder", "amass", "assetfinder", "altdns", "httprobe",
        "naabu", "masscan", "nmap", "gobuster", "dirsearch", "ffuf",
        "whatweb", "wappalyzer", "techstack", "nuclei", "httpx"
    ]
    
    OSINT_TOOLS = [
        "sherlock", "maigret", "holehe", "phoneinfoga", "osintgram",
        "social-analyzer", "profil3r", "intelligence-x", "spiderfoot",
        "theharvester", "recon-ng", "maltego"
    ]
    
    SCANNING_TOOLS = [
        "nuclei", "trivy", "lynis", "openvas", "vuls", "nikto",
        "zap", "burp", "sslscan", "testssl", "kubescape"
    ]
    
    WEB_EXPLOIT_TOOLS = [
        "sqlmap", "dalfox", "xsstrike", "wpscan", "joomscan",
        "droopescan", "wfuzz", "commix", "ssrfmap", "nosqlmap"
    ]
    
    CREDENTIAL_TOOLS = [
        "hydra", "kerbrute", "hashcat", "john", "ncrack", "brutespray"
    ]
    
    EXPLOIT_TOOLS = [
        "metasploit", "autosploit", "kubesploit", "owtf", "astra"
    ]
    
    POST_EXPLOIT_TOOLS = [
        "bloodhound", "linenum", "evil-winrm", "winpwn", "mimikatz"
    ]
    
    THREAT_INTEL_TOOLS = [
        "intelowl", "threatingestor", "ail-framework", "misp"
    ]
    
    AI_TOOLS = [
        "pentestgpt", "claude", "anomaly_detection", "attack_path_generator"
    ]
    
    def __init__(
        self,
        output_dir: str = "./investigation_results",
        profile: str = "comprehensive",
        parallel: bool = True,
        max_concurrency: int = 10,
        skip_installed_check: bool = False,
        save_raw: bool = True,
        generate_reports: bool = True,
        interactive: bool = False,
    ):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.profile = profile
        self.parallel = parallel
        self.max_concurrency = max_concurrency
        self.skip_installed_check = skip_installed_check
        self.save_raw = save_raw
        self.generate_reports = generate_reports
        self.interactive = interactive
        
        self.investigation_id = str(uuid.uuid4())[:8]
        self.result = InvestigationResult(
            investigation_id=self.investigation_id,
            started_at=datetime.utcnow().isoformat(),
            finished_at="",
            duration_seconds=0.0,
            targets={},
            profile=profile,
            success=False,
        )
        
        # Initialize components
        self.entity_graph = IdentityGraph()
        self.graph_builder = GraphBuilder()
        self.decision_engine = DecisionEngine()
        self.autonomous_agent = AutonomousAgent() if profile == "ai_autonomous" else None
        
        # Tool wrappers cache
        self._wrappers_cache: Dict[str, Any] = {}
        
        log.info(f"Initialized MassiveInvestigationPipeline [ID: {self.investigation_id}]")
        log.info(f"Output directory: {self.output_dir}")
        log.info(f"Profile: {profile} | Parallel: {parallel} | Concurrency: {max_concurrency}")
    
    def _get_wrapper(self, tool_name: str):
        """Lazy-load tool wrappers."""
        if tool_name in self._wrappers_cache:
            return self._wrappers_cache[tool_name]
        
        try:
            # Try framework modules first
            if tool_name in ["subfinder", "amass", "naabu", "httpx", "gobuster", "ffuf", "whatweb"]:
                module = __import__(f"modules.recon.{tool_name}_wrapper", fromlist=[tool_name.title() + "Wrapper"])
                wrapper_class = getattr(module, tool_name.title() + "Wrapper")
                wrapper = wrapper_class()
            elif tool_name in ["sherlock", "maigret", "holehe", "phoneinfoga"]:
                module = __import__(f"modules.osint.{tool_name}_wrapper", fromlist=[tool_name.title() + "Wrapper"])
                wrapper_class = getattr(module, tool_name.title() + "Wrapper")
                wrapper = wrapper_class()
            elif tool_name in ["nuclei", "trivy", "lynis"]:
                module = __import__(f"modules.scanning.{tool_name}_wrapper", fromlist=[tool_name.title() + "Wrapper"])
                wrapper_class = getattr(module, tool_name.title() + "Wrapper")
                wrapper = wrapper_class()
            elif tool_name in ["sqlmap", "dalfox", "wpscan"]:
                module = __import__(f"modules.web_exploitation.{tool_name}_wrapper", fromlist=[tool_name.title() + "Wrapper"])
                wrapper_class = getattr(module, tool_name.title() + "Wrapper")
                wrapper = wrapper_class()
            elif tool_name in ["hydra", "kerbrute", "hashcat", "john"]:
                module = __import__(f"modules.credential_attacks.{tool_name}_wrapper", fromlist=[tool_name.title() + "Wrapper"])
                wrapper_class = getattr(module, tool_name.title() + "Wrapper")
                wrapper = wrapper_class()
            elif tool_name in ["metasploit", "bloodhound"]:
                module = __import__(f"modules.exploitation_frameworks.{tool_name}_wrapper", fromlist=[tool_name.title() + "Wrapper"])
                wrapper_class = getattr(module, tool_name.title() + "Wrapper")
                wrapper = wrapper_class()
            else:
                return None
            
            self._wrappers_cache[tool_name] = wrapper
            return wrapper
        except Exception as e:
            log.debug(f"Could not load wrapper for {tool_name}: {e}")
            return None
    
    async def run(self, targets: Dict[str, str], options: Optional[Dict[str, Any]] = None) -> InvestigationResult:
        """
        Execute the complete massive investigation pipeline.
        
        Args:
            targets: Dictionary with target identifiers
                     {"domain": "...", "username": "...", "email": "...", 
                      "ip": "...", "phone": "...", "url": "..."}
            options: Additional configuration options
        
        Returns:
            InvestigationResult with all findings
        """
        start_time = time.monotonic()
        self.result.targets = targets
        
        log.info("=" * 70)
        log.info(f"MASSIVE AUTOMATIC INVESTIGATION PIPELINE")
        log.info(f"Investigation ID: {self.investigation_id}")
        log.info(f"Targets: {json.dumps(targets, indent=2)}")
        log.info(f"Profile: {self.profile}")
        log.info("=" * 70)
        
        options = options or {}
        
        try:
            # PHASE 1: Initialize entity graph and normalize targets
            await self._phase1_init(targets)
            
            # PHASE 2: Comprehensive Reconnaissance (ALL recon tools)
            await self._phase2_recon(targets, options)
            
            # PHASE 3: OSINT Investigation (ALL OSINT tools)
            await self._phase3_osint(targets, options)
            
            # PHASE 4: Vulnerability Scanning (ALL scanners)
            await self._phase4_scanning(targets, options)
            
            # PHASE 5: Web Exploitation Analysis
            await self._phase5_web_exploit(targets, options)
            
            # PHASE 6: Credential Attack Simulation
            await self._phase6_credentials(targets, options)
            
            # PHASE 7: Exploitation Framework Execution
            await self._phase7_exploitation(targets, options)
            
            # PHASE 8: Post-Exploitation Analysis
            await self._phase8_post_exploit(targets, options)
            
            # PHASE 9: Threat Intelligence Enrichment
            await self._phase9_threat_intel(targets, options)
            
            # PHASE 10: AI Analysis & Attack Path Generation
            await self._phase10_ai_analysis(targets, options)
            
            # PHASE 11: Run All Built-in Workflows
            await self._phase11_workflows(targets, options)
            
            # PHASE 12: Execute Automation Pipelines
            await self._phase12_pipelines(targets, options)
            
            # PHASE 13: Correlation & Entity Graph Finalization
            await self._phase13_correlation()
            
            # PHASE 14: Generate Reports
            await self._phase14_reporting()
            
            self.result.success = True
            
        except Exception as e:
            log.error(f"Pipeline execution error: {e}")
            self.result.success = False
            raise
        
        finally:
            self.result.finished_at = datetime.utcnow().isoformat()
            self.result.duration_seconds = round(time.monotonic() - start_time, 2)
            
            log.info("=" * 70)
            log.info(f"INVESTIGATION COMPLETE")
            log.info(f"Duration: {self.result.duration_seconds}s")
            log.info(f"Tools executed: {self.result.tools_executed} ({self.result.tools_successful} OK, {self.result.tools_failed} failed)")
            log.info(f"Total findings: {len(self.result.findings)}")
            log.info(f"Reports generated: {len(self.result.report_files)}")
            log.info("=" * 70)
        
        return self.result
    
    async def _phase1_init(self, targets: Dict[str, str]):
        """Phase 1: Initialize entity graph with all targets."""
        log.info("\n[PHASE 1] Initializing entity graph...")
        
        type_mapping = {
            "domain": "DOMAIN",
            "ip": "IP_ADDRESS",
            "email": "EMAIL",
            "username": "USERNAME",
            "phone": "PHONE",
            "url": "URL",
            "company": "ORGANIZATION",
        }
        
        for key, value in targets.items():
            if value:
                entity_type = type_mapping.get(key.lower(), "OTHER")
                self.entity_graph.add_entity(
                    entity_type=entity_type,
                    identifier=value,
                    source="seed_target",
                    confidence=1.0
                )
                if entity_type not in self.result.entities:
                    self.result.entities[entity_type] = []
                self.result.entities[entity_type].append(value)
                
                log.info(f"  Added {entity_type}: {value}")
        
        log.info(f"  Entity graph initialized with {sum(len(v) for v in self.result.entities.values())} entities")
    
    async def _phase2_recon(self, targets: Dict[str, str], options: Dict):
        """Phase 2: Execute ALL reconnaissance tools."""
        log.info("\n[PHASE 2] Running comprehensive reconnaissance...")
        
        domain = targets.get("domain", "")
        ip = targets.get("ip", "")
        url = targets.get("url", "")
        
        recon_target = domain or ip or url
        if not recon_target:
            log.warning("  No recon target available, skipping phase 2")
            return
        
        recon_tasks = []
        
        # Subdomain enumeration tools
        if domain:
            for tool in ["subfinder", "amass", "assetfinder", "altdns"]:
                wrapper = self._get_wrapper(tool)
                if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                    recon_tasks.append(self._run_recon_tool(tool, wrapper, domain, options))
        
        # Port scanning tools
        scan_target = ip or domain
        if scan_target:
            for tool in ["naabu", "httpx"]:
                wrapper = self._get_wrapper(tool)
                if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                    recon_tasks.append(self._run_recon_tool(tool, wrapper, scan_target, options))
        
        # Web fingerprinting
        if url or domain:
            for tool in ["whatweb", "gobuster", "ffuf"]:
                wrapper = self._get_wrapper(tool)
                if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                    recon_tasks.append(self._run_recon_tool(tool, wrapper, url or f"https://{domain}", options))
        
        if self.parallel and recon_tasks:
            results = await asyncio.gather(*recon_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    log.error(f"  Recon task failed: {result}")
                elif result:
                    self._process_recon_result(result)
        else:
            for task in recon_tasks:
                try:
                    result = await task
                    self._process_recon_result(result)
                except Exception as e:
                    log.error(f"  Recon task failed: {e}")
    
    async def _run_recon_tool(self, tool_name: str, wrapper, target: str, options: Dict) -> Dict:
        """Run a single recon tool."""
        log.info(f"  Running {tool_name} on {target}...")
        self.result.tools_executed += 1
        
        try:
            tool_options = options.get(tool_name, {})
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: wrapper.run(target, tool_options)
            )
            
            if result and result.success:
                self.result.tools_successful += 1
                return {"tool": tool_name, "target": target, "result": result}
            else:
                self.result.tools_failed += 1
                return {"tool": tool_name, "target": target, "error": result.error if result else "Unknown error"}
        except Exception as e:
            self.result.tools_failed += 1
            log.error(f"  {tool_name} failed: {e}")
            return {"tool": tool_name, "target": target, "error": str(e)}
    
    def _process_recon_result(self, result: Dict):
        """Process reconnaissance results."""
        tool = result.get("tool", "unknown")
        log.info(f"  ✓ {tool} completed")
        
        if "error" in result:
            log.warning(f"  {tool}: {result['error']}")
            return
        
        recon_result = result.get("result")
        if not recon_result:
            return
        
        # Extract and store findings
        data = recon_result.data if hasattr(recon_result, 'data') else {}
        
        if tool in ["subfinder", "amass", "assetfinder"]:
            subdomains = data.get("subdomains", [])
            self.result.subdomains.extend(subdomains)
            for sub in subdomains:
                self.entity_graph.add_entity("DOMAIN", sub, source=tool, confidence=0.8)
                self.result.findings.append({
                    "title": f"Subdomain discovered: {sub}",
                    "severity": "info",
                    "source": tool,
                    "category": "recon"
                })
        
        if tool in ["naabu", "masscan"]:
            ports = data.get("open_ports", [])
            self.result.open_ports.extend(ports)
            for port_info in ports:
                self.result.findings.append({
                    "title": f"Open port {port_info.get('port')} ({port_info.get('service', 'unknown')})",
                    "severity": "info",
                    "source": tool,
                    "category": "recon",
                    "data": port_info
                })
        
        if tool in ["whatweb", "wappalyzer"]:
            tech_stack = data.get("technologies", [])
            for tech in tech_stack:
                self.result.findings.append({
                    "title": f"Technology detected: {tech}",
                    "severity": "info",
                    "source": tool,
                    "category": "recon"
                })
        
        # Save raw data
        if self.save_raw:
            raw_file = self.output_dir / f"recon_{tool}_{self.investigation_id}.json"
            raw_file.write_text(json.dumps(data, indent=2, default=str))
            self.result.raw_data_files.append(str(raw_file))
        
        self.result.recon_results[tool] = data
    
    async def _phase3_osint(self, targets: Dict[str, str], options: Dict):
        """Phase 3: Execute ALL OSINT tools."""
        log.info("\n[PHASE 3] Running comprehensive OSINT investigation...")
        
        username = targets.get("username", "")
        email = targets.get("email", "")
        phone = targets.get("phone", "")
        
        osint_tasks = []
        
        # Username-based OSINT
        if username:
            for tool in ["sherlock", "maigret", "social-analyzer", "profil3r"]:
                wrapper = self._get_wrapper(tool)
                if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                    osint_tasks.append(self._run_osint_tool(tool, wrapper, username, "username", options))
        
        # Email-based OSINT
        if email:
            for tool in ["holehe", "intelligence-x"]:
                wrapper = self._get_wrapper(tool)
                if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                    osint_tasks.append(self._run_osint_tool(tool, wrapper, email, "email", options))
        
        # Phone-based OSINT
        if phone:
            wrapper = self._get_wrapper("phoneinfoga")
            if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                osint_tasks.append(self._run_osint_tool("phoneinfoga", wrapper, phone, "phone", options))
        
        if self.parallel and osint_tasks:
            results = await asyncio.gather(*osint_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.error(f"  OSINT task failed: {result}")
                elif result:
                    self._process_osint_result(result)
        else:
            for task in osint_tasks:
                try:
                    result = await task
                    self._process_osint_result(result)
                except Exception as e:
                    log.error(f"  OSINT task failed: {e}")
    
    async def _run_osint_tool(self, tool_name: str, wrapper, target: str, target_type: str, options: Dict) -> Dict:
        """Run a single OSINT tool."""
        log.info(f"  Running {tool_name} on {target_type}: {target}...")
        self.result.tools_executed += 1
        
        try:
            tool_options = options.get(tool_name, {})
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: wrapper.run(target, tool_options)
            )
            
            if result and result.success:
                self.result.tools_successful += 1
                return {"tool": tool_name, "target": target, "target_type": target_type, "result": result}
            else:
                self.result.tools_failed += 1
                return {"tool": tool_name, "target": target, "error": result.error if result else "Unknown error"}
        except Exception as e:
            self.result.tools_failed += 1
            return {"tool": tool_name, "target": target, "error": str(e)}
    
    def _process_osint_result(self, result: Dict):
        """Process OSINT results."""
        tool = result.get("tool", "unknown")
        log.info(f"  ✓ {tool} completed")
        
        if "error" in result:
            log.warning(f"  {tool}: {result['error']}")
            return
        
        osint_result = result.get("result")
        if not osint_result:
            return
        
        data = osint_result.data if hasattr(osint_result, 'data') else {}
        
        # Process social media accounts
        accounts = data.get("accounts", []) or data.get("profiles", [])
        for account in accounts:
            platform = account.get("platform", "unknown")
            url = account.get("url", "")
            
            if platform not in self.result.social_accounts:
                self.result.social_accounts[platform] = []
            self.result.social_accounts[platform].append(account)
            
            self.entity_graph.add_entity("SOCIAL_ACCOUNT", url, source=tool, 
                                        metadata={"platform": platform})
            self.result.findings.append({
                "title": f"Social media account found on {platform}",
                "severity": "info",
                "source": tool,
                "category": "osint",
                "data": account
            })
        
        # Process breach data
        breaches = data.get("breaches", []) or data.get("leaks", [])
        for breach in breaches:
            self.result.breaches.append(breach)
            self.result.findings.append({
                "title": f"Data breach detected: {breach.get('name', 'Unknown')}",
                "severity": "high",
                "source": tool,
                "category": "osint",
                "data": breach
            })
        
        # Save raw data
        if self.save_raw:
            raw_file = self.output_dir / f"osint_{tool}_{self.investigation_id}.json"
            raw_file.write_text(json.dumps(data, indent=2, default=str))
            self.result.raw_data_files.append(str(raw_file))
        
        self.result.osint_results[tool] = data
    
    async def _phase4_scanning(self, targets: Dict[str, str], options: Dict):
        """Phase 4: Execute ALL vulnerability scanners."""
        log.info("\n[PHASE 4] Running vulnerability scanning...")
        
        domain = targets.get("domain", "")
        ip = targets.get("ip", "")
        url = targets.get("url", "")
        
        scan_targets = []
        if url:
            scan_targets.append(url)
        if domain:
            scan_targets.append(f"https://{domain}")
            scan_targets.append(f"http://{domain}")
        if ip:
            scan_targets.append(f"http://{ip}")
        
        # Also scan discovered subdomains
        for subdomain in self.result.subdomains[:10]:  # Limit to first 10
            scan_targets.append(f"https://{subdomain}")
        
        scanning_tasks = []
        
        for target in set(scan_targets):
            for tool in ["nuclei", "nikto", "sslscan"]:
                wrapper = self._get_wrapper(tool)
                if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                    scanning_tasks.append(self._run_scanner(tool, wrapper, target, options))
        
        if self.parallel and scanning_tasks:
            # Limit concurrency for scanners
            semaphore = asyncio.Semaphore(self.max_concurrency)
            
            async def limited_scan(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(*[limited_scan(t) for t in scanning_tasks], return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.error(f"  Scan task failed: {result}")
                elif result:
                    self._process_scan_result(result)
        else:
            for task in scanning_tasks:
                try:
                    result = await task
                    self._process_scan_result(result)
                except Exception as e:
                    log.error(f"  Scan task failed: {e}")
    
    async def _run_scanner(self, tool_name: str, wrapper, target: str, options: Dict) -> Dict:
        """Run a single scanner."""
        log.info(f"  Running {tool_name} on {target}...")
        self.result.tools_executed += 1
        
        try:
            tool_options = options.get(tool_name, {"severity": "critical,high,medium"})
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: wrapper.run(target, tool_options)
            )
            
            if result and result.success:
                self.result.tools_successful += 1
                return {"tool": tool_name, "target": target, "result": result}
            else:
                self.result.tools_failed += 1
                return {"tool": tool_name, "target": target, "error": result.error if result else "Unknown error"}
        except Exception as e:
            self.result.tools_failed += 1
            return {"tool": tool_name, "target": target, "error": str(e)}
    
    def _process_scan_result(self, result: Dict):
        """Process scanning results."""
        tool = result.get("tool", "unknown")
        log.info(f"  ✓ {tool} completed")
        
        if "error" in result:
            log.warning(f"  {tool}: {result['error']}")
            return
        
        scan_result = result.get("result")
        if not scan_result:
            return
        
        data = scan_result.data if hasattr(scan_result, 'data') else {}
        
        # Process vulnerabilities
        findings = data.get("findings", []) or data.get("vulnerabilities", [])
        for vuln in findings:
            severity = vuln.get("severity", "info").lower()
            vuln_name = vuln.get("name", vuln.get("template_id", "Unknown"))
            
            if severity not in self.result.vulnerabilities:
                self.result.vulnerabilities[severity] = []
            self.result.vulnerabilities[severity].append(vuln)
            
            self.result.findings.append({
                "title": f"Vulnerability: {vuln_name}",
                "severity": severity,
                "source": tool,
                "category": "vulnerability",
                "data": vuln
            })
        
        # Save raw data
        if self.save_raw:
            raw_file = self.output_dir / f"scan_{tool}_{self.investigation_id}.json"
            raw_file.write_text(json.dumps(data, indent=2, default=str))
            self.result.raw_data_files.append(str(raw_file))
        
        self.result.scanning_results[tool] = data
    
    async def _phase5_web_exploit(self, targets: Dict[str, str], options: Dict):
        """Phase 5: Execute ALL web exploitation tools."""
        log.info("\n[PHASE 5] Running web exploitation analysis...")
        
        url = targets.get("url", "")
        domain = targets.get("domain", "")
        
        if not url and not domain:
            log.warning("  No web target available, skipping phase 5")
            return
        
        exploit_tasks = []
        test_urls = [url] if url else [f"https://{domain}", f"http://{domain}"]
        
        for test_url in test_urls:
            for tool in ["sqlmap", "dalfox", "wpscan", "xsstrike"]:
                wrapper = self._get_wrapper(tool)
                if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                    exploit_tasks.append(self._run_web_exploit_tool(tool, wrapper, test_url, options))
        
        if exploit_tasks:
            results = await asyncio.gather(*exploit_tasks[:5], return_exceptions=True)  # Limit to 5
            for result in results:
                if isinstance(result, Exception):
                    log.error(f"  Web exploit task failed: {result}")
                elif result:
                    self._process_web_exploit_result(result)
    
    async def _run_web_exploit_tool(self, tool_name: str, wrapper, target: str, options: Dict) -> Dict:
        """Run a single web exploitation tool."""
        log.info(f"  Running {tool_name} on {target}...")
        self.result.tools_executed += 1
        
        try:
            tool_options = options.get(tool_name, {})
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: wrapper.run(target, tool_options)
            )
            
            if result and result.success:
                self.result.tools_successful += 1
                return {"tool": tool_name, "target": target, "result": result}
            else:
                self.result.tools_failed += 1
                return {"tool": tool_name, "target": target, "error": result.error if result else "Unknown error"}
        except Exception as e:
            self.result.tools_failed += 1
            return {"tool": tool_name, "target": target, "error": str(e)}
    
    def _process_web_exploit_result(self, result: Dict):
        """Process web exploitation results."""
        tool = result.get("tool", "unknown")
        log.info(f"  ✓ {tool} completed")
        
        if "error" in result:
            log.warning(f"  {tool}: {result['error']}")
            return
        
        exploit_result = result.get("result")
        if not exploit_result:
            return
        
        data = exploit_result.data if hasattr(exploit_result, 'data') else {}
        
        # Process findings
        findings = data.get("findings", []) or data.get("vulnerabilities", [])
        for finding in findings:
            self.result.findings.append({
                "title": f"Web vulnerability: {finding.get('type', finding.get('name', 'Unknown'))}",
                "severity": finding.get("severity", "high"),
                "source": tool,
                "category": "web_exploitation",
                "data": finding
            })
        
        if self.save_raw:
            raw_file = self.output_dir / f"web_exploit_{tool}_{self.investigation_id}.json"
            raw_file.write_text(json.dumps(data, indent=2, default=str))
            self.result.raw_data_files.append(str(raw_file))
        
        self.result.exploitation_results[tool] = data
    
    async def _phase6_credentials(self, targets: Dict[str, str], options: Dict):
        """Phase 6: Execute credential attack simulations."""
        log.info("\n[PHASE 6] Running credential attack simulation...")
        
        # This phase requires specific credentials or wordlists
        # Only run if explicitly enabled
        if not options.get("enable_credential_attacks", False):
            log.info("  Credential attacks disabled (use --enable-credential-attacks to enable)")
            return
        
        # Placeholder for credential attack logic
        log.info("  Credential attack simulation would run here")
        self.result.post_exploit_results["credential_attacks"] = {"status": "skipped", "reason": "Not enabled"}
    
    async def _phase7_exploitation(self, targets: Dict[str, str], options: Dict):
        """Phase 7: Execute exploitation frameworks."""
        log.info("\n[PHASE 7] Running exploitation frameworks...")
        
        # This phase is highly context-dependent and requires specific targets
        # Only run if explicitly enabled
        if not options.get("enable_exploitation", False):
            log.info("  Exploitation disabled (use --enable-exploitation to enable)")
            return
        
        log.info("  Exploitation would run here with proper authorization")
        self.result.exploitation_results["frameworks"] = {"status": "skipped", "reason": "Not enabled"}
    
    async def _phase8_post_exploit(self, targets: Dict[str, str], options: Dict):
        """Phase 8: Execute post-exploitation tools."""
        log.info("\n[PHASE 8] Running post-exploitation analysis...")
        
        # Requires prior exploitation success
        log.info("  Post-exploitation requires successful exploitation phase")
        self.result.post_exploit_results["status"] = "skipped"
    
    async def _phase9_threat_intel(self, targets: Dict[str, str], options: Dict):
        """Phase 9: Execute threat intelligence enrichment."""
        log.info("\n[PHASE 9] Running threat intelligence enrichment...")
        
        domain = targets.get("domain", "")
        ip = targets.get("ip", "")
        
        intel_tasks = []
        
        for indicator in [domain, ip]:
            if indicator:
                for tool in ["intelowl", "virustotal"]:
                    wrapper = self._get_wrapper(tool)
                    if wrapper and (self.skip_installed_check or wrapper.is_installed()):
                        intel_tasks.append(self._run_threat_intel_tool(tool, wrapper, indicator, options))
        
        if intel_tasks:
            results = await asyncio.gather(*intel_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.error(f"  Threat intel task failed: {result}")
                elif result:
                    self._process_threat_intel_result(result)
    
    async def _run_threat_intel_tool(self, tool_name: str, wrapper, indicator: str, options: Dict) -> Dict:
        """Run a single threat intel tool."""
        log.info(f"  Running {tool_name} on {indicator}...")
        self.result.tools_executed += 1
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: wrapper.run(indicator, options.get(tool_name, {}))
            )
            
            if result and result.success:
                self.result.tools_successful += 1
                return {"tool": tool_name, "indicator": indicator, "result": result}
            else:
                self.result.tools_failed += 1
                return {"tool": tool_name, "indicator": indicator, "error": result.error if result else "Unknown error"}
        except Exception as e:
            self.result.tools_failed += 1
            return {"tool": tool_name, "indicator": indicator, "error": str(e)}
    
    def _process_threat_intel_result(self, result: Dict):
        """Process threat intelligence results."""
        tool = result.get("tool", "unknown")
        log.info(f"  ✓ {tool} completed")
        
        if "error" in result:
            log.warning(f"  {tool}: {result['error']}")
            return
        
        intel_result = result.get("result")
        if not intel_result:
            return
        
        data = intel_result.data if hasattr(intel_result, 'data') else {}
        
        # Process threat indicators
        if data.get("malicious", False) or data.get("threat_score", 0) > 50:
            self.result.findings.append({
                "title": f"Threat intelligence alert for {result.get('indicator')}",
                "severity": "high",
                "source": tool,
                "category": "threat_intelligence",
                "data": data
            })
        
        if self.save_raw:
            raw_file = self.output_dir / f"threat_intel_{tool}_{self.investigation_id}.json"
            raw_file.write_text(json.dumps(data, indent=2, default=str))
            self.result.raw_data_files.append(str(raw_file))
        
        self.result.threat_intel_results[tool] = data
    
    async def _phase10_ai_analysis(self, targets: Dict[str, str], options: Dict):
        """Phase 10: Execute AI analysis and attack path generation."""
        log.info("\n[PHASE 10] Running AI analysis...")
        
        # Use autonomous agent if available
        if self.autonomous_agent:
            try:
                log.info("  Running autonomous agent analysis...")
                analysis = await self.autonomous_agent.analyze(
                    findings=self.result.findings,
                    entities=self.result.entities,
                    targets=targets
                )
                self.result.ai_analysis_results["autonomous_agent"] = analysis
                
                # Generate attack paths
                attack_paths = await self.autonomous_agent.generate_attack_paths()
                self.result.attack_paths = attack_paths
                
            except Exception as e:
                log.error(f"  Autonomous agent analysis failed: {e}")
        
        # Use decision engine for recommendations
        try:
            recommendations = self.decision_engine.recommend_next_steps(
                findings=self.result.findings,
                profile=self.profile
            )
            self.result.ai_analysis_results["recommendations"] = recommendations
        except Exception as e:
            log.error(f"  Decision engine failed: {e}")
        
        log.info(f"  AI analysis complete: {len(self.result.attack_paths)} attack paths generated")
    
    async def _phase11_workflows(self, targets: Dict[str, str], options: Dict):
        """Phase 11: Execute all built-in workflows."""
        log.info("\n[PHASE 11] Running built-in workflows...")
        
        workflow_options = {**targets, **options.get("workflow_options", {})}
        
        for workflow_name in BUILTIN_WORKFLOWS.keys():
            try:
                log.info(f"  Running workflow: {workflow_name}")
                workflow = get_workflow(workflow_name, workflow_options)
                result = await workflow.run(output_dir=str(self.output_dir / "workflows"))
                
                self.result.workflows_run.append(workflow_name)
                
                if isinstance(result, WorkflowResult):
                    # Convert workflow findings
                    for step_result in result.steps:
                        if step_result.result and step_result.result.findings:
                            for finding in step_result.result.findings:
                                self.result.findings.append({
                                    "title": finding.title if hasattr(finding, 'title') else str(finding),
                                    "severity": str(finding.severity) if hasattr(finding, 'severity') else "info",
                                    "source": f"workflow:{workflow_name}",
                                    "category": "workflow"
                                })
                
                log.info(f"  ✓ Workflow {workflow_name} completed")
                
            except Exception as e:
                log.error(f"  Workflow {workflow_name} failed: {e}")
                self.result.tools_failed += 1
    
    async def _phase12_pipelines(self, targets: Dict[str, str], options: Dict):
        """Phase 12: Execute automation pipelines."""
        log.info("\n[PHASE 12] Running automation pipelines...")
        
        # Create and run advanced pipeline
        try:
            pipeline = AdvancedPipeline("comprehensive_investigation")
            
            # Add dynamic steps based on discovered data
            if self.result.subdomains:
                async def nuclei_step(ctx):
                    wrapper = self._get_wrapper("nuclei")
                    if wrapper:
                        result = wrapper.run(",".join(self.result.subdomains[:5]), {})
                        return {"nuclei_result": result.data if result else {}}
                
                pipeline.add_step(AdvancedStep(
                    name="nuclei_on_subdomains",
                    runner=nuclei_step,
                    retries=1
                ))
            
            pipeline_result = await pipeline.run(initial_context={"targets": targets})
            self.result.pipelines_executed.append("comprehensive_investigation")
            
            log.info(f"  ✓ Advanced pipeline completed: {pipeline_result.success}")
            
        except Exception as e:
            log.error(f"  Advanced pipeline failed: {e}")
        
        # Run V2 pipeline engine
        try:
            engine = PipelineEngineV2(concurrency=self.max_concurrency)
            
            async def correlation_step(ctx):
                return {"correlation_status": "complete"}
            
            engine.add_step(PipelineStepV2(
                name="final_correlation",
                runner=correlation_step
            ))
            
            v2_result = await engine.run(initial_context={"targets": targets})
            self.result.pipelines_executed.append("pipeline_v2")
            
            log.info(f"  ✓ Pipeline V2 completed: {v2_result.success}")
            
        except Exception as e:
            log.error(f"  Pipeline V2 failed: {e}")
    
    async def _phase13_correlation(self):
        """Phase 13: Final correlation and entity graph finalization."""
        log.info("\n[PHASE 13] Running final correlation...")
        
        # Build relationship graph
        self.graph_builder.build_from_findings(self.result.findings)
        
        # Extract relationships
        self.result.relationships = self.entity_graph.get_relationships()
        
        log.info(f"  Entity graph contains {len(self.result.relationships)} relationships")
    
    async def _phase14_reporting(self):
        """Phase 14: Generate comprehensive reports."""
        log.info("\n[PHASE 14] Generating reports...")
        
        if not self.generate_reports:
            log.info("  Report generation disabled")
            return
        
        # Convert findings to report format
        report_findings = []
        for finding in self.result.findings:
            severity_map = {"critical": RS.CRITICAL, "high": RS.HIGH, 
                          "medium": RS.MEDIUM, "low": RS.LOW, "info": RS.INFO}
            sev = severity_map.get(str(finding.get("severity", "info")).lower(), RS.INFO)
            
            report_findings.append(RF(
                title=finding.get("title", "Unknown"),
                description=json.dumps(finding.get("data", {}), default=str),
                severity=sev,
                target=self.result.targets.get("domain", self.result.targets.get("ip", "unknown")),
                category=finding.get("category", "general")
            ))
        
        # Generate reports in multiple formats
        report_title = f"RTF Investigation Report - {self.investigation_id}"
        
        for fmt in ["html", "json", "md"]:
            try:
                output_path = str(self.output_dir / f"report_{self.investigation_id}.{fmt}")
                report_engine.generate(
                    title=report_title,
                    findings=report_findings,
                    format=fmt,
                    output_path=output_path
                )
                self.result.report_files.append(output_path)
                log.info(f"  Generated {fmt.upper()} report: {output_path}")
            except Exception as e:
                log.error(f"  Failed to generate {fmt} report: {e}")
        
        # Save comprehensive JSON result
        result_file = self.output_dir / f"investigation_result_{self.investigation_id}.json"
        result_file.write_text(json.dumps(self.result.to_dict(), indent=2, default=str))
        self.result.report_files.append(str(result_file))
        log.info(f"  Saved comprehensive result: {result_file}")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rtf",
        description="RTF v2.0 - Massive Automatic Investigation Pipeline"
    )
    
    # Main investigation command
    investigate_group = parser.add_argument_group("Investigation Options")
    investigate_group.add_argument(
        "--investigate", 
        action="store_true",
        help="Run the massive automatic investigation pipeline"
    )
    
    # Target specification
    target_group = parser.add_argument_group("Target Specification")
    target_group.add_argument("-u", "--username", default="", help="Username to investigate")
    target_group.add_argument("-d", "--domain", default="", help="Domain to investigate")
    target_group.add_argument("-e", "--email", default="", help="Email address to investigate")
    target_group.add_argument("-p", "--phone", default="", help="Phone number to investigate")
    target_group.add_argument("-i", "--ip", default="", help="IP address to investigate")
    target_group.add_argument("--url", default="", help="URL to investigate")
    target_group.add_argument("--target", default="", help="Generic target (will auto-detect type)")
    
    # Investigation modes
    mode_group = parser.add_argument_group("Investigation Modes")
    mode_group.add_argument(
        "--comprehensive", 
        action="store_true",
        help="Run comprehensive investigation (all tools)"
    )
    mode_group.add_argument(
        "--full-stack", 
        action="store_true",
        help="Run full-stack investigation including exploitation"
    )
    mode_group.add_argument(
        "--active-investigation", 
        action="store_true",
        help="Enable active scanning and exploitation"
    )
    mode_group.add_argument(
        "--passive-only", 
        action="store_true",
        help="Run only passive reconnaissance"
    )
    mode_group.add_argument(
        "--ai-autonomous", 
        action="store_true",
        help="Use AI autonomous agent for investigation"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "-o", "--output", 
        default="./investigation_results",
        help="Output directory for results (default: ./investigation_results)"
    )
    output_group.add_argument(
        "--no-reports", 
        action="store_true",
        help="Disable report generation"
    )
    output_group.add_argument(
        "--save-raw", 
        action="store_true",
        default=True,
        help="Save raw tool output (default: enabled)"
    )
    output_group.add_argument(
        "--no-save-raw", 
        action="store_true",
        help="Disable saving raw tool output"
    )
    
    # Performance options
    perf_group = parser.add_argument_group("Performance Options")
    perf_group.add_argument(
        "--parallel", 
        action="store_true",
        default=True,
        help="Run tools in parallel (default: enabled)"
    )
    perf_group.add_argument(
        "--sequential", 
        action="store_true",
        help="Run tools sequentially"
    )
    perf_group.add_argument(
        "--max-concurrency", 
        type=int,
        default=10,
        help="Maximum concurrent tool executions (default: 10)"
    )
    
    # Advanced options
    adv_group = parser.add_argument_group("Advanced Options")
    adv_group.add_argument(
        "--enable-credential-attacks", 
        action="store_true",
        help="Enable credential attack simulations"
    )
    adv_group.add_argument(
        "--enable-exploitation", 
        action="store_true",
        help="Enable exploitation frameworks"
    )
    adv_group.add_argument(
        "--skip-installed-check", 
        action="store_true",
        help="Skip checking if tools are installed"
    )
    adv_group.add_argument(
        "--profile", 
        default="comprehensive",
        choices=["core", "comprehensive", "full", "aggressive", "ai_autonomous"],
        help="Investigation profile (default: comprehensive)"
    )
    adv_group.add_argument(
        "--config", 
        default="",
        help="Path to configuration file"
    )
    
    # Existing commands (for backward compatibility)
    subs = parser.add_subparsers(dest="command")
    subs.add_parser("console", help="Start interactive operator console")
    
    api_p = subs.add_parser("api", help="Start REST API server")
    api_p.add_argument("--host", default="")
    api_p.add_argument("--port", type=int, default=0)
    
    subs.add_parser("version", help="Print version")
    
    return parser


def parse_args() -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args()
    
    # Auto-detect target type if --target is provided
    if args.target and not any([args.username, args.domain, args.email, args.phone, args.ip, args.url]):
        if "@" in args.target:
            args.email = args.target
        elif args.target.replace(".", "").isdigit() or ":" in args.target:
            args.ip = args.target
        elif args.target.startswith("http"):
            args.url = args.target
        elif args.target.isdigit() or args.target.startswith("+"):
            args.phone = args.target
        else:
            args.domain = args.target
    
    return args


async def run_investigation(args: argparse.Namespace):
    """Run the massive investigation pipeline."""
    
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
    
    # Initialize and run pipeline
    pipeline = MassiveInvestigationPipeline(
        output_dir=args.output,
        profile=profile,
        parallel=not args.sequential,
        max_concurrency=args.max_concurrency,
        skip_installed_check=args.skip_installed_check,
        save_raw=not args.no_save_raw,
        generate_reports=not args.no_reports,
    )
    
    try:
        result = await pipeline.run(targets, options)
        
        # Print summary
        print("\n" + "=" * 70)
        print("INVESTIGATION SUMMARY")
        print("=" * 70)
        print(f"Investigation ID: {result.investigation_id}")
        print(f"Duration: {result.duration_seconds}s")
        print(f"Profile: {result.profile}")
        print(f"Success: {'✓' if result.success else '✗'}")
        print(f"\nTools: {result.tools_executed} executed, {result.tools_successful} OK, {result.tools_failed} failed")
        print(f"Findings: {len(result.findings)} total")
        print(f"Workflows: {len(result.workflows_run)} run")
        print(f"Pipelines: {len(result.pipelines_executed)} executed")
        
        if result.subdomains:
            print(f"\nSubdomains discovered: {len(result.subdomains)}")
        if result.open_ports:
            print(f"Open ports found: {len(result.open_ports)}")
        if result.social_accounts:
            print(f"Social accounts: {sum(len(v) for v in result.social_accounts.values())}")
        if result.breaches:
            print(f"Breaches detected: {len(result.breaches)}")
        
        print(f"\nReports saved to: {args.output}")
        for report in result.report_files:
            print(f"  - {report}")
        
        print("=" * 70)
        
        return result
        
    except KeyboardInterrupt:
        print("\n[!] Investigation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_args()
    
    # Handle simple commands
    if args.command == "version":
        print(f"RedTeam Framework v{VERSION}")
        print("Massive Automatic Investigation Pipeline")
        return
    
    if args.command == "console":
        from framework.cli.console import run_console
        run_console()
        return
    
    if args.command == "api":
        from framework.api.server import run_server
        run_server(host=args.host or None, port=args.port or None)
        return
    
    # Run investigation if requested
    if args.investigate:
        # Initialize framework
        config.load()
        configure_root_logger(
            level=config.get("log_level", "INFO"),
            log_file=config.get("log_file")
        )
        
        # Initialize database
        db.init(config.get("db_path", "data/framework.db"))
        
        # Load modules
        module_loader.load_all()
        
        # Refresh tool registry
        tool_registry.refresh()
        
        # Run investigation
        asyncio.run(run_investigation(args))
    else:
        # Show help if no command given
        build_parser().print_help()


if __name__ == "__main__":
    main()
