from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from framework.modules.loader import module_loader
from framework.titan.knowledge_graph import ENTITY_TYPES, RELATIONSHIP_TYPES


@dataclass
class OmegaEngine:
    name: str
    mission: str
    categories: List[str] = field(default_factory=list)
    workflows: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    storage: List[str] = field(default_factory=list)
    tool_families: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mission": self.mission,
            "categories": list(self.categories),
            "workflows": list(self.workflows),
            "interfaces": list(self.interfaces),
            "storage": list(self.storage),
            "tool_families": list(self.tool_families),
            "tags": list(self.tags),
        }


class OmegaEngineRegistry:
    def __init__(self) -> None:
        self._engines: Dict[str, OmegaEngine] = {
            "rtf-core": OmegaEngine(
                name="rtf-core",
                mission="Compatibility, config, registry, CLI, scheduler, and persistence spine.",
                categories=["recon", "osint", "web", "active_directory", "cloud", "network", "wireless"],
                workflows=["full_recon", "web_audit", "cloud_audit"],
                interfaces=["cli", "api", "scheduler", "database"],
                storage=["sqlite", "reports", "events"],
                tags=["backward-compatible", "loader-integrated"],
            ),
            "rtf-osint-engine": OmegaEngine(
                name="rtf-osint-engine",
                mission="Username, email, phone, domain, repository, and search-based intelligence collection.",
                categories=["osint"],
                workflows=["osint_person", "deep_osint", "nexus_identity_workflow"],
                interfaces=["module_loader", "workflow_engine", "api"],
                storage=["graph_nodes", "graph_edges", "artifacts"],
                tool_families=["sherlock", "maigret", "social-analyzer", "holehe", "phoneinfoga", "search-scrapers"],
                tags=["socmint", "osint", "1000-source-ready"],
            ),
            "rtf-socmint-engine": OmegaEngine(
                name="rtf-socmint-engine",
                mission="15-stage social-media intelligence pipeline with recursive pivoting and threat scoring.",
                categories=["osint"],
                workflows=["identity_fusion", "omega_socmint"],
                interfaces=["titan", "workflow_engine", "reporting"],
                storage=["neo4j", "sqlite", "reports"],
                tool_families=["twint", "instaloader", "snscrape", "toutatis", "gitfive", "reddit-user-analyser"],
                tags=["pipeline", "graph", "recursive-pivot"],
            ),
            "rtf-breach-engine": OmegaEngine(
                name="rtf-breach-engine",
                mission="Breach correlation, credential reuse detection, and exposed-secret enrichment.",
                categories=["osint", "post_exploitation"],
                workflows=["credential_attack_chain", "credential_intelligence"],
                interfaces=["module_loader", "workflow_engine", "credential-vault"],
                storage=["credentials_vault", "findings", "graph_nodes"],
                tool_families=["holehe", "breach_correlation", "trufflehog", "gitleaks"],
                tags=["breach", "credentials"],
            ),
            "rtf-scraper-engine": OmegaEngine(
                name="rtf-scraper-engine",
                mission="Search-engine and web-scraping execution fabric for distributed collection.",
                categories=["osint", "recon", "web"],
                workflows=["deep_osint", "attack_surface_mapping"],
                interfaces=["api", "scheduler", "workers"],
                storage=["artifacts", "events"],
                tool_families=["google", "duckduckgo", "bing", "brave", "startpage", "qwant", "yandex", "baidu"],
                tags=["scraping", "parallel"],
            ),
            "rtf-casm-engine": OmegaEngine(
                name="rtf-casm-engine",
                mission="Continuous attack-surface monitoring for domains, subdomains, services, and exposures.",
                categories=["recon"],
                workflows=["attack_surface_mapping", "continuous_attack_surface", "full_recon"],
                interfaces=["scheduler", "workflow_engine", "dashboard"],
                storage=["targets", "findings", "reports"],
                tool_families=["subfinder", "amass", "httpx", "naabu", "nmap", "nuclei"],
                tags=["casm", "monitoring"],
            ),
            "rtf-graph-engine": OmegaEngine(
                name="rtf-graph-engine",
                mission="Neo4j-compatible entity/relationship ingestion, querying, and evidence provenance.",
                categories=["osint", "recon", "post_exploitation"],
                workflows=["omega_socmint"],
                interfaces=["database", "neo4j", "api", "dashboard"],
                storage=["graph_nodes", "graph_edges", "neo4j"],
                tags=["graph", "neo4j", "entities", "relationships"],
            ),
            "rtf-ai-engine": OmegaEngine(
                name="rtf-ai-engine",
                mission="Research, correlation, prioritization, and autonomous pipeline evolution.",
                categories=["ai_analysis", "osint"],
                workflows=["omega_autonomous_lab", "identity_fusion"],
                interfaces=["agents", "workflow_engine", "dashboard"],
                storage=["artifacts", "reports", "events"],
                tool_families=["claude", "pentestgpt", "behavioral_fingerprinting"],
                tags=["ai", "autonomous"],
            ),
            "rtf-credential-engine": OmegaEngine(
                name="rtf-credential-engine",
                mission="Credential attack simulation, vaulting, reuse analysis, and breach pivots.",
                categories=["credential_attacks", "post_exploitation"],
                workflows=["credential_attack_chain", "credential_intelligence"],
                interfaces=["module_loader", "database", "reporting"],
                storage=["credentials_vault", "findings"],
                tool_families=["hashcat", "john", "hydra", "kerbrute", "brutespray", "ncrack"],
                tags=["credentials", "vault"],
            ),
            "rtf-report-engine": OmegaEngine(
                name="rtf-report-engine",
                mission="Multi-format reporting, exports, timelines, and operation snapshots.",
                categories=["osint", "recon", "web"],
                workflows=["full_recon", "omega_socmint", "omega_autonomous_lab"],
                interfaces=["reporting", "dashboard", "api"],
                storage=["reports", "artifacts"],
                tags=["html", "pdf", "json", "csv", "docx"],
            ),
            "rtf-monitoring-engine": OmegaEngine(
                name="rtf-monitoring-engine",
                mission="Health checks, event streaming, scheduler inspection, and dependency validation.",
                categories=["recon", "osint", "web"],
                workflows=["omega_autonomous_lab"],
                interfaces=["scheduler", "events", "api", "cli"],
                storage=["event_log", "jobs"],
                tags=["monitoring", "self-healing"],
            ),
            "rtf-automation-engine": OmegaEngine(
                name="rtf-automation-engine",
                mission="Async orchestration, interval scheduling, parallel fan-out, and repair loops.",
                categories=["osint", "recon", "web", "cloud"],
                workflows=["omega_socmint", "omega_autonomous_lab"],
                interfaces=["scheduler", "workflow_engine", "pipeline_v2"],
                storage=["jobs", "event_log"],
                tags=["parallel", "async", "repair"],
            ),
            "rtf-worker-cluster": OmegaEngine(
                name="rtf-worker-cluster",
                mission="Queue-backed worker model for large source catalogs and high-volume investigations.",
                categories=["osint", "recon", "threat_intelligence"],
                workflows=["omega_socmint", "continuous_attack_surface"],
                interfaces=["message-bus", "scheduler", "api"],
                storage=["events", "artifacts"],
                tags=["workers", "scaling", "distributed"],
            ),
        }

    def list_engines(self) -> List[Dict[str, Any]]:
        return [engine.to_dict() for engine in self._engines.values()]

    def get(self, name: str) -> Dict[str, Any]:
        return self._engines[name].to_dict()

    def source_catalog(self) -> Dict[str, Any]:
        return {
            "target_scale": 1000,
            "categories": {
                "username_intelligence": ["social networks", "username scanners", "public profiles", "forums", "gaming"],
                "email_intelligence": ["breach databases", "MX/WHOIS", "public mentions", "code repositories"],
                "phone_intelligence": ["carrier data", "messaging apps", "public records", "reverse lookup"],
                "domain_intelligence": ["WHOIS", "certificate transparency", "subdomain tools", "threat intel feeds"],
                "organization_intelligence": ["company records", "press releases", "employees", "suppliers"],
                "breach_intelligence": ["leak aggregators", "credential dumps", "secret scanners", "dark web sources"],
                "ip_intelligence": ["passive DNS", "scan telemetry", "hosting metadata", "geo datasets"],
                "document_intelligence": ["search engines", "metadata sources", "file indexes", "archives"],
                "image_intelligence": ["EXIF", "reverse image search", "social media CDNs", "media archives"],
            },
            "search_engines": ["google", "duckduckgo", "bing", "brave", "yahoo", "startpage", "qwant", "swisscows", "yandex", "baidu"],
            "username_discovery": ["sherlock", "maigret", "nexfil", "blackbird", "social-analyzer", "whatsmyname", "checkusernames", "namechk"],
            "social_scraping": ["twint", "instaloader", "snscrape", "toutatis", "gitfive", "reddit-user-analyser"],
            "domain_intelligence": ["subfinder", "amass", "httpx", "naabu", "nmap", "nuclei"],
            "secret_discovery": ["trufflehog", "gitleaks"],
            "metadata_analysis": ["exiftool"],
        }

    def graph_schema(self) -> Dict[str, Any]:
        return {
            "backend": "Neo4j",
            "entity_types": list(ENTITY_TYPES),
            "relationship_types": list(RELATIONSHIP_TYPES),
            "required_relationships": [
                "OWNS", "USES_EMAIL", "USES_PHONE", "REGISTERED_WITH", "CONNECTED_TO",
                "POSTED_FROM", "MENTIONED_IN", "FOLLOWS", "ASSOCIATED_WITH",
            ],
        }

    def loader_integration(self) -> Dict[str, Any]:
        modules = module_loader.list_modules() if module_loader.list_modules() else []
        categories: Dict[str, int] = {}
        for module in modules:
            categories[module["category"]] = categories.get(module["category"], 0) + 1
        bindings = []
        for engine in self._engines.values():
            matched = [m["path"] for m in modules if m["category"] in engine.categories][:12]
            bindings.append({
                "engine": engine.name,
                "categories": engine.categories,
                "matched_module_count": len([m for m in modules if m["category"] in engine.categories]),
                "sample_modules": matched,
                "workflows": engine.workflows,
            })
        return {
            "module_count": len(modules),
            "module_categories": categories,
            "bindings": bindings,
        }

    def manifest(self) -> Dict[str, Any]:
        return {
            "name": "RedTeam Framework v4.0 OMEGA-BLACK",
            "version": "4.0.0-omega-black",
            "engines": self.list_engines(),
            "source_catalog": self.source_catalog(),
            "graph_schema": self.graph_schema(),
            "loader_integration": self.loader_integration(),
            "agents": [
                "ResearchAgent", "ModuleGenerator", "PipelineEvolutionAgent", "ToolIntegrationAgent",
                "GraphAgent", "DashboardAgent", "SecurityAgent", "TestingAgent", "BugFixAgent",
                "SelfHealingAgent", "ReleaseAgent",
            ],
            "self_healing_commands": ["doctor", "fix", "validate", "repair", "upgrade"],
        }


omega_registry = OmegaEngineRegistry()
