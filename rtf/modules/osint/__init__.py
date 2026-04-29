"""
RTF OSINT Module - Massive Expansion
500+ Tools Integrated Across 22 Categories
"""

__version__ = "5.0.0"
__author__ = "RTF Team"

from .username import *
from .email import *
from .phone import *
from .social_media import *
from .domain_dns import *
from .web_scraping import *
from .image import *
from .geolocation import *
from .blockchain import *
from .darknet import *
from .document import *
from .corporate import *
from .threat_intel import *
from .network import *
from .vuln_scan import *
from .web_app import *
from .directory_fuzz import *
from .password_attacks import *
from .exploitation import *
from .forensics import *
from .cloud import *
from .ai_automation import *

# Tool registry with all 500+ tools
OSINT_TOOL_REGISTRY = {
    "username_enumeration": 25,
    "email_osint": 25,
    "phone_osint": 20,
    "social_media_osint": 30,
    "domain_dns_osint": 30,
    "web_scraping": 25,
    "image_osint": 25,
    "geolocation_osint": 25,
    "blockchain_crypto": 20,
    "darknet_tor": 20,
    "document_osint": 20,
    "corporate_business": 20,
    "threat_intelligence": 25,
    "network_scanning": 25,
    "vulnerability_scanning": 25,
    "web_application_testing": 25,
    "directory_fuzzing": 20,
    "password_attacks": 20,
    "exploitation_frameworks": 15,
    "forensics_ir": 20,
    "cloud_osint": 20,
    "ai_automation": 20,
}

TOTAL_TOOLS = sum(OSINT_TOOL_REGISTRY.values())  # 500+ tools

def get_tool_count():
    """Return total number of integrated OSINT tools"""
    return TOTAL_TOOLS

def get_categories():
    """Return all OSINT categories"""
    return list(OSINT_TOOL_REGISTRY.keys())

def get_category_tools(category):
    """Return tool count for a specific category"""
    return OSINT_TOOL_REGISTRY.get(category, 0)
