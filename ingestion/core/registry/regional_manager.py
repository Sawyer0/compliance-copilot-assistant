"""Regional management for source organization."""

from pathlib import Path
from typing import Dict, List
from uuid import UUID

import yaml

from core.logging import get_logger
from models.source import Source

logger = get_logger(__name__)


class RegionalManager:
    """Manages regional organization of sources."""
    
    def __init__(self, sources_dir: Path):
        self.sources_dir = sources_dir
        self.regions_config = {
            'north_america/us': {'region': 'North America', 'jurisdiction': 'United States'},
            'north_america/canada': {'region': 'North America', 'jurisdiction': 'Canada'},
            'europe/eu': {'region': 'Europe', 'jurisdiction': 'European Union'},
            'europe/uk': {'region': 'Europe', 'jurisdiction': 'United Kingdom'},
            'asia_pacific/singapore': {'region': 'Asia Pacific', 'jurisdiction': 'Singapore'},
            'international': {'region': 'International', 'jurisdiction': 'Global'},
        }
    
    def create_empty_structure(self) -> None:
        """Create empty organized sources directory structure."""
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        
        for path, metadata in self.regions_config.items():
            region_dir = self.sources_dir / path
            region_dir.mkdir(parents=True, exist_ok=True)
            
            # Create empty source file for each region
            empty_config = {
                'version': '1.0',
                'region': metadata['region'],
                'jurisdiction': metadata['jurisdiction'],
                'sources': []
            }
            
            source_file = region_dir / f"{path.split('/')[-1]}_sources.yaml"
            if not source_file.exists():  # Don't overwrite existing files
                with open(source_file, 'w', encoding='utf-8') as f:
                    yaml.dump(empty_config, f, default_flow_style=False)
        
        logger.info("Created organized sources structure")
    
    def get_sources_by_region(self, region: str, sources: Dict[UUID, Source], source_files: Dict[str, Path]) -> List[Source]:
        """Get sources by region (e.g., 'North America', 'Europe', 'Asia Pacific')."""
        region_sources = []
        
        for source_id_str, source_file in source_files.items():
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    if data.get('region') == region:
                        source_id = UUID(source_id_str)
                        if source_id in sources:
                            region_sources.append(sources[source_id])
            except Exception:
                continue
        
        return region_sources
    
    def get_regional_summary(self, source_files: Dict[str, Path], sources: Dict[UUID, Source]) -> Dict[str, Dict[str, int]]:
        """Get a summary of sources organized by region and jurisdiction."""
        summary = {}
        
        for source_id_str, source_file in source_files.items():
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    region = data.get('region', 'Unknown')
                    jurisdiction = data.get('jurisdiction', 'Unknown')
                    
                    if region not in summary:
                        summary[region] = {}
                    if jurisdiction not in summary[region]:
                        summary[region][jurisdiction] = 0
                    
                    source_id = UUID(source_id_str)
                    if source_id in sources:
                        summary[region][jurisdiction] += 1
            except Exception:
                continue
        
        return summary
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions."""
        return list(set(config['region'] for config in self.regions_config.values()))
    
    def get_available_jurisdictions(self) -> List[str]:
        """Get list of available jurisdictions."""
        return [config['jurisdiction'] for config in self.regions_config.values()]
    
    def get_region_for_jurisdiction(self, jurisdiction: str) -> str:
        """Get the region for a given jurisdiction."""
        for config in self.regions_config.values():
            if config['jurisdiction'] == jurisdiction:
                return config['region']
        return 'Unknown'
    
    def get_jurisdictions_in_region(self, region: str) -> List[str]:
        """Get all jurisdictions within a region."""
        return [
            config['jurisdiction'] 
            for config in self.regions_config.values() 
            if config['region'] == region
        ] 