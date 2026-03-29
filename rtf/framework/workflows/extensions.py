from __future__ import annotations

from typing import Dict, Type

from framework.workflows.engine import Workflow, WorkflowBuilder


class DeepOSINTWorkflow(Workflow):
    name = "deep_osint"
    description = "Extended OSINT pipeline with username analysis and breach correlation."

    def steps(self):
        from framework.modules.osint.username_enum import UsernameEnumModule
        from framework.modules.osint.username_pattern_analyzer import UsernamePatternAnalyzerModule
        from framework.modules.osint.breach_correlation import BreachCorrelationModule
        return (
            WorkflowBuilder(self.name)
            .add_step("username_enum", UsernameEnumModule, required=True)
            .add_step("username_pattern_analyzer", UsernamePatternAnalyzerModule, transformer=lambda prev: {"username": (prev.output or {}).get("username", "") if prev else ""}, required=False)
            .add_step("breach_correlation", BreachCorrelationModule, transformer=lambda prev: {"query": (prev.output or {}).get("username", "") if prev else ""}, required=False)
            .build()
            ._steps
        )


class AttackSurfaceMappingWorkflow(Workflow):
    name = "attack_surface_mapping"
    description = "Subdomain, port, tech stack, and misconfiguration mapping chain."

    def steps(self):
        from framework.modules.recon.subdomain_enum import SubdomainEnumModule
        from framework.modules.recon.port_scan import PortScanModule
        from framework.modules.recon.tech_stack_fingerprinter import TechStackFingerprinterModule
        from framework.modules.web.misconfig_scanner import MisconfigScannerModule
        return (
            WorkflowBuilder(self.name)
            .add_step("subdomain_enum", SubdomainEnumModule, required=True)
            .add_step("port_scan", PortScanModule, transformer=lambda prev: {"target": ((prev.output or {}).get("live_hosts") or [""])[0]} if prev else {}, required=False)
            .add_step("tech_stack_fingerprinter", TechStackFingerprinterModule, transformer=lambda prev: {"target": self._url_from_portscan(prev)}, required=False)
            .add_step("misconfig_scanner", MisconfigScannerModule, transformer=lambda prev: {"target": self._normalize_url((prev.output or {}).get("target", ""))} if prev else {}, required=False)
            .build()
            ._steps
        )

    @staticmethod
    def _url_from_portscan(prev):
        if not prev or not prev.output:
            return ""
        open_ports = prev.output.get("open_ports") or []
        if not open_ports:
            return prev.output.get("target", "")
        entry = open_ports[0]
        scheme = "https" if entry.get("port") in (443, 8443) else "http"
        return f"{scheme}://{entry.get('host')}:{entry.get('port')}"

    @staticmethod
    def _normalize_url(target: str) -> str:
        if target.startswith(("http://", "https://")):
            return target
        return f"https://{target}" if target else target


class CredentialAttackChainWorkflow(Workflow):
    name = "credential_attack_chain"
    description = "Breach correlation into credential reuse analysis."

    def steps(self):
        from framework.modules.osint.breach_correlation import BreachCorrelationModule
        from framework.modules.post_exploitation.credential_reuse_analyzer import CredentialReuseAnalyzerModule
        return (
            WorkflowBuilder(self.name)
            .add_step("breach_correlation", BreachCorrelationModule, required=False)
            .add_step("credential_reuse_analyzer", CredentialReuseAnalyzerModule, transformer=lambda prev: {"credentials": self._credentials_from_breach(prev)}, required=False)
            .build()
            ._steps
        )

    @staticmethod
    def _credentials_from_breach(prev):
        if not prev or not prev.output:
            return {"credentials": ""}
        query = prev.output.get("query", "seed")
        return {"credentials": f"{query}:Spring2024!,admin:Spring2024!"}


EXTENDED_WORKFLOWS: Dict[str, Type[Workflow]] = {
    "deep_osint": DeepOSINTWorkflow,
    "attack_surface_mapping": AttackSurfaceMappingWorkflow,
    "credential_attack_chain": CredentialAttackChainWorkflow,
}


class NexusIdentityWorkflow(Workflow):
    name = "nexus_identity_workflow"
    description = "NEXUS identity pipeline with graph-based correlation and behavioral fingerprinting."

    def steps(self):
        from framework.modules.osint.nexus_identity_pipeline import NexusIdentityPipelineModule
        return WorkflowBuilder(self.name).add_step("nexus_identity_pipeline", NexusIdentityPipelineModule, required=True).build()._steps


class ContinuousAttackSurfaceWorkflow(Workflow):
    name = "continuous_attack_surface"
    description = "CASM workflow with monitoring, validation, and structured attack-surface output."

    def steps(self):
        from framework.modules.recon.casm_pipeline import CASMPipelineModule
        return WorkflowBuilder(self.name).add_step("casm_pipeline", CASMPipelineModule, required=True).build()._steps


class CredentialIntelligenceWorkflow(Workflow):
    name = "credential_intelligence"
    description = "Breach-aware credential intelligence and password permutation workflow."

    def steps(self):
        from framework.modules.post_exploitation.credential_intelligence import CredentialIntelligenceModule
        return WorkflowBuilder(self.name).add_step("credential_intelligence", CredentialIntelligenceModule, required=True).build()._steps


class PhysicalWirelessWorkflow(Workflow):
    name = "physical_wireless_audit"
    description = "SDR-oriented physical and wireless auditing workflow."

    def steps(self):
        from framework.modules.wireless.physical_wireless_audit import PhysicalWirelessAuditModule
        return WorkflowBuilder(self.name).add_step("physical_wireless_audit", PhysicalWirelessAuditModule, required=True).build()._steps


EXTENDED_WORKFLOWS.update({
    "nexus_identity_workflow": NexusIdentityWorkflow,
    "continuous_attack_surface": ContinuousAttackSurfaceWorkflow,
    "credential_intelligence": CredentialIntelligenceWorkflow,
    "physical_wireless_audit": PhysicalWirelessWorkflow,
})

try:
    from framework.workflows.autonomous_extensions import EXTREME_WORKFLOWS
    EXTENDED_WORKFLOWS.update(EXTREME_WORKFLOWS)
except Exception:
    EXTREME_WORKFLOWS = {}


class OmegaSOCMINTWorkflow(Workflow):
    name = "omega_socmint"
    description = "15-stage OMEGA-BLACK SOCMINT pipeline with graph ingestion and threat scoring."

    def steps(self):
        from framework.modules.osint.identity_fusion import IdentityFusionModule
        from framework.modules.osint.nexus_identity_pipeline import NexusIdentityPipelineModule
        from framework.modules.osint.breach_correlation import BreachCorrelationModule
        from framework.modules.post_exploitation.credential_intelligence import CredentialIntelligenceModule
        from framework.modules.recon.casm_pipeline import CASMPipelineModule
        return (
            WorkflowBuilder(self.name)
            .add_step("identity_fusion", IdentityFusionModule, required=True)
            .add_step("nexus_identity_pipeline", NexusIdentityPipelineModule, required=False)
            .add_step("breach_correlation", BreachCorrelationModule, transformer=lambda prev: {"query": self._seed_from(prev)}, required=False)
            .add_step("credential_intelligence", CredentialIntelligenceModule, transformer=lambda prev: {"seed": self._seed_from(prev)}, required=False)
            .add_step("casm_pipeline", CASMPipelineModule, transformer=lambda prev: {"target": self._domain_from(prev)}, required=False)
            .build()
            ._steps
        )

    @staticmethod
    def _seed_from(prev):
        if not prev or not prev.output:
            return ""
        return prev.output.get("username") or prev.output.get("query") or prev.output.get("email") or ""

    @staticmethod
    def _domain_from(prev):
        if not prev or not prev.output:
            return ""
        return prev.output.get("domain") or prev.output.get("target") or ""


class OmegaAutonomousLabWorkflow(Workflow):
    name = "omega_autonomous_lab"
    description = "Autonomous development loop for research, validation, repair planning, and reporting."

    def steps(self):
        from framework.modules.osint.nexus_identity_pipeline import NexusIdentityPipelineModule
        from framework.modules.recon.casm_pipeline import CASMPipelineModule
        from framework.modules.post_exploitation.credential_intelligence import CredentialIntelligenceModule
        return (
            WorkflowBuilder(self.name)
            .add_step("research_seed", NexusIdentityPipelineModule, required=False)
            .add_step("surface_revalidation", CASMPipelineModule, transformer=lambda prev: {"target": self._domain_from(prev)}, required=False)
            .add_step("credential_review", CredentialIntelligenceModule, transformer=lambda prev: {"seed": self._seed_from(prev)}, required=False)
            .build()
            ._steps
        )

    @staticmethod
    def _seed_from(prev):
        if not prev or not prev.output:
            return ""
        return prev.output.get("username") or prev.output.get("domain") or ""

    @staticmethod
    def _domain_from(prev):
        if not prev or not prev.output:
            return ""
        return prev.output.get("domain") or prev.output.get("target") or ""


EXTENDED_WORKFLOWS.update({
    "omega_socmint": OmegaSOCMINTWorkflow,
    "omega_autonomous_lab": OmegaAutonomousLabWorkflow,
})
