# RTF v2.0 - Massive Automatic Investigation Pipeline

## Overview

The **Massive Automatic Investigation Pipeline** is the ultimate unified investigation framework that combines **ALL modules, tools, workflows, and pipelines** from the RedTeam Framework into one massive automatic execution engine.

This single entry point orchestrates every component of the framework into a comprehensive, multi-stage investigation that can be executed with a single command.

## Features

### Complete Tool Integration
- **Reconnaissance**: subfinder, amass, assetfinder, altdns, httprobe, naabu, gobuster, ffuf, whatweb, and more
- **OSINT**: sherlock, maigret, holehe, phoneinfoga, osintgram, social-analyzer, profil3r, intelligence-x
- **Scanning**: nuclei, trivy, lynis, openvas, vuls, nikto, sslscan
- **Web Exploitation**: sqlmap, dalfox, xsstrike, wpscan, joomscan, wfuzz, commix, ssrfmap
- **Credential Attacks**: hydra, kerbrute, hashcat, john, ncrack, brutespray
- **Exploitation**: metasploit, autosploit, kubesploit, owtf
- **Post-Exploitation**: bloodhound, linenum, evil-winrm, winpwn
- **Threat Intelligence**: intelowl, threatingestor, ail-framework
- **AI Analysis**: autonomous agents, anomaly detection, attack path generation

### All Workflows & Pipelines
- Executes all 8+ built-in workflows (full_recon, ad_attack, web_audit, osint_person, identity_fusion, etc.)
- Runs advanced automation pipelines (Pipeline V2, AdvancedPipeline)
- Integrates entity graph correlation and relationship mapping

### Multi-Stage Investigation Phases
1. **Phase 1**: Entity graph initialization & target normalization
2. **Phase 2**: Comprehensive reconnaissance (ALL recon tools)
3. **Phase 3**: OSINT investigation (ALL OSINT tools)
4. **Phase 4**: Vulnerability scanning (ALL scanners)
5. **Phase 5**: Web exploitation analysis
6. **Phase 6**: Credential attack simulation
7. **Phase 7**: Exploitation framework execution
8. **Phase 8**: Post-exploitation analysis
9. **Phase 9**: Threat intelligence enrichment
10. **Phase 10**: AI analysis & attack path generation
11. **Phase 11**: Built-in workflows execution
12. **Phase 12**: Automation pipelines execution
13. **Phase 13**: Final correlation & entity graph finalization
14. **Phase 14**: Comprehensive report generation

## Usage

### Basic Usage

```bash
# Investigate a domain
python3 rtf.py investigate -d "example.com" -o ~/results

# Investigate a username across all platforms
python3 rtf.py investigate -u "target_username" -o ~/osint_results

# Investigate an email address
python3 rtf.py investigate -e "user@example.com" -o ~/email_results

# Investigate a phone number
python3 rtf.py investigate -p "+1234567890" -o ~/phone_results

# Auto-detect target type
python3 rtf.py investigate --target "example.com" -o ./output
python3 rtf.py investigate --target "user@example.com" -o ./output
```

### Comprehensive Investigation

```bash
# Full comprehensive investigation (all tools, parallel execution)
python3 rtf.py investigate -d "target.com" --comprehensive -o ~/comprehensive_results

# Active investigation with exploitation enabled
python3 rtf.py investigate -d "target.com" --active-investigation --enable-exploitation -o ~/active_results

# Full-stack investigation
python3 rtf.py investigate -d "target.com" --full-stack -o ~/fullstack_results
```

### AI Autonomous Mode

```bash
# Use AI autonomous agent for intelligent investigation
python3 rtf.py investigate -d "target.com" --ai-autonomous -o ~/ai_results
```

### Passive Only Mode

```bash
# Run only passive reconnaissance (stealthy)
python3 rtf.py investigate -d "target.com" --passive-only -o ~/passive_results
```

### Combined Target Investigation

```bash
# Investigate multiple targets simultaneously
python3 rtf.py investigate \
    -d "example.com" \
    -u "admin" \
    -e "admin@example.com" \
    -p "+1234567890" \
    --comprehensive \
    -o ~/multi_target_results
```

### Performance Options

```bash
# Sequential execution (one tool at a time)
python3 rtf.py investigate -d "target.com" --sequential -o ./results

# Limit concurrency
python3 rtf.py investigate -d "target.com" --max-concurrency 5 -o ./results

# Skip installed check (faster startup)
python3 rtf.py investigate -d "target.com" --skip-installed-check -o ./results
```

### Output Options

```bash
# Disable report generation
python3 rtf.py investigate -d "target.com" --no-reports -o ./results

# Disable saving raw tool output
python3 rtf.py investigate -d "target.com" --no-save-raw -o ./results
```

### Advanced Options

```bash
# Enable credential attacks (requires proper authorization)
python3 rtf.py investigate -d "target.com" --enable-credential-attacks -o ./results

# Select specific profile
python3 rtf.py investigate -d "target.com" --profile aggressive -o ./results
python3 rtf.py investigate -d "target.com" --profile core -o ./results
python3 rtf.py investigate -d "target.com" --profile full -o ./results
```

## Command-Line Arguments

### Target Specification
| Argument | Description |
|----------|-------------|
| `-u, --username` | Username to investigate |
| `-d, --domain` | Domain to investigate |
| `-e, --email` | Email address to investigate |
| `-p, --phone` | Phone number to investigate |
| `-i, --ip` | IP address to investigate |
| `--url` | URL to investigate |
| `--target` | Generic target (auto-detects type) |

### Investigation Modes
| Argument | Description |
|----------|-------------|
| `--comprehensive` | Run comprehensive investigation (all tools) |
| `--full-stack` | Run full-stack investigation including exploitation |
| `--active-investigation` | Enable active scanning and exploitation |
| `--passive-only` | Run only passive reconnaissance |
| `--ai-autonomous` | Use AI autonomous agent for investigation |

### Output Options
| Argument | Description | Default |
|----------|-------------|---------|
| `-o, --output` | Output directory for results | `./investigation_results` |
| `--no-reports` | Disable report generation | Reports enabled |
| `--no-save-raw` | Disable saving raw tool output | Raw saved |

### Performance Options
| Argument | Description | Default |
|----------|-------------|---------|
| `--parallel` | Run tools in parallel | Enabled |
| `--sequential` | Run tools sequentially | Parallel |
| `--max-concurrency` | Maximum concurrent executions | 10 |

### Advanced Options
| Argument | Description |
|----------|-------------|
| `--enable-credential-attacks` | Enable credential attack simulations |
| `--enable-exploitation` | Enable exploitation frameworks |
| `--skip-installed-check` | Skip checking if tools are installed |
| `--profile` | Investigation profile (core/comprehensive/full/aggressive/ai_autonomous) |

## Output Structure

After execution, the output directory will contain:

```
investigation_results/
├── investigation_result_<ID>.json    # Comprehensive JSON result
├── report_<ID>.html                  # HTML report
├── report_<ID>.json                  # JSON report
├── report_<ID>.md                    # Markdown report
├── recon_<tool>_<ID>.json            # Raw recon tool outputs
├── osint_<tool>_<ID>.json            # Raw OSINT tool outputs
├── scan_<tool>_<ID>.json             # Raw scanner outputs
├── web_exploit_<tool>_<ID>.json      # Raw web exploit outputs
├── threat_intel_<tool>_<ID>.json     # Raw threat intel outputs
└── workflows/                        # Workflow execution results
```

## Result Structure

The investigation result includes:

```json
{
  "investigation_id": "abc12345",
  "started_at": "2024-01-01T00:00:00",
  "finished_at": "2024-01-01T01:00:00",
  "duration_seconds": 3600.5,
  "targets": {"domain": "example.com"},
  "profile": "comprehensive",
  "success": true,
  "summary": {
    "tools_executed": 50,
    "tools_successful": 45,
    "tools_failed": 5,
    "total_findings": 150,
    "workflows_run": 8,
    "pipelines_executed": 2
  },
  "recon": {...},
  "osint": {...},
  "scanning": {...},
  "findings": [...],
  "entities": {...},
  "attack_paths": [...],
  "report_files": [...]
}
```

## Profiles

| Profile | Description | Tools Included |
|---------|-------------|----------------|
| `core` | Essential tools only | subfinder, naabu, sherlock, nuclei |
| `comprehensive` | Balanced investigation | Most recon, OSINT, and scanning tools |
| `full` | Complete toolkit | All recon, OSINT, scanning, web exploit tools |
| `aggressive` | Maximum coverage | ALL tools including exploitation |
| `ai_autonomous` | AI-driven selection | Dynamic tool selection based on findings |

## Examples

### Example 1: Quick Domain Recon
```bash
python3 rtf.py investigate -d "target.com" --passive-only -o ./quick_recon
```

### Example 2: Full SOCMINT Investigation
```bash
python3 rtf.py investigate \
    -u "suspect_user" \
    -e "suspect@email.com" \
    --comprehensive \
    -o ./socmint_investigation
```

### Example 3: Corporate Security Assessment
```bash
python3 rtf.py investigate \
    -d "company.com" \
    --comprehensive \
    --max-concurrency 15 \
    -o ./company_assessment
```

### Example 4: AI-Powered Autonomous Investigation
```bash
python3 rtf.py investigate \
    -d "target.org" \
    --ai-autonomous \
    --comprehensive \
    -o ./ai_investigation
```

## Integration with Existing Commands

The investigation pipeline integrates seamlessly with existing RTF commands:

```bash
# After investigation, view findings
rtf findings

# Generate additional reports
rtf report html ./custom_report.html

# View job history
rtf jobs

# List available tools
rtf tools list --installed
```

## Requirements

- Python 3.8+
- All tool dependencies (see `requirements.txt`)
- Proper authorization for target systems
- Sufficient disk space for results

## Legal Notice

**WARNING**: This tool is designed for authorized security testing only. Ensure you have proper written authorization before running investigations against any target. Unauthorized access to computer systems is illegal.

## Support

For issues and feature requests, please refer to the main RTF documentation.

---

**RTF v2.0 - Enterprise RedTeam Platform**
*For Authorized Testing Only*
