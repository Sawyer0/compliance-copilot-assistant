"""Fetcher modules for different compliance document sources."""

from .base_fetcher import BaseFetcher, FetchResult
from .fetch_nist import NISTFetcher
from .fetch_eu_ai_act import EUAIActFetcher
from .fetch_fpf import FPFFetcher
from .fetch_us_gov import USGovernmentFetcher
from .fetch_canada_gov import CanadianGovernmentFetcher
from .fetch_uk_gov import UKGovernmentFetcher
from .fetch_international_reg import InternationalRegulatoryFetcher

__all__ = [
    'BaseFetcher',
    'FetchResult',
    'NISTFetcher',
    'EUAIActFetcher', 
    'FPFFetcher',
    'USGovernmentFetcher',
    'CanadianGovernmentFetcher',
    'UKGovernmentFetcher',
    'InternationalRegulatoryFetcher'
]

# Fetcher registry mapping source types to fetcher classes
FETCHER_REGISTRY = {
    'nist': NISTFetcher,
    'eu_ai_act': EUAIActFetcher,
    'fpf': FPFFetcher,
    'us_government': USGovernmentFetcher,
    'us_gov': USGovernmentFetcher,  # Alias
    'whitehouse': USGovernmentFetcher,
    'ftc': USGovernmentFetcher,
    'canada_government': CanadianGovernmentFetcher,
    'canada_gov': CanadianGovernmentFetcher,  # Alias
    'canadian_gov': CanadianGovernmentFetcher,  # Alias
    'uk_government': UKGovernmentFetcher,
    'uk_gov': UKGovernmentFetcher,  # Alias
    'singapore': InternationalRegulatoryFetcher,
    'singapore_gov': InternationalRegulatoryFetcher,
    'iso_iec': InternationalRegulatoryFetcher,
    'iso': InternationalRegulatoryFetcher,
    'iec': InternationalRegulatoryFetcher,
    'edpb': InternationalRegulatoryFetcher,
    'gdpr': InternationalRegulatoryFetcher,
    'international': InternationalRegulatoryFetcher,
    'regulatory': InternationalRegulatoryFetcher
}


def get_fetcher_class(source_type: str) -> type[BaseFetcher]:
    """Get the appropriate fetcher class for a source type."""
    source_type_lower = source_type.lower().replace('-', '_').replace(' ', '_')
    
    if source_type_lower in FETCHER_REGISTRY:
        return FETCHER_REGISTRY[source_type_lower]
    
    # Default fallback
    return InternationalRegulatoryFetcher


def list_available_fetchers() -> dict[str, str]:
    """List all available fetcher types and their descriptions."""
    return {
        'nist': 'NIST AI Risk Management Framework and related documents',
        'eu_ai_act': 'EU AI Act and European AI regulations',
        'fpf': 'Future of Privacy Forum research and reports',
        'us_government': 'US Government AI guidance (White House, FTC, etc.)',
        'canada_government': 'Canadian Government AI governance frameworks',
        'uk_government': 'UK Government AI white papers and guidance',
        'singapore': 'Singapore AI governance models and frameworks',
        'iso_iec': 'ISO/IEC AI standards and technical specifications',
        'edpb': 'European Data Protection Board GDPR AI guidance',
        'international': 'Generic international regulatory documents'
    } 