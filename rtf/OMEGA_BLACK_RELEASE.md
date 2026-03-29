# RedTeam Framework v4.0 OMEGA-BLACK Release Notes

## Architectural Expansion

RTF v4.0 OMEGA-BLACK extends the existing platform without removing modules, pipelines, or CLI compatibility. The upgrade preserves the dynamic module loader, SQLite persistence, FastAPI API layer, scheduler, and workflow registry while adding an Omega engine registry that maps the following engines into the current architecture:

- rtf-core
- rtf-osint-engine
- rtf-socmint-engine
- rtf-breach-engine
- rtf-scraper-engine
- rtf-casm-engine
- rtf-graph-engine
- rtf-ai-engine
- rtf-credential-engine
- rtf-report-engine
- rtf-monitoring-engine
- rtf-automation-engine
- rtf-worker-cluster

## New Platform Surfaces

- CLI self-healing commands: `doctor`, `fix`, `validate`, `repair`
- FastAPI endpoints: `/omega/manifest`, `/omega/sources`, `/omega/doctor`, `/omega/validate`
- Graph intelligence schema aligned to Neo4j-compatible entities and relationships
- 1000-source OSINT source catalog grouped by username, email, phone, domain, organization, breach, IP, document, and image intelligence
- Autonomous development loop support through engine metadata and workflow registrations

## Backward Compatibility

All existing modules, workflows, pipelines, report formats, and CLI subcommands remain intact. OMEGA-BLACK is an additive architecture layer.
