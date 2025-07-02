"""Source registry for managing source configurations."""

from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import yaml
from pydantic import ValidationError

from models.source import Source, SourceConfig
from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class SourceRegistry:
    """Registry for managing source configurations."""
    
    def __init__(self, sources_dir: Optional[Path] = None):
        self.settings = get_settings()
        self.sources_dir = sources_dir or self.settings.base_dir / "registry" / "sources"
        self._sources: Dict[UUID, Source] = {}
        self._source_files: Dict[str, Path] = {}  # Track which file each source came from
        self._load_sources()
    
    def _load_sources(self) -> None:
        """Load sources from organized regional YAML files."""
        if not self.sources_dir.exists():
            logger.warning(
                "Sources directory not found, creating empty registry",
                sources_dir=str(self.sources_dir)
            )
            self._create_empty_sources_structure()
            return
        
        try:
            # Find all YAML files in the sources directory recursively
            yaml_files = list(self.sources_dir.rglob("*.yaml")) + list(self.sources_dir.rglob("*.yml"))
            
            if not yaml_files:
                logger.warning("No YAML source files found in sources directory")
                return
            
            total_loaded = 0
            for yaml_file in yaml_files:
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f) or {}
                    
                    # Extract region/jurisdiction info
                    region = data.get('region', 'Unknown')
                    jurisdiction = data.get('jurisdiction', 'Unknown')
                    sources_data = data.get('sources', [])
                    
                    logger.debug(
                        "Loading sources file",
                        file=str(yaml_file),
                        region=region,
                        jurisdiction=jurisdiction,
                        source_count=len(sources_data)
                    )
                    
                    # Load each source in the file
                    for source_data in sources_data:
                        try:
                            config = SourceConfig(**source_data)
                            source = Source(config=config)
                            self._sources[config.source_id] = source
                            
                            # Track which file this source came from
                            self._source_files[str(config.source_id)] = yaml_file
                            
                            logger.debug(
                                "Loaded source",
                                source_id=str(config.source_id),
                                source_name=config.name,
                                region=region,
                                jurisdiction=jurisdiction
                            )
                            total_loaded += 1
                        
                        except ValidationError as e:
                            logger.error(
                                "Invalid source configuration",
                                source_data=source_data,
                                file=str(yaml_file),
                                error=str(e)
                            )
                
                except Exception as e:
                    logger.error(
                        "Failed to load sources file",
                        file=str(yaml_file),
                        error=str(e)
                    )
            
            logger.info(
                "Loaded sources from organized registry",
                total_sources=len(self._sources),
                active_sources=len([s for s in self._sources.values() if s.config.is_active]),
                files_processed=len(yaml_files),
                sources_loaded=total_loaded
            )
        
        except Exception as e:
            logger.error(
                "Failed to load sources directory",
                sources_dir=str(self.sources_dir),
                error=str(e)
            )
            self._sources = {}
            self._source_files = {}
    
    def _create_empty_sources_structure(self) -> None:
        """Create empty sources directory structure."""
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        
        # Create organized directory structure
        regions = {
            'north_america/us': {'region': 'North America', 'jurisdiction': 'United States'},
            'north_america/canada': {'region': 'North America', 'jurisdiction': 'Canada'},
            'europe/eu': {'region': 'Europe', 'jurisdiction': 'European Union'},
            'europe/uk': {'region': 'Europe', 'jurisdiction': 'United Kingdom'},
            'asia_pacific/singapore': {'region': 'Asia Pacific', 'jurisdiction': 'Singapore'},
            'international': {'region': 'International', 'jurisdiction': 'Global'},
        }
        
        for path, metadata in regions.items():
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
            with open(source_file, 'w', encoding='utf-8') as f:
                yaml.dump(empty_config, f, default_flow_style=False)
        
        logger.info("Created empty organized sources structure")
    
    def get_source(self, source_id: UUID) -> Optional[Source]:
        """Get source by ID."""
        return self._sources.get(source_id)
    
    def get_source_by_name(self, name: str) -> Optional[Source]:
        """Get source by name."""
        for source in self._sources.values():
            if source.config.name == name:
                return source
        return None
    
    def list_sources(self, active_only: bool = False) -> List[Source]:
        """List all sources."""
        sources = list(self._sources.values())
        
        if active_only:
            sources = [s for s in sources if s.config.is_active]
        
        return sources
    
    def add_source(self, config: SourceConfig) -> Source:
        """Add a new source."""
        source = Source(config=config)
        self._sources[config.source_id] = source
        self._save_sources()
        
        logger.info(
            "Added new source",
            source_id=str(config.source_id),
            source_name=config.name
        )
        
        return source
    
    def update_source(self, source_id: UUID, config: SourceConfig) -> Optional[Source]:
        """Update an existing source."""
        if source_id not in self._sources:
            return None
        
        source = Source(config=config)
        # Preserve runtime statistics
        old_source = self._sources[source_id]
        source.total_documents_fetched = old_source.total_documents_fetched
        source.successful_fetches = old_source.successful_fetches
        source.failed_fetches = old_source.failed_fetches
        source.average_fetch_time = old_source.average_fetch_time
        
        self._sources[source_id] = source
        self._save_sources()
        
        logger.info(
            "Updated source",
            source_id=str(source_id),
            source_name=config.name
        )
        
        return source
    
    def remove_source(self, source_id: UUID) -> bool:
        """Remove a source."""
        if source_id not in self._sources:
            return False
        
        source_name = self._sources[source_id].config.name
        del self._sources[source_id]
        self._save_sources()
        
        logger.info(
            "Removed source",
            source_id=str(source_id),
            source_name=source_name
        )
        
        return True
    
    def _save_sources(self) -> None:
        """Save sources back to their organized regional YAML files."""
        try:
            # Group sources by their original files
            file_sources = {}
            
            for source in self._sources.values():
                source_id_str = str(source.config.source_id)
                source_file = self._source_files.get(source_id_str)
                
                if source_file and source_file.exists():
                    if source_file not in file_sources:
                        file_sources[source_file] = []
                    file_sources[source_file].append(source)
                else:
                    # If no file tracked, try to determine by jurisdiction
                    jurisdiction = source.config.jurisdiction
                    source_file = self._get_file_for_jurisdiction(jurisdiction)
                    if source_file:
                        if source_file not in file_sources:
                            file_sources[source_file] = []
                        file_sources[source_file].append(source)
                        self._source_files[source_id_str] = source_file
            
            # Save each regional file
            for source_file, sources in file_sources.items():
                try:
                    # Load existing file to preserve metadata
                    if source_file.exists():
                        with open(source_file, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f) or {}
                    else:
                        data = {'version': '1.0', 'region': 'Unknown', 'jurisdiction': 'Unknown'}
                    
                    # Update sources data
                    sources_data = []
                    for source in sources:
                        source_dict = source.config.dict()
                        sources_data.append(source_dict)
                    
                    data['sources'] = sources_data
                    
                    # Write back to file
                    with open(source_file, 'w', encoding='utf-8') as f:
                        yaml.dump(data, f, default_flow_style=False)
                    
                    logger.debug(
                        "Saved regional source file",
                        file=str(source_file),
                        source_count=len(sources)
                    )
                
                except Exception as e:
                    logger.error(
                        "Failed to save regional source file",
                        file=str(source_file),
                        error=str(e)
                    )
            
            logger.debug("Saved sources to organized registry")
        
        except Exception as e:
            logger.error(
                "Failed to save sources",
                sources_dir=str(self.sources_dir),
                error=str(e)
            )
    
    def _get_file_for_jurisdiction(self, jurisdiction: str) -> Optional[Path]:
        """Get the appropriate file path for a jurisdiction."""
        jurisdiction_map = {
            'United States': self.sources_dir / 'north_america' / 'us' / 'us_sources.yaml',
            'Canada': self.sources_dir / 'north_america' / 'canada' / 'canada_sources.yaml',
            'European Union': self.sources_dir / 'europe' / 'eu' / 'eu_sources.yaml',
            'United Kingdom': self.sources_dir / 'europe' / 'uk' / 'uk_sources.yaml',
            'Singapore': self.sources_dir / 'asia_pacific' / 'singapore' / 'singapore_sources.yaml',
            'Global': self.sources_dir / 'international' / 'international_sources.yaml',
            'International': self.sources_dir / 'international' / 'international_sources.yaml',
        }
        
        return jurisdiction_map.get(jurisdiction)
    
    def get_sources_by_jurisdiction(self, jurisdiction: str) -> List[Source]:
        """Get sources by jurisdiction."""
        return [
            source for source in self._sources.values()
            if source.config.jurisdiction == jurisdiction
        ]
    
    def get_sources_by_type(self, source_type: str) -> List[Source]:
        """Get sources by type."""
        return [
            source for source in self._sources.values()
            if source.config.source_type == source_type
        ]
    
    def get_sources_by_priority(self, min_priority: int = 1) -> List[Source]:
        """Get sources by minimum priority, sorted by priority (highest first)."""
        sources = [
            source for source in self._sources.values()
            if source.config.priority >= min_priority and source.config.is_active
        ]
        
        return sorted(sources, key=lambda s: s.config.priority, reverse=True)
    
    def get_sources_by_region(self, region: str) -> List[Source]:
        """Get sources by region (e.g., 'North America', 'Europe', 'Asia Pacific')."""
        region_sources = []
        
        for source_id_str, source_file in self._source_files.items():
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    if data.get('region') == region:
                        source_id = UUID(source_id_str)
                        if source_id in self._sources:
                            region_sources.append(self._sources[source_id])
            except Exception:
                continue
        
        return region_sources
    
    def get_regional_summary(self) -> Dict[str, Dict[str, int]]:
        """Get a summary of sources organized by region and jurisdiction."""
        summary = {}
        
        for source_id_str, source_file in self._source_files.items():
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
                    if source_id in self._sources:
                        summary[region][jurisdiction] += 1
            except Exception:
                continue
        
        return summary 