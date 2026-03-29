# ⚔ RedTeam Framework v2.0

> **Enterprise-grade modular offensive security platform — Authorized testing only.**  
> Professional/government red team scale with Palantir-level data integration, analytics, and multi-layered investigation capabilities.

---

## What's new in v4.0 OMEGA-BLACK

- **23 modules** across 9 categories (recon, osint, AD, cloud, web, crypto, wireless, post-exploitation, network)
- **8 workflows** including `full_ad_compromise`, `identity_fusion`, `ssl_web_recon`, `cloud_audit`
- **Claude AI Stage J** in identity_fusion for intelligent correlation analysis
- **90+ SOCMINT tools** in the 9-stage identity investigation pipeline
- **Metasploit-style console v2** with `setg`, `workspace`, `sessions`, `history/!N`, `grep`, `resource`, `notes`, `creds`, `report`, `spool`
- **Enterprise modules**: Azure AD/Entra, GCP, LDAP, Shodan, SSL/TLS, credential spray, API security
- **Parallel installer v2** with backup commands for 14+ failing tools and exponential backoff
- **Professional reporting engine**: HTML, PDF, XLSX, Markdown, JSON with MITRE ATT&CK mapping
- **OMEGA-BLACK engine fabric**: 12+ architecture engines wired into the existing loader, workflows, API, scheduler, and reporting layers
- **Self-healing controls**: `rtf doctor`, `rtf fix`, `rtf validate`, and `rtf repair` for dependency, loader, and engine validation
- **Neo4j-ready graph intelligence** with Person/Username/Email/Phone/Domain/Organization/Account/Repository/IP/Location/Device/Website/Document/Media entities

---

## Quick Start

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the interactive console (Metasploit-style)
python rtf.py console

# Run a module directly
python rtf.py module run recon/subdomain_enum --options '{"target":"example.com"}'

# Run the full installer
python rtf.py install

# Start the REST API
python rtf.py api --port 8000

# Start the web dashboard
python rtf.py dashboard --port 5000

# Generate the V4 architecture report
python rtf.py upgrade analyze

# Validate the OMEGA-BLACK architecture and self-healing layer
python rtf.py validate
python rtf.py doctor

# Docker
docker-compose up -d
```

---

## Console Commands

```
rtf > use recon/subdomain_enum        # Select a module
rtf > set target example.com          # Set option
rtf > setg domain example.com         # Set GLOBAL option (persists)
rtf > show options                    # Show current options
rtf > run                             # Execute module
rtf > back                            # Deselect module

rtf > search subdomain                # Search modules
rtf > info recon/port_scan            # Module details
rtf > workflows                       # List all 8 workflows
rtf > run_workflow full_recon {"target":"example.com"}

rtf > workspace pentest-corp          # Switch workspace
rtf > notes example.com "Admin panel found at /admin"
rtf > report html reports/engagement.html
rtf > spool logs/session.log          # Log everything to file

rtf > history                         # Command history
rtf > !5                              # Replay command #5
rtf > grep admin search web           # Filter output by regex

rtf > jobs                            # Recent jobs
rtf > findings --severity high        # Filter findings
rtf > db_status                       # Database status
```

---

## Modules (23 total)

| Category | Module | Description |
|----------|--------|-------------|
| recon | subdomain_enum | subfinder + assetfinder + httpx |
| recon | port_scan | naabu + nmap service detection |
| recon | nuclei_scan | Template-based vulnerability scanner |
| recon | ssl_scan | TLS/SSL certificate + protocol analysis |
| recon | shodan_search | Shodan host/search/CVE enumeration |
| osint | username_enum | Sherlock 300+ social networks |
| osint | email_harvest | theHarvester multi-source |
| osint | identity_fusion | **9-stage SOCMINT, 90+ tools, Claude AI** |
| active_directory | bloodhound_collect | BloodHound Python ingestor |
| active_directory | kerberoast | Impacket TGS ticket extraction |
| active_directory | asreproast | AS-REP hash capture |
| cloud | aws_enum | boto3 IAM/S3/EC2/Lambda |
| cloud | azure_enum | Azure AD/Entra ID enumeration |
| cloud | gcp_enum | GCP IAM/Storage/Compute |
| network | ldap_enum | AD LDAP: users, admins, policy, GPOs |
| web | dir_fuzz | ffuf directory/file fuzzing |
| web | xss_scan | dalfox XSS scanner |
| web | sqli_scan | sqlmap automation |
| web | api_security | Security headers, GraphQL, Swagger |
| crypto | hash_crack | hashcat GPU/CPU cracking |
| wireless | wpa2_capture | aircrack-ng WPA2 handshake |
| post_exploitation | privesc_check | SUID/sudo/cron/caps + LinPEAS |
| post_exploitation | credential_spray | Low-and-slow spray: SMB/WinRM/LDAP |

---

## Identity Fusion Pipeline (osint/identity_fusion)

9-stage investigation with 90+ tools and Claude AI correlation:

```
Stage A  Seed normalization
Stage B  Username sweep      (sherlock, maigret, nexfil, blackbird, socialscan + 12 more)
Stage C  Email pivot/breach  (holehe, h8mail, emailrep, dehashed + 5 more)
Stage D  Social media        (instaloader, twint, toutatis, osintgram + 5 more)
Stage E  Domain intel        (theHarvester, spiderfoot, shodan, censys + 16 more)
Stage F  Code/secrets        (gitfive, trufflehog, gitleaks + 4 more)
Stage G  Phone OSINT         (phoneinfoga, email2phonenumber)
Stage H  Dark web/breach     (intelx, pwndb-cli, dehashed + 2 more)
Stage I  Geo/metadata        (creepy, waybackpack, ghunt, exiftool + 16 more)
Stage J  Claude AI correlation & confidence scoring
Stage K  Multi-format report  JSON / CSV / XLSX / PDF / HTML
```

```bash
python rtf.py module run osint/identity_fusion \
  --options '{"username":"target_handle","email":"target@example.com","output_format":"html","use_ai":true}'
```

---

## Workflows (8 built-in)

```
full_recon         subdomain_enum → port_scan → nuclei_scan
ad_attack          bloodhound_collect → kerberoast → asreproast
web_audit          dir_fuzz → xss_scan → sqli_scan → api_security
osint_person       username_enum → email_harvest
identity_fusion    Full 9-stage SOCMINT pipeline
cloud_audit        aws_enum → shodan_search
full_ad_compromise ldap_enum → bloodhound → kerberoast → asreproast
ssl_web_recon      ssl_scan → subdomain_enum → nuclei → api_security
```

---

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/stats` | System stats |
| GET | `/modules` | List all modules |
| POST | `/modules/{cat}/{name}/run` | Execute a module |
| GET | `/workflows` | List workflows |
| POST | `/workflows/{name}/run` | Run a workflow |
| GET | `/jobs` | List jobs (paginated) |
| GET | `/findings` | List findings (paginated) |
| GET | `/tools/summary` | Tool installation summary |

All endpoints also under `/api/v1/...` for versioned access.

---

## Legal Notice

For **authorized testing only**: penetration testing engagements, red team operations with written permission, CTF competitions, and internal security research in controlled lab environments.


## RTF TITAN

RTF v2.4 now includes a backward-compatible TITAN architecture layer for distributed OSINT, SOCMINT, CASM, credential intelligence, graph analytics, AI identity resolution, queue-backed orchestration, and multi-service observability. Use `python rtf.py titan manifest`, `python rtf.py titan health`, or `python rtf.py titan investigate --options ...` to inspect and validate the new distributed layer.


## V4 Upgrade Pipeline

RTF v4.0 now exposes a sequential upgrade pipeline that preserves CLI and module compatibility while generating machine-readable architecture artifacts.

```bash
python rtf.py upgrade analyze   # architecture map + report artifacts
python rtf.py upgrade run       # full sequential agent output
```

The pipeline executes these agents in order:

1. Architecture agent
2. Module builder
3. OSINT pipeline builder
4. SOCMINT pipeline builder
5. Dashboard builder
6. Self-healing system builder
7. Final integration engine

Artifacts are written to `rtf/V4_ARCHITECTURE_REPORT.md` and `rtf/V4_UPGRADE_REPORT.json`.
