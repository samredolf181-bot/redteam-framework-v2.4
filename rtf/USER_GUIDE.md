# RTF v2.0 — Complete Operator User Guide

**RedTeam Framework v2.0 — Enterprise RedTeam Platform**  
*Authorized testing only. Ensure written permission before any engagement.*

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [Installation](#2-installation)
3. [Console Reference (Metasploit-style)](#3-console-reference-metasploit-style)
4. [Module Reference](#4-module-reference)
5. [Workflow Reference](#5-workflow-reference)
6. [Identity Fusion (SOCMINT Pipeline)](#6-identity-fusion-socmint-pipeline)
7. [REST API Reference](#7-rest-api-reference)
8. [Web Dashboard](#8-web-dashboard)
9. [Reporting Engine](#9-reporting-engine)
10. [Tool Registry & Installer](#10-tool-registry--installer)
11. [Configuration Reference](#11-configuration-reference)
12. [Writing Custom Modules](#12-writing-custom-modules)
13. [Building Custom Workflows](#13-building-custom-workflows)
14. [Engagement Workflow — Step by Step](#14-engagement-workflow--step-by-step)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Overview & Architecture

RTF v2.0 is a fully modular offensive security platform built around three principles:

- **Graceful degradation** — every stage works with whatever tools are installed; missing tools are skipped, not fatal
- **Everything is a module** — recon, OSINT, AD attacks, cloud enum, web scanning, crypto, wireless, post-exploitation
- **Investigation graph** — discovered entities (emails, URLs, usernames) automatically flow between stages

### Directory layout

```
rtf/
├── rtf.py                        ← Main entry point (all CLI commands)
├── requirements.txt
├── Dockerfile / docker-compose.yml
├── config/
│   └── framework.yaml            ← Runtime config (paths, API keys, ports)
├── framework/
│   ├── core/
│   │   ├── config.py             ← Singleton config (YAML + env overrides)
│   │   ├── logger.py             ← Structured logging (Rich)
│   │   └── exceptions.py         ← Exception hierarchy
│   ├── db/
│   │   └── database.py           ← SQLite (jobs, findings, targets, tools)
│   ├── modules/
│   │   ├── base.py               ← BaseModule ABC (all modules inherit this)
│   │   ├── loader.py             ← Dynamic module loader & registry
│   │   ├── recon/                ← subdomain_enum, port_scan, nuclei_scan, ssl_scan, shodan_search
│   │   ├── osint/                ← username_enum, email_harvest, identity_fusion, web_search_scraper
│   │   ├── active_directory/     ← bloodhound_collect, kerberoast, asreproast
│   │   ├── cloud/                ← aws_enum, azure_enum, gcp_enum
│   │   ├── network/              ← ldap_enum
│   │   ├── web/                  ← dir_fuzz, xss_scan, sqli_scan, api_security
│   │   ├── crypto/               ← hash_crack
│   │   ├── wireless/             ← wpa2_capture
│   │   └── post_exploitation/    ← privesc_check, credential_spray
│   ├── workflows/
│   │   └── engine.py             ← 8 built-in workflows + WorkflowBuilder
│   ├── cli/
│   │   └── console.py            ← Metasploit-style interactive console
│   ├── api/
│   │   └── server.py             ← FastAPI REST API
│   ├── dashboard/
│   │   └── app.py                ← Flask web dashboard (127.0.0.1:5000)
│   ├── installer/
│   │   └── installer.py          ← Parallel installer with backup commands
│   ├── registry/
│   │   └── tool_registry.py      ← 55+ tool catalogue
│   ├── scheduler/
│   │   └── scheduler.py          ← Async job queue
│   └── reporting/
│       └── engine.py             ← HTML/PDF/XLSX/MD/JSON report generator
├── tests/
│   └── test_framework.py         ← 23 unit + integration tests
└── data/                         ← SQLite DB, logs, outputs
```

---

## 2. Installation

### Minimum requirements

- Python 3.10+
- 2 GB RAM (8 GB recommended for full tool suite)
- Internet connection for tool installation

### Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Install system tools (optional but recommended)

The installer handles everything from APT packages to Go tools, Rust crates, and pipx packages.

```bash
# Full install (takes 20–60 min depending on connection)
python rtf.py install

# Skip sections you don't need
python rtf.py install --skip-apt --skip-rust
python rtf.py install --categories osint,recon,web

# Force reinstall everything
python rtf.py install --force
```

### Step 3 — Verify installation

```bash
python rtf.py tools summary
python rtf.py tools list --installed
python rtf.py tools list --missing
```

### Step 4 — Start the console

```bash
python rtf.py console
```

### Docker (API + Dashboard + Neo4j + Redis)

```bash
docker-compose up -d
# API:       http://localhost:8000
# Dashboard: http://127.0.0.1:5000
# Neo4j:     http://localhost:7474
```

### Environment variables

All config keys can be overridden with `RTF_<KEY_UPPERCASE>`:

```bash
export RTF_API_PORT=9000
export RTF_LOG_LEVEL=DEBUG
export RTF_SHODAN_API_KEY=your_key_here
export RTF_API_KEYS=secret_key_1,secret_key_2
```

---

## 3. Console Reference (Metasploit-style)

Start the console:

```bash
python rtf.py console
```

The console prompt shows your current workspace and active module:

```
rtf >                        # no module selected
rtf (recon/port_scan) >      # module selected
rtf [pentest-corp]>          # workspace active
```

### Module management

| Command | Description | Example |
|---------|-------------|---------|
| `use <path>` | Select a module | `use recon/subdomain_enum` |
| `back` | Deselect current module | `back` |
| `set <opt> <val>` | Set a module option | `set target example.com` |
| `setg <opt> <val>` | Set a **global** option (persists across `back`) | `setg domain corp.local` |
| `unset <opt>` | Clear a module option | `unset output_file` |
| `unsetg <opt>` | Clear a global option | `unsetg domain` |
| `show options` | Show current module options | `show options` |
| `show modules` | List all loaded modules | `show modules` |
| `show categories` | List module categories | `show categories` |
| `show globals` | Show all global options | `show globals` |
| `show jobs` | Show recent job history | `show jobs` |
| `show findings` | Show all findings | `show findings` |
| `show loot` | Show captured credentials/hashes | `show loot` |
| `options` | Alias for `show options` | `options` |
| `info [path]` | Full module details | `info recon/nuclei_scan` |
| `search <term>` | Search modules | `search subdomain` |
| `reload` | Hot-reload all modules from disk | `reload` |

### Execution

| Command | Description | Example |
|---------|-------------|---------|
| `run` | Execute active module | `run` |
| `exploit` | Alias for `run` | `exploit` |
| `run_workflow <name> [opts]` | Run a workflow | `run_workflow full_recon {"target":"example.com"}` |
| `workflows` | List all 8 workflows | `workflows` |
| `resource <file.rc>` | Execute commands from a script file | `resource scripts/enum.rc` |

### Workspace management

Workspaces keep different engagements completely isolated in the console:

```
rtf > workspace client-a         # create/switch to workspace
rtf > workspace client-b
rtf > workspace -l               # list all workspaces
rtf > workspace -d old-ws        # delete a workspace
```

### Investigation notes & credentials

```
rtf > notes 10.0.0.5 "Admin login found — admin:Password1"
rtf > notes 10.0.0.5 "RDP open on 3389"
rtf > notes                      # show all notes
rtf > notes 10.0.0.5             # show notes for target

rtf > creds add admin:Password1@10.0.0.5
rtf > creds list
```

### Data & jobs

```
rtf > jobs                                # last 20 jobs
rtf > findings                            # all findings
rtf > findings --severity high            # filter by severity
rtf > findings --severity critical --limit 10
rtf > targets                             # list targets
rtf > targets add 10.0.0.0/24 cidr
rtf > db_status                           # database stats
```

### Output & reporting

```
rtf > report html reports/engagement.html       # HTML report from all findings
rtf > report pdf  reports/report.pdf
rtf > report xlsx reports/findings.xlsx
rtf > report json reports/data.json

rtf > spool logs/session-2024.log     # log everything to file
rtf > spool off                       # stop logging

rtf > save configs/port_scan.json     # save current module + options
rtf > load configs/port_scan.json     # load saved state
```

### Productivity

```
rtf > history                     # show last 100 commands
rtf > !5                          # replay command #5 from history
rtf > grep open show jobs         # filter job output by regex
rtf > banner                      # random operator quote
rtf > color off                   # disable Rich color (for piping)
rtf > color on                    # re-enable color
rtf > clear                       # clear the screen
rtf > help                        # full command reference
rtf > exit                        # quit (also: quit, Ctrl-D)
```

### Example console session

```
# Start a full recon engagement
rtf > setg target example.com
rtf > setg domain example.com

rtf > workspace pentest-example-com

rtf > use recon/subdomain_enum
rtf > show options
rtf > run

rtf > use recon/port_scan
rtf > set ports top-1000
rtf > set service_detection true
rtf > run

rtf > use recon/nuclei_scan
rtf > set targets data/live_hosts.txt
rtf > set severity critical,high
rtf > run

rtf > findings --severity critical
rtf > report html reports/example-com-report.html
rtf > spool logs/example-com.log
```

---

## 4. Module Reference

### recon/subdomain_enum

Enumerate subdomains using `subfinder` + `assetfinder` in parallel, then probe live hosts with `httpx`.

```bash
python rtf.py module run recon/subdomain_enum --options '{"target":"example.com","resolve_live":true}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `target` | — | Target domain |
| `output_file` | — | Write subdomains to file |
| `resolve_live` | true | Probe with httpx to find live hosts |
| `timeout` | 300 | Per-tool timeout (seconds) |

---

### recon/port_scan

Fast port discovery with `naabu`, optional service/version detection with `nmap -sV`.

```bash
python rtf.py module run recon/port_scan --options '{"target":"10.0.0.1","ports":"top-1000","service_detection":true}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `target` | — | Host / IP / CIDR |
| `ports` | top-100 | `top-100`, `top-1000`, or `80,443,8080` |
| `service_detection` | false | Run nmap -sV on open ports |
| `rate` | 1000 | Packets per second |
| `timeout` | 600 | Scan timeout |

---

### recon/nuclei_scan

Template-based vulnerability scanning with ProjectDiscovery Nuclei.

```bash
python rtf.py module run recon/nuclei_scan --options '{"targets":"example.com","severity":"critical,high"}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `targets` | — | Comma-separated URLs or file path |
| `severity` | critical,high,medium | Filter severity |
| `tags` | — | Template tags filter |
| `templates_dir` | — | Custom templates directory |
| `rate_limit` | 150 | Max requests/sec |
| `concurrency` | 25 | Concurrent templates |

---

### recon/ssl_scan

TLS/SSL certificate analysis: expiry, weak protocols (TLS 1.0/1.1, SSLv2/3). Uses `tlsx` with stdlib fallback.

```bash
python rtf.py module run recon/ssl_scan --options '{"target":"example.com","port":443}'
```

---

### recon/shodan_search

Shodan host/IP lookup and dork search including CVE enumeration.

```bash
python rtf.py module run recon/shodan_search --options '{"query":"8.8.8.8","api_key":"YOUR_KEY","mode":"host"}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `query` | — | IP, hostname, or Shodan dork |
| `api_key` | — | Shodan API key |
| `mode` | host | `host`, `search`, or `count` |
| `limit` | 10 | Max search results |

---

### osint/username_enum

Search for a username across 300+ social networks using Sherlock.

```bash
python rtf.py module run osint/username_enum --options '{"username":"target_handle"}'
```

---

### osint/email_harvest

Harvest emails, subdomains, and hosts from public sources using theHarvester.

```bash
python rtf.py module run osint/email_harvest --options '{"domain":"corp.com","sources":"all","limit":500}'
```

---

### osint/web_search_scraper

Search multiple engines (DuckDuckGo, Bing, Brave, Google, Yahoo, StartPage) for a target and optionally scrape each result page for emails, phones, and social links.

```bash
# Basic search
python rtf.py module run osint/web_search_scraper \
  --options '{"query":"John Smith CEO TechCorp","engines":"duckduckgo,bing,brave"}'

# Full search with page scraping
python rtf.py module run osint/web_search_scraper \
  --options '{"query":"john.smith@corp.com","engines":"duckduckgo,bing,brave,google,yahoo","fetch_pages":true,"max_fetch":10}'

# Google with official API key (avoids blocks)
python rtf.py module run osint/web_search_scraper \
  --options '{"query":"target_username","engines":"google","google_api_key":"AIza...","google_cx":"cx_id"}'

# Brave with official API key
python rtf.py module run osint/web_search_scraper \
  --options '{"query":"target@email.com","engines":"brave","brave_api_key":"BSA..."}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `query` | — | Name, username, email, or any phrase |
| `engines` | duckduckgo,bing,brave | Comma-separated engine list |
| `results_per_engine` | 10 | Results to fetch per engine |
| `fetch_pages` | false | Scrape each result page |
| `max_fetch` | 5 | Max pages to scrape |
| `timeout` | 20 | Per-request timeout |
| `delay` | 1.5 | Seconds between engine requests |
| `google_api_key` | — | Google Custom Search API key |
| `google_cx` | — | Google Custom Search CX ID |
| `brave_api_key` | — | Brave Search API key |
| `deduplicate` | true | Remove duplicate URLs |
| `output_file` | — | Save results as JSON |

**Supported engines:**

| Engine | Method | Key Required |
|--------|--------|--------------|
| DuckDuckGo | HTML scrape | No |
| Bing | HTML scrape | No |
| Brave | HTML scrape / API | Optional |
| Google | HTML scrape / CSE API | Optional (recommended) |
| Yahoo | HTML scrape | No |
| StartPage | HTML scrape | No |

> **Tip:** DuckDuckGo and Bing are most reliable for HTML scraping. Google actively rate-limits scrapers — use the official Custom Search API (100 free queries/day) if you need consistent Google results.

---

### osint/identity_fusion

See [Section 6](#6-identity-fusion-socmint-pipeline) for the full pipeline reference.

---

### active_directory/bloodhound_collect

Collect Active Directory data for BloodHound analysis.

```bash
python rtf.py module run active_directory/bloodhound_collect \
  --options '{"domain":"corp.local","dc_ip":"10.0.0.1","username":"user","password":"Pass123"}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `domain` | — | AD domain FQDN |
| `dc_ip` | — | Domain Controller IP |
| `username` | — | Domain username |
| `password` | — | Domain password |
| `collection_method` | All | All, DCOnly, Session, LoggedOn, Trusts |
| `output_dir` | /tmp/bloodhound_output | Output directory for JSON zip |

---

### active_directory/kerberoast

Extract Kerberos TGS tickets for service accounts via Impacket `GetUserSPNs.py`.

```bash
python rtf.py module run active_directory/kerberoast \
  --options '{"domain":"corp.local","dc_ip":"10.0.0.1","username":"user","password":"Pass123"}'
```

---

### active_directory/asreproast

AS-REP Roasting — capture hashes for accounts without Kerberos pre-auth.

```bash
python rtf.py module run active_directory/asreproast \
  --options '{"domain":"corp.local","dc_ip":"10.0.0.1","users_file":"/tmp/users.txt"}'
```

---

### network/ldap_enum

Enumerate Active Directory over LDAP: users, domain admins, password policy, GPOs.

```bash
python rtf.py module run network/ldap_enum \
  --options '{"dc_ip":"10.0.0.1","domain":"corp.local","username":"corp\\user","password":"Pass123","checks":"users,admins,policy"}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `dc_ip` | — | Domain Controller IP |
| `domain` | — | Domain FQDN (corp.local) |
| `username` | — | DOMAIN\\user or user@domain |
| `password` | — | Bind password |
| `checks` | users,admins,policy | users, admins, policy, gpos, computers, spns |
| `use_ssl` | false | Use LDAPS (port 636) |

---

### cloud/aws_enum

Enumerate AWS: IAM users/roles, S3 buckets (public access detection), EC2, Lambda.

```bash
python rtf.py module run cloud/aws_enum \
  --options '{"access_key_id":"AKIA...","secret_access_key":"...","checks":"iam,s3,ec2,lambda"}'
```

---

### cloud/azure_enum

Enumerate Azure AD/Entra ID: users, groups, applications, subscriptions.

```bash
python rtf.py module run cloud/azure_enum \
  --options '{"tenant_id":"...","client_id":"...","client_secret":"...","checks":"users,groups,apps"}'
```

---

### cloud/gcp_enum

Enumerate Google Cloud Platform: IAM bindings, public buckets, compute.

```bash
python rtf.py module run cloud/gcp_enum \
  --options '{"project_id":"my-project","service_account_json":"/path/to/sa.json","checks":"iam,storage,compute"}'
```

---

### web/dir_fuzz

High-speed directory and file fuzzing with `ffuf`.

```bash
python rtf.py module run web/dir_fuzz \
  --options '{"url":"https://example.com/FUZZ","wordlist":"/usr/share/seclists/Discovery/Web-Content/common.txt"}'
```

---

### web/xss_scan

XSS scanning with `dalfox` (primary) and XSStrike fallback.

```bash
python rtf.py module run web/xss_scan \
  --options '{"url":"https://example.com/search?q=test","cookies":"session=abc"}'
```

---

### web/sqli_scan

SQL injection detection using `sqlmap`.

```bash
python rtf.py module run web/sqli_scan \
  --options '{"url":"https://example.com/item?id=1","level":3,"risk":2}'
```

---

### web/api_security

API security: missing security headers, dangerous HTTP methods, GraphQL introspection, OpenAPI/Swagger exposure.

```bash
python rtf.py module run web/api_security --options '{"url":"https://api.example.com"}'
```

---

### crypto/hash_crack

GPU/CPU offline hash cracking with `hashcat`. Supports NTLM, bcrypt, kerberoast, WPA2, and 20+ other hash types.

```bash
python rtf.py module run crypto/hash_crack \
  --options '{"hash_file":"/tmp/hashes.txt","hash_type":"ntlm","wordlist":"/usr/share/wordlists/rockyou.txt"}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `hash_file` | — | File with hashes (one per line) |
| `hash_type` | — | ntlm, sha1, md5, bcrypt, kerberoast, asreproast, wpa2, etc. |
| `wordlist` | /usr/share/wordlists/rockyou.txt | Wordlist path |
| `rules` | — | Hashcat rules file |
| `attack_mode` | dictionary | dictionary, bruteforce, hybrid_wordlist_mask |
| `mask` | — | Bruteforce mask e.g. `?a?a?a?a?a?a` |
| `workload` | 2 | 1=low, 2=default, 3=high, 4=nightmare |

---

### post_exploitation/privesc_check

Linux privilege escalation: SUID binaries, sudo rules, cron jobs, capabilities. Optionally downloads and runs LinPEAS.

```bash
python rtf.py module run post_exploitation/privesc_check --options '{"run_linpeas":true}'
```

---

### post_exploitation/credential_spray

Low-and-slow credential spraying: SMB, WinRM, LDAP, HTTP. Lockout-aware with configurable threshold and automatic pause.

```bash
python rtf.py module run post_exploitation/credential_spray \
  --options '{"targets":"10.0.0.1,10.0.0.2","usernames":"users.txt","passwords":"Spring2024!,Winter2023!","protocol":"smb","delay":30}'
```

| Option | Default | Description |
|--------|---------|-------------|
| `targets` | — | Comma-separated IPs or file path |
| `usernames` | — | Comma-separated usernames or file |
| `passwords` | — | Comma-separated passwords or file |
| `protocol` | smb | smb, winrm, ldap, http, https |
| `delay` | 30 | Seconds between spray rounds |
| `lockout_threshold` | 3 | Stop after this many lockouts detected |

---

### wireless/wpa2_capture

WPA2 4-way handshake capture using the aircrack-ng suite. Sends optional deauth frames to force re-association.

```bash
python rtf.py module run wireless/wpa2_capture \
  --options '{"interface":"wlan0","bssid":"AA:BB:CC:DD:EE:FF","channel":"6","capture_duration":120}'
```

---

## 5. Workflow Reference

Workflows chain multiple modules together, automatically piping output between stages.

```bash
# List all workflows
python rtf.py workflow list

# Run a workflow
python rtf.py workflow run full_recon --options '{"target":"example.com"}'

# In the console
rtf > workflows
rtf > run_workflow full_recon {"target":"example.com"}
rtf > run_workflow full_ad_compromise {"domain":"corp.local","dc_ip":"10.0.0.1","username":"user","password":"Pass123"}
```

### full_recon
**Chain:** `subdomain_enum` → `port_scan` → `nuclei_scan`

Full external recon: find subdomains, scan ports on live hosts, run Nuclei templates.

```bash
python rtf.py workflow run full_recon --options '{"target":"example.com"}' --output-dir reports/
```

### ad_attack
**Chain:** `bloodhound_collect` → `kerberoast` → `asreproast`

Active Directory attack chain: collect BloodHound data, kerberoast service accounts, AS-REP roast.

```bash
python rtf.py workflow run ad_attack \
  --options '{"domain":"corp.local","dc_ip":"10.0.0.1","username":"jsmith","password":"Password1"}'
```

### web_audit
**Chain:** `dir_fuzz` → `xss_scan` → `sqli_scan` → `api_security`

Full web application audit pipeline.

```bash
python rtf.py workflow run web_audit --options '{"url":"https://example.com/FUZZ"}'
```

### osint_person
**Chain:** `username_enum` → `email_harvest`

Quick OSINT sweep: find social accounts then harvest emails.

```bash
python rtf.py workflow run osint_person --options '{"username":"target_handle","domain":"example.com"}'
```

### identity_fusion
**Chain:** Full 9-stage SOCMINT pipeline (see Section 6)

```bash
python rtf.py workflow run identity_fusion \
  --options '{"username":"target","email":"t@example.com","output_format":"html"}'
```

### cloud_audit
**Chain:** `aws_enum` → `shodan_search`

AWS enumeration followed by Shodan exposure check.

```bash
python rtf.py workflow run cloud_audit \
  --options '{"access_key_id":"AKIA...","secret_access_key":"...","query":"8.8.8.8"}'
```

### full_ad_compromise
**Chain:** `ldap_enum` → `bloodhound_collect` → `kerberoast` → `asreproast`

Full AD compromise chain: LDAP recon, BloodHound collection, credential capture.

```bash
python rtf.py workflow run full_ad_compromise \
  --options '{"domain":"corp.local","dc_ip":"10.0.0.1","username":"user","password":"Pass123"}'
```

### ssl_web_recon
**Chain:** `ssl_scan` → `subdomain_enum` → `nuclei_scan` → `api_security`

Certificate audit + full external recon + API security checks.

```bash
python rtf.py workflow run ssl_web_recon --options '{"target":"example.com"}'
```

---

## 6. Identity Fusion (SOCMINT Pipeline)

`osint/identity_fusion` is the flagship module — a 11-stage investigation pipeline that uses 90+ SOCMINT tools plus multi-engine web search and Claude AI correlation.

### Quick start

```bash
# Minimum seed: username only
python rtf.py module run osint/identity_fusion --options '{"username":"target_handle"}'

# Full seeds + HTML report
python rtf.py module run osint/identity_fusion \
  --options '{
    "username":  "target_handle",
    "email":     "target@example.com",
    "full_name": "John Smith",
    "domain":    "example.com",
    "output_format": "html"
  }'

# Aggressive profile + AI + web search
python rtf.py module run osint/identity_fusion \
  --options '{
    "username":        "target_handle",
    "tool_profile":    "aggressive",
    "scrape_accounts": true,
    "web_search":      true,
    "search_engines":  "duckduckgo,bing,brave,yahoo",
    "use_ai":          true,
    "output_format":   "xlsx"
  }'
```

### Pipeline stages

| Stage | Name | Tools | Description |
|-------|------|-------|-------------|
| A | Seed normalization | — | Parse and validate all input seeds |
| B | Username sweep | sherlock, maigret, nexfil, blackbird, socialscan, whatsmyname, social-analyzer, snoop, osrframework, seekr, profil3r, namechk, checkusernames, peekyou, usersearch (+2) | Discover all accounts for the username across 300+ networks |
| B2 | Deep account scraping | twint, instaloader, gitfive, toutatis, snscrape, twscrape + generic httpx | Scrape every discovered profile URL for bio, followers, emails, linked accounts |
| B3 | Multi-engine web search | DuckDuckGo, Bing, Brave, Google, Yahoo, StartPage | Search all engines for username/name/email mentions |
| C | Email pivot & breach | holehe, h8mail, emailrep, ignorant, dehashed, breach-parse, emailfinder, hibp | Check email registrations, breach exposure |
| D | Social media deep dive | instaloader, toutatis, twint, tinfoleak, socid-extractor, osintgram, twscrape, snscrape, reddit-user-analyser | Deep-dive individual platforms |
| E | Domain intelligence | theHarvester, spiderfoot, metagoofil, dnstwist, linkedin2username, crosslinked, photon, subfinder, amass, shodan, censys, urlscan (+more) | Domain, email, subdomain, and exposure intel |
| F | Code/secrets forensics | gitfive, octosuite, trufflehog, gitleaks, gitrecon, gharchive, intelowl | GitHub OSINT, credential leaks, repository analysis |
| G | Phone OSINT | phoneinfoga, email2phonenumber | Phone number lookup and email-to-phone pivot |
| H | Dark web & breach | intelx, pwndb-cli, dehashed, skymem | Breach databases and dark web exposure |
| I | Geolocation & metadata | creepy, waybackpack, ghunt, sn0int, buster, exiftool, foca, archivebox, harpoon, waymore, mentionmapp, clearbit, fullcontact, pipl, hunter (+more) | Location intelligence, metadata, historical data |
| J | Claude AI correlation | claude-sonnet-4-20250514 | AI-powered correlation, confidence scoring, anomaly detection |
| K | Multi-format report | — | JSON / CSV / XLSX / PDF / HTML |

### Stage B2 — Deep account scraping

For every account URL discovered in Stage B, B2 runs three layers:

1. **CLI tool** (if installed): `twint` for Twitter, `instaloader` for Instagram, `gitfive` for GitHub, etc.
2. **JSON/API endpoint**: GitHub API, Reddit API, Mastodon API, HN Firebase — no auth required
3. **HTTP scraper fallback**: fetches the profile page and extracts:
   - `bio`, `display_name`, `followers`, `following`, `posts`
   - `location`, `website`, `joined`, `verified`
   - `emails_found` — emails scraped from the page
   - `phones_found` — phone numbers
   - `linked_accounts` — cross-platform links (e.g. GitHub bio linking to Twitter)
   - `post_samples` — up to 5 real post snippets

Scraped data automatically feeds back into the entity graph.

### Stage B3 — Multi-engine web search

Generates queries from all available seeds and searches each configured engine:

- `"username"` — direct username search
- `"Full Name"` — quoted name search
- `email@domain.com` — email search
- `"username" site:twitter.com OR site:instagram.com OR site:github.com` — cross-platform query
- `"username" email OR contact OR profile` — contact discovery

Each result page is optionally fetched to extract emails, phones, and social links.

### Stage J — Claude AI Correlation

Sends all gathered entities + scraped profile summaries to Claude. Returns:

- `confidence_score` (0–100) — how likely all data belongs to one person
- `identity_summary` — most likely real-world identity
- `primary_aliases` — most-used handles
- `cross_platform_timeline` — account creation chronology
- `location_indicators` — geographic clues
- `bio_consistency_score` — how consistent bios are across platforms
- `anomalies` — suspicious discrepancies
- `risk_level` — LOW / MEDIUM / HIGH / CRITICAL
- `top_pivots` — 5 next investigative actions
- `linked_identity_graph` — maps each username to confirmed platforms

Falls back to rule-based analysis if the API is unavailable.

### All options

| Option | Default | Description |
|--------|---------|-------------|
| `username` | — | Seed username |
| `email` | — | Seed email address |
| `full_name` | — | Seed full name |
| `phone` | — | Seed phone (E.164 format, e.g. +1234567890) |
| `domain` | — | Seed domain |
| `image_url` | — | Image URL for reverse image search |
| `tool_profile` | core | `core` (5 tools/stage), `full` (10), `aggressive` (all) |
| `stages` | all | Comma-separated: `B,C,D,E` or `all` |
| `scrape_accounts` | true | Enable Stage B2 account scraping |
| `scrape_timeout` | 20 | Per-URL scrape timeout |
| `max_scrape_urls` | 50 | Max URLs to scrape in B2 |
| `scrape_concurrency` | 8 | Parallel HTTP connections for scraping |
| `web_search` | true | Enable Stage B3 web search |
| `search_engines` | duckduckgo,bing,brave | Engines to use |
| `search_results` | 10 | Results per engine per query |
| `search_fetch` | true | Scrape each search result page |
| `search_max_fetch` | 5 | Max result pages to scrape per query |
| `search_delay` | 1.5 | Seconds between engine requests |
| `google_api_key` | — | Google Custom Search API key |
| `google_cx` | — | Google Custom Search CX ID |
| `brave_api_key` | — | Brave Search API key |
| `use_ai` | true | Enable Stage J Claude AI correlation |
| `output_format` | json | `json`, `csv`, `xlsx`, `pdf`, `html` |
| `output_file` | auto | Explicit output path |
| `concurrency` | 4 | Parallel tools per stage |
| `max_pivots` | 500 | Max items per entity type |

---

## 7. REST API Reference

Start the API:

```bash
python rtf.py api --host 0.0.0.0 --port 8000
```

### Authentication

Enable API key authentication in `config/framework.yaml`:

```yaml
api_keys:
  - your_secret_key_1
  - your_secret_key_2
```

Then include the header `X-API-Key: your_secret_key_1` on all requests.

### Endpoints

All endpoints available at both `/endpoint` and `/api/v1/endpoint`.

```bash
# System
GET  /health                          # Health check
GET  /stats                           # Module/tool/job counts

# Modules
GET  /modules                         # List all modules
GET  /modules?category=recon          # Filter by category
GET  /modules/search?q=subdomain      # Full-text search
GET  /modules/{cat}/{name}            # Module info + options
POST /modules/{cat}/{name}/run        # Execute (async, returns job_id)
     Body: {"options": {"target": "example.com"}}

# Workflows
GET  /workflows                       # List all workflows
POST /workflows/{name}/run            # Run workflow (async)
     Body: {"options": {...}, "output_dir": "/tmp/output"}

# Jobs (paginated)
GET  /jobs?limit=50&offset=0          # List jobs
GET  /jobs/{id}                       # Job details + status

# Findings (paginated)
GET  /findings?severity=high&limit=100
GET  /findings?job_id=abc123&offset=0

# Targets
GET  /targets
POST /targets  Body: {"value":"example.com","type":"domain"}

# Tools
GET  /tools                           # Full tool list
GET  /tools?category=recon&installed=true
GET  /tools/summary                   # Installation counts
POST /tools/{name}/install            # Install a tool
POST /tools/refresh                   # Re-check all installations

# Scheduler
GET  /scheduler/jobs                  # Scheduled job list
```

### Example API usage

```bash
# Run a module
curl -X POST http://localhost:8000/modules/recon/subdomain_enum/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{"options": {"target": "example.com"}}'
# Response: {"job_id": "abc-123", "status": "running", "module": "recon/subdomain_enum"}

# Poll job status
curl http://localhost:8000/jobs/abc-123 -H "X-API-Key: your_key"

# Fetch findings
curl "http://localhost:8000/findings?severity=critical&limit=20" -H "X-API-Key: your_key"

# Run identity fusion workflow
curl -X POST http://localhost:8000/workflows/identity_fusion/run \
  -H "Content-Type: application/json" \
  -d '{"options": {"username":"target","email":"t@example.com","output_format":"html"}}'
```

---

## 8. Web Dashboard

Start the dashboard:

```bash
python rtf.py dashboard --port 5000
# Open: http://127.0.0.1:5000
```

The dashboard provides:
- **System overview** — modules, tools (installed/total), findings count
- **Tool installation chart** — bar chart by category
- **Module browser** — searchable table with one-click "Run" modal
- **Findings table** — all findings with severity badges
- **Workflow launcher** — click any workflow to launch with custom options
- **Recent jobs** — live status feed

The Run and Workflow modals accept JSON options and submit to the REST API.

---

## 9. Reporting Engine

Generate reports from all database findings:

```bash
# From CLI
python rtf.py report --format html --output reports/engagement.html
python rtf.py report --format pdf  --output reports/engagement.pdf
python rtf.py report --format xlsx --output reports/findings.xlsx

# From console
rtf > report html reports/client-report.html
rtf > report pdf  reports/executive-summary.pdf
```

### Formats

| Format | Content | Requires |
|--------|---------|----------|
| HTML | Full interactive report with severity stats | Nothing |
| PDF | Professional PDF with MITRE mapping | reportlab |
| XLSX | 3 sheets: Findings, Summary, MITRE ATT&CK | openpyxl |
| Markdown | Severity tables + finding list | Nothing |
| JSON | Machine-readable structured data | Nothing |

All formats include:
- **Executive summary** with severity breakdown and risk score
- **MITRE ATT&CK** mapping (auto-inferred from finding tags)
- **Finding details** with target, description, evidence
- **Metadata**: operator, workspace, timestamp

---

## 10. Tool Registry & Installer

### Check tool status

```bash
python rtf.py tools list                    # all tools
python rtf.py tools list --installed        # installed only
python rtf.py tools list --missing          # missing only
python rtf.py tools list --category recon   # by category
python rtf.py tools summary                 # counts by category
```

### Install tools

```bash
# Install a single tool
python rtf.py tools install nuclei
python rtf.py tools install sherlock

# Full installer
python rtf.py install

# Skip sections
python rtf.py install --skip-apt --skip-rust
python rtf.py install --categories osint,recon,web

# Skip git repos (fastest for Python/Go only)
python rtf.py install --skip-repos
```

### Installer features

The installer v2 includes:
- **Parallel execution**: Go tools (8 concurrent), git clones (15 concurrent), APT (10 concurrent)
- **Exponential backoff retry**: 3 attempts per tool with 2s → 4s → 8s delays
- **14+ backup install strategies** for commonly-failing tools (crackmapexec, evil-winrm, bloodhound, ghidra, wifite, bettercap, radare2, nikto, neo4j, masscan, hcxtools, sherlock, amass, feroxbuster, and more)
- **Smart skip**: already-installed tools are not reinstalled unless `--force` is used
- **Per-tool install log** saved to `logs/install_<timestamp>.log`

---

## 11. Configuration Reference

Edit `config/framework.yaml` for persistent settings.

```yaml
# Paths
base_dir:     ~/redteam-lab
tools_dir:    ~/redteam-lab/tools
data_dir:     ~/redteam-lab/data
logs_dir:     ~/redteam-lab/logs
db_path:      ~/redteam-lab/data/framework.db

# API Server
api_host:     0.0.0.0
api_port:     8000
api_keys:     []         # Leave empty to disable auth, or add keys

# Web Dashboard (localhost only for security)
dashboard_host: 127.0.0.1
dashboard_port: 5000

# Logging
log_level:    INFO       # DEBUG, INFO, WARNING, ERROR

# External API keys (optional — enhance module capabilities)
shodan_api_key:      ""
censys_api_id:       ""
censys_api_secret:   ""
virustotal_api_key:  ""
hunter_api_key:      ""
```

All values can be overridden at runtime with environment variables:

```bash
export RTF_API_PORT=9000
export RTF_LOG_LEVEL=DEBUG
export RTF_SHODAN_API_KEY=abc123
export RTF_API_KEYS="key1,key2"
export RTF_DASHBOARD_PORT=8080
```

---

## 12. Writing Custom Modules

Every module inherits from `BaseModule`. The minimum is: `info()`, `_declare_options()`, and `run()`.

```python
# framework/modules/recon/my_scanner.py
from framework.modules.base import BaseModule, ModuleResult, Severity

class MyScannerModule(BaseModule):

    def info(self):
        return {
            "name":        "my_scanner",
            "description": "My custom recon module",
            "author":      "Your Name",
            "category":    "recon",       # determines which directory it goes in
            "version":     "1.0",
            "references":  ["https://example.com/tool"],
            "tags":        ["recon", "custom"],
        }

    def _declare_options(self):
        # required=True options must be set before run() is called
        self._register_option("target",  "Target host or IP", required=True)
        self._register_option("timeout", "Timeout seconds",   required=False, default=60,    type=int)
        self._register_option("verbose", "Verbose output",    required=False, default=False, type=bool)
        self._register_option("mode",    "Scan mode",         required=False, default="fast",
                              choices=["fast", "full", "stealth"])

    async def run(self) -> ModuleResult:
        target  = self.get("target")
        timeout = self.get("timeout")

        # Check tool is installed (raises ToolNotInstalledError if missing)
        self.require_tool("nmap")

        # Run an async subprocess
        stdout, stderr, rc = await self.run_command_async(
            ["nmap", "-T4", "-Pn", target],
            timeout=timeout,
        )

        # Create findings
        findings = []
        if "open" in stdout:
            findings.append(self.make_finding(
                title=f"Open ports on {target}",
                target=target,
                severity=Severity.MEDIUM,
                description=f"nmap found open ports",
                evidence={"raw": stdout[:500]},
                tags=["recon", "ports"],
            ))

        return ModuleResult(
            success=rc == 0,
            output={"raw": stdout, "target": target},
            findings=findings,
            raw_output=stdout,
            error=stderr if rc != 0 else None,
        )
```

The module is **auto-discovered** on next `reload` or framework restart — no registration needed.

### Option types

```python
self._register_option("count",   "A number",     type=int,   default=5)
self._register_option("enabled", "A flag",       type=bool,  default=True)
self._register_option("ratio",   "A float",      type=float, default=0.5)
self._register_option("mode",    "One of these", choices=["a","b","c"], default="a")
```

### Severity levels

```python
Severity.CRITICAL  # RCE, credential capture, domain compromise
Severity.HIGH      # SQLi, XSS, public S3, kerberoastable accounts
Severity.MEDIUM    # Info disclosure, weak configs, missing headers
Severity.LOW       # Minor findings, informational issues
Severity.INFO      # Enumeration results, discovered assets
```

---

## 13. Building Custom Workflows

Use `WorkflowBuilder` for fluent workflow construction:

```python
from framework.workflows.engine import WorkflowBuilder
from framework.modules.recon.subdomain_enum import SubdomainEnumModule
from framework.modules.recon.port_scan import PortScanModule

wf = (
    WorkflowBuilder("my_workflow")
    .with_options(target="example.com")
    .add_step("subdomains", SubdomainEnumModule, required=True)
    .add_step(
        "port_scan",
        PortScanModule,
        options={"ports": "top-100"},
        # Pipe live_hosts from previous step into target option
        pipe_key="live_hosts",
        pipe_option="target",
        retry_count=1,   # retry once on failure
    )
    .build()
)

import asyncio
result = asyncio.run(wf.run(output_dir="/tmp/reports"))
print(result.to_dict())
```

The `option_transformer` parameter lets you write arbitrary logic to map one step's output into the next step's options:

```python
def extract_targets(prev_result):
    if prev_result and prev_result.output:
        live = prev_result.output.get("live_hosts", [])
        return {"targets": ",".join(live[:20])}
    return {}

.add_step("nuclei", NucleiScanModule, option_transformer=extract_targets)
```

---

## 14. Engagement Workflow — Step by Step

### External penetration test

```bash
# 1. Set up workspace and global options
rtf > workspace client-external-2024
rtf > setg domain example.com
rtf > setg target example.com

# 2. Subdomain enumeration
rtf > use recon/subdomain_enum
rtf > run
# → Saves to output, populates live_hosts

# 3. Port scan all live hosts
rtf > use recon/port_scan
rtf > set ports top-1000
rtf > set service_detection true
rtf > run

# 4. Vulnerability scan
rtf > use recon/nuclei_scan
rtf > set targets data/live_hosts.txt
rtf > set severity critical,high,medium
rtf > run

# 5. SSL/TLS audit
rtf > use recon/ssl_scan
rtf > set target example.com
rtf > run

# 6. Web application testing
rtf > use web/dir_fuzz
rtf > set url https://example.com/FUZZ
rtf > run

rtf > use web/api_security
rtf > set url https://api.example.com
rtf > run

# 7. Generate report
rtf > report html reports/example-com-external.html
```

### OSINT / person investigation

```bash
# 1. Quick identity sweep
rtf > use osint/identity_fusion
rtf > set username target_handle
rtf > set email target@example.com
rtf > set output_format html
rtf > set tool_profile full
rtf > run

# 2. Targeted web search
rtf > use osint/web_search_scraper
rtf > set query '"John Smith" "target@example.com"'
rtf > set engines duckduckgo,bing,brave,yahoo
rtf > set fetch_pages true
rtf > run

# 3. Review and pivot
rtf > findings
rtf > notes target_handle "LinkedIn found: linkedin.com/in/jsmith-tech"
```

### Active Directory attack chain

```bash
# 1. LDAP recon
rtf > use network/ldap_enum
rtf > set dc_ip 10.0.0.1
rtf > set domain corp.local
rtf > set username "corp\lowpriv"
rtf > set password Password1
rtf > run

# 2. BloodHound collection
rtf > use active_directory/bloodhound_collect
rtf > set domain corp.local
rtf > set dc_ip 10.0.0.1
rtf > set username "corp\lowpriv"
rtf > set password Password1
rtf > run

# 3. Kerberoast
rtf > use active_directory/kerberoast
rtf > set domain corp.local
rtf > set dc_ip 10.0.0.1
rtf > set username "corp\lowpriv"
rtf > set password Password1
rtf > set output_file /tmp/tgs_hashes.txt
rtf > run

# 4. Crack the hashes
rtf > use crypto/hash_crack
rtf > set hash_file /tmp/tgs_hashes.txt
rtf > set hash_type kerberoast
rtf > set wordlist /usr/share/wordlists/rockyou.txt
rtf > run

# 5. Credential spray with cracked passwords
rtf > use post_exploitation/credential_spray
rtf > set targets 10.0.0.0/24
rtf > set usernames data/ad_users.txt
rtf > set passwords "Cracked_Password_1"
rtf > set protocol smb
rtf > set delay 60
rtf > run
```

---

## 15. Troubleshooting

### Console won't start

```bash
# Check Python version
python --version  # Must be 3.10+

# Check dependencies
pip install -r requirements.txt

# Run with debug logging
RTF_LOG_LEVEL=DEBUG python rtf.py console
```

### Module fails with "Tool not installed"

```bash
# Check what's missing
python rtf.py tools list --missing

# Install a specific tool
python rtf.py tools install nuclei
python rtf.py tools install sherlock

# Install all tools for a category
python rtf.py install --categories recon
```

### Identity fusion: all tools show as missing

This is normal if tools aren't installed. The module still runs and produces results from installed tools. Install the tools you need:

```bash
python rtf.py install --categories osint
pip install sherlock-project maigret holehe h8mail instaloader socialscan
```

### Web search returns 0 results (Google)

Google actively blocks scrapers. Solutions:
1. Use DuckDuckGo or Bing instead (more reliable without keys)
2. Set up a [Google Custom Search Engine](https://programmablesearchengine.google.com/) (free, 100 queries/day) and use `google_api_key` + `google_cx` options
3. Increase `search_delay` to 3–5 seconds

### API authentication fails

```bash
# Check your config
grep api_keys config/framework.yaml

# Or use env var
export RTF_API_KEYS="your_secret_key"

# Test
curl http://localhost:8000/health -H "X-API-Key: your_secret_key"
```

### DB errors on startup

```bash
# Reset the database (loses all findings/jobs)
rm data/framework.db
python rtf.py console  # will recreate it
```

### Scheduler hangs on stop

This happens if a long-running job is in progress. Press `Ctrl-C` twice to force exit. The job will resume next time via the DB status.

### Modules not reloading after edit

```bash
rtf > reload          # hot-reload all modules from disk
```

### Report generation fails (PDF)

```bash
pip install reportlab  # for PDF support
pip install openpyxl   # for XLSX support
```

---

## Legal Notice

This framework is intended exclusively for:
- Authorized penetration testing engagements with written permission
- Red team operations with explicit client authorization
- CTF competitions
- Internal security research in isolated lab environments

**Unauthorized use against systems you do not own or lack explicit written permission to test is illegal under the Computer Fraud and Abuse Act (CFAA), Computer Misuse Act (UK), and equivalent legislation in most jurisdictions.**

The developers assume no liability for misuse. Always obtain written authorization before testing.

---

*RTF v2.0 — RedTeam Framework — Enterprise RedTeam Platform*

## v6.0 Additions

- Workspaces API: `/api/v1/workspaces`
- Evidence Vault API: `/api/v1/evidence`
- Timeline API: `/api/v1/timeline`
- AI Agent API: `/api/v1/agents`
- Dossier API: `/api/v1/dossiers`
- Plugin API: `/api/v1/plugins`

Use `rtf/scripts/install_v6.sh` to bootstrap the v6 schema and directories.
