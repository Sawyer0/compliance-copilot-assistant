"""File management for source configurations."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import yaml
from pydantic import ValidationError

from core.logging import get_logger
from models.source import Source, SourceConfig

logger = get_logger(__name__)


class SourceFileManager:
    """Manages loading and saving of source configuration files."""
    
    def __init__(self, sources_dir: Path):
        self.sources_dir = sources_dir
    
    def load_all_sources(self) -> Tuple[Dict[UUID, Source], Dict[str, Path]]:
        """Load all sources from organized regional YAML files."""
        sources = {}
        source_files = {}
        
        if not self.sources_dir.exists():
            logger.warning(
                "Sources directory not found",
                sources_dir=str(self.sources_dir)
            )
            return sources, source_files
        
        try:
            # Find all YAML files in the sources directory recursively
            yaml_files = list(self.sources_dir.rglob("*.yaml")) + list(self.sources_dir.rglob("*.yml"))
            
            if not yaml_files:
                logger.warning("No YAML source files found in sources directory")
                return sources, source_files
            
            total_loaded = 0
            for yaml_file in yaml_files:
                file_sources, file_mappings = self._load_single_file(yaml_file)
                sources.update(file_sources)
                source_files.update(file_mappings)
                total_loaded += len(file_sources)
            
            logger.info(
                "Loaded sources from organized registry",
                total_sources=len(sources),
                active_sources=len([s for s in sources.values() if s.config.is_active]),
                files_processed=len(yaml_files),
                sources_loaded=total_loaded
            )
            
        except Exception as e:
            logger.error(
                "Failed to load sources directory",
                sources_dir=str(self.sources_dir),
                error=str(e)
            )
        
        return sources, source_files
    
    def _load_single_file(self, yaml_file: Path) -> Tuple[Dict[UUID, Source], Dict[str, Path]]:
        """Load sources from a single YAML file."""
        sources = {}
        source_files = {}
        
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
                    sources[config.source_id] = source
                    
                    # Track which file this source came from
                    source_files[str(config.source_id)] = yaml_file
                    
                    logger.debug(
                        "Loaded source",
                        source_id=str(config.source_id),
                        source_name=config.name,
                        region=region,
                        jurisdiction=jurisdiction
                    )
                
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
        
        return sources, source_files
    
    def save_sources_by_file(self, sources: Dict[UUID, Source], source_files: Dict[str, Path]) -> None:
        """Save sources back to their organized regional YAML files."""
        try:
            # Group sources by their original files
            file_sources = {}
            
            for source in sources.values():
                source_id_str = str(source.config.source_id)
                source_file = source_files.get(source_id_str)
                
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
                        source_files[source_id_str] = source_file
            
            # Save each regional file
            for source_file, file_sources_list in file_sources.items():
                self._save_single_file(source_file, file_sources_list)
            
            logger.debug("Saved sources to organized registry")
        
        except Exception as e:
            logger.error(
                "Failed to save sources",
                sources_dir=str(self.sources_dir),
                error=str(e)
            )
    
    def _save_single_file(self, source_file: Path, sources: List[Source]) -> None:
        """Save sources to a single YAML file."""
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